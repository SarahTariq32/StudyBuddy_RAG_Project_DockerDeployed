// import { defineConfig } from 'vite'
// import react from '@vitejs/plugin-react'

// export default defineConfig({
//   plugins: [react()],
// })

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],

  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: "./src/tests/setup.js",
    css: true,
    clearMocks: true,
    include: ["src/tests/**/*.{test,spec}.{js,jsx,ts,tsx}"],
    // Keep unit tests focused on app code and ignore e2e/vendor suites.
    exclude: [
      "tests/**",
      "node_modules/**",
      "dist/**",
    ],
  },
});
