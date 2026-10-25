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
  // alphaTab starts its worker as a module worker and its worklet with
  // addModule(), and reads import.meta.url inside both. Rolldown (vite 8)
  // empties import.meta in an iife bundle; Rollup used to rewrite it. The
  // worker build does not inherit build.minify, so it is asked for here.
  worker: { format: "es", rolldownOptions: { output: { minify: true } } },
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.ts"],
  },
});
