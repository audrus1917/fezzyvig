<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue";

import { api, ApiError, unauthorizedEvent } from "./api";
import { branding } from "./branding";
import type { User } from "./types";
import AuthView from "./components/AuthView.vue";
import EmployerView from "./components/EmployerView.vue";

const user = ref<User | null>(null);
const loading = ref(true);
const menuOpen = ref(false);

function navigate(path: string): void {
  if (window.location.pathname !== path) window.history.replaceState(null, "", path);
}

async function loadUser(): Promise<void> {
  try {
    user.value = await api<User>("/auth/me");
    if (window.location.pathname === "/login") navigate("/");
  } catch (error) {
    if (!(error instanceof ApiError) || error.status !== 401) throw error;
    navigate("/login");
  } finally {
    loading.value = false;
  }
}

function authenticated(value: User): void {
  user.value = value;
  navigate("/");
}

async function logout(): Promise<void> {
  await api<void>("/auth/logout", { method: "POST" });
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

function onUnauthorized(): void {
  user.value = null;
  closeMenu();
  navigate("/login");
}

onMounted(() => {
  void loadUser();
  window.addEventListener("keydown", onKeydown);
  window.addEventListener(unauthorizedEvent, onUnauthorized);
});
onUnmounted(() => {
  window.removeEventListener("keydown", onKeydown);
  window.removeEventListener(unauthorizedEvent, onUnauthorized);
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
      <a class="brand" href="/" :aria-label="branding.productName">{{ branding.productName }}</a>
      <span class="account-email">{{ [user.first_name, user.last_name].filter(Boolean).join(" ") || user.email }}</span>
    </header>

    <button v-if="menuOpen" class="menu-backdrop" type="button" :aria-label="branding.closeMenu" @click="closeMenu"></button>
    <nav id="workspace-menu" class="side-menu" :class="{ open: menuOpen }" :aria-label="branding.menuTitle" :inert="!menuOpen">
      <div class="menu-header">
        <strong>{{ branding.workspaceTitle }}</strong>
        <button class="menu-close" type="button" :aria-label="branding.closeMenu" @click="closeMenu">×</button>
      </div>
      <a href="#vacancies" @click="closeMenu">{{ branding.vacanciesTitle }}</a>
      <div class="menu-footer">
        <span>{{ [user.first_name, user.last_name].filter(Boolean).join(" ") || user.email }}</span>
        <button type="button" @click="logout">{{ branding.logout }}</button>
      </div>
    </nav>

    <main class="main-content">
      <EmployerView />
    </main>
  </div>
</template>
