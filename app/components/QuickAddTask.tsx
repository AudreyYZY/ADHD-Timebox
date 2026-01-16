import { useState } from "react";
import { Plus, ChevronUp } from "lucide-react";
import { MICROCOPY } from "../constants";

interface QuickAddTaskProps {
  onAdd: (title: string, priority: "urgent" | "medium" | "low") => void;
  disabled: boolean;
  isDark: boolean;
}

export const QuickAddTask = ({
  onAdd,
  disabled,
  isDark,
}: QuickAddTaskProps) => {
  const [val, setVal] = useState("");
  const [priority, setPriority] = useState<"urgent" | "medium" | "low">("low");
  const [isFocused, setIsFocused] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (val.trim()) {
      onAdd(val, priority);
      setVal("");
      setPriority("low");
    }
  };

  const priorities: Array<{
    id: "urgent" | "medium" | "low";
    color: string;
    label: string;
  }> = [
    { id: "urgent", color: "bg-rose-500", label: "Urgent" },
    { id: "medium", color: "bg-amber-400", label: "Medium" },
    { id: "low", color: "bg-sky-400", label: "Low" },
  ];

  if (disabled) {
    return null;
  }

  return (
    <form onSubmit={handleSubmit} className="mb-6">
      <div
        className={`
        relative rounded-3xl transition-all duration-300 border flex flex-col focus-within:ring-0
        ${
          isFocused
            ? isDark
              ? "bg-slate-800 border-transparent shadow-lg"
              : "bg-white border-transparent shadow-xl"
            : isDark
            ? "bg-slate-900 border-slate-800"
            : "bg-white border-slate-100"
        }
      `}
      >
        {/* Input Area */}
        <div className="relative pb-6">
          <input
            type="text"
            value={val}
            onChange={(e) => setVal(e.target.value)}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            placeholder={MICROCOPY.idle.taskInputPlaceholder}
            className={`
              w-full bg-transparent border-none rounded-t-3xl px-6 pt-6 pb-0 pl-14 focus:outline-none focus:ring-0 focus-visible:ring-0 font-bold text-lg
              ${
                isDark
                  ? "text-slate-100 placeholder:text-slate-600"
                  : "text-slate-700 placeholder:text-slate-300"
              }
            `}
          />
          <Plus
            className={`absolute left-5 top-6 transition-colors ${
              isDark ? "text-slate-600" : "text-slate-300"
            }`}
            size={24}
            strokeWidth={2.5}
          />
        </div>

        {/* Separator Line */}
        <div
          className={`mx-6 border-t ${
            isDark ? "border-slate-700" : "border-slate-200"
          }`}
        />

        {/* Priority Selection Bar */}
        <div
          className={`px-6 pb-4 pt-6 flex items-center justify-between transition-opacity duration-200 overflow-visible ${
            isFocused || val ? "opacity-100" : "opacity-40 hover:opacity-100"
          }`}
        >
          <div className="flex gap-3 items-center">
            {priorities.map((p) => (
              <button
                key={p.id}
                type="button"
                onClick={() => setPriority(p.id)}
                className={`
                   rounded-full flex items-center justify-center transition-all shrink-0 ring-0 focus:ring-0 focus-visible:ring-0 p-0 min-h-0 min-w-0
                   ${p.color} 
                   ${priority === p.id ? "" : "opacity-40 hover:opacity-100"}
                 `}
                style={{
                  width: "24px",
                  height: "24px",
                  aspectRatio: "1 / 1",
                  borderRadius: "50%",
                  padding: "0",
                  minWidth: "0",
                  minHeight: "0",
                  maxWidth: "24px",
                  maxHeight: "24px",
                  flexShrink: 0,
                }}
                title={p.label}
                aria-label={`Select ${p.label} priority`}
              >
                {priority === p.id && (
                  <div className="w-2 h-2 bg-white rounded-full shadow-sm" />
                )}
              </button>
            ))}
          </div>

          <button
            type="submit"
            disabled={!val}
            className={`p-2 rounded-xl transition-all ${
              val
                ? isDark
                  ? "bg-indigo-600 text-white hover:bg-indigo-500"
                  : "bg-slate-800 text-white hover:bg-slate-700"
                : "opacity-0 pointer-events-none"
            }`}
          >
            <ChevronUp size={20} strokeWidth={2.5} />
          </button>
        </div>
      </div>
    </form>
  );
};
