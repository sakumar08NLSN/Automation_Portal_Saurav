// import React from "react";
// import { Menu, Moon, Search, Settings, Sun, User } from "lucide-react";
// import Link from "next/link";
// import { useAppDispatch, useAppSelector } from "@/app/redux";
// import { setIsDarkMode, setIsSidebarCollapsed } from "@/state";
// import { useGetAuthUserQuery } from "@/state/api";
// import { signOut } from "aws-amplify/auth";
// import Image from "next/image";

// const Navbar = () => {
//   const dispatch = useAppDispatch();
//   const isSidebarCollapsed = useAppSelector(
//     (state) => state.global.isSidebarCollapsed,
//   );
//   const isDarkMode = useAppSelector((state) => state.global.isDarkMode);

//   const { data: currentUser } = useGetAuthUserQuery();
//   const handleSignOut = async () => {
//     try {
//       await signOut();
//     } catch (error) {
//       console.error("Error signing out: ", error);
//     }
//   };

//   if (!currentUser) return null;
//   const currentUserDetails = currentUser?.userDetails;

//   return (
//     <div className="flex items-center justify-between bg-white px-4 py-3 dark:bg-black sticky top-0 z-50 shadow-md">
//       {/* LEFT SIDE: Logo & Search Bar */}
//       <div className="flex items-center gap-8">
//         {!isSidebarCollapsed ? null : (
//           <button
//             onClick={() => dispatch(setIsSidebarCollapsed(!isSidebarCollapsed))}
//           >
//             <Menu className="h-8 w-8 dark:text-white" />
//           </button>
//         )}

//         {/* 1. NEW LOGO ADDED HERE */}
//         {/* Replace "/logo.png" with your actual file path in the public folder */}
//         <Image
//           src="/nielsen_sports.png" 
//           alt="Nielsen Sports"
//           width={160}
//           height={40}
//           priority
//           unoptimized={process.env.NODE_ENV === 'production'} 
//           className="cursor-pointer object-contain dark:invert"
//         />

//         {/* 2. SEARCH BAR MOVED HERE */}
//         {/* <div className="relative flex h-min w-[200px]">
//           <Search className="absolute left-[4px] top-1/2 mr-2 h-5 w-5 -translate-y-1/2 transform cursor-pointer dark:text-white" />
//           <input
//             className="w-full rounded border-none bg-gray-100 p-2 pl-8 placeholder-gray-500 focus:border-transparent focus:outline-none dark:bg-gray-700 dark:text-white dark:placeholder-white"
//             type="search"
//             placeholder="Search..."
//           />
//         </div> */}
//       </div>

//       {/* RIGHT SIDE: Icons & User */}
//       <div className="flex items-center">
//         <button
//           onClick={() => dispatch(setIsDarkMode(!isDarkMode))}
//           className={
//             isDarkMode
//               ? `rounded p-2 dark:hover:bg-gray-700`
//               : `rounded p-2 hover:bg-gray-100`
//           }
//         >
//           {isDarkMode ? (
//             <Sun className="h-6 w-6 cursor-pointer dark:text-white" />
//           ) : (
//             <Moon className="h-6 w-6 cursor-pointer dark:text-white" />
//           )}
//         </button>
//         <Link
//           href="/settings"
//           className={
//             isDarkMode
//               ? `h-min w-min rounded p-2 dark:hover:bg-gray-700`
//               : `h-min w-min rounded p-2 hover:bg-gray-100`
//           }
//         >
//           {/* <Settings className="h-6 w-6 cursor-pointer dark:text-white" /> */}
//         </Link>
//         <div className="ml-2 mr-5 hidden min-h-[2em] w-[0.1rem] bg-gray-200 md:inline-block"></div>
//         <div className="hidden items-center justify-between md:flex">
//           <div className="align-center flex h-9 w-9 justify-center">
//             {!!currentUserDetails?.profilePictureUrl ? (
//               <Image
//                 src={`https://pm-s3-images.s3.us-east-2.amazonaws.com/${currentUserDetails?.profilePictureUrl}`}
//                 alt={currentUserDetails?.username || "User Profile Picture"}
//                 width={100}
//                 height={50}
//                 className="h-full rounded-full object-cover"
//               />
//             ) : (
//               <User className="h-6 w-6 cursor-pointer self-center rounded-full dark:text-white" />
//             )}
//           </div>
//           <span className="mx-3 text-gray-800 dark:text-white">
//             {currentUserDetails?.username}
//           </span>
//           <button
//             className="hidden rounded bg-blue-400 px-4 py-2 text-xs font-bold text-white hover:bg-blue-500 md:block"
//             onClick={handleSignOut}
//           >
//             Sign out 
//           </button>
//         </div>
//       </div>
//     </div>
//   );
// };

