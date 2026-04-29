"use client";

import React from "react";
import { Security } from "@okta/okta-react";
import { oktaAuth } from "@/state/authConfig";
import { useRouter } from "next/navigation";

export default function OktaProviderWrapper({ children }: { children: React.ReactNode }) {
  const router = useRouter();

  const restoreOriginalUri = (_oktaAuth: any, originalUri: string) => {
    router.replace(originalUri || "/");
  };

  if (!oktaAuth) return <>{children}</>;

  return (
    <Security oktaAuth={oktaAuth} restoreOriginalUri={restoreOriginalUri}>
      {children}
    </Security>
  );
}