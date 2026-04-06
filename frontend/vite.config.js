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
    rollupOptions: {
      output: {
        // Split vendor libraries into a separate cached chunk
        manualChunks: (id) => {
          if (id.includes("node_modules")) {
            // Firebase gets its own chunk (large & rarely changes)
            if (id.includes("firebase")) return "firebase";
            // React ecosystem in one vendor chunk
            if (
              id.includes("react") ||
              id.includes("react-dom") ||
              id.includes("react-router") ||
              id.includes("redux")
            )
              return "react-vendor";
            // Everything else in a general vendor chunk
            return "vendor";
          }
        },
      },
    },
  },
}));
