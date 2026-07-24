import json
import smtplib
import ssl
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from email.utils import make_msgid
from urllib.parse import urlencode

import httpx

from app.core.config import settings


class ProviderError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def google_authorization_url(state: str) -> str:
    _require_oauth_settings("google_calendar")
    query = urlencode(
        {
            "client_id": settings.google_oauth_client_id,
            "redirect_uri": _oauth_callback_url("google_calendar"),
            "response_type": "code",
            "scope": "https://www.googleapis.com/auth/calendar",
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
            "state": state,
        }
    )
    return f"https://accounts.google.com/o/oauth2/v2/auth?{query}"


def microsoft_authorization_url(state: str) -> str:
    _require_oauth_settings("microsoft_calendar")
    tenant = settings.microsoft_oauth_tenant
    query = urlencode(
        {
            "client_id": settings.microsoft_oauth_client_id,
            "redirect_uri": _oauth_callback_url("microsoft_calendar"),
            "response_type": "code",
            "response_mode": "query",
            "scope": "offline_access Calendars.ReadWrite User.Read",
            "state": state,
        }
    )
    return f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize?{query}"


def exchange_authorization_code(provider: str, code: str) -> dict:
    _require_oauth_settings(provider)
    if provider == "google_calendar":
        url = "https://oauth2.googleapis.com/token"
        data = {
            "client_id": settings.google_oauth_client_id,
            "client_secret": settings.google_oauth_client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": _oauth_callback_url(provider),
        }
    elif provider == "microsoft_calendar":
        url = (
            f"https://login.microsoftonline.com/{settings.microsoft_oauth_tenant}"
            "/oauth2/v2.0/token"
        )
        data = {
            "client_id": settings.microsoft_oauth_client_id,
            "client_secret": settings.microsoft_oauth_client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": _oauth_callback_url(provider),
            "scope": "offline_access Calendars.ReadWrite User.Read",
        }
    else:
        raise ProviderError("Unsupported OAuth provider")
    payload = _request_json("POST", url, data=data)
    return _normalize_token(payload)


