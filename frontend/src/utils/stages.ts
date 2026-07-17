const STAGE_LABELS: Record<string, string> = {
  new: "Новые",
  lead: "Новые",
  "new lead": "Новые",
  новые: "Новые",
  qualified: "Разработка",
  qualification: "Разработка",
  discovery: "Разработка",
  meeting: "Разработка",
  разработка: "Разработка",
  proposal: "КП",
  quote: "КП",
  quotation: "КП",
  кп: "КП",
  negotiation: "Переговоры",
  negotiations: "Переговоры",
  переговоры: "Переговоры",
  won: "Закрыты",
  lost: "Закрыты",
  closed: "Закрыты",
  "closed won": "Закрыты",
  "closed lost": "Закрыты",
  закрыты: "Закрыты"
};

export function formatStageName(value?: string | null): string {
  const source = value?.trim();
  if (!source) return "Без этапа";
  return STAGE_LABELS[source.toLocaleLowerCase("ru-RU")] ?? source;
}

export function isTerminalStage(value?: string | null): boolean {
  const source = value?.trim().toLocaleLowerCase("ru-RU") ?? "";
  return ["won", "lost", "closed", "closed won", "closed lost", "закрыты", "успешно", "проиграно"].includes(source);
}
