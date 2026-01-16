import { Pause, Play, Sparkles, Coffee, Heart } from "lucide-react";
import { FocusState, FOCUS_STATES } from "../types";

interface FullScreenFocusProps {
  remainingSeconds: number;
  activeTaskTitle?: string;
  onPause: () => void;
  onResume: () => void;
  onAbandon: () => void;
  isDark: boolean;
  focusState: FocusState;
}

export const FullScreenFocus = ({
  remainingSeconds,
  activeTaskTitle,
  onPause,
  onResume,
  onAbandon,
  isDark,
  focusState,
}: FullScreenFocusProps) => {
  const mins = Math.floor(remainingSeconds / 60);
  const secs = remainingSeconds % 60;
  const isPaused = focusState === FOCUS_STATES.PAUSED;

  return (
    <div
      className={`fixed inset-0 z-50 flex flex-col items-center justify-center transition-colors duration-500 ${
        isDark ? "bg-slate-950 text-white" : "bg-indigo-50 text-slate-800"
      }`}
    >
      {/* Decorative Background Elements - Pulse pauses when timer pauses */}
      <div
        className={`absolute w-[40vw] h-[40vw] rounded-full blur-3xl opacity-20 ${
          isPaused ? "" : "animate-pulse"
        } ${isDark ? "bg-indigo-600" : "bg-pink-300"}`}
        style={{ top: "10%", left: "10%", animationDuration: "4s" }}
      ></div>
      <div
        className={`absolute w-[35vw] h-[35vw] rounded-full blur-3xl opacity-20 ${
          isPaused ? "" : "animate-pulse"
        } ${isDark ? "bg-purple-600" : "bg-indigo-300"}`}
        style={{ bottom: "10%", right: "10%", animationDuration: "6s" }}
      ></div>

      <div className="relative z-10 flex flex-col items-center text-center p-8 max-w-4xl w-full">
        {/* Cute Icon / Badge */}
        <div
          className={`mb-8 px-6 py-2 rounded-full text-sm font-bold uppercase tracking-wider shadow-sm flex items-center gap-2 ${
            isPaused ? "" : "animate-bounce"
          } ${
            isDark ? "bg-white/10 text-indigo-200" : "bg-white text-indigo-500"
          }`}
          style={{ animationDuration: "2s" }}
        >
          {isPaused ? (
            <Coffee size={16} fill="currentColor" />
          ) : (
            <Sparkles size={16} fill="currentColor" />
          )}
          {isPaused ? "Paused" : "Focusing Mode"}
        </div>

        {/* Task Title */}
        <h2
          className={`text-3xl md:text-5xl font-bold mb-10 max-w-3xl leading-tight ${
            isDark ? "text-slate-200" : "text-slate-700"
          }`}
        >
          {activeTaskTitle || "Deep Work Session"}
        </h2>

        {/* Giant Cute Timer */}
        <div
          className={`font-mono font-black text-[18vw] md:text-[12rem] leading-none mb-12 tracking-tighter drop-shadow-lg tabular-nums ${
            isDark ? "text-white" : "text-indigo-600"
          } ${isPaused ? "opacity-50" : ""}`}
        >
          {mins}:{secs < 10 ? `0${secs}` : secs}
        </div>

        {/* Controls Switcher */}
        {isPaused ? (
          <div className="flex flex-col md:flex-row gap-4 animate-slide-up">
            <button
              onClick={onResume}
              className={`
                group px-10 py-5 rounded-3xl font-bold text-xl transition-all transform hover:scale-105 shadow-xl flex items-center gap-3
                ${
                  isDark
                    ? "bg-emerald-600 text-white hover:bg-emerald-500"
                    : "bg-emerald-400 text-white hover:bg-emerald-500"
                }
              `}
            >
              <Play size={24} fill="currentColor" />
              <span>Resume Focus</span>
            </button>
            <button
              onClick={onAbandon}
              className={`
                px-8 py-5 rounded-3xl font-bold text-lg transition-all hover:bg-white/10 hover:text-rose-400
                ${isDark ? "text-slate-400" : "text-slate-500"}
              `}
            >
              Abandon Session
            </button>
          </div>
        ) : (
          <div className="animate-fade-in">
            <p
              className={`text-xl md:text-2xl font-medium mb-12 opacity-80 flex items-center justify-center gap-2 ${
                isDark ? "text-indigo-200" : "text-slate-500"
              }`}
            >
              You're doing great! Keep going{" "}
              <Heart size={20} fill="currentColor" className="text-rose-400" />
            </p>
            <button
              onClick={onPause}
              className={`
                group relative px-10 py-5 rounded-3xl font-bold text-xl transition-all transform hover:scale-105 hover:-translate-y-1 shadow-xl
                ${
                  isDark
                    ? "bg-slate-800 text-white hover:bg-slate-700"
                    : "bg-white text-indigo-600 hover:bg-indigo-50"
                }
              `}
            >
              <div className="flex items-center gap-3">
                <Pause size={24} fill="currentColor" />
                <span>Take a Break</span>
              </div>
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
