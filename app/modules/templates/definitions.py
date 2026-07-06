from dataclasses import dataclass


@dataclass(frozen=True)
class CompanyTemplate:
    code: str
    title: str
    description: str
    pipeline_name: str
    stages: list[str]
    lead_sources: list[str]
    knowledge_title: str
    knowledge_text: str
    ai_instruction: str


TEMPLATES = [
    CompanyTemplate(
        code="b2b_services",
        title="B2B услуги",
        description="Консалтинг, агентства, интеграторы, профессиональные услуги.",
        pipeline_name="B2B продажи",
        stages=["Новый лид", "Квалификация", "Встреча", "КП", "Переговоры", "Договор", "Выиграно"],
        lead_sources=["site", "referral", "conference", "cold_outreach"],
        knowledge_title="B2B sales playbook",
        knowledge_text=(
            "Шаблон B2B услуг. После новой заявки нужно связаться с клиентом в течение 15 минут, "
            "уточнить сферу бизнеса, роль контакта, проблему, бюджет, срок принятия решения и текущий процесс. "
            "Квалифицированный лид должен иметь боль, лицо принятия решения, примерный бюджет и следующий шаг. "
            "После встречи менеджер отправляет краткое резюме, КП и создает задачу follow-up."
        ),
        ai_instruction="Фокусируйся на квалификации BANT, следующем шаге и follow-up задачах.",
    ),
    CompanyTemplate(
        code="wholesale",
        title="Оптовая торговля",
        description="Дистрибуция, поставки, дилеры, регулярные закупки.",
        pipeline_name="Оптовые продажи",
        stages=["Заявка", "Подбор товара", "Расчет", "Счет", "Оплата", "Отгрузка", "Повторная продажа"],
        lead_sources=["site", "marketplace", "dealer", "phone", "csv"],
        knowledge_title="Wholesale sales playbook",
        knowledge_text=(
            "Шаблон оптовой торговли. В заявке важно уточнить номенклатуру, объем, регион, сроки поставки, "
            "условия оплаты и наличие договора. После счета менеджер контролирует оплату и отгрузку. "
            "После первой поставки нужно создать задачу на повторный контакт."
        ),
        ai_instruction="Помогай уточнять товар, объем, сроки, оплату и следующий закупочный цикл.",
    ),
    CompanyTemplate(
        code="real_estate",
        title="Недвижимость",
        description="Продажа объектов, агентства, новостройки, аренда.",
        pipeline_name="Недвижимость",
        stages=["Новый запрос", "Квалификация", "Подбор объектов", "Показ", "Бронь", "Сделка"],
        lead_sources=["site", "cian", "avito", "referral", "phone"],
        knowledge_title="Real estate sales playbook",
        knowledge_text=(
            "Шаблон недвижимости. Нужно уточнить бюджет, район, тип объекта, срок покупки, источник средств, "
            "ипотеку и обязательные критерии. После подбора объектов менеджер назначает показ и фиксирует обратную связь."
        ),
        ai_instruction="Помогай подбирать следующий шаг: квалификация, подбор, показ, бронь.",
    ),
    CompanyTemplate(
        code="online_education",
        title="Онлайн-образование",
        description="Курсы, школы, наставничество, обучение сотрудников.",
        pipeline_name="Продажи обучения",
        stages=["Заявка", "Диагностика", "Презентация", "Оплата", "Онбординг"],
        lead_sources=["webinar", "site", "ads", "referral", "telegram"],
        knowledge_title="Education sales playbook",
        knowledge_text=(
            "Шаблон онлайн-образования. Нужно уточнить цель обучения, текущий уровень, желаемый результат, "
            "сроки, бюджет и возражения. После презентации менеджер отправляет программу, отзывы и дедлайн оплаты."
        ),
        ai_instruction="Помогай выявлять цель обучения, мотивацию и возражения.",
    ),
    CompanyTemplate(
        code="manufacturing",
        title="Производство",
        description="Заказы на производство, проектные продажи, B2B поставки.",
        pipeline_name="Производственные заказы",
        stages=["Запрос", "ТЗ", "Расчет", "Согласование", "Производство", "Отгрузка"],
        lead_sources=["site", "tender", "dealer", "referral", "email"],
        knowledge_title="Manufacturing sales playbook",
        knowledge_text=(
            "Шаблон производства. Важно собрать техническое задание, объем, материалы, требования к качеству, "
            "сроки, логистику и условия оплаты. После расчета нужно подтвердить спецификацию и дату готовности."
        ),
        ai_instruction="Помогай собирать ТЗ, контролировать расчет, производство и отгрузку.",
    ),
]


def get_template(code: str) -> CompanyTemplate | None:
    return next((template for template in TEMPLATES if template.code == code), None)

