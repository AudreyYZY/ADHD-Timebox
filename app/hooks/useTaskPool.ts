import { useState } from "react";
import { Task } from "../types";

export const useTaskPool = () => {
  const [tasks, setTasks] = useState<Task[]>([
    { id: "1", title: "Check Emails", priority: "urgent" },
    { id: "2", title: "Write Report", priority: "medium" },
    { id: "3", title: "Tidy Up", priority: "low" },
  ]);

  const addTask = (
    title: string,
    priority: "urgent" | "medium" | "low" = "low"
  ) => {
    setTasks([...tasks, { id: Date.now().toString(), title, priority }]);
  };

  return { tasks, addTask };
};
