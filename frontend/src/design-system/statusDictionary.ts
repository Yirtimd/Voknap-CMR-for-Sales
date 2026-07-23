export type StatusTone = "neutral" | "info" | "success" | "warning" | "danger" | "ai";
export type StatusDomain =
  | "common"
  | "company"
  | "lead"
  | "deal"
  | "task"
  | "document"
  | "connector"
  | "communication"
  | "aiAction"
  | "template"
  | "automation"
  | "approval"
  | "outbox"
  | "invitation"
  | "risk"
  | "priority"
  | "role";

export type StatusMeta = {
  label: string;
  tone: StatusTone;
};

const common: Record<string, StatusMeta> = {
  active: { label: "Активно", tone: "success" },
  inactive: { label: "Отключено", tone: "neutral" },
  enabled: { label: "Включено", tone: "success" },
  disabled: { label: "Отключено", tone: "neutral" },
  new: { label: "Новое", tone: "info" },
  open: { label: "Открыто", tone: "info" },
  pending: { label: "Ожидает", tone: "warning" },
  processing: { label: "Обрабатывается", tone: "info" },
  running: { label: "Выполняется", tone: "info" },
  completed: { label: "Завершено", tone: "success" },
  done: { label: "Завершено", tone: "success" },
  success: { label: "Успешно", tone: "success" },
  succeeded: { label: "Успешно", tone: "success" },
  failed: { label: "Ошибка", tone: "danger" },
  error: { label: "Ошибка", tone: "danger" },
  cancelled: { label: "Отменено", tone: "neutral" },
  archived: { label: "В архиве", tone: "neutral" },
  deleted: { label: "В корзине", tone: "danger" }
};

const dictionaries: Record<StatusDomain, Record<string, StatusMeta>> = {
  common,
  company: {
    active: { label: "Активная", tone: "success" },
    inactive: { label: "Неактивная", tone: "neutral" },
    prospect: { label: "Потенциальный клиент", tone: "info" },
    churned: { label: "Ушедший клиент", tone: "danger" }
  },
  lead: {
    new: { label: "Новый", tone: "info" },
    contacted: { label: "Связались", tone: "info" },
    qualified: { label: "Квалифицирован", tone: "success" },
    converted: { label: "Конвертирован", tone: "success" },
    disqualified: { label: "Дисквалифицирован", tone: "neutral" }
  },
  deal: {
    open: { label: "Открыта", tone: "info" },
    won: { label: "Выиграна", tone: "success" },
    lost: { label: "Проиграна", tone: "danger" },
    on_hold: { label: "Приостановлена", tone: "warning" }
  },
  task: {
    open: { label: "Открыта", tone: "info" },
    in_progress: { label: "В работе", tone: "info" },
    waiting: { label: "Ожидает", tone: "warning" },
    completed: { label: "Завершена", tone: "success" },
    overdue: { label: "Просрочена", tone: "danger" },
    cancelled: { label: "Отменена", tone: "neutral" }
  },
  document: {
    uploaded: { label: "Загружен", tone: "info" },
    processing: { label: "Индексируется", tone: "info" },
    indexed: { label: "Готов", tone: "success" },
    ready: { label: "Готов", tone: "success" },
    failed: { label: "Ошибка обработки", tone: "danger" }
  },
  connector: {
    connected: { label: "Подключён", tone: "success" },
    disconnected: { label: "Отключён", tone: "neutral" },
    syncing: { label: "Синхронизация", tone: "info" },
    success: { label: "Успешно", tone: "success" },
    retry_scheduled: { label: "Повтор запланирован", tone: "warning" },
    failed: { label: "Ошибка синхронизации", tone: "danger" }
  },
  communication: {
    new: { label: "Не привязано", tone: "warning" },
    received: { label: "Получено", tone: "info" },
    unread: { label: "Не прочитано", tone: "info" },
    linked: { label: "Привязано", tone: "success" },
    activity_created: { label: "Активность создана", tone: "success" }
  },
  aiAction: {
    pending: { label: "Ожидает подтверждения", tone: "warning" },
    confirmed: { label: "Подтверждено", tone: "success" },
    completed: { label: "Выполнено", tone: "success" },
    rejected: { label: "Отклонено", tone: "danger" },
    failed: { label: "Ошибка выполнения", tone: "danger" }
  },
  template: {
    draft: { label: "Черновик", tone: "neutral" },
    active: { label: "Активен", tone: "success" },
    applied: { label: "Применён", tone: "success" },
    failed: { label: "Ошибка применения", tone: "danger" }
  },
  automation: {
    running: { label: "Выполняется", tone: "info" },
    succeeded: { label: "Успешно", tone: "success" },
    failed: { label: "Ошибка", tone: "danger" },
    skipped: { label: "Пропущено", tone: "neutral" },
    cancelled: { label: "Отменено", tone: "neutral" }
  },
  approval: {
    pending: { label: "Ожидает решения", tone: "warning" },
    approved: { label: "Согласовано", tone: "success" },
    rejected: { label: "Отклонено", tone: "danger" },
    expired: { label: "Срок истёк", tone: "neutral" }
  },
  outbox: {
    pending: { label: "Ожидает отправки", tone: "warning" },
    sending: { label: "Отправляется", tone: "info" },
    sent: { label: "Отправлено", tone: "success" },
    failed: { label: "Ошибка доставки", tone: "danger" },
    cancelled: { label: "Отменено", tone: "neutral" }
  },
  invitation: {
    pending: { label: "Ожидает принятия", tone: "warning" },
    accepted: { label: "Принято", tone: "success" },
    revoked: { label: "Отозвано", tone: "danger" },
    expired: { label: "Срок истёк", tone: "neutral" }
  },
  risk: {
    none: { label: "Без риска", tone: "neutral" },
    low: { label: "Низкий риск", tone: "success" },
    medium: { label: "Средний риск", tone: "warning" },
    high: { label: "Высокий риск", tone: "danger" },
    critical: { label: "Критический риск", tone: "danger" }
  },
  priority: {
    low: { label: "Низкий", tone: "neutral" },
    normal: { label: "Средний", tone: "info" },
    medium: { label: "Средний", tone: "info" },
    high: { label: "Высокий", tone: "warning" },
    urgent: { label: "Срочный", tone: "danger" }
  },
  role: {
    owner: { label: "Владелец", tone: "ai" },
    admin: { label: "Администратор", tone: "info" },
    sales_manager: { label: "Руководитель продаж", tone: "info" },
    sales_rep: { label: "Менеджер продаж", tone: "neutral" },
    viewer: { label: "Наблюдатель", tone: "neutral" }
  }
};

function normalize(value: string | null | undefined) {
  return String(value ?? "").trim().toLowerCase().replace(/[\s-]+/g, "_");
}

function humanize(value: string) {
  const normalized = normalize(value);
  if (!normalized) return "Не указан";
  return normalized.charAt(0).toUpperCase() + normalized.slice(1).replace(/_/g, " ");
}

export function statusMeta(value: string | null | undefined, domain: StatusDomain = "common"): StatusMeta {
  const key = normalize(value);
  return dictionaries[domain][key] ?? common[key] ?? { label: humanize(key), tone: "neutral" };
}

export function statusLabel(value: string | null | undefined, domain: StatusDomain = "common") {
  return statusMeta(value, domain).label;
}

export function statusTone(value: string | null | undefined, domain: StatusDomain = "common") {
  return statusMeta(value, domain).tone;
}
