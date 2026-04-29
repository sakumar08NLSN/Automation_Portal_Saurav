// "use client";

// import { useAppDispatch, useAppSelector } from "@/app/redux";
// import { setIsSidebarCollapsed } from "@/state";
// import { useGetAuthUserQuery, useGetProjectsQuery } from "@/state/api";
// import { signOut } from "aws-amplify/auth";
// import {
//   AlertCircle,
//   AlertOctagon,
//   AlertTriangle,
//   Briefcase,
//   ChevronDown,
//   ChevronUp,
//   Home,
//   Layers3,
//   LockIcon,
//   LucideIcon,
//   Search,
//   Settings,
//   ShieldAlert,
//   User,
//   Users,
//   X,
// } from "lucide-react";
// import Image from "next/image";
// import Link from "next/link";
// import { usePathname } from "next/navigation";
// import React, { useState } from "react";

// const Sidebar = () => {
//   const [showProjects, setShowProjects] = useState(true);
//   const [showPriority, setShowPriority] = useState(true);

//   const { data: projects } = useGetProjectsQuery();
//   const dispatch = useAppDispatch();
//   const isSidebarCollapsed = useAppSelector(
//     (state) => state.global.isSidebarCollapsed,
//   );

//   // const { data: currentUser } = useGetAuthUserQuery({});
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

//   const sidebarClassNames = `fixed flex flex-col h-[100%] justify-between shadow-xl
//     transition-all duration-300 h-full z-40 dark:bg-black overflow-y-auto bg-white
//     ${isSidebarCollapsed ? "w-0 hidden" : "w-64"}
//   `;

//   return (
//     <div className={sidebarClassNames}>
//       <div className="flex h-[100%] w-full flex-col justify-start">
//         {/* TOP LOGO */}
//         <div className="z-50 flex min-h-[56px] w-64 items-center justify-between bg-white px-6 pt-3 dark:bg-black">
//           <div className="text-xl font-bold text-gray-800 dark:text-white">
//             Sports
//           </div>
//           {isSidebarCollapsed ? null : (
//             <button
//               className="py-3"
//               onClick={() => {
//                 dispatch(setIsSidebarCollapsed(!isSidebarCollapsed));
//               }}
//             >
//               <X className="h-6 w-6 text-gray-800 hover:text-gray-500 dark:text-white" />
//             </button>
//           )}
//         </div>
//         {/* TEAM */}
//         <div className="flex items-center gap-5 border-y-[1.5px] border-gray-200 px-8 py-4 dark:border-gray-700">
//           <Image
//             src="/Nielsen_logo.png"
//             alt="Logo"
//             width={40}
//             height={40}
//           />
//           <div>
//             <h3 className="text-md font-bold tracking-wide dark:text-gray-200">
//               Nielsen
//             </h3>
//             <div className="mt-1 flex items-start gap-2">
//               <LockIcon className="mt-[0.1rem] h-3 w-3 text-gray-500 dark:text-gray-400" />
//               <p className="text-xs text-gray-500">Private</p>
//             </div>
//           </div>
//         </div>
//         {/* NAVBAR LINKS */}
//         <nav className="z-10 w-full">
//           <SidebarLink icon={Home} label="Home" href="/" />
//           <SidebarLink icon={Briefcase} label="Data Camparision" href="/timeline" />
//           <SidebarLink icon={Search} label="Search" href="/search" />
//           <SidebarLink icon={Settings} label="Settings" href="/settings" />
//           <SidebarLink icon={User} label="Users" href="/users" />
//           <SidebarLink icon={Users} label="Teams" href="/teams" />
//         </nav>

//         {/* PROJECTS LINKS */}
//         <button
//           onClick={() => setShowProjects((prev) => !prev)}
//           className="flex w-full items-center justify-between px-8 py-3 text-gray-500"
//         >
//           <span className="">Projects</span>
//           {showProjects ? (
//             <ChevronUp className="h-5 w-5" />
//           ) : (
//             <ChevronDown className="h-5 w-5" />
//           )}
//         </button>
//         {/* PROJECTS LIST */}
//         {showProjects &&
//           projects?.map((project) => (
//             <SidebarLink
//               key={project.id}
//               icon={Briefcase}
//               label={project.name}
//               href={`/projects/${project.id}`}
//             />
//           ))}

