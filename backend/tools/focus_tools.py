import datetime
import json
import os
import re
import subprocess
from typing import Any, Dict, List, Optional, Tuple

from tools.plan_tools_v2 import PlanManager
from tools.reward_tools import RewardToolkit


def _safe_parse_dt(value: Optional[str], plan_date: datetime.date, tzinfo) -> Optional[datetime.datetime]:
    """Parse common datetime/time formats into aware datetime."""
    if not value:
        return None
    value = value.strip()
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.datetime.strptime(value, fmt).replace(tzinfo=tzinfo)
        except ValueError:
            continue
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            t = datetime.datetime.strptime(value, fmt).time()
            return datetime.datetime.combine(plan_date, t).replace(tzinfo=tzinfo)
        except ValueError:
            continue
    return None


class ContextTool:
    """
    负责提供前台窗口和当前任务状态，避免 LLM 自行猜测。
    - get_active_window(): 返回 macOS 前台应用与窗口标题。
    - get_idle_seconds(): 返回系统空闲秒数（macOS，仅在 ioreg 可用时）。
    - get_focus_state(): 返回当前时间、计划路径、当下/下一任务及剩余时间。
    """

    def __init__(self, plan_dir: Optional[str] = None):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        default_plan_dir = os.path.join(base_dir, "adhd_brain")
        self.plan_dir = plan_dir or default_plan_dir
        os.makedirs(self.plan_dir, exist_ok=True)

    # -- 公共工具方法 --

    def get_active_window(self) -> str:
        """在 macOS 上读取当前前台窗口，失败时返回原因。"""
        script = (
            'tell application "System Events" to get name of first application process whose frontmost is true\n'
            "set frontApp to result\n"
            "set windowTitle to \"\"\n"
            "try\n"
            "    tell application frontApp to set windowTitle to name of front window\n"
            "end try\n"
            'return frontApp & " - " & windowTitle'
        )
        try:
            output = subprocess.check_output(["osascript", "-e", script], timeout=2)
            text = output.decode("utf-8", errors="ignore").strip()
            return text or "无法获取窗口标题"
        except FileNotFoundError:
            return "osascript 不可用，可能不是 macOS 环境。"
        except subprocess.TimeoutExpired:
            return "前台窗口查询超时。"
        except Exception as exc:
            return f"获取前台窗口失败：{exc}"

    def get_idle_seconds(self) -> Optional[int]:
        """基于 ioreg 读取系统空闲时长（秒），仅在 macOS 可用。"""
        try:
            output = subprocess.check_output(["ioreg", "-c", "IOHIDSystem"], timeout=2)
        except FileNotFoundError:
            return None
        except subprocess.TimeoutExpired:
            return None
        except Exception:
            return None

        text = ""
        try:
            text = output.decode("utf-8", errors="ignore")
        except Exception:
            return None

        match = re.search(r'HIDIdleTime\" = (\d+)', text)
        if not match:
            return None

        try:
            nanoseconds = int(match.group(1))
            return int(nanoseconds / 1_000_000_000)
        except Exception:
            return None

    def get_focus_state(self) -> Dict[str, Any]:
        """
        返回结构化的专注状态。
        字段：
        - status: current/upcoming/finished/no_plan/empty
        - active_task: {title,start,end,remaining_minutes,plan_date}
        - progress: {done,total}
        - plan_path: 计划文件路径
        - now: ISO 时间字符串
        - message: 友好描述
        """
        now = datetime.datetime.now().astimezone()
        plan_path = self._resolve_plan_path()
        if not plan_path:
            return {
                "status": "no_plan",
                "active_task": None,
                "progress": {"done": 0, "total": 0},
                "plan_path": None,
                "now": now.isoformat(),
                "message": f"未找到计划文件，目录：{self.plan_dir}",
            }

        tasks, plan_date = self._load_tasks(plan_path)
        if tasks is None:
            return {
                "status": "empty",
                "active_task": None,
                "progress": {"done": 0, "total": 0},
                "plan_path": plan_path,
                "now": now.isoformat(),
                "message": f"计划文件为空：{plan_path}",
            }

        normalized = self._normalize_tasks(tasks, plan_date)
        status, task = self._determine_focus_task(normalized, now)
        active_task = None
        if task:
            include_date = plan_date != datetime.date.today()
            start_text = self._format_time(task.get("start_dt"), include_date)
            end_text = self._format_time(task.get("end_dt"), include_date)
            remaining = None
            if task.get("end_dt"):
                remaining = max(int((task["end_dt"] - now).total_seconds() // 60), 0)
            active_task = {
                "title": task.get("title") or "当前任务",
                "start": start_text,
                "end": end_text,
                "remaining_minutes": remaining,
                "plan_date": plan_date.isoformat(),
            }
        progress = {
            "done": len([t for t in normalized if t.get("status") == "done"]),
            "total": len(normalized),
        }
        message = self._build_message(status, active_task)
        return {
            "status": status,
            "active_task": active_task,
            "progress": progress,
            "plan_path": plan_path,
            "now": now.isoformat(),
            "message": message,
        }

    # -- 内部辅助方法 --

    def _resolve_plan_path(self) -> Optional[str]:
        today = datetime.date.today().isoformat()
        today_path = os.path.join(self.plan_dir, f"daily_tasks_{today}.json")
        if os.path.exists(today_path):
            return today_path
        candidates = sorted(
            (
                f
                for f in os.listdir(self.plan_dir)
                if f.startswith("daily_tasks_") and f.endswith(".json")
            )
        )
        if not candidates:
            return None
        return os.path.join(self.plan_dir, candidates[-1])

    def _load_tasks(self, path: str) -> Tuple[Optional[List[Dict[str, Any]]], datetime.date]:
        try:
            with open(path, "r") as f:
                tasks = json.load(f)
        except Exception:
            return None, datetime.date.today()
        plan_date = self._plan_date_from_path(path)
        if not isinstance(tasks, list):
            return None, plan_date
        return tasks, plan_date

    def _normalize_tasks(self, tasks: List[dict], plan_date: datetime.date) -> List[dict]:
        tzinfo = datetime.datetime.now().astimezone().tzinfo
        normalized = []
        for task in tasks:
            start_dt = _safe_parse_dt(task.get("start"), plan_date, tzinfo)
            end_dt = _safe_parse_dt(task.get("end"), plan_date, tzinfo)
            normalized.append({**task, "start_dt": start_dt, "end_dt": end_dt})
        normalized.sort(
            key=lambda t: t.get("start_dt")
            or datetime.datetime.max.replace(tzinfo=tzinfo)
        )
        return normalized

    def _determine_focus_task(
        self, tasks: List[dict], now: datetime.datetime
    ) -> Tuple[str, Optional[dict]]:
        if not tasks:
            return "empty", None
        timed = [t for t in tasks if t.get("start_dt")]
        if not timed:
            return "no_timed", tasks[0]
        
        # 过滤掉已完成的任务，不再将其视为“当前专注”的目标
        # 这样如果当前时间段的任务已完成，会自动滑向下一个即将开始的任务（upcoming）
        pending_timed = [
            t for t in timed 
            if str(t.get("status", "")).lower() not in {"done", "completed", "complete"}
        ]
        
        # 如果所有有时间的任务都做完了，返回最后一个任务标记为 finished
        if not pending_timed:
            return "finished", timed[-1]

        for task in pending_timed:
            start_dt = task.get("start_dt")
            end_dt = task.get("end_dt") or start_dt
            
            # 1. 刚好在时间窗口内 -> current
            if start_dt <= now <= end_dt:
                return "current", task
            
            # 2. 时间窗口还没到 -> upcoming
            # 由于 pending_timed 已经按时间排序，遇到的第一个“未来”任务即为 upcoming
            if start_dt > now:
                # 【优化】如果下一个任务在 20 分钟内开始，且之前的任务都已完成，
                # 我们将其视为 "current"（提前进入状态），以便 IdleWatcher 生效。
                diff_minutes = (start_dt - now).total_seconds() / 60
                if diff_minutes <= 20:
                     return "current", task
                return "upcoming", task
        
        # 如果代码走到这里，说明所有 pending 任务的时间窗口都已过去（overdue）
        # 或者当前时间处于任务之间的空隙（且之前的都做完了）。
        # 这种情况下，我们找第一个 pending 任务作为 fallback
        return "upcoming", pending_timed[0]

    def _plan_date_from_path(self, path: str) -> datetime.date:
        try:
            return datetime.datetime.strptime(
                os.path.basename(path), "daily_tasks_%Y-%m-%d.json"
            ).date()
        except ValueError:
            return datetime.date.today()

    def _format_time(self, dt_value: Optional[datetime.datetime], include_date: bool) -> str:
        if not dt_value:
            return "-"
        fmt = "%Y-%m-%d %H:%M" if include_date else "%H:%M"
        return dt_value.strftime(fmt)

    def _build_message(self, status: str, active_task: Optional[dict]) -> str:
        if not active_task:
            return "暂无任务进行中。"
        title = active_task.get("title", "")
        start = active_task.get("start", "-")
        end = active_task.get("end", "-")
        if status == "current":
            remaining = active_task.get("remaining_minutes")
            tail = f"，剩余约 {remaining} 分钟" if remaining is not None else ""
            return f"当前任务：{title}（{start}-{end}）{tail}"
        if status == "upcoming":
            return f"下一任务：{title}（{start}-{end}）"
        if status == "finished":
            return f"已完成所有有时间的任务，最后一条：{title}（{start}-{end}）"
        return f"当前任务：{title}（{start}-{end}）"


class FocusToolkit:
    """
    Focus Agent 的辅助工具集合：
    - complete_task(task_id): 将任务标记为 done。
    - suggest_micro_step(task_title): 拆分 2-3 个可执行的微步骤。
    - white_noise(action): 启停白噪声提示（文本占位，不播放音频）。
    """

    def __init__(
        self,
        plan_manager: Optional[PlanManager] = None,
        context_tool: Optional[ContextTool] = None,
        reward_toolkit: Optional[RewardToolkit] = None,
    ):
        self.plan_manager = plan_manager or PlanManager()
        self.context_tool = context_tool or ContextTool(plan_dir=self.plan_manager.plan_dir)
        self.reward_toolkit = reward_toolkit or RewardToolkit(brain_dir=self.plan_manager.plan_dir)

    def complete_task(self, task_id: str) -> str:
        """
        标记指定任务为完成。task_id 可为任务 ID 或标题的子串。
        返回确认文本或错误提示，不抛异常。
        """
        lock = getattr(self.plan_manager, "_file_lock", None)
        if lock:
            lock.__enter__()
        try:
            path = self.context_tool._resolve_plan_path()
            if not path:
                return "❌ 未找到计划文件，无法完成任务。"
            tasks, plan_date = self.context_tool._load_tasks(path)
            if tasks is None:
                return f"❌ 计划文件不可读：{path}"

            target = self._locate_task(tasks, task_id)
            if target is None:
                return f"❌ 未找到任务：{task_id}"

            target["status"] = "done"
            target["completed_at"] = datetime.datetime.now().astimezone().isoformat()
            try:
                with open(path, "w") as f:
                    json.dump(tasks, f, ensure_ascii=False, indent=2)
            except Exception as exc:
                return f"❌ 写入失败：{exc}"
        finally:
            if lock:
                lock.__exit__(None, None, None)

        title = target.get("title") or task_id
        start_text = target.get("start") or "-"
        end_text = target.get("end") or "-"
        reward_block = ""
        if self.reward_toolkit:
            try:
                reward_block = "\n\n" + self.reward_toolkit.generate_micro_reward(title)
            except Exception as exc:
                reward_block = f"\n\n[奖励生成失败：{exc}]"
        return f"✅ 已完成：{title}（{start_text} - {end_text}）{reward_block}\n\n(SYSTEM NOTE: 请务必在最终回复中原样展示上述 ASCII Art 奖励，不要省略。)"

    def suggest_micro_step(self, task_title: str) -> str:
        """
        当用户卡住时，给出 2-3 个可在 5 分钟内完成的微步骤。
        设计为纯文本，不依赖外部服务。
        """
        normalized = (task_title or "当前任务").strip()
        steps = [
            f"写下「{normalized}」的最小完成标准，用 1 句话描述。",
            "打开相关文件/文档，找到最需要修改的入口位置并插入 TODO 注释。",
            "写出第一个空的函数/段落骨架，确保能运行或保存。",
        ]
        return " / ".join(steps)

    def white_noise(self, action: str) -> str:
        """
        占位实现：提示开启/关闭白噪声，不真正播放音频。
        action: start/stop。
        """
        normalized = (action or "").strip().lower()
        if normalized in {"start", "on", "play"}:
            return "🔊 白噪声提示：已记录为开启（文本提示，不播放音频）。"
        if normalized in {"stop", "off", "pause"}:
            return "🤫 白噪声提示：已记录为关闭。"
        return "请指定 action=start/stop。"

    # -- 内部辅助方法 --

    def _locate_task(self, tasks: List[dict], task_id: str) -> Optional[dict]:
        if not task_id:
            return None
        lowered = task_id.lower()
        for task in tasks:
            if str(task.get("id", "")).lower() == lowered:
                return task
        for task in tasks:
            title = str(task.get("title", "")).lower()
            if lowered in title:
                return task
        return None
