# backend/new_agent.py
# ADHD 专注力守护者 (The Guardian Agent)
#
# 作用：
# - 读取时间盒教练生成的结构化计划（daily_tasks_*.json）
# - 在每个时间盒开始时，用 TodoList 做微步启动
# - 运行中处理“念头停车场”（后台 WebFetch + 记忆存储）
# - 监控走神（简易心跳），收尾时释放奖励与停车场信息
#
# 运行方式：python new_agent.py

import os
import json
import datetime
import random
from typing import Optional

from dotenv import load_dotenv
from connectonion import Agent, Memory, GoogleCalendar, TodoList, WebFetch
from rich.console import Console
from rich.panel import Panel
try:
    import cowsay
except Exception:
    cowsay = None

# --- 常量与路径 ---

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ADHD_DIR = os.path.join(BASE_DIR, "adhd_brain")
os.makedirs(ADHD_DIR, exist_ok=True)

load_dotenv(os.path.join(BASE_DIR, ".env"))

PARKING_LOT_FILE = os.path.join(ADHD_DIR, "parking_lot_buffer.md")
STATE_FILE = os.path.join(ADHD_DIR, "guardian_state.json")
HANDOVER_NOTE_FILE = os.path.join(ADHD_DIR, "handover_note.json")

console = Console()
_latest_plan_data = None
_victory_shown = False
_handover_written = False

VICTORY_ASCII = [
    r"""
         \   ^__^
          \  (oo)\_______
             (__)\       )\/\
                 ||----w |
                 ||     ||
    """,
    r"""
      /\_/\
     ( o.o )
      > ^ <
    """,
    r"""
          __
         / _)
  .-^^^-/ /
 __/       /
<__.|_|-|_|
    """,
    r"""
          __.-._   _.-.__
       .-`      '.'      `-.
     .'                     `.
    /    YODA SAYS:            \
   |   Do or do not. There is   |
   |          no try.           |
    \                           /
     `.                       .'
       `-._               _.-'
            `-..___..-'
    """,
]

VICTORY_PHRASES = [
    "任务杀手！",
    "多巴胺满载！",
    "今日成就解锁！",
    "收工！把快乐装进口袋。",
    "大脑电量回满，去享受奖励吧！",
]

_COWSAY_COWS = [
    "cow",
    "tux",
    "dragon",
    "kitty",
    "stegosaurus",
]


# --- 工具函数 / 工具类 ---

def get_current_datetime() -> str:
    """返回当前本地时间，包含时区，供 Agent 感知。"""
    now = datetime.datetime.now().astimezone()
    return now.strftime("当前本地时间：%Y-%m-%d %H:%M:%S %Z (UTC%z)")


def _resolve_plan_path(date: Optional[str] = None) -> Optional[str]:
    """定位计划文件路径，优先今天，其次最近一次保存的计划。"""
    target_date = date or datetime.date.today().isoformat()
    today_path = os.path.join(ADHD_DIR, f"daily_tasks_{target_date}.json")
    if os.path.exists(today_path):
        return today_path
    candidates = sorted(
        f for f in os.listdir(ADHD_DIR) if f.startswith("daily_tasks_") and f.endswith(".json")
    )
    if not candidates:
        return None
    return os.path.join(ADHD_DIR, candidates[-1])


def _plan_date_from_path(path: str) -> datetime.date:
    """从 daily_tasks_YYYY-MM-DD.json 提取日期，失败则回退到今天。"""
    try:
        return datetime.datetime.strptime(os.path.basename(path), "daily_tasks_%Y-%m-%d.json").date()
    except ValueError:
        return datetime.date.today()


def _parse_task_time(value: Optional[str], plan_date: datetime.date, tzinfo) -> Optional[datetime.datetime]:
    """将时间字符串解析为带时区的 datetime，用计划日期补全缺失的日期。"""
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
            time_part = datetime.datetime.strptime(value, fmt).time()
            return datetime.datetime.combine(plan_date, time_part).replace(tzinfo=tzinfo)
        except ValueError:
            continue
    return None


def _normalize_plan_tasks(tasks: list, plan_date: datetime.date) -> list:
    """为任务补齐解析后的开始/结束时间，便于排序和判断当前时间段。"""
    tzinfo = datetime.datetime.now().astimezone().tzinfo
    normalized = []
    for task in tasks:
        start_dt = _parse_task_time(task.get("start"), plan_date, tzinfo)
        end_dt = _parse_task_time(task.get("end"), plan_date, tzinfo)
        normalized.append({**task, "start_dt": start_dt, "end_dt": end_dt})
    normalized.sort(key=lambda t: t["start_dt"] or datetime.datetime.max.replace(tzinfo=tzinfo))
    return normalized


