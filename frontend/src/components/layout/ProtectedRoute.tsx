import { useAuth } from "@clerk/clerk-react";
import { Navigate, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ROUTES } from "@/constants/routes";
import { apiClient } from "@/api/client";
import { TrainingStatus } from "@/types";

interface ProtectedRouteProps {
  children: React.ReactNode;
}

const ProtectedRoute = ({ children }: ProtectedRouteProps) => {
  const { isLoaded, isSignedIn } = useAuth();
  const location = useLocation();

  const { data: trainingStatus, isLoading: statusLoading, isError } = useQuery<TrainingStatus>({
    queryKey: ["trainingStatus"],
    queryFn: () => apiClient.training.status(),
    enabled: isSignedIn && isLoaded,
    retry: 1,
    // Don't refetch on window focus to prevent endless loading
    refetchOnWindowFocus: false,
    // Set a stale time to prevent constant refetching
    staleTime: 30000, // 30 seconds
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

  // Redirect logic based on training status (only if we have data)
  if (trainingStatus && !isError) {
    const isTrainingPage = location.pathname === ROUTES.TRAINING;
    const isActivityPage = location.pathname === ROUTES.ACTIVITY;
    const isDashboardPage = location.pathname === ROUTES.DASHBOARD;

    // If training incomplete and on activity page, redirect to training
    if (!trainingStatus.isComplete && isActivityPage) {
      return <Navigate to={ROUTES.TRAINING} replace />;
    }

    // If training complete and on training page, redirect to activity
    if (trainingStatus.isComplete && isTrainingPage) {
      return <Navigate to={ROUTES.ACTIVITY} replace />;
    }

    // If on dashboard, redirect based on training status
    if (isDashboardPage) {
      if (trainingStatus.isComplete) {
        return <Navigate to={ROUTES.ACTIVITY} replace />;
      } else {
        return <Navigate to={ROUTES.TRAINING} replace />;
      }
    }
  }

  // If API error or no training status, still render the page
  // The individual pages will handle their own error states
  return <>{children}</>;
};

export default ProtectedRoute;