def refresh_access_token(provider: str, credentials: dict) -> dict:
    expires_at = credentials.get("expires_at")
    if credentials.get("access_token") and expires_at:
        expiry = datetime.fromisoformat(str(expires_at))
        if expiry > datetime.now(timezone.utc) + timedelta(minutes=2):
            return credentials
    refresh_token = credentials.get("refresh_token")
    if not refresh_token:
        raise ProviderError("OAuth refresh token is missing; reconnect the account")
    if provider == "google_calendar":
        url = "https://oauth2.googleapis.com/token"
        data = {
            "client_id": settings.google_oauth_client_id,
            "client_secret": settings.google_oauth_client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
    elif provider == "microsoft_calendar":
        url = (
            f"https://login.microsoftonline.com/{settings.microsoft_oauth_tenant}"
            "/oauth2/v2.0/token"
        )
        data = {
            "client_id": settings.microsoft_oauth_client_id,
            "client_secret": settings.microsoft_oauth_client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
            "scope": "offline_access Calendars.ReadWrite User.Read",
        }
    else:
        raise ProviderError("Unsupported OAuth provider")
    refreshed = _normalize_token(_request_json("POST", url, data=data))
    if not refreshed.get("refresh_token"):
        refreshed["refresh_token"] = refresh_token
    return refreshed


def fetch_calendar_events(provider: str, credentials: dict, cursor: str | None) -> tuple[list[dict], str]:
    token = credentials["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    events: list[dict] = []
    if provider == "google_calendar":
        url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
        base_params: dict[str, str] = {
            "singleEvents": "true",
            "showDeleted": "true",
            "maxResults": "250",
        }
        if cursor:
            base_params["syncToken"] = cursor
        else:
            base_params["timeMin"] = (
                datetime.now(timezone.utc) - timedelta(days=30)
            ).isoformat()
        params: dict[str, str] | None = dict(base_params)
        next_cursor = ""
        while url:
            try:
                payload = _request_json("GET", url, headers=headers, params=params)
            except ProviderError as error:
                if cursor and error.status_code == 410:
                    return fetch_calendar_events(provider, credentials, None)
                raise
            events.extend(_normalize_google_event(item) for item in payload.get("items", []))
            page_token = payload.get("nextPageToken")
            next_cursor = payload.get("nextSyncToken") or next_cursor
            params = {**base_params, "pageToken": page_token} if page_token else None
            url = url if page_token else ""
        if not next_cursor:
            raise ProviderError("Google Calendar did not return nextSyncToken")
        return events, next_cursor

    if provider == "microsoft_calendar":
        if cursor:
            url = cursor
        else:
            start = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
            end = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
            url = (
                "https://graph.microsoft.com/v1.0/me/calendarView/delta?"
                + urlencode({"startDateTime": start, "endDateTime": end})
            )
        next_cursor = ""
        while url:
            payload = _request_json("GET", url, headers=headers)
            events.extend(_normalize_microsoft_event(item) for item in payload.get("value", []))
            next_url = payload.get("@odata.nextLink")
            next_cursor = payload.get("@odata.deltaLink") or next_cursor
            url = next_url or ""
        if not next_cursor:
            raise ProviderError("Microsoft Graph did not return deltaLink")
        return events, next_cursor
    raise ProviderError("Unsupported calendar provider")


def create_calendar_event(provider: str, credentials: dict, payload: dict) -> dict:
    headers = {
        "Authorization": f"Bearer {credentials['access_token']}",
        "Content-Type": "application/json",
    }
    if provider == "google_calendar":
        body = {
            "summary": payload["title"],
            "description": payload.get("description"),
            "start": {"dateTime": payload["starts_at"], "timeZone": payload.get("timezone", "UTC")},
            "end": {"dateTime": payload["ends_at"], "timeZone": payload.get("timezone", "UTC")},
            "attendees": [{"email": value} for value in payload.get("attendees", [])],
        }
        result = _request_json(
            "POST",
            "https://www.googleapis.com/calendar/v3/calendars/primary/events",
            headers=headers,
            json=body,
        )
        return _normalize_google_event(result)
    if provider == "microsoft_calendar":
        body = {
            "subject": payload["title"],
            "body": {"contentType": "text", "content": payload.get("description") or ""},
            "start": {"dateTime": payload["starts_at"], "timeZone": payload.get("timezone", "UTC")},
            "end": {"dateTime": payload["ends_at"], "timeZone": payload.get("timezone", "UTC")},
            "attendees": [
                {"emailAddress": {"address": value}, "type": "required"}
                for value in payload.get("attendees", [])
            ],
        }
        result = _request_json(
            "POST",
            "https://graph.microsoft.com/v1.0/me/events",
            headers=headers,
            json=body,
        )
        return _normalize_microsoft_event(result)
    raise ProviderError("Unsupported calendar provider")


def send_smtp_email(credentials: dict, account_settings: dict, payload: dict) -> str:
    host = str(account_settings.get("smtp_host") or "")
    if not host:
        raise ProviderError("SMTP host is missing")
    port = int(account_settings.get("smtp_port") or 465)
    username = str(credentials.get("username") or "")
    password = str(credentials.get("password") or "")
    sender = str(account_settings.get("from_email") or username)
    if not username or not password or not sender:
        raise ProviderError("SMTP credentials are incomplete")
    message = EmailMessage()
    message["From"] = sender
    message["To"] = payload["recipient"]
    message["Subject"] = payload["subject"]
    message["Message-ID"] = make_msgid(domain=sender.split("@")[-1] if "@" in sender else None)
    message.set_content(payload.get("body") or "")
    timeout = int(account_settings.get("timeout_seconds") or 20)
    use_ssl = bool(account_settings.get("smtp_use_ssl", port == 465))
    context = ssl.create_default_context()
    if use_ssl:
        client: smtplib.SMTP = smtplib.SMTP_SSL(host, port, timeout=timeout, context=context)
    else:
        client = smtplib.SMTP(host, port, timeout=timeout)
    try:
        if not use_ssl and account_settings.get("smtp_starttls", True):
            client.starttls(context=context)
        client.login(username, password)
        client.send_message(message)
    except (OSError, smtplib.SMTPException) as error:
        raise ProviderError(f"SMTP send failed: {error}") from error
    finally:
        try:
            client.quit()
        except (OSError, smtplib.SMTPException):
            pass
    return str(message["Message-ID"] or "")


def test_smtp_connection(credentials: dict, account_settings: dict) -> None:
    host = str(account_settings.get("smtp_host") or "")
    if not host:
        raise ProviderError("SMTP host is missing")
    port = int(account_settings.get("smtp_port") or 465)
    timeout = int(account_settings.get("timeout_seconds") or 20)
    use_ssl = bool(account_settings.get("smtp_use_ssl", port == 465))
    context = ssl.create_default_context()
    try:
        if use_ssl:
            client: smtplib.SMTP = smtplib.SMTP_SSL(host, port, timeout=timeout, context=context)
        else:
            client = smtplib.SMTP(host, port, timeout=timeout)
            if account_settings.get("smtp_starttls", True):
                client.starttls(context=context)
        client.login(str(credentials["username"]), str(credentials["password"]))
        client.quit()
    except (OSError, smtplib.SMTPException) as error:
        raise ProviderError(f"SMTP connection failed: {error}") from error


def _oauth_callback_url(provider: str) -> str:
    return f"{settings.public_api_base_url.rstrip('/')}/connectors/oauth/{provider}/callback"


def _require_oauth_settings(provider: str) -> None:
    if settings.secret_key == "change-me-in-production" or len(settings.secret_key) < 32:
        raise ProviderError("Set a unique SECRET_KEY of at least 32 characters before OAuth")
    if provider == "google_calendar":
        values = (settings.google_oauth_client_id, settings.google_oauth_client_secret)
    elif provider == "microsoft_calendar":
        values = (settings.microsoft_oauth_client_id, settings.microsoft_oauth_client_secret)
    else:
        raise ProviderError("Unsupported OAuth provider")
    if not all(values):
        raise ProviderError(f"{provider} OAuth credentials are not configured")


def _normalize_token(payload: dict) -> dict:
    if "access_token" not in payload:
        raise ProviderError(f"OAuth token response is invalid: {json.dumps(payload)[:300]}")
    expires_in = int(payload.get("expires_in") or 3600)
    return {
        **payload,
        "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=expires_in)).isoformat(),
    }


def _request_json(method: str, url: str, **kwargs) -> dict:
    try:
        response = httpx.request(method, url, timeout=30.0, **kwargs)
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPError, ValueError) as error:
        detail = ""
        if isinstance(error, httpx.HTTPStatusError):
            detail = error.response.text[:500]
        status_code = error.response.status_code if isinstance(error, httpx.HTTPStatusError) else None
        raise ProviderError(
            f"Provider request failed: {error} {detail}".strip(),
            status_code=status_code,
        ) from error


def _normalize_google_event(item: dict) -> dict:
    return {
        "id": item.get("id"),
        "deleted": item.get("status") == "cancelled",
        "title": item.get("summary") or "Calendar event",
        "description": item.get("description"),
        "organizer": (item.get("organizer") or {}).get("email"),
        "attendees": [
            attendee.get("email")
            for attendee in item.get("attendees", [])
            if attendee.get("email")
        ],
        "starts_at": (item.get("start") or {}).get("dateTime")
        or (item.get("start") or {}).get("date"),
        "ends_at": (item.get("end") or {}).get("dateTime")
        or (item.get("end") or {}).get("date"),
        "updated_at": item.get("updated"),
        "html_link": item.get("htmlLink"),
    }


def _normalize_microsoft_event(item: dict) -> dict:
    return {
        "id": item.get("id"),
        "deleted": "@removed" in item or item.get("isCancelled", False),
        "title": item.get("subject") or "Calendar event",
        "description": (item.get("body") or {}).get("content"),
        "organizer": ((item.get("organizer") or {}).get("emailAddress") or {}).get("address"),
        "attendees": [
            (attendee.get("emailAddress") or {}).get("address")
            for attendee in item.get("attendees", [])
            if (attendee.get("emailAddress") or {}).get("address")
        ],
        "starts_at": (item.get("start") or {}).get("dateTime"),
        "ends_at": (item.get("end") or {}).get("dateTime"),
        "updated_at": item.get("lastModifiedDateTime"),
        "html_link": item.get("webLink"),
    }
