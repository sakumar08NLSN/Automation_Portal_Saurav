// src/components/AuthGuard.tsx (or src/app/AuthGuard.tsx)
"use client";

import { useOktaAuth, LoginCallback } from '@okta/okta-react';
import { useEffect, useState } from 'react';

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const { authState, oktaAuth } = useOktaAuth();
  const [isHandlingCallback, setIsHandlingCallback] = useState(false);

  // 🚨 LOCAL DEV SWITCH
  const isLocalDev = typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');

  useEffect(() => {
    if (window.location.search.includes('code=') || window.location.search.includes('state=')) {
      setIsHandlingCallback(true);
    }
  }, []);

  useEffect(() => {
    if (isHandlingCallback && authState?.isAuthenticated) {
      setIsHandlingCallback(false);
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, [authState?.isAuthenticated, isHandlingCallback]);

  // 1. HIGHEST PRIORITY: Render the callback handler FIRST! 
  if (isHandlingCallback && !isLocalDev) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-white dark:bg-black">
        <div className="text-xl font-bold animate-pulse text-blue-600">Authenticating with Nielsen...</div>
        <div className="hidden"><LoginCallback /></div>
      </div>
    );
  }

  // 2. Wait for Okta to figure out if you are logged in
  if (!authState && !isLocalDev) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-white dark:bg-black">
        <div className="text-xl font-bold animate-pulse text-gray-500">Loading...</div>
      </div>
    );
  }

  // 3. THE GLOBAL GATEKEEPER: Hide the ENTIRE APP if not logged in!
  if (!isLocalDev && !authState?.isAuthenticated) {
    return (
      <div className="flex flex-col h-screen w-full items-center justify-center bg-[#F9FBFC] dark:bg-[#08090A]">
        <h1 className="text-4xl font-bold mb-4 text-gray-800 dark:text-white">
          Nielsen Automation Portal
        </h1>
        <p className="mb-8 text-lg text-gray-600 dark:text-gray-300">
          Please sign in with your Okta account to view this page.
        </p>
        <button
          onClick={() => oktaAuth.signInWithRedirect()}
          className="rounded-lg px-8 py-3 text-lg font-bold text-white bg-blue-600 hover:bg-blue-700 shadow-lg transition-all"
        >
          Sign In
        </button>
      </div>
    );
  }

  // 4. If Authenticated, render the protected content (Navbar, Sidebar, Page)
  return <>{children}</>;
}