import { useAuth } from "@clerk/clerk-react";
import { Navigate } from "react-router-dom";
import { ROUTES } from "@/constants/routes";

interface ProtectedRouteProps {
  children: React.ReactNode;
}

/**
 * Protected route component that ensures user is authenticated.
 * No longer redirects based on training completion status - both Training
 * and Activity pages are always accessible to authenticated users.
 */
const ProtectedRoute = ({ children }: ProtectedRouteProps) => {
  const { isLoaded, isSignedIn } = useAuth();

  // Wait for Clerk to load
  if (!isLoaded) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  // Redirect to sign in if not authenticated
  if (!isSignedIn) {
    return <Navigate to={ROUTES.SIGN_IN} replace />;
  }

  // User is authenticated - render the protected content
  return <>{children}</>;
};

export default ProtectedRoute;
