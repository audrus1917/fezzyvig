<script setup lang="ts">
defineProps<{ message: string; error?: boolean }>();
</script>

<template>
  <p class="form-status" :class="{ error }" aria-live="polite">{{ message }}</p>
</template>
