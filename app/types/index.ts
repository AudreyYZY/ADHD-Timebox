// State Definitions
export const FOCUS_STATES = {
  IDLE: "idle",
  RUNNING: "running",
  PAUSED: "paused",
  COMPLETED: "completed",
  ABANDONED: "abandoned",
} as const;

export type FocusState = (typeof FOCUS_STATES)[keyof typeof FOCUS_STATES];

export interface Task {
  id: string;
  title: string;
  priority: "urgent" | "medium" | "low";
}

export interface SessionHistory {
  id: number;
  date: string;
  duration: number;
  outcome: "completed" | "abandoned";
}

export interface FocusStateData {
  status: FocusState;
  activeTaskId: string | null;
  durationMinutes: number;
  remainingSeconds: number;
  history: SessionHistory[];
}

export type FocusAction =
  | { type: "START"; payload: { taskId: string | null; duration: number } }
  | { type: "PAUSE" }
  | { type: "RESUME" }
  | { type: "TICK" }
  | { type: "ABANDON" }
  | { type: "RESET_COMPLETED" }
  | { type: "SET_DURATION"; payload: number };
