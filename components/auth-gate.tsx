"use client";

import React from "react";
import { SignedIn, SignedOut, SignIn } from "@clerk/nextjs";

type AuthGateProps = {
  children: React.ReactNode;
};

export function AuthGate({ children }: AuthGateProps) {
  return (
    <>
      <SignedOut>
        <div className="flex min-h-screen items-center justify-center bg-background px-6">
          <SignIn
            routing="hash"
            appearance={{
              elements: {
                card: "shadow-none",
                socialButtonsBlockButton__apple: "hidden",
              },
            }}
          />
        </div>
      </SignedOut>
      <SignedIn>{children}</SignedIn>
    </>
  );
}
