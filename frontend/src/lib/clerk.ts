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
      console.error(message);
    }
  } else if (!isValidKey && publishableKey.length > 0) {
    console.error(
      "[Clerk Config] Invalid Clerk publishable key format. Expected key starting with 'pk_test_' or 'pk_live_'."
    );
  } else if (isDevelopment && publishableKey) {
    console.log("[Clerk Config] Clerk publishable key loaded successfully", {
      keyPrefix: publishableKey.substring(0, 8) + "...",
      isTestKey: publishableKey.startsWith("pk_test_"),
    });
  }

  return {
    publishableKey,
    isConfigured: Boolean(publishableKey && isValidKey),
  };
};

export const clerkConfig = getClerkConfig();
