<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue";

import { api, ApiError, unauthorizedEvent } from "./api";
import { branding } from "./branding";
import type { User } from "./types";
import AuthView from "./components/AuthView.vue";
import EmployerView from "./components/EmployerView.vue";
import StatusMessage from "./components/StatusMessage.vue";

interface SyncJob {
  task_id: string;
  status: string;
  synced: number | null;
}

const user = ref<User | null>(null);
const loading = ref(true);
const menuOpen = ref(false);
const mobileMenuQuery = window.matchMedia("(max-width: 900px)");
const mobileMenu = ref(mobileMenuQuery.matches);
const topbarTitle = /^\/vacancies\/\d+\/?$/.test(window.location.pathname)
  ? branding.vacancyDetails : branding.vacanciesTitle;
const employerView = ref<InstanceType<typeof EmployerView> | null>(null);
const syncing = ref(false);
const syncMessage = ref("");
const syncError = ref(false);
let syncRun = 0;
let loginReturnPath = "/";

function navigate(path: string): void {
  if (window.location.pathname !== path) window.history.replaceState(null, "", path);
}

async function loadUser(): Promise<void> {
  try {
    user.value = await api<User>("/auth/me");
    if (window.location.pathname === "/login") navigate("/");
  } catch (error) {
    if (!(error instanceof ApiError) || error.status !== 401) throw error;
    if (/^\/vacancies\/\d+\/?$/.test(window.location.pathname)) {
      loginReturnPath = window.location.pathname;
    }
    navigate("/login");
  } finally {
    loading.value = false;
  }
}

function authenticated(value: User): void {
  user.value = value;
  navigate(loginReturnPath);
  loginReturnPath = "/";
}

function resetSync(): void {
  syncRun++;
  syncing.value = false;
  syncMessage.value = "";
  syncError.value = false;
}

async function logout(): Promise<void> {
  await api<void>("/auth/logout", { method: "POST" });
  resetSync();
  loginReturnPath = "/";
  user.value = null;
  menuOpen.value = false;
  navigate("/login");
}

function closeMenu(): void {
  menuOpen.value = false;
}

function onKeydown(event: KeyboardEvent): void {
  if (event.key === "Escape") closeMenu();
}

function onMenuBreakpoint(event: MediaQueryListEvent): void {
  mobileMenu.value = event.matches;
  closeMenu();
}

function onUnauthorized(): void {
  if (/^\/vacancies\/\d+\/?$/.test(window.location.pathname)) {
    loginReturnPath = window.location.pathname;
  }
  resetSync();
  user.value = null;
  closeMenu();
  navigate("/login");
}

async function synchronize(): Promise<void> {
  if (syncing.value) return;
  const run = ++syncRun;
  syncing.value = true;
  syncError.value = false;
  syncMessage.value = branding.syncQueued;
  closeMenu();

  try {
    let job = await api<SyncJob>("/employer/sync", { method: "POST" });
    while (run === syncRun && (job.status === "queued" || job.status === "running")) {
      syncMessage.value = job.status === "running" ? branding.syncRunning : branding.syncQueued;
      await new Promise((resolve) => setTimeout(resolve, 2000));
      if (run !== syncRun) return;
      job = await api<SyncJob>(`/employer/sync/${job.task_id}`);
    }
    if (run !== syncRun) return;
    if (job.status !== "succeeded") throw new Error(branding.syncFailed);
    await employerView.value?.load();
    syncMessage.value = `${branding.syncComplete}: ${job.synced ?? 0}`;
  } catch (error) {
    if (run !== syncRun) return;
    syncError.value = true;
    syncMessage.value = error instanceof Error ? error.message : branding.syncFailed;
  } finally {
    if (run === syncRun) syncing.value = false;
  }
}

onMounted(() => {
  void loadUser();
  window.addEventListener("keydown", onKeydown);
  window.addEventListener(unauthorizedEvent, onUnauthorized);
  mobileMenuQuery.addEventListener("change", onMenuBreakpoint);
});
onUnmounted(() => {
  syncRun++;
  window.removeEventListener("keydown", onKeydown);
  window.removeEventListener(unauthorizedEvent, onUnauthorized);
  mobileMenuQuery.removeEventListener("change", onMenuBreakpoint);
});
</script>

<template>
  <div v-if="loading" class="loading-panel app-loading">{{ branding.loadingWorkspace }}</div>
  <AuthView v-else-if="!user" @authenticated="authenticated" />
  <div v-else class="app-shell">
    <header class="topbar">
      <button
        class="menu-button"
        type="button"
        :aria-label="branding.openMenu"
        aria-controls="workspace-menu"
        :aria-expanded="menuOpen"
        @click="menuOpen = true"
      ><span></span><span></span><span></span></button>
      <strong class="topbar-title">{{ topbarTitle }}</strong>
      <span class="account-email">{{ [user.first_name, user.last_name].filter(Boolean).join(" ") || user.email }}</span>
    </header>

    <button v-if="menuOpen" class="menu-backdrop" type="button" :aria-label="branding.closeMenu" @click="closeMenu"></button>
    <nav id="workspace-menu" class="side-menu" :class="{ open: menuOpen }" :aria-label="branding.menuTitle" :inert="mobileMenu && !menuOpen">
      <div class="menu-header">
        <a class="sidebar-brand" href="/">{{ branding.productName }}</a>
        <button class="menu-close" type="button" :aria-label="branding.closeMenu" @click="closeMenu">×</button>
      </div>
      <span class="menu-section-label">{{ branding.menuTitle }}</span>
      <a class="menu-link active" href="/#vacancies" @click="closeMenu"><span class="nav-icon" aria-hidden="true">▤</span>{{ branding.vacanciesTitle }}</a>
      <button class="menu-action" type="button" :disabled="syncing" @click="synchronize">
        <span class="nav-icon" aria-hidden="true">↻</span>{{ syncing ? branding.syncRunning : branding.synchronize }}
      </button>
      <div class="menu-footer">
        <span>{{ [user.first_name, user.last_name].filter(Boolean).join(" ") || user.email }}</span>
        <button type="button" @click="logout">{{ branding.logout }}</button>
      </div>
    </nav>

    <main class="main-content">
      <StatusMessage v-if="syncMessage" class="sync-status" :message="syncMessage" :error="syncError" />
      <EmployerView ref="employerView" />
    </main>
  </div>
</template>
