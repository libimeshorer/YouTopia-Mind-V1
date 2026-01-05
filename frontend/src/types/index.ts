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

/**
 * Training stats for crystal calculation
 * Note: The old TrainingStatus with progress/thresholds/achievements has been removed.
 * Crystal count is now calculated client-side based on these counts.
 * @see useCrystals hook for crystal calculation logic
 */
export interface TrainingStats {
  documentsCount: number;
  insightsCount: number;
  integrationsCount: number;
  dataPoints: number;
  lastActivity?: string;
}

// Chat types
export interface ChatSession {
  id: number;
  cloneId: string;
  startedAt: string;
  lastMessageAt: string;
  messageCount: number;
  status: 'active' | 'closed';
}

export interface ChatMessage {
  id: string;
  sessionId: number;
  role: 'external_user' | 'clone';
  content: string;
  createdAt: string;
  externalUserName?: string;
  ragContext?: {
    chunks: Array<{
      content: string;
      score: number;
      metadata?: Record<string, unknown>;
    }>;
  };
  tokensUsed?: number;
  responseTimeMs?: number;
  feedbackRating?: number; // -1 (thumbs down), 1 (thumbs up), or null
}

export interface SendMessageRequest {
  content: string;
  externalUserName?: string;
}

export interface SendMessageResponse {
  userMessage: ChatMessage;
  cloneMessage: ChatMessage;
}

