<script setup lang="ts">
import { onMounted, ref } from "vue";

import { api, ApiError } from "./api";
import type { User } from "./types";
import AuthView from "./components/AuthView.vue";
import EmployerView from "./components/EmployerView.vue";

const user = ref<User | null>(null);
const loading = ref(true);

async function loadUser(): Promise<void> {
  try {
    user.value = await api<User>("/auth/me");
  } catch (error) {
    if (!(error instanceof ApiError) || error.status !== 401) throw error;
  } finally {
    loading.value = false;
  }
}

async function logout(): Promise<void> {
  await api<void>("/auth/logout", { method: "POST" });
  user.value = null;
}

onMounted(loadUser);
</script>

<template>
  <header class="topbar">
    <a class="brand" href="/" aria-label="Fezzyvig">
      <span class="brand-mark">F</span>
      <span>Fezzyvig</span>
    </a>
    <p>Рабочее пространство работодателя</p>
    <div class="account-actions">
      <span v-if="user">{{ [user.first_name, user.last_name].filter(Boolean).join(" ") || user.email }}</span>
      <button v-if="user" type="button" @click="logout">Выйти</button>
      <a v-else class="api-link" href="/docs">API ↗</a>
    </div>
  </header>
  <main>
    <div v-if="loading" class="loading-panel app-loading">Загружаем рабочее пространство…</div>
    <EmployerView v-else-if="user" />
    <AuthView v-else @authenticated="user = $event" />
  </main>
</template>
