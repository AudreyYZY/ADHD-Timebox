"use client";

import { useState, useEffect } from "react";
import { FOCUS_STATES, Task } from "./types";
import { useFocusSession } from "./hooks/useFocusSession";
import { useTaskPool } from "./hooks/useTaskPool";
import {
  HeaderBar,
  FullScreenFocus,
  PausedBanner,
  CurrentFocusCard,
  QuickAddTask,
  TaskPool,
  DailyReview,
} from "./components";

export default function TimeBoxApp() {
  const {
    focusState,
    remainingSeconds,
    activeTaskId,
    selectedDuration,
    history,
    actions,
  } = useFocusSession();
  const { tasks, addTask } = useTaskPool();
  const [activeTaskSelection, setActiveTaskSelection] = useState<string | null>(
    null
  );
  const [isPoolExpanded, setIsPoolExpanded] = useState(true);
  const [showReview, setShowReview] = useState(false);
  const [isDarkMode, setIsDarkMode] = useState(false);

  useEffect(() => {
    if (activeTaskId) {
      setActiveTaskSelection(activeTaskId);
      setIsPoolExpanded(false);
    } else if (focusState === FOCUS_STATES.IDLE) {
      setIsPoolExpanded(true);
    }
  }, [activeTaskId, focusState]);

  const isRunning = focusState === FOCUS_STATES.RUNNING;
  const isPaused = focusState === FOCUS_STATES.PAUSED;
  const isLocked =
    isRunning || isPaused || focusState === FOCUS_STATES.COMPLETED;

  const activeTaskIdStr: string | null = activeTaskSelection;
  const activeTask: Task | undefined =
    activeTaskIdStr !== null
      ? tasks.find((t: Task) => t.id === activeTaskIdStr)
      : undefined;
  const canStart = activeTaskIdStr !== null && selectedDuration > 0;

  const handleStart = (taskId: string | null, duration: number) => {
    const finalTaskId = taskId || activeTaskSelection;
    if (finalTaskId) {
      actions.start(finalTaskId, duration);
    }
  };

  // --- RENDER FULL SCREEN FOCUS MODE IF RUNNING OR PAUSED ---
  // Updated: Now includes isPaused so the full screen mode persists during pause
  if (isRunning || isPaused) {
    return (
      <FullScreenFocus
        remainingSeconds={remainingSeconds}
        activeTaskTitle={activeTask?.title}
        onPause={actions.pause}
        onResume={actions.resume}
        onAbandon={actions.abandon}
        isDark={isDarkMode}
        focusState={focusState}
      />
    );
  }

  // --- STANDARD DASHBOARD LAYOUT ---
  return (
    <div
      className={`h-screen overflow-hidden font-sans transition-colors duration-300 ${
        isDarkMode
          ? "bg-slate-950 text-slate-200 selection:bg-indigo-500/30 selection:text-indigo-200"
          : "bg-slate-50 text-slate-900 selection:bg-indigo-200 selection:text-indigo-900"
      }`}
    >
      {/* --- Layout Container --- */}
      <div className="max-w-[1600px] mx-auto px-6 h-full relative flex flex-col">
        <HeaderBar
          toggleReview={() => setShowReview(true)}
          isReviewOpen={showReview}
          isDark={isDarkMode}
          toggleTheme={() => setIsDarkMode(!isDarkMode)}
        />

        {/* --- Main Content Grid --- */}
        <div className="flex-1 grid grid-cols-1 md:grid-cols-12 gap-6 md:gap-12 pb-6 min-h-0">
          {/* Left Column (Desktop): Task Management */}
          <div className="md:col-span-5 lg:col-span-4 flex flex-col gap-6 order-2 md:order-1 overflow-y-auto md:overflow-visible pr-2 md:pr-0">
            <div className="md:h-full md:flex md:flex-col">
              {!isLocked && (
                <QuickAddTask
                  onAdd={addTask}
                  disabled={isLocked}
                  isDark={isDarkMode}
                />
              )}
              <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar">
                <TaskPool
                  tasks={tasks}
                  activeTaskId={activeTaskSelection}
                  onSelectActive={setActiveTaskSelection}
                  isLocked={isLocked}
                  isExpanded={isPoolExpanded}
                  toggleExpand={() => setIsPoolExpanded(!isPoolExpanded)}
                  isDark={isDarkMode}
                />
              </div>
            </div>
          </div>

          {/* Right Column (Desktop): Focus Zone */}
          <div className="md:col-span-7 lg:col-span-8 flex flex-col order-1 md:order-2 h-full">
            {/* PausedBanner is hidden here because we use FullScreenFocus now, but keeping in logic for fallback */}
            {isPaused && (
              <PausedBanner
                remainingSeconds={remainingSeconds}
                onResume={actions.resume}
                onAbandon={actions.abandon}
                isDark={isDarkMode}
              />
            )}
            <CurrentFocusCard
              focusState={focusState}
              activeTaskTitle={activeTask?.title}
              remainingSeconds={remainingSeconds}
              selectedDuration={selectedDuration}
              actions={{ ...actions, start: handleStart }}
              canStart={canStart}
              isDark={isDarkMode}
            />
          </div>
        </div>
      </div>

      {/* --- Overlay Page: Review --- */}
      {showReview && (
        <DailyReview
          history={history}
          onClose={() => setShowReview(false)}
          isDark={isDarkMode}
        />
      )}
    </div>
  );
}
