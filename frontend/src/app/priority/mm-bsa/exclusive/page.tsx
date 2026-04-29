"use client";

import { useState } from "react";
import { UploadCloud, Loader, Download } from "lucide-react";
import { useRunMmBsaQcMutation } from "@/state/api";

const QC_CHECKS = [
  { id: "duplicate_aid_final", title: "Duplicate AID Check" },
  { id: "audience_spotprice_check", title: "Audience & Spot Price Check" },
  { id: "program_category_check_mm", title: "Program Category Check" },
  { id: "channel_country_mapping_check", title: "Channel & Country Mapping" },
  { id: "apt_bt_check", title: "APT / BT Check" },
  { id: "season_monitoring_check", title: "Season Monitoring Check" },
  { id: "fixture_validation_check", title: "Event / Matchday Validation Check" },
  { id: "stadium_consistency_check", title: "Stadium Consistency Check" },
  { id: "event_quality_check", title: "Event Quality Check" },
  { id: "home_market_check", title: "Home Market Check" },
  { id: "ps_market_channel_check", title: "PS Market & Channel Check" },
  { id: "ps_content_check", title: "PS Content Check" },
  { id: "mm_bsr_consistency_check", title: "MM vs BSR Consistency Check" },
  { id: "audience_spot_range_clean_view", title: "Audience Range Check" },
  { id: "ea_creation_check", title: "EA Creation Check" },
  { id: "previous_delivery_check", title: "Previous Delivery Check" },
  { id: "live_delayed_check", title: "Live vs Delayed Check" },
  { id: "program_analysis_status_check", title: "Program Status Check" },
];

