<script setup lang="ts">
import { onMounted, ref } from "vue";

import { api } from "../api";
import type { EmployerSyncResult, EmployerVacancy } from "../types";
import EmptyState from "./EmptyState.vue";
import StatusMessage from "./StatusMessage.vue";

const vacancies = ref<EmployerVacancy[]>([]);
const loading = ref(false);
const syncing = ref(false);
const statusMessage = ref("");
const statusError = ref(false);

function descriptionPreview(description: string): string {
  const normalized = description.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
  return normalized.length > 220 ? `${normalized.slice(0, 217)}…` : normalized;
}

function formatDate(value: string | null): string {
  if (!value) return "Дата не указана";
  return new Intl.DateTimeFormat("ru-RU", { dateStyle: "medium" }).format(new Date(value));
}

async function load(): Promise<void> {
  loading.value = true;
  statusError.value = false;
  try {
    vacancies.value = await api<EmployerVacancy[]>("/employer/vacancies");
  } catch (error) {
    statusError.value = true;
    statusMessage.value = error instanceof Error ? error.message : "Не удалось загрузить вакансии";
  } finally {
    loading.value = false;
  }
}

async function sync(): Promise<void> {
  syncing.value = true;
  statusError.value = false;
  statusMessage.value = "Синхронизируем вакансии с HeadHunter…";
  try {
    const result = await api<EmployerSyncResult>("/employer/sync", { method: "POST" });
    statusMessage.value = `Синхронизировано вакансий: ${result.synced}`;
    await load();
  } catch (error) {
    statusError.value = true;
    statusMessage.value = error instanceof Error ? error.message : "Не удалось синхронизировать вакансии";
  } finally {
    syncing.value = false;
  }
}

function connectHH(): void {
  window.open("/employer/oauth/authorize", "fezzyvig-hh-oauth", "popup,width=720,height=760");
}

onMounted(load);
</script>

<template>
  <section class="hero">
    <div>
      <p class="eyebrow">TALENT WORKSPACE</p>
      <h1>Найти людей,<br><em>которые подходят.</em></h1>
      <p class="hero-copy">
        Подключите кабинет работодателя и синхронизируйте опубликованные вакансии
        в отдельном рабочем пространстве.
      </p>
    </div>
    <div class="connect-card">
      <p class="company">HEADHUNTER FOR EMPLOYERS</p>
      <h2>Подключение кабинета</h2>
      <p>OAuth-токен хранится на сервере отдельно для вашего аккаунта и не передаётся во frontend.</p>
      <div class="connect-actions">
        <button class="secondary-button" type="button" @click="connectHH">Подключить HH ↗</button>
        <button class="primary-button" type="button" :disabled="syncing" @click="sync">
          {{ syncing ? "Синхронизация…" : "Синхронизировать" }}
        </button>
      </div>
      <StatusMessage :message="statusMessage" :error="statusError" />
    </div>
  </section>

  <section class="workspace">
    <div class="section-heading">
      <div>
        <p class="eyebrow">EMPLOYER VACANCIES</p>
        <h2>Мои вакансии</h2>
      </div>
      <span class="count-badge">{{ vacancies.length }}</span>
    </div>

    <div v-if="loading && !vacancies.length" class="loading-panel">Загружаем вакансии…</div>
    <div v-else-if="vacancies.length" class="card-grid">
      <article v-for="vacancy in vacancies" :key="vacancy.id" class="vacancy-card">
        <p class="company">{{ vacancy.company }}</p>
        <h3>{{ vacancy.title }}</h3>
        <div class="meta">
          <span class="tag">Опубликована {{ formatDate(vacancy.published_at) }}</span>
          <span class="tag good">Синхронизирована {{ formatDate(vacancy.synced_at) }}</span>
        </div>
        <p class="summary">{{ descriptionPreview(vacancy.description) || "Описание отсутствует." }}</p>
        <a :href="vacancy.url" target="_blank" rel="noopener noreferrer">Открыть на HH ↗</a>
      </article>
    </div>
    <EmptyState
      v-else
      title="Вакансии не синхронизированы"
      description="Подключите кабинет HeadHunter и запустите синхронизацию."
    />
  </section>
</template>
