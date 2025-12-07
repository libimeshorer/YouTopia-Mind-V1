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

export interface Document {
  id: string;
  name: string;
  size: number;
  type: string;
  status: "pending" | "processing" | "complete" | "error";
  uploadedAt: string;
  chunksExtracted?: number;
  errorMessage?: string;
  previewUrl?: string;
}

export interface Insight {
  id: string;
  content: string;
  type: "voice" | "text";
  audioUrl?: string; // For voice notes
  transcriptionId?: string; // Reference to transcription
  createdAt: string;
  updatedAt: string;
}

export interface CloneAction {
  id: string;
  type: "task" | "decision" | "recommendation" | "other";
  description: string;
  platform?: "slack" | "email" | "linkedin" | "x" | "other";
  timestamp: string;
  outcome?: string;
  relatedConversationId?: string;
  metadata?: Record<string, unknown>;
}

export interface Conversation {
  id: string;
  platform: "slack" | "email" | "linkedin" | "x" | "granola" | "fathom" | "other";
  participants: string[];
  preview: string;
  messageCount?: number;
  timestamp: string;
  lastMessageAt: string;
  metadata?: Record<string, unknown>;
}

export interface Integration {
  id: string;
  type: "slack" | "email" | "linkedin" | "x" | "google_drive" | "granola" | "fathom" | "other";
  name: string;
  category: "communication" | "storage" | "ai_agent";
  status: "connected" | "disconnected" | "error";
  lastSyncAt?: string;
  dataSyncedCount?: number;
  icon?: string;
}

export interface TrainingStatus {
  isComplete: boolean;
  progress: number; // 0-100
  documentsCount: number;
  insightsCount: number;
  integrationsCount: number;
  thresholds: {
    minDocuments: number;
    minInsights: number;
    minIntegrations: number;
  };
  achievements: string[];
}