//         {/* PRIORITIES LINKS   */}
//         <button
//           onClick={() => setShowPriority((prev) => !prev)}
//           className="flex w-full items-center justify-between px-8 py-3 text-gray-500"
//         >
//           <span className="">Priority</span>
//           {showPriority ? (
//             <ChevronUp className="h-5 w-5" />
//           ) : (
//             <ChevronDown className="h-5 w-5" />
//           )}
//         </button>
//         {showPriority && (
//           <>
//             <SidebarLink
//               icon={AlertCircle}
//               label="Urgent"
//               href="/priority/urgent"
//             />
//             <SidebarLink
//               icon={ShieldAlert}
//               label="High"
//               href="/priority/high"
//             />
//             <SidebarLink
//               icon={AlertTriangle}
//               label="Medium"
//               href="/priority/medium"
//             />
//             <SidebarLink icon={AlertOctagon} label="Low" href="/priority/low" />
//             <SidebarLink
//               icon={Layers3}
//               label="Backlog"
//               href="/priority/backlog"
//             />
//           </>
//         )}
//       </div>
//       <div className="z-10 mt-32 flex w-full flex-col items-center gap-4 bg-white px-8 py-4 dark:bg-black md:hidden">
//         <div className="flex w-full items-center">
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
//             className="self-start rounded bg-blue-400 px-4 py-2 text-xs font-bold text-white hover:bg-blue-500 md:block"
//             onClick={handleSignOut}
//           >
//             Sign out
//           </button>
//         </div>
//       </div>
//     </div>
//   );
// };

// interface SidebarLinkProps {
//   href: string;
//   icon: LucideIcon;
//   label: string;
// }

// const SidebarLink = ({ href, icon: Icon, label }: SidebarLinkProps) => {
//   const pathname = usePathname();
//   const isActive =
//     pathname === href || (pathname === "/" && href === "/dashboard");

//   return (
//     <Link href={href} className="w-full">
//       <div
//         className={`relative flex cursor-pointer items-center gap-3 transition-colors hover:bg-gray-100 dark:bg-black dark:hover:bg-gray-700 ${
//           isActive ? "bg-gray-100 text-white dark:bg-gray-600" : ""
//         } justify-start px-8 py-3`}
//       >
//         {isActive && (
//           <div className="absolute left-0 top-0 h-[100%] w-[5px] bg-blue-200" />
//         )}

//         <Icon className="h-6 w-6 text-gray-800 dark:text-gray-100" />
//         <span className={`font-medium text-gray-800 dark:text-gray-100`}>
//           {label}
//         </span>
//       </div>
//     </Link>
//   );
// };

// export default Sidebar;
"use client";

import { useAppDispatch, useAppSelector } from "@/app/redux";
import { setIsSidebarCollapsed } from "@/state";
import { useGetAuthUserQuery, useGetProjectsQuery } from "@/state/api";
import { signOut } from "aws-amplify/auth";
import {
  Briefcase,
  ChevronDown,
  ChevronUp,
  Home,
  Layers3,
  NotebookPen,
  User,
  Users,
  X,
  LucideIcon,
  LayoutDashboard,
  List,
  ListCheckIcon,
  ClipboardList,
  ClipboardPen,
  CircleGauge,
  Activity
} from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import React, { useState } from "react";

// --- CONFIG: Map your Project Names to Image Paths here ---
const projectImages: Record<string, string> = {
  "Formula 1": "/sidebar_f1.png",
  "Laliga": "/sidebar_laliga.png",
  "EPL": "/sidebar_premier_league.png",
  "Serie A": "/sidebar_serie_a.png",
};

