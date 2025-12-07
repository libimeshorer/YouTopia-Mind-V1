import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { useUser } from "@clerk/clerk-react";
import { useMemo } from "react";
import Header from "@/components/layout/Header";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { DocumentUpload } from "@/components/features/DocumentUpload";
import { InsightsManager } from "@/components/features/InsightsManager";
import { IntegrationCard } from "@/components/features/IntegrationCard";
import { TrainingProgress } from "@/components/features/TrainingProgress";
import { StatsCards } from "@/components/features/StatsCards";
import { apiClient } from "@/api/client";
import { TrainingStatus, Integration } from "@/types";
import { ROUTES } from "@/constants/routes";
import { useToast } from "@/hooks/use-toast";
import { Bot, MessageSquare, Loader2 } from "lucide-react";

const Training = () => {
  const { user } = useUser();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { toast } = useToast();

  // Only refetch if training is not complete - once complete, no need to keep checking
  const { data: trainingStatus, isLoading: statusLoading, isFetching: statusFetching, isError: statusError } = useQuery<TrainingStatus>({
    queryKey: ["trainingStatus"],
    queryFn: () => apiClient.training.status(),
    // Only refetch if training is incomplete - stop refetching once complete
    // This prevents unnecessary refetches that cause page reloads
    refetchInterval: (query) => {
      const data = query.state.data as TrainingStatus | undefined;
      // If training is complete, stop refetching (return false)
      if (data?.isComplete) {
        return false;
      }
      // Otherwise refetch every 60 seconds (increased from 30 to reduce reloads)
      return 60000;
    },
    retry: 1,
    refetchOnWindowFocus: false,
    // Don't refetch on mount if we have cached data to prevent initial reload
    refetchOnMount: false,
  });

  const { data: stats } = useQuery({
    queryKey: ["trainingStats"],
    queryFn: () => apiClient.training.stats(),
  });

  const { data: integrations = [] } = useQuery<Integration[]>({
    queryKey: ["integrations"],
    queryFn: () => apiClient.integrations.list(),
  });

  const completeMutation = useMutation({
    mutationFn: () => apiClient.training.complete(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["trainingStatus"] });
      setTimeout(() => {
        navigate(ROUTES.ACTIVITY);
      }, 2000);
    },
  });

  const handleComplete = () => {
    if (effectiveTrainingStatus && effectiveTrainingStatus.progress >= 100) {
      completeMutation.mutate();
    }
  };

  // Create a default training status if API fails
  const defaultTrainingStatus: TrainingStatus = {
    isComplete: false,
    progress: 0,
    documentsCount: 0,
    insightsCount: 0,
    integrationsCount: 0,
    thresholds: {
      minDocuments: 5,
      minInsights: 3,
      minIntegrations: 1,
    },
    achievements: [],
  };

  // Use default status if API fails or is loading
  const effectiveTrainingStatus = trainingStatus || defaultTrainingStatus;

  // Only show loading spinner on initial load, not during background refetches
  if (statusLoading && !trainingStatus) {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <div className="container mx-auto px-6 py-24">
          <div className="flex items-center justify-center">
            <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
          </div>
        </div>
      </div>
    );
  }

  // Memoize grouped integrations to prevent recalculation on every render
  const groupedIntegrations = useMemo(
    () =>
      integrations.reduce(
        (acc, integration) => {
          if (!acc[integration.category]) {
            acc[integration.category] = [];
          }
          acc[integration.category].push(integration);
          return acc;
        },
        {} as Record<string, Integration[]>
      ),
    [integrations]
  );

  return (
    <div className="min-h-screen bg-background">
      <Header />
      <div className="container mx-auto px-6 py-24">
        <div className="max-w-7xl mx-auto space-y-8">
          {/* Welcome Section */}
          <div className="mb-8">
            <h1 className="text-4xl md:text-5xl font-bold mb-4">
              Welcome, {user?.firstName || user?.emailAddresses?.[0]?.emailAddress?.split("@")[0] || "there"}!
            </h1>
            <p className="text-xl text-muted-foreground">
              Let's train your digital twin. Complete the steps below to get started.
            </p>
            {statusError && (
              <div className="mt-4 p-4 bg-yellow-500/10 border border-yellow-500/20 rounded-lg">
                <p className="text-sm text-yellow-600 dark:text-yellow-400">
                  ⚠️ Unable to connect to the backend. You can still explore the interface, but data won't be saved.
                </p>
              </div>
            )}
          </div>

          {/* Progress Indicator */}
          <Card>
            <CardContent className="pt-6">
              <TrainingProgress
                trainingStatus={effectiveTrainingStatus}
                onComplete={handleComplete}
              />
            </CardContent>
          </Card>

          {/* Main Content Grid */}
          <div className="grid lg:grid-cols-3 gap-8">
            {/* Left Column - Training Sections */}
            <div className="lg:col-span-2 space-y-8">
              {/* Section 1.1: Upload Documents */}
              <Card data-training-section data-complete={effectiveTrainingStatus.documentsCount >= effectiveTrainingStatus.thresholds.minDocuments ? "true" : "false"}>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Bot className="w-5 h-5" />
                    1.1 Upload Documents
                  </CardTitle>
                  <CardDescription>
                    Upload PDFs, Word documents, and text files to train your clone
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <DocumentUpload
                    onUploadComplete={() => {
                      queryClient.invalidateQueries({ queryKey: ["trainingStatus"] });
                    }}
                  />
                </CardContent>
              </Card>

              {/* Section 1.2: Agent Interviewer */}
              <Card data-training-section data-complete="false">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <MessageSquare className="w-5 h-5" />
                    1.2 Agent Interviewer
                  </CardTitle>
                  <CardDescription>
                    Use our AI interviewer to collect initial data about you
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="text-center py-8">
                    <p className="text-muted-foreground mb-4">
                      The agent interviewer will be available soon.
                    </p>
                    <Button disabled variant="outline">
                      Coming Soon
                    </Button>
                  </div>
                </CardContent>
              </Card>

              {/* Section 1.3: Connect Integrations */}
              <Card data-training-section data-complete={effectiveTrainingStatus.integrationsCount >= effectiveTrainingStatus.thresholds.minIntegrations ? "true" : "false"}>
                <CardHeader>
                  <CardTitle>1.3 Connect Integrations</CardTitle>
                  <CardDescription>
                    Link your communication and productivity tools to sync data
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  {/* Communication Integrations */}
                  {groupedIntegrations.communication && (
                    <div>
                      <h4 className="text-sm font-semibold mb-3 text-muted-foreground">
                        Communication
                      </h4>
                      <div className="grid md:grid-cols-2 gap-4">
                        {groupedIntegrations.communication.map((integration) => (
                          <IntegrationCard key={integration.id} integration={integration} />
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Storage Integrations */}
                  {groupedIntegrations.storage && (
                    <div>
                      <h4 className="text-sm font-semibold mb-3 text-muted-foreground">
                        Storage
                      </h4>
                      <div className="grid md:grid-cols-2 gap-4">
                        {groupedIntegrations.storage.map((integration) => (
                          <IntegrationCard key={integration.id} integration={integration} />
                        ))}
                      </div>
                    </div>
                  )}

                  {/* AI Agent Integrations */}
                  {groupedIntegrations.ai_agent && (
                    <div>
                      <h4 className="text-sm font-semibold mb-3 text-muted-foreground">
                        AI Agents
                      </h4>
                      <div className="grid md:grid-cols-2 gap-4">
                        {groupedIntegrations.ai_agent.map((integration) => (
                          <IntegrationCard key={integration.id} integration={integration} />
                        ))}
                      </div>
                    </div>
                  )}

                  {integrations.length === 0 && (
                    <div className="text-center py-8 text-muted-foreground">
                      <p>No integrations available yet</p>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Section 1.4: Record Insights */}
              <Card data-training-section data-complete={effectiveTrainingStatus.insightsCount >= effectiveTrainingStatus.thresholds.minInsights ? "true" : "false"}>
                <CardHeader>
                  <CardTitle>1.4 Record Insights</CardTitle>
                  <CardDescription>
                    Record voice notes or add text insights about yourself
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <InsightsManager />
                </CardContent>
              </Card>
            </div>

            {/* Right Column - Stats */}
            <div className="lg:col-span-1">
              <div className="sticky top-24">
                <StatsCards
                  documentsCount={effectiveTrainingStatus.documentsCount}
                  insightsCount={effectiveTrainingStatus.insightsCount}
                  integrationsCount={effectiveTrainingStatus.integrationsCount}
                  dataPoints={stats?.dataPoints || 0}
                  lastActivity={stats?.lastActivity}
                  progress={effectiveTrainingStatus.progress}
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Training;

