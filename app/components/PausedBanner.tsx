import { Coffee, Play } from "lucide-react";
import { MICROCOPY } from "../constants";

interface PausedBannerProps {
  remainingSeconds: number;
  onResume: () => void;
  onAbandon: () => void;
  isDark: boolean;
}

export const PausedBanner = ({
  remainingSeconds,
  onResume,
  onAbandon,
  isDark,
}: PausedBannerProps) => {
  const mins = Math.floor(remainingSeconds / 60);
  const secs = remainingSeconds % 60;

  return (
    <div
      className={`
      border p-6 rounded-3xl mb-6 animate-fade-in relative overflow-hidden shadow-sm
      ${
        isDark
          ? "bg-amber-900/10 border-amber-500/20"
          : "bg-amber-50 border-amber-100"
      }
    `}
    >
      <div className="absolute top-0 left-0 w-1.5 h-full bg-amber-400"></div>
      <div className="flex justify-between items-center relative z-10 flex-wrap gap-4">
        <div>
          <h3
            className={`font-bold text-lg flex items-center gap-2 ${
              isDark ? "text-amber-400" : "text-amber-700"
            }`}
          >
            <Coffee size={20} />
            {MICROCOPY.paused.banner}
          </h3>
          <p
            className={`text-sm font-medium mt-1 opacity-80 ${
              isDark ? "text-amber-200" : "text-amber-800"
            }`}
          >
            Time left: {mins}:{secs < 10 ? `0${secs}` : secs}
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={onAbandon}
            className={`text-sm px-4 py-2 font-bold rounded-xl transition-colors ${
              isDark
                ? "text-slate-500 hover:text-rose-400 hover:bg-rose-950/20"
                : "text-slate-400 hover:text-rose-600 hover:bg-rose-50"
            }`}
          >
            {MICROCOPY.paused.abandonBtn}
          </button>
          <button
            onClick={onResume}
            className={`
            px-6 py-2.5 rounded-xl text-sm font-bold shadow-md transition-all flex items-center gap-2 hover:scale-105 hover:shadow-lg
            ${
              isDark
                ? "bg-amber-500 hover:bg-amber-400 text-slate-900"
                : "bg-amber-400 hover:bg-amber-500 text-white"
            }
          `}
          >
            <Play size={16} fill="currentColor" /> {MICROCOPY.paused.resumeBtn}
          </button>
        </div>
      </div>
    </div>
  );
};