const Sidebar = () => {
  const [showDashboards, setShowDashboards] = useState(true);
  const [showPriority, setShowPriority] = useState(true);
  const [showRates, setShowRates] = useState(false); // New state for Rates group
  const [showProjects, setShowProjects] = useState(false);
  const [isCompareModalOpen, setIsCompareModalOpen] = useState(false);

  const { data: projects } = useGetProjectsQuery();
  const dispatch = useAppDispatch();
  const isSidebarCollapsed = useAppSelector(
    (state) => state.global.isSidebarCollapsed,
  );

  const { data: currentUser } = useGetAuthUserQuery();
  const handleSignOut = async () => {
    try {
      await signOut();
    } catch (error) {
      console.error("Error signing out: ", error);
    }
  };

  if (!currentUser) return null;
  const currentUserDetails = currentUser?.userDetails;

  const sidebarClassNames = `fixed flex flex-col h-[100%] justify-between shadow-xl
    transition-all duration-300 h-full z-40 dark:bg-black overflow-y-auto bg-white
    ${isSidebarCollapsed ? "w-0 hidden" : "w-64"}
  `;

  return (
    <>
      <div className={sidebarClassNames}>
        <div className="flex h-[100%] w-full flex-col justify-start">
          {/* TOP LOGO */}
          <div className="z-50 flex min-h-[56px] w-64 items-center justify-between bg-white px-6 pt-3 dark:bg-black">
            <SidebarTitle />
            {isSidebarCollapsed ? null : (
              <button
                className="py-3"
                onClick={() => {
                  dispatch(setIsSidebarCollapsed(!isSidebarCollapsed));
                }}
              >
                <X className="h-6 w-6 text-gray-800 hover:text-gray-500 dark:text-white" />
              </button>
            )}
          </div>

          {/* NAVBAR LINKS */}
          <nav className="z-10 w-full">
            <SidebarLink icon={Home} label="Home" href="/" />
            <SidebarLink icon={Users} label="Teams" href="/teams" />
          </nav>

          {/* --- DASHBOARDS SECTION --- */}
          <button
            onClick={() => setShowDashboards((prev) => !prev)}
            className="flex w-full items-center justify-between px-8 py-3 text-gray-500"
          >
            <span className="">Dashboards</span>
            {showDashboards ? (
              <ChevronUp className="h-5 w-5" />
            ) : (
              <ChevronDown className="h-5 w-5" />
            )}
          </button>

          {showDashboards && (
            <>
              <SidebarLink
                icon={CircleGauge}
                label="GMS Dashboard"
                href="/gms-dashboard"
              />
              <SidebarLink
                icon={Activity}
                label="Audit Trail"
                href="/qc-history"
              />
              <SidebarButton
                icon={LayoutDashboard}
                label="Data Comparison"
                onClick={() => setIsCompareModalOpen(true)}
              />
              <SidebarLink
                icon={List}
                label="BSA Early Warning"
                href="/dashboards/early-warning"
              />
              
            </>
          )}

          {/* --- BSR GENERAL CHECKS --- */}
          <button
            onClick={() => setShowPriority((prev) => !prev)}
            className="flex w-full items-center justify-between px-8 py-3 text-gray-500"
          >
            <span className="">BSR General Checks</span>
            {showPriority ? (
              <ChevronUp className="h-5 w-5" />
            ) : (
              <ChevronDown className="h-5 w-5" />
            )}
          </button>
          {showPriority && (
            <>
              <SidebarLink
                icon={Layers3}
                label="General QC's"
                href="/priority/urgent"
              />
              <SidebarLink
                icon={ListCheckIcon}
                label="E2E Checks"
                href="/priority/mm-bsa"
              />
            </>
          )}

          {/* --- NEW SECTION: RATES AND RATING --- */}
          <button
            onClick={() => setShowRates((prev) => !prev)}
            className="flex w-full items-center justify-between px-8 py-3 text-gray-500"
          >
            <span className="">Rates and Rating</span>
            {showRates ? (
              <ChevronUp className="h-5 w-5" />
            ) : (
              <ChevronDown className="h-5 w-5" />
            )}
          </button>
          {showRates && (
            <>
              <SidebarLink
                icon={NotebookPen}
                label="Rates (International)"
                href="/priority/medium"
              />

              <SidebarLink
                icon={ClipboardPen}
                label="Rates-Ratings (USA)"
                href="/priority/high"
              />
              
              <SidebarLink
                icon={ClipboardPen}
                label="MLS (USA and CAN)"
                href="/priority/low"
              />
               <SidebarLink
                icon={ClipboardPen}
                label="Rates- Ratings (JAP) "
                href="/priority/japan"
              />
            </>
          )}

          {/* --- SPORTS SPECIFIC CHECKS --- */}
          <button
            onClick={() => setShowProjects((prev) => !prev)}
            className="flex w-full items-center justify-between px-8 py-3 text-gray-500"
          >
            <span className="">Sports Specific Checks</span>
            {showProjects ? (
              <ChevronUp className="h-5 w-5" />
            ) : (
              <ChevronDown className="h-5 w-5" />
            )}
          </button>

          {showProjects &&
            projects?.map((project) => (
              <SidebarLink
                key={project.id}
                icon={Briefcase}
                label={project.name}
                href={`/projects/${project.id}`}
                imageSrc={projectImages[project.name]}
              />
            ))}
        </div>

        {/* SIGN OUT SECTION */}
        <div className="z-10 mt-32 flex w-full flex-col items-center gap-4 bg-white px-8 py-4 dark:bg-black md:hidden">
          <div className="flex w-full items-center">
            <div className="align-center flex h-9 w-9 justify-center">
              {!!currentUserDetails?.profilePictureUrl ? (
                <Image
                  src={`https://pm-s3-images.s3.us-east-2.amazonaws.com/${currentUserDetails?.profilePictureUrl}`}
                  alt={currentUserDetails?.username || "User Profile Picture"}
                  width={100}
                  height={50}
                  className="h-full rounded-full object-cover"
                />
              ) : (
                <User className="h-6 w-6 cursor-pointer self-center rounded-full dark:text-white" />
              )}
            </div>
            <span className="mx-3 text-gray-800 dark:text-white">
              {currentUserDetails?.username}
            </span>
            <button
              className="self-start rounded bg-blue-400 px-4 py-2 text-xs font-bold text-white hover:bg-blue-500 md:block"
              onClick={handleSignOut}
            >
              Sign out
            </button>
          </div>
        </div>
      </div>

      {/* DATA COMPARISON MODAL */}
      {isCompareModalOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
          <div className="relative flex h-[90vh] w-[95vw] max-w-7xl flex-col rounded-xl bg-gray-50 p-6 shadow-2xl dark:bg-black">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                Data Comparison
              </h2>
              <button
                onClick={() => setIsCompareModalOpen(false)}
                className="rounded-full p-2 text-gray-500 hover:bg-gray-200 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-white transition-colors"
              >
                <X className="h-6 w-6" />
              </button>
            </div>

            <div className="flex-grow w-full overflow-hidden rounded-lg bg-white shadow-inner dark:bg-dark-secondary">
              <iframe
                src="https://lookerstudio.google.com/embed/reporting/f4dd42e6-dc43-4e3a-87c7-b81aca3a8c68/page/AROkF"
                title="Data Comparison Dashboard"
                width="100%"
                height="100%"
                style={{ border: 0 }}
                allowFullScreen
                sandbox="allow-storage-access-by-user-activation allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox"
              />
            </div>
          </div>
        </div>
      )}
    </>
  );
};

