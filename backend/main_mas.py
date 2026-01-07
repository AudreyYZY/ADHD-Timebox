"""Phase 1 entrypoint for the MAS orchestrator."""

from agents.orchestrator import OrchestratorAgent
from tools.idle_watcher import IdleWatcher


def _build_idle_handler(orchestrator: OrchestratorAgent):
    def _on_idle(payload):
        try:
            event_type = payload.get("type", "idle_alert")
            idle_seconds = int(payload.get("idle_seconds") or 0)
            idle_minutes = max(idle_seconds // 60, 1)
            window = payload.get("active_window") or "未知窗口"
            focus_state = (
                payload.get("focus_state") if isinstance(payload, dict) else {}
            )
            active_task = (
                focus_state.get("active_task") if isinstance(focus_state, dict) else {}
            )
            task_title = (active_task or {}).get("title") or "当前任务"

            if event_type == "routine_check":
                # 主动轮询：检查 Active Window 与 Task 是否相关
                # 不提 idle 时间，只关注上下文匹配
                message = f"[ROUTINE_CHECK] 当前窗口：{window}。当前任务：{task_title}"
            else:
                # 默认 idle_alert
                message = f"[IDLE_ALERT] 已空闲约 {idle_minutes} 分钟。当前窗口：{window}。当前任务：{task_title}"

            resp = orchestrator.focus_agent.handle(message)
            content = resp.get("content") if isinstance(resp, dict) else str(resp)

            # 如果是 Routine Check 且 Agent 认为应该保持沉默 (<<SILENCE>>)，则不输出任何内容
            if event_type == "routine_check" and "<<SILENCE>>" in content:
                return

            # 移除标记，展示真实内容
            display_content = content.replace("<<SILENCE>>", "").strip()
            if not display_content:
                return

            header = "⚠️ 走神检测" if event_type == "idle_alert" else "🛡️ 上下文监测"
            print(f"\n{header}\n{display_content}\n(提示：输入任意内容继续对话)")

        except Exception as exc:
            print(f"[IdleWatcher] 推送提醒失败：{exc}")

    return _on_idle


def main():
    orchestrator = OrchestratorAgent()
    idle_watcher = IdleWatcher(
        context_tool=orchestrator.focus_agent.context_tool,
        on_idle=_build_idle_handler(orchestrator),
        interval_seconds=30,
        idle_threshold_seconds=300,  # 5分钟不动 -> 提醒
        cooldown_seconds=600,  # 提醒后 10分钟不打扰
        focus_only=True,
        routine_check_seconds=300,  # 每 5 分钟检查一次窗口相关性 (无论是否动鼠标)
    )
    idle_watcher.start()

    print("\n" + "=" * 40)
    print("🤖 ADHD 时间盒助手 (MAS版) 已启动")
    print("=" * 40)
    print("我可以帮你减轻负担，专注于当下：")
    print("1. 📅 规划日程：输入 '今天要做...' 或 '把会议推迟10分钟'")
    print("2. 🧘 专注执行：输入 '开始任务' 进入心流模式")
    print("3. 💡 念头停泊：随时输入 '记一下...' 把杂念暂存")
    print("-" * 40)

    # 检查今日任务
    tasks_summary = orchestrator.plan_manager.list_tasks()
    if "今日无计划" in tasks_summary or "未找到计划文件" in tasks_summary:
        print("👇 今日首次使用，请告诉我你今天有哪些任务？")
    else:
        print("📅 今日计划概览：")
        print(tasks_summary)
        print("\n👇 请指示下一步 (如：'开始第一项'、'推迟10分钟'...)")

    try:
        while True:
            user_input = input("\n你: ").strip()
            if user_input.lower() in {"q", "quit", "exit"}:
                print("👋 系统退出，再见。")
                break
            try:
                orchestrator.route(user_input)
            except KeyboardInterrupt:
                print("\n👋 系统退出，再见。")
                break
            except Exception as exc:
                print(f"[错误] {exc}")
    finally:
        idle_watcher.stop()


if __name__ == "__main__":
    main()
