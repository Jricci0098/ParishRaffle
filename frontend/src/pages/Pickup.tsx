import { useRef, useState } from "react";
import { Link } from "react-router-dom";

import { Confirm } from "../components/Confirm";
import { DemoBanner } from "../components/DemoBanner";
import { useWebSocket } from "../hooks/useWebSocket";
import { ApiError, api } from "../services/api";
import type { PrizeView } from "../types";

export function Pickup() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<PrizeView[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [confirmPrize, setConfirmPrize] = useState<PrizeView | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const search = async () => {
    setBusy(true);
    setError("");
    try {
      const res = await api.searchWinners(query.trim());
      setResults(res);
    } catch (e) {
      setError((e as ApiError).message);
    } finally {
      setBusy(false);
    }
  };

  useWebSocket({
    deviceName: "Prize Pickup",
    role: "pickup",
    onEvent: (msg) => {
      if (
        (msg.event === "prize.claimed" || msg.event === "winner.redrawn") &&
        results
      ) {
        search();
      }
    },
  });

  const doClaim = async () => {
    if (!confirmPrize) return;
    const prize = confirmPrize;
    setConfirmPrize(null);
    try {
      await api.claim(prize.id, "volunteer");
      await search();
    } catch (e) {
      setError((e as ApiError).message);
    }
  };

  return (
    <div className="min-h-screen">
      <DemoBanner />
      <Confirm
        open={confirmPrize !== null}
        title="Have you verified the physical ticket?"
        message={
          confirmPrize ? (
            <span>
              Marking <b>{confirmPrize.winner_name}</b> — Prize #
              {confirmPrize.prize_number} as picked up.
            </span>
          ) : null
        }
        confirmLabel="YES — MARK PICKED UP"
        onConfirm={doClaim}
        onCancel={() => setConfirmPrize(null)}
      />

      <div className="mx-auto max-w-2xl p-4 sm:p-6">
        <div className="flex justify-between mb-4">
          <Link to="/" className="text-slate-500 underline">
            Home
          </Link>
          <Link to="/unclaimed" className="text-slate-500 underline">
            Unclaimed list
          </Link>
        </div>
        <h1 className="text-4xl font-black text-center mb-6">Prize Pickup</h1>

        <div className="card mb-6">
          <label className="label" htmlFor="pickup-search">
            Search by ticket #, winner name, or prize #
          </label>
          <input
            id="pickup-search"
            ref={inputRef}
            className="input-lg text-center"
            value={query}
            autoFocus
            autoComplete="off"
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && search()}
          />
          <button
            className="btn-primary w-full mt-4 py-6"
            onClick={search}
            disabled={busy}
          >
            SEARCH
          </button>
        </div>

        {error && (
          <p className="text-red-600 font-bold text-center mb-4">{error}</p>
        )}

        {results && results.length === 0 && (
          <p className="text-center text-2xl text-slate-500">
            No matching winners found.
          </p>
        )}

        <div className="space-y-4">
          {results?.map((r) => (
            <div key={r.id} className="card">
              <div className="text-4xl font-black">{r.winner_name}</div>
              <div className="text-xl text-slate-500 mt-2">Winning Ticket</div>
              <div className="text-3xl font-bold">{r.winning_ticket}</div>
              <div className="text-xl mt-2">
                Prize #{r.prize_number} — {r.name}
              </div>
              <div className="text-xl mt-1">
                Pickup Station: <b>{r.pickup_station || "—"}</b>
              </div>
              <div
                className={`inline-block mt-3 px-4 py-1 rounded-full text-lg font-black ${
                  r.claimed
                    ? "bg-green-100 text-green-800"
                    : "bg-orange-100 text-orange-800"
                }`}
              >
                {r.claimed ? "CLAIMED" : "UNCLAIMED"}
              </div>

              {!r.claimed && (
                <>
                  <p className="mt-4 text-red-600 font-black text-xl">
                    PHYSICAL WINNING TICKET MUST BE PRESENT
                  </p>
                  <button
                    className="btn-success w-full mt-3 py-6"
                    onClick={() => setConfirmPrize(r)}
                  >
                    MARK AS PICKED UP
                  </button>
                </>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
