const API_BASE_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000/api";
const LOCAL_API_BASE = "/api";

export interface ChatResponse {
  response: string;
  status: string;
}

export interface BackendTask {
  id: string;
  title: string;
  priority: string;
  estimatedMinutes?: number;
  cognitiveLoad?: string;
  status: string;
}

export interface RecommendationResponse {
  taskId: string;
  durationMinutes: number;
  reason: string;
  preferLowCognitiveLoad: bool;
}

export const api = {
  chat: async (message: string): Promise<ChatResponse> => {
    const res = await fetch(`${API_BASE_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    if (!res.ok) {
      throw new Error("Chat failed");
    }
    return res.json();
  },

  getTasks: async (): Promise<BackendTask[]> => {
    const res = await fetch(`${LOCAL_API_BASE}/tasks`);
    if (!res.ok) {
      throw new Error("Failed to fetch tasks");
    }
    return res.json();
  },

  getRecommendation: async (context: any): Promise<RecommendationResponse> => {
    const res = await fetch(`${API_BASE_URL}/recommend`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ context }),
    });
    if (!res.ok) {
      throw new Error("Failed to get recommendation");
    }
    return res.json();
  },

  updateTaskStatus: async (taskId: string, status: string): Promise<void> => {
    const res = await fetch(`${LOCAL_API_BASE}/tasks/${taskId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    });
    if (!res.ok) {
      throw new Error("Failed to update task status");
    }
  },
};
