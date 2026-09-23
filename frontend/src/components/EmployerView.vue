<script setup lang="ts">
import { onMounted, ref } from "vue";

import { api } from "../api";
import { branding } from "../branding";
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
  if (!value) return branding.dateMissing;
  return new Intl.DateTimeFormat("ru-RU", { dateStyle: "medium" }).format(new Date(value));
}

async function load(): Promise<void> {
  loading.value = true;
  statusError.value = false;
  try {
    vacancies.value = await api<EmployerVacancy[]>("/employer/vacancies");
  } catch (error) {
    statusError.value = true;
    statusMessage.value = error instanceof Error ? error.message : branding.vacanciesError;
  } finally {
    loading.value = false;
  }
}

async function sync(): Promise<void> {
  syncing.value = true;
  statusError.value = false;
  statusMessage.value = branding.syncingMessage;
  try {
    const result = await api<EmployerSyncResult>("/employer/sync", { method: "POST" });
    statusMessage.value = `${branding.syncedMessage}: ${result.synced}`;
    await load();
  } catch (error) {
    statusError.value = true;
    statusMessage.value = error instanceof Error ? error.message : branding.syncError;
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
  <div class="page-heading">
    <p class="eyebrow">{{ branding.workspaceTitle }}</p>
    <h1>{{ branding.vacanciesTitle }}</h1>
  </div>

  <section id="connection" class="connect-card">
    <h2>{{ branding.connectionTitle }}</h2>
    <p>{{ branding.connectionDescription }}</p>
    <div class="connect-actions">
      <button class="secondary-button" type="button" @click="connectHH">{{ branding.connectButton }}</button>
      <button class="primary-button" type="button" :disabled="syncing" @click="sync">
        {{ syncing ? branding.syncing : branding.syncButton }}
      </button>
    </div>
    <StatusMessage :message="statusMessage" :error="statusError" />
  </section>

  <section id="vacancies" class="workspace">
    <div class="section-heading">
      <div>
        <h2>{{ branding.vacanciesTitle }}</h2>
      </div>
      <span class="count-badge">{{ vacancies.length }}</span>
    </div>

    <div v-if="loading && !vacancies.length" class="loading-panel">{{ branding.vacanciesLoading }}</div>
    <div v-else-if="vacancies.length" class="card-grid">
      <article v-for="vacancy in vacancies" :key="vacancy.id" class="vacancy-card">
        <p class="company">{{ vacancy.company }}</p>
        <h3>{{ vacancy.title }}</h3>
        <div class="meta">
          <span class="tag">{{ branding.publishedAt }} {{ formatDate(vacancy.published_at) }}</span>
          <span class="tag good">{{ branding.syncedAt }} {{ formatDate(vacancy.synced_at) }}</span>
        </div>
        <p class="summary">{{ descriptionPreview(vacancy.description) || branding.descriptionMissing }}</p>
        <a :href="vacancy.url" target="_blank" rel="noopener noreferrer">{{ branding.openVacancy }}</a>
      </article>
    </div>
    <EmptyState
      v-else
      :title="branding.vacanciesEmptyTitle"
      :description="branding.vacanciesEmptyDescription"
    />
  </section>
</template>
