<script setup lang="ts">
import { useRouter } from "vue-router";

import voknapLogo from "../assets/voknap-logo.png";
import { crmStore } from "../stores/crm";

const router = useRouter();

async function registerCompany() {
  await crmStore.registerCompany();
  if (crmStore.isAuthed.value) void router.push("/dashboard");
}

async function login() {
  await crmStore.login();
  if (crmStore.isAuthed.value) void router.push("/dashboard");
}
</script>

<template>
  <main class="login-shell">
    <section class="login-header">
      <img class="login-logo" :src="voknapLogo" alt="Voknap" />
      <h1>Вход в CRM</h1>
    </section>

    <div v-if="crmStore.error.value" class="alert error">{{ crmStore.error.value }}</div>
    <div v-if="crmStore.ok.value" class="alert success">{{ crmStore.ok.value }}</div>

    <section class="auth-layout">
      <form class="panel" @submit.prevent="registerCompany">
        <h2>Регистрация компании</h2>
        <label>Компания<input v-model="crmStore.registerForm.value.company_name" /></label>
        <label>Slug<input v-model="crmStore.registerForm.value.company_slug" /></label>
        <label>Email владельца<input v-model="crmStore.registerForm.value.owner_email" /></label>
        <label>Имя владельца<input v-model="crmStore.registerForm.value.owner_full_name" /></label>
        <label>Пароль<input v-model="crmStore.registerForm.value.owner_password" type="password" /></label>
        <button type="submit" :disabled="crmStore.isLoading.value">Создать компанию</button>
      </form>

      <form class="panel" @submit.prevent="login">
        <h2>Вход</h2>
        <label>Email<input v-model="crmStore.loginForm.value.email" /></label>
        <label>Пароль<input v-model="crmStore.loginForm.value.password" type="password" /></label>
        <button type="submit" :disabled="crmStore.isLoading.value">Войти</button>
      </form>
    </section>
  </main>
</template>
