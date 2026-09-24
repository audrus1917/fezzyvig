import { fileURLToPath, URL } from "node:url";

import vue from "@vitejs/plugin-vue";
import { defineConfig } from "vite";

export default defineConfig(({ command }) => ({
  base: command === "build" ? "/static/" : "/",
  plugins: [vue()],
  build: {
    outDir: fileURLToPath(new URL("../src/fezzyvig/static", import.meta.url)),
    emptyOutDir: true,
  },
  server: {
    port: 5174,
    proxy: {
      "/auth": "http://127.0.0.1:8000",
      "/employer": "http://127.0.0.1:8000",
    },
  },
}));
