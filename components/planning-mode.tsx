"use client";

import React from "react";

import { useState, useRef, useEffect } from "react";
import { useChat } from "@ai-sdk/react";
import { TextStreamChatTransport } from "ai";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useAppStore, type Task } from "@/lib/store";
import { cn } from "@/lib/utils";
import { Send, Play, Clock } from "lucide-react";

function getMessageText(message: { parts?: Array<{ type: string; text?: string }> }): string {
  if (!message.parts || !Array.isArray(message.parts)) return "";
  return message.parts
    .filter((p): p is { type: "text"; text: string } => p.type === "text")
    .map((p) => p.text)
    .join("");
}

function PendingIndicator() {
  return (
    <div className="flex justify-start">
      <div
        className="rounded-2xl border border-border bg-card px-4 py-3"
        role="status"
        aria-live="polite"
      >
        <div className="flex gap-1">
          <span
            className="h-2 w-2 rounded-full bg-muted-foreground/40 animate-bounce"
            style={{ animationDelay: "0ms" }}
          />
          <span
            className="h-2 w-2 rounded-full bg-muted-foreground/40 animate-bounce"
            style={{ animationDelay: "150ms" }}
          />
          <span
            className="h-2 w-2 rounded-full bg-muted-foreground/40 animate-bounce"
            style={{ animationDelay: "300ms" }}
          />
        </div>
        <span className="sr-only">Assistant is thinking</span>
      </div>
    </div>
  );
}

