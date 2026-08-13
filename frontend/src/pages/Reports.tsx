import { useState } from "react";
import { Link } from "react-router-dom";

import { DemoBanner } from "../components/DemoBanner";
import { ApiError, api, reportUrl } from "../services/api";

const REPORTS = [
  ["ticket-sales", "All Ticket Sales"],
  ["buyers", "Buyers"],
  ["winners", "Winners"],
  ["prizes", "Prizes"],
  ["claimed", "Claimed Prizes"],
  ["unclaimed", "Unclaimed Prizes"],
  ["drawing-history", "Drawing History"],
  ["session-summary", "Session Summary"],
] as const;

export function Reports() {
  const [csv, setCsv] = useState("");
  const [msg, setMsg] = useState("");

  const importTickets = async () => {
    setMsg("");
    try {
      const res = await api.importTicketsRaw(csv);
      setMsg(`Imported ${res.created} tickets (${res.skipped} skipped).`);
      setCsv("");
    } catch (e) {
      setMsg((e as ApiError).message);
    }
  };

  return (
    <div className="min-h-screen">
      <DemoBanner />
      <div className="mx-auto max-w-4xl p-4 sm:p-6">
        <Link to="/admin" className="text-slate-500 underline">
          ← Admin
        </Link>
        <h1 className="text-4xl font-black my-6">Reporting / Export</h1>

        <div className="card mb-6">
          <h2 className="text-2xl font-black mb-3">Download CSV Reports</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {REPORTS.map(([key, label]) => (
              <a
                key={key}
                className="btn-primary text-center"
                href={reportUrl(key)}
                target="_blank"
                rel="noreferrer"
              >
                {label}
              </a>
            ))}
          </div>
        </div>

        <div className="card">
          <h2 className="text-2xl font-black mb-3">Import Tickets (fallback)</h2>
          <p className="text-slate-500 mb-2">
            Columns: <code>ticket_number,first_name,last_name</code>
          </p>
          <textarea
            className="input-lg text-lg font-mono"
            rows={4}
            placeholder={"ticket_number,first_name,last_name\n005001,Mary,Jones"}
            value={csv}
            onChange={(e) => setCsv(e.target.value)}
          />
          <input
            type="file"
            accept=".csv,text/csv"
            className="mt-3"
            onChange={async (e) => {
              const file = e.target.files?.[0];
              if (file) setCsv(await file.text());
            }}
          />
          <button
            className="btn-primary w-full mt-3"
            onClick={importTickets}
            disabled={!csv.trim()}
          >
            IMPORT TICKETS
          </button>
          {msg && <p className="mt-3 font-semibold">{msg}</p>}
        </div>
      </div>
    </div>
  );
}
