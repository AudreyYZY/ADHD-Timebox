"""Orchestrator agent for Phase 1 MAS routing."""

import datetime
import json
import os
from typing import Optional

from connectonion import Agent

from agents.focus_agent import FocusAgent
from agents.planner_agent import PlannerAgent
from agents.reward_agent import RewardAgent
from tools.parking_tools import ParkingService
from tools.plan_tools_v2 import PlanManager


SYSTEM_PROMPT = """
你是 OrchestratorAgent，多智能体系统的中央路由中枢。
你的任务是极其冷静、客观地分类用户的意图。

### 路由规则：
1. **PLANNER (计划管家)**
   - 关键词：日程、时间、推迟、提前、安排、计划、明天干嘛、今天有什么。
   - 例子："推迟 10 分钟"、"把会议改到下午"、"今天还有什么事"。

2. **FOCUS (执行教练)**
   - 关键词：开始、做完了、卡住了、不想做、分心了、正在做。
   - 例子："开始第一项任务"、"我做完了"、"这太难了"、"我走神了"。

3. **PARKING (念头停车场)**
   - 关键词：搜索、查一下、想到一个点子、记录、我想知道。
   - 例子："查一下 Python 的这个用法"、"突然想到要去买牛奶"、"把这个记下来"。

### 输出格式（严格遵守）：
- 确认为上述意图时 -> CALL: <AGENT_NAME> | <REASON>
- 只是打招呼或无法分类时 -> REPLY: <回复内容>

### 示例训练：
User: "把现在的任务顺延 30 分钟"
Output: CALL: PLANNER | 调整时间

User: "我准备好开始写代码了"
Output: CALL: FOCUS | 任务开始

User: "帮我查一下现在的汇率"
Output: CALL: PARKING | 外部搜索

User: "你好呀"
Output: REPLY: 你好！我是你的中枢，请告诉我下一步行动。

User: "我觉得有点累，不想动"
Output: CALL: FOCUS | 情绪干预
""".strip()

STATUS_CONTINUE = "CONTINUE"
STATUS_FINISHED = "FINISHED"


