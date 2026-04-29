"use client";

import { LoginCallback } from '@okta/okta-react';

export default function OktaCallbackPage() {
  return (
    <div className="flex h-screen w-full items-center justify-center">
      <div className="text-xl font-bold animate-pulse">Authenticating with Nielsen...</div>
      <LoginCallback />
    </div>
  );
}