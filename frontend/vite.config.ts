import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";

// Log environment variables during build (for debugging)
if (process.env.VITE_CLERK_PUBLISHABLE_KEY) {
  console.log("✅ [Vite Build] VITE_CLERK_PUBLISHABLE_KEY is available during build");
  console.log("   Key prefix:", process.env.VITE_CLERK_PUBLISHABLE_KEY.substring(0, 8) + "...");
} else {
  console.warn("⚠️  [Vite Build] VITE_CLERK_PUBLISHABLE_KEY is NOT available during build");
  console.warn("   This will cause authentication to fail in production!");
  console.warn("   Make sure it's set in Vercel → Settings → Environment Variables");
}

// https://vitejs.dev/config/
export default defineConfig({
  server: {
    host: "::",
    port: 8080,
  },
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
