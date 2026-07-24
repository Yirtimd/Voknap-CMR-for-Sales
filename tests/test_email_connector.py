from app.modules.connectors.service import ConnectorService
from app.modules.connectors.providers import send_smtp_email


RAW_EMAIL = b"""From: =?UTF-8?B?0JjQstCw0L0g0J/RtdGC0YDQvtCy?= <client@example.com>\r
To: sales@example.com\r
Subject: =?UTF-8?B?0JfQsNC/0YDQvtGBINC90LAg0JrQnw==?=\r
Date: Sun, 13 Jul 2026 10:00:00 +0300\r
Message-ID: <crm-test-1@example.com>\r
Content-Type: text/plain; charset=utf-8\r
\r
Please send proposal.\r
"""


class FakeImap:
    def select(self, folder: str, readonly: bool = True):
        assert folder == "INBOX"
        assert readonly is True
        return "OK", [b"1"]

    def uid(self, command: str, *args):
        if command == "search":
            assert args[-1] == "UID 42:*"
            return "OK", [b"42"]
        if command == "fetch":
            return "OK", [(b"42 (RFC822)", RAW_EMAIL)]
        raise AssertionError(command)

    def logout(self):
        return "BYE", []


def test_credentials_use_authenticated_encryption():
    service = ConnectorService(None)
    credentials = {"username": "sales@example.com", "password": "app-password"}

    encrypted = service._encrypt_credentials(credentials)

    assert "app-password" not in encrypted
    assert service._decrypt_credentials(encrypted) == credentials


def test_imap_fetch_decodes_message_and_advances_cursor(monkeypatch):
    service = ConnectorService(None)
    monkeypatch.setattr(service, "_imap_connect", lambda credentials, settings: FakeImap())

    messages, cursor = service._fetch_imap_messages(
        {"username": "sales@example.com", "password": "app-password"},
        {"host": "imap.example.com", "folder": "INBOX"},
        after_uid=41,
        limit=100,
    )

    assert cursor == 42
    assert messages[0]["sender"].endswith("<client@example.com>")
    assert messages[0]["subject"] == "Запрос на КП"
    assert messages[0]["body"] == "Please send proposal."
    assert messages[0]["external_id"].endswith(":INBOX:42")


def test_smtp_send_uses_configured_account(monkeypatch):
    sent = []

    class FakeSmtp:
        def __init__(self, host, port, timeout, context):
            assert (host, port, timeout) == ("smtp.example.com", 465, 20)

        def login(self, username, password):
            assert (username, password) == ("sales@example.com", "app-password")

        def send_message(self, message):
            sent.append(message)

        def quit(self):
            return None

    monkeypatch.setattr("app.modules.connectors.providers.smtplib.SMTP_SSL", FakeSmtp)

    message_id = send_smtp_email(
        {"username": "sales@example.com", "password": "app-password"},
        {
            "smtp_host": "smtp.example.com",
            "smtp_port": 465,
            "smtp_use_ssl": True,
            "from_email": "sales@example.com",
        },
        {
            "recipient": "client@example.com",
            "subject": "Proposal",
            "body": "Attached later",
        },
    )

    assert sent[0]["To"] == "client@example.com"
    assert sent[0]["Subject"] == "Proposal"
    assert message_id.startswith("<")
