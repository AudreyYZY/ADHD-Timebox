const API_BASE_URL = "http://localhost:8000/api";

export interface ChatResponse {
  content: string;
  status: string;
  agent: string;
  tasks_updated: boolean;
  ascii_art?: string | null;
}

export interface BackendTask {
  id: string;
  title: string;
  start?: string | null;
  end?: string | null;
  type?: string;
  status: string;
  google_event_id?: string | null;
}

export interface RecommendationResponse {
  taskId: string;
  durationMinutes: number;
  reason: string;
  preferLowCognitiveLoad: boolean;
}

export interface ParkingResponse {
  content: string;
  status: string;
  agent: string;
}

interface TasksResponse {
  date: string;
  tasks: BackendTask[];
  summary?: {
    total: number;
    done: number;
    pending: number;
  };
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
    const res = await fetch(`${API_BASE_URL}/tasks`);
    if (!res.ok) {
      throw new Error("Failed to fetch tasks");
    }
    const data = (await res.json()) as TasksResponse;
    if (!data || !Array.isArray(data.tasks)) {
      return [];
    }
    return data.tasks;
  },

  updateTaskStatus: async (taskId: string, status: string): Promise<void> => {
    const res = await fetch(`${API_BASE_URL}/tasks/${taskId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    });
    if (!res.ok) {
      throw new Error("Failed to update task status");
    }
  },

  parkThought: async (
    message: string,
    thoughtType?: "search" | "memo" | "todo"
  ): Promise<ParkingResponse> => {
    const res = await fetch(`${API_BASE_URL}/parking`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, thought_type: thoughtType }),
    });
    if (!res.ok) {
      throw new Error("Failed to park thought");
    }
    return res.json();
  },
};
