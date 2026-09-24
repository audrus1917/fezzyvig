<script setup lang="ts">
import { ref } from "vue";

import { api } from "../api";
import { branding } from "../branding";
import type { User } from "../types";
import StatusMessage from "./StatusMessage.vue";

const emit = defineEmits<{ authenticated: [user: User] }>();

const email = ref("");
const password = ref("");
const submitting = ref(false);
const message = ref("");

async function submit(): Promise<void> {
  submitting.value = true;
  message.value = "";
  try {
    const user = await api<User>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email: email.value, password: password.value }),
    });
    emit("authenticated", user);
  } catch (error) {
    message.value = error instanceof Error ? error.message : branding.loginError;
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <section class="auth-page">
    <form class="auth-card" @submit.prevent="submit">
      <h1>{{ branding.loginTitle }}</h1>
      <label>
        {{ branding.emailLabel }}
        <input v-model.trim="email" type="email" autocomplete="email" required maxlength="320">
      </label>
      <label>
        {{ branding.passwordLabel }}
        <input
          v-model="password"
          type="password"
          autocomplete="current-password"
          required
          minlength="8"
          maxlength="256"
        >
      </label>
      <button class="primary-button" type="submit" :disabled="submitting">
        {{ submitting ? branding.submitting : branding.loginButton }}
      </button>
      <StatusMessage :message="message" error />
    </form>
  </section>
</template>
