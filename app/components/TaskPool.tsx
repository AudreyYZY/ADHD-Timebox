import { ChevronDown, ChevronUp, Play } from "lucide-react";
import { Task } from "../types";
import { getPriorityColor } from "../utils/getPriorityColor";

interface TaskPoolProps {
  tasks: Task[];
  onSelectActive: (taskId: string) => void;
  activeTaskId: string | null;
  isLocked: boolean;
  isExpanded: boolean;
  toggleExpand: () => void;
  isDark: boolean;
}

export const TaskPool = ({
  tasks,
  onSelectActive,
  activeTaskId,
  isLocked,
  isExpanded,
  toggleExpand,
  isDark,
}: TaskPoolProps) => {
  const containerClass = isLocked
    ? "opacity-40 pointer-events-none select-none grayscale"
    : "opacity-100";

  return (
    <div
      className={`transition-all duration-500 ease-in-out ${containerClass}`}
    >
      <div
        onClick={!isLocked ? toggleExpand : undefined}
        className="flex justify-between items-center cursor-pointer py-3 px-4 mb-2 select-none group"
      >
        <h3
          className={`text-xs font-black uppercase tracking-widest transition-colors ${
            isDark
              ? "text-slate-500 group-hover:text-slate-300"
              : "text-slate-400 group-hover:text-slate-600"
          }`}
        >
          Task Pool ({tasks.length})
        </h3>
        {!isLocked && (
          <div
            className={`p-2 rounded-xl transition-colors ${
              isDark
                ? "bg-slate-900 text-slate-500 group-hover:bg-slate-800 group-hover:text-slate-300"
                : "bg-slate-100 text-slate-400 group-hover:bg-slate-200 group-hover:text-slate-600"
            }`}
          >
            {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </div>
        )}
      </div>

      {isExpanded && (
        <div className="space-y-3">
          {tasks.length === 0 && (
            <div
              className={`text-sm py-12 italic text-center border border-dashed rounded-3xl font-medium ${
                isDark
                  ? "text-slate-600 border-slate-800"
                  : "text-slate-400 border-slate-200"
              }`}
            >
              No tasks yet. Clear mind?
            </div>
          )}
          {tasks.map((task) => {
            const styles = getPriorityColor(task.priority, isDark);
            return (
              <div
                key={task.id}
                onClick={() => !isLocked && onSelectActive(task.id)}
                className={`
                  group flex items-center justify-between p-5 rounded-3xl border transition-all cursor-pointer relative overflow-hidden
                  ${
                    activeTaskId === task.id
                      ? isDark
                        ? "bg-indigo-900/20 border-indigo-500/50 shadow-md"
                        : "bg-indigo-50 border-indigo-100 shadow-sm"
                      : isDark
                      ? "bg-slate-900 border-slate-800 hover:border-slate-700 hover:bg-slate-800"
                      : "bg-white border-slate-100 hover:border-indigo-100 hover:bg-white hover:shadow-md"
                  }
                `}
              >
                {/* Selection Indicator Bar */}
                {activeTaskId === task.id && (
                  <div className="absolute left-0 top-0 bottom-0 w-1.5 bg-indigo-500"></div>
                )}

                <div className="flex items-center gap-4 pl-2">
                  <div
                    className={`w-3.5 h-3.5 rounded-full ${styles.dot} ${styles.shadow} border-2 border-white/20`}
                  />
                  <span
                    className={`text-base font-bold transition-colors ${
                      activeTaskId === task.id
                        ? isDark
                          ? "text-indigo-200"
                          : "text-indigo-900"
                        : isDark
                        ? "text-slate-300 group-hover:text-slate-100"
                        : "text-slate-600 group-hover:text-slate-800"
                    }`}
                  >
                    {task.title}
                  </span>
                </div>
                <button
                  className={`
                  p-2.5 rounded-full transition-all duration-300 transform
                  ${
                    activeTaskId === task.id
                      ? isDark
                        ? "text-indigo-400 bg-indigo-950/50 scale-100 opacity-100"
                        : "text-indigo-500 bg-indigo-50 scale-100 opacity-100"
                      : (isDark
                          ? "text-slate-500 bg-slate-800"
                          : "text-slate-300 bg-slate-50") +
                        " scale-75 opacity-0 group-hover:opacity-100 group-hover:scale-100 hover:text-white"
                  }
                `}
                >
                  <Play size={18} fill="currentColor" />
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
