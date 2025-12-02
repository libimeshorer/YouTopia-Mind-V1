import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";

// Log environment variables during build (for debugging)
console.log("🔍 [Vite Build] Checking environment variables...");
console.log("   NODE_ENV:", process.env.NODE_ENV);
console.log("   All VITE_* env vars:", Object.keys(process.env).filter(key => key.startsWith("VITE_")));

if (process.env.VITE_CLERK_PUBLISHABLE_KEY) {
  console.log("✅ [Vite Build] VITE_CLERK_PUBLISHABLE_KEY is available during build");
  console.log("   Key prefix:", process.env.VITE_CLERK_PUBLISHABLE_KEY.substring(0, 8) + "...");
  console.log("   Key length:", process.env.VITE_CLERK_PUBLISHABLE_KEY.length);
} else {
  console.error("❌ [Vite Build] VITE_CLERK_PUBLISHABLE_KEY is NOT available during build");
  console.error("   This will cause authentication to fail in production!");
  console.error("   Make sure it's set in Vercel → Settings → Environment Variables");
  console.error("   Variable name must be exactly: VITE_CLERK_PUBLISHABLE_KEY (case-sensitive)");
  console.error("   Check that it's enabled for Production, Preview, and Development environments");
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
