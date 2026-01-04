"""Reward toolkit: cowsay-based ASCII rewards and daily summary logging."""

import datetime
import os
import random
import textwrap
from typing import List, Optional

try:  # Optional dependency
    import cowsay  # type: ignore
except Exception:  # pragma: no cover - defensive fallback
    cowsay = None


# Lightweight夸奖语录库，避免每次都调 LLM
MICRO_PHRASES = [
    "火力全开，命中目标！",
    "干得漂亮，收获 +1 多巴胺。",
    "技能冷却完毕，下一关走起！",
    "小步快跑，连击不断！",
    "完美收招，保持节奏。",
    "一刀斩断，利落又帅气。",
    "解锁进度条，前进 1 格。",
    "打怪掉落：自信 +5。",
]

MACRO_PHRASES = [
    "今日主线告捷，坐等战利品。",
    "整日刷本成功，经验值暴涨！",
    "Boss 已倒地，英雄请领奖。",
    "史诗时刻，献上荣誉横幅。",
]

# cowsay 的小型与“大型/稀有”角色列表；会在运行时过滤实际存在的角色
SMALL_CHARACTERS = ["cow", "kitty", "pig", "turtle", "turkey", "fox", "cheese", "daemon", "octopus"]
BIG_CHARACTERS = ["dragon", "stegosaurus", "tux", "trex"]


class RewardToolkit:
    """封装 cowsay 奖励输出与日志存档。"""

    def __init__(self, brain_dir: Optional[str] = None, log_dir: Optional[str] = None):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.brain_dir = brain_dir or os.path.join(base_dir, "adhd_brain")
        self.log_dir = log_dir or os.path.join(self.brain_dir, "logs")
        os.makedirs(self.log_dir, exist_ok=True)

        self._has_cowsay = cowsay is not None
        self._available_chars = set(getattr(cowsay, "char_names", SMALL_CHARACTERS)) if cowsay else set()

    # -- 公开方法 ------------------------------------------------------

    def get_random_character(self, is_big: bool = False) -> str:
        """返回随机 cowsay 角色，按需倾向“大型”角色。"""
        pool = self._filter_available(BIG_CHARACTERS if is_big else SMALL_CHARACTERS)
        if not pool:  # 回退到全部角色再到默认 cow
            pool = self._filter_available(SMALL_CHARACTERS + BIG_CHARACTERS) or ["cow"]
        return random.choice(pool)

    def get_hype_phrase(self, is_macro: bool = False) -> str:
        """返回随机鼓励语句，宏模式用宏语录，否则用微语录。"""
        pool = MACRO_PHRASES if is_macro else MICRO_PHRASES
        return random.choice(pool)

    def generate_micro_reward(self, task_name: Optional[str] = None) -> str:
        """
        生成小任务奖励的 ASCII 艺术。
        主要使用内置语录，保证延迟极低。
        """
        title = (task_name or "这条任务").strip()
        phrase = self.get_hype_phrase(is_macro=False)
        message = f"搞定「{title}」！{phrase}"
        return self._render(message, is_big=False)

    def generate_macro_reward(self, summary_text: str) -> str:
        """
        生成日结/宏奖励的 ASCII 艺术。
        """
        phrase = self.get_hype_phrase(is_macro=True)
        combined = f"{summary_text.strip()}\n—— {phrase}"
        return self._render(combined, is_big=True)

    def save_daily_summary(
        self,
        plan_date: datetime.date,
        summary_text: str,
        completed_tasks: Optional[List[dict]] = None,
    ) -> str:
        """
        将每日总结落盘，返回保存路径。
        """
        date_str = plan_date.isoformat()
        path = os.path.join(self.log_dir, f"daily_summary_{date_str}.md")
        lines = [
            f"# Daily Summary {date_str}",
            "",
            summary_text.strip(),
        ]
        tasks = completed_tasks or []
        if tasks:
            lines.append("")
            lines.append("## Completed Tasks")
            for task in tasks:
                title = task.get("title") or task.get("id") or "任务"
                start = task.get("start") or "-"
                end = task.get("end") or "-"
                lines.append(f"- {title} ({start} - {end})")
        content = "\n".join(lines).rstrip() + "\n"
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    # -- 内部方法 ------------------------------------------------------

    def _filter_available(self, candidates: List[str]) -> List[str]:
        if not self._has_cowsay:
            return candidates
        return [c for c in candidates if c in self._available_chars]

    def _render(self, text: str, is_big: bool = False) -> str:
        """优先用 cowsay 渲染，否则使用简易气泡回退。"""
        character = self.get_random_character(is_big=is_big)
        if self._has_cowsay:
            try:
                # get_output_string 是 python-cowsay 的官方 API
                render_fn = getattr(cowsay, "get_output_string", None)
                if callable(render_fn):
                    return render_fn(character, text)
                # 回退到同名函数（某些版本导出为属性）
                cow_fn = getattr(cowsay, character, None)
                if callable(cow_fn):
                    return cow_fn(text)
            except Exception:
                pass  # 继续走回退
        return self._render_fallback(text)

    def _render_fallback(self, text: str) -> str:
        """当未安装 cowsay 时的文本气泡回退。"""
        wrapped = self._wrap(text)
        lines = wrapped.splitlines() or [text]
        width = max(len(line) for line in lines)
        top = " " + "_" * (width + 2)
        bottom = " " + "-" * (width + 2)
        bubble = "\n".join([f"| {line.ljust(width)} |" for line in lines])
        return f"{top}\n{bubble}\n{bottom}\n (•ᴗ•)つ━☆・*"

    @staticmethod
    def _wrap(text: str, width: int = 48) -> str:
        return textwrap.fill(text.strip(), width=width)
