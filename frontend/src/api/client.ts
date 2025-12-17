/**
 * API client for backend communication
 */

import { Document, Insight, CloneAction, Conversation, Integration, TrainingStatus } from "@/types";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

// Log API URL for debugging (only in development)
if (import.meta.env.DEV) {
  console.log("🔗 API Base URL:", API_BASE_URL);
  if (!import.meta.env.VITE_API_URL) {
    console.warn("⚠️ VITE_API_URL not set - using default localhost:8000");
    console.warn("   Set VITE_API_URL environment variable to your backend URL");
  }
}

export const apiClient = {
  baseURL: API_BASE_URL,
  
  async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;
    
    const response = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.statusText}`);
    }

    return response.json();
  },

  get<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: "GET" });
  },

  post<T>(endpoint: string, data?: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: "POST",
      body: data ? JSON.stringify(data) : undefined,
    });
  },

  put<T>(endpoint: string, data?: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: "PUT",
      body: data ? JSON.stringify(data) : undefined,
    });
  },

  delete<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: "DELETE" });
  },

  // Documents endpoints
  documents: {
    list: () => apiClient.get<Document[]>("/api/clone/documents"),
    upload: async (files: File[]) => {
      const formData = new FormData();
      files.forEach((file) => formData.append("files", file));
      
      try {
        const response = await fetch(`${API_BASE_URL}/api/clone/documents`, {
          method: "POST",
          body: formData,
          // Don't set Content-Type header - browser will set it with boundary for FormData
        });

        if (!response.ok) {
          const errorText = await response.text().catch(() => response.statusText);
          throw new Error(`API Error (${response.status}): ${errorText || response.statusText}`);
        }

        return await response.json();
      } catch (error) {
        // Handle network errors (failed to fetch)
        if (error instanceof TypeError && error.message.includes("fetch")) {
          const errorMsg = API_BASE_URL.includes("localhost") 
            ? `Failed to connect to backend at ${API_BASE_URL}. If deployed, set VITE_API_URL environment variable to your backend URL (e.g., https://api.you-topia.ai)`
            : `Failed to connect to backend at ${API_BASE_URL}. Please verify the backend is running and accessible.`;
          throw new Error(errorMsg);
        }
        // Re-throw other errors as-is
        throw error;
      }
    },
    get: (id: string) => apiClient.get<Document>(`/api/clone/documents/${id}`),
    preview: (id: string) => apiClient.get<{ url: string }>(`/api/clone/documents/${id}/preview`),
    delete: (id: string) => apiClient.delete(`/api/clone/documents/${id}`),
    status: (id: string) => apiClient.get<Document>(`/api/clone/documents/${id}/status`),
    search: (query: string) => apiClient.get<Document[]>(`/api/clone/documents/search?q=${encodeURIComponent(query)}`),
  },

  // Insights endpoints
  insights: {
    list: () => apiClient.get<Insight[]>("/api/clone/insights"),
    create: (content: string) => apiClient.post<Insight>("/api/clone/insights", { content }),
    uploadVoice: async (audioBlob: Blob) => {
      const formData = new FormData();
      formData.append("audio", audioBlob, "recording.webm");
      
      try {
        const response = await fetch(`${API_BASE_URL}/api/clone/insights/voice`, {
          method: "POST",
          body: formData,
        });

        if (!response.ok) {
          const errorText = await response.text().catch(() => response.statusText);
          throw new Error(`API Error (${response.status}): ${errorText || response.statusText}`);
        }

        return await response.json();
      } catch (error) {
        if (error instanceof TypeError && error.message.includes("fetch")) {
          const errorMsg = API_BASE_URL.includes("localhost") 
            ? `Failed to connect to backend at ${API_BASE_URL}. If deployed, set VITE_API_URL environment variable to your backend URL (e.g., https://api.you-topia.ai)`
            : `Failed to connect to backend at ${API_BASE_URL}. Please verify the backend is running and accessible.`;
          throw new Error(errorMsg);
        }
        throw error;
      }
    },
    update: (id: string, content: string) => apiClient.put<Insight>(`/api/clone/insights/${id}`, { content }),
    delete: (id: string) => apiClient.delete(`/api/clone/insights/${id}`),
    search: (query: string) => apiClient.get<Insight[]>(`/api/clone/insights/search?q=${encodeURIComponent(query)}`),
  },

  // Integrations endpoints
  integrations: {
    list: () => apiClient.get<Integration[]>("/api/clone/integrations"),
    connect: (type: string) => apiClient.post<{ authUrl: string }>(`/api/clone/integrations/${type}/connect`),
    disconnect: (type: string) => apiClient.post(`/api/clone/integrations/${type}/disconnect`),
    status: (type: string) => apiClient.get<Integration>(`/api/clone/integrations/${type}/status`),
    sync: (type: string) => apiClient.post(`/api/clone/integrations/${type}/sync`),
  },

  // Activity endpoints
  activity: {
    actions: (filters?: { type?: string; platform?: string; startDate?: string; endDate?: string; page?: number }) => {
      const params = new URLSearchParams();
      if (filters?.type) params.append("type", filters.type);
      if (filters?.platform) params.append("platform", filters.platform);
      if (filters?.startDate) params.append("startDate", filters.startDate);
      if (filters?.endDate) params.append("endDate", filters.endDate);
      if (filters?.page) params.append("page", filters.page.toString());
      return apiClient.get<{ items: CloneAction[]; total: number; page: number }>(`/api/clone/actions?${params.toString()}`);
    },
    conversations: (filters?: { platform?: string; participant?: string; startDate?: string; endDate?: string; page?: number }) => {
      const params = new URLSearchParams();
      if (filters?.platform) params.append("platform", filters.platform);
      if (filters?.participant) params.append("participant", filters.participant);
      if (filters?.startDate) params.append("startDate", filters.startDate);
      if (filters?.endDate) params.append("endDate", filters.endDate);
      if (filters?.page) params.append("page", filters.page.toString());
      return apiClient.get<{ items: Conversation[]; total: number; page: number }>(`/api/clone/conversations?${params.toString()}`);
    },
    search: (query: string) => apiClient.get<{ actions: CloneAction[]; conversations: Conversation[] }>(`/api/clone/activity/search?q=${encodeURIComponent(query)}`),
    get: (id: string) => apiClient.get<CloneAction | Conversation>(`/api/clone/activity/${id}`),
  },

  // Training endpoints
  training: {
    status: () => apiClient.get<TrainingStatus>("/api/clone/training/status"),
    complete: () => apiClient.post<TrainingStatus>("/api/clone/training/complete"),
    stats: () => apiClient.get<{ documentsCount: number; insightsCount: number; integrationsCount: number; dataPoints: number; lastActivity?: string }>("/api/clone/training/stats"),
  },

  // Voice transcription endpoints
  transcribe: {
    upload: async (audioBlob: Blob) => {
      const formData = new FormData();
      formData.append("audio", audioBlob, "recording.webm");
      
      try {
        const response = await fetch(`${API_BASE_URL}/api/clone/transcribe`, {
          method: "POST",
          body: formData,
        });

        if (!response.ok) {
          const errorText = await response.text().catch(() => response.statusText);
          throw new Error(`API Error (${response.status}): ${errorText || response.statusText}`);
        }

        return await response.json();
      } catch (error) {
        if (error instanceof TypeError && error.message.includes("fetch")) {
          const errorMsg = API_BASE_URL.includes("localhost") 
            ? `Failed to connect to backend at ${API_BASE_URL}. If deployed, set VITE_API_URL environment variable to your backend URL (e.g., https://api.you-topia.ai)`
            : `Failed to connect to backend at ${API_BASE_URL}. Please verify the backend is running and accessible.`;
          throw new Error(errorMsg);
        }
        throw error;
      }
    },
    status: (id: string) => apiClient.get<{ status: string; transcription?: string }>(`/api/clone/transcribe/${id}`),
  },
};

