// "use client";

// import React, { useState, useRef } from "react";
// import { useAppSelector } from "../redux";
// import Header from "@/components/Header";
// import { 
//   ShieldAlert,
//   Search, 
//   ZoomIn, 
//   ZoomOut,
//   Lock
// } from "lucide-react";

// const Teams = () => {
//   const isDarkMode = useAppSelector((state) => state.global.isDarkMode);
//   const [zoom, setZoom] = useState(0.6);
//   const [searchTerm, setSearchTerm] = useState("");
  
//   // Logic kept for structural consistency
//   const handleZoomIn = () => setZoom((prev) => Math.min(prev + 0.05, 2));
//   const handleZoomOut = () => setZoom((prev) => Math.max(prev - 0.05, 0.2));

//   return (
//     <div className={`flex w-full flex-col p-8 min-h-screen transition-colors duration-300 ${isDarkMode ? "bg-dark-bg text-white" : "bg-gray-50 text-gray-900"}`}>
      
//       {/* HEADER SECTION */}
//       <div className="flex flex-col md:flex-row justify-between items-center mb-6 gap-6">
//         <Header name="Master Organization Chart" />
//         <div className="flex items-center gap-4 opacity-40 pointer-events-none">
//           <div className="relative">
//             <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
//             <input 
//               type="text" placeholder="Search..." disabled
//               className={`pl-10 pr-4 py-2 rounded-lg border text-sm w-72 ${isDarkMode ? "bg-gray-800 border-gray-700 text-white" : "bg-white border-gray-300 text-black"}`}
//             />
//           </div>
//           <div className={`flex items-center gap-2 p-1.5 rounded-lg border ${isDarkMode ? "bg-gray-800 border-gray-700" : "bg-white border-gray-300"}`}>
//             <button className="p-1"><ZoomOut className="w-4 h-4"/></button>
//             <span className="text-xs font-bold w-12 text-center select-none">{Math.round(zoom * 100)}%</span>
//             <button className="p-1"><ZoomIn className="w-4 h-4"/></button>
//           </div>
//         </div>
//       </div>

//       {/* SECURITY NOTICE AREA */}
//       <div className={`flex-1 flex flex-col items-center justify-center rounded-xl border-2 transition-colors duration-300 ${isDarkMode ? "border-red-900/40 bg-black/40" : "border-red-100 bg-white shadow-inner"}`}>
//         <div className="text-center p-10 flex flex-col items-center">
//           {/* Static Icon - No Animation */}
//           <div className={`p-5 rounded-2xl mb-6 border-2 ${isDarkMode ? "bg-red-950/30 border-red-900/50 text-red-500" : "bg-red-50 border-red-100 text-red-600"}`}>
//             <ShieldAlert size={64} strokeWidth={1.5} />
//           </div>
          
//           <h2 className="text-3xl font-black uppercase tracking-tight mb-3">Access Restricted</h2>
          
//           <div className={`flex items-center gap-2 mb-6 px-4 py-1.5 rounded-full border ${isDarkMode ? "bg-red-900/10 border-red-900/40 text-red-400" : "bg-red-50 border-red-200 text-red-700"}`}>
//             <Lock size={14} />
//             <span className="text-[11px] font-bold uppercase tracking-widest">Protocol 403-Secure</span>
//           </div>

//           <p className={`text-sm font-medium max-w-md leading-relaxed ${isDarkMode ? "text-gray-500" : "text-gray-500"}`}>
//             This page has currently down. 
//           </p>
//         </div>
//       </div>

//       {/* FOOTER */}
//       <div className="mt-8 pt-6 border-t border-gray-500/10 flex justify-between items-center opacity-40">
//         <span className="text-[10px] font-mono tracking-tighter">NODE_STATUS: OFFLINE</span>
//         <span className="text-[10px] font-bold uppercase tracking-[0.2em]">Security Clearance Required</span>
//       </div>
//     </div>
//   );
// };

// export default Teams;

"use client";

import React, { useState, useRef, useEffect } from "react";
import { useAppSelector } from "../redux";
import Header from "@/components/Header";
import { 
  ArrowDown, 
  ZoomIn, 
  ZoomOut, 
  Search, 
  User, 
  Mail, 
  ShieldCheck,
  X,
  HelpCircle
} from "lucide-react";

