"use client";

import { useEffect, useCallback } from "react";
import { useAppStore } from "@/lib/store";
import { cn } from "@/lib/utils";

export function TimerDisplay() {
  const {
    timeRemaining,
    setTimeRemaining,
    isTimerRunning,
    currentTask,
  } = useAppStore();

  const tick = useCallback(() => {
    setTimeRemaining(Math.max(0, timeRemaining - 1));
  }, [timeRemaining, setTimeRemaining]);

  useEffect(() => {
    if (!isTimerRunning || timeRemaining <= 0) return;

    const interval = setInterval(tick, 1000);
    return () => clearInterval(interval);
  }, [isTimerRunning, timeRemaining, tick]);

  const minutes = Math.floor(timeRemaining / 60);
  const seconds = timeRemaining % 60;

  const progress = currentTask
    ? ((currentTask.duration * 60 - timeRemaining) / (currentTask.duration * 60)) * 100
    : 0;

  if (!currentTask) return null;

  return (
    <div className="flex flex-col items-center gap-4">
      {/* Circular progress */}
      <div className="relative h-48 w-48">
        <svg className="h-full w-full -rotate-90" viewBox="0 0 100 100">
          {/* Background circle */}
          <circle
            cx="50"
            cy="50"
            r="45"
            fill="none"
            stroke="currentColor"
            strokeWidth="6"
            className="text-muted"
          />
          {/* Progress circle */}
          <circle
            cx="50"
            cy="50"
            r="45"
            fill="none"
            stroke="currentColor"
            strokeWidth="6"
            strokeLinecap="round"
            strokeDasharray={`${progress * 2.827} 282.7`}
            className={cn(
              "transition-all duration-1000",
              progress < 75 ? "text-primary" : "text-safe"
            )}
          />
        </svg>
        {/* Time display */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="font-mono text-4xl font-medium tabular-nums text-foreground">
            {String(minutes).padStart(2, "0")}:{String(seconds).padStart(2, "0")}
          </span>
          <span className="mt-1 text-sm text-muted-foreground">remaining</span>
        </div>
      </div>

      {/* Task title */}
      <div className="text-center">
        <p className="text-lg font-medium text-foreground">{currentTask.title}</p>
        {currentTask.description && (
          <p className="mt-1 text-sm text-muted-foreground">
            {currentTask.description}
          </p>
        )}
      </div>
    </div>
  );
}
