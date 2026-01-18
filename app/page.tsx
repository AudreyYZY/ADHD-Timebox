"use client";

import { useState, useEffect, useRef } from "react";
import { FOCUS_STATES, Task } from "./types";
import { useFocusSession } from "./hooks/useFocusSession";
import { useTaskPool } from "./hooks/useTaskPool";
import { useOrchestrator } from "./hooks/useOrchestrator";
import {
  HeaderBar,
  FullScreenFocus,
  PausedBanner,
  CurrentFocusCard,
  QuickAddTask,
  TaskPool,
  DailyReview,
  ChatInterface,
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

  // Orchestrator 集成
  const {
    recommendation,
    isLoadingRecommendation,
    events: orchestratorEvents,
    updateTasks,
    acceptRecommendation,
  } = useOrchestrator();

  const [activeTaskSelection, setActiveTaskSelection] = useState<string | null>(
    null
  );
  const [isPoolExpanded, setIsPoolExpanded] = useState(true);
  const [showReview, setShowReview] = useState(false);
  const [isDarkMode, setIsDarkMode] = useState(false);

  // 跟踪上一个 focusState 用于检测状态变化
  const prevFocusState = useRef(focusState);
  const isInitialized = useRef(false);

  // APP_START: 应用启动时初始化 Orchestrator
  useEffect(() => {
    if (!isInitialized.current && tasks.length > 0) {
      isInitialized.current = true;
      orchestratorEvents.appStart(tasks);
    }
  }, [tasks, orchestratorEvents]);

  // 同步任务池到 Orchestrator
  useEffect(() => {
    if (isInitialized.current) {
      updateTasks(tasks);
    }
  }, [tasks, updateTasks]);

  // 监听 focusState 变化，发送相应事件
  useEffect(() => {
    const prevState = prevFocusState.current;
    prevFocusState.current = focusState;

    // TIMEBOX_STARTED: 从 IDLE 变为 RUNNING
    if (prevState === FOCUS_STATES.IDLE && focusState === FOCUS_STATES.RUNNING) {
      if (activeTaskId) {
        orchestratorEvents.timeBoxStarted(activeTaskId, selectedDuration);
      }
    }

    // TIMEBOX_ENDED: 变为 COMPLETED
    if (focusState === FOCUS_STATES.COMPLETED && prevState !== FOCUS_STATES.COMPLETED) {
      if (activeTaskId) {
        orchestratorEvents.timeBoxEnded(
          activeTaskId,
          selectedDuration,
          selectedDuration // 完成时 actualMinutes = durationMinutes
        );
      }
    }

    // TIMEBOX_INTERRUPTED: 变为 ABANDONED
    if (focusState === FOCUS_STATES.ABANDONED && prevState !== FOCUS_STATES.ABANDONED) {
      if (activeTaskId) {
        const elapsedMinutes = Math.round(
          (selectedDuration * 60 - remainingSeconds) / 60
        );
        orchestratorEvents.timeBoxInterrupted(
          activeTaskId,
          selectedDuration,
          elapsedMinutes,
          "User abandoned"
        );
      }
    }
  }, [
    focusState,
    activeTaskId,
    selectedDuration,
    remainingSeconds,
    orchestratorEvents,
  ]);

  // 当收到推荐时，自动选择推荐的任务
  useEffect(() => {
    if (recommendation && focusState === FOCUS_STATES.IDLE) {
      setActiveTaskSelection(recommendation.taskId);
      // 可选：自动设置推荐的时长
      if (recommendation.durationMinutes !== selectedDuration) {
        actions.setDuration(recommendation.durationMinutes);
      }
    }
  }, [recommendation, focusState, selectedDuration, actions]);

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

      {/* Chat Interface */}
      <ChatInterface isDark={isDarkMode} />
    </div>
  );
}
