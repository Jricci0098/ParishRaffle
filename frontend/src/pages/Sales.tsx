import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { Confirm } from "../components/Confirm";
import { DemoBanner } from "../components/DemoBanner";
import { useWebSocket } from "../hooks/useWebSocket";
import { ApiError, api, getAdminPin, setAdminPin } from "../services/api";
import type { SaleResult, Station } from "../types";

const STATION_KEY = "raffle_station_id";
const QUICK = [1, 5, 10, 20];

export function Sales() {
  const [stations, setStations] = useState<Station[]>([]);
  const [station, setStation] = useState<Station | null>(null);
  const [salesOpen, setSalesOpen] = useState(true);
  const [first, setFirst] = useState("");
  const [last, setLast] = useState("");
  const [qty, setQty] = useState(1);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<SaleResult | null>(null);
  const [showUndo, setShowUndo] = useState(false);
  const firstRef = useRef<HTMLInputElement>(null);
  const resetTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const loadStation = useCallback(async (id: number) => {
    try {
      const s = await api.station(id);
      setStation(s);
    } catch {
      /* station removed */
    }
  }, []);

  const refreshStatus = useCallback(async () => {
    const s = await api.salesStatus();
    setSalesOpen(s.sales_open);
  }, []);

  useEffect(() => {
    api.stations().then(setStations).catch(() => setStations([]));
    refreshStatus();
    const saved = localStorage.getItem(STATION_KEY);
    if (saved) loadStation(Number(saved));
  }, [loadStation, refreshStatus]);

  useWebSocket({
    deviceName: station ? station.name : "Sales (unassigned)",
    role: "sales",
    onEvent: (msg) => {
      if (msg.event === "sales.closed") setSalesOpen(false);
      if (msg.event === "sales.opened") setSalesOpen(true);
      if (
        msg.event === "sale.created" &&
        station &&
        msg.data.station_id === station.id
      ) {
        loadStation(station.id);
      }
    },
  });

  const chooseStation = (s: Station) => {
    localStorage.setItem(STATION_KEY, String(s.id));
    setStation(s);
  };

  const resetForm = () => {
    setFirst("");
    setLast("");
    setQty(1);
    setResult(null);
    setError("");
    firstRef.current?.focus();
  };

  const completeSale = async () => {
    if (!station) return;
    setBusy(true);
    setError("");
    try {
      const res = await api.createSale({
        station_id: station.id,
        first_name: first,
        last_name: last,
        quantity: qty,
        device: station.name,
      });
      setResult(res);
      await loadStation(station.id);
      // Auto-reset for the next customer.
      resetTimer.current = setTimeout(resetForm, 6000);
    } catch (e) {
      const err = e as ApiError;
      setError(err.message);
      if (err.code === "sales_closed") setSalesOpen(false);
    } finally {
      setBusy(false);
    }
  };

  const doUndo = async () => {
    if (!station) return;
    setShowUndo(false);
    // Undo requires the admin PIN.
    if (!getAdminPin()) {
      const pin = window.prompt("Enter Admin PIN to undo the last sale:");
      if (!pin) return;
      setAdminPin(pin);
    }
    try {
      await api.undoSale(station.id);
      await loadStation(station.id);
      setError("");
      alert("Last sale undone.");
    } catch (e) {
      setError((e as ApiError).message);
    }
  };

  useEffect(
    () => () => {
      if (resetTimer.current) clearTimeout(resetTimer.current);
    },
    []
  );

  // ----- Station not yet chosen -----
  if (!station) {
    return (
      <div className="min-h-screen">
        <DemoBanner />
        <div className="mx-auto max-w-2xl p-6">
          <h1 className="text-4xl font-black text-center my-8">
            Select This Station
          </h1>
          <div className="grid gap-4">
            {stations.map((s) => (
              <button
                key={s.id}
                className="btn-primary w-full py-8 text-3xl"
                onClick={() => chooseStation(s)}
                disabled={!s.active}
              >
                {s.name}
                <span className="ml-3 text-xl opacity-80">
                  {s.range_start_display}–{s.range_end_display}
                </span>
              </button>
            ))}
            {stations.length === 0 && (
              <p className="text-center text-slate-500 text-xl">
                No stations yet. Ask the administrator to set them up.
              </p>
            )}
          </div>
        </div>
      </div>
    );
  }

  // ----- Sales closed hard stop -----
  if (!salesOpen) {
    return (
      <div className="min-h-screen flex flex-col">
        <DemoBanner />
        <div className="flex-1 flex flex-col items-center justify-center bg-red-700 text-white text-center p-8">
          <div className="text-7xl mb-6">🛑</div>
          <h1 className="text-6xl font-black">
            RAFFLE TICKET SALES ARE CLOSED
          </h1>
          <p className="mt-6 text-2xl opacity-90">
            No additional sales may be recorded.
          </p>
          <button
            className="btn-neutral mt-10"
            onClick={() => {
              localStorage.removeItem(STATION_KEY);
              setStation(null);
            }}
          >
            Change Station
          </button>
        </div>
      </div>
    );
  }

  // ----- Sale confirmation -----
  if (result) {
    return (
      <div className="min-h-screen flex flex-col">
        <DemoBanner />
        <div className="flex-1 flex flex-col items-center justify-center bg-green-600 text-white text-center p-8">
          <h1 className="text-6xl font-black mb-8">SALE COMPLETE</h1>
          <p className="text-5xl font-bold mb-6">{result.buyer.display_name}</p>
          <p className="text-3xl opacity-90">Tickets</p>
          <p className="text-7xl font-black tracking-wider mt-2">
            {result.first_ticket}
            {result.quantity > 1 ? `–${result.last_ticket}` : ""}
          </p>
          <button className="btn-neutral mt-12 text-3xl px-12" onClick={resetForm}>
            NEXT CUSTOMER
          </button>
        </div>
      </div>
    );
  }

  const exhausted = station.exhausted;

  // ----- Sales form -----
  return (
    <div className="min-h-screen">
      <DemoBanner />
      <Confirm
        open={showUndo}
        title="Undo the last sale?"
        message="This removes the most recent tickets sold at this station. Requires admin."
        danger
        confirmLabel="Yes, undo"
        onConfirm={doUndo}
        onCancel={() => setShowUndo(false)}
      />
      <div className="mx-auto max-w-2xl p-4 sm:p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="text-sm text-slate-500">Station</div>
            <div className="text-2xl font-black">{station.name}</div>
          </div>
          <button
            className="text-sm text-slate-500 underline"
            onClick={() => {
              localStorage.removeItem(STATION_KEY);
              setStation(null);
            }}
          >
            Change
          </button>
        </div>

        <div className="card mb-4 text-center">
          <div className="text-lg text-slate-500">Next available ticket</div>
          <div
            className={`text-6xl font-black tracking-wider ${
              exhausted ? "text-red-600" : "text-blue-700"
            }`}
          >
            {exhausted ? "EXHAUSTED" : station.next_ticket_display}
          </div>
          {exhausted && (
            <p className="text-red-600 font-semibold mt-2">
              TICKET RANGE EXHAUSTED — contact the raffle administrator.
            </p>
          )}
        </div>

        <div className="card space-y-5">
          <div>
            <label className="label" htmlFor="first">
              Buyer First Name
            </label>
            <input
              id="first"
              ref={firstRef}
              className="input-lg"
              value={first}
              autoFocus
              onChange={(e) => setFirst(e.target.value)}
            />
          </div>
          <div>
            <label className="label" htmlFor="last">
              Buyer Last Name
            </label>
            <input
              id="last"
              className="input-lg"
              value={last}
              onChange={(e) => setLast(e.target.value)}
            />
          </div>
          <div>
            <label className="label">Ticket Quantity</label>
            <div className="grid grid-cols-4 gap-3 mb-3">
              {QUICK.map((q) => (
                <button
                  key={q}
                  className={
                    qty === q ? "btn-primary" : "btn-neutral"
                  }
                  onClick={() => setQty(q)}
                >
                  {q}
                </button>
              ))}
            </div>
            <input
              className="input-lg text-center"
              type="number"
              min={1}
              value={qty}
              onChange={(e) => setQty(Math.max(1, Number(e.target.value) || 1))}
              aria-label="Custom quantity"
            />
          </div>

          {error && (
            <p className="text-red-600 font-bold text-xl text-center">{error}</p>
          )}

          <button
            className="btn-success w-full py-8 text-4xl"
            onClick={completeSale}
            disabled={busy || exhausted}
          >
            {busy ? "Saving…" : "COMPLETE SALE"}
          </button>
          <button
            className="btn-danger w-full"
            onClick={() => setShowUndo(true)}
          >
            UNDO LAST SALE
          </button>
        </div>

        <div className="text-center mt-6">
          <Link to="/" className="text-slate-500 underline">
            Home
          </Link>
        </div>
      </div>
    </div>
  );
}
