import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { DemoBanner } from "../components/DemoBanner";
import { useWebSocket } from "../hooks/useWebSocket";
import {
  BACKUP_DOWNLOAD_PATH,
  api,
  getAdminPin,
} from "../services/api";
import type { AdminSummary, AuditEntry, DeviceInfo } from "../types";

const DISPLAY_MODES = [
  ["LATEST", "Latest Winners"],
  ["ALL", "All Winners"],
  ["UNCLAIMED", "Unclaimed Only"],
  ["SESSION_1", "Session 1"],
  ["SESSION_2", "Session 2"],
  ["ANNOUNCEMENT", "Announcement"],
] as const;

function Card({ label, value, accent }: { label: string; value: React.ReactNode; accent?: string }) {
  return (
    <div className="card text-center">
      <div className="text-lg text-slate-500">{label}</div>
      <div className={`text-5xl font-black ${accent || ""}`}>{value}</div>
    </div>
  );
}

export function AdminDashboard() {
  const [summary, setSummary] = useState<AdminSummary | null>(null);
  const [devices, setDevices] = useState<DeviceInfo[]>([]);
  const [audit, setAudit] = useState<AuditEntry[]>([]);
  const [announcement, setAnnouncement] = useState("");
  const [msg, setMsg] = useState("");

  const load = useCallback(async () => {
    const s = await api.summary();
    setSummary(s);
    setAnnouncement(s.announcement_text || "");
    api.devices().then(setDevices).catch(() => {});
    api.audit(30).then(setAudit).catch(() => {});
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(() => {
      api.devices().then(setDevices).catch(() => {});
    }, 8000);
    return () => clearInterval(id);
  }, [load]);

  useWebSocket({
    deviceName: "Admin Dashboard",
    role: "admin",
    onEvent: () => load(),
  });

  const act = async (fn: () => Promise<unknown>, note: string) => {
    try {
      await fn();
      setMsg(note);
      await load();
    } catch (e) {
      setMsg((e as Error).message);
    }
  };

  const setDisplay = (mode: string) =>
    act(
      () => api.setDisplay(mode, mode === "ANNOUNCEMENT" ? announcement : undefined),
      `Display set to ${mode}.`
    );

  const downloadBackup = async () => {
    const res = await fetch(BACKUP_DOWNLOAD_PATH, {
      headers: { "X-Admin-Pin": getAdminPin() },
    });
    if (!res.ok) {
      setMsg("Backup download failed.");
      return;
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "raffle-backup.db";
    a.click();
    URL.revokeObjectURL(url);
  };

  if (!summary) return <div className="p-8 text-2xl">Loading…</div>;

  return (
    <div className="min-h-screen">
      <DemoBanner />
      <div className="mx-auto max-w-6xl p-4 sm:p-6">
        <div className="flex flex-wrap gap-3 items-center justify-between mb-6">
          <h1 className="text-4xl font-black">Admin Dashboard</h1>
          <div className="flex flex-wrap gap-2">
            <Link to="/admin/prizes" className="btn-neutral text-lg py-2 px-4">
              Prizes
            </Link>
            <Link to="/admin/reports" className="btn-neutral text-lg py-2 px-4">
              Reports
            </Link>
            <Link to="/admin/setup" className="btn-neutral text-lg py-2 px-4">
              Setup
            </Link>
            <Link to="/admin/demo" className="btn-neutral text-lg py-2 px-4">
              Demo
            </Link>
          </div>
        </div>

        {msg && (
          <div className="mb-4 rounded-xl bg-blue-100 text-blue-900 px-4 py-2 font-semibold">
            {msg}
          </div>
        )}

        {/* Summary cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <Card label="Tickets Sold" value={summary.tickets_sold} />
          <Card label="Buyers" value={summary.buyers} />
          <Card label="Prizes" value={summary.prizes} />
          <Card label="Prizes Drawn" value={summary.prizes_drawn} />
          <Card label="Claimed" value={summary.claimed} accent="text-green-700" />
          <Card
            label="Unclaimed"
            value={summary.unclaimed}
            accent="text-orange-600"
          />
          <Card label="Current Session" value={summary.current_session} />
          <Card
            label="Sales Status"
            value={summary.sales_open ? "OPEN" : "CLOSED"}
            accent={summary.sales_open ? "text-green-700" : "text-red-600"}
          />
        </div>

        {/* Sales control */}
        <div className="card mb-6">
          <h2 className="text-2xl font-black mb-3">Ticket Sales</h2>
          <div className="grid grid-cols-2 gap-4">
            <button
              className="btn-success"
              onClick={() => act(api.openSales, "Sales opened.")}
              disabled={summary.sales_open}
            >
              OPEN SALES
            </button>
            <button
              className="btn-danger"
              onClick={() => act(api.closeSales, "Sales closed.")}
              disabled={!summary.sales_open}
            >
              CLOSE SALES
            </button>
          </div>
        </div>

        {/* Sessions */}
        <div className="card mb-6">
          <h2 className="text-2xl font-black mb-3">Sessions</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <button className="btn-primary" onClick={() => act(() => api.startSession(1), "Session 1 started.")}>
              START SESSION 1
            </button>
            <button className="btn-neutral" onClick={() => act(() => api.endSession(1), "Session 1 ended.")}>
              END SESSION 1
            </button>
            <button className="btn-primary" onClick={() => act(() => api.startSession(2), "Session 2 started.")}>
              START SESSION 2
            </button>
            <button className="btn-neutral" onClick={() => act(() => api.endSession(2), "Session 2 ended.")}>
              END SESSION 2
            </button>
          </div>
        </div>

        {/* Display control */}
        <div className="card mb-6">
          <h2 className="text-2xl font-black mb-3">Public TV Display</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-4">
            {DISPLAY_MODES.map(([mode, label]) => (
              <button
                key={mode}
                className={summary.display_mode === mode ? "btn-primary" : "btn-neutral"}
                onClick={() => setDisplay(mode)}
              >
                {label}
              </button>
            ))}
          </div>
          <label className="label" htmlFor="announcement">
            Announcement text (for Announcement mode)
          </label>
          <textarea
            id="announcement"
            className="input-lg text-2xl"
            rows={2}
            value={announcement}
            onChange={(e) => setAnnouncement(e.target.value)}
          />
        </div>

        {/* Backup */}
        <div className="card mb-6">
          <h2 className="text-2xl font-black mb-3">Backup & Export</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <button className="btn-primary" onClick={downloadBackup}>
              DOWNLOAD BACKUP
            </button>
            <button
              className="btn-neutral"
              onClick={() => act(api.createBackup, "Backup created on server.")}
            >
              CREATE SERVER BACKUP
            </button>
            <Link to="/admin/reports" className="btn-neutral text-center">
              EXPORT RESULTS
            </Link>
          </div>
        </div>

        {/* Devices */}
        <div className="card mb-6">
          <h2 className="text-2xl font-black mb-3">Device Status</h2>
          {devices.length === 0 ? (
            <p className="text-slate-500">No devices connected.</p>
          ) : (
            <ul className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {devices.map((d, i) => (
                <li
                  key={i}
                  className="flex justify-between items-center border-b border-slate-100 py-2"
                >
                  <span className="font-semibold">
                    {d.name}{" "}
                    <span className="text-slate-400 text-sm">({d.role})</span>
                  </span>
                  <span className="text-green-600 font-black">● ONLINE</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Audit log */}
        <div className="card">
          <h2 className="text-2xl font-black mb-3">Recent Activity (Audit Log)</h2>
          <ul className="text-sm space-y-1 max-h-72 overflow-y-auto">
            {audit.map((a) => (
              <li key={a.id} className="border-b border-slate-100 py-1">
                <span className="text-slate-400">
                  {new Date(a.created_at).toLocaleTimeString()}
                </span>{" "}
                <b>{a.action}</b> {a.details}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
