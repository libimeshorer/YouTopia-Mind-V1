import { useAuth } from "@clerk/clerk-react";
import { Navigate, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useRef } from "react";
import { ROUTES } from "@/constants/routes";
import { apiClient } from "@/api/client";
import { TrainingStatus } from "@/types";

interface ProtectedRouteProps {
  children: React.ReactNode;
}

const ProtectedRoute = ({ children }: ProtectedRouteProps) => {
  const { isLoaded, isSignedIn } = useAuth();
  const location = useLocation();
  const lastRedirectPath = useRef<string | null>(null);

  // Read from cache only - don't create a new query instance
  // The Training page will handle the actual refetching
  const { data: trainingStatus, isLoading: statusLoading, isError } = useQuery<TrainingStatus>({
    queryKey: ["trainingStatus"],
    queryFn: () => apiClient.training.status(),
    enabled: isSignedIn && isLoaded,
    retry: 1,
    refetchOnWindowFocus: false,
    refetchOnMount: false, // Don't refetch on mount, use cached data
    staleTime: Infinity, // Use cached data, let Training page handle refetching
  });

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

  // If API call is still loading, allow Training page to render immediately
  // Other pages can wait, but Training should show content even while loading
  const isTrainingPage = location.pathname === ROUTES.TRAINING;
  if (statusLoading && !isTrainingPage) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading your data...</p>
        </div>
      </div>
    );
  }

  // Memoize redirect logic to prevent unnecessary re-evaluations
  const redirectTarget = useMemo(() => {
    if (!trainingStatus || isError) return null;

    const currentPath = location.pathname;
    const isTrainingPage = currentPath === ROUTES.TRAINING;
    const isActivityPage = currentPath === ROUTES.ACTIVITY;
    const isDashboardPage = currentPath === ROUTES.DASHBOARD;

    // Only redirect if we haven't already redirected to this target
    // This prevents redirect loops when data refetches
    if (!trainingStatus.isComplete && isActivityPage) {
      const target = ROUTES.TRAINING;
      if (lastRedirectPath.current !== target) {
        lastRedirectPath.current = target;
        return target;
      }
    }

    if (trainingStatus.isComplete && isTrainingPage) {
      const target = ROUTES.ACTIVITY;
      if (lastRedirectPath.current !== target) {
        lastRedirectPath.current = target;
        return target;
      }
    }

    if (isDashboardPage) {
      const target = trainingStatus.isComplete ? ROUTES.ACTIVITY : ROUTES.TRAINING;
      if (lastRedirectPath.current !== target) {
        lastRedirectPath.current = target;
        return target;
      }
    }

    // Reset redirect path if we're already on the correct page
    if (
      (trainingStatus.isComplete && isActivityPage) ||
      (!trainingStatus.isComplete && isTrainingPage)
    ) {
      lastRedirectPath.current = currentPath;
    }

    return null;
  }, [trainingStatus, isError, location.pathname]);

  // Only redirect if we have a target and it's different from current path
  if (redirectTarget && redirectTarget !== location.pathname) {
    return <Navigate to={redirectTarget} replace />;
  }

  // If API error or no training status, still render the page
  // The individual pages will handle their own error states
  return <>{children}</>;
};

export default ProtectedRoute;




