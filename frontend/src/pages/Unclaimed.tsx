import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { DemoBanner } from "../components/DemoBanner";
import { useWebSocket } from "../hooks/useWebSocket";
import { api, getAdminPin, setAdminPin } from "../services/api";
import type { PrizeView } from "../types";

export function Unclaimed() {
  const [rows, setRows] = useState<PrizeView[]>([]);
  const [msg, setMsg] = useState("");

  const load = useCallback(async () => {
    setRows(await api.unclaimed());
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useWebSocket({
    role: "unclaimed",
    onEvent: (m) => {
      if (["winner.created", "prize.claimed", "winner.redrawn"].includes(m.event))
        load();
    },
  });

  const showOnTvs = async () => {
    if (!getAdminPin()) {
      const pin = window.prompt("Enter Admin PIN:");
      if (!pin) return;
      setAdminPin(pin);
    }
    try {
      await api.setDisplay("UNCLAIMED");
      setMsg("TVs now showing Unclaimed Winners.");
    } catch {
      setMsg("Could not update TVs (check admin PIN).");
    }
  };

  return (
    <div className="min-h-screen">
      <DemoBanner />
      <div className="mx-auto max-w-5xl p-4 sm:p-6">
        <div className="flex justify-between mb-4">
          <Link to="/" className="text-slate-500 underline">
            Home
          </Link>
          <button className="btn-primary" onClick={showOnTvs}>
            SHOW UNCLAIMED ON TVs
          </button>
        </div>
        <h1 className="text-4xl font-black mb-2">Unclaimed Prizes</h1>
        {msg && <p className="text-green-700 font-semibold mb-4">{msg}</p>}

        <div className="card overflow-x-auto">
          <table className="w-full text-left text-lg">
            <thead>
              <tr className="border-b-2 border-slate-200 text-slate-500">
                <th className="py-3 pr-4">Prize #</th>
                <th className="py-3 pr-4">Prize Name</th>
                <th className="py-3 pr-4">Winner</th>
                <th className="py-3 pr-4">Ticket #</th>
                <th className="py-3 pr-4">Pickup</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} className="border-b border-slate-100">
                  <td className="py-3 pr-4 font-bold">#{r.prize_number}</td>
                  <td className="py-3 pr-4">{r.name}</td>
                  <td className="py-3 pr-4 font-semibold">{r.winner_name}</td>
                  <td className="py-3 pr-4">{r.winning_ticket}</td>
                  <td className="py-3 pr-4">{r.pickup_station || "—"}</td>
                </tr>
              ))}
              {rows.length === 0 && (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-slate-400 text-2xl">
                    All prizes claimed 🎉
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
