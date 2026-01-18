import { useState, useEffect } from "react";
import { Task } from "../types";
import { api } from "../utils/api";

export const useTaskPool = () => {
  const [tasks, setTasks] = useState<Task[]>([]);

  useEffect(() => {
    const fetchTasks = async () => {
      try {
        const backendTasks = await api.getTasks();
        // Convert BackendTask to Task if needed
        const mappedTasks: Task[] = backendTasks.map(t => ({
            id: t.id,
            title: t.title,
            priority: (t.priority as "urgent" | "medium" | "low") || "medium",
            estimatedMinutes: t.estimatedMinutes,
            cognitiveLoad: (t.cognitiveLoad as "low" | "medium" | "high") || "medium",
            status: t.status
        }));
        setTasks(mappedTasks);
      } catch (e) {
        console.error("Failed to fetch tasks from backend", e);
        // Fallback to local tasks if backend is down
        setTasks([
            { id: "1", title: "Check Emails (Local Fallback)", priority: "urgent" },
            { id: "2", title: "Backend Unavailable", priority: "medium" }
        ]);
      }
    };
    fetchTasks();
  }, []);

  const addTask = (
    title: string,
    priority: "urgent" | "medium" | "low" = "low"
  ) => {
    const newTask: Task = { id: Date.now().toString(), title, priority };
    setTasks([...tasks, newTask]);
    // Note: We are not syncing writes to backend yet as PlanManager is complex
  };

  return { tasks, addTask };
};
