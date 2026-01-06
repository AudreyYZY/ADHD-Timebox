"""PlannerAgent (V2) — 核心时间管家。"""

import os
import warnings

# 忽略 connectonion 把长 Prompt 当作文件路径的警告
warnings.filterwarnings(
    "ignore", category=UserWarning, module="connectonion.core.agent"
)

from typing import Optional

from connectonion import Agent, GoogleCalendar

from tools.plan_tools_v2 import PlanManager


DEFAULT_MODEL = "co/gemini-2.5-pro"
FINISHED_MARKER = "<<FINISHED>>"
STATUS_CONTINUE = "CONTINUE"
STATUS_FINISHED = "FINISHED"

PLANNER_PROMPT_PATH = os.path.join(
    os.path.dirname(__file__), "prompts", "planner_prompt.md"
)
try:
    with open(PLANNER_PROMPT_PATH, "r", encoding="utf-8") as f:
        PLANNER_PROMPT = f.read()
except Exception as e:
    PLANNER_PROMPT = f"Error loading system prompt: {e}"


class CalendarFallback:
    """当 Google Calendar 未就绪时的降级实现。"""

    def __init__(self, reason: str):
        self.reason = reason

    def create_event(
        self,
        title: str,
        start_time: str = None,
        end_time: str = None,
        start: str = None,
        end: str = None,
    ) -> str:
        return f"Calendar unavailable ({self.reason}); skip create_event for {title} {start_time or start} -> {end_time or end}."


class PlannerAgent:
    """时间盒 Planner Agent 封装，用于多智能体路由或独立运行。"""

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        plan_manager: Optional[PlanManager] = None,
        calendar: Optional[object] = None,
    ):
        self.calendar = calendar or self._init_calendar()
        self.plan_manager = plan_manager or PlanManager(calendar=self.calendar)

        # 补丁：如果传入的 plan_manager 没有 calendar，手动注入
        # 这解决了 Orchestrator 初始化 PlanManager 时未传入 Calendar 的问题
        if self.plan_manager.calendar is None:
            self.plan_manager.calendar = self.calendar

        self.agent = Agent(
            name="planner_agent_v2",
            model=model,
            system_prompt=PLANNER_PROMPT,
            tools=[self.plan_manager],
            quiet=False,  # 开启日志以便调试工具调用
            max_iterations=20,
        )

    def _init_calendar(self):
        try:
            return GoogleCalendar()
        except Exception as exc:
            return CalendarFallback(str(exc))

    def handle(self, user_input: str) -> dict:
        """
        单轮对话入口，返回包含 content/status 的信封。
        status:
        - CONTINUE: 继续持有会话锁
        - FINISHED: 释放锁
        """
        raw = self.agent.input(user_input)

        if not isinstance(raw, str):
            return {"content": str(raw), "status": STATUS_FINISHED}

        if FINISHED_MARKER in raw:
            content = raw.replace(FINISHED_MARKER, "").strip()
            status = STATUS_FINISHED
        else:
            content = raw
            status = STATUS_CONTINUE

        return {"content": content, "status": status}

    __call__ = handle
