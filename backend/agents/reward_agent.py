"""Reward Agent: celebrates wins and crafts daily summaries."""

import datetime
import json
import os
from typing import List, Optional, Tuple

from connectonion import Agent

from tools.plan_tools_v2 import PlanManager
from tools.reward_tools import RewardToolkit


DEFAULT_MODEL = "co/gemini-2.5-pro"

SUMMARY_SYSTEM_PROMPT = """
你是用户的史诗级吟游诗人与 hype man。
- 语气：热血、幽默、有画面感，避免客套。
- 字数：50 字以内。
- 任务：用户已看到任务清单，你只需给出一段震撼/俏皮的庆祝，不要重复列出清单。
""".strip()


class RewardAgent:
    """负责微奖励与日结总结的 Agent。"""

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        plan_manager: Optional[PlanManager] = None,
        toolkit: Optional[RewardToolkit] = None,
    ):
        self.plan_manager = plan_manager or PlanManager()
        self.toolkit = toolkit or RewardToolkit(brain_dir=self.plan_manager.plan_dir)
        self.agent = Agent(
            name="reward_agent",
            model=model,
            system_prompt=SUMMARY_SYSTEM_PROMPT,
            tools=[],
            quiet=True,
        )

    # -- 公共接口 ------------------------------------------------------

    def celebrate_task(self, task_name: str) -> str:
        """用本地语录生成即时奖励。"""
        return self.toolkit.generate_micro_reward(task_name)

    def summarize_day(self, tasks_data: Optional[List[dict]] = None) -> str:
        """
        汇总当日已完成任务，调用 LLM 生成总结，并用大型 cowsay 输出。
        tasks_data: 可选的任务列表；若缺省，则自动读取今日计划文件或最近的 daily_tasks。
        """
        tasks, plan_date, err = self._resolve_tasks(tasks_data)
        if err:
            return err

        completed = self._filter_completed(tasks)
        if not completed:
            return "📭 今天还没有标记完成的任务，先收割几条再来总结吧。"

        report_text = self._format_task_report(completed)
        summary_text = self._draft_summary(report_text, plan_date)
        reward_art = self.toolkit.generate_macro_reward(summary_text)
        log_path = self.toolkit.save_daily_summary(
            plan_date=plan_date, summary_text=summary_text, completed_tasks=completed
        )
        header = f"📅 {plan_date.isoformat()} 今日战报"
        separator = "-" * 30
        body = (
            f"{header}\n"
            f"{separator}\n"
            f"{report_text}\n"
            f"{separator}\n\n"
            f"{reward_art}\n\n"
            f"🗂 已归档：{log_path}"
        )
        return body

    # -- 内部方法 ------------------------------------------------------

    def _resolve_tasks(
        self, tasks_data: Optional[List[dict]]
    ) -> Tuple[Optional[List[dict]], datetime.date, Optional[str]]:
        """从参数或磁盘加载任务列表，并返回 (tasks, plan_date, error)。"""
        plan_date = datetime.date.today()

        if tasks_data is not None:
            if not isinstance(tasks_data, list):
                return None, plan_date, "❌ summarize_day 需要任务列表。"
            return tasks_data, plan_date, None

        path = self._locate_plan_path()
        if not path:
            return None, plan_date, "❌ 未找到今日或最近的计划文件，无法总结。"

        try:
            with open(path, "r", encoding="utf-8") as f:
                tasks = json.load(f)
        except Exception as exc:
            return None, plan_date, f"❌ 读取计划失败：{exc}"

        plan_date = self.plan_manager._plan_date_from_path(path)
        if not isinstance(tasks, list):
            return None, plan_date, f"❌ 计划文件格式异常：{path}"
        return tasks, plan_date, None

    def _locate_plan_path(self) -> Optional[str]:
        """优先使用今日计划，缺省时回退到最近的 daily_tasks 文件。"""
        today = datetime.date.today().isoformat()
        today_path = os.path.join(self.plan_manager.plan_dir, f"daily_tasks_{today}.json")
        if os.path.exists(today_path):
            return today_path
        candidates = sorted(
            f
            for f in os.listdir(self.plan_manager.plan_dir)
            if f.startswith("daily_tasks_") and f.endswith(".json")
        )
        if not candidates:
            return None
        return os.path.join(self.plan_manager.plan_dir, candidates[-1])

    def _filter_completed(self, tasks: List[dict]) -> List[dict]:
        """筛出已完成任务，兼容 status=done/completed。"""
        completed = []
        for task in tasks:
            status = str(task.get("status") or "").lower()
            if status in {"done", "completed", "complete"}:
                completed.append(task)
        return completed

    def _format_task_report(self, completed: List[dict]) -> str:
        """生成客观的战绩清单。"""
        lines = []
        for idx, task in enumerate(completed, start=1):
            title = task.get("title") or task.get("id") or f"任务{idx}"
            start = task.get("start") or "-"
            end = task.get("end") or "-"
            lines.append(f"{idx}. ✅ {title}（{start} - {end}）")
        return "\n".join(lines)

    def _draft_summary(self, report_text: str, plan_date: datetime.date) -> str:
        prompt = (
            f"日期：{plan_date.isoformat()}\n"
            f"已完成任务清单：\n{report_text}\n\n"
            "任务清单已经展示给用户，你只需在 50 字以内给出一段庆祝/夸奖，避免重复罗列任务，语气可热血或俏皮。"
        )
        try:
            result = self.agent.input(prompt)
            return result.strip() if isinstance(result, str) else str(result)
        except Exception as exc:  # pragma: no cover - LLM 依赖
            fallback = "今日主线完成，手动点赞！"
            return f"{fallback}（模型暂不可用：{exc}）"
