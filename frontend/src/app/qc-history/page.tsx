"use client";

import React, { useState, useMemo } from "react";
import { 
  Search, Filter, Clock, AlertCircle, CheckCircle2, User, FolderGit2, Hash,
  Activity, CalendarDays, ChevronRight, ShieldCheck, X, BarChart3, MapPin, FileText,
  TrendingDown, TrendingUp, Users, Sparkles, Zap, Layers, Target, Info,
  LineChart as LineChartIcon, Download, Calendar, ArrowRight, Truck, HelpCircle
} from "lucide-react";
import { useGetQcHistoryQuery, useGetDeliveryDashboardQuery, useLazyDownloadWeeklyQcReportQuery } from "@/state/api"; 
import { 
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell, 
  ScatterChart, Scatter, ZAxis, LabelList,
  XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, 
  ResponsiveContainer, Legend, LineChart, Line,
  ComposedChart, Brush, Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  ReferenceLine
} from "recharts";

// --- HELPER FUNCTIONS ---
const formatCheckName = (key: string) => key.replace(/_OK$/i, "").replace(/_check_result$/i, "").replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
const truncateText = (text: string, maxLength: number = 14) => (!text ? "" : text.length > maxLength ? text.substring(0, maxLength) + "..." : text);
const formatLargeNumber = (num: number) => {
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
  if (num >= 1000) return (num / 1000).toFixed(1) + 'k';
  return num.toString();
};

const CHART_COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#14b8a6', '#f97316', '#6366f1', '#ec4899', '#06b6d4'];

// --- CUSTOM TOOLTIP COMPONENT ---
const InfoTooltip = ({ text, position = "top", align = "center" }: { text: string, position?: "top" | "bottom", align?: "center" | "left" | "right" }) => {
  const posClasses = position === "top" ? "bottom-full mb-2" : "top-full mt-2";
  const alignClasses = align === "left" ? "left-0" : align === "right" ? "right-0" : "left-1/2 -translate-x-1/2";
  const arrowClasses = position === "top" ? "top-full border-t-slate-800 dark:border-t-slate-700" : "bottom-full border-b-slate-800 dark:border-b-slate-700";
  const arrowAlignClasses = align === "left" ? "left-2" : align === "right" ? "right-2" : "left-1/2 -translate-x-1/2";

  return (
    <span className="relative group inline-flex items-center justify-center ml-1.5 cursor-help z-50">
      <Info size={12} className="text-slate-400 group-hover:text-blue-500 transition-colors" />
      <span className={`absolute ${posClasses} ${alignClasses} hidden group-hover:block w-52 p-2 bg-slate-800 dark:bg-slate-700 text-white text-[10px] leading-relaxed rounded-lg shadow-xl font-normal normalcase tracking-normal pointer-events-none z-[100] whitespace-normal`}>
        {text}
        <span className={`absolute ${arrowClasses} ${arrowAlignClasses} border-4 border-transparent`}></span>
      </span>
    </span>
  );
};

const QcHistoryDashboard = () => {
  const { data: historyData = [], isLoading: historyLoading, isError: historyError } = useGetQcHistoryQuery();
  const { data: deliveryData = [], isLoading: deliveryLoading } = useGetDeliveryDashboardQuery();

  const [searchTerm, setSearchTerm] = useState("");
  const [filterStatus, setFilterStatus] = useState<"all" | "clean" | "error">("all");
  const [isFilterOpen, setIsFilterOpen] = useState(false);
  const [selectedRecord, setSelectedRecord] = useState<any | null>(null);
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({});
  
  const [exportStartDate, setExportStartDate] = useState("");
  const [exportEndDate, setExportEndDate] = useState("");
  
  const [deliveryFilterStart, setDeliveryFilterStart] = useState("");
  const [deliveryFilterEnd, setDeliveryFilterEnd] = useState("");

  const [activeChartLines, setActiveChartLines] = useState<Record<string, string[]>>({});

  const toggleGroup = (groupId: string) => {
    setExpandedGroups(prev => ({ ...prev, [groupId]: !prev[groupId] }));
  };

  const toggleChartLine = (groupId: string, lineName: string) => {
    setActiveChartLines(prev => {
      const current = prev[groupId] || ['Total Errors'];
      if (current.includes(lineName)) {
        if (current.length === 1) return prev; 
        return { ...prev, [groupId]: current.filter(l => l !== lineName) };
      }
      return { ...prev, [groupId]: [...current, lineName] };
    });
  };

  const handleDownloadReport = () => {
    const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
    let url = `${baseUrl}/qc/history/weekly-export`;
    const params = new URLSearchParams();
    if (exportStartDate) params.append("start_date", exportStartDate);
    if (exportEndDate) params.append("end_date", exportEndDate);
    if (params.toString()) url += `?${params.toString()}`;
    window.open(url, "_blank");
  };

  // --- DYNAMIC DATA & SMART ANALYTICS ENGINE ---
  const { 
    filteredData, kpis, chartData, globalRuleStats, 
    deliveryRiskData, pipelineTableData
  } = useMemo(() => {
    
    const unlockedHistory = historyData.map((row: any) => ({ ...row }));

    const totalRuns = unlockedHistory.length;
    let globalEvals = 0;
    let globalFails = 0;
    let totalDuration = 0;

    const projectErrorRateMap: Record<string, { evals: number, fails: number }> = {};
    const ruleStats: Record<string, { evals: number, fails: number }> = {};
    const userMap: Record<string, number> = {};
    const anomalies: any[] = [];
    const trendMap: Record<string, { date: string, runs: number, totalEvals: number, totalFails: number }> = {};

    unlockedHistory.forEach((row: any) => {
      totalDuration += row.run_duration || 0;
      const user = row.user_name || "System";
      userMap[user] = (userMap[user] || 0) + 1;

      const date = new Date(row.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
      if (!trendMap[date]) trendMap[date] = { date, runs: 0, totalEvals: 0, totalFails: 0 };
      trendMap[date].runs += 1;

      let fileMaxRows = 0;
      let fileTotalEvals = 0;
      let fileTotalFails = 0;

      if (row.qc_summary) {
        Object.entries(row.qc_summary).forEach(([ruleKey, stats]: [string, any]) => {
          const cleanName = formatCheckName(ruleKey);
          const evals = stats.Total_Evaluated || 0;
          const fails = stats.Failed || 0;

          globalEvals += evals;
          globalFails += fails;
          fileTotalEvals += evals;
          fileTotalFails += fails;
          if (evals > fileMaxRows) fileMaxRows = evals;

          if (row.project_name) {
            if (!projectErrorRateMap[row.project_name]) projectErrorRateMap[row.project_name] = { evals: 0, fails: 0 };
            projectErrorRateMap[row.project_name].evals += evals;
            projectErrorRateMap[row.project_name].fails += fails;
          }

          if (!ruleStats[cleanName]) ruleStats[cleanName] = { evals: 0, fails: 0 };
          ruleStats[cleanName].evals += evals;
          ruleStats[cleanName].fails += fails;
        });
      }

      trendMap[date].totalEvals += fileTotalEvals;
      trendMap[date].totalFails += fileTotalFails;

      row._computedErrorRate = fileTotalEvals > 0 ? (fileTotalFails / fileTotalEvals) * 100 : 0;
      row._computedSpeed = fileMaxRows > 0 && row.run_duration > 0 ? fileMaxRows / row.run_duration : 0;
      row._computedLineItems = fileMaxRows; 
    });

    const avgDuration = totalRuns > 0 ? totalDuration / totalRuns : 0;
    const globalErrorRate = globalEvals > 0 ? (globalFails / globalEvals) * 100 : 0;

    const densityBuckets = { "Clean (0%)": 0, "Low (1-10%)": 0, "Medium (11-25%)": 0, "High (>25%)": 0 };

    unlockedHistory.forEach((row: any) => {
      const isSlow = row.run_duration > avgDuration * 2 && row.run_duration > 15;
      const isBuggy = (row._computedErrorRate || 0) > 25; 
      if (isSlow || isBuggy) anomalies.push({ ...row, isSlow, isBuggy });

      const rate = row._computedErrorRate || 0;
      if (rate === 0) densityBuckets["Clean (0%)"]++;
      else if (rate <= 10) densityBuckets["Low (1-10%)"]++;
      else if (rate <= 25) densityBuckets["Medium (11-25%)"]++;
      else densityBuckets["High (>25%)"]++;
    });

    const densityDistData = [
      { name: "Clean (0%)", count: densityBuckets["Clean (0%)"], fill: "#10b981" },
      { name: "Low (1-10%)", count: densityBuckets["Low (1-10%)"], fill: "#3b82f6" },
      { name: "Medium (11-25%)", count: densityBuckets["Medium (11-25%)"], fill: "#f59e0b" },
      { name: "High (>25%)", count: densityBuckets["High (>25%)"], fill: "#f43f5e" },
    ];

    const trendTimeline = Object.values(trendMap).map(t => ({
      ...t,
      errorRate: t.totalEvals > 0 ? Number(((t.totalFails / t.totalEvals) * 100).toFixed(1)) : 0
    })).reverse();

    const projectErrors = Object.keys(projectErrorRateMap)
      .map(name => ({
        fullName: name,
        shortName: truncateText(name, 16),
        errorRate: projectErrorRateMap[name].evals > 0 
          ? Number(((projectErrorRateMap[name].fails / projectErrorRateMap[name].evals) * 100).toFixed(1)) 
          : 0
      }))
      .filter(p => p.errorRate > 0)
      .sort((a, b) => b.errorRate - a.errorRate)
      .slice(0, 5);

    const topFailedRules = Object.keys(ruleStats)
      .map(name => ({
        fullName: name,
        shortName: truncateText(name, 16),
        failRate: ruleStats[name].evals > 0 ? Number(((ruleStats[name].fails / ruleStats[name].evals) * 100).toFixed(1)) : 0
      }))
      .filter(r => r.failRate > 0)
      .sort((a, b) => b.failRate - a.failRate)
      .slice(0, 5);

    const topUsers = Object.keys(userMap)
      .map(u => ({ fullName: u, shortName: truncateText(u, 14), runs: userMap[u] }))
      .sort((a, b) => b.runs - a.runs).slice(0, 5);

    const scatterData = unlockedHistory.map((row: any) => ({
      name: row.project_name || "Unknown",
      id: row.manual_rosco_id || row.rosco_id,
      duration: Number((row.run_duration || 0).toFixed(1)),
      errorRate: Number((row._computedErrorRate || 0).toFixed(1)),
      lineItems: row._computedLineItems || 0,
      isAnomaly: (row.run_duration > avgDuration * 2 && row.run_duration > 15) || ((row._computedErrorRate || 0) > 25)
    }));

    // --- GROUP DATABASE HISTORY BY ROSCO ID ---
    const groupedMap: Record<string, any[]> = {};
    unlockedHistory.forEach((row: any) => {
      const rid = row.manual_rosco_id || row.rosco_id || "Unknown_ID";
      if (!groupedMap[rid]) groupedMap[rid] = [];
      groupedMap[rid].push(row);
    });

    const historyStatusMap: Record<string, any> = {};

    let processedGroups = Object.values(groupedMap).map((runs) => {
      runs.sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());
      const firstRun = runs[0];
      const latestRun = runs[runs.length - 1];
      const groupId = firstRun.manual_rosco_id || firstRun.rosco_id || "Unknown";
      
      let fileTotalEvals = 0;
      let fileTotalFails = 0;
      let maxRows = 0;
      
      if (latestRun.qc_summary) {
        Object.values(latestRun.qc_summary).forEach((stats: any) => {
          fileTotalEvals += stats.Total_Evaluated || 0;
          fileTotalFails += stats.Failed || 0;
          if (stats.Total_Evaluated > maxRows) maxRows = stats.Total_Evaluated;
        });
      }
      latestRun._computedErrorRate = fileTotalEvals > 0 ? (fileTotalFails / fileTotalEvals) * 100 : 0;
      latestRun._computedSpeed = maxRows > 0 && latestRun.run_duration > 0 ? maxRows / latestRun.run_duration : 0;

      // Track this for the Delivery Pipeline cross-reference
      historyStatusMap[groupId] = {
        hasRun: true,
        isClean: latestRun.error_count === 0,
        errorCount: latestRun.error_count,
        totalRuns: runs.length,
        errorRate: latestRun._computedErrorRate
      };

      const allFailedRules = new Set<string>();

      runs.forEach((run: any, index: number) => {
        run.stepFixed = [];
        run.stepBroken = [];
        run.errorDelta = 0;
        if (run.qc_summary) {
          Object.entries(run.qc_summary).forEach(([rule, stats]: any) => {
            if (stats.Failed > 0) allFailedRules.add(formatCheckName(rule));
          });
        }
        if (index > 0) {
          const prevRun = runs[index - 1];
          run.errorDelta = (run.error_count || 0) - (prevRun.error_count || 0);

          if (prevRun.qc_summary && run.qc_summary) {
            Object.entries(prevRun.qc_summary).forEach(([rule, stats]: any) => {
              if (stats.Failed > 0 && (!run.qc_summary[rule] || run.qc_summary[rule].Failed === 0)) run.stepFixed.push(formatCheckName(rule));
            });
            Object.entries(run.qc_summary).forEach(([rule, stats]: any) => {
              if (stats.Failed > 0 && (!prevRun.qc_summary[rule] || prevRun.qc_summary[rule].Failed === 0)) run.stepBroken.push(formatCheckName(rule));
            });
          }
        }
      });

      const overallFixed: string[] = []; 
      const overallBroken: string[] = []; 
      if (runs.length > 1 && firstRun.qc_summary && latestRun.qc_summary) {
        Object.entries(firstRun.qc_summary).forEach(([rule, stats]: any) => {
          if (stats.Failed > 0 && latestRun.qc_summary[rule]?.Failed === 0) overallFixed.push(formatCheckName(rule));
        });
        Object.entries(latestRun.qc_summary).forEach(([rule, stats]: any) => {
          if (stats.Failed > 0 && (!firstRun.qc_summary[rule] || firstRun.qc_summary[rule].Failed === 0)) overallBroken.push(formatCheckName(rule));
        });
      }

      return {
        id: groupId,
        project_name: latestRun.project_name,
        destination_id: latestRun.destination_id,
        user_name: latestRun.user_name,
        latestRun,
        allRuns: runs, 
        totalRuns: runs.length,
        overallFixed,
        overallBroken,
        allFailedRules: Array.from(allFailedRules),
        deliveryInfo: null as any // 🎯 FIX: Declare the property upfront so TS doesn't complain
      };
    });

    // --- 🎯 NEW: DELIVERY READINESS PIPELINE LOGIC ---
    let pipelineList: any[] = [];

    deliveryData.forEach((d: any) => {
      if (!d.original_delivery_date) return;
      
      const deliveryDate = new Date(d.original_delivery_date).getTime();
      let includeRecord = true;
      if (deliveryFilterStart && deliveryFilterEnd) {
        const start = new Date(deliveryFilterStart).getTime();
        const end = new Date(deliveryFilterEnd).getTime() + 86400000;
        if (deliveryDate < start || deliveryDate > end) includeRecord = false;
      } else if (deliveryFilterStart) {
        if (deliveryDate < new Date(deliveryFilterStart).getTime()) includeRecord = false;
      } else if (deliveryFilterEnd) {
        if (deliveryDate > new Date(deliveryFilterEnd).getTime() + 86400000) includeRecord = false;
      }

      if (!includeRecord) return;

      const hStats = historyStatusMap[d.tracking_id];
      let status = "Not Run";
      if (hStats) {
        status = hStats.isClean ? "Clean" : "Failing";
      }

      pipelineList.push({
        ...d,
        qc_status: status,
        total_qc_runs: hStats ? hStats.totalRuns : 0,
        final_error_rate: hStats ? hStats.errorRate : null,
        error_count: hStats ? hStats.errorCount : null
      });
    });

    pipelineList.sort((a, b) => new Date(a.original_delivery_date).getTime() - new Date(b.original_delivery_date).getTime());

    // 🎯 NEW: Transform Pipeline Data into Scatter Plot Matrix Data
    const mappedRiskData = pipelineList.map((d: any) => {
      // Force "Not Run" items below the 0% line (e.g., -15%) so they separate visually
      const plotErrorRate = d.qc_status === "Not Run" ? -15 : (d.final_error_rate || 0);
      
      return {
        date: new Date(d.original_delivery_date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
        originalDate: d.original_delivery_date,
        roscoId: d.tracking_id,
        deliveryId: d.delivery_uid,
        projectName: d.project_name || d.client_account,
        status: d.qc_status,
        runs: d.total_qc_runs,
        errorCount: d.error_count || 0,
        errorRate: plotErrorRate, // The Y-Axis value
        realErrorRate: d.final_error_rate || 0 // The actual label value
      };
    });

    // Grouping delivery tracking IDs back to processedGroups for main table mapping
    const deliveryLookup: Record<string, any[]> = {};
    pipelineList.forEach(d => {
      if (!deliveryLookup[d.tracking_id]) deliveryLookup[d.tracking_id] = [];
      deliveryLookup[d.tracking_id].push(d);
    });

    processedGroups.forEach(group => {
      const allDeliveries = deliveryLookup[group.id] || [];
      if (allDeliveries.length > 0) {
        group.deliveryInfo = { ...allDeliveries[0], _total_associated_deliveries: allDeliveries.length };
      }
    });

    // Apply Search/Filters
    let filteredGroups = processedGroups.filter((group: any) => {
      const searchLower = searchTerm.toLowerCase();
      return (
        (group.project_name || "").toLowerCase().includes(searchLower) ||
        (group.user_name || "").toLowerCase().includes(searchLower) ||
        (group.id || "").toLowerCase().includes(searchLower)
      );
    });

    if (filterStatus === "clean") filteredGroups = filteredGroups.filter(g => g.latestRun.error_count === 0);
    else if (filterStatus === "error") filteredGroups = filteredGroups.filter(g => g.latestRun.error_count > 0);

    return { 
      filteredData: filteredGroups, 
      kpis: { totalRuns, globalEvals, avgDuration: avgDuration.toFixed(1), globalErrorRate: globalErrorRate.toFixed(1) },
      chartData: { trendTimeline, projectErrors, topFailedRules, scatterData, topUsers, densityDistData },
      deliveryRiskData: mappedRiskData,
      pipelineTableData: pipelineList,
      globalRuleStats: ruleStats
    };
  }, [historyData, deliveryData, searchTerm, filterStatus, deliveryFilterStart, deliveryFilterEnd]);

  const modalAnalytics = useMemo(() => {
    if (!selectedRecord || !selectedRecord.qc_summary) return null;
    let totalPass = 0, totalFail = 0, totalNA = 0;
    const failedRules: any[] = [];

    Object.entries(selectedRecord.qc_summary).forEach(([key, stats]: any) => {
      totalPass += stats.Passed || 0;
      totalFail += stats.Failed || 0;
      totalNA += stats.NA || 0;

      if (stats.Failed > 0) {
        failedRules.push({ fullName: formatCheckName(key), shortName: truncateText(formatCheckName(key), 12), fails: stats.Failed });
      }
    });

    const executionData = [
      { name: "Passed Checks", value: totalPass, color: "#10b981" },
      { name: "Failed Checks", value: totalFail, color: "#f43f5e" },
      { name: "N/A / Skipped", value: totalNA, color: "#475569" }
    ].filter(d => d.value > 0);

    failedRules.sort((a, b) => b.fails - a.fails);

    return { executionData, failedRules, totalEvals: totalPass + totalFail + totalNA };
  }, [selectedRecord]);

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const displayName = payload[0].payload?.fullName || label || payload[0].name;
      return (
        <div className="bg-white dark:bg-[#111623] border border-slate-200 dark:border-slate-800 p-3 rounded-lg shadow-2xl z-50 animate-in zoom-in-95 duration-100">
          <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-1">{displayName}</p>
          {payload.map((entry: any, index: number) => (
            <p key={index} className="text-sm font-black flex items-center gap-1" style={{ color: entry.color || entry.payload?.fill || '#3b82f6' }}>
              {entry.value}{entry.dataKey === 'errorRate' || entry.dataKey === 'Total Error Rate' || entry.dataKey === 'failRate' ? '%' : ''} 
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest pl-1">
                {entry.name === 'runs' || entry.name === 'total' ? 'Count' : entry.name}
              </span>
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  const ScatterTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-white dark:bg-[#111623] border border-slate-200 dark:border-slate-800 p-3 rounded-lg shadow-xl z-50 animate-in zoom-in-95 duration-100 min-w-[160px]">
          <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-1 flex items-center gap-1"><Hash size={10}/> {data.id}</p>
          <p className="text-sm font-black dark:text-white mb-2 truncate">{data.name}</p>
          <div className="grid grid-cols-2 gap-2 text-xs font-bold bg-slate-50 dark:bg-slate-800/50 p-2 rounded-md">
            <div><span className="block text-[8px] uppercase text-slate-400">Duration</span><span className="text-amber-500">{data.duration}s</span></div>
            <div><span className="block text-[8px] uppercase text-slate-400">Failure Rate</span><span className="text-rose-500">{data.errorRate}%</span></div>
          </div>
          {data.isAnomaly && <div className="mt-2 text-[9px] uppercase tracking-widest font-black text-rose-500 flex items-center gap-1"><AlertCircle size={10}/> System Anomaly</div>}
        </div>
      );
    }
    return null;
  };

  const CorrelationTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-white dark:bg-[#111623] border border-slate-200 dark:border-slate-800 p-3 rounded-lg shadow-xl z-50 animate-in zoom-in-95 duration-100 min-w-[160px]">
          <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-1 flex items-center gap-1"><Hash size={10}/> {data.id}</p>
          <p className="text-sm font-black dark:text-white mb-2 truncate">{data.name}</p>
          <div className="grid grid-cols-2 gap-2 text-xs font-bold bg-slate-50 dark:bg-slate-800/50 p-2 rounded-md">
            <div><span className="block text-[8px] uppercase text-slate-400">Line Items</span><span className="text-blue-500">{data.lineItems}</span></div>
            <div><span className="block text-[8px] uppercase text-slate-400">Failure Rate</span><span className="text-rose-500">{data.errorRate}%</span></div>
          </div>
        </div>
      );
    }
    return null;
  };

  // 🎯 NEW: Master Tooltip for the Delivery Risk Matrix
  const DeliveryRiskTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-[#111623] border border-indigo-500/30 p-4 rounded-xl shadow-2xl z-50 min-w-[240px] animate-in zoom-in-95">
          <div className="border-b border-slate-700/60 pb-3 mb-3">
            <p className="text-[10px] font-bold uppercase tracking-widest text-indigo-400 mb-1.5 flex items-center gap-1"><Calendar size={10}/> Due: {data.originalDate}</p>
            <p className="text-base font-black text-white flex items-center gap-1"><Hash size={14}/> {data.roscoId}</p>
            <p className="text-xs font-bold text-slate-400 truncate max-w-[240px]">{data.projectName || "Unknown Project"}</p>
            {data.deliveryId && <p className="text-[10px] text-slate-500 font-mono mt-1">Delivery ID: {data.deliveryId}</p>}
          </div>

          {data.status === 'Not Run' ? (
            <div className="flex items-center gap-2 text-slate-400 bg-slate-800/50 p-2 rounded-lg border border-slate-700">
              <HelpCircle size={16}/> <span className="text-xs font-bold">No QC Runs Yet</span>
            </div>
          ) : data.status === 'Clean' ? (
            <div className="flex items-center gap-2 text-emerald-400 bg-emerald-500/10 p-2 rounded-lg border border-emerald-500/20">
              <CheckCircle2 size={16}/> <span className="text-xs font-bold">Ready to Ship ({data.runs} run{data.runs > 1 ? 's' : ''})</span>
            </div>
          ) : (
            <div className="bg-rose-500/10 p-3 rounded-lg border border-rose-500/20">
              <div className="flex items-center justify-between mb-2">
                <span className="flex items-center gap-1.5 text-rose-400 text-xs font-bold"><AlertCircle size={14}/> Failing QC</span>
                <span className="text-[10px] font-bold text-slate-400">{data.runs} runs total</span>
              </div>
              <p className="text-lg font-black text-rose-500">{data.realErrorRate.toFixed(1)}% Error</p>
              <p className="text-[10px] font-bold text-rose-400 mt-1">{data.errorCount} individual errors flagged</p>
            </div>
          )}
        </div>
      );
    }
    return null;
  };

  if (historyLoading || deliveryLoading) return <div className="flex items-center justify-center h-screen bg-[#F9FBFC] dark:bg-[#08090A]"><div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div></div>;
  if (historyError) return <div className="flex items-center justify-center h-screen bg-[#F9FBFC] dark:bg-[#08090A] text-red-500 font-medium">Failed to load QC History.</div>;

  return (
    <div className="min-h-screen bg-[#F9FBFC] dark:bg-[#08090A] p-4 lg:p-8 text-slate-900 dark:text-slate-100 transition-colors duration-300 relative flex flex-col gap-6 overflow-x-hidden">
      
      {/* --- DETAILED ANALYSIS MODAL --- */}
      {selectedRecord && modalAnalytics && (
        <div className="fixed inset-0 z-50 flex items-center justify-end bg-slate-900/60 backdrop-blur-sm p-4 sm:p-6 animate-in fade-in duration-300">
          <div className="absolute inset-0" onClick={() => setSelectedRecord(null)}></div>
          <div className="relative w-full max-w-4xl h-full max-h-[90vh] bg-white dark:bg-[#0B0F1A] border border-slate-200 dark:border-slate-800 rounded-3xl shadow-2xl flex flex-col overflow-hidden animate-in slide-in-from-right-8 duration-500">
            <div className="flex justify-between items-start p-6 border-b border-slate-100 dark:border-slate-800/60 bg-slate-50/50 dark:bg-white/[0.02] shrink-0">
              <div>
                <h2 className="text-xl font-black text-slate-800 dark:text-white flex items-center gap-2 mb-1"><BarChart3 className="text-blue-500" /> Advanced Run Analytics</h2>
                <div className="flex items-center gap-3 text-xs font-medium text-slate-500 dark:text-slate-400">
                  <span className="flex items-center gap-1"><FolderGit2 size={14}/> {selectedRecord.project_name || "Unknown"}</span>
                  <span className="w-1 h-1 rounded-full bg-slate-300 dark:bg-slate-700"></span>
                  <span className="flex items-center gap-1"><Hash size={14}/> {selectedRecord.manual_rosco_id || selectedRecord.rosco_id || "N/A"}</span>
                </div>
              </div>
              <button onClick={() => setSelectedRecord(null)} className="p-2 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-500 rounded-full transition-all hover:rotate-90 hover:scale-110 duration-300"><X size={18} /></button>
            </div>
            
            <div className="flex-1 overflow-y-auto p-14 custom-scrollbar bg-slate-50/30 dark:bg-[#08090A]/50">
              
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
                <div className="p-4 bg-white dark:bg-[#111623] rounded-xl border border-slate-200 dark:border-slate-800/60 shadow-sm hover:-translate-y-1 transition-transform duration-300 animate-in slide-in-from-bottom-2 fill-mode-both" style={{ animationDelay: '100ms' }}>
                  <span className="text-[10px] uppercase font-bold text-slate-400 mb-1 flex items-center">
                    Processing Speed
                  </span>
                  <span className="text-sm font-bold dark:text-slate-200 flex items-center gap-1"><Zap size={14} className="text-amber-500"/> {selectedRecord._computedSpeed.toFixed(0)} rows/sec</span>
                </div>
                <div className="p-4 bg-white dark:bg-[#111623] rounded-xl border border-slate-200 dark:border-slate-800/60 shadow-sm hover:-translate-y-1 transition-transform duration-300 animate-in slide-in-from-bottom-2 fill-mode-both" style={{ animationDelay: '150ms' }}>
                  <span className="text-[10px] uppercase font-bold text-slate-400 mb-1 flex items-center">
                    Time Taken 
                  </span>
                  <span className="text-sm font-bold dark:text-slate-200 flex items-center gap-1"><Clock size={14} className="text-blue-500"/> {selectedRecord.run_duration}s</span>
                </div>
                <div className="p-4 bg-white dark:bg-[#111623] rounded-xl border border-slate-200 dark:border-slate-800/60 shadow-sm hover:-translate-y-1 transition-transform duration-300 animate-in slide-in-from-bottom-2 fill-mode-both" style={{ animationDelay: '200ms' }}>
                  <span className="text-[10px] uppercase font-bold text-slate-400 mb-1 flex items-center">
                    Absolute Errors 
                  </span>
                  <span className={`text-sm font-bold flex items-center gap-1 ${selectedRecord.error_count > 0 ? "text-rose-500" : "text-emerald-500"}`}>
                    {selectedRecord.error_count > 0 ? <AlertCircle size={14}/> : <CheckCircle2 size={14}/>} {selectedRecord.error_count}
                  </span>
                </div>
                <div className="p-4 bg-white dark:bg-[#111623] rounded-xl border border-slate-200 dark:border-slate-800/60 shadow-sm hover:-translate-y-1 transition-transform duration-300 animate-in slide-in-from-bottom-2 fill-mode-both" style={{ animationDelay: '250ms' }}>
                  <span className="text-[10px] uppercase font-bold text-slate-400 mb-1 flex items-center">
                    Error Density 
                  </span>
                  <span className={`text-sm font-bold flex items-center gap-1 ${selectedRecord._computedErrorRate > 10 ? "text-rose-500" : "text-emerald-500"}`}>
                    <Target size={14}/> {selectedRecord._computedErrorRate.toFixed(1)}% Failure
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8 h-56">
                
                <div className="bg-white dark:bg-[#111623] border border-slate-200 dark:border-slate-800/60 rounded-xl p-4 shadow-sm flex flex-col group animate-in zoom-in-95 duration-500 fill-mode-both" style={{ animationDelay: '300ms' }}>
                  <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-2 flex items-center z-10">
                    Quality Footprint (Radar)
                    <InfoTooltip align="left" text="Maps the distribution of failures across all evaluated rules. A larger web means widespread rule failures." />
                  </h3>
                  <div className="flex-1 w-full relative transition-transform duration-500 group-hover:scale-105">
                    {modalAnalytics.failedRules.length > 2 ? (
                      <ResponsiveContainer width="100%" height="100%">
                        <RadarChart cx="50%" cy="50%" outerRadius="70%" data={modalAnalytics.failedRules}>
                          <PolarGrid stroke="#334155" opacity={0.3} />
                          <PolarAngleAxis dataKey="shortName" tick={{ fill: '#64748b', fontSize: 8, fontWeight: 'bold' }} />
                          <PolarRadiusAxis angle={30} domain={[0, 'auto']} tick={false} axisLine={false} />
                          <Radar name="Errors" dataKey="fails" stroke="#8b5cf6" strokeWidth={2} fill="#8b5cf6" fillOpacity={0.4} />
                          <RechartsTooltip contentStyle={{ backgroundColor: '#111623', borderColor: '#1e293b', fontSize: '10px' }} />
                        </RadarChart>
                      </ResponsiveContainer>
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        <span className="text-xs font-bold text-slate-500 text-center px-4">Not enough failed rule variety to generate a Radar map.</span>
                      </div>
                    )}
                  </div>
                </div>

                <div className="bg-white dark:bg-[#111623] border border-slate-200 dark:border-slate-800/60 rounded-xl p-4 shadow-sm relative overflow-hidden animate-in zoom-in-95 duration-500 fill-mode-both" style={{ animationDelay: '400ms' }}>
                  <h3 className="absolute top-4 left-4 text-[10px] font-black uppercase tracking-widest text-slate-400 z-10 flex items-center">
                    Failure Distribution <InfoTooltip align="left" text="Breaks down which specific rules contributed to the total Absolute Errors." />
                  </h3>
                  {modalAnalytics.failedRules.length > 0 ? (
                    <div className="w-full h-full pt-6 transition-transform duration-500 hover:scale-[1.02]">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={modalAnalytics.failedRules} layout="vertical" margin={{ top: 0, right: 10, left: 0, bottom: 0 }}>
                          <XAxis type="number" hide />
                          <YAxis dataKey="shortName" type="category" axisLine={false} tickLine={false} tick={{ fontSize: 9, fill: '#64748b' }} width={85} />
                          <RechartsTooltip cursor={{ fill: 'transparent' }} content={<CustomTooltip />} />
                          <Bar dataKey="fails" name="Errors" fill="#f43f5e" radius={[0, 4, 4, 0]} barSize={12} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  ) : (
                    <div className="w-full h-full flex flex-col items-center justify-center text-center text-emerald-500 bg-emerald-50/50 dark:bg-emerald-500/5 rounded-lg border border-emerald-100 dark:border-emerald-500/10 animate-pulse mt-4">
                      <Sparkles size={24} className="mb-2" />
                      <p className="text-sm font-black uppercase tracking-widest">Perfect Clean Run</p>
                    </div>
                  )}
                </div>
              </div>

              <h3 className="text-sm font-black uppercase tracking-widest text-slate-400 mb-4 border-b border-slate-200 dark:border-slate-800/60 pb-2 animate-in fade-in duration-500 fill-mode-both flex items-center" style={{ animationDelay: '500ms' }}>
                Global Benchmarking by Rule
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {selectedRecord.qc_summary && Object.keys(selectedRecord.qc_summary).length > 0 ? (
                  Object.entries(selectedRecord.qc_summary).map(([key, stats]: [string, any], idx) => {
                    const cleanName = formatCheckName(key);
                    const total = stats.Total_Evaluated || 0;
                    const passed = stats.Passed || 0;
                    const failed = stats.Failed || 0;
                    const na = stats.NA || 0;
                    const percent = total > 0 ? Math.round((passed / total) * 100) : 0;
                    
                    const globalStat = globalRuleStats[cleanName];
                    const localFailRate = total > 0 ? (failed / total) * 100 : 0;
                    const globalFailRate = globalStat && globalStat.evals > 0 ? (globalStat.fails / globalStat.evals) * 100 : 0;
                    const diffPercent = Math.round(localFailRate - globalFailRate);
                    
                    let trendBadge = null;
                    if (total > 0 && globalStat && globalStat.evals > 0) {
                      if (diffPercent > 2) trendBadge = <span className="flex items-center gap-0.5 text-[9px] font-bold bg-rose-50 text-rose-600 dark:bg-rose-500/10 dark:text-rose-400 px-1.5 py-0.5 rounded" title={`Failing ${diffPercent}% more than global average`}><TrendingUp size={10}/> {diffPercent}% vs avg</span>;
                      else if (diffPercent < -2) trendBadge = <span className="flex items-center gap-0.5 text-[9px] font-bold bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-400 px-1.5 py-0.5 rounded" title={`Failing ${Math.abs(diffPercent)}% less than global average`}><TrendingDown size={10}/> {Math.abs(diffPercent)}% vs avg</span>;
                      else trendBadge = <span className="flex items-center gap-0.5 text-[9px] font-bold bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400 px-1.5 py-0.5 rounded">Avg</span>;
                    }

                    const ruleChartData = [
                      { name: 'Passed', value: passed, color: '#10b981' },
                      { name: 'Failed', value: failed, color: '#f43f5e' },
                      { name: 'N/A', value: na, color: '#64748b' } 
                    ].filter(d => d.value > 0);

                    return (
                      <div key={key} className="group p-4 bg-white dark:bg-[#111623] border border-slate-200 dark:border-slate-800/60 rounded-xl shadow-sm flex items-center gap-4 hover:border-blue-500/50 hover:shadow-md transition-all duration-300 animate-in slide-in-from-bottom-4 duration-500 fill-mode-both" style={{ animationDelay: `${500 + (idx * 50)}ms` }}>
                        <div className="h-16 w-16 shrink-0 relative transition-transform duration-500 group-hover:scale-110">
                          {total > 0 ? (
                            <>
                              <ResponsiveContainer width="100%" height="100%">
                                <PieChart>
                                  <Pie data={ruleChartData} innerRadius={18} outerRadius={28} paddingAngle={2} dataKey="value" stroke="none">
                                    {ruleChartData.map((entry, index) => (<Cell key={`cell-${index}`} fill={entry.color} />))}
                                  </Pie>
                                  <RechartsTooltip content={<CustomTooltip />} />
                                </PieChart>
                              </ResponsiveContainer>
                              <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                                <span className={`text-[9px] font-black ${failed > 0 ? 'text-rose-500' : 'text-emerald-500'}`}>{percent}%</span>
                              </div>
                            </>
                          ) : (
                            <div className="w-full h-full rounded-full border-[3px] border-slate-100 dark:border-slate-800 flex items-center justify-center"><span className="text-[9px] font-bold text-slate-400">N/A</span></div>
                          )}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between mb-1">
                            <span className="font-bold text-sm text-slate-700 dark:text-slate-200 block truncate group-hover:text-blue-500 transition-colors" title={cleanName}>{cleanName}</span>
                            {trendBadge}
                          </div>
                          <div className="flex gap-2 text-[10px] font-black uppercase flex-wrap mt-1.5">
                            {failed > 0 && <span className="px-1.5 py-0.5 bg-rose-50 text-rose-600 dark:bg-rose-500/10 dark:text-rose-400 rounded-md border border-rose-200 dark:border-rose-500/20">{failed} Fails</span>}
                            {passed > 0 && <span className="px-1.5 py-0.5 bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-400 rounded-md border border-emerald-200 dark:border-emerald-500/20">{passed} Pass</span>}
                            {na > 0 && <span className="px-1.5 py-0.5 bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400 rounded-md border border-slate-200 dark:border-slate-700">{na} N/A</span>}
                          </div>
                        </div>
                      </div>
                    );
                  })
                ) : <div className="text-sm text-slate-500">No data available.</div>}
              </div>
            </div>
            <div className="p-4 border-t border-slate-100 dark:border-slate-800/60 bg-slate-50/50 dark:bg-white/[0.02] text-xs text-slate-400 flex items-center justify-between shrink-0">
              <span className="flex items-center gap-1"><FileText size={14}/> {selectedRecord.original_filename}</span>
            </div>
          </div>
        </div>
      )}

      {/* HEADER */}
      <div className="mt-2 animate-in fade-in slide-in-from-left-4 duration-500 fill-mode-both flex flex-col xl:flex-row justify-between items-start xl:items-center gap-4" style={{ animationDelay: '100ms' }}>
        <h1 className="text-2xl lg:text-3xl font-black tracking-tight flex items-center gap-3">
          <ShieldCheck className="text-blue-500" size={32} /> General QC Dashboard
        </h1>
        
        <div className="flex flex-col sm:flex-row items-center gap-3 w-full xl:w-auto bg-white dark:bg-[#111623] p-1.5 rounded-xl border border-slate-200 dark:border-slate-800/60 shadow-sm">
          <div className="flex items-center gap-2 px-3 border-r border-slate-200 dark:border-slate-700/60 w-full sm:w-auto">
            <Calendar size={14} className="text-slate-400" />
            <input 
              type="date" 
              value={exportStartDate} 
              onChange={e => setExportStartDate(e.target.value)} 
              className="bg-transparent text-xs outline-none text-slate-600 dark:text-slate-300 font-medium cursor-pointer"
            />
            <span className="text-slate-400 text-xs">-</span>
            <input 
              type="date" 
              value={exportEndDate} 
              onChange={e => setExportEndDate(e.target.value)} 
              className="bg-transparent text-xs outline-none text-slate-600 dark:text-slate-300 font-medium cursor-pointer"
            />
          </div>
          <button 
            onClick={handleDownloadReport}
            className="flex items-center justify-center w-full sm:w-auto gap-2 bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg text-sm font-bold shadow-md hover:-translate-y-0.5 active:scale-95 transition-all duration-200"
          >
            <Download size={14} /> 
            Export Report
          </button>
        </div>
      </div>

      {/* KPI CARDS */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { title: "Total Audits", value: kpis.totalRuns, icon: <Activity />, color: "text-blue-500" },
          { title: "Data Points Verified", value: formatLargeNumber(kpis.globalEvals), icon: <Layers />, color: "text-indigo-500", tooltip: "Sum of all individual cell/row checks evaluated across the entire database history." },
          { title: "Global Error Rate", value: `${kpis.globalErrorRate}%`, icon: <Target />, color: Number(kpis.globalErrorRate) > 10 ? "text-rose-500" : "text-emerald-500", tooltip: "Formula: (Global Fails ÷ Global Data Points Verified) × 100." },
          { title: "Avg Process Time", value: `${kpis.avgDuration}s`, icon: <Clock />, color: "text-amber-500", tooltip: "Average duration of the Python QC script execution." },
        ].map((kpi, idx) => (
          <div key={idx} className="group bg-white dark:bg-[#111623] border border-slate-200 dark:border-slate-800/60 rounded-xl p-5 shadow-sm flex flex-col justify-between hover:-translate-y-1 hover:shadow-md hover:border-blue-500/50 transition-all duration-300 animate-in slide-in-from-bottom-6 fade-in fill-mode-both" style={{ animationDelay: `${(idx * 100) + 200}ms` }}>
            <div className="flex items-center justify-between mb-3">
              <span className="text-[10px] font-black uppercase tracking-widest text-slate-400 group-hover:text-slate-600 dark:group-hover:text-slate-300 transition-colors flex items-center">
                {kpi.title} 
                {kpi.tooltip && <InfoTooltip text={kpi.tooltip} align={idx === 3 ? "right" : "left"} />}
              </span>
              <div className={`${kpi.color} bg-slate-50 dark:bg-slate-800/50 p-2 rounded-lg transition-transform duration-300 group-hover:scale-110 group-hover:rotate-3`}>{React.cloneElement(kpi.icon, { size: 16 })}</div>
            </div>
            <div className="text-2xl font-black dark:text-white transition-transform group-hover:translate-x-1">{kpi.value}</div>
          </div>
        ))}
      </div>

      {/* --- ROW 1 CHARTS: Trends & ANOMALY DETECTION --- */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 h-72">
        
        <div className="lg:col-span-2 bg-white dark:bg-[#111623] border border-slate-200 dark:border-slate-800/60 rounded-xl p-5 shadow-sm flex flex-col group animate-in zoom-in-95 fade-in duration-700 fill-mode-both" style={{ animationDelay: '400ms' }}>
          <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-4 flex items-center gap-2">
            <Activity size={12} className="text-blue-500"/> Volume vs. Failure Rate Overlay
            <InfoTooltip align="left" text="Bars represent total runs (left axis). The Line represents the average failure rate for that day (right axis). Use the slider at the bottom to zoom." />
          </h3>
          <div className="flex-1 w-full min-h-0 transition-transform duration-700 group-hover:scale-[1.005]">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={chartData.trendTimeline} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#334155" opacity={0.2} />
                <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fontSize: 9, fill: '#64748b' }} dy={10} />
                <YAxis yAxisId="left" axisLine={false} tickLine={false} tick={{ fontSize: 9, fill: '#64748b' }} />
                <YAxis yAxisId="right" orientation="right" axisLine={false} tickLine={false} tick={{ fontSize: 9, fill: '#f43f5e' }} tickFormatter={(val) => `${val}%`} />
                <RechartsTooltip 
                  cursor={{ fill: '#334155', opacity: 0.1 }} 
                  contentStyle={{ backgroundColor: '#111623', borderColor: '#1e293b', borderRadius: '8px', color: '#fff', fontSize: '10px' }}
                />
                <Legend verticalAlign="top" height={36} wrapperStyle={{ fontSize: '10px', fontWeight: 'bold' }} />
                <Bar yAxisId="left" dataKey="runs" name="Total Runs" fill="#3b82f6" radius={[4, 4, 0, 0]} barSize={20} />
                <Line yAxisId="right" type="monotone" dataKey="errorRate" name="Avg Error Rate" stroke="#f43f5e" strokeWidth={3} dot={{ r: 3, fill: '#f43f5e' }} activeDot={{ r: 6 }} />
                <Brush dataKey="date" height={20} stroke="#3b82f6" fill="#0B0F1A" tickFormatter={() => ''} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-white dark:bg-[#111623] border border-slate-200 dark:border-slate-800/60 rounded-xl p-5 shadow-sm flex flex-col group relative overflow-hidden animate-in zoom-in-95 fade-in duration-700 fill-mode-both" style={{ animationDelay: '500ms' }}>
          <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-4 flex items-center gap-2">
            <Target size={12}/> Anomaly Detection 
          </h3>
          <div className="flex-1 w-full min-h-0 transition-transform duration-500 group-hover:scale-[1.02]">
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 10, right: 20, bottom: 10, left: -20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.2} />
                <XAxis type="number" dataKey="duration" name="Duration" unit="s" axisLine={false} tickLine={false} tick={{ fontSize: 9, fill: '#64748b' }} />
                <YAxis type="number" dataKey="errorRate" name="Error Rate" unit="%" axisLine={false} tickLine={false} tick={{ fontSize: 9, fill: '#64748b' }} />
                <ZAxis type="number" range={[40, 100]} />
                <RechartsTooltip cursor={{ strokeDasharray: '3 3' }} content={<ScatterTooltip />} />
                <Scatter name="Audits" data={chartData.scatterData}>
                  {chartData.scatterData.map((entry: any, index: number) => (
                    <Cell key={`cell-${index}`} fill={entry.isAnomaly ? '#f43f5e' : '#3b82f6'} opacity={entry.isAnomaly ? 0.9 : 0.6} />
                  ))}
                </Scatter>
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* --- ROW 2 CHARTS: SCALE CORRELATION & DISTRIBUTION --- */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 h-72">
        <div className="bg-white dark:bg-[#111623] border border-slate-200 dark:border-slate-800/60 rounded-xl p-5 shadow-sm flex flex-col group relative overflow-hidden animate-in zoom-in-95 fade-in duration-700 fill-mode-both" style={{ animationDelay: '550ms' }}>
          <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-4 flex items-center gap-2">
            <LineChartIcon size={12}/> Scale vs. Stability (Correlation) <InfoTooltip align="left" text="Plots File Size (Line Items) against its Error Rate. Do larger files break more often?" />
          </h3>
          <div className="flex-1 w-full min-h-0 transition-transform duration-500 group-hover:scale-[1.01]">
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 10, right: 20, bottom: 10, left: -20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.2} />
                <XAxis type="number" dataKey="lineItems" name="Line Items" axisLine={false} tickLine={false} tick={{ fontSize: 9, fill: '#64748b' }} />
                <YAxis type="number" dataKey="errorRate" name="Error Rate" unit="%" axisLine={false} tickLine={false} tick={{ fontSize: 9, fill: '#64748b' }} />
                <ZAxis type="number" range={[40, 80]} />
                <RechartsTooltip cursor={{ strokeDasharray: '3 3' }} content={<CorrelationTooltip />} />
                <Scatter name="Files" data={chartData.scatterData}>
                  {chartData.scatterData.map((entry: any, index: number) => (
                    <Cell key={`cell-${index}`} fill="#8b5cf6" opacity={0.7} />
                  ))}
                </Scatter>
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-white dark:bg-[#111623] border border-slate-200 dark:border-slate-800/60 rounded-xl p-5 shadow-sm flex flex-col min-h-0 group animate-in slide-in-from-bottom-8 fade-in duration-700 fill-mode-both" style={{ animationDelay: '550ms' }}>
          <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-4 flex items-center gap-2">
            <BarChart3 size={12}/> Quality Distribution Matrix <InfoTooltip align="right" text="Groups all files into health buckets based on their error density." />
          </h3>
          <div className="flex-1 w-full text-xs transition-transform duration-500 group-hover:scale-[1.02]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData.densityDistData} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#334155" opacity={0.2} />
                <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#64748b' }} dy={10} />
                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 9, fill: '#64748b' }} />
                <RechartsTooltip cursor={{ fill: 'transparent' }} content={<CustomTooltip />} />
                <Bar dataKey="count" name="Files" radius={[4, 4, 0, 0]} barSize={40}>
                  {chartData.densityDistData.map((entry: any, index: number) => (
                    <Cell key={`cell-${index}`} fill={entry.fill} />
                  ))}
                  <LabelList dataKey="count" position="top" style={{ fill: '#64748b', fontSize: 10, fontWeight: 'bold' }} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* 🎯 NEW SECTION: DELIVERY READINESS PIPELINE */}
      {deliveryRiskData.length > 0 && (
        <div className="mt-8 pt-8 border-t border-slate-200 dark:border-slate-800/60 animate-in fade-in duration-1000 fill-mode-both">
          
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-4">
            <h2 className="text-xl font-black tracking-tight flex items-center gap-3">
              <Truck className="text-indigo-500" size={28} /> Delivery Readiness Tracker
            </h2>
            
            <div className="flex items-center gap-2 bg-white dark:bg-[#0B0F1A] border border-indigo-200 dark:border-indigo-500/30 p-1.5 rounded-lg shadow-sm">
              <span className="text-[10px] font-bold text-indigo-500 uppercase tracking-widest pl-2 flex items-center gap-1">
                <CalendarDays size={10}/> Delivery Date:
              </span>
              <input 
                type="date" 
                value={deliveryFilterStart} 
                onChange={e => setDeliveryFilterStart(e.target.value)} 
                className="bg-transparent text-xs outline-none text-slate-600 dark:text-slate-300 cursor-pointer"
              />
              <span className="text-slate-400 text-xs">-</span>
              <input 
                type="date" 
                value={deliveryFilterEnd} 
                onChange={e => setDeliveryFilterEnd(e.target.value)} 
                className="bg-transparent text-xs outline-none text-slate-600 dark:text-slate-300 cursor-pointer pr-2"
              />
              {(deliveryFilterStart || deliveryFilterEnd) && (
                <button onClick={() => { setDeliveryFilterStart(""); setDeliveryFilterEnd(""); }} className="p-1 hover:bg-indigo-50 dark:hover:bg-indigo-500/20 rounded text-indigo-500 mr-1"><X size={12}/></button>
              )}
            </div>
          </div>
          
          {/* 🎯 THE DELIVERY RISK SCATTER MATRIX */}
          <div className="bg-white dark:bg-[#111623] border border-slate-200 dark:border-slate-800/60 rounded-xl p-5 shadow-sm flex flex-col group h-[450px] mb-4">
            <div className="flex justify-between items-center mb-4 border-b border-slate-100 dark:border-slate-800/60 pb-3">
              <div>
                <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400 flex items-center gap-2">
                  <Activity size={12} className="text-indigo-500"/> Delivery Risk & Error Spread Matrix
                </h3>
                <p className="text-xs text-slate-500 mt-1">Plots individual deliveries by target date. Hover over any dot to see the exact Rosco ID, Delivery ID, and current error rate.</p>
              </div>
              <div className="flex items-center gap-3 text-[10px] font-bold uppercase tracking-widest bg-slate-50 dark:bg-[#0B0F1A] px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700/50">
                <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span> Ready</span>
                <span className="flex items-center gap-1 ml-2"><span className="w-2.5 h-2.5 rounded-full bg-amber-500"></span> Failing</span>
                <span className="flex items-center gap-1 ml-2"><span className="w-2.5 h-2.5 rounded-full bg-slate-400"></span> Not Run Yet</span>
              </div>
            </div>

            <div className="flex-1 w-full min-h-0 transition-transform duration-700 group-hover:scale-[1.005]">
              <ResponsiveContainer width="100%" height="100%">
                <ScatterChart margin={{ top: 20, right: 20, bottom: 10, left: -10 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#334155" opacity={0.15} />
                  
                  {/* Clean 0% Line */}
                  <ReferenceLine y={0} stroke="#10b981" strokeDasharray="3 3" opacity={0.5} />
                  {/* Not Run Holding Pen Line */}
                  <ReferenceLine y={-15} stroke="#64748b" strokeOpacity={0.3} />

                  <XAxis 
                    dataKey="date" 
                    type="category" 
                    allowDuplicatedCategory={true} 
                    axisLine={false} 
                    tickLine={false} 
                    tick={{ fontSize: 10, fill: '#64748b', fontWeight: 'bold' }} 
                    dy={10} 
                  />
                  <YAxis 
                    dataKey="errorRate" 
                    type="number" 
                    domain={[-20, 100]} 
                    axisLine={false} 
                    tickLine={false} 
                    tick={{ fontSize: 9, fill: '#64748b' }}
                    tickFormatter={(val) => {
                      if (val === -15) return "Not Run";
                      if (val < 0) return "";
                      return `${val}%`;
                    }}
                  />
                  <ZAxis type="number" range={[60, 150]} />
                  <RechartsTooltip cursor={{ strokeDasharray: '3 3', stroke: '#334155' }} content={<DeliveryRiskTooltip />} />
                  
                  <Scatter name="Deliveries" data={deliveryRiskData}>
                    {deliveryRiskData.map((entry: any, index: number) => {
                      let color = '#f59e0b'; // Failing (Yellow default)
                      if (entry.status === 'Clean') color = '#10b981'; // Clean (Green)
                      else if (entry.status === 'Not Run') color = '#64748b'; // Not Run (Grey)
                      else if (entry.errorRate > 20) color = '#f43f5e'; // High Fail (Red)

                      return (
                        <Cell key={`cell-${index}`} fill={color} fillOpacity={0.8} stroke="#ffffff" strokeWidth={1} />
                      );
                    })}
                  </Scatter>
                </ScatterChart>
              </ResponsiveContainer>
            </div>
          </div>

         
        </div>
      )}

      {/* ORIGINAL DB DATA TABLE */}
      <div className="bg-white dark:bg-[#111623] border border-slate-200 dark:border-slate-800/60 rounded-xl shadow-sm overflow-hidden flex-1 flex flex-col min-h-[400px] animate-in slide-in-from-bottom-10 fade-in duration-700 fill-mode-both" style={{ animationDelay: '900ms' }}>
        

        <div className="overflow-x-auto custom-scrollbar flex-1">
          <table className="w-full text-left border-collapse min-w-[1100px]">
            <thead>
              <tr className="bg-slate-50/50 dark:bg-[#0B0F1A]/50 border-b border-slate-200 dark:border-slate-800/60 text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400">
                <th className="px-5 py-3 font-black">Rosco ID</th>
                <th className="px-5 py-3 font-black">Project Name</th>
                <th className="px-5 py-3 font-black">Runs</th>
                <th className="px-5 py-3 font-black">Latest Status</th>
                <th className="px-5 py-3 font-black">Trend (Gained / Lost)</th>
                <th className="px-5 py-3 font-black text-right">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
              {filteredData.length === 0 ? (
                <tr><td colSpan={6} className="px-5 py-10 text-center text-slate-400 text-xs font-medium">No records found matching your filters.</td></tr>
              ) : (
                filteredData.map((group: any, idx: number) => {
                  const activeLines = activeChartLines[group.id] || ['Total Errors'];
                  
                  const trendData = group.allRuns.map((r: any, i: number) => {
                    const dp: any = { name: `Run ${i + 1}`, 'Total Errors': r.error_count || 0 };
                    group.allFailedRules.forEach((rule: string) => {
                      const rawRuleKey = Object.keys(r.qc_summary || {}).find(k => formatCheckName(k) === rule);
                      dp[rule] = rawRuleKey && r.qc_summary[rawRuleKey] ? r.qc_summary[rawRuleKey].Failed : 0;
                    });
                    return dp;
                  });

                  return (
                    <React.Fragment key={group.id}>
                      {/* MASTER ROW FOR THE ROSCO ID */}
                      <tr 
                        onClick={() => toggleGroup(group.id)} 
                        className={`hover:bg-slate-50 dark:hover:bg-white/[0.02] transition-colors cursor-pointer animate-in fade-in fill-mode-both ${expandedGroups[group.id] ? 'bg-slate-50 dark:bg-slate-800/20' : ''}`} 
                        style={{ animationDelay: `${Math.min(idx * 30, 500)}ms` }}
                      >
                        <td className="px-5 py-4"><div className="flex items-center gap-2 text-sm font-black dark:text-white"><Hash size={14} className="text-slate-400" /> {group.id}</div></td>
                        <td className="px-5 py-4"><div className="flex items-center gap-2 text-xs font-medium dark:text-slate-200"><FolderGit2 size={12} className="text-blue-500" /> {group.project_name || "Unknown"}</div></td>
                        <td className="px-5 py-4"><span className="text-xs font-bold text-slate-500 dark:text-slate-400">{group.totalRuns} Run{group.totalRuns > 1 ? 's' : ''}</span></td>
                        <td className="px-5 py-4">
                          {group.latestRun.error_count === 0 ? (
                            <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10 border border-emerald-200"><CheckCircle2 size={10} /> Clean</span>
                          ) : (
                            <span className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-[10px] font-bold border ${group.latestRun._computedErrorRate > 25 ? 'bg-rose-50 text-rose-600 border-rose-200' : 'bg-amber-50 text-amber-600 border-amber-200'}`}>
                              <Target size={10} /> {group.latestRun._computedErrorRate.toFixed(1)}% Fail
                            </span>
                          )}
                        </td>
                        <td className="px-5 py-4">
                          <div className="flex flex-col gap-1">
                            {group.totalRuns === 1 ? (
                              <span className="text-[10px] text-slate-400 italic">No previous runs</span>
                            ) : (
                              <>
                                {group.overallFixed.length > 0 && <span className="text-[10px] font-bold text-emerald-500 flex items-center gap-1"><TrendingDown size={12}/> Gained: {group.overallFixed.join(', ')}</span>}
                                {group.overallBroken.length > 0 && <span className="text-[10px] font-bold text-rose-500 flex items-center gap-1"><TrendingUp size={12}/> Lost: {group.overallBroken.join(', ')}</span>}
                                {group.overallFixed.length === 0 && group.overallBroken.length === 0 && <span className="text-[10px] text-slate-400">No change in failing rules</span>}
                              </>
                            )}
                          </div>
                        </td>
                        <td className="px-5 py-4 text-right">
                          <ChevronRight size={18} className={`inline text-slate-400 transition-transform duration-300 ${expandedGroups[group.id] ? 'rotate-90' : ''}`} />
                        </td>
                      </tr>

                      {/* EXPANDED HISTORY ROWS, CHART & MATRIX */}
                      {expandedGroups[group.id] && (
                        <tr className="bg-slate-50/50 dark:bg-[#0B0F1A]/80 shadow-inner">
                          <td colSpan={6} className="p-0 border-b border-slate-200 dark:border-slate-800">
                            <div className="py-6 px-4 sm:px-8 border-l-4 border-blue-500 ml-5 my-2">
                              
                              <h4 className="text-[10px] font-black uppercase text-slate-400 mb-4 flex items-center gap-2">
                                <Activity size={12}/> Sequential Audit Trail: {group.id}
                              </h4>
                              
                              {/* Individual Run Cards */}
                              <div className="flex flex-col gap-2 min-w-[700px] mb-8">
                                {group.allRuns.map((run: any, rIdx: number) => (
                                  <div key={run.id} onClick={(e) => { e.stopPropagation(); setSelectedRecord(run); }} className="flex items-center p-3 bg-white dark:bg-[#111623] border border-slate-200 dark:border-slate-700/60 rounded-lg hover:border-blue-500/50 cursor-pointer group/row transition-all gap-4">
                                    
                                    <div className="flex items-center gap-2 w-20 shrink-0">
                                      <span className="text-[10px] font-black uppercase tracking-widest text-slate-400 bg-slate-100 dark:bg-slate-800 px-2 py-1 rounded">Run {rIdx + 1}</span>
                                    </div>
                                    <div className="text-xs text-slate-600 dark:text-slate-300 w-32 shrink-0 flex items-center gap-1.5"><CalendarDays size={12}/> {new Date(run.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'})}</div>
                                    
                                    <div className="w-24 shrink-0">
                                      {run.error_count > 0 ? (
                                        <span className="text-xs font-bold text-rose-500 flex items-center gap-1"><AlertCircle size={12}/> {run.error_count} Errors</span>
                                      ) : (
                                        <span className="text-xs font-bold text-emerald-500 flex items-center gap-1"><CheckCircle2 size={12}/> Clean</span>
                                      )}
                                    </div>

                                    <div className="flex-1 border-l border-slate-200 dark:border-slate-700 pl-4 flex flex-col justify-center min-h-[32px]">
                                      {rIdx === 0 ? (
                                        <span className="text-[10px] text-slate-400 italic">Initial baseline run.</span>
                                      ) : (
                                        <div className="flex flex-col gap-0.5">
                                          <div className="flex items-center gap-2 text-[10px] font-bold">
                                            <span className="text-slate-500 uppercase tracking-widest text-[9px]">Delta:</span>
                                            {run.errorDelta > 0 ? <span className="text-rose-500">+{run.errorDelta} Errors</span> : run.errorDelta < 0 ? <span className="text-emerald-500">{run.errorDelta} Errors</span> : <span className="text-slate-400">No Change in Volume</span>}
                                          </div>
                                          
                                          {(run.stepFixed.length > 0 || run.stepBroken.length > 0) && (
                                            <div className="flex flex-wrap gap-x-4 gap-y-1 mt-1">
                                              {run.stepFixed.length > 0 && <span className="text-[10px] text-emerald-600 dark:text-emerald-400 flex items-center gap-1 leading-tight"><TrendingDown size={10}/> <span className="font-semibold">Fixed:</span> {run.stepFixed.join(', ')}</span>}
                                              {run.stepBroken.length > 0 && <span className="text-[10px] text-rose-600 dark:text-rose-400 flex items-center gap-1 leading-tight"><TrendingUp size={10}/> <span className="font-semibold">Broke:</span> {run.stepBroken.join(', ')}</span>}
                                            </div>
                                          )}
                                        </div>
                                      )}
                                    </div>

                                    <div className="w-8 shrink-0 text-right">
                                      <BarChart3 size={14} className="text-blue-500 opacity-0 group-hover/row:opacity-100 transition-opacity ml-auto"/>
                                    </div>
                                  </div>
                                ))}
                              </div>

                              {group.totalRuns > 1 && (
                                <div className="mb-8 animate-in fade-in slide-in-from-bottom-2 duration-500">
                                  <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-3 mb-4">
                                    <h4 className="text-[10px] font-black uppercase text-slate-400 flex items-center gap-2 shrink-0">
                                      <LineChartIcon size={12}/> Error Volume Trend
                                    </h4>
                                    
                                    <div className="flex flex-wrap gap-1.5 items-center">
                                      <button 
                                        onClick={() => toggleChartLine(group.id, 'Total Errors')}
                                        className={`px-2 py-1 text-[9px] font-bold rounded-md border transition-all ${activeLines.includes('Total Errors') ? 'bg-rose-50 border-rose-500 text-rose-600 dark:bg-rose-500/20 dark:text-rose-400' : 'bg-transparent border-slate-200 text-slate-400 dark:border-slate-700'}`}
                                      >
                                        Total Errors
                                      </button>
                                      {group.allFailedRules.map((rule: string, idx: number) => {
                                        const isActive = activeLines.includes(rule);
                                        const color = CHART_COLORS[idx % CHART_COLORS.length];
                                        return (
                                          <button 
                                            key={rule}
                                            onClick={() => toggleChartLine(group.id, rule)}
                                            className={`px-2 py-1 text-[9px] font-bold rounded-md border transition-all`}
                                            style={isActive ? { backgroundColor: `${color}20`, borderColor: color, color: color } : { borderColor: 'transparent' }}
                                          >
                                            <span className={!isActive ? 'text-slate-400' : ''}>{rule}</span>
                                          </button>
                                        );
                                      })}
                                    </div>
                                  </div>

                                  <div className="h-64 w-full bg-white dark:bg-[#111623] border border-slate-200 dark:border-slate-700/60 rounded-xl p-4 shadow-sm">
                                    <ResponsiveContainer width="100%" height="100%">
                                      <LineChart data={trendData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#334155" opacity={0.2} />
                                        <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 9, fill: '#64748b' }} dy={10} />
                                        <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 9, fill: '#64748b' }} />
                                        <RechartsTooltip 
                                          cursor={{ stroke: '#334155', strokeWidth: 1, strokeDasharray: '3 3' }}
                                          contentStyle={{ backgroundColor: '#111623', border: '1px solid #1e293b', borderRadius: '8px', color: '#fff', fontSize: '10px', fontWeight: 'bold' }}
                                        />
                                        
                                        {activeLines.includes('Total Errors') && (
                                          <Line type="monotone" dataKey="Total Errors" stroke="#f43f5e" strokeWidth={3} dot={{ r: 4, fill: '#f43f5e', strokeWidth: 2, stroke: '#fff' }} activeDot={{ r: 6 }} />
                                        )}
                                        
                                        {group.allFailedRules.map((rule: string, idx: number) => {
                                          if (!activeLines.includes(rule)) return null;
                                          const color = CHART_COLORS[idx % CHART_COLORS.length];
                                          return (
                                            <Line key={rule} type="monotone" dataKey={rule} stroke={color} strokeWidth={2} dot={{ r: 3, fill: color, strokeWidth: 1, stroke: '#fff' }} activeDot={{ r: 5 }} />
                                          );
                                        })}
                                      </LineChart>
                                    </ResponsiveContainer>
                                  </div>
                                </div>
                              )}

                              {group.allFailedRules.length > 0 && group.totalRuns > 1 && (
                                <div className="animate-in fade-in slide-in-from-bottom-2 duration-500">
                                  <h4 className="text-[10px] font-black uppercase text-slate-400 mb-3 flex items-center gap-2">
                                    <Layers size={12}/> Rule Progression Matrix
                                  </h4>
                                  <div className="border border-slate-200 dark:border-slate-700/60 rounded-xl overflow-hidden bg-white dark:bg-[#111623] shadow-sm">
                                    <div className="overflow-x-auto">
                                      <table className="w-full text-left text-xs whitespace-nowrap">
                                        <thead className="bg-slate-50 dark:bg-slate-800/40 border-b border-slate-200 dark:border-slate-700/60">
                                          <tr>
                                            <th className="px-4 py-3 font-bold text-slate-500 uppercase tracking-widest text-[9px] w-64">QC Rule</th>
                                            {group.allRuns.map((r: any, i: number) => (
                                              <th key={i} className="px-4 py-3 font-bold text-slate-500 text-center border-l border-slate-200 dark:border-slate-700/60 uppercase tracking-widest text-[9px] w-20">
                                                R{i + 1}
                                              </th>
                                            ))}
                                          </tr>
                                        </thead>
                                        <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
                                          {group.allFailedRules.map((rule: string) => (
                                            <tr key={rule} className="hover:bg-slate-50 dark:hover:bg-slate-800/20 transition-colors">
                                              <td className="px-4 py-3 font-bold text-slate-700 dark:text-slate-300 truncate" title={rule}>{rule}</td>
                                              {group.allRuns.map((r: any, i: number) => {
                                                const rawRuleKey = Object.keys(r.qc_summary || {}).find(k => formatCheckName(k) === rule);
                                                const fails = rawRuleKey && r.qc_summary[rawRuleKey] ? r.qc_summary[rawRuleKey].Failed : 0;
                                                
                                                return (
                                                  <td key={i} className="px-4 py-3 text-center border-l border-slate-100 dark:border-slate-800/60">
                                                    {fails > 0 ? (
                                                      <span className="inline-flex justify-center items-center font-black text-[10px] text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-500/10 px-2 py-1 rounded w-8">
                                                        {fails}
                                                      </span>
                                                    ) : (
                                                      <span className="inline-flex justify-center items-center w-8 text-emerald-500">
                                                        <CheckCircle2 size={14} />
                                                      </span>
                                                    )}
                                                  </td>
                                                );
                                              })}
                                            </tr>
                                          ))}
                                        </tbody>
                                      </table>
                                    </div>
                                  </div>
                                </div>
                              )}

                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default QcHistoryDashboard;