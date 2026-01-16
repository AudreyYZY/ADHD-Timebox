import { X, Check, History } from "lucide-react";
import { SessionHistory } from "../types";
import { MICROCOPY } from "../constants";

interface DailyReviewProps {
  history: SessionHistory[];
  onClose: () => void;
  isDark: boolean;
}

export const DailyReview = ({
  history,
  onClose,
  isDark,
}: DailyReviewProps) => {
  const todayStr = new Date().toDateString();
  const todaysSessions = history.filter(
    (h) => new Date(h.date).toDateString() === todayStr
  );
  const completedCount = todaysSessions.filter(
    (h) => h.outcome === "completed"
  ).length;
  const totalMinutes = todaysSessions.reduce(
    (acc, curr) => acc + (curr.outcome === "completed" ? curr.duration : 0),
    0
  );

  const bgPage = isDark ? "bg-slate-950" : "bg-white";
  const textTitle = isDark ? "text-white" : "text-slate-800";
  const textSub = isDark ? "text-slate-500" : "text-slate-400";
  const cardBg = isDark
    ? "bg-slate-900 border-slate-800"
    : "bg-slate-50 border-slate-100";

  return (
    <div
      className={`fixed inset-0 z-50 p-6 animate-slide-up overflow-y-auto ${bgPage}`}
    >
      <div className="max-w-2xl mx-auto mt-10">
        <div className="flex justify-between items-start mb-8">
          <div>
            <h2
              className={`text-4xl font-black mb-2 tracking-tight ${textTitle}`}
            >
              Daily Review
            </h2>
            <p className={`text-xl font-medium ${textSub}`}>
              {new Date().toLocaleDateString("en-US", {
                weekday: "long",
                month: "long",
                day: "numeric",
              })}
            </p>
          </div>
          <button
            onClick={onClose}
            className={`p-3 rounded-full transition-colors ${
              isDark
                ? "bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-white"
                : "bg-slate-100 hover:bg-slate-200 text-slate-500 hover:text-slate-800"
            }`}
          >
            <X size={24} />
          </button>
        </div>

        <div className="grid grid-cols-2 gap-6 mb-10">
          <div
            className={`${cardBg} p-8 rounded-[2.5rem] border relative overflow-hidden group`}
          >
            <div className="absolute top-0 right-0 p-6 opacity-10 group-hover:opacity-20 transition-opacity">
              <Check
                size={64}
                className={isDark ? "text-white" : "text-slate-800"}
              />
            </div>
            <div className={`text-6xl font-black mb-3 ${textTitle}`}>
              {completedCount}
            </div>
            <div
              className={`text-sm font-bold uppercase tracking-widest ${textSub}`}
            >
              {MICROCOPY.review.statLabel}
            </div>
          </div>
          <div
            className={`${cardBg} p-8 rounded-[2.5rem] border relative overflow-hidden group`}
          >
            <div className="absolute top-0 right-0 p-6 opacity-10 group-hover:opacity-20 transition-opacity">
              <History
                size={64}
                className={isDark ? "text-white" : "text-slate-800"}
              />
            </div>
            <div className={`text-6xl font-black mb-3 ${textTitle}`}>
              {totalMinutes}
            </div>
            <div
              className={`text-sm font-bold uppercase tracking-widest ${textSub}`}
            >
              {MICROCOPY.review.timeLabel}
            </div>
          </div>
        </div>

        {completedCount === 0 ? (
          <div
            className={`text-center p-16 border-2 border-dashed rounded-[2.5rem] ${
              isDark
                ? "border-slate-800 bg-slate-900/50"
                : "border-slate-200 bg-slate-50"
            }`}
          >
            <p
              className={`mb-2 text-lg font-bold ${
                isDark ? "text-slate-400" : "text-slate-500"
              }`}
            >
              {MICROCOPY.review.empty}
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            <h3
              className={`text-sm font-black uppercase tracking-widest mb-6 pl-2 ${textSub}`}
            >
              Session Log
            </h3>
            {todaysSessions.map((session) => (
              <div
                key={session.id}
                className={`flex justify-between items-center p-6 rounded-3xl border transition-colors ${
                  isDark
                    ? "bg-slate-900 border-slate-800/50 hover:border-slate-700"
                    : "bg-white border-slate-100 hover:border-slate-200 shadow-sm"
                }`}
              >
                <div className="flex items-center gap-5">
                  <div
                    className={`w-4 h-4 rounded-full shadow-sm ${
                      session.outcome === "completed"
                        ? "bg-emerald-500"
                        : "bg-rose-500"
                    }`}
                  />
                  <span
                    className={`text-base font-bold ${
                      isDark ? "text-slate-400" : "text-slate-500"
                    }`}
                  >
                    {new Date(session.date).toLocaleTimeString("en-US", {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                </div>
                <span className={`text-base font-black ${textTitle}`}>
                  {session.duration} min
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
