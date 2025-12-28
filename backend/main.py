# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import os
import json
import datetime

# 引入 ConnectOnion
from connectonion import Agent, Memory, GoogleCalendar

CONFIRM_KEYWORDS = ("确认", "同意", "可以", "没问题", "ok", "OK", "好", "行", "同步", "go", "yes")
_plan_synced = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ADHD_DIR = os.path.join(BASE_DIR, "adhd_brain")
HANDOVER_NOTE_FILE = os.path.join(ADHD_DIR, "handover_note.json")
os.makedirs(ADHD_DIR, exist_ok=True)

# --- 1. 定义工具 (Tools) ---

# 初始化记忆模块，用于存储历史任务和遗留任务
memory = Memory(memory_dir="adhd_brain")
# 初始化日历工具
calendar = GoogleCalendar()


def get_current_datetime() -> str:
    """返回当前本地时间，包含时区信息，用于让 Agent 显式确认今天的日期。"""
    now = datetime.datetime.now().astimezone()
    return now.strftime("当前本地时间：%Y-%m-%d %H:%M:%S %Z (UTC%z)")


def save_structured_plan(tasks_json: str) -> str:
    """
    保存结构化的今日任务列表，供执行 Agent 读取。
    Args:
        tasks_json: JSON 字符串列表。
        格式示例：
        [
            {"id": "task_1", "title": "撰写周报", "start": "14:00", "end": "14:30", "type": "work"},
            {"id": "task_2", "title": "洗衣服", "start": "14:30", "end": "15:00", "type": "chore"}
        ]
    """
    date = datetime.date.today().isoformat()
    try:
        tasks = json.loads(tasks_json)
        if not isinstance(tasks, list):
            raise ValueError("tasks_json 应该是任务列表。")
    except Exception as e:
        return f"❌ 保存失败：请传入 JSON 列表字符串。错误: {e}"

    path = os.path.join(ADHD_DIR, f"daily_tasks_{date}.json")
    with open(path, "w") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)

    # 记录一次摘要到 Memory，便于追踪保存历史
    memory.write_memory(f"plan_{date}_structured", f"Saved {len(tasks)} tasks to {path}")
    return f"✅ 结构化计划已保存，共 {len(tasks)} 条任务，路径：{path}"


def get_legacy_tasks() -> str:
    """
    获取历史遗留的任务或过期的任务。
    """
    # 这里我们简单模拟，实际可以搜索 memory 中未标记完成的任务
    # 也可以让 Agent 养成习惯，每天早上先读一下昨天的复盘
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    return memory.read_memory(f"plan_{yesterday}")


