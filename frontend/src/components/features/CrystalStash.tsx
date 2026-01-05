import { Card, CardContent } from "@/components/ui/card";
import { useCrystals } from "@/hooks/useCrystals";

// Import crystal images
import crystalPile1 from "@/assets/crystals/crystal-pile-1.png";
import crystalPile2 from "@/assets/crystals/crystal-pile-2.png";
import crystalPile3 from "@/assets/crystals/crystal-pile-3.png";
import crystalPile4 from "@/assets/crystals/crystal-pile-4.png";
import crystalPile5 from "@/assets/crystals/crystal-pile-5.png";
import crystalPile6 from "@/assets/crystals/crystal-pile-6.png";
import crystalPile7 from "@/assets/crystals/crystal-pile-7.png";
import crystalPile8 from "@/assets/crystals/crystal-pile-8.png";

// Map image filenames to imports
const CRYSTAL_IMAGES: Record<string, string> = {
  "crystal-pile-1.png": crystalPile1,
  "crystal-pile-2.png": crystalPile2,
  "crystal-pile-3.png": crystalPile3,
  "crystal-pile-4.png": crystalPile4,
  "crystal-pile-5.png": crystalPile5,
  "crystal-pile-6.png": crystalPile6,
  "crystal-pile-7.png": crystalPile7,
  "crystal-pile-8.png": crystalPile8,
};

interface CrystalStashProps {
  documentsCount: number;
  insightsCount: number;
  integrationsCount: number;
}

export const CrystalStash = ({
  documentsCount,
  insightsCount,
  integrationsCount,
}: CrystalStashProps) => {
  const { crystalCount, crystalImage, totalItems, nextMilestone } = useCrystals(
    documentsCount,
    insightsCount,
    integrationsCount
  );

  const imageSrc = crystalImage ? CRYSTAL_IMAGES[crystalImage] : null;

  return (
    <Card className="bg-gradient-to-r from-primary/10 to-primary/5 border-primary/20">
      <CardContent className="p-6">
        <div className="text-center space-y-4">
          {/* Header */}
          <h3 className="font-semibold text-lg">Your Knowledge Crystals</h3>

          {/* Crystal Image */}
          <div className="relative flex items-center justify-center min-h-[160px]">
            {imageSrc ? (
              <img
                src={imageSrc}
                alt={`${crystalCount} crystal${crystalCount !== 1 ? "s" : ""}`}
                className="max-h-[160px] w-auto object-contain drop-shadow-lg transition-all duration-500"
              />
            ) : (
              <div className="flex flex-col items-center justify-center text-muted-foreground">
                <div className="w-16 h-16 rounded-full bg-muted/50 flex items-center justify-center mb-2">
                  <span className="text-2xl">?</span>
                </div>
                <p className="text-sm">Add your first item to earn a crystal</p>
              </div>
            )}
          </div>

          {/* Crystal Count */}
          <div className="space-y-1">
            <p className="text-2xl font-bold text-primary">
              {crystalCount} crystal{crystalCount !== 1 ? "s" : ""}
            </p>
            <p className="text-xs text-muted-foreground">
              {documentsCount} doc{documentsCount !== 1 ? "s" : ""} ·{" "}
              {insightsCount} insight{insightsCount !== 1 ? "s" : ""} ·{" "}
              {integrationsCount} integration{integrationsCount !== 1 ? "s" : ""}
            </p>
          </div>

          {/* Next Milestone */}
          {nextMilestone && crystalCount < 8 && (
            <p className="text-sm text-muted-foreground">
              {nextMilestone.remaining} more item
              {nextMilestone.remaining !== 1 ? "s" : ""} to earn your next
              crystal
            </p>
          )}

          {crystalCount >= 8 && (
            <p className="text-sm text-primary font-medium">
              Maximum crystal collection reached!
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );
};