const SidebarTitle = () => {
  return (
    <div className="ml-8 text-xl font-bold text-gray-800 dark:text-white font-mono tracking-tight">
      <span className="text-black-600 dark:text-blue-400">Automation</span>
    </div>
  );
};

interface SidebarLinkProps {
  href: string;
  icon: LucideIcon;
  label: string;
  imageSrc?: string;
}

const SidebarLink = ({ href, icon: Icon, label, imageSrc }: SidebarLinkProps) => {
  const pathname = usePathname();
  const isActive = pathname === href || (pathname === "/" && href === "/dashboard");

  return (
    <Link href={href} className="w-full">
      <div
        className={`relative flex cursor-pointer items-center gap-3 transition-colors hover:bg-gray-100 dark:bg-black dark:hover:bg-gray-700 ${
          isActive ? "bg-gray-100 text-white dark:bg-gray-600" : ""
        } justify-start px-8 py-3`}
      >
        {isActive && (
          <div className="absolute left-0 top-0 h-[100%] w-[5px] bg-blue-200" />
        )}

        {imageSrc ? (
          <Image
            src={imageSrc}
            alt={label}
            width={24}
            height={24}
            className="h-6 w-6 rounded-full object-cover"
          />
        ) : (
          <Icon className="h-6 w-6 text-gray-800 dark:text-gray-100" />
        )}

        <span className={`font-medium text-gray-800 dark:text-gray-100`}>
          {label}
        </span>
      </div>
    </Link>
  );
};

interface SidebarButtonProps {
  icon: LucideIcon;
  label: string;
  onClick: () => void;
}

const SidebarButton = ({ icon: Icon, label, onClick }: SidebarButtonProps) => {
  return (
    <button onClick={onClick} className="w-full text-left">
      <div className="relative flex cursor-pointer items-center gap-3 transition-colors hover:bg-gray-100 dark:bg-black dark:hover:bg-gray-700 justify-start px-8 py-3">
        <Icon className="h-6 w-6 text-gray-800 dark:text-gray-100" />
        <span className="font-medium text-gray-800 dark:text-gray-100">
          {label}
        </span>
      </div>
    </button>
  );
};

export default Sidebar;