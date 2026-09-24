<script setup lang="ts">
import { ref } from "vue";

import { api } from "../api";
import type { User } from "../types";
import StatusMessage from "./StatusMessage.vue";

const emit = defineEmits<{ authenticated: [user: User] }>();

const mode = ref<"login" | "register">("login");
const firstName = ref("");
const lastName = ref("");
const email = ref("");
const password = ref("");
const submitting = ref(false);
const message = ref("");

async function submit(): Promise<void> {
  submitting.value = true;
  message.value = "";
  try {
    const user = await api<User>(`/auth/${mode.value}`, {
      method: "POST",
      body: JSON.stringify({
        email: email.value,
        password: password.value,
        ...(mode.value === "register"
          ? { first_name: firstName.value, last_name: lastName.value }
          : {}),
      }),
    });
    emit("authenticated", user);
  } catch (error) {
    message.value = error instanceof Error ? error.message : "Не удалось выполнить вход";
  } finally {
    submitting.value = false;
  }
}

function switchMode(): void {
  mode.value = mode.value === "login" ? "register" : "login";
  message.value = "";
}
</script>

<template>
  <section class="auth-page">
    <div class="auth-intro">
      <p class="eyebrow">TALENT WORKSPACE</p>
      <h1>Работа начинается<br><em>с правильных людей.</em></h1>
      <p class="hero-copy">
        Войдите в личное рабочее пространство, чтобы подключить HeadHunter и управлять
        своими вакансиями.
      </p>
    </div>
    <form class="auth-card" @submit.prevent="submit">
      <p class="company">FEZZYVIG ACCOUNT</p>
      <h2>{{ mode === "login" ? "Вход" : "Регистрация" }}</h2>
      <template v-if="mode === 'register'">
        <label>
          Имя
          <input v-model.trim="firstName" type="text" autocomplete="given-name" required maxlength="100">
        </label>
        <label>
          Фамилия
          <input v-model.trim="lastName" type="text" autocomplete="family-name" required maxlength="100">
        </label>
      </template>
      <label>
        Email
        <input v-model.trim="email" type="email" autocomplete="email" required maxlength="320">
      </label>
      <label>
        Пароль
        <input
          v-model="password"
          type="password"
          :autocomplete="mode === 'login' ? 'current-password' : 'new-password'"
          required
          minlength="8"
          maxlength="256"
        >
      </label>
      <button class="primary-button" type="submit" :disabled="submitting">
        {{ submitting ? "Подождите…" : mode === "login" ? "Войти" : "Создать аккаунт" }}
      </button>
      <StatusMessage :message="message" error />
      <button class="auth-switch" type="button" @click="switchMode">
        {{ mode === "login" ? "Нет аккаунта? Зарегистрироваться" : "Уже есть аккаунт? Войти" }}
      </button>
    </form>
  </section>
</template>
