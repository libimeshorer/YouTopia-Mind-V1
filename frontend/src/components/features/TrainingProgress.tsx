import { TrainingStatus } from "@/types";
import { Progress } from "@/components/ui/progress";
import { CheckCircle2, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";

interface TrainingProgressProps {
  trainingStatus: TrainingStatus;
  onComplete?: () => void;
}

export const TrainingProgress = ({ trainingStatus, onComplete }: TrainingProgressProps) => {
  const [showCelebration, setShowCelebration] = useState(false);

  useEffect(() => {
    if (trainingStatus.isComplete && !showCelebration) {
      setShowCelebration(true);
      const timer = setTimeout(() => {
        setShowCelebration(false);
        onComplete?.();
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [trainingStatus.isComplete, showCelebration, onComplete]);

  const getMilestoneMessage = () => {
    if (trainingStatus.progress >= 100) return "🎉 Training Complete!";
    if (trainingStatus.progress >= 75) return "Almost there! You're doing great!";
    if (trainingStatus.progress >= 50) return "Halfway there! Keep going!";
    if (trainingStatus.progress >= 25) return "Great start! You're making progress!";
    return "Let's get started!";
  };

  const getAchievements = () => {
    const achievements = [];
    if (trainingStatus.documentsCount > 0) {
      achievements.push("📄 First Document");
    }
    if (trainingStatus.documentsCount >= trainingStatus.thresholds.minDocuments) {
      achievements.push("📚 Document Master");
    }
    if (trainingStatus.insightsCount > 0) {
      achievements.push("💡 First Insight");
    }
    if (trainingStatus.insightsCount >= trainingStatus.thresholds.minInsights) {
      achievements.push("🧠 Insight Collector");
    }
    if (trainingStatus.integrationsCount > 0) {
      achievements.push("🔗 First Connection");
    }
    if (trainingStatus.integrationsCount >= trainingStatus.thresholds.minIntegrations) {
      achievements.push("🌐 Integration Expert");
    }
    return achievements;
  };

  return (
    <div className="space-y-4">
      {showCelebration && (
        <div className="relative p-6 bg-gradient-to-r from-primary/20 to-primary/10 rounded-lg border-2 border-primary/50 animate-pulse">
          <div className="flex items-center justify-center gap-2">
            <Sparkles className="w-6 h-6 text-primary animate-spin" />
            <h3 className="text-2xl font-bold text-primary">🎉 Training Complete!</h3>
            <Sparkles className="w-6 h-6 text-primary animate-spin" />
          </div>
          <p className="text-center text-muted-foreground mt-2">
            Your clone is ready! Redirecting to activity page...
          </p>
        </div>
      )}

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">Training Progress</h3>
          <span className="text-2xl font-bold text-primary">{Math.round(trainingStatus.progress)}%</span>
        </div>
        <Progress value={trainingStatus.progress} className="h-3" />
        <p className="text-sm text-muted-foreground text-center">{getMilestoneMessage()}</p>
      </div>

      <div className="grid grid-cols-3 gap-4 text-center">
        <div className="p-4 bg-muted rounded-lg">
          <div className="text-2xl font-bold text-primary">{trainingStatus.documentsCount}</div>
          <div className="text-xs text-muted-foreground mt-1">
            / {trainingStatus.thresholds.minDocuments} Documents
          </div>
        </div>
        <div className="p-4 bg-muted rounded-lg">
          <div className="text-2xl font-bold text-primary">{trainingStatus.insightsCount}</div>
          <div className="text-xs text-muted-foreground mt-1">
            / {trainingStatus.thresholds.minInsights} Insights
          </div>
        </div>
        <div className="p-4 bg-muted rounded-lg">
          <div className="text-2xl font-bold text-primary">{trainingStatus.integrationsCount}</div>
          <div className="text-xs text-muted-foreground mt-1">
            / {trainingStatus.thresholds.minIntegrations} Integrations
          </div>
        </div>
      </div>

      {getAchievements().length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-semibold">Achievements Unlocked</h4>
          <div className="flex flex-wrap gap-2">
            {getAchievements().map((achievement, index) => (
              <div
                key={index}
                className="flex items-center gap-1 px-3 py-1 bg-primary/10 text-primary rounded-full text-sm"
              >
                <CheckCircle2 className="w-4 h-4" />
                {achievement}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

