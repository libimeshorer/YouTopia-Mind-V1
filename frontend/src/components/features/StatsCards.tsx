import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { 
  FileText, 
  Lightbulb, 
  Link2, 
  Clock, 
  Sparkles,
  TrendingUp,
  Zap
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { ROUTES } from "@/constants/routes";

interface StatsCardsProps {
  documentsCount: number;
  insightsCount: number;
  integrationsCount: number;
  lastActivity?: string;
  progress: number;
}

export const StatsCards = ({
  documentsCount,
  insightsCount,
  integrationsCount,
  lastActivity,
  progress,
}: StatsCardsProps) => {
  const navigate = useNavigate();

  const formatLastActivity = (dateString?: string) => {
    if (!dateString) return "No activity yet";
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

  const getNextAction = () => {
    if (documentsCount === 0) return "Upload your first document";
    if (insightsCount === 0) return "Record your first insight";
    if (integrationsCount === 0) return "Connect your first integration";
    if (progress < 100) return "Continue training";
    return "View activity";
  };

  const handleContinueTraining = () => {
    if (progress >= 100) {
      navigate(ROUTES.ACTIVITY);
    } else {
      // Scroll to first incomplete section
      const sections = document.querySelectorAll('[data-training-section]');
      for (const section of sections) {
        if (section.getAttribute('data-complete') === 'false') {
          section.scrollIntoView({ behavior: 'smooth', block: 'start' });
          break;
        }
      }
    }
  };

  const stats = [
    {
      icon: FileText,
      label: "Documents",
      value: documentsCount,
    },
    {
      icon: Lightbulb,
      label: "Insights",
      value: insightsCount,
    },
    {
      icon: Link2,
      label: "Integrations",
      value: integrationsCount,
    },
  ];

  return (
    <div className="space-y-6">
      {/* Main Stats Grid */}
      <div className="grid grid-cols-3 gap-4">
        {stats.map((stat, index) => {
          const Icon = stat.icon;
          return (
            <Card
              key={index}
              className="bg-gradient-to-r from-primary/10 to-primary/5 border-primary/20 border-2 hover:border-primary/30 transition-all"
            >
              <CardContent className="p-4">
                <div className="space-y-2">
                  <div className="flex items-center gap-2 sm:gap-3">
                    <Icon className="w-4 h-4 sm:w-5 sm:h-5 text-primary flex-shrink-0" />
                    <div className="text-xl sm:text-2xl font-bold text-muted-foreground">{stat.value}</div>
                  </div>
                  <div className="text-xs text-muted-foreground pl-4 sm:pl-5">
                    {stat.label}
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Progress Card */}
      <Card className="bg-gradient-to-r from-primary/10 to-primary/5 border-primary/20">
        <CardContent className="p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-primary" />
              <span className="font-semibold">Training Progress</span>
            </div>
            <span className="text-2xl font-bold text-primary">{Math.round(progress)}%</span>
          </div>
          <div className="w-full bg-muted rounded-full h-3 mb-4">
            <div
              className="bg-gradient-primary h-3 rounded-full transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>
          {progress < 100 && (
            <p className="text-sm text-muted-foreground mb-4">
              {getNextAction()}
            </p>
          )}
          <Button
            onClick={handleContinueTraining}
            className="w-full bg-gradient-primary hover:shadow-glow"
          >
            {progress >= 100 ? (
              <>
                <Zap className="w-4 h-4 mr-2" />
                View Activity
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4 mr-2" />
                Continue Training
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      {/* Last Activity */}
      {lastActivity && (
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-sm">
              <Clock className="w-4 h-4 text-muted-foreground" />
              <span className="text-muted-foreground">Last synced:</span>
              <span className="font-medium">{formatLastActivity(lastActivity)}</span>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

