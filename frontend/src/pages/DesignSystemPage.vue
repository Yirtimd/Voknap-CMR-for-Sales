<script setup lang="ts">
import { ref } from "vue";

import {
  UiAlert,
  UiBadge,
  UiButton,
  UiCard,
  UiDensityToggle,
  UiDrawer,
  UiEmptyState,
  UiInput,
  UiModal,
  UiSelect,
  UiSkeleton,
  UiSkeletonGroup,
  UiSparkline,
  UiTable,
  UiTabs,
  UiThemeToggle
} from "../components/ui";
import { useDensity } from "../design-system/density";

withDefaults(defineProps<{ embedded?: boolean }>(), { embedded: false });

const { density } = useDensity();
const activeTab = ref("overview");
const inputValue = ref("");
const selectValue = ref<string | number | null>("");
const modalOpen = ref(false);
const drawerOpen = ref(false);
const tabItems = [
  { value: "overview", label: "Обзор", count: 12 },
  { value: "states", label: "Состояния", count: 4 },
  { value: "data", label: "Данные" }
];
const selectOptions = [
  { value: "new", label: "Новый" },
  { value: "qualified", label: "Квалифицирован" },
  { value: "converted", label: "Конвертирован" }
];
const colors = [
  ["Primary", "var(--color-primary)"],
  ["AI", "var(--color-ai)"],
  ["Success", "var(--color-success)"],
  ["Warning", "var(--color-warning)"],
  ["Danger", "var(--color-danger)"],
  ["Text", "var(--color-text-primary)"],
  ["Muted", "var(--color-text-muted)"],
  ["Border", "var(--color-border)"]
];
</script>

<template>
  <component :is="embedded ? 'div' : 'main'" class="ds-page" :class="[{ embedded }, `density-${density}`]" :data-density="density" data-testid="design-system-page">
    <header v-if="!embedded" class="ds-hero">
      <div><p class="eyebrow">Voknap Design System</p><h1>Компоненты и визуальные контракты</h1><p>Живая проверочная страница tokens, состояний, плотности и responsive-поведения.</p></div>
      <div><UiThemeToggle /><UiDensityToggle /><RouterLink class="ds-back" to="/home">Вернуться в CRM</RouterLink></div>
    </header>
    <header v-else class="ds-embedded-header">
      <div><p class="eyebrow">Voknap Design System</p><h2>Компоненты и визуальные контракты</h2><p>Tokens, состояния, плотность и responsive-поведение интерфейса.</p></div>
      <div class="ds-preferences"><UiThemeToggle /><UiDensityToggle /></div>
    </header>

    <UiTabs v-model="activeTab" :items="tabItems" label="Разделы библиотеки" />

    <section class="ds-section">
      <header><p class="eyebrow">Foundations</p><h2>Цвета и радиусы</h2></header>
      <div class="ds-colors">
        <article v-for="[label, color] in colors" :key="label"><i :style="{ background: color }"></i><strong>{{ label }}</strong><code>{{ color }}</code></article>
      </div>
      <div class="ds-radii">
        <span v-for="radius in ['xs','sm','control','card','panel','modal','pill']" :key="radius" :style="{ borderRadius: `var(--radius-${radius})` }">{{ radius }}</span>
      </div>
    </section>

    <section class="ds-section">
      <header><p class="eyebrow">Actions</p><h2>Buttons и badges</h2></header>
      <div class="ds-row">
        <UiButton icon="plus">Основное действие</UiButton>
        <UiButton variant="secondary" icon="filter">Фильтр</UiButton>
        <UiButton variant="ghost">Тихое действие</UiButton>
        <UiButton variant="ai" icon="sparkles">AI-действие</UiButton>
        <UiButton variant="danger">Удалить</UiButton>
        <UiButton loading>Загрузка</UiButton>
        <UiButton disabled>Недоступно</UiButton>
      </div>
      <div class="ds-row">
        <UiBadge tone="neutral">Черновик</UiBadge><UiBadge tone="info">В работе</UiBadge><UiBadge tone="success">Выполнено</UiBadge><UiBadge tone="warning">Внимание</UiBadge><UiBadge tone="danger">Риск</UiBadge><UiBadge tone="ai">AI-прогноз</UiBadge>
      </div>
    </section>

    <section class="ds-grid">
      <UiCard>
        <template #header><div><p class="eyebrow">Forms</p><h2>Поля</h2></div></template>
        <div class="ds-form">
          <UiInput v-model="inputValue" label="Название" placeholder="Введите значение" hint="Подсказка остаётся рядом с полем" />
          <UiSelect v-model="selectValue" label="Статус" :options="selectOptions" placeholder="Выберите статус" />
          <UiInput model-value="Некорректное значение" label="Поле с ошибкой" error="Проверьте формат" />
        </div>
      </UiCard>
      <UiCard interactive>
        <template #header><div><p class="eyebrow">Overlay</p><h2>Modal и drawer</h2></div></template>
        <p>Проверка focus, Escape, backdrop и fullscreen mobile.</p>
        <template #footer><UiButton variant="secondary" @click="modalOpen = true">Modal</UiButton><UiButton @click="drawerOpen = true">Drawer</UiButton></template>
      </UiCard>
    </section>

    <section class="ds-section">
      <header><p class="eyebrow">Feedback</p><h2>Alerts и states</h2></header>
      <div class="ds-alerts"><UiAlert tone="info" title="Информация">Контекст для принятия решения.</UiAlert><UiAlert tone="success" title="Готово">Изменения сохранены.</UiAlert><UiAlert tone="warning" title="Нужно внимание">Проверьте обязательные поля.</UiAlert><UiAlert tone="danger" title="Ошибка">Данные сохранены, повторите действие.</UiAlert></div>
      <div class="ds-grid">
        <UiEmptyState title="Данных пока нет" description="Добавьте первую запись, чтобы начать работу." icon="file"><template #actions><UiButton icon="plus">Добавить</UiButton></template></UiEmptyState>
        <UiCard><template #header><h3>Skeleton library</h3></template><UiSkeletonGroup :rows="3" avatar /></UiCard>
      </div>
    </section>

    <section class="ds-grid">
      <UiCard>
        <template #header><div><p class="eyebrow">Charts</p><h2>Sparkline</h2></div></template>
        <UiSparkline :values="[18,26,22,39,42,57,51,68]" label="Взвешенный прогноз за 8 периодов" />
      </UiCard>
      <UiCard>
        <template #header><div><p class="eyebrow">Loading</p><h2>Primitive shapes</h2></div></template>
        <div class="ds-shapes"><UiSkeleton shape="circle" width="52px" height="52px" /><div><UiSkeleton width="55%" height="16px" /><UiSkeleton width="90%" height="12px" /><UiSkeleton width="72%" height="12px" /></div></div>
      </UiCard>
    </section>

    <section class="ds-section">
      <header><p class="eyebrow">Data display</p><h2>Таблица</h2></header>
      <UiTable label="Пример сделок">
        <thead><tr><th>Сделка</th><th>Компания</th><th>Статус</th><th>Сумма</th></tr></thead>
        <tbody><tr><td>Внедрение CRM</td><td>Альфа</td><td><UiBadge tone="info">Переговоры</UiBadge></td><td>1 250 000 ₽</td></tr><tr><td>Расширение лицензий</td><td>Вектор</td><td><UiBadge tone="warning">Согласование</UiBadge></td><td>480 000 ₽</td></tr></tbody>
      </UiTable>
    </section>

    <UiModal :open="modalOpen" title="Подтверждение действия" description="Короткое фокусное взаимодействие." @close="modalOpen = false"><p>Modal использует общий overlay contract.</p><template #footer><UiButton variant="secondary" @click="modalOpen = false">Отмена</UiButton><UiButton @click="modalOpen = false">Подтвердить</UiButton></template></UiModal>
    <UiDrawer :open="drawerOpen" title="Карточка сущности" description="Контекст остаётся рядом со списком." @close="drawerOpen = false"><UiSkeletonGroup :rows="5" /></UiDrawer>
  </component>
</template>

<style scoped>
.ds-page{width:min(1440px,100%);display:grid;gap:28px;margin:0 auto;padding:32px clamp(16px,4vw,56px) 64px;color:var(--color-text-primary);font-family:var(--font-family-sans)}.ds-page.embedded{width:100%;gap:16px;padding:0}.ds-hero,.ds-embedded-header{display:flex;align-items:flex-end;justify-content:space-between;gap:28px}.ds-hero h1{max-width:780px;margin:6px 0 10px;font-size:clamp(30px,4vw,52px);line-height:1.04;letter-spacing:-.035em}.ds-hero p:last-child,.ds-embedded-header p:last-child{max-width:680px;margin:0;color:var(--color-text-muted)}.ds-embedded-header h2{margin:4px 0 6px;font-size:20px}.ds-hero>div:last-child,.ds-preferences{display:grid;gap:10px}.ds-back{color:var(--color-primary);font-size:var(--font-size-meta);text-align:center}.ds-section{display:grid;gap:16px;border:1px solid var(--color-border);border-radius:var(--radius-panel);padding:var(--density-card-padding,var(--space-6));background:var(--color-surface)}.ds-section header h2,.ds-section header p,.ds-grid h2,.ds-grid p{margin:0}.ds-row{display:flex;align-items:center;flex-wrap:wrap;gap:10px}.ds-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}.ds-colors{display:grid;grid-template-columns:repeat(4,minmax(120px,1fr));gap:10px}.ds-colors article{display:grid;gap:5px}.ds-colors i{height:56px;border:1px solid var(--color-border);border-radius:var(--radius-control)}.ds-colors code{overflow:hidden;color:var(--color-text-muted);font-size:var(--font-size-caption);text-overflow:ellipsis}.ds-radii{display:flex;flex-wrap:wrap;gap:10px}.ds-radii span{display:grid;place-items:center;width:90px;height:56px;border:1px solid var(--color-border-strong);background:var(--color-surface-subtle);font-size:var(--font-size-meta)}.ds-form,.ds-alerts{display:grid;gap:12px}.ds-alerts{grid-template-columns:repeat(2,1fr)}.ds-shapes{display:grid;grid-template-columns:auto 1fr;align-items:center;gap:14px}.ds-shapes>div{display:grid;gap:9px}
@media(max-width:760px){.ds-page{gap:20px;padding:22px 14px 48px}.ds-page.embedded{padding:0}.ds-hero,.ds-embedded-header{align-items:stretch;flex-direction:column}.ds-hero>div:last-child{align-self:stretch}.ds-grid,.ds-alerts{grid-template-columns:1fr}.ds-colors{grid-template-columns:repeat(2,1fr)}}
</style>
