<script setup lang="ts">
import { computed } from "vue";

import { branding } from "../branding";
import { hhVacancyFieldLabels } from "../hhVacancyFieldLabels";
import type { EmployerVacancy } from "../types";

const props = defineProps<{ vacancy: EmployerVacancy }>();

interface Field {
  path: string;
  label: string;
  value: string;
}

function formatDate(value: string | null): string {
  if (!value) return branding.dateMissing;
  return new Intl.DateTimeFormat("ru-RU", { dateStyle: "medium", timeStyle: "short" })
    .format(new Date(value));
}

function fieldLabel(path: string, labelPath: string): string {
  const label = hhVacancyFieldLabels[labelPath]
    ?? hhVacancyFieldLabels[labelPath.replace(/\[\]/g, "")];
  return label ? `${label}${(path.match(/\[\d+\]/g) ?? []).join("")}` : path;
}

function flatten(value: unknown, path: string, labelPath: string): Field[] {
  if (Array.isArray(value)) {
    if (!value.length) return [{ path, label: fieldLabel(path, labelPath), value: "—" }];
    return value.flatMap((item, index) => flatten(item, `${path}[${index + 1}]`, `${labelPath}[]`));
  }
  if (value !== null && typeof value === "object") {
    const entries = Object.entries(value);
    if (!entries.length) return [{ path, label: fieldLabel(path, labelPath), value: "—" }];
    return entries.flatMap(([key, item]) =>
      flatten(item, path ? `${path}.${key}` : key, labelPath ? `${labelPath}.${key}` : key),
    );
  }
  return [{
    path,
    label: fieldLabel(path, labelPath),
    value: value === null ? "—" : typeof value === "boolean" ? (value ? "Да" : "Нет") : String(value),
  }];
}

const fields = computed(() => flatten(props.vacancy.data, "", ""));

function isWebUrl(value: string): boolean {
  return /^https?:\/\//i.test(value);
}
</script>

<template>
  <section class="vacancy-card" :aria-label="`${branding.vacancyDetails}: ${vacancy.title}`">
    <h2>{{ vacancy.title }}</h2>
    <h3>{{ branding.vacancySummary }}</h3>
    <dl class="vacancy-card-fields">
      <div><dt>{{ branding.vacancyName }}:</dt><dd>{{ vacancy.title }}</dd></div>
      <div><dt>{{ branding.externalId }}:</dt><dd>{{ vacancy.external_id }}</dd></div>
      <div><dt>{{ branding.companyName }}:</dt><dd>{{ vacancy.company || "—" }}</dd></div>
      <div><dt>{{ branding.areaName }}:</dt><dd>{{ vacancy.area_name || "—" }}</dd></div>
      <div><dt>{{ branding.employmentForm }}:</dt><dd>{{ vacancy.employment_form_name || "—" }}</dd></div>
      <div><dt>{{ branding.vacancyType }}:</dt><dd>{{ vacancy.vacancy_type_name || "—" }}</dd></div>
      <div><dt>{{ branding.createdAt }}:</dt><dd>{{ formatDate(vacancy.created_at) }}</dd></div>
      <div><dt>{{ branding.publishedAt }}:</dt><dd>{{ formatDate(vacancy.published_at) }}</dd></div>
      <div><dt>{{ branding.expiresAt }}:</dt><dd>{{ formatDate(vacancy.expires_at) }}</dd></div>
      <div><dt>{{ branding.syncedAt }}:</dt><dd>{{ formatDate(vacancy.synced_at) }}</dd></div>
      <div><dt>{{ branding.hhLinkColumn }}:</dt><dd><a v-if="isWebUrl(vacancy.url)" :href="vacancy.url" target="_blank" rel="noopener noreferrer">{{ vacancy.url }}</a><span v-else>{{ vacancy.url || "—" }}</span></dd></div>
      <div><dt>{{ branding.description }}:</dt><dd>{{ vacancy.description || "—" }}</dd></div>
    </dl>

    <h3>{{ branding.hhData }}</h3>
    <dl v-if="fields.length" class="vacancy-card-fields">
      <div v-for="field in fields" :key="field.path">
        <dt>{{ field.label }}:</dt>
        <dd><a v-if="isWebUrl(field.value)" :href="field.value" target="_blank" rel="noopener noreferrer">{{ field.value }}</a><span v-else>{{ field.value }}</span></dd>
      </div>
    </dl>
    <p v-else>{{ branding.noHhData }}</p>
  </section>
</template>
