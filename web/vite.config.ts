import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";
import { alphaTab } from "@coderline/alphatab-vite";

export default defineConfig({
  plugins: [svelte(), alphaTab()],
  base: "./",
  server: { port: 5173, fs: { strict: false } },
  build: {
    target: "es2022",
    sourcemap: true,
  },
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.ts"],
  },
});
