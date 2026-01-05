import { SignedIn, SignedOut, UserButton, useAuth } from "@clerk/clerk-react";
import { Button } from "@/components/ui/button";
import { LogIn, UserPlus } from "lucide-react";
import { Link, useLocation } from "react-router-dom";
import { ROUTES } from "@/constants/routes";
import { clerkConfig } from "@/lib/clerk";
import { useEffect, useState } from "react";

// Sign In button component (reusable)
const SignInButton = () => (
  <Link to={ROUTES.SIGN_IN}>
    <Button
      variant="outline"
      size="sm"
      className="bg-card/80 backdrop-blur-sm border-border/50 hover:bg-card hover:border-primary/30"
    >
      <LogIn className="w-4 h-4 mr-2" />
      Sign In
    </Button>
  </Link>
);

// Sign Up button component (reusable)
const SignUpButton = () => (
  <Link to={ROUTES.SIGN_UP}>
    <Button
      size="sm"
      className="bg-gradient-primary hover:shadow-glow transition-all duration-300"
    >
      <UserPlus className="w-4 h-4 mr-2" />
      Sign Up
    </Button>
  </Link>
);

// Header with Clerk integration (only used when ClerkProvider is present)
const ClerkHeader = () => {
  const auth = useAuth();
  const location = useLocation();
  const isLoaded = auth?.isLoaded ?? false;
  const isSignedIn = auth?.isSignedIn ?? false;
  const [showFallback, setShowFallback] = useState(false);

  useEffect(() => {
    if (isLoaded) {
      console.log("[Header] Clerk initialized successfully", {
        isSignedIn,
      });
      setShowFallback(false);
    } else {
      // Set a timeout to show fallback if Clerk doesn't load
      const timeout = setTimeout(() => {
        if (!isLoaded) {
          console.warn(
            "[Header] Clerk failed to load after 3s timeout. Showing fallback Sign In button."
          );
          setShowFallback(true);
        }
      }, 3000);

      return () => clearTimeout(timeout);
    }
  }, [isLoaded, isSignedIn]);

  if (showFallback || !isLoaded) {
    return (
      <header className="absolute top-0 left-0 right-0 z-50 p-6">
        <div className="container mx-auto flex justify-end items-center gap-3">
          {!isLoaded && <div className="w-40 h-8" />}
          {showFallback && (
            <>
              <SignInButton />
              <SignUpButton />
            </>
          )}
        </div>
      </header>
    );
  }

  return (
    <header className="absolute top-0 left-0 right-0 z-50 p-6">
      <div className="container mx-auto flex justify-between items-center">
        <div className="flex items-center gap-4">
          <SignedIn>
            {/* Always show both Training and Activity links */}
            <Link
              to={ROUTES.TRAINING}
              className={`text-sm font-medium transition-colors ${
                location.pathname === ROUTES.TRAINING
                  ? "text-primary"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              Training
            </Link>
            <Link
              to={ROUTES.ACTIVITY}
              className={`text-sm font-medium transition-colors ${
                location.pathname === ROUTES.ACTIVITY
                  ? "text-primary"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              Activity
            </Link>
          </SignedIn>
        </div>
        <div className="flex items-center gap-3">
          <SignedOut>
            <SignInButton />
            <SignUpButton />
          </SignedOut>
          <SignedIn>
            <UserButton
              appearance={{
                elements: {
                  avatarBox: "w-10 h-10",
                },
              }}
            />
          </SignedIn>
        </div>
      </div>
    </header>
  );
};

// Fallback header without Clerk (used when ClerkProvider is not present)
const FallbackHeader = () => {
  useEffect(() => {
    console.warn(
      "[Header] Clerk is not configured. Showing fallback Sign In button."
    );
  }, []);

  return (
    <header className="absolute top-0 left-0 right-0 z-50 p-6">
      <div className="container mx-auto flex justify-end items-center gap-3">
        <SignInButton />
        <SignUpButton />
      </div>
    </header>
  );
};

// Main Header component - conditionally renders based on Clerk configuration
// Note: ClerkHeader uses useAuth() which requires ClerkProvider to be present
// If App.tsx doesn't render ClerkProvider (when Clerk not configured),
// we must use FallbackHeader instead
const Header = () => {
  // Only use ClerkHeader if Clerk is configured
  // App.tsx will conditionally render ClerkProvider based on clerkConfig.isConfigured
  // So if isConfigured is true, ClerkProvider should be present
  if (clerkConfig.isConfigured && clerkConfig.publishableKey) {
    // ClerkProvider should be present (rendered by App.tsx)
    // ClerkHeader will use useAuth() which requires ClerkProvider
    return <ClerkHeader />;
  }

  // Clerk not configured, use fallback (no Clerk hooks)
  return <FallbackHeader />;
};

export default Header;
