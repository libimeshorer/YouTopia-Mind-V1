import { SignedIn, SignedOut, UserButton, useAuth } from "@clerk/clerk-react";
import { Button } from "@/components/ui/button";
import { LogIn } from "lucide-react";
import { Link } from "react-router-dom";
import { ROUTES } from "@/constants/routes";
import { clerkConfig } from "@/lib/clerk";
import { useEffect, useState } from "react";

const Header = () => {
  const [showFallback, setShowFallback] = useState(!clerkConfig.isConfigured);

  // Always call useAuth hook unconditionally (React rules)
  // If Clerk isn't configured, ClerkProvider will still provide a context
  const auth = useAuth();
  const isLoaded = auth?.isLoaded ?? false;
  const isSignedIn = auth?.isSignedIn ?? false;

  useEffect(() => {
    // Check if Clerk is properly configured
    if (!clerkConfig.isConfigured) {
      console.warn(
        "[Header] Clerk is not configured. Showing fallback Sign In button."
      );
      setShowFallback(true);
      return;
    }

    // If Clerk is configured, wait for it to load
    if (isLoaded) {
      console.log("[Header] Clerk initialized successfully", {
        isSignedIn,
        isConfigured: clerkConfig.isConfigured,
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

  return (
    <header className="absolute top-0 left-0 right-0 z-50 p-6">
      <div className="container mx-auto flex justify-end items-center">
        {/* Fallback: Show Sign In button if Clerk isn't configured or failed to load */}
        {showFallback && <SignInButton />}

        {/* Clerk-based rendering (only if Clerk is configured and loaded) */}
        {!showFallback && clerkConfig.isConfigured && (
          <>
            <SignedOut>
              <SignInButton />
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
          </>
        )}

        {/* Loading state: Show placeholder while Clerk loads (only if configured) */}
        {!showFallback && !isLoaded && clerkConfig.isConfigured && (
          <div className="w-20 h-8" />
        )}
      </div>
    </header>
  );
};

export default Header;