def load_handover_note():
    """
    读取守护者写入的交接留言，读后标记为已读。
    返回格式：{"date": "...", "content": ["..."], "status": "read", "read_at": "..."}
    """
    if not os.path.exists(HANDOVER_NOTE_FILE):
        return None
    try:
        with open(HANDOVER_NOTE_FILE, "r") as f:
            data = json.load(f)
    except Exception:
        return None
    raw_content = (data or {}).get("content", [])
    if isinstance(raw_content, str):
        raw_content = [raw_content]
    content_list = [c.strip() for c in raw_content if isinstance(c, str) and c.strip()]
    if not content_list:
        return None
    data["content"] = content_list
    data["status"] = "read"
    data["read_at"] = datetime.datetime.now().isoformat()
    with open(HANDOVER_NOTE_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data


def _normalize_time_str(value: str, default_date: str = None) -> str:
    """
    将时间字符串标准化为 'YYYY-MM-DD HH:MM' 以兼容 GoogleCalendar。
    - 接受含秒的时间或 ISO 格式。
    - 若仅有时间且提供 default_date，则补全日期。
    """
    if not value or not isinstance(value, str):
        return None
    value = value.strip()
    # 如果只传了时间，补上日期
    if default_date and (" " not in value and "T" not in value):
        value = f"{default_date} {value}"
    # 尝试解析 ISO/标准格式
    try:
        dt = datetime.datetime.fromisoformat(value.replace("T", " "))
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        pass
    # 尝试包含秒的 "YYYY-MM-DD HH:MM:SS"
    try:
        dt = datetime.datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return None


def _sync_today_plan_to_calendar(date: str = None) -> str:
    """读取今日计划并批量同步到 Google Calendar；若今日无计划，提示先生成。"""
    target_date = date or datetime.date.today().isoformat()
    path = os.path.join(ADHD_DIR, f"daily_tasks_{target_date}.json")
    if not os.path.exists(path):
        return (
            f"⚠️ 今日计划未找到：{path}\n"
            f"请先用时间盒教练生成今日的 daily_tasks_{target_date}.json，再同步日历。"
        )
    try:
        with open(path, "r") as f:
            tasks = json.load(f)
    except Exception as exc:
        return f"❌ 读取计划失败：{exc}"
    if not isinstance(tasks, list) or not tasks:
        return "❌ 计划为空或格式异常，无法同步日历。"

    success, errors = 0, []
    for task in tasks:
        title = task.get("title") or "未命名任务"
        raw_start = task.get("start")
        raw_end = task.get("end")
        start = _normalize_time_str(raw_start, target_date)
        end = _normalize_time_str(raw_end, target_date)
        if not start or not end:
            errors.append(f"{title} 开始/结束时间格式无法解析：{raw_start} -> {raw_end}，已跳过。")
            continue
        try:
            calendar.create_event(title=title, start=start, end=end)
            success += 1
        except Exception as exc:
            errors.append(f"{title} 同步失败：{exc}")

    summary = f"✅ 已同步 {success}/{len(tasks)} 条任务到日历。"
    if errors:
        summary += " ⚠️ " + " | ".join(errors)
    return summary


# --- 2. 定义系统提示词 (The Brain) ---
# 这里我们将《时间盒》的方法论转化为 AI 的指令

base_system_prompt = """
你是一位专为 ADHD 用户设计的“时间盒（Timeboxing）”管理教练。你的目标是帮助用户减轻认知负荷，将混乱的任务转化为可视化的、可执行的时间块。

## 你的核心工作流程：

0. **【先报当前日期时间并收集任务】**
   - 回复用户前，**必须先调用** `get_current_datetime`，把“今天的日期 + 当前时间 + 时区”报给用户。
   - 在同一句里请用户提供/确认任务清单，并附带一句：“如果时间不对请告诉我正确的时间/日期/时区”即可，无需单独等待确认。

1. **接收与整形**：
   - 用户会把今天想做的事一股脑告诉你，不管顺序。
   - **任务整形**：如果用户只说了名词（如“周报”），你要改成动词短语（如“撰写周报”）。
   
2. **颗粒度调整 (至关重要)**：
   - **大拆小**：对于模糊的大任务（如“写论文”），必须拆解为 15-60 分钟能完成的子任务（如“浏览3篇文献”、“梳理大纲”）。
   - **小合并**：对于琐碎杂事（回微信、交电费、看邮件），不要单独列，将它们打包进一个“Admin Block（行政事务盒）”或“杂事盒”。

3. **优先级筛选与历史回顾**：
   - 总是先查看是否有历史遗留任务（User 可能会忘记）。
   - 协助用户选出 **3-5 个核心任务**。
   - 如果任务超过 5 个，温柔地提醒用户：“贪多嚼不烂，我们先聚焦这几个，其他的放入待办池？”

4. **装填时间盒**：
   - 必须为每个任务分配时间盒：
     - **15 min**：简单任务、快速清理。
     - **30 min**：标准工作。
     - **60 min**：深度工作（复杂任务）。
   - 提醒用户预留“缓冲时间”和“休息时间”。
   - 在输出计划时开头明确说明“为你规划 <日期> 的日程：…”，并确保不使用过去时间或错误年份；若时间在当前时间之前，先提示用户并重新生成。

## 交互原则：
- **必须获得同意**：在你整理完清单和时间表后，必须问用户：“这样安排可以吗？还是需要调整？”
- **只有用户明确同意后**，执行以下操作：
  1. 调用 `GoogleCalendar.create_event`（带确认）同步到日历，保持事件时间与文本一致。
  2. 调用 `save_structured_plan`，以 JSON 列表字符串保存今日任务，字段需能反映日历中的开始/结束时间，确保两边一致。
- 语气要像朋友一样支持，不要像教官一样严厉。ADHD 用户需要鼓励。


## 示例输出格式：
【今日核心（Top 3）】
1. 撰写周报（30min）
...

【时间盒安排】
09:00 - 10:00 [60min] 深度工作：梳理论文大纲
10:00 - 10:15 [15min] 休息/散步
10:15 - 10:45 [30min] 杂事盒：回邮件 + 交电费
...
"""

handover_note = load_handover_note()
system_prompt = base_system_prompt
handover_banner = None
if handover_note:
    note_date = handover_note.get("date", "未知日期")
    note_content_list = handover_note.get("content", [])
    note_lines = "\n".join(f"- {c}" for c in note_content_list)
    system_prompt += f"\n\n# 昨日守护者的留言（{note_date}）\n{note_lines}\n请在规划时优先考虑这条留言。"
    handover_banner = f"📩 昨天的你有一条留言：‘{'；'.join(note_content_list)}’"

# --- 3. 创建 Agent ---

agent = Agent(
    name="timebox_coach",
    model="co/gemini-2.5-pro",  # 使用性价比高的模型，或者换成 co/gpt-5
    system_prompt=system_prompt,
    tools=[memory, save_structured_plan, get_legacy_tasks, get_current_datetime, calendar],
)

# --- 4. 运行 ---

print("🤖 时间盒教练已启动！(输入 'q' 退出)")
print("你可以说：'今天要做周报、写论文、还有回几个微信和买菜。'")
if handover_banner:
    print(handover_banner)

while True:
    user_input = input("\n你: ")
    if user_input.lower() in ["q", "quit", "exit"]:
        break

    # 用户口头确认后，自动尝试同步日历（防止模型迟迟不调用）
    if not _plan_synced and any(k in user_input for k in CONFIRM_KEYWORDS):
        sync_msg = _sync_today_plan_to_calendar()
        print(f"\n[日历同步] {sync_msg}")
        if sync_msg.startswith("✅"):
            _plan_synced = True

    # 将用户输入传给 Agent
    response = agent.input(user_input)
    print(f"\n教练: {response}")
