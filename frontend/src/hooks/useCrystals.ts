/**
 * Hook to calculate crystal count based on training activity
 *
 * TODO: Revisit this logic and improve it based on user feedback (espcially CrystalCount and milestones calc).
 * Crystal milestones are earned by:
 * 1. Starting a new category (first doc, first insight, first integration) = +1 crystal each
 * 2. Reaching total item thresholds (3, 6, 10, 15, 22, 30, 40+ items)
 */

// Thresholds for earning crystals based on total items
const VOLUME_THRESHOLDS = [3, 6, 10, 15, 22, 30, 40];

// Crystal pile images (1-8 crystals)
const CRYSTAL_IMAGES = [
  null, // 0 crystals - no image
  "crystal-pile-1.png",
  "crystal-pile-2.png",
  "crystal-pile-3.png",
  "crystal-pile-4.png",
  "crystal-pile-5.png",
  "crystal-pile-6.png",
  "crystal-pile-7.png",
  "crystal-pile-8.png",
];

export interface CrystalStatus {
  crystalCount: number;
  crystalImage: string | null;
  totalItems: number;
  categoriesStarted: number;
  nextMilestone: {
    threshold: number;
    remaining: number;
  } | null;
}

/**
 * Calculate the number of crystals earned and which image to display
 */
export function calculateCrystals(
  documentsCount: number,
  insightsCount: number,
  integrationsCount: number
): CrystalStatus {
  const totalItems = documentsCount + insightsCount + integrationsCount;

  // Count unique categories started (first-time bonuses)
  const categoriesStarted =
    (documentsCount > 0 ? 1 : 0) +
    (insightsCount > 0 ? 1 : 0) +
    (integrationsCount > 0 ? 1 : 0);

  // Calculate crystals from volume thresholds
  let volumeCrystals = 0;
  for (const threshold of VOLUME_THRESHOLDS) {
    if (totalItems >= threshold) {
      volumeCrystals++;
    }
  }

  // Total crystals = categories started + volume-based crystals
  // But cap at 8 (max image we have)
  const crystalCount = Math.min(8, categoriesStarted + volumeCrystals);

  // Determine the crystal image
  const crystalImage = crystalCount > 0 ? CRYSTAL_IMAGES[crystalCount] : null;

  // Calculate next milestone
  let nextMilestone: CrystalStatus["nextMilestone"] = null;

  if (crystalCount < 8) {
    // First check if they can earn a category crystal
    if (categoriesStarted < 3) {
      const missingCategories = [];
      if (documentsCount === 0) missingCategories.push("document");
      if (insightsCount === 0) missingCategories.push("insight");
      if (integrationsCount === 0) missingCategories.push("integration");

      // Show the smallest volume threshold they haven't reached yet
      const nextVolumeThreshold = VOLUME_THRESHOLDS.find(t => totalItems < t);
      if (nextVolumeThreshold) {
        nextMilestone = {
          threshold: nextVolumeThreshold,
          remaining: nextVolumeThreshold - totalItems,
        };
      }
    } else {
      // All categories started, just volume thresholds left
      const nextVolumeThreshold = VOLUME_THRESHOLDS.find(t => totalItems < t);
      if (nextVolumeThreshold) {
        nextMilestone = {
          threshold: nextVolumeThreshold,
          remaining: nextVolumeThreshold - totalItems,
        };
      }
    }
  }

  return {
    crystalCount,
    crystalImage,
    totalItems,
    categoriesStarted,
    nextMilestone,
  };
}

/**
 * React hook to use crystal status with training stats
 */
export function useCrystals(
  documentsCount: number,
  insightsCount: number,
  integrationsCount: number
): CrystalStatus {
  return calculateCrystals(documentsCount, insightsCount, integrationsCount);
}