const Teams = () => {
  const isDarkMode = useAppSelector((state) => state.global.isDarkMode);
  const [zoom, setZoom] = useState(0.6);
  const [searchTerm, setSearchTerm] = useState("");
  const [isSupportOpen, setIsSupportOpen] = useState(false);
  const supportRef = useRef<HTMLDivElement>(null);

  // Close support panel when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (supportRef.current && !supportRef.current.contains(event.target as Node)) {
        setIsSupportOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleZoomIn = () => setZoom((prev) => Math.min(prev + 0.05, 2));
  const handleZoomOut = () => setZoom((prev) => Math.max(prev - 0.05, 0.2));

  // --- Unified Data Structure ---
  const globalLead = { name: "Sumeet Champatiroy", title: "Global Delivery Lead", count: 129 };

  const directReports = [
    { id: 1, name: "Pradeep Ramanna", title: "Media Team US", geo: "USA", p2: 7, p3: 6 },
    { id: 2, name: "Abhishek Mukherjee", title: "Media Team EUR LATAM", geo: "EU & LATAM", p2: 8, p3: 9 },
    { id: 3, name: "Rohit Bhat", title: "Media Team AUS/UK", geo: "UK & Australia", p2: 6, p3: 5 },
    { id: 4, name: "Umang Vashishtha", title: "Media Team ASIA", geo: "Middle East & Asia", p2: 5, p3: 5 },
    { 
      id: 9, 
      name: "Vivek Mailar S", 
      title: "GMOS Lead", 
      isVivek: true,
      subTeams: [
        { 
          manager: "Hitesh Kumar Dhanjani", 
          lob: "BSR", 
          members: ["Almas Begum I Mulla", "Arun Kumar P", "Jeevikaa Anand", "Jesintha Mary", "Kumari Apurva", "Ram Mohan M", "Srikanth Gaonkar", "Srinidhi Srinivasan", "Sumit Kumar", "Vinayaka LNU", "Vishal V Kurdekar"] 
        },
        { 
          manager: "Naveen Sengottiyan", 
          lob: "BSR", 
          members: ["Dharuman B", "Lohith Jayaprakash", "Madhu C", "Mohammed Unus M", "Moulika C", "Prem Kumar R", "Santhosh M", "Saurabh Singh", "Soumya Ranjan Nayak", "Sridevi Venigalla"] 
        },
        { 
          manager: "Direct Reports", 
          lob: "Various", 
          members: ["Arun S Alexander", "B Avanish", "Bharath Raj G", "Chethan SA", "Khushi Mittal", "Nishanth Viswajith", "Priya K V", "Rajath M", "Sasmita Panda", "Saurav Kumar"] 
        }
      ]
    },
    { id: 5, name: "Deepak RS", title: "A&V Lead", geo: "Global", p2: 2, p3: 0 },
    { id: 6, name: "Swadhin Mishra", title: "Research Team US", geo: "US/CA/UK", p2: 5, p3: 5 },
    { id: 7, name: "Sonal Agarwal", title: "Research Team INT", geo: "Global excl. US/CA/UK", p2: 4, p3: 5 },
    { id: 8, name: "Pushkar Raj", title: "Consulting Team lead", geo: "Global", p2: 6, p3: 9 },
  ];

  const techSupport = [
    { name: "Priya K V", email: "priya.kv@nielsen.com" },
    { name: "Bharath Raj G", email: "bharath.rajg@nielsen.com" },
    { name: "Saurav Kumar", email: "saurav.kumar2@nielsen.com" },
  ];

  const isMatch = (name: string, title?: string, members?: string[]) => {
    const term = searchTerm.toLowerCase();
    if (searchTerm === "") return true;
    if (name.toLowerCase().includes(term)) return true;
    if (title && title.toLowerCase().includes(term)) return true;
    if (members && members.some(m => m.toLowerCase().includes(term))) return true;
    return false;
  };

  const nodeBg = isDarkMode ? "bg-[#ffd8b1]" : "bg-[#ffe6cc]";
  const nodeBorder = isDarkMode ? "border-orange-500" : "border-orange-400";
  const lineStroke = isDarkMode ? "bg-gray-500" : "bg-gray-400";

  return (
    <div className={`flex w-full flex-col p-8 min-h-screen transition-colors duration-300 ${isDarkMode ? "bg-dark-bg text-white" : "bg-gray-50 text-gray-900"}`}>
      
      {/* HEADER SECTION */}
      <div className="flex flex-col md:flex-row justify-between items-center mb-6 gap-6">
        <Header name="Master Organization Chart" />
        <div className="flex items-center gap-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
            <input 
              type="text" placeholder="Search name or team..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)}
              className={`pl-10 pr-4 py-2 rounded-lg border text-sm w-72 focus:ring-2 focus:ring-orange-500 outline-none ${isDarkMode ? "bg-gray-800 border-gray-700 text-white" : "bg-white border-gray-300 text-black"}`}
            />
          </div>
          <div className={`flex items-center gap-2 p-1.5 rounded-lg border ${isDarkMode ? "bg-gray-800 border-gray-700" : "bg-white border-gray-300"}`}>
            <button onClick={handleZoomOut} className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"><ZoomOut className="w-4 h-4"/></button>
            <span className="text-xs font-bold w-12 text-center select-none">{Math.round(zoom * 100)}%</span>
            <button onClick={handleZoomIn} className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"><ZoomIn className="w-4 h-4"/></button>
          </div>
        </div>
      </div>

      {/* CHART AREA */}
      <div className={`w-full overflow-auto pb-48 rounded-xl border transition-colors duration-300 ${isDarkMode ? "border-gray-800 bg-black/10" : "border-gray-200 bg-white"}`}>
        <div 
          className="flex flex-col items-start min-w-max p-20 transition-transform duration-200 ease-out origin-top-left"
          style={{ transform: `scale(${zoom})` }}
        >
          <div className="flex flex-col items-center w-full">
            {/* LEVEL 1 */}
            <div className={`relative ${nodeBg} w-[350px] p-6 text-center shadow-xl border-2 ${nodeBorder} text-black rounded-sm`}>
              <h3 className="font-bold text-lg uppercase tracking-tight">{globalLead.name}</h3>
              <p className="text-xs font-bold opacity-70 italic">{globalLead.title}</p>
              <div className="absolute -bottom-4 -right-4 bg-slate-900 text-white text-xs font-bold w-10 h-10 flex items-center justify-center rounded-full border-4 border-white shadow-lg">{globalLead.count}</div>
            </div>

            <div className={`w-px h-16 ${lineStroke}`}></div>

            {/* LEVEL 2 */}
            <div className="flex gap-10 relative">
              {directReports.map((node, index) => {
                const match = isMatch(node.name, node.title, node.subTeams?.flatMap(s => s.members));
                const columnWidth = node.isVivek ? "w-[680px]" : "w-[210px]";

                return (
                  <div key={node.id} className={`relative flex flex-col items-center ${columnWidth} transition-all duration-300`}>
                    <div className={`absolute top-0 h-px ${lineStroke} ${index === 0 ? "left-1/2 right-0" : index === directReports.length - 1 ? "left-0 right-1/2" : "left-0 right-0"}`} />
                    <div className={`w-px h-10 ${lineStroke}`}></div>

                    <div className={`flex flex-col items-center w-full transition-all duration-500 ${match ? "opacity-100 translate-y-0" : "opacity-10 grayscale scale-95"}`}>
                      <div className={`relative ${nodeBg} w-[210px] p-4 text-center shadow-md border-2 ${node.isVivek ? "border-blue-600 ring-4 ring-blue-50/50" : nodeBorder} text-black min-h-[115px] flex flex-col justify-center rounded-sm transition-all`}>
                        <h4 className="font-bold text-[12px] uppercase leading-tight">{node.name}</h4>
                        <p className="text-[10px] font-semibold opacity-75 mt-1">{node.title}</p>
                        {node.isVivek && <div className="absolute -top-3 -right-3 bg-blue-600 text-white p-1.5 rounded-full shadow-lg"><User className="w-4 h-4" /></div>}
                      </div>

                      {node.isVivek && node.subTeams ? (
                        <div className="flex flex-col items-center w-full">
                          <div className={`w-px h-12 ${lineStroke}`}></div>
                          <div className="flex gap-8 relative w-full justify-center px-4">
                            {node.subTeams.map((sub, sIdx) => (
                              <div key={sub.manager} className="relative flex flex-col items-center w-[200px]">
                                <div className={`absolute top-0 h-px ${lineStroke} ${sIdx === 0 ? "left-1/2 right-0" : sIdx === node.subTeams!.length - 1 ? "left-0 right-1/2" : "left-0 right-0"}`} />
                                <div className={`w-px h-6 ${lineStroke}`}></div>
                                <div className="bg-white dark:bg-gray-800 border-2 border-blue-500 p-3 w-full text-center rounded-sm shadow-md transition-colors">
                                  <p className="text-[11px] font-bold text-blue-600 dark:text-blue-400">{sub.manager}</p>
                                  <p className="text-[9px] font-black uppercase opacity-50 tracking-tighter">{sub.lob}</p>
                                </div>
                                <ArrowDown className="h-4 w-4 my-2 text-blue-500" strokeWidth={3} />
                                <div className="bg-white dark:bg-gray-900 border-2 border-gray-200 dark:border-gray-700 w-full rounded-sm overflow-hidden shadow-inner transition-colors">
                                  <div className="bg-gray-50 dark:bg-gray-800/50 px-2 py-1.5 text-[9px] font-bold text-gray-500 uppercase border-b border-gray-200 dark:border-gray-700">Team Members</div>
                                  <div className="p-2 space-y-1.5 max-h-[350px] overflow-y-auto custom-scrollbar">
                                    {sub.members.map(m => (
                                      <div key={m} className={`text-[10px] px-2 py-0.5 rounded-sm transition-all ${m.toLowerCase().includes(searchTerm.toLowerCase()) && searchTerm !== "" ? "bg-yellow-300 text-black font-bold scale-105 shadow-sm" : "text-gray-600 dark:text-gray-400"}`}>
                                        • {m}
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      ) : (
                        <>
                          <ArrowDown className={`h-5 w-5 my-3 ${isDarkMode ? 'text-gray-600' : 'text-gray-400'}`} strokeWidth={3} />
                          <div className={`${nodeBg} w-[190px] py-3 border-2 ${nodeBorder} rounded-sm flex flex-col items-center justify-center text-black font-black shadow-sm`}>
                            <span className="text-[11px] tracking-tight">{node.p2} P2</span>
                            <div className="w-1/2 h-[1px] bg-orange-300 my-1.5"></div>
                            <span className="text-[11px] tracking-tight">{node.p3} P3</span>
                          </div>
                          <div className="mt-4 bg-[#0000ff] text-white w-[190px] py-3 text-[10px] font-extrabold text-center rounded-sm shadow-lg uppercase tracking-widest border border-blue-800">
                            {node.geo}
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* --- FLOATING HIDEABLE SUPPORT BUTTON --- */}
      <div className="fixed bottom-8 right-8 z-[110]" ref={supportRef}>
        {!isSupportOpen ? (
          <button 
            onClick={() => setIsSupportOpen(true)}
            className="group flex items-center bg-blue-600 hover:bg-blue-700 text-white p-3 rounded-full shadow-2xl transition-all hover:scale-105 active:scale-95"
          >
            <HelpCircle className="w-6 h-6 shrink-0" />
            <span className="max-w-0 overflow-hidden opacity-0 group-hover:max-w-xs group-hover:opacity-100 group-hover:ml-2 transition-all duration-500 ease-in-out whitespace-nowrap font-bold text-sm">
              Need Support?
            </span>
          </button>
        ) : (
          <div className={`flex flex-col gap-3 p-4 rounded-2xl border shadow-2xl backdrop-blur-md animate-in fade-in zoom-in slide-in-from-bottom-4 duration-300 w-[320px] ${isDarkMode ? "bg-gray-900/95 border-gray-700" : "bg-white/95 border-gray-200"}`}>
            
            {/* Header */}
            <div className="flex justify-between items-start pb-2 border-b border-gray-500/10">
              <div className="flex flex-col">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-blue-600" />
                  <span className="text-xs font-black uppercase tracking-wider">Automation Help</span>
                </div>
                <p className="text-[10px] opacity-60">Tool issues or data queries</p>
              </div>
              <button 
                onClick={() => setIsSupportOpen(false)}
                className="p-1 hover:bg-gray-500/10 rounded-lg transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* DL Section */}
            <div className={`p-3 rounded-xl border flex flex-col gap-1 transition-colors ${isDarkMode ? "bg-blue-950/20 border-blue-800/50" : "bg-blue-50/50 border-blue-100"}`}>
              <span className="text-[9px] font-black uppercase tracking-widest text-blue-600/70">Team Distribution List</span>
              <div className="flex items-center gap-2">
                <Mail className="w-3.5 h-3.5 text-blue-600" />
                <span className="text-[11px] font-bold text-blue-600 select-all break-all leading-tight">AutomationGDTGMO@nielsen.com</span>
              </div>
            </div>

            {/* POC List */}
            <div className="flex flex-col gap-3 px-1">
              {techSupport.map((poc) => (
                <div key={poc.name} className="flex flex-col gap-0.5 group">
                  <span className="text-[11px] font-bold leading-tight group-hover:text-blue-500 transition-colors">
                    {poc.name}
                  </span>
                  <a 
                    href={`mailto:${poc.email}`} 
                    className="text-[10px] opacity-60 hover:opacity-100 hover:text-blue-600 transition-all truncate"
                  >
                    {poc.email}
                  </a>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Teams;

// "use client";

// import { useGetTeamsQuery } from "@/state/api";
// import React from "react";
// import { useAppSelector } from "../redux";
// import Header from "@/components/Header";
// import {
//   Briefcase,
//   User,
//   Users,
//   Star,
//   ShieldCheck,
// } from "lucide-react";

// const Teams = () => {
//   const { data: teams, isLoading, isError } = useGetTeamsQuery();
//   const isDarkMode = useAppSelector((state) => state.global.isDarkMode);

//   if (isLoading) return <div className="p-8">Loading teams...</div>;
//   if (isError || !teams) return <div className="p-8 text-red-500">Error fetching teams</div>;

//   return (
//     <div className="flex w-full flex-col p-8 bg-gray-50 dark:bg-dark-bg min-h-screen">
//       <Header name="Teams Organization" />
      
//       {/* Grid Layout for Team Trees */}
//       <div className="mt-8 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-10">
//         {teams.map((team) => (
//           <div key={team.teamId} className="flex justify-center">
//             <TeamTree 
//               team={team} 
//               isDarkMode={isDarkMode} 
//             />
//           </div>
//         ))}
//       </div>
//     </div>
//   );
// };

// // --- Custom Component: Single Team Org Tree ---
// const TeamTree = ({ team, isDarkMode }: { team: any; isDarkMode: boolean }) => {
  
//   // Common card styles
//   const cardStyle = `
//     flex flex-col items-center justify-center rounded-lg border p-3 shadow-sm w-32
//     ${isDarkMode ? "bg-gray-800 border-gray-700 text-white" : "bg-white border-gray-200 text-gray-800"}
//   `;

//   return (
//     <div className="flex flex-col items-center">
      
//       {/* LEVEL 1: Team Name (Root) */}
//       <div className={`${cardStyle} !w-48 border-b-4 border-b-blue-500`}>
//         <Users className="h-6 w-6 text-blue-500 mb-1" />
//         <h3 className="text-lg font-bold tracking-tight text-center">{team.teamName}</h3>
//         <span className="text-xs text-gray-500 uppercase tracking-widest">Team ID: {team.id}</span>
//       </div>

//       {/* Vertical Connector Line */}
//       <div className={`h-8 w-px ${isDarkMode ? "bg-gray-600" : "bg-gray-300"}`}></div>

//       {/* Horizontal Connector Line (Split) */}
//       <div className="relative w-full flex justify-center">
//         {/* The horizontal bar */}
//         <div className={`absolute top-0 h-px w-[60%] ${isDarkMode ? "bg-gray-600" : "bg-gray-300"}`}></div>
        
//         {/* Left Branch Vertical */}
//         <div className={`absolute top-0 left-[20%] h-6 w-px ${isDarkMode ? "bg-gray-600" : "bg-gray-300"}`}></div>
        
//         {/* Right Branch Vertical */}
//         <div className={`absolute top-0 right-[20%] h-6 w-px ${isDarkMode ? "bg-gray-600" : "bg-gray-300"}`}></div>
//       </div>

//       {/* Spacing for the vertical lines above to reach the next nodes */}
//       <div className="h-6"></div>

//       {/* LEVEL 2: PM and PO */}
//       <div className="flex gap-8 w-full justify-between px-2">
        
//         {/* Left Node: Project Manager */}
//         <div className="flex flex-col items-center">
//            <div className={`${cardStyle}`}>
//             <Briefcase className="h-5 w-5 text-green-500 mb-1" />
//             <p className="text-sm font-semibold truncate w-full text-center">
//               {team.projectManagerUsername || "Unassigned"}
//             </p>
//             <span className="text-[10px] text-gray-500">Project Manager</span>
//            </div>
//         </div>

//         {/* Right Node: Product Owner */}
//         <div className="flex flex-col items-center">
//            <div className={`${cardStyle}`}>
//             <Star className="h-5 w-5 text-orange-500 mb-1" />
//             <p className="text-sm font-semibold truncate w-full text-center">
//               {team.productOwnerUsername || "Unassigned"}
//             </p>
//             <span className="text-[10px] text-gray-500">Product Owner</span>
//            </div>
//         </div>

//       </div>
//     </div>
//   );
// };

// export default Teams;
