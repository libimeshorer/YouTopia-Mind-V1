/**
 * Clerk configuration
 * Validates and exports Clerk publishable key from environment variables
 */
const getClerkConfig = () => {
  const publishableKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY || "";
  const isProduction = import.meta.env.PROD;
  const isDevelopment = import.meta.env.DEV;

  // Debug: Log all available VITE_ env vars to help troubleshoot
  const allViteEnvVars = Object.keys(import.meta.env).filter(key => key.startsWith("VITE_"));
  
  // Validate key format
  const isValidKey = publishableKey.startsWith("pk_test_") || 
                     publishableKey.startsWith("pk_live_");

  if (!publishableKey) {
    const message = "[Clerk Config] ❌ VITE_CLERK_PUBLISHABLE_KEY is not set. Clerk authentication will not work.";
    if (isDevelopment) {
      console.warn(message);
      console.info("[Clerk Config] 🔍 Debug info:", {
        envVarExists: typeof import.meta.env.VITE_CLERK_PUBLISHABLE_KEY !== "undefined",
        envVarValue: import.meta.env.VITE_CLERK_PUBLISHABLE_KEY || "(empty or undefined)",
        allViteEnvVars: allViteEnvVars,
        mode: import.meta.env.MODE,
      });
      console.info("[Clerk Config] 🔧 To fix locally:");
      console.info("   1. Create/update .env.local in the frontend/ directory");
      console.info("   2. Add: VITE_CLERK_PUBLISHABLE_KEY=pk_test_your_key_here");
      console.info("   3. Restart the dev server (stop and run 'npm run dev' again)");
      console.info("   4. Check browser console for this message to confirm it's loaded");
    } else {
      // In production, log more details to help debug
      console.error(message);
      console.error("[Clerk Config] 🔍 Debug info:", {
        envVarExists: typeof import.meta.env.VITE_CLERK_PUBLISHABLE_KEY !== "undefined",
        envVarValue: import.meta.env.VITE_CLERK_PUBLISHABLE_KEY || "(empty or undefined)",
        isProduction: isProduction,
        allViteEnvVars: allViteEnvVars,
        mode: import.meta.env.MODE,
      });
      console.info("[Clerk Config] 🔧 To fix in production:");
      console.info("   1. Go to Vercel → Settings → Environment Variables");
      console.info("   2. Add/verify: VITE_CLERK_PUBLISHABLE_KEY (exact name, case-sensitive)");
      console.info("   3. Set value to your Clerk publishable key (starts with pk_test_ or pk_live_)");
      console.info("   4. Select all environments (Production, Preview, Development)");
      console.info("   5. Redeploy with 'Clear Build Cache' option");
    }
  } else if (!isValidKey && publishableKey.length > 0) {
    console.error(
      "[Clerk Config] ❌ Invalid Clerk publishable key format. Expected key starting with 'pk_test_' or 'pk_live_'."
    );
    console.error("[Clerk Config] Received value:", publishableKey.substring(0, 30) + "...");
    console.error("[Clerk Config] Key length:", publishableKey.length);
    console.error("[Clerk Config] First 20 chars:", publishableKey.substring(0, 20));
  } else if (publishableKey) {
    // Log success in both dev and production (helps verify it's working)
    const logLevel = isDevelopment ? console.log : console.info;
    logLevel("[Clerk Config] ✅ Clerk publishable key loaded successfully", {
      keyPrefix: publishableKey.substring(0, 12) + "...",
      keyLength: publishableKey.length,
      isTestKey: publishableKey.startsWith("pk_test_"),
      environment: isProduction ? "production" : "development",
    });
  }

  return {
    publishableKey,
    isConfigured: Boolean(publishableKey && isValidKey),
  };
};

export const clerkConfig = getClerkConfig();
