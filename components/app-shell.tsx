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
import { UserButton } from "@clerk/nextjs";

export function AppShell() {
  const { userState, hasCompletedOnboarding, hasHydrated } = useAppStore();

  if (!hasHydrated) {
    return <div className="min-h-screen bg-background" aria-hidden="true" />;
  }

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
            <span className="sr-only">Timebox</span>
            <img
              src="/icon-light-32x32.png"
              alt=""
              className="h-6 w-6 dark:hidden"
            />
            <img
              src="/icon-dark-32x32.png"
              alt=""
              className="hidden h-6 w-6 dark:block"
            />
          </div>
          <div className="flex items-center gap-3">
            <StateIndicator />
            <UserButton afterSignOutUrl="/" />
          </div>
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
