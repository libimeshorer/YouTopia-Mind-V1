import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";

// Log environment variables during build (for debugging)
console.log("🔍 [Vite Build] Checking environment variables...");
console.log("   NODE_ENV:", process.env.NODE_ENV);
const viteEnvVars = Object.keys(process.env).filter(key => key.startsWith("VITE_"));
console.log("   All VITE_* env vars:", viteEnvVars);
console.log("   Total VITE_* vars found:", viteEnvVars.length);

// Check for similar variable names (in case of typo)
const clerkRelatedVars = viteEnvVars.filter(key => 
  key.toLowerCase().includes("clerk") || 
  key.toLowerCase().includes("publishable")
);
if (clerkRelatedVars.length > 0) {
  console.warn("   ⚠️  Found similar variable names:", clerkRelatedVars);
  console.warn("   These might be typos - check the exact variable name!");
}

// Check for the exact variable
if (process.env.VITE_CLERK_PUBLISHABLE_KEY) {
  console.log("✅ [Vite Build] VITE_CLERK_PUBLISHABLE_KEY is available during build");
  console.log("   Key prefix:", process.env.VITE_CLERK_PUBLISHABLE_KEY.substring(0, 8) + "...");
  console.log("   Key length:", process.env.VITE_CLERK_PUBLISHABLE_KEY.length);
} else {
  console.error("❌ [Vite Build] VITE_CLERK_PUBLISHABLE_KEY is NOT available during build");
  console.error("   This will cause authentication to fail in production!");
  console.error("");
  console.error("   🔧 TROUBLESHOOTING STEPS:");
  console.error("   1. Go to Vercel → Settings → Environment Variables");
  console.error("   2. Verify the variable name is EXACTLY: VITE_CLERK_PUBLISHABLE_KEY");
  console.error("      (Check for spaces, typos, or case differences)");
  console.error("   3. Click 'Edit' on the variable and verify:");
  console.error("      - Name matches exactly (case-sensitive)");
  console.error("      - All environments (Production, Preview, Development) are checked");
  console.error("      - Value starts with 'pk_test_' or 'pk_live_'");
  console.error("   4. Delete the variable and re-add it (sometimes fixes sync issues)");
  console.error("   5. Redeploy with 'Clear Build Cache' option");
  console.error("");
  console.error("   📋 Available VITE_* variables in this build:");
  viteEnvVars.forEach(v => console.error(`      - ${v}`));
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
