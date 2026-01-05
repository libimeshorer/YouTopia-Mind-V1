import { Card, CardContent } from "@/components/ui/card";
// import { FileText, Lightbulb, Link2 } from "lucide-react";
import { Clock } from "lucide-react";
import { CrystalStash } from "./CrystalStash";

interface StatsCardsProps {
  documentsCount: number;
  insightsCount: number;
  integrationsCount: number;
  lastActivity?: string;
}

export const StatsCards = ({
  documentsCount,
  insightsCount,
  integrationsCount,
  lastActivity,
}: StatsCardsProps) => {
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

  // const stats = [
  //   {
  //     icon: FileText,
  //     label: "Documents",
  //     value: documentsCount,
  //   },
  //   {
  //     icon: Lightbulb,
  //     label: "Insights",
  //     value: insightsCount,
  //   },
  //   {
  //     icon: Link2,
  //     label: "Integrations",
  //     value: integrationsCount,
  //   },
  // ];

  return (
    <div className="space-y-6">
      {/* Main Stats Grid - Commented out, may restore later */}
      {/* <div className="grid grid-cols-3 gap-4">
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
                    <div className="text-xl sm:text-2xl font-bold text-muted-foreground">
                      {stat.value}
                    </div>
                  </div>
                  <div className="text-xs text-muted-foreground pl-4 sm:pl-5">
                    {stat.label}
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div> */}

      {/* Crystal Stash - replaces Progress Card */}
      <CrystalStash
        documentsCount={documentsCount}
        insightsCount={insightsCount}
        integrationsCount={integrationsCount}
      />

      {/* Last Activity */}
      {lastActivity && (
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-sm">
              <Clock className="w-4 h-4 text-muted-foreground" />
              <span className="text-muted-foreground">Last synced:</span>
              <span className="font-medium">
                {formatLastActivity(lastActivity)}
              </span>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};
