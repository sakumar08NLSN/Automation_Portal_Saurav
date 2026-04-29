"use client";

import React, { useEffect } from "react";
import Navbar from "@/components/Navbar";
import Sidebar from "@/components/Sidebar";
import AuthProvider from "./authProvider";
import StoreProvider, { useAppSelector } from "./redux";
import OktaProviderWrapper from "@/components/OktaProviderWrapper";
import AuthGuard from "@/components/AuthGuard";

const DashboardLayout = ({ children }: { children: React.ReactNode }) => {
  const isSidebarCollapsed = useAppSelector(
    (state) => state.global.isSidebarCollapsed,
  );
  const isDarkMode = useAppSelector((state) => state.global.isDarkMode);

  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  });

  return (
    <div className="flex min-h-screen w-full bg-gray-50 text-gray-900">
      <Sidebar />
      <main
        className={`flex w-full flex-col bg-gray-50 dark:bg-dark-bg ${
          isSidebarCollapsed ? "" : "md:pl-64"
        }`}
      >
        <Navbar />
        {children}
      </main>
    </div>
  );
};

const DashboardWrapper = ({ children }: { children: React.ReactNode }) => {
  return (
    <StoreProvider>
      <OktaProviderWrapper>
        <AuthGuard>
      {/* <AuthProvider> */}
        <DashboardLayout>{children}</DashboardLayout>
      {/* </AuthProvider> */}
        </AuthGuard>
      </OktaProviderWrapper>
    </StoreProvider>
  );
};

export default DashboardWrapper;


// "use client";

// import React, { useEffect, useState } from "react";
// import { useRouter, usePathname } from "next/navigation"; // Import usePathname
// import { Security, useOktaAuth } from "@okta/okta-react";
// import { toRelativeUrl } from "@okta/okta-auth-js";
// import { oktaAuth } from "@/state/authConfig"; 
// import Navbar from "@/components/Navbar";
// import Sidebar from "@/components/Sidebar";
// import StoreProvider, { useAppSelector } from "./redux";

// // --- AUTH GUARD ---
// const AuthGuard = ({ children }: { children: React.ReactNode }) => {
//   const { oktaAuth, authState } = useOktaAuth();
//   const pathname = usePathname();

//   useEffect(() => {
//     // 🛑 STOP THE LOOP: If we are already at the callback page, do NOTHING.
//     if (pathname === "/login/callback") return;

//     if (authState && !authState.isAuthenticated) {
//       const originalUri = toRelativeUrl(window.location.href, window.location.origin);
//       oktaAuth.setOriginalUri(originalUri);
//       oktaAuth.signInWithRedirect();
//     }
//   }, [authState, oktaAuth, pathname]);

//   // If on callback page, allow the LoginCallback component to render
//   if (pathname === "/login/callback") {
//     return <>{children}</>;
//   }

//   // If not authenticated (and not on callback), show loader
//   if (!authState || !authState.isAuthenticated) {
//     return (
//       <div className="flex h-screen w-full items-center justify-center bg-gray-50">
//         <div className="text-center">
//           <div className="h-10 w-10 animate-spin rounded-full border-4 border-blue-600 border-t-transparent mx-auto"></div>
//           <p className="mt-4 text-gray-600">Redirecting to Nielsen Login...</p>
//         </div>
//       </div>
//     );
//   }

//   return <>{children}</>;
// };

// // --- LAYOUT ---
// const DashboardLayout = ({ children }: { children: React.ReactNode }) => {
//   const isSidebarCollapsed = useAppSelector((state) => state.global.isSidebarCollapsed);
//   const isDarkMode = useAppSelector((state) => state.global.isDarkMode);

//   useEffect(() => {
//     if (isDarkMode) {
//       document.documentElement.classList.add("dark");
//     } else {
//       document.documentElement.classList.remove("dark");
//     }
//   }, [isDarkMode]);

//   return (
//     <div className="flex min-h-screen w-full bg-gray-50 text-gray-900">
//       <Sidebar />
//       <main className={`flex w-full flex-col bg-gray-50 dark:bg-dark-bg ${isSidebarCollapsed ? "" : "md:pl-64"}`}>
//         <Navbar />
//         {children}
//       </main>
//     </div>
//   );
// };

// // --- WRAPPER ---
// const DashboardWrapper = ({ children }: { children: React.ReactNode }) => {
//   const router = useRouter();
//   const [isMounted, setIsMounted] = useState(false);

//   useEffect(() => {
//     setIsMounted(true);
//   }, []);

//   const restoreOriginalUri = async (_oktaAuth: any, originalUri: string) => {
//     router.replace(toRelativeUrl(originalUri || "/", window.location.origin));
//   };

//   if (!isMounted || !oktaAuth) {
//     return (
//       <div className="flex h-screen w-full items-center justify-center bg-gray-50">
//         <div className="h-10 w-10 animate-spin rounded-full border-4 border-gray-300 border-t-blue-600"></div>
//       </div>
//     );
//   }

//   return (
//     <StoreProvider>
//       <Security oktaAuth={oktaAuth} restoreOriginalUri={restoreOriginalUri}>
//         <AuthGuard>
//           {/* This renders DashboardLayout normally, OR the LoginCallback page if the path matches */}
//           <DashboardLayout>{children}</DashboardLayout>
//         </AuthGuard>
//       </Security>
//     </StoreProvider>
//   );
// };

// export default DashboardWrapper;