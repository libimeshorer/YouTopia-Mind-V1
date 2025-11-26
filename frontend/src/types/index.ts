/**
 * Shared TypeScript types
 */

export interface Clone {
  id: string;
  name: string;
  description?: string;
  status: "not_started" | "in_progress" | "complete";
  createdAt: string;
  updatedAt: string;
}

export interface PersonalityProfile {
  communicationStyle: {
    formalityLevel: string;
    sentenceLengthAvg: number;
    decisionMakingStyle: string;
    detailLevel: string;
    directness: string;
  };
  toneCharacteristics: Record<string, number>;
  knowledgeDomains: string[];
}

export interface IngestionStatus {
  status: "pending" | "processing" | "complete" | "error";
  chunksIngested: number;
  sourceType: "document" | "slack" | "email";
  sourceName: string;
}

export interface Connection {
  id: string;
  type: "slack" | "email";
  status: "connected" | "disconnected" | "error";
  lastSyncAt?: string;
}