def load_plan_for_startup(date: Optional[str] = None):
    """读取并解析计划，返回结构化数据和错误信息（二者之一）。"""
    path = _resolve_plan_path(date)
    if not path:
        target_date = date or datetime.date.today().isoformat()
        expected = os.path.join(ADHD_DIR, f"daily_tasks_{target_date}.json")
        return None, f"未找到计划文件：{expected}"
    try:
        with open(path, "r") as f:
            tasks = json.load(f)
    except Exception as exc:
        return None, f"读取计划失败（{path}）：{exc}"
    if not isinstance(tasks, list):
        return None, f"计划格式异常（期望列表）：{path}"
    plan_date = _plan_date_from_path(path)
    normalized = _normalize_plan_tasks(tasks, plan_date)
    plan_data = {"path": path, "plan_date": plan_date, "tasks": tasks, "normalized_tasks": normalized}
    global _latest_plan_data
    _latest_plan_data = plan_data
    return (plan_data, None)


def _format_dt(dt_value: Optional[datetime.datetime], plan_date: datetime.date) -> str:
    """友好格式化时间，若与今日日期不符则包含日期。"""
    if not dt_value:
        return "未标时间"
    today = datetime.date.today()
    show_full_date = dt_value.date() != plan_date or plan_date != today
    fmt = "%Y-%m-%d %H:%M" if show_full_date else "%H:%M"
    return dt_value.strftime(fmt)


def _determine_focus_task(normalized_tasks: list):
    """基于当前时间返回状态与要关注的任务。"""
    if not normalized_tasks:
        return "empty", None
    now = datetime.datetime.now().astimezone()
    timed_tasks = [t for t in normalized_tasks if t.get("start_dt")]
    if not timed_tasks:
        return "no_timed", normalized_tasks[0]
    for task in timed_tasks:
        start_dt = task["start_dt"]
        end_dt = task.get("end_dt") or start_dt
        if start_dt <= now <= end_dt:
            return "current", task
        if start_dt > now:
            return "upcoming", task
    return "finished", timed_tasks[-1]


def _parse_parking_lot_entries() -> list:
    """提取停车场条目文本，去除时间戳。"""
    if not os.path.exists(PARKING_LOT_FILE):
        return []
    with open(PARKING_LOT_FILE, "r") as f:
        content = f.read().strip()
    if not content:
        return []
    entries = []
    for block in content.split("\n\n"):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        if lines[0].startswith("[") and "]" in lines[0]:
            lines = lines[1:]
        if not lines:
            continue
        entries.append(" ".join(lines))
    return entries


def _get_last_timed_end(normalized_tasks: list) -> Optional[datetime.datetime]:
    """获取最后一个有时间的任务的结束时间。"""
    timed = [t for t in normalized_tasks if t.get("start_dt") or t.get("end_dt")]
    if not timed:
        return None
    last = timed[-1]
    return last.get("end_dt") or last.get("start_dt")


def _is_plan_finished(plan_data: dict) -> bool:
    """检查当前时间是否已超过最后一个任务的结束时间。"""
    last_end = _get_last_timed_end(plan_data.get("normalized_tasks", []))
    if not last_end:
        return False
    now = datetime.datetime.now().astimezone()
    return now > last_end


def _build_daily_report(plan_data: dict) -> str:
    """生成每日复盘报告文本。"""
    tasks = plan_data.get("tasks", [])
    normalized = plan_data.get("normalized_tasks", [])
    total_tasks = len(tasks)

    minutes = 0
    for task in normalized:
        start = task.get("start_dt")
        end = task.get("end_dt") or start
        if start and end:
            delta = (end - start).total_seconds() / 60
            if delta > 0:
                minutes += delta
    hours_text = f"{minutes/60:.1f}".rstrip("0").rstrip(".") or "0"

    report_lines = [f"你今天专注了 {hours_text} 小时，击败了 {total_tasks} 个任务。"]

    parking_entries = _parse_parking_lot_entries()
    if parking_entries:
        joined = "；".join(parking_entries)
        report_lines.append(f"你今天忍住没去做的 {len(parking_entries)} 件事：{joined}")
        report_lines.append("心理暗示：这些是你延迟满足的战利品，现在可以去做了！")
    else:
        report_lines.append("今天没有停车场条目，专注力拉满！")

    return "\n".join(report_lines)


