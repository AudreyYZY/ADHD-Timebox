const LOCAL_API_BASE = "/api";

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

const withUserHeader = (userId?: string) =>
  userId ? { "X-User-Id": userId } : {};

export const api = {
  chat: async (message: string, userId?: string): Promise<ChatResponse> => {
    const res = await fetch(`${LOCAL_API_BASE}/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...withUserHeader(userId),
      },
      body: JSON.stringify({ message }),
      credentials: "include",
    });
    if (!res.ok) {
      throw new Error("Chat failed");
    }
    return res.json();
  },

  getTasks: async (userId?: string): Promise<BackendTask[]> => {
    const res = await fetch(`${LOCAL_API_BASE}/tasks`, {
      headers: withUserHeader(userId),
      credentials: "include",
    });
    if (!res.ok) {
      throw new Error("Failed to fetch tasks");
    }
    const data = (await res.json()) as TasksResponse;
    if (!data || !Array.isArray(data.tasks)) {
      return [];
    }
    return data.tasks;
  },

  updateTaskStatus: async (
    taskId: string,
    status: string,
    userId?: string
  ): Promise<void> => {
    const res = await fetch(`${LOCAL_API_BASE}/tasks/${taskId}`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        ...withUserHeader(userId),
      },
      body: JSON.stringify({ status }),
      credentials: "include",
    });
    if (!res.ok) {
      throw new Error("Failed to update task status");
    }
  },

  parkThought: async (
    message: string,
    thoughtType?: "search" | "memo" | "todo",
    userId?: string
  ): Promise<ParkingResponse> => {
    const res = await fetch(`${LOCAL_API_BASE}/parking`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...withUserHeader(userId),
      },
      body: JSON.stringify({ message, thought_type: thoughtType }),
      credentials: "include",
    });
    if (!res.ok) {
      throw new Error("Failed to park thought");
    }
    return res.json();
  },
};
