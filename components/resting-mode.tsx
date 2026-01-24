"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { useAppStore } from "@/lib/store";
import { getRandomReward } from "@/lib/rewards";
import { ArrowRight, Clock } from "lucide-react";

export function RestingMode() {
  const [restTime, setRestTime] = useState(0);
  const { setUserState, currentTask, setCurrentTask, setTimeRemaining } = useAppStore();

  // Track rest time
  useEffect(() => {
    const interval = setInterval(() => {
      setRestTime((prev) => prev + 1);
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    if (mins === 0) return `${secs}s`;
    return `${mins}m ${secs}s`;
  };

  const handleReturnToTask = () => {
    if (currentTask) {
      setUserState("focusing");
    } else {
      setUserState("planning");
    }
  };

  const handleStartFresh = () => {
    setCurrentTask(null);
    setTimeRemaining(0);
    setUserState("planning");
  };

  return (
    <div className="flex flex-1 flex-col items-center justify-center">
      <div className="w-full max-w-md text-center">
        {/* Rest message */}
        <div className="mb-8">
          <div className="mb-6 inline-flex h-20 w-20 items-center justify-center rounded-full bg-muted">
            <Clock className="h-10 w-10 text-muted-foreground" />
          </div>
          <h2 className="text-2xl font-medium text-foreground mb-2">
            Resting
          </h2>
          <p className="text-muted-foreground mb-4">
            {getRandomReward("choseRest")}
          </p>
          <p className="text-sm text-muted-foreground/60">
            Resting for {formatTime(restTime)}
          </p>
        </div>

        {/* Gentle guidance */}
        <div className="mb-8 rounded-xl bg-secondary/50 p-4">
          <p className="text-sm text-muted-foreground">
            Take all the time you need. When you're ready, you can return to your task
            or start something new. No rush.
          </p>
        </div>

        {/* Actions */}
        <div className="space-y-3">
          {currentTask && (
            <Button onClick={handleReturnToTask} className="w-full" size="lg">
              <ArrowRight className="mr-2 h-4 w-4" />
              Return to "{currentTask.title}"
            </Button>
          )}
          <Button
            variant={currentTask ? "outline" : "default"}
            onClick={handleStartFresh}
            className="w-full"
            size="lg"
          >
            Start fresh with something new
          </Button>
        </div>

        {/* Bottom message */}
        <p className="mt-8 text-xs text-muted-foreground/60">
          Rest is not weakness. It's how you recharge.
        </p>
      </div>
    </div>
  );
}