def _victory_lap_text(plan_data: dict) -> str:
    phrase = random.choice(VICTORY_PHRASES)
    report = _build_daily_report(plan_data)

    # 尝试用 cowsay 随机角色输出奖励，如果不可用则用内置 ASCII
    art = random.choice(VICTORY_ASCII)
    if cowsay:
        try:
            list_fn = getattr(cowsay, "list_cows", None)
            available_all = list_fn() if callable(list_fn) else _COWSAY_COWS
            available = [c for c in _COWSAY_COWS if c in available_all] or available_all
            cow_name = random.choice(available) if available else "cow"
            get_fn = getattr(cowsay, "get_output_string", None)
            if callable(get_fn):
                art = get_fn(cow_name, phrase)
            else:
                cow_fn = getattr(cowsay, cow_name, None)
                if callable(cow_fn):
                    art = cow_fn(phrase)
        except Exception:
            art = random.choice(VICTORY_ASCII)

    return f"{art}\n\n{report}"


def show_victory_lap(plan_data: dict) -> None:
    """ASCII 剧场 Victory Lap。"""
    text = _victory_lap_text(plan_data)
    console.print(Panel(text, title="Victory Lap", border_style="green", expand=True))


def write_handover_note(contents: list[str]) -> str:
    payload = {
        "date": datetime.date.today().isoformat(),
        "content": contents,
        "status": "unread",
    }
    with open(HANDOVER_NOTE_FILE, "w") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return f"已写入交接留言（{len(contents)} 条）：{HANDOVER_NOTE_FILE}"


def prompt_handover_note() -> None:
    """向用户收集交接留言，可多条，写入 handover_note.json。"""
    global _handover_written
    if _handover_written:
        return
    notes: list[str] = []
    print("\n📩 有什么想嘱咐明天的计划师（Planner）的吗？比如“明天早起”或“把没写完的论文加进去”？")
    while True:
        note = input("留言内容（回车跳过）：").strip()
        if not note:
            if not notes:
                print("已跳过留言。")
            break
        notes.append(note)
        print(f"已记录：{note}")
        more = input("还要添加吗？输入 y 继续，回车结束：").strip().lower()
        if not more.startswith("y"):
            break
    _handover_written = True
    if not notes:
        return
    path_msg = write_handover_note(notes)
    print(path_msg)


def maybe_handle_completion(plan_data: Optional[dict] = None) -> None:
    """若任务已全部结束，则触发胜利巡游、复盘和交接。"""
    global _victory_shown
    data = plan_data
    if data is None:
        data, _ = load_plan_for_startup()
    if not data or _victory_shown:
        return
    if not _is_plan_finished(data):
        return
    _victory_shown = True
    show_victory_lap(data)
    prompt_handover_note()


def read_structured_plan(date: Optional[str] = None) -> str:
    """
    读取时间盒教练保存的结构化计划。
    Args:
        date: 可选，格式 YYYY-MM-DD；为空则读取今天。
    Returns:
        计划 JSON 字符串或错误提示。
    """
    path = _resolve_plan_path(date)
    if not path:
        target_date = date or datetime.date.today().isoformat()
        return f"未找到计划文件：{os.path.join(ADHD_DIR, f'daily_tasks_{target_date}.json')}"
    with open(path, "r") as f:
        return f.read()


def append_parking_lot(entry: str) -> str:
    """将念头停车场条目写入缓冲文件（时间戳 + 文本）。"""
    ts = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z (UTC%z)")
    with open(PARKING_LOT_FILE, "a") as f:
        f.write(f"[{ts}]\n{entry}\n\n")
    return f"已记录到停车场：{PARKING_LOT_FILE}"


def read_parking_lot() -> str:
    """读取念头停车场内容。"""
    if not os.path.exists(PARKING_LOT_FILE):
        return "停车场为空。"
    with open(PARKING_LOT_FILE, "r") as f:
        return f.read()


def clear_parking_lot() -> str:
    """清空念头停车场。"""
    if os.path.exists(PARKING_LOT_FILE):
        os.remove(PARKING_LOT_FILE)
    return "停车场已清空。"


# --- 停车场 TodoList 的代理函数（避免工具名冲突） ---

def parking_add(content: str, active_form: Optional[str] = None) -> str:
    """向停车场 TodoList 添加一项。active_form 为空则复用 content。"""
    return todo_parking.add(content, active_form or content)


def parking_complete(content: str) -> str:
    """完成停车场 Todo 项。"""
    return todo_parking.complete(content)


