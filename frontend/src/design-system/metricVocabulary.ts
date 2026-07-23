export const metricVocabulary = {
  aiScore: {
    label: "AI-прогноз",
    description: "Оценка модели от 0 до 100: насколько вероятен успешный исход на основе доступных сигналов."
  },
  healthScore: {
    label: "Рейтинг отношений",
    description: "Сводная оценка качества взаимодействия с компанией от 0 до 100."
  },
  probability: {
    label: "Вероятность сделки",
    description: "Ожидаемая вероятность закрытия сделки в процентах."
  },
  risk: {
    label: "Индекс риска",
    description: "Сила негативных сигналов от 0 до 100. Уровни: низкий, средний, высокий."
  }
} as const;

export type MetricVocabularyKey = keyof typeof metricVocabulary;
