import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { useEffect } from "react";
import { apiClient } from "@/api/client";
import { TrainingStatus } from "@/types";
import { ROUTES } from "@/constants/routes";

/**
 * Hook to check training status and handle redirects
 */
export const useTrainingStatus = () => {
  const navigate = useNavigate();

  const { data: trainingStatus, isLoading, error } = useQuery<TrainingStatus>({
    queryKey: ["trainingStatus"],
    queryFn: () => apiClient.training.status(),
    retry: 1,
    staleTime: 30000, // 30 seconds
  });

  // Redirect logic based on training status
  useEffect(() => {
    if (isLoading || error) return;

    if (trainingStatus) {
      if (!trainingStatus.isComplete) {
        // If training incomplete and not already on training page, redirect
        if (window.location.pathname !== ROUTES.TRAINING) {
          navigate(ROUTES.TRAINING, { replace: true });
        }
      } else {
        // If training complete and on training page, redirect to activity
        if (window.location.pathname === ROUTES.TRAINING) {
          navigate(ROUTES.ACTIVITY, { replace: true });
        }
      }
    }
  }, [trainingStatus, isLoading, error, navigate]);

  return {
    trainingStatus,
    isLoading,
    error,
    isComplete: trainingStatus?.isComplete ?? false,
    progress: trainingStatus?.progress ?? 0,
  };
};

