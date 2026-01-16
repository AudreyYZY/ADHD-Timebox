import { Check } from "lucide-react";
import { MICROCOPY } from "../constants";

interface CompletionCardProps {
  onReset: () => void;
  isDark: boolean;
}

export const CompletionCard = ({ onReset, isDark }: CompletionCardProps) => (
  <div className="text-center py-12 animate-scale-up flex flex-col justify-center h-full">
    <div>
      <div
        className={`w-24 h-24 rounded-full flex items-center justify-center mx-auto mb-8 ring-8 transition-all animate-bounce ${
          isDark
            ? "bg-emerald-500/20 text-emerald-400 ring-emerald-500/5"
            : "bg-emerald-100 text-emerald-500 ring-emerald-50"
        }`}
        style={{ animationDuration: "3s" }}
      >
        <Check size={48} strokeWidth={3} />
      </div>
      <h2
        className={`text-4xl font-black mb-4 ${
          isDark ? "text-white" : "text-slate-800"
        }`}
      >
        {MICROCOPY.completed.title}
      </h2>
      <p
        className={`mb-12 max-w-[240px] mx-auto leading-relaxed text-lg font-medium ${
          isDark ? "text-slate-400" : "text-slate-500"
        }`}
      >
        {MICROCOPY.completed.subtext}
      </p>
    </div>
    <button
      onClick={onReset}
      className={`w-full max-w-sm mx-auto py-5 rounded-2xl font-bold text-lg hover:scale-[1.02] transition-all shadow-xl ${
        isDark
          ? "bg-slate-100 text-slate-900 hover:bg-white"
          : "bg-slate-800 text-white hover:bg-slate-700"
      }`}
    >
      {MICROCOPY.completed.nextAction}
    </button>
  </div>
);
