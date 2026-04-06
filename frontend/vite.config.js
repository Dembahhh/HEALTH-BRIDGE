import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import tailwindcss from "@tailwindcss/vite";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => ({
  plugins: [react(), tailwindcss()],
  define: {
    global: "globalThis",
  },
  build: {
    sourcemap: mode === "development",
    target: "es2015",
    cssCodeSplit: false,
  },
}));