def parking_list() -> str:
    """列出停车场 Todo。"""
    return todo_parking.list()


def parking_clear() -> str:
    """清空停车场 TodoList。"""
    return todo_parking.clear()


def set_guardian_state(state: str) -> str:
    """设置状态机当前状态。"""
    payload = {"state": state, "updated_at": datetime.datetime.now().isoformat()}
    with open(STATE_FILE, "w") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return f"状态已更新为：{state}"


def get_guardian_state() -> str:
    """读取状态机当前状态。"""
    if not os.path.exists(STATE_FILE):
        return "state: Idle"
    with open(STATE_FILE, "r") as f:
        data = json.load(f)
    return f"state: {data.get('state', 'Idle')} (updated_at: {data.get('updated_at')})"


def announce_plan_on_startup() -> None:
    """启动时自动汇报今日计划与首个动作。"""
    plan_data, error = load_plan_for_startup()
    print(f"\n⏱️ {get_current_datetime()}")
    if error:
        print(f"⚠️ {error}")
        print("提示：先用时间盒教练生成计划 (daily_tasks_YYYY-MM-DD.json)。")
        return

    plan_date = plan_data["plan_date"]
    tasks = plan_data["tasks"]
    normalized = plan_data["normalized_tasks"]
    file_name = os.path.basename(plan_data["path"])

    print(f"🗂️ 读取到 {plan_date} 的计划（{file_name}），共 {len(tasks)} 条：")
    for idx, task in enumerate(tasks, start=1):
        start = task.get("start") or "-"
        end = task.get("end") or "-"
        title = task.get("title") or "未命名任务"
        print(f"{idx}. {start} -> {end} | {title}")

    today = datetime.date.today()
    if plan_date != today:
        print(f"提醒：计划日期为 {plan_date}，与当前日期 {today} 不同。")

    status, focus_task = _determine_focus_task(normalized)
    if status == "current":
        title = focus_task.get("title") or "当前任务"
        start_text = _format_dt(focus_task.get("start_dt"), plan_date)
        end_text = _format_dt(focus_task.get("end_dt") or focus_task.get("start_dt"), plan_date)
        print(f"🚦 现在应该在做：{title}（{start_text}-{end_text}）")
    elif status == "upcoming":
        title = focus_task.get("title") or "下一任务"
        start_text = _format_dt(focus_task.get("start_dt"), plan_date)
        print(f"⏭️ 下一步 {start_text} 开始：{title}")
    elif status == "finished":
        title = focus_task.get("title") or "最后任务"
        end_text = _format_dt(focus_task.get("end_dt") or focus_task.get("start_dt"), plan_date)
        print(f"✅ 计划时间段已结束。最后一项是：{title}（结束于 {end_text}）")
    elif status == "no_timed":
        title = focus_task.get("title") or "任务"
        print(f"📝 计划未写时间，从第一个任务开始：{title}")
    else:
        print("⚠️ 计划为空，请先生成今天的时间盒。")

    maybe_handle_completion(plan_data)


def ask_start_smoothness(plan_data: Optional[dict] = None) -> None:
    """启动时主动询问启动顺利度，便于后续是否触发“先做5分钟”提示。"""
    if _victory_shown:
        return
    data = plan_data or _latest_plan_data
    if data and _is_plan_finished(data):
        return
    print("\n👋 开始顺利吗？哪些任务有阻力或不想动？")
    print("说明：顺利的就直接开干，我不会重复“先做5分钟”；卡住的才用微步和 5 分钟起步。")


class ActivityMonitor:
    """
    简易走神监控：用“心跳”记录最近一次活动时间，检查是否超时。
    如果需要真实的鼠标监听，可在此基础上接入 pynput。
    """

    def __init__(self, idle_minutes: int = 5):
        self.idle_threshold = datetime.timedelta(minutes=idle_minutes)
        self.last_activity = datetime.datetime.now()

    def heartbeat(self, note: str = "") -> str:
        self.last_activity = datetime.datetime.now()
        suffix = f" | {note}" if note else ""
        return f"已记录活动时间：{self.last_activity.isoformat()}{suffix}"

    def check_idle(self) -> str:
        delta = datetime.datetime.now() - self.last_activity
        if delta >= self.idle_threshold:
            minutes = round(delta.total_seconds() / 60, 1)
            return f"idle: {minutes} min (超过阈值)"
        return "active"


class ParkingTodoList(TodoList):
    """专用于念头停车场的 TodoList，避免与主 TodoList 重名。"""
    pass


# --- 初始化工具 ---