class OrchestratorAgent:  # 注意：不再继承 Agent，而是组合使用 Agent
    """Front-of-house router that simulates hand-offs."""

    def __init__(self):
        # 预热 PlannerAgent，便于直接转接；PlanManager 提升为路由层依赖以做状态注入
        self.plan_manager = PlanManager()
        self.planner_agent = PlannerAgent(plan_manager=self.plan_manager)
        self.parking_service = ParkingService()
        self.reward_agent = RewardAgent(plan_manager=self.plan_manager)
        self.focus_agent = FocusAgent(
            plan_manager=self.plan_manager,
            parking_service=self.parking_service,
            reward_toolkit=self.reward_agent.toolkit,
        )
        # 会话锁：若被占用，则后续用户输入将直接转发至锁定 Agent
        self.locked_agent = None
        self.escape_words = {"退出", "exit", "stop", "解锁", "终止", "结束"}

    def route(self, user_input: str) -> str:
        """
        Route user input with exclusive call mechanism:
        - If locked_agent exists, bypass classification and forward directly.
        - Otherwise classify intent, select agent, and update lock per envelope status.
        """
        normalized = user_input.strip().lower()

        if self._is_finish_day_intent(normalized):
            self.locked_agent = None
            summary = self.reward_agent.summarize_day()
            print(summary)
            return summary

        # Escape hatch: force unlock
        if self.locked_agent and any(word in normalized for word in self.escape_words):
            self.locked_agent = None
            msg = "🔓 已解除当前会话锁。"
            print(msg)
            return msg

        # Fast path: locked agent consumes input directly
        if self.locked_agent:
            print(">> [会话锁] 直接转接至已锁定 Agent ...")
            envelope = self._safe_handle(self.locked_agent, user_input)
            content = envelope.get("content", "")
            self._update_lock(self.locked_agent, envelope)
            final_content = self._maybe_attach_daily_reward(content)
            print(final_content)
            return final_content

        # 每次请求都创建一个全新的、一次性的 Agent 实例
        # name="orchestrator_temp" 甚至可以是随机数，确保无残留记忆
        temp_agent = Agent(
            name="orchestrator_temp",
            system_prompt=SYSTEM_PROMPT,
            model="co/gemini-2.5-pro",
            tools=[],
            quiet=True,  # 减少不必要的日志
        )

        # 强制清空可能存在的 session 文件 (如果 connectonion 在 init 时创建了)
        # 但既然是 temp，我们更希望它不读旧文件。
        # 如果 connectonion 强行读盘，我们需要一个随机名
        import time

        temp_agent.name = f"orchestrator_{int(time.time()*1000)}"

        raw = temp_agent.input(user_input).strip()

        if raw.startswith("CALL:"):
            parts = raw.split("|", 1)
            target = parts[0].replace("CALL:", "").strip().upper()
            reason = parts[1].strip() if len(parts) > 1 else ""
            print(f">> [系统路由] 正在转接至 {target}...{f' 理由：{reason}' if reason else ''}")

            active_agent = None
            if target == "PLANNER":
                active_agent = self.planner_agent
            elif target == "FOCUS":
                active_agent = self.focus_agent
            elif target == "PARKING":
                result = self.parking_service.dispatch_task(
                    content=user_input, task_type="search", source="orchestrator"
                )
                self.locked_agent = None
                final_result = self._maybe_attach_daily_reward(result)
                print(final_result)
                return final_result

            if not active_agent:
                msg = f"暂未实现对 {target} 的处理。"
                self.locked_agent = None
                print(msg)
                return msg

            envelope = self._safe_handle(active_agent, user_input)
            content = envelope.get("content", "")
            self._update_lock(active_agent, envelope)
            final_content = self._maybe_attach_daily_reward(content)
            print(final_content)
            return final_content

        if raw.startswith("REPLY:"):
            reply = raw.replace("REPLY:", "", 1).strip()
            self.locked_agent = None
            final_reply = self._maybe_attach_daily_reward(reply)
            print(final_reply)
            return final_reply

        # Fallback
        fallback = f"REPLY: {raw}"
        self.locked_agent = None
        final_fallback = self._maybe_attach_daily_reward(fallback)
        print(final_fallback)
        return final_fallback

    def _safe_handle(self, agent, user_input: str) -> dict:
        """调用目标 Agent 的 handle，并包装成信封；Planner 会自动注入 System State。"""
        payload = self._build_payload(agent, user_input)
        try:
            resp = agent.handle(payload)
        except Exception as exc:
            return {"content": f"[{agent.__class__.__name__} 错误] {exc}", "status": STATUS_FINISHED}
        return self._normalize_envelope(resp)

    def _build_payload(self, agent, user_input: str) -> str:
        """针对 Planner 注入计划上下文，其余 Agent 保持原始输入。"""
        if isinstance(agent, PlannerAgent):
            return self._inject_plan_context(user_input)
        return user_input

    def _inject_plan_context(self, user_input: str) -> str:
        """拼装用户输入与今日计划上下文，防止 Planner 忽略状态。"""
        try:
            context = self.plan_manager.get_current_context()
        except Exception as exc:
            context = f"PlanManager.get_current_context 失败：{exc}"

        sanitized_input = user_input.strip()
        return f"<User_Input>\n{sanitized_input}\n</User_Input>\n\n<System_State>\n{context}\n</System_State>"

    def _normalize_envelope(self, resp) -> dict:
        """确保返回包含 content/status，未改造的 Agent 默认为 FINISHED。"""
        if isinstance(resp, dict):
            content = resp.get("content", "")
            status = (resp.get("status") or STATUS_FINISHED).upper()
            return {"content": content, "status": status}
        return {"content": str(resp), "status": STATUS_FINISHED}

    def _update_lock(self, agent, envelope: dict):
        status = (envelope.get("status") if isinstance(envelope, dict) else STATUS_FINISHED) or STATUS_FINISHED
        if str(status).upper() == STATUS_CONTINUE:
            self.locked_agent = agent
        else:
            self.locked_agent = None

    # -- 奖励 / 总结钩子 ------------------------------------------------

    def _is_finish_day_intent(self, normalized_input: str) -> bool:
        keywords = [
            "结束",
            "收工",
            "收尾",
            "总结",
            "finish day",
            "end of day",
            "today done",
        ]
        return any(key in normalized_input for key in keywords)

    def _maybe_attach_daily_reward(self, content: str) -> str:
        reward = self._auto_reward_if_completed()
        if reward:
            return f"{content}\n\n---\n{reward}" if content else reward
        return content

    def _auto_reward_if_completed(self) -> Optional[str]:
        all_done, plan_date = self._all_tasks_completed()
        if not all_done:
            return None
        log_path = os.path.join(
            self.reward_agent.toolkit.log_dir,
            f"daily_summary_{plan_date.isoformat()}.md",
        )
        if os.path.exists(log_path):
            return None
        return self.reward_agent.summarize_day()

    def _all_tasks_completed(self) -> tuple[bool, datetime.date]:
        plan_path = self.reward_agent._locate_plan_path()
        if not plan_path:
            return False, datetime.date.today()
        plan_date = self.plan_manager._plan_date_from_path(plan_path)
        try:
            with open(plan_path, "r", encoding="utf-8") as f:
                tasks = json.load(f)
        except Exception:
            return False, plan_date
        if not isinstance(tasks, list) or not tasks:
            return False, plan_date
        statuses = [str(t.get("status") or "").lower() for t in tasks]
        all_done = statuses and all(s in {"done", "completed", "complete"} for s in statuses)
        return all_done, plan_date
