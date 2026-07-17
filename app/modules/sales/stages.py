STAGE_LABELS_RU = {
    "new": "Новые",
    "lead": "Новые",
    "new lead": "Новые",
    "qualified": "Разработка",
    "qualification": "Разработка",
    "discovery": "Разработка",
    "meeting": "Разработка",
    "proposal": "КП",
    "quote": "КП",
    "quotation": "КП",
    "negotiation": "Переговоры",
    "negotiations": "Переговоры",
    "won": "Закрыты",
    "lost": "Закрыты",
    "closed": "Закрыты",
    "closed won": "Закрыты",
    "closed lost": "Закрыты",
}


def stage_label_ru(value: str | None) -> str:
    source = (value or "").strip()
    if not source:
        return "Без этапа"
    return STAGE_LABELS_RU.get(source.lower(), source)