memory = Memory(memory_dir="adhd_brain")
calendar = GoogleCalendar()
todo_main = TodoList()             # 主任务/微步启动
todo_parking = ParkingTodoList()   # 停车场 Todo（独立类名，避免注册冲突）
webfetch = WebFetch(timeout=20)    # 静默搜索
activity_monitor = ActivityMonitor(idle_minutes=8)


# --- 系统提示词 ---

guardian_system_prompt = """
你是 “ADHD 专注力守护者 (The Guardian Agent)” —— 一个常驻后台的执行教练。
你的目标：在时间盒执行期，用可视化进度与温柔提醒，陪伴用户完成任务。

## 严禁幻觉 / 边界
- 只能基于 `read_structured_plan()` 读取的计划内容说话，**禁止**自己生成/猜测新的任务或明天/未来的计划。
- 如果计划文件缺失或无法读取，明确说“未找到计划文件”，请用户去时间盒教练 (Planner) 生成；不要臆测或替用户规划。
- 不要为明天写计划，不要补充不存在的任务时间，不能擅自改写任务标题。
- 若用户问“明天/新计划”，回复“我是执行守护者，不负责排程，请用时间盒教练生成”，不要输出任何假计划。

## 状态机 (保持状态文件同步)
- Idle：等待下一个时间盒。
- Starting：时间到但用户未动，启动“微步”引导，使用 TodoList 清单。
- Running：专注进行中，开启念头停车场与走神检测。
- Closing：收尾，庆祝并释放停车场内容。
使用 `set_guardian_state` / `get_guardian_state` 显式标记状态。

## 输入/数据来源
- `read_structured_plan()`：读取 Agent A 的 JSON 计划。优先使用时间盒名称、起止时间。
- `get_current_datetime()`：报时、感知当前日期。

## 核心玩法
0) 开始前问询
   - 第一句先问：“开始顺利吗？哪些任务有阻力或不想动？”
   - 用户说“顺利/已经开始”的任务，不要反复说“先做5分钟”；只对卡住/抗拒/拖延的任务用“先做5分钟”微步。

1) 微步启动 (Starting)
   - 当用户表明“卡住/不想开始”或你检测到迟疑时：TodoList.clear()，生成 3-5 个超小起步动作，调用 add()/start()，逐项 complete()。
   - 只对卡住的任务提醒：“只做 5 分钟就好”；顺利的任务无需重复。

2) 念头停车场 (Running)
   - 离题请求：不要立刻喂结果。
   - 若需搜索，后台用 WebFetch.fetch()/strip_tags()/analyze_page()，摘要写入 `append_parking_lot` 或 todo_parking。
   - 回复用户：“我记下并查好了，先专注当前任务，结果在停车场等你。”

3) 走神检测
   - 周期性调用 activity_monitor.check_idle()；超时提醒：“还没勾掉 TodoList 上的 <当前项>，要不要卡点完成？”

4) 收尾 (Closing)
   - 展示 TodoList 进度；肯定用户；调用 read_parking_lot() 释放停车场内容，再 clear_parking_lot()。
   - 未完成任务：建议标记“移至明天”，避免完美主义。

5) 日程同步/调整
   - 如用户要求修改/删除日程，可调用 GoogleCalendar 对应接口（保持正确时区）。

## 语气
- 温柔、鼓励、简短指令式，避免长篇说教。
- 优先行动（调用工具），减少空话。
""".strip()


# --- 创建 Agent ---

guardian_agent = Agent(
    name="adhd_guardian",
    model="co/gemini-2.5-pro",
    system_prompt=guardian_system_prompt,
    tools=[
        memory,
        todo_main,
        webfetch,
        activity_monitor,
        read_structured_plan,
        append_parking_lot,
        read_parking_lot,
        clear_parking_lot,
        parking_add,
        parking_complete,
        parking_list,
        parking_clear,
        set_guardian_state,
        get_guardian_state,
        get_current_datetime,
        calendar,
    ],
)


# --- 运行入口 ---

def main():
    print("🛡️ ADHD 专注力守护者已启动！(输入 'q' 退出)")
    print("提示：先用 Agent A (时间盒教练) 生成计划，再让我来执行。")
    announce_plan_on_startup()
    ask_start_smoothness(_latest_plan_data)
    while True:
        user_input = input("\n你: ")
        if user_input.lower() in ["q", "quit", "exit"]:
            break
        response = guardian_agent.input(user_input)
        print(f"\n守护者: {response}")
        maybe_handle_completion()


if __name__ == "__main__":
    main()