// export default Navbar;




"use client";

import React from "react";
import { Menu, Moon, Sun, LogIn } from "lucide-react";
import { useAppDispatch, useAppSelector } from "@/app/redux";
import { setIsDarkMode, setIsSidebarCollapsed } from "@/state";
import { useGetAuthUserQuery } from "@/state/api";
import { useOktaAuth } from "@okta/okta-react"; 
import Image from "next/image";

const Navbar = () => {
  const dispatch = useAppDispatch();
  const { oktaAuth, authState } = useOktaAuth(); 
  const isSidebarCollapsed = useAppSelector((state) => state.global.isSidebarCollapsed);
  const isDarkMode = useAppSelector((state) => state.global.isDarkMode);

  const { data: currentUser } = useGetAuthUserQuery();

  const handleAuthAction = async () => {
    if (authState?.isAuthenticated) {
      await oktaAuth.signOut();
    } else {
      await oktaAuth.signInWithRedirect();
    }
  };

  // 🚨 LOCAL DEV SWITCH
  const isLocalDev = typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');
  const isAuthenticated = authState?.isAuthenticated || isLocalDev;

  // 🚨 ROBUST DISPLAY NAME LOGIC
  // 1. Try to get the exact First & Last name directly from the Okta Token
  // 2. Fallback to the Redux Database username
  // 3. Fallback to Local Admin (for localhost testing)
  const displayName = authState?.idToken?.claims?.name 
    || currentUser?.user?.username 
    || currentUser?.userDetails?.username 
    || "Nielsen User";

  return (
    <div className="flex items-center justify-between bg-white px-4 py-3 dark:bg-black sticky top-0 z-50 shadow-md">
      {/* LEFT SIDE */}
      <div className="flex items-center gap-8">
        {isSidebarCollapsed && (
          <button onClick={() => dispatch(setIsSidebarCollapsed(!isSidebarCollapsed))}>
            <Menu className="h-8 w-8 dark:text-white" />
          </button>
        )}
        <Image
          src="/nielsen_sports.png" 
          alt="Nielsen Sports"
          width={160}
          height={40}
          priority
          className="cursor-pointer object-contain dark:invert"
        />
      </div>

      {/* RIGHT SIDE */}
      <div className="flex items-center">
        <button
          onClick={() => dispatch(setIsDarkMode(!isDarkMode))}
          className={`rounded p-2 ${isDarkMode ? 'dark:hover:bg-gray-700' : 'hover:bg-gray-100'}`}
        >
          {isDarkMode ? <Sun className="h-6 w-6 dark:text-white" /> : <Moon className="h-6 w-6 dark:text-white" />}
        </button>

        <div className="ml-2 mr-5 hidden min-h-[2em] w-[0.1rem] bg-gray-200 md:inline-block"></div>

        {/* User Info & Button */}
        <div className="flex items-center">
          
          {/* Render Name if Authenticated (or in Local Dev) */}
          {isAuthenticated && (
            <div className="hidden items-center justify-between md:flex mr-4">
              <span className="mx-3 text-gray-800 dark:text-white font-bold">
                {displayName}
              </span>
            </div>
          )}
          
          {/* Hide Sign-In/Out buttons on localhost since Okta is bypassed */}
          {!isLocalDev && (
            <button
              className={`rounded px-4 py-2 text-xs font-bold text-white transition-colors flex items-center gap-2 ${
                authState?.isAuthenticated ? "bg-red-500 hover:bg-red-600" : "bg-blue-600 hover:bg-blue-700"
              }`}
              onClick={handleAuthAction}
              disabled={!authState}
            >
              {authState?.isAuthenticated ? "Sign out" : <><LogIn className="w-4 h-4" /> Sign in</>}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default Navbar;