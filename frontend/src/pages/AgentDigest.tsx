import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import Header from "@/components/layout/Header";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  Loader2,
  AlertCircle,
  ThumbsUp,
  ThumbsDown,
  ChevronDown,
  ChevronUp,
  Clock,
  Hash,
  User,
  Sparkles,
  Star,
  HelpCircle,
  Eye,
} from "lucide-react";
import { AgentObservation, AgentDigest } from "@/types";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";

const AgentDigestPage = () => {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [expandedInteresting, setExpandedInteresting] = useState(false);

  // Fetch digest
  const {
    data: digest,
    isLoading,
    error,
  } = useQuery<AgentDigest>({
    queryKey: ["agent-digest"],
    queryFn: () => apiClient.agent.getDigest(7),
  });

  // Feedback mutation
  const feedbackMutation = useMutation({
    mutationFn: ({
      observationId,
      feedback,
    }: {
      observationId: string;
      feedback: string;
    }) => apiClient.agent.submitObservationFeedback(observationId, feedback),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["agent-digest"] });
      toast({
        title: "Feedback submitted",
        description: data.preferenceUpdated
          ? "Your preferences have been updated."
          : "Thanks for your feedback!",
      });
    },
    onError: () => {
      toast({
        title: "Error",
        description: "Failed to submit feedback. Please try again.",
        variant: "destructive",
      });
    },
  });

  const handleFeedback = (observationId: string, feedback: string) => {
    feedbackMutation.mutate({ observationId, feedback });
  };

  if (isLoading) {
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

  if (error) {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <div className="container mx-auto px-6 py-24">
          <Card className="p-6 text-center">
            <AlertCircle className="w-12 h-12 mx-auto mb-4 text-destructive" />
            <h2 className="text-xl font-semibold mb-2">Error loading digest</h2>
            <p className="text-muted-foreground">
              Please try again later or check your agent settings.
            </p>
          </Card>
        </div>
      </div>
    );
  }

  const hasObservations =
    digest &&
    (digest.veryInteresting.length > 0 ||
      digest.interesting.length > 0 ||
      digest.reviewNeeded.length > 0);

  return (
    <div className="min-h-screen bg-background">
      <Header />
      <div className="container mx-auto px-6 py-12">
        <div className="max-w-4xl mx-auto">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-3xl font-bold mb-2">Agent Digest</h1>
            <p className="text-muted-foreground">
              Messages surfaced from your connected channels
            </p>
            {digest?.stats && (
              <div className="flex gap-4 mt-4 text-sm text-muted-foreground">
                <span>
                  {digest.stats.totalObservations} observations in last{" "}
                  {digest.stats.periodDays} days
                </span>
                {digest.stats.lastObservationAt && (
                  <span>
                    Last updated:{" "}
                    {new Date(digest.stats.lastObservationAt).toLocaleString()}
                  </span>
                )}
              </div>
            )}
          </div>

          {!hasObservations ? (
            <Card className="p-12 text-center">
              <Eye className="w-16 h-16 mx-auto mb-4 text-muted-foreground" />
              <h2 className="text-xl font-semibold mb-2">No observations yet</h2>
              <p className="text-muted-foreground mb-4">
                Your agent hasn't observed any messages yet. Make sure you have
                set up a Slack connection and selected channels to monitor.
              </p>
              <Button
                onClick={() => (window.location.href = "/training")}
                className="bg-gradient-primary"
              >
                Go to Training
              </Button>
            </Card>
          ) : (
            <div className="space-y-8">
              {/* Very Interesting Section */}
              {digest.veryInteresting.length > 0 && (
                <DigestSection
                  title="Very Interesting"
                  icon={<Sparkles className="w-5 h-5 text-yellow-500" />}
                  badge={
                    <Badge variant="default" className="bg-yellow-500">
                      {digest.veryInteresting.length}
                    </Badge>
                  }
                  observations={digest.veryInteresting}
                  onFeedback={handleFeedback}
                  feedbackLoading={feedbackMutation.isPending}
                />
              )}

              {/* Interesting Section */}
              {digest.interesting.length > 0 && (
                <DigestSection
                  title="Interesting"
                  icon={<Star className="w-5 h-5 text-blue-500" />}
                  badge={
                    <Badge variant="secondary">
                      {digest.stats.interestingShown} /{" "}
                      {digest.stats.interestingCount}
                    </Badge>
                  }
                  observations={
                    expandedInteresting
                      ? digest.interesting
                      : digest.interesting.slice(0, 5)
                  }
                  onFeedback={handleFeedback}
                  feedbackLoading={feedbackMutation.isPending}
                  footer={
                    digest.interesting.length > 5 && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() =>
                          setExpandedInteresting(!expandedInteresting)
                        }
                        className="w-full mt-2"
                      >
                        {expandedInteresting ? (
                          <>
                            <ChevronUp className="w-4 h-4 mr-2" />
                            Show less
                          </>
                        ) : (
                          <>
                            <ChevronDown className="w-4 h-4 mr-2" />
                            Show {digest.interesting.length - 5} more
                          </>
                        )}
                      </Button>
                    )
                  }
                />
              )}

              {/* Review Needed Section */}
              {digest.reviewNeeded.length > 0 && (
                <DigestSection
                  title="Needs Review"
                  icon={<HelpCircle className="w-5 h-5 text-orange-500" />}
                  badge={
                    <Badge variant="outline" className="border-orange-500">
                      {digest.reviewNeeded.length}
                    </Badge>
                  }
                  description="These messages need your input to help improve classification"
                  observations={digest.reviewNeeded}
                  onFeedback={handleFeedback}
                  feedbackLoading={feedbackMutation.isPending}
                  showRecategorize
                />
              )}

              {/* Not Interesting Sample */}
              {digest.notInterestingSample.length > 0 && (
                <DigestSection
                  title="Filtered Out (Sample)"
                  icon={<Eye className="w-5 h-5 text-muted-foreground" />}
                  badge={<Badge variant="outline">Sample</Badge>}
                  description="These were classified as not interesting. Let us know if we got it wrong."
                  observations={digest.notInterestingSample}
                  onFeedback={handleFeedback}
                  feedbackLoading={feedbackMutation.isPending}
                  showRecategorize
                  muted
                />
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// Digest Section Component
interface DigestSectionProps {
  title: string;
  icon: React.ReactNode;
  badge: React.ReactNode;
  description?: string;
  observations: AgentObservation[];
  onFeedback: (observationId: string, feedback: string) => void;
  feedbackLoading: boolean;
  showRecategorize?: boolean;
  muted?: boolean;
  footer?: React.ReactNode;
}

const DigestSection = ({
  title,
  icon,
  badge,
  description,
  observations,
  onFeedback,
  feedbackLoading,
  showRecategorize,
  muted,
  footer,
}: DigestSectionProps) => {
  return (
    <div>
      <div className="flex items-center gap-2 mb-3">
        {icon}
        <h2 className="text-lg font-semibold">{title}</h2>
        {badge}
      </div>
      {description && (
        <p className="text-sm text-muted-foreground mb-3">{description}</p>
      )}
      <div className="space-y-3">
        {observations.map((obs) => (
          <ObservationCard
            key={obs.id}
            observation={obs}
            onFeedback={onFeedback}
            feedbackLoading={feedbackLoading}
            showRecategorize={showRecategorize}
            muted={muted}
          />
        ))}
      </div>
      {footer}
    </div>
  );
};

// Observation Card Component
interface ObservationCardProps {
  observation: AgentObservation;
  onFeedback: (observationId: string, feedback: string) => void;
  feedbackLoading: boolean;
  showRecategorize?: boolean;
  muted?: boolean;
}

const ObservationCard = ({
  observation,
  onFeedback,
  feedbackLoading,
  showRecategorize,
  muted,
}: ObservationCardProps) => {
  const isReviewed = observation.status === "reviewed";

  return (
    <Card
      className={`p-4 ${muted ? "opacity-70" : ""} ${
        isReviewed ? "border-green-500/30 bg-green-500/5" : ""
      }`}
    >
      {/* Metadata */}
      <div className="flex items-center gap-3 text-sm text-muted-foreground mb-2">
        <span className="flex items-center gap-1">
          <Hash className="w-3 h-3" />
          {observation.sourceMetadata.channel_name || "unknown"}
        </span>
        <span className="flex items-center gap-1">
          <User className="w-3 h-3" />
          {observation.sourceMetadata.author_name || "unknown"}
        </span>
        <span className="flex items-center gap-1">
          <Clock className="w-3 h-3" />
          {new Date(observation.observedAt).toLocaleString()}
        </span>
      </div>

      {/* Content */}
      <p className="text-sm mb-3 whitespace-pre-wrap">{observation.content}</p>

      {/* Reasoning */}
      {observation.classificationReasoning && (
        <p className="text-xs text-muted-foreground mb-3 italic">
          Why: {observation.classificationReasoning}
        </p>
      )}

      {/* Actions */}
      <div className="flex items-center gap-2">
        {!isReviewed ? (
          <>
            <Button
              size="sm"
              variant="outline"
              onClick={() => onFeedback(observation.id, "confirmed")}
              disabled={feedbackLoading}
              className="text-green-600 hover:text-green-700 hover:bg-green-50"
            >
              <ThumbsUp className="w-4 h-4 mr-1" />
              Good catch
            </Button>

            {showRecategorize ? (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={feedbackLoading}
                    className="text-red-600 hover:text-red-700 hover:bg-red-50"
                  >
                    <ThumbsDown className="w-4 h-4 mr-1" />
                    Wrong
                    <ChevronDown className="w-3 h-3 ml-1" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                  <DropdownMenuItem
                    onClick={() =>
                      onFeedback(
                        observation.id,
                        "corrected_to_very_interesting"
                      )
                    }
                  >
                    Should be: Very Interesting
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onClick={() =>
                      onFeedback(observation.id, "corrected_to_interesting")
                    }
                  >
                    Should be: Interesting
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onClick={() =>
                      onFeedback(observation.id, "corrected_to_not_interesting")
                    }
                  >
                    Should be: Not Interesting
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            ) : (
              <Button
                size="sm"
                variant="outline"
                onClick={() =>
                  onFeedback(observation.id, "corrected_to_not_interesting")
                }
                disabled={feedbackLoading}
                className="text-red-600 hover:text-red-700 hover:bg-red-50"
              >
                <ThumbsDown className="w-4 h-4 mr-1" />
                Not relevant
              </Button>
            )}
          </>
        ) : (
          <Badge variant="outline" className="text-green-600">
            Reviewed: {observation.userFeedback}
          </Badge>
        )}

        {observation.needsReview && !isReviewed && (
          <Badge variant="outline" className="text-orange-500 ml-auto">
            Low confidence ({((observation.classificationConfidence || 0) * 100).toFixed(0)}%)
          </Badge>
        )}
      </div>
    </Card>
  );
};

export default AgentDigestPage;
