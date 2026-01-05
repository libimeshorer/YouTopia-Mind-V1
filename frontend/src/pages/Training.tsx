import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useUser } from "@clerk/clerk-react";
import Header from "@/components/layout/Header";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { DocumentUpload } from "@/components/features/DocumentUpload";
import { InsightsManager } from "@/components/features/InsightsManager";
import { IntegrationCard } from "@/components/features/IntegrationCard";
import { StatsCards } from "@/components/features/StatsCards";
import { apiClient } from "@/api/client";
import { Integration } from "@/types";
import { Bot, MessageSquare, Loader2 } from "lucide-react";

// Type for training stats response
interface TrainingStats {
  documentsCount: number;
  insightsCount: number;
  integrationsCount: number;
  dataPoints: number;
  lastActivity?: string;
}

const Training = () => {
  const { user } = useUser();
  const queryClient = useQueryClient();

  // Only fetch stats - no longer need training status with progress/thresholds
  const {
    data: stats,
    isLoading: statsLoading,
    isError: statsError,
  } = useQuery<TrainingStats>({
    queryKey: ["trainingStats"],
    queryFn: () => apiClient.training.stats(),
    staleTime: 30000,
    retry: 1,
    refetchOnWindowFocus: false,
  });

  const { data: integrations = [] } = useQuery<Integration[]>({
    queryKey: ["integrations"],
    queryFn: () => apiClient.integrations.list(),
  });

  // Default stats if API fails
  const effectiveStats: TrainingStats = stats || {
    documentsCount: 0,
    insightsCount: 0,
    integrationsCount: 0,
    dataPoints: 0,
  };

  // Only show loading spinner on initial load
  if (statsLoading && !stats) {
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

  // Group integrations by category
  const groupedIntegrations = integrations.reduce(
    (acc, integration) => {
      if (!acc[integration.category]) {
        acc[integration.category] = [];
      }
      acc[integration.category].push(integration);
      return acc;
    },
    {} as Record<string, Integration[]>
  );

  return (
    <div className="min-h-screen bg-background">
      <Header />
      <div className="container mx-auto px-6 py-24">
        <div className="max-w-7xl mx-auto space-y-8">
          {/* Welcome Section */}
          <div className="mb-8">
            <h1 className="text-4xl md:text-5xl font-bold mb-4">
              Welcome,{" "}
              {user?.firstName ||
                user?.emailAddresses?.[0]?.emailAddress?.split("@")[0] ||
                "there"}
              !
            </h1>
            <p className="text-xl text-muted-foreground">
              Let's train your clone! Add documents, insights, and integrations
              to grow your knowledge crystals.
            </p>
            {statsError && (
              <div className="mt-4 p-4 bg-yellow-500/10 border border-yellow-500/20 rounded-lg">
                <p className="text-sm text-yellow-600 dark:text-yellow-400 font-medium mb-2">
                  Unable to connect to the backend
                </p>
                <p className="text-xs text-yellow-600/80 dark:text-yellow-400/80">
                  {import.meta.env.VITE_API_URL
                    ? `Backend URL is configured as: ${import.meta.env.VITE_API_URL}. Please verify it's correct and the backend is running.`
                    : `VITE_API_URL environment variable is not set. Set it to your backend URL (e.g., https://api.you-topia.ai) in your deployment platform (Vercel → Settings → Environment Variables).`}
                </p>
                <p className="text-xs text-yellow-600/80 dark:text-yellow-400/80 mt-2">
                  You can still explore the interface, but data won't be saved.
                </p>
              </div>
            )}
          </div>

          {/* Main Content Grid */}
          <div className="grid lg:grid-cols-3 gap-8">
            {/* Left Column - Training Sections */}
            <div className="lg:col-span-2 space-y-8">
              {/* Section 1.1: Upload Documents */}
              <Card data-training-section>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Bot className="w-5 h-5" />
                    1. Upload Documents
                  </CardTitle>
                  <CardDescription>
                    Upload PDFs, Word documents, and text files to train your
                    clone
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <DocumentUpload
                    onUploadComplete={() => {
                      queryClient.invalidateQueries({
                        queryKey: ["trainingStats"],
                      });
                    }}
                  />
                </CardContent>
              </Card>

              {/* Section 1.2: Agent Interviewer */}
              <Card data-training-section>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <MessageSquare className="w-5 h-5" />
                    2. Agent Interviewer
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
              <Card data-training-section>
                <CardHeader>
                  <CardTitle>3. Connect Integrations</CardTitle>
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
                          <IntegrationCard
                            key={integration.id}
                            integration={integration}
                          />
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
                          <IntegrationCard
                            key={integration.id}
                            integration={integration}
                          />
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
                          <IntegrationCard
                            key={integration.id}
                            integration={integration}
                          />
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
              <Card data-training-section>
                <CardHeader>
                  <CardTitle>4. Record Insights</CardTitle>
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
                  documentsCount={effectiveStats.documentsCount}
                  integrationsCount={effectiveStats.integrationsCount}
                  insightsCount={effectiveStats.insightsCount}
                  lastActivity={effectiveStats.lastActivity}
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
