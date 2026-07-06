<script setup lang="ts">
import type { CompanyWorkspace } from "../../types";

defineProps<{ workspace: CompanyWorkspace }>();
</script>

<template>
  <section class="panel">
    <h2>Contacts</h2>
    <div v-for="contact in workspace.contacts" :key="contact.id" class="list-row">
      <span>{{ contact.name }}</span>
      <small>{{ contact.phone ?? contact.email ?? "no contact" }}</small>
    </div>
    <p v-if="!workspace.contacts.length" class="empty">No contacts yet</p>
  </section>
</template>

