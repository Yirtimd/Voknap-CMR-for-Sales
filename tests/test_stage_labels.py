from app.modules.sales.stages import stage_label_ru


def test_standard_stage_names_are_localized_consistently():
    assert [
        stage_label_ru(name)
        for name in ("New", "Discovery", "Proposal", "Negotiation", "Won")
    ] == ["Новые", "Разработка", "КП", "Переговоры", "Закрыты"]


def test_custom_and_already_localized_stage_names_are_preserved():
    assert stage_label_ru("Legal review") == "Legal review"
    assert stage_label_ru("Переговоры") == "Переговоры"
