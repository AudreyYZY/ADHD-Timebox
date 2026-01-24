"use client";

import React from "react"

import { useState, useRef, useEffect } from "react";
import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport } from "ai";
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

export function PlanningMode() {
  const [input, setInput] = useState("");
  const [taskTitle, setTaskTitle] = useState("");
  const [taskDuration, setTaskDuration] = useState(15);
  const [showTaskForm, setShowTaskForm] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  const { setCurrentTask, setUserState, setTimeRemaining, setIsTimerRunning, addTask } = useAppStore();

  const { messages, sendMessage, status } = useChat({
    transport: new DefaultChatTransport({ api: "/api/chat/planning" }),
  });

  const isLoading = status === "streaming" || status === "submitted";

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
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
                <p className="text-sm leading-relaxed whitespace-pre-wrap">{text}</p>
              </div>
            </div>
          );
        })}

        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-card border border-border rounded-2xl px-4 py-3">
              <div className="flex gap-1">
                <span className="h-2 w-2 bg-muted-foreground/40 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                <span className="h-2 w-2 bg-muted-foreground/40 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                <span className="h-2 w-2 bg-muted-foreground/40 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
              </div>
            </div>
          </div>
        )}

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
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e);
              }
            }}
            disabled={isLoading}
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
