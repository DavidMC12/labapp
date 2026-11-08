import path from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(import.meta.dirname, "src"),
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.ts",
    coverage: {
      include: ["src/**/*.{ts,tsx}"],
      exclude: [
        // Tests and the test helpers are themselves not under test.
        "**/*.test.{ts,tsx}",
        "src/test/**",
        // Type-only modules carry no run-time code to cover.
        "src/**/*.d.ts",
        "src/features/*/types.ts",
        // Generated Next.js files.
        ".next/**",
        "next-env.d.ts",
        "./next-env.d.ts",
      ],
      reporter: ["text-summary", "lcov"],
    },
  },
});
