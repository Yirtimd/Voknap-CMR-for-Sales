import type { EntityType } from "./types";

export type LifecycleField = {
  key: string;
  label: string;
  kind?: "text" | "email" | "tel" | "number" | "datetime-local" | "textarea" | "select" | "reference";
  reference?: "companies" | "contacts" | "leads" | "deals" | "stages";
  options?: Array<{ value: string; label: string }>;
  required?: boolean;
  create?: boolean;
  edit?: boolean;
  min?: number;
  max?: number;
};

export type LifecycleEntityConfig = {
  label: string;
  singular: string;
  titleKey: string;
  subtitleKeys: string[];
  merge: boolean;
  reassign: boolean;
  sortable: Array<{ value: string; label: string }>;
  fields: LifecycleField[];
};

export const ENTITY_TYPES: EntityType[] = ["contacts", "leads", "deals", "tasks", "notes"];

export const ENTITY_CONFIG: Record<EntityType, LifecycleEntityConfig> = {
  contacts: {
    label: "Контакты",
    singular: "контакт",
    titleKey: "name",
    subtitleKeys: ["company_name", "email", "phone"],
    merge: true,
    reassign: true,
    sortable: [
      { value: "created_at", label: "Дата создания" },
      { value: "updated_at", label: "Дата изменения" },
      { value: "name", label: "Имя" }
    ],
    fields: [
      { key: "company_id", label: "Компания", kind: "reference", reference: "companies", required: true, create: true, edit: true },
      { key: "name", label: "Имя", required: true, create: true, edit: true },
      { key: "phone", label: "Телефон", kind: "tel", create: true, edit: true },
      { key: "email", label: "Email", kind: "email", create: true, edit: true },
      { key: "company_name", label: "Название компании", create: true, edit: true },
      { key: "role", label: "Должность", create: true, edit: true }
    ]
  },
  leads: {
    label: "Лиды",
    singular: "лид",
    titleKey: "title",
    subtitleKeys: ["source", "status"],
    merge: true,
    reassign: true,
    sortable: [
      { value: "created_at", label: "Дата создания" },
      { value: "updated_at", label: "Дата изменения" },
      { value: "title", label: "Название" },
      { value: "status", label: "Статус" },
      { value: "qualified_at", label: "Квалификация" }
    ],
    fields: [
      { key: "company_id", label: "Компания", kind: "reference", reference: "companies", required: true, create: true, edit: true },
      { key: "title", label: "Название", required: true, create: true, edit: true },
      { key: "source", label: "Источник", create: true, edit: true },
      { key: "contact_id", label: "Контакт", kind: "reference", reference: "contacts", create: true, edit: true },
      {
        key: "status",
        label: "Рабочий статус",
        kind: "select",
        options: [
          { value: "new", label: "Новый" },
          { value: "open", label: "В работе" }
        ],
        edit: true
      }
    ]
  },
  deals: {
    label: "Сделки",
    singular: "сделку",
    titleKey: "title",
    subtitleKeys: ["amount", "status", "risk_level"],
    merge: true,
    reassign: true,
    sortable: [
      { value: "created_at", label: "Дата создания" },
      { value: "updated_at", label: "Дата изменения" },
      { value: "title", label: "Название" },
      { value: "amount", label: "Сумма" },
      { value: "expected_close_date", label: "Дата закрытия" }
    ],
    fields: [
      { key: "company_id", label: "Компания", kind: "reference", reference: "companies", required: true, create: true, edit: true },
      { key: "title", label: "Название", required: true, create: true, edit: true },
      { key: "stage_id", label: "Этап", kind: "reference", reference: "stages", required: true, create: true, edit: true },
      { key: "lead_id", label: "Лид", kind: "reference", reference: "leads", create: true, edit: true },
      { key: "amount", label: "Сумма", kind: "number", min: 0, create: true, edit: true },
      { key: "discount_percent", label: "Скидка, %", kind: "number", min: 0, max: 100, create: true, edit: true },
      { key: "probability", label: "Вероятность, %", kind: "number", min: 0, max: 100, create: true, edit: true },
      { key: "expected_close_date", label: "Ожидаемое закрытие", kind: "datetime-local", create: true, edit: true },
      { key: "expected_next_event", label: "Следующее событие", create: true, edit: true },
      { key: "next_step", label: "Следующий шаг", create: true, edit: true },
      {
        key: "risk_level",
        label: "Риск",
        kind: "select",
        options: [
          { value: "low", label: "Низкий" },
          { value: "medium", label: "Средний" },
          { value: "high", label: "Высокий" }
        ],
        create: true,
        edit: true
      },
      { key: "forecast_category", label: "Категория прогноза", create: true, edit: true }
    ]
  },
  tasks: {
    label: "Задачи",
    singular: "задачу",
    titleKey: "title",
    subtitleKeys: ["priority", "status", "due_at"],
    merge: false,
    reassign: true,
    sortable: [
      { value: "created_at", label: "Дата создания" },
      { value: "updated_at", label: "Дата изменения" },
      { value: "title", label: "Название" },
      { value: "priority", label: "Приоритет" },
      { value: "due_at", label: "Срок" }
    ],
    fields: [
      { key: "company_id", label: "Компания", kind: "reference", reference: "companies", required: true, create: true, edit: true },
      { key: "title", label: "Название", required: true, create: true, edit: true },
      { key: "description", label: "Описание", kind: "textarea", create: true, edit: true },
      { key: "deal_id", label: "Сделка", kind: "reference", reference: "deals", create: true, edit: true },
      {
        key: "priority",
        label: "Приоритет",
        kind: "select",
        options: [
          { value: "low", label: "Низкий" },
          { value: "normal", label: "Обычный" },
          { value: "high", label: "Высокий" }
        ],
        create: true,
        edit: true
      },
      { key: "due_at", label: "Срок", kind: "datetime-local", create: true, edit: true },
      {
        key: "status",
        label: "Статус",
        kind: "select",
        options: [
          { value: "open", label: "Открыта" },
          { value: "in_progress", label: "В работе" },
          { value: "done", label: "Выполнена" }
        ],
        edit: true
      }
    ]
  },
  notes: {
    label: "Заметки",
    singular: "заметку",
    titleKey: "text",
    subtitleKeys: ["created_at"],
    merge: false,
    reassign: false,
    sortable: [
      { value: "created_at", label: "Дата создания" },
      { value: "updated_at", label: "Дата изменения" }
    ],
    fields: [
      { key: "company_id", label: "Компания", kind: "reference", reference: "companies", required: true, create: true },
      { key: "text", label: "Текст", kind: "textarea", required: true, create: true, edit: true },
      { key: "lead_id", label: "Лид", kind: "reference", reference: "leads", create: true },
      { key: "deal_id", label: "Сделка", kind: "reference", reference: "deals", create: true }
    ]
  }
};
