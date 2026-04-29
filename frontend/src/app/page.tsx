// "use client";

// import { useOktaAuth, LoginCallback } from '@okta/okta-react';
// import { useEffect, useState } from 'react';
// import HomePage from "./home/page"; 

// export default function Home() {
//   const { authState, oktaAuth } = useOktaAuth();
//   const [isHandlingCallback, setIsHandlingCallback] = useState(false);

//   // 🚨 LOCAL DEV SWITCH: Check if we are running in development mode (npm run dev)
//   // const isLocalDev = process.env.NODE_ENV === 'development';
//   const isLocalDev = typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');

//   useEffect(() => {
//     if (window.location.search.includes('code=') || window.location.search.includes('state=')) {
//       setIsHandlingCallback(true);
//     }
//   }, []);

//   useEffect(() => {
//     if (isHandlingCallback && authState?.isAuthenticated) {
//       setIsHandlingCallback(false);
//       window.history.replaceState({}, document.title, window.location.pathname);
//     }
//   }, [authState?.isAuthenticated, isHandlingCallback]);

//   // 1. HIGHEST PRIORITY: Render the callback handler FIRST! 
//   // (We skip this if we are in local dev to prevent getting stuck)
//   if (isHandlingCallback && !isLocalDev) {
//     return (
//       <div className="flex h-screen w-full items-center justify-center">
//         <div className="text-xl font-bold animate-pulse text-blue-600">Authenticating with Nielsen...</div>
//         <div className="hidden">
//            <LoginCallback />
//         </div>
//       </div>
//     );
//   }

//   // 2. Wait for Okta to figure out if you are logged in or not (Skip if local dev)
//   if (!authState && !isLocalDev) {
//     return (
//       <div className="flex h-screen w-full items-center justify-center">
//         <div className="text-xl font-bold animate-pulse text-gray-500">Loading...</div>
//       </div>
//     );
//   }

//   // 3. THE GATEKEEPER: Hide the dashboard if NOT logged in AND NOT in local dev
//   if (!isLocalDev && !authState?.isAuthenticated) {
//     return (
//       <div className="flex flex-col h-[80vh] w-full items-center justify-center">
//         <h1 className="text-4xl font-bold mb-4 text-gray-800 dark:text-white">
//           Nielsen Automation Portal
//         </h1>
//         <p className="mb-8 text-lg text-gray-600 dark:text-gray-300">
//           Please sign in with your Okta account to view the dashboard.
//         </p>
//         <button
//           onClick={() => oktaAuth.signInWithRedirect()}
//           className="rounded-lg px-8 py-3 text-lg font-bold text-white bg-blue-600 hover:bg-blue-700 shadow-lg transition-all"
//         >
//           Sign In
//         </button>
//       </div>
//     );
//   }

//   // 4. ONLY if everything above passes (or if local dev), show the actual dashboard!
//   return <HomePage />;
// }


"use client";

import HomePage from "./home/page"; 

export default function Home() {
  // 🛡️ All Okta security, login buttons, and loading screens 
  // are now handled globally by AuthGuard in DashboardWrapper.tsx!
  
  // If a user reaches this line of code, they are 100% authenticated.
  return <HomePage />;
}