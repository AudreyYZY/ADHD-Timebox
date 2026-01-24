"use client";

import { useAppStore, type UserState } from "@/lib/store";
import { cn } from "@/lib/utils";

const stateConfig: Record<
  UserState,
  { label: string; description: string; color: string }
> = {
  planning: {
    label: "Planning",
    description: "Figuring out what to work on",
    color: "bg-primary/20 text-primary",
  },
  focusing: {
    label: "Focusing",
    description: "Working on your task",
    color: "bg-safe/20 text-safe",
  },
  interrupted: {
    label: "Paused",
    description: "Taking a moment",
    color: "bg-accent/20 text-accent",
  },
  resting: {
    label: "Resting",
    description: "Recharging",
    color: "bg-muted text-muted-foreground",
  },
};

export function StateIndicator() {
  const { userState } = useAppStore();
  const config = stateConfig[userState];

  return (
    <div className="flex items-center gap-2">
      <div
        className={cn(
          "flex items-center gap-2 rounded-full px-3 py-1.5 text-sm font-medium transition-colors",
          config.color
        )}
      >
        <div
          className={cn(
            "h-2 w-2 rounded-full",
            userState === "focusing" && "animate-pulse bg-safe",
            userState === "planning" && "bg-primary",
            userState === "interrupted" && "bg-accent",
            userState === "resting" && "bg-muted-foreground"
          )}
        />
        <span>{config.label}</span>
      </div>
    </div>
  );
}
