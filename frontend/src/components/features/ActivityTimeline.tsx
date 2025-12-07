import { CloneAction, Conversation } from "@/types";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  CheckCircle2,
  MessageSquare,
  Mail,
  Linkedin,
  Twitter,
  Video,
  ArrowRight,
  Loader2,
} from "lucide-react";

interface ActivityTimelineProps {
  actions: CloneAction[];
  conversations: Conversation[];
  isLoading?: boolean;
}

const platformIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  slack: MessageSquare,
  email: Mail,
  linkedin: Linkedin,
  x: Twitter,
  granola: Video,
  fathom: Video,
  other: MessageSquare,
};

const actionTypeColors: Record<string, string> = {
  task: "bg-blue-500",
  decision: "bg-green-500",
  recommendation: "bg-purple-500",
  other: "bg-gray-500",
};

export const ActivityTimeline = ({ actions, conversations, isLoading }: ActivityTimelineProps) => {
  const formatTimestamp = (timestamp: string) => {
    try {
      const date = new Date(timestamp);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffMins = Math.floor(diffMs / 60000);
      const diffHours = Math.floor(diffMs / 3600000);
      const diffDays = Math.floor(diffMs / 86400000);

      if (diffMins < 1) return "Just now";
      if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? "s" : ""} ago`;
      if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? "s" : ""} ago`;
      if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? "s" : ""} ago`;
      return date.toLocaleDateString();
    } catch {
      return new Date(timestamp).toLocaleString();
    }
  };

  const groupByDate = <T extends { timestamp: string }>(items: T[]) => {
    const groups: Record<string, T[]> = {};
    items.forEach((item) => {
      const date = new Date(item.timestamp).toLocaleDateString();
      if (!groups[date]) {
        groups[date] = [];
      }
      groups[date].push(item);
    });
    return groups;
  };

  const actionGroups = groupByDate(actions);
  const conversationGroups = groupByDate(conversations);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Clone Actions Section */}
      <div>
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <CheckCircle2 className="w-5 h-5" />
          Clone Actions
        </h3>
        {actions.length === 0 ? (
          <Card>
            <CardContent className="py-8 text-center text-muted-foreground">
              No actions recorded yet
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-6">
            {Object.entries(actionGroups)
              .sort(([a], [b]) => new Date(b).getTime() - new Date(a).getTime())
              .map(([date, dateActions]) => (
                <div key={date} className="space-y-3">
                  <h4 className="text-sm font-medium text-muted-foreground sticky top-0 bg-background py-2">
                    {date}
                  </h4>
                  {dateActions.map((action) => (
                    <Card key={action.id} className="hover:bg-muted/50 transition-colors">
                      <CardContent className="p-4">
                        <div className="flex items-start gap-3">
                          <div
                            className={`w-2 h-2 rounded-full mt-2 ${actionTypeColors[action.type] || actionTypeColors.other}`}
                          />
                          <div className="flex-1 space-y-2">
                            <div className="flex items-center gap-2 flex-wrap">
                              <Badge variant="secondary" className="capitalize">
                                {action.type}
                              </Badge>
                              {action.platform && (
                                <Badge variant="outline" className="text-xs">
                                  {action.platform}
                                </Badge>
                              )}
                              <span className="text-xs text-muted-foreground">
                                {formatTimestamp(action.timestamp)}
                              </span>
                            </div>
                            <p className="text-sm">{action.description}</p>
                            {action.outcome && (
                              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                <ArrowRight className="w-3 h-3" />
                                <span>{action.outcome}</span>
                              </div>
                            )}
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              ))}
          </div>
        )}
      </div>

      {/* Conversations Section */}
      <div>
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <MessageSquare className="w-5 h-5" />
          Conversations
        </h3>
        {conversations.length === 0 ? (
          <Card>
            <CardContent className="py-8 text-center text-muted-foreground">
              No conversations recorded yet
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-6">
            {Object.entries(conversationGroups)
              .sort(([a], [b]) => new Date(b).getTime() - new Date(a).getTime())
              .map(([date, dateConversations]) => (
                <div key={date} className="space-y-3">
                  <h4 className="text-sm font-medium text-muted-foreground sticky top-0 bg-background py-2">
                    {date}
                  </h4>
                  {dateConversations.map((conversation) => {
                    const PlatformIcon = platformIcons[conversation.platform] || platformIcons.other;
                    return (
                      <Card key={conversation.id} className="hover:bg-muted/50 transition-colors">
                        <CardContent className="p-4">
                          <div className="flex items-start gap-3">
                            <div className="p-2 rounded-lg bg-muted">
                              <PlatformIcon className="w-4 h-4" />
                            </div>
                            <div className="flex-1 space-y-2">
                              <div className="flex items-center gap-2 flex-wrap">
                                <Badge variant="outline" className="capitalize">
                                  {conversation.platform}
                                </Badge>
                                {conversation.messageCount && (
                                  <Badge variant="secondary" className="text-xs">
                                    {conversation.messageCount} messages
                                  </Badge>
                                )}
                                <span className="text-xs text-muted-foreground">
                                  {formatTimestamp(conversation.timestamp)}
                                </span>
                              </div>
                              <div className="text-xs text-muted-foreground">
                                {conversation.participants.join(", ")}
                              </div>
                              <p className="text-sm overflow-hidden text-ellipsis line-clamp-2">{conversation.preview}</p>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    );
                  })}
                </div>
              ))}
          </div>
        )}
      </div>
    </div>
  );
};