export default function Page() {
  const [dpmmFile, setDpmmFile] = useState<File | null>(null);
  const [roscoFile, setRoscoFile] = useState<File | null>(null);
  const [fixtureFile, setFixtureFile] = useState<File | null>(null);
  const [prevFile, setPrevFile] = useState<File | null>(null);
  const [bsrFile, setBsrFile] = useState<File | null>(null);

  const [selectedChecks, setSelectedChecks] = useState<string[]>([]);
  const [btThreshold, setBtThreshold] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);

  const [runMmBsaQc, { isLoading }] = useRunMmBsaQcMutation();

  const allSelected = selectedChecks.length === QC_CHECKS.length;

  const toggleCheck = (id: string) => {
    setSelectedChecks((prev) =>
      prev.includes(id)
        ? prev.filter((c) => c !== id)
        : [...prev, id]
    );
  };

  const toggleSelectAll = () => {
    setSelectedChecks(allSelected ? [] : QC_CHECKS.map((c) => c.id));
  };

  const runChecks = async () => {
    if (!dpmmFile) return alert("Upload DPMM file");
    if (selectedChecks.length === 0) return alert("Select at least one check");

    const formData = new FormData();
    formData.append("adapt_file", dpmmFile); // same backend param
    formData.append("selected_checks", JSON.stringify(selectedChecks));

    if (roscoFile) formData.append("rosco_file", roscoFile);
    if (fixtureFile) formData.append("fixture_file", fixtureFile);
    if (prevFile) formData.append("previous_delivery_file", prevFile);
    if (bsrFile) formData.append("bsr_file", bsrFile);

    if (btThreshold) formData.append("bt_threshold", btThreshold);
    if (startDate) formData.append("start_date", startDate);
    if (endDate) formData.append("end_date", endDate);

    try {
      const blob = await runMmBsaQc(formData).unwrap();
      const url = window.URL.createObjectURL(blob);
      setDownloadUrl(url);
    } catch (err: any) {
      alert(err?.data?.detail || "Something failed");
    }
  };

  const ready = dpmmFile;


  return (
    <div className="p-6 w-full min-h-screen bg-white dark:bg-slate-950 text-slate-800 dark:text-slate-200">

      <h1 className="text-xl font-semibold mb-6">
        OPS MM Exclusive Checks
      </h1>

      <div className="grid grid-cols-3 gap-6">

        {/* LEFT */}
        <div className="col-span-2 flex flex-col gap-6">

          {/* FILE UPLOAD */}
          <div className="grid grid-cols-5 gap-4">
            {[
              { label: "📂 DPMM File", file: dpmmFile, set: setDpmmFile },
              { label: "📑 ROSCO File", file: roscoFile, set: setRoscoFile },
              { label: "📋 Fixture File", file: fixtureFile, set: setFixtureFile },
              { label: "📋 Previous Delivery", file: prevFile, set: setPrevFile },
              { label: "📋 BSR File", file: bsrFile, set: setBsrFile },
            ].map((item, i) => (
              <label
                key={i}
                className={`border rounded-xl p-3 text-center cursor-pointer transition
                ${item.file
                    ? "border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20"
                    : "border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 hover:border-blue-500 hover:shadow-sm"
                  }`}
              >
                <input
                  type="file"
                  className="hidden"
                  onChange={(e) => item.set(e.target.files?.[0] || null)}
                />

                <div className="flex flex-col items-center gap-2">
                  <UploadCloud size={18} className="text-slate-400" />
                  <p className="text-xs font-medium">{item.label}</p>

                  {item.file && (
                    <>
                      <p className="text-[10px] text-emerald-600 truncate max-w-full">
                        {item.file.name}
                      </p>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.preventDefault();
                          item.set(null);
                        }}
                        className="text-[10px] text-red-500"
                      >
                        Remove
                      </button>
                    </>
                  )}
                </div>
              </label>
            ))}
          </div>

          {/* CHECKS */}
          <div className="rounded-2xl p-5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 shadow-sm">

            <h3 className="text-sm font-semibold mb-4">
              Validation Rules
            </h3>

            <label className="flex items-center gap-2 mb-3 text-sm">
              <input
                type="checkbox"
                className="accent-blue-600"
                checked={allSelected}
                onChange={toggleSelectAll}
              />
              Select All
            </label>

            <div className="grid grid-cols-2 gap-2 max-h-72 overflow-y-auto">
              {QC_CHECKS.map((c) => (
                <label
                  key={c.id}
                  className="flex items-center gap-2 text-sm px-2 py-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800"
                >
                  <input
                    type="checkbox"
                    className="accent-blue-600"
                    checked={selectedChecks.includes(c.id)}
                    onChange={() => toggleCheck(c.id)}
                  />
                  {c.title}
                </label>
              ))}
            </div>
          </div>

          {/* MONITORING */}
          <div className="rounded-2xl p-5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700">

            <h3 className="text-sm font-semibold mb-4">
              Monitoring
            </h3>

            <div className="flex gap-3 mb-3">
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-full border rounded-lg px-3 py-2 text-sm bg-white dark:bg-slate-800"
              />
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="w-full border rounded-lg px-3 py-2 text-sm bg-white dark:bg-slate-800"
              />
            </div>

            <input
              type="number"
              placeholder="BT Threshold"
              value={btThreshold}
              onChange={(e) => setBtThreshold(e.target.value)}
              className="w-full border rounded-lg px-3 py-2 text-sm bg-white dark:bg-slate-800"
            />
          </div>
        </div>

        {/* RIGHT */}
        <div className="rounded-2xl p-6 flex flex-col gap-4 justify-center bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 shadow-sm">

          <button
            onClick={runChecks}
            disabled={!ready || isLoading}
            className="w-full py-3 rounded-xl font-semibold text-white bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 shadow-md flex items-center justify-center gap-2"
          >
            {isLoading ? <Loader className="animate-spin" size={16} /> : <UploadCloud size={16} />}
            {isLoading ? "Running..." : "Run OPS Checks"}
          </button>

          {downloadUrl && (
            <button
              onClick={() => {
                const a = document.createElement("a");
                a.href = downloadUrl;
                a.download = "OPS_Output.xlsx";
                a.click();
              }}
              className="w-full py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg flex justify-center gap-2"
            >
              <Download size={14} /> Download Output
            </button>
          )}
        </div>
      </div>
    </div>
  );
}