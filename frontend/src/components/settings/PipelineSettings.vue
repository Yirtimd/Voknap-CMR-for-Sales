<script setup lang="ts">
import { computed, reactive, ref } from "vue";

import type { Pipeline } from "../../types";
import { crmStore } from "../../stores/crm";

type StageDraft = {
  id?: string;
  name: string;
  code: string;
  probability: number;
  stage_type: "open" | "won" | "lost";
  required_fields: string;
};

const editingId = ref("");
const form = reactive({
  name: "",
  description: "",
  is_active: true,
  is_default: false,
  stages: [] as StageDraft[]
});
const editing = computed(() => crmStore.pipelines.value.find((item) => item.id === editingId.value));

function emptyStage(index: number): StageDraft {
  return { name: "", code: `stage_${index + 1}`, probability: 0, stage_type: "open", required_fields: "" };
}

function reset() {
  editingId.value = "";
  form.name = "";
  form.description = "";
  form.is_active = true;
  form.is_default = false;
  form.stages = [
    { ...emptyStage(0), name: "Новый", probability: 10 },
    { ...emptyStage(1), name: "В работе", probability: 40 },
    { ...emptyStage(2), name: "КП", probability: 70 },
    { ...emptyStage(3), name: "Успешно", probability: 100, stage_type: "won" }
  ];
}

function edit(pipeline: Pipeline) {
  editingId.value = pipeline.id;
  form.name = pipeline.name;
  form.description = pipeline.description ?? "";
  form.is_active = pipeline.is_active;
  form.is_default = pipeline.is_default;
  form.stages = pipeline.stages.filter((stage) => stage.is_active).map((stage) => ({
    id: stage.id,
    name: stage.name,
    code: stage.code,
    probability: stage.probability,
    stage_type: stage.stage_type,
    required_fields: stage.required_fields.join(", ")
  }));
}

async function save() {
  await crmStore.savePipeline({
    id: editing.value?.id,
    version: editing.value?.version,
    name: form.name,
    description: form.description || null,
    is_active: form.is_active,
    is_default: form.is_default,
    stages: form.stages.map((stage) => ({
      id: stage.id,
      name: stage.name,
      code: stage.code,
      probability: stage.probability,
      stage_type: stage.stage_type,
      required_fields: stage.required_fields.split(",").map((item) => item.trim()).filter(Boolean)
    }))
  });
  reset();
}

reset();
</script>

<template>
  <section class="pipeline-settings">
    <form class="panel pipeline-editor" @submit.prevent="save">
      <header><div><h2>{{ editing ? "Редактирование воронки" : "Новая воронка" }}</h2><p>Этапы управляют вероятностью и статусом сделки.</p></div><button v-if="editing" class="secondary" type="button" @click="reset">Отмена</button></header>
      <label>Название<input v-model="form.name" required minlength="2" /></label>
      <label>Описание<textarea v-model="form.description" rows="2"></textarea></label>
      <div class="pipeline-flags"><label><input v-model="form.is_default" type="checkbox" /> По умолчанию</label><label><input v-model="form.is_active" type="checkbox" /> Активна</label></div>
      <fieldset><legend>Этапы</legend>
        <article v-for="(stage, index) in form.stages" :key="stage.id || index" class="stage-row">
          <input v-model="stage.name" required placeholder="Название" />
          <input v-model="stage.code" required pattern="[a-z0-9_]+" placeholder="code" />
          <input v-model.number="stage.probability" type="number" min="0" max="100" required aria-label="Вероятность" />
          <select v-model="stage.stage_type" aria-label="Тип этапа"><option value="open">Открытый</option><option value="won">Успех</option><option value="lost">Проигрыш</option></select>
          <input v-model="stage.required_fields" placeholder="Обязательные поля через запятую" />
          <button class="danger-quiet" type="button" :disabled="form.stages.length === 1" @click="form.stages.splice(index, 1)">Удалить</button>
        </article>
        <button class="secondary" type="button" @click="form.stages.push(emptyStage(form.stages.length))">Добавить этап</button>
      </fieldset>
      <button type="submit" :disabled="crmStore.isLoading.value">{{ editing ? "Сохранить изменения" : "Создать воронку" }}</button>
    </form>
    <section class="panel pipeline-list"><h2>Воронки продаж</h2>
      <article v-for="pipeline in crmStore.pipelines.value" :key="pipeline.id">
        <div><strong>{{ pipeline.name }}</strong><small>{{ pipeline.stages.filter((stage) => stage.is_active).length }} этапов · v{{ pipeline.version }}</small></div>
        <span>{{ pipeline.is_default ? "По умолчанию" : pipeline.is_active ? "Активна" : "Отключена" }}</span>
        <button type="button" @click="edit(pipeline)">Настроить</button>
      </article>
      <p v-if="!crmStore.pipelines.value.length" class="empty">Воронок пока нет.</p>
    </section>
  </section>
</template>

<style scoped>
.pipeline-settings{display:grid;grid-template-columns:minmax(360px,1fr) minmax(280px,.7fr);gap:14px;align-items:start}.pipeline-editor,.pipeline-list{display:grid;gap:14px;padding:20px}.pipeline-editor header,.pipeline-list article{display:flex;align-items:flex-start;justify-content:space-between;gap:12px}.pipeline-editor h2,.pipeline-list h2,.pipeline-editor p{margin:0}.pipeline-editor p,.pipeline-list small{color:var(--color-text-muted)}.pipeline-flags{display:flex;gap:18px}.pipeline-flags label{display:flex;align-items:center;gap:8px}.pipeline-editor fieldset{display:grid;gap:9px;border:1px solid var(--color-border);border-radius:var(--radius-control);padding:12px}.stage-row{display:grid;grid-template-columns:1fr 120px 80px 110px 1.2fr auto;gap:7px}.pipeline-list article{align-items:center;border-top:1px solid var(--color-border-subtle);padding-top:12px}.pipeline-list article div{display:grid;gap:3px}.pipeline-list article span{font-size:12px}@media(max-width:1050px){.pipeline-settings{grid-template-columns:1fr}.stage-row{grid-template-columns:1fr 1fr 90px 120px}.stage-row input:nth-of-type(4){grid-column:1/-1}}@media(max-width:640px){.stage-row{grid-template-columns:1fr}.stage-row>*{grid-column:1!important}.pipeline-list article{flex-wrap:wrap}.pipeline-list article div{flex:1 0 100%}}
</style>
