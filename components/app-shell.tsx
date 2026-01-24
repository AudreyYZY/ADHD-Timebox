"use client";

import { useAppStore } from "@/lib/store";
import { StateIndicator } from "./state-indicator";
import { PlanningMode } from "./planning-mode";
import { FocusMode } from "./focus-mode";
import { InterruptedMode } from "./interrupted-mode";
import { RestingMode } from "./resting-mode";
import { ThoughtParkingSheet } from "./thought-parking-sheet";
import { OnboardingDialog } from "./onboarding-dialog";
import { Sidebar } from "./sidebar";

export function AppShell() {
  const { userState, hasCompletedOnboarding } = useAppStore();

  const renderCurrentMode = () => {
    switch (userState) {
      case "planning":
        return <PlanningMode />;
      case "focusing":
        return <FocusMode />;
      case "interrupted":
        return <InterruptedMode />;
      case "resting":
        return <RestingMode />;
      default:
        return <PlanningMode />;
    }
  };

  return (
    <div className="flex min-h-screen flex-col bg-background">
      {/* Header */}
      <header className="sticky top-0 z-40 border-b border-border bg-background/80 backdrop-blur-sm">
        <div className="flex h-14 items-center justify-between px-4 lg:px-6">
          <div className="flex items-center gap-3">
            <span className="text-lg font-medium text-foreground">Timebox</span>
          </div>
          <StateIndicator />
        </div>
      </header>

      {/* Sidebar - fixed position, hidden on mobile */}
      <Sidebar />

      {/* Main content - with left margin to account for fixed sidebar */}
      <main className="flex flex-1 flex-col lg:ml-16">
        <div className="mx-auto flex w-full max-w-2xl flex-1 flex-col px-4 py-6">
          {renderCurrentMode()}
        </div>
      </main>

      {/* Thought parking sheet */}
      <ThoughtParkingSheet />

      {/* Onboarding */}
      {!hasCompletedOnboarding && <OnboardingDialog />}
    </div>
  );
}
