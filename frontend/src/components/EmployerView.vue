<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { api } from "../api";
import { branding } from "../branding";
import type { EmployerVacancy } from "../types";
import StatusMessage from "./StatusMessage.vue";
import VacancyCard from "./VacancyCard.vue";

const vacancies = ref<EmployerVacancy[]>([]);
const titleFilter = ref("");
const filteredVacancies = computed(() => {
  const query = titleFilter.value.trim().toLocaleLowerCase("ru-RU");
  return query
    ? vacancies.value.filter((vacancy) => vacancy.title.toLocaleLowerCase("ru-RU").includes(query))
    : vacancies.value;
});
const loading = ref(false);
const statusMessage = ref("");
const vacancyId = /^\/vacancies\/(\d+)\/?$/.exec(window.location.pathname)?.[1];
const selectedVacancy = computed(() =>
  vacancies.value.find((vacancy) => String(vacancy.id) === vacancyId),
);

function formatDate(value: string | null): string {
  if (!value) return branding.dateMissing;
  return new Intl.DateTimeFormat("ru-RU", { dateStyle: "medium" }).format(new Date(value));
}

async function load(): Promise<void> {
  loading.value = true;
  statusMessage.value = "";
  try {
    vacancies.value = await api<EmployerVacancy[]>("/employer/vacancies");
  } catch (error) {
    statusMessage.value = error instanceof Error ? error.message : branding.vacanciesError;
  } finally {
    loading.value = false;
  }
}

onMounted(load);
defineExpose({ load });
</script>

<template>
  <template v-if="vacancyId">
    <a class="back-link" href="/">{{ branding.backToVacancies }}</a>
    <div v-if="loading" class="loading-panel">{{ branding.vacanciesLoading }}</div>
    <StatusMessage v-else-if="statusMessage" :message="statusMessage" error />
    <VacancyCard v-else-if="selectedVacancy" :vacancy="selectedVacancy" />
    <p v-else>{{ branding.vacancyNotFound }}</p>
  </template>
  <template v-else>
  <StatusMessage v-if="statusMessage" class="workspace-status" :message="statusMessage" error />

  <section id="vacancies" class="workspace" :aria-label="branding.vacanciesTitle">
    <div class="panel-heading">
      <div>
        <h1>{{ branding.vacanciesTitle }}</h1>
        <p>{{ branding.vacanciesSubtitle }}</p>
      </div>
      <span class="panel-count">{{ branding.totalLabel }}: {{ filteredVacancies.length }}</span>
    </div>
    <details class="vacancy-filters">
      <summary>
        {{ branding.filtersTitle }}
        <span v-if="titleFilter.trim()" class="filter-current">{{ titleFilter.trim() }}</span>
      </summary>
      <div class="filter-fields">
        <label for="vacancy-title-filter">{{ branding.titleFilterLabel }}</label>
        <input
          id="vacancy-title-filter"
          v-model="titleFilter"
          type="search"
          :placeholder="branding.titleFilterPlaceholder"
        />
        <button
          class="filter-reset"
          type="button"
          :disabled="!titleFilter"
          @click="titleFilter = ''"
        >
          {{ branding.resetFilters }}
        </button>
      </div>
    </details>

    <div v-if="loading && !vacancies.length" class="loading-panel">{{ branding.vacanciesLoading }}</div>
    <div v-else class="vacancies-table-wrap">
      <table class="vacancies-table">
        <thead>
          <tr>
            <th scope="col">{{ branding.externalId }}</th>
            <th scope="col">{{ branding.vacancyName }}</th>
            <th scope="col">{{ branding.companyName }}</th>
            <th scope="col">{{ branding.publishedAt }}</th>
            <th scope="col">{{ branding.syncedAt }}</th>
            <th scope="col">{{ branding.hhLinkColumn }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="vacancy in filteredVacancies" :key="vacancy.id">
            <td class="vacancy-id">{{ vacancy.external_id }}</td>
            <td class="vacancy-title"><a :href="`/vacancies/${vacancy.id}`">{{ vacancy.title }}</a></td>
            <td>{{ vacancy.company || "—" }}</td>
            <td>{{ formatDate(vacancy.published_at) }}</td>
            <td>{{ formatDate(vacancy.synced_at) }}</td>
            <td>
              <a
                :href="vacancy.url"
                :aria-label="`${branding.openVacancyLabel}: ${vacancy.title}`"
                target="_blank"
                rel="noopener noreferrer"
              >
                {{ branding.openVacancy }}
              </a>
            </td>
          </tr>
          <tr v-if="!filteredVacancies.length">
            <td colspan="6" class="vacancies-empty">
              <strong>{{ titleFilter.trim() ? branding.filterEmpty : branding.vacanciesEmptyTitle }}</strong>
              <span v-if="!titleFilter.trim()">{{ branding.vacanciesEmptyDescription }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
  </template>
</template>
