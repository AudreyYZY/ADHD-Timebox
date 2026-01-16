import { Task } from "../types";

export const getPriorityColor = (
  priority: Task["priority"],
  isDark: boolean
) => {
  switch (priority) {
    case "urgent": // Red
      return {
        dot: "bg-rose-500",
        shadow: "shadow-rose-500/50",
        ring: "ring-rose-500",
      };
    case "medium": // Yellow
      return {
        dot: "bg-amber-400",
        shadow: "shadow-amber-400/50",
        ring: "ring-amber-400",
      };
    case "low": // Blue
    default:
      return {
        dot: "bg-sky-400",
        shadow: "shadow-sky-400/50",
        ring: "ring-sky-400",
      };
  }
};