export function PlanningMode() {
  const [input, setInput] = useState("");
  const [taskTitle, setTaskTitle] = useState("");
  const [taskDuration, setTaskDuration] = useState(15);
  const [showTaskForm, setShowTaskForm] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const { setCurrentTask, setUserState, setTimeRemaining, setIsTimerRunning, addTask } = useAppStore();

  const { messages, sendMessage, status } = useChat({
    transport: new TextStreamChatTransport({ api: "/api/chat/stream" }),
  });

  const isLoading = status === "streaming" || status === "submitted";

  // ✅ IME 处理：避免 Enter 结束组词时直接触发发送
  const [isComposing, setIsComposing] = useState(false);
  const lastCompositionEndRef = useRef(0);
  const shouldBlockEnterSend = () => Date.now() - lastCompositionEndRef.current < 80;

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    // ✅ 双保险：IME 组词中 or 刚结束组词的那一下 Enter，不发送
    if (isComposing || shouldBlockEnterSend()) return;

    if (!input.trim() || isLoading) return;
    sendMessage({ text: input });
    setInput("");
  };

  const handleStartTask = () => {
    if (!taskTitle.trim()) return;

    const newTask: Task = {
      id: crypto.randomUUID(),
      title: taskTitle,
      duration: taskDuration,
      createdAt: new Date(),
      status: "in-progress",
      startedAt: new Date(),
    };

    addTask(newTask);
    setCurrentTask(newTask);
    setTimeRemaining(taskDuration * 60);
    setIsTimerRunning(true);
    setUserState("focusing");
    setShowTaskForm(false);
    setTaskTitle("");
  };

  const durationOptions = [5, 10, 15, 20, 25];

  return (
    <div className="flex flex-1 flex-col">
      {/* Chat messages */}
      <div className="flex-1 space-y-4 pb-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <div className="mb-4 h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center">
              <Clock className="h-8 w-8 text-primary" />
            </div>
            <h2 className="text-xl font-medium text-foreground mb-2">
              What would you like to work on?
            </h2>
            <p className="text-muted-foreground max-w-sm">
              Tell me what's on your mind. I'll help you turn it into something doable.
            </p>
          </div>
        )}

        {messages.map((message) => {
          const text = getMessageText(message);
          if (!text) return null;

          return (
            <div
              key={message.id}
              className={cn(
                "flex",
                message.role === "user" ? "justify-end" : "justify-start"
              )}
            >
              <div
                className={cn(
                  "max-w-[85%] rounded-2xl px-4 py-3",
                  message.role === "user"
                    ? "bg-primary text-primary-foreground"
                    : "bg-card border border-border text-card-foreground"
                )}
              >
                <p className="text-sm leading-relaxed whitespace-pre-wrap">
                  {text}
                </p>
              </div>
            </div>
          );
        })}

        {(() => {
          const lastMessage = messages[messages.length - 1];
          const lastMessageText = lastMessage ? getMessageText(lastMessage) : "";
          const waitingForAssistant =
            status === "submitted" ||
            (status === "streaming" &&
              (!lastMessage ||
                lastMessage.role !== "assistant" ||
                !lastMessageText));

          return waitingForAssistant ? <PendingIndicator /> : null;
        })()}

        <div ref={messagesEndRef} />
      </div>

      {/* Task creation form */}
      {showTaskForm && (
        <div className="mb-4 rounded-xl border border-border bg-card p-4">
          <h3 className="text-sm font-medium text-foreground mb-3">Create a task</h3>
          <input
            type="text"
            value={taskTitle}
            onChange={(e) => setTaskTitle(e.target.value)}
            placeholder="What will you work on?"
            className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm mb-3 focus:outline-none focus:ring-2 focus:ring-ring"
            autoFocus
          />
          <div className="mb-4">
            <p className="text-xs text-muted-foreground mb-2">How long?</p>
            <div className="flex gap-2">
              {durationOptions.map((d) => (
                <button
                  key={d}
                  onClick={() => setTaskDuration(d)}
                  className={cn(
                    "rounded-lg px-3 py-1.5 text-sm transition-colors",
                    taskDuration === d
                      ? "bg-primary text-primary-foreground"
                      : "bg-secondary text-secondary-foreground hover:bg-secondary/80"
                  )}
                >
                  {d}m
                </button>
              ))}
            </div>
          </div>
          <div className="flex gap-2">
            <Button
              onClick={handleStartTask}
              disabled={!taskTitle.trim()}
              className="flex-1"
            >
              <Play className="mr-2 h-4 w-4" />
              Start focus
            </Button>
            <Button
              variant="outline"
              onClick={() => setShowTaskForm(false)}
            >
              Cancel
            </Button>
          </div>
        </div>
      )}

      {/* Input area */}
      <div className="border-t border-border pt-4">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="What's on your mind?"
            className="min-h-[52px] max-h-32 resize-none"
            disabled={isLoading}
            onCompositionStart={() => {
              setIsComposing(true);
            }}
            onCompositionEnd={(e) => {
              lastCompositionEndRef.current = Date.now();
              setIsComposing(false);
              setInput(e.currentTarget.value);
            }}
            onKeyDown={(e) => {
              if (e.key !== "Enter") return;

              // Shift+Enter: 换行
              if (e.shiftKey) return;

              // ✅ 原生 isComposing + 我们的状态 + 刚结束窗口期：都拦住
              // @ts-ignore
              const nativeIsComposing = e.nativeEvent?.isComposing === true;

              if (nativeIsComposing || isComposing || shouldBlockEnterSend()) {
                return; // 让 IME 自己处理 Enter（确认候选/结束组词）
              }

              // 否则 Enter 发送
              e.preventDefault();
              e.stopPropagation();
              handleSubmit(e);
            }}
          />
          <div className="flex flex-col gap-2">
            <Button
              type="submit"
              size="icon"
              disabled={!input.trim() || isLoading}
              className="h-[52px] w-[52px]"
            >
              <Send className="h-5 w-5" />
              <span className="sr-only">Send message</span>
            </Button>
          </div>
        </form>

        {messages.length > 0 && !showTaskForm && (
          <Button
            variant="outline"
            onClick={() => setShowTaskForm(true)}
            className="mt-3 w-full"
          >
            <Play className="mr-2 h-4 w-4" />
            Ready to start a task
          </Button>
        )}
      </div>
    </div>
  );
}
