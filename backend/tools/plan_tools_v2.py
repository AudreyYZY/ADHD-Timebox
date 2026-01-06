import datetime
import json
import os
import re
from typing import Dict, List, Optional, Tuple, Union


# 【新增 1】定义一个强力调试函数，直接写文件，绕过控制台
def debug_log(message):
    try:
        # 获取 backend 目录 (假设当前脚本在 backend/tools 下)
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        log_path = os.path.join(base_dir, "FORCE_DEBUG.txt")

        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {message}\n")
    except Exception:
        pass  # 绝不报错


# 【新增 2】模块加载证明
debug_log(">>> plan_tools_v2 模块已被加载！<<<")


class PlanManager:
    """
    管理 daily_tasks_YYYY-MM-DD.json 的读写与冲突检测。
    设计目标：为 PlannerAgent 提供可靠的上下文感知与时间盒调整能力。
    """

    def __init__(self, plan_dir: Optional[str] = None, calendar=None):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        default_plan_dir = os.path.join(base_dir, "adhd_brain")
        self.plan_dir = plan_dir or default_plan_dir
        os.makedirs(self.plan_dir, exist_ok=True)
        self.calendar = calendar

    # -- 公共方法 --

    def get_current_context(self) -> str:
        """
        返回当前日期/时间/时区，以及今日计划摘要（若存在）。
        确保 Agent 在生成或调整时不会落入过去时间。
        """
        now = datetime.datetime.now().astimezone()
        now_text = now.strftime("%Y-%m-%d %H:%M %Z (UTC%z)")
        today = now.date()
        tasks, path, err = self._load_tasks(today.isoformat(), create_if_missing=False)
        header = f"当前时间：{now_text}"
        if err:
            return f"{header}\n今日计划读取失败：{err}"
        if tasks is None or not tasks:
            return (
                f"{header}\n今日尚未生成计划文件：{self._plan_path(today.isoformat())}"
            )

        summary_lines = []
        plan_date = self._plan_date_from_path(path)
        normalized = self._normalize_for_summary(tasks, plan_date)
        for idx, task in enumerate(normalized, start=1):
            start_text = (
                task["start_dt"].strftime("%H:%M")
                if task["start_dt"]
                else (task["raw_start"] or "-")
            )
            end_text = (
                task["end_dt"].strftime("%H:%M")
                if task["end_dt"]
                else (task["raw_end"] or "-")
            )
            duration = self._format_duration(task["start_dt"], task["end_dt"])
            duration_mark = f" ({duration}分钟)" if duration else ""
            title = task.get("title") or f"任务{idx}"
            status = task.get("status", "pending")
            status_mark = f" [{status}]" if status != "pending" else ""
            summary_lines.append(
                f"{idx}. {start_text}-{end_text}{duration_mark} | {title}{status_mark}"
            )
        summary = "\n".join(summary_lines)
        return f"{header}\n今日计划：\n{summary}"

    def create_daily_plan(self, tasks: Union[List[Dict], str]) -> str:
        """
        [智能合并模式] 更新或创建今日计划。
        如果今日已有计划，会将新传入的任务合并进去（Upsert），而不是直接覆盖。
        这防止了 Agent 只传新任务导致旧任务丢失的问题。
        """
        # 【新增】函数入口证明
        debug_log(f"create_daily_plan (Smart Merge) 被调用！参数类型: {type(tasks)}")
        debug_log(f"原始数据摘要: {str(tasks)[:100]}...")

        # --- 1. 参数解析与校验 ---
        original_tasks = tasks
        if isinstance(tasks, str):
            try:
                tasks = json.loads(tasks)
            except json.JSONDecodeError as exc:
                err_msg = f"JSON 解析崩溃: {exc}"
                debug_log(err_msg)
                return f"❌ 计划生成失败：tasks 解析错误：{exc}"

        if not isinstance(tasks, list):
            err_msg = f"类型错误: 期望 list, 实际是 {type(original_tasks).__name__}"
            debug_log(err_msg)
            return f"❌ 计划生成失败：tasks 必须是列表。"

        now = datetime.datetime.now().astimezone()
        plan_date = now.date()

        # --- 2. 预处理新任务 (Normalization) ---
        # 这里我们先处理新进来的任务，确保格式正确
        normalized_new_tasks = []
        errors = []

        for idx, task in enumerate(tasks):
            if not isinstance(task, dict):
                continue

            title = (task.get("title") or "").strip()
            if not title:
                continue  # 跳过无标题任务

            # 时间解析
            start_dt = self._normalize_to_dt(task.get("start"), plan_date)
            end_dt = self._normalize_to_dt(task.get("end"), plan_date)

            # 基础逻辑校验
            if not start_dt or not end_dt:
                errors.append(f"任务 '{title}' 时间格式错误")
                continue

            # 简单的日期检查
            if start_dt.date() != plan_date:
                # 如果Agent传了非今天的日期，这里记录一下但暂不严格阻断
                debug_log(f"Warning: 任务 {title} 日期 {start_dt.date()} 不是今天")
                pass

            normalized_task = {**task}
            # 确保有ID，如果没有就用 title 或时间戳生成
            if not normalized_task.get("id"):
                normalized_task["id"] = f"task_{int(now.timestamp())}_{idx}"

            normalized_task["title"] = title
            normalized_task["start"] = start_dt.strftime("%Y-%m-%d %H:%M")
            normalized_task["end"] = end_dt.strftime("%Y-%m-%d %H:%M")
            normalized_task.setdefault("type", "work")
            # 新任务默认pending，除非传入了特定状态
            normalized_task.setdefault("status", "pending")

            normalized_new_tasks.append(normalized_task)

        if not normalized_new_tasks and errors:
            debug_log(f"任务校验失败: {errors}")
            return "❌ 无法添加任务：" + "；".join(errors)

        # --- 3. 核心修改：读取旧数据并合并 (Smart Merge) ---

        # 尝试读取今天已有的文件
        existing_tasks, path, _ = self._load_tasks(
            plan_date.isoformat(), create_if_missing=True
        )
        if existing_tasks is None:
            existing_tasks = []

        # 使用字典进行合并，以 title 或 id 作为唯一键
        # 策略：以 existing_tasks 为基础，用 normalized_new_tasks 去更新它
        task_map = {}
        for t in existing_tasks:
            key = t.get("id") or t.get("title")
            task_map[key] = t

        added_count = 0
        updated_count = 0
        sync_success = 0
        sync_errors: List[str] = []

        for new_t in normalized_new_tasks:
            key = new_t.get("id") or new_t.get("title")
            if not key:
                continue

            old_task = task_map.get(key)
            merged_task = {**(old_task or {}), **new_t}

            # 保留旧状态（若新任务未显式传入）
            if old_task and "status" not in new_t:
                merged_task["status"] = old_task.get("status", "pending")
            merged_task.setdefault("status", "pending")

            # 承袭或写回关联的 calendar event id
            merged_task["google_event_id"] = merged_task.get("google_event_id") or (
                old_task.get("google_event_id") if old_task else None
            )

            action = "update" if old_task else "create"
            # 如果内容完全未变且已有 event id，则跳过多余的日历调用
            needs_sync = True
            if old_task:
                unchanged = (
                    merged_task.get("google_event_id")
                    and merged_task.get("start") == old_task.get("start")
                    and merged_task.get("end") == old_task.get("end")
                    and merged_task.get("title") == old_task.get("title")
                )
                needs_sync = not unchanged

            if needs_sync:
                synced, event_id, sync_msg = self._sync_calendar(merged_task, action)
                merged_task["google_event_id"] = event_id or merged_task.get(
                    "google_event_id"
                )
                if synced:
                    sync_success += 1
                elif sync_msg:
                    sync_errors.append(
                        f"{merged_task.get('title')}: {sync_msg.lstrip('，')}"
                    )

            task_map[key] = merged_task
            if old_task:
                updated_count += 1
            else:
                added_count += 1

        final_tasks = list(task_map.values())
        final_tasks.sort(key=lambda t: t.get("start", ""))

        # --- 4. 写入文件 ---
        debug_log(f"准备写入文件，目标路径: {path}，任务数: {len(final_tasks)}")
        write_err = self._write_tasks(path, final_tasks)
        if write_err:
            debug_log(f"❌ 致命错误：文件写入失败 - {write_err}")
            return f"❌ 文件写入失败：{write_err}"

        # --- 5. 日历同步反馈 ---
        sync_msg = ""
        if sync_success:
            sync_msg = f" (已同步 {sync_success} 个到日历)"
        if sync_errors:
            sync_msg = f"{sync_msg}（同步失败 {len(sync_errors)} 个，详见日志）"

        action_msg = []
        if added_count:
            action_msg.append(f"新增 {added_count} 个")
        if updated_count:
            action_msg.append(f"更新 {updated_count} 个")

        result_msg = f"✅ 计划已更新。{'，'.join(action_msg)}。当前共有 {len(final_tasks)} 个任务。{sync_msg}"
        return result_msg

    def update_schedule(
        self, task_id: str, new_start: str, new_end: str, force: bool = False
    ) -> str:
        """
        修改已有任务或插入新任务。
        - 冲突时返回 CONFLICT 消息（除非 force=True）
        - 成功后写回 JSON，并尝试同步日历
        """
        plan_date_str = datetime.date.today().isoformat()
        tasks, path, err = self._load_tasks(plan_date_str, create_if_missing=True)
        if err:
            return f"❌ 更新失败：{err}"
        if tasks is None:
            return f"❌ 更新失败：计划文件格式异常：{path}"

        plan_date = self._plan_date_from_path(path)
        start_dt = self._normalize_to_dt(new_start, plan_date)
        end_dt = self._normalize_to_dt(new_end, plan_date)
        if not start_dt or not end_dt:
            return f"❌ 时间格式无法解析：{new_start} -> {new_end}"
        if start_dt.date() != plan_date or end_dt.date() != plan_date:
            return f"❌ 仅支持调整今日（{plan_date.isoformat()}）的时间盒。"
        if end_dt <= start_dt:
            return "❌ 结束时间必须晚于开始时间。"
        if start_dt < datetime.datetime.now().astimezone():
            return f"❌ 新开始时间 {start_dt.strftime('%H:%M')} 早于当前时间。"

        target_task = self._find_task(tasks, task_id)
        conflicts = self._find_conflicts(
            tasks, start_dt, end_dt, plan_date, exclude=target_task
        )

        if conflicts and not force:
            conflict_names = ", ".join(
                [c.get("title") or c.get("id") or "未命名任务" for c in conflicts]
            )
            return f"CONFLICT: {conflict_names}"

        if conflicts:
            for c in conflicts:
                # 优先删除对应的日历事件，防止“旧事件叠加”
                self._sync_calendar(c, "delete")
                tasks.remove(c)

        start_text = start_dt.strftime("%Y-%m-%d %H:%M")
        end_text = end_dt.strftime("%Y-%m-%d %H:%M")
        created = False

        if target_task:
            target_task["start"] = start_text
            target_task["end"] = end_text
        else:
            new_task = {
                "id": task_id,
                "title": task_id,
                "start": start_text,
                "end": end_text,
                "type": "work",
                "status": "pending",  # 默认状态
                "google_event_id": None,
            }
            tasks.append(new_task)
            target_task = new_task
            created = True

        tasks.sort(key=lambda t: t.get("start", ""))

        action_for_calendar = (
            "create" if created or not target_task.get("google_event_id") else "update"
        )
        _, event_id, sync_msg = self._sync_calendar(target_task, action_for_calendar)
        if event_id:
            target_task["google_event_id"] = event_id

        write_err = self._write_tasks(path, tasks)
        if write_err:
            return f"❌ 文件写入失败：{write_err}"

        action = "已添加" if created else "已更新"
        replaced = f"，替换了 {len(conflicts)} 个冲突任务" if conflicts else ""
        return f"✅ {action} {task_id}: {start_text[11:]}-{end_text[11:]}{replaced}{sync_msg}"

    def list_tasks(self) -> str:
        """列出今日计划的所有任务及状态。"""
        today = datetime.date.today().isoformat()
        tasks, path, err = self._load_tasks(today, create_if_missing=False)
        if err:
            return f"❌ {err}"
        if tasks is None or not tasks:
            return f"今日无计划：{self._plan_path(today)}"

        plan_date = self._plan_date_from_path(path)
        normalized = self._normalize_for_summary(tasks, plan_date)
        lines = [f"计划文件：{path}"]
        for idx, task in enumerate(normalized, start=1):
            start_text = (
                task["start_dt"].strftime("%H:%M")
                if task["start_dt"]
                else (task["raw_start"] or "-")
            )
            end_text = (
                task["end_dt"].strftime("%H:%M")
                if task["end_dt"]
                else (task["raw_end"] or "-")
            )
            duration = self._format_duration(task["start_dt"], task["end_dt"])
            duration_mark = f" ({duration}分钟)" if duration else ""
            title = task.get("title") or f"任务{idx}"
            status = task.get("status", "pending")
            lines.append(
                f"{idx}. {start_text}-{end_text}{duration_mark} | {title} [{status}]"
            )
        return "\n".join(lines)

    # -- 内部辅助方法 --

    def _plan_path(self, date_str: str) -> str:
        return os.path.join(self.plan_dir, f"daily_tasks_{date_str}.json")

    def _plan_date_from_path(self, path: str) -> datetime.date:
        try:
            return datetime.datetime.strptime(
                os.path.basename(path).replace("daily_tasks_", "").replace(".json", ""),
                "%Y-%m-%d",
            ).date()
        except Exception:
            return datetime.date.today()

    def _load_tasks(
        self, target_date: str, create_if_missing: bool
    ) -> Tuple[Optional[List[Dict]], str, Optional[str]]:
        path = self._plan_path(target_date)
        if not os.path.exists(path):
            if create_if_missing:
                return [], path, None
            return None, path, f"未找到计划文件：{path}"
        try:
            with open(path, "r") as f:
                tasks = json.load(f)
        except Exception as exc:
            return None, path, f"读取计划失败：{exc}"
        if not isinstance(tasks, list):
            return None, path, "计划文件格式应为列表。"
        return tasks, path, None

    def _write_tasks(self, path: str, tasks: List[Dict]) -> Optional[str]:
        """Persist tasks list to disk, returning error text on failure."""
        try:
            with open(path, "w") as f:
                json.dump(tasks, f, ensure_ascii=False, indent=2)
            return None
        except Exception as exc:
            return str(exc)

    def _normalize_to_dt(
        self, raw_value: Optional[str], plan_date: datetime.date
    ) -> Optional[datetime.datetime]:
        """将各种常见格式解析为带时区的 datetime。"""
        if not raw_value or not isinstance(raw_value, str):
            return None
        value = raw_value.strip()
        tzinfo = datetime.datetime.now().astimezone().tzinfo

        try:
            dt = datetime.datetime.fromisoformat(value.replace("T", " "))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=tzinfo)
            return dt.astimezone(tzinfo)
        except Exception:
            pass

        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
            try:
                dt = datetime.datetime.strptime(value, fmt)
                return dt.replace(tzinfo=tzinfo)
            except ValueError:
                continue

        for fmt in ("%H:%M:%S", "%H:%M"):
            try:
                t = datetime.datetime.strptime(value, fmt).time()
                return datetime.datetime.combine(plan_date, t).replace(tzinfo=tzinfo)
            except ValueError:
                continue

        return None

    def _find_task(self, tasks: List[Dict], task_id: str) -> Optional[Dict]:
        for task in tasks:
            if task.get("id") == task_id or task.get("title") == task_id:
                return task
        return None

    def _find_conflicts(
        self,
        tasks: List[Dict],
        start_dt: datetime.datetime,
        end_dt: datetime.datetime,
        plan_date: datetime.date,
        exclude: Optional[Dict] = None,
    ) -> List[Dict]:
        conflicts: List[Dict] = []
        for task in tasks:
            if task is exclude:
                continue
            t_start = self._normalize_to_dt(task.get("start"), plan_date)
            t_end = self._normalize_to_dt(task.get("end"), plan_date)
            if not t_start or not t_end:
                continue
            if start_dt < t_end and end_dt > t_start:
                conflicts.append(task)
        return conflicts

    def _normalize_for_summary(
        self, tasks: List[Dict], plan_date: datetime.date
    ) -> List[Dict]:
        """为摘要排序并附带解析后的时间，便于展示。"""
        normalized = []
        for task in tasks:
            start_dt = self._normalize_to_dt(task.get("start"), plan_date)
            end_dt = self._normalize_to_dt(task.get("end"), plan_date)
            normalized.append(
                {
                    **task,
                    "start_dt": start_dt,
                    "end_dt": end_dt,
                    "raw_start": task.get("start"),
                    "raw_end": task.get("end"),
                }
            )
        normalized.sort(
            key=lambda t: t.get("start_dt")
            or datetime.datetime.max.replace(
                tzinfo=datetime.datetime.now().astimezone().tzinfo
            )
        )
        return normalized

    def _format_duration(
        self,
        start_dt: Optional[datetime.datetime],
        end_dt: Optional[datetime.datetime],
    ) -> Optional[int]:
        """Calculate duration in minutes if both times are valid and positive."""
        if not start_dt or not end_dt:
            return None
        try:
            minutes = int((end_dt - start_dt).total_seconds() // 60)
            return minutes if minutes > 0 else None
        except Exception:
            return None

    def _format_calendar_time(self, value: Optional[str]) -> Optional[str]:
        """Normalize stored 'YYYY-MM-DD HH:MM' to ISO-like 'YYYY-MM-DDTHH:MM:SS'."""
        if not value or not isinstance(value, str):
            return None
        text = value.strip()
        if "T" not in text and " " in text:
            text = text.replace(" ", "T")
        if "T" not in text:
            return text
        # Ensure seconds are present to satisfy GoogleCalendar parser
        if len(text.split("T", 1)[1]) == 5:
            text = f"{text}:00"
        return text

    def _extract_event_id(self, response: Union[str, Dict]) -> Optional[str]:
        """Best-effort extraction of event id from ConnectOnion GoogleCalendar responses."""
        if isinstance(response, dict):
            if "id" in response:
                return str(response.get("id"))
            if "event_id" in response:
                return str(response.get("event_id"))
        if not response:
            return None
        text = str(response)
        match = re.search(r"Event ID:\s*([^\s]+)", text)
        if match:
            return match.group(1).strip()
        match = re.search(r"Event deleted:\s*([^\s]+)", text)
        if match:
            return match.group(1).strip()
        return None

    def _sync_calendar(self, task: Dict, action: str) -> Tuple[bool, Optional[str], str]:
        """
        尝试同步到 Google Calendar，失败不抛异常。
        返回 (是否成功, event_id, 反馈文案)；action: create/update/delete
        """
        title = task.get("title") or task.get("id") or "未命名任务"
        event_id = task.get("google_event_id")
        start = task.get("start")
        end = task.get("end")

        # 1. 防御性校验
        if not self.calendar or isinstance(self.calendar, str):
            debug_log(f"[Calendar] 未配置或类型错误: {type(self.calendar)}")
            return False, event_id, ""
        if hasattr(self.calendar, "reason"):
            debug_log(f"[Calendar] 处于 Fallback 模式: {self.calendar.reason}")
            return False, event_id, ""

        iso_start = self._format_calendar_time(start)
        iso_end = self._format_calendar_time(end)
        if action in {"create", "update"} and (not iso_start or not iso_end):
            debug_log(
                f"[Calendar] 时间格式异常，跳过同步: {title} | {start}-{end} ({action})"
            )
            return False, event_id, ""

        # 2. 删除旧事件（用于冲突清理）
        if action == "delete":
            if not event_id:
                debug_log(f"[Calendar] 跳过删除：任务无 event_id {title}")
                return False, None, ""
            if not hasattr(self.calendar, "delete_event"):
                debug_log("[Calendar] 对象缺少 delete_event 方法")
                return False, event_id, ""
            try:
                try:
                    resp = self.calendar.delete_event(event_id=event_id)
                except TypeError:
                    resp = self.calendar.delete_event(event_id)
                debug_log(f"[Calendar] ✅ 删除成功 {event_id} | 响应: {resp}")
                return True, None, ""
            except Exception as exc:
                debug_log(f"[Calendar] ❌ 删除失败 {event_id}: {exc}")
                return False, event_id, f"，但日历同步失败：{exc}"

        # 3. 创建新事件
        def _create_event() -> Tuple[bool, Optional[str], str]:
            if not hasattr(self.calendar, "create_event"):
                debug_log("[Calendar] 对象缺少 create_event 方法")
                return False, event_id, ""
            try:
                try:
                    resp = self.calendar.create_event(
                        title=title, start_time=iso_start, end_time=iso_end
                    )
                except TypeError:
                    resp = self.calendar.create_event(
                        title=title, start=iso_start, end=iso_end
                    )
                new_id = self._extract_event_id(resp) or event_id
                debug_log(f"[Calendar] ✅ 创建成功 {title} | id={new_id} | 响应: {resp}")
                return True, new_id, "，并已同步到日历"
            except Exception as exc:
                debug_log(
                    f"[Calendar] ❌ 创建失败 {title} {iso_start}-{iso_end}: {exc}"
                )
                return False, event_id, f"，但日历同步失败：{exc}"

        # 4. 更新事件，失败则降级创建
        if action == "update" and event_id and hasattr(self.calendar, "update_event"):
            try:
                try:
                    resp = self.calendar.update_event(
                        event_id=event_id,
                        title=title,
                        start_time=iso_start,
                        end_time=iso_end,
                    )
                except TypeError:
                    resp = self.calendar.update_event(
                        event_id,
                        title=title,
                        start=iso_start,
                        end=iso_end,
                    )
                new_id = self._extract_event_id(resp) or event_id
                debug_log(f"[Calendar] ✅ 更新成功 {title} | id={new_id} | 响应: {resp}")
                return True, new_id, "，并已同步到日历"
            except Exception as exc:
                debug_log(
                    f"[Calendar] 更新失败，尝试重新创建 {title} ({event_id}): {exc}"
                )
                return _create_event()

        # 默认走创建逻辑
        return _create_event()
