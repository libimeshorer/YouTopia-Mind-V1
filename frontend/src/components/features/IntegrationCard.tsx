import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Integration } from "@/types";
import { apiClient } from "@/api/client";
import { useToast } from "@/hooks/use-toast";
import { 
  MessageSquare, 
  Mail, 
  Linkedin, 
  Twitter, 
  HardDrive, 
  Video, 
  CheckCircle2, 
  XCircle, 
  AlertCircle,
  Loader2,
  RefreshCw
} from "lucide-react";

interface IntegrationCardProps {
  integration: Integration;
}

const integrationIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  slack: MessageSquare,
  email: Mail,
  linkedin: Linkedin,
  x: Twitter,
  google_drive: HardDrive,
  granola: Video,
  fathom: Video,
  other: Video,
};

const integrationNames: Record<string, string> = {
  slack: "Slack",
  email: "Email",
  linkedin: "LinkedIn",
  x: "X (Twitter)",
  google_drive: "Google Drive",
  granola: "Granola",
  fathom: "Fathom",
  other: "Other",
};

export const IntegrationCard = ({ integration }: IntegrationCardProps) => {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const Icon = integrationIcons[integration.type] || integrationIcons.other;
  const name = integrationNames[integration.type] || integration.name;

  const connectMutation = useMutation({
    mutationFn: () => apiClient.integrations.connect(integration.type),
    onSuccess: (data) => {
      if (data.authUrl) {
        window.location.href = data.authUrl;
      } else {
        queryClient.invalidateQueries({ queryKey: ["integrations"] });
        toast({
          title: "Connected",
          description: `${name} has been connected successfully`,
        });
      }
    },
    onError: () => {
      toast({
        title: "Connection Failed",
        description: `Failed to connect ${name}`,
        variant: "destructive",
      });
    },
  });

  const disconnectMutation = useMutation({
    mutationFn: () => apiClient.integrations.disconnect(integration.type),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["integrations"] });
      toast({
        title: "Disconnected",
        description: `${name} has been disconnected`,
      });
    },
    onError: () => {
      toast({
        title: "Disconnect Failed",
        description: `Failed to disconnect ${name}`,
        variant: "destructive",
      });
    },
  });

  const syncMutation = useMutation({
    mutationFn: () => apiClient.integrations.sync(integration.type),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["integrations"] });
      toast({
        title: "Sync Started",
        description: `Syncing data from ${name}...`,
      });
    },
    onError: () => {
      toast({
        title: "Sync Failed",
        description: `Failed to sync ${name}`,
        variant: "destructive",
      });
    },
  });

  const getStatusIcon = () => {
    switch (integration.status) {
      case "connected":
        return <CheckCircle2 className="w-5 h-5 text-green-500" />;
      case "error":
        return <AlertCircle className="w-5 h-5 text-red-500" />;
      default:
        return <XCircle className="w-5 h-5 text-muted-foreground" />;
    }
  };

  const getStatusBadge = () => {
    switch (integration.status) {
      case "connected":
        return <Badge className="bg-green-500">Connected</Badge>;
      case "error":
        return <Badge variant="destructive">Error</Badge>;
      default:
        return <Badge variant="secondary">Disconnected</Badge>;
    }
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return "Never";
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins} minutes ago`;
    if (diffHours < 24) return `${diffHours} hours ago`;
    if (diffDays < 7) return `${diffDays} days ago`;
    return date.toLocaleDateString();
  };

  return (
    <Card className="hover:border-primary/30 transition-all">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-muted">
              <Icon className="w-6 h-6" />
            </div>
            <div>
              <CardTitle className="text-lg">{name}</CardTitle>
              <CardDescription className="capitalize">{integration.category}</CardDescription>
            </div>
          </div>
          {getStatusIcon()}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center justify-between">
          {getStatusBadge()}
          {integration.dataSyncedCount !== undefined && (
            <span className="text-sm text-muted-foreground">
              {integration.dataSyncedCount.toLocaleString()} items synced
            </span>
          )}
        </div>

        {integration.lastSyncAt && (
          <div className="text-sm text-muted-foreground">
            Last synced: {formatDate(integration.lastSyncAt)}
          </div>
        )}

        <div className="flex gap-2">
          {integration.status === "connected" ? (
            <>
              <Button
                variant="outline"
                size="sm"
                onClick={() => syncMutation.mutate()}
                disabled={syncMutation.isPending}
                className="flex-1"
              >
                {syncMutation.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Syncing...
                  </>
                ) : (
                  <>
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Sync Now
                  </>
                )}
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={() => disconnectMutation.mutate()}
                disabled={disconnectMutation.isPending}
              >
                {disconnectMutation.isPending ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  "Disconnect"
                )}
              </Button>
            </>
          ) : (
            <Button
              onClick={() => connectMutation.mutate()}
              disabled={connectMutation.isPending}
              className="w-full"
            >
              {connectMutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Connecting...
                </>
              ) : (
                "Connect"
              )}
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

