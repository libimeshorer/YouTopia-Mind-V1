/**
 * Clerk configuration
 * Validates and exports Clerk publishable key from environment variables
 */
const getClerkConfig = () => {
  const publishableKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY || "";
  const isProduction = import.meta.env.PROD;
  const isDevelopment = import.meta.env.DEV;

  // Validate key format
  const isValidKey = publishableKey.startsWith("pk_test_") || 
                     publishableKey.startsWith("pk_live_");

  if (!publishableKey) {
    const message = "[Clerk Config] VITE_CLERK_PUBLISHABLE_KEY is not set. Clerk authentication will not work.";
    if (isDevelopment) {
      console.warn(message);
      console.info("[Clerk Config] To fix: Add VITE_CLERK_PUBLISHABLE_KEY to your .env.local file or Vercel environment variables.");
    } else {
      // In production, log more details to help debug
      console.error(message);
      console.error("[Clerk Config] Debug info:", {
        envVarExists: typeof import.meta.env.VITE_CLERK_PUBLISHABLE_KEY !== "undefined",
        envVarValue: import.meta.env.VITE_CLERK_PUBLISHABLE_KEY || "(empty or undefined)",
        isProduction: isProduction,
        allEnvKeys: Object.keys(import.meta.env).filter(key => key.startsWith("VITE_")),
      });
      console.info("[Clerk Config] To fix: Add VITE_CLERK_PUBLISHABLE_KEY in Vercel Settings → Environment Variables, then redeploy.");
    }
  } else if (!isValidKey && publishableKey.length > 0) {
    console.error(
      "[Clerk Config] Invalid Clerk publishable key format. Expected key starting with 'pk_test_' or 'pk_live_'."
    );
    console.error("[Clerk Config] Received value:", publishableKey.substring(0, 20) + "...");
  } else if (publishableKey) {
    // Log success in both dev and production (helps verify it's working)
    const logLevel = isDevelopment ? console.log : console.info;
    logLevel("[Clerk Config] Clerk publishable key loaded successfully", {
      keyPrefix: publishableKey.substring(0, 8) + "...",
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
