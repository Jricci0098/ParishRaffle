import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { DemoBanner } from "../components/DemoBanner";
import { ApiError, api, getAdminPin, setAdminPin } from "../services/api";
import type { LookupResult, PrizeView } from "../types";

function ensureAdmin(): boolean {
  if (getAdminPin()) return true;
  const pin = window.prompt("Admin authorization required. Enter Admin PIN:");
  if (!pin) return false;
  setAdminPin(pin);
  return true;
}

export function Drawing() {
  const [prize, setPrize] = useState<PrizeView | null>(null);
  const [ticket, setTicket] = useState("");
  const [lookup, setLookup] = useState<LookupResult | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const focusInput = () => setTimeout(() => inputRef.current?.focus(), 50);

  const loadCurrent = useCallback(async () => {
    const p = await api.currentPrize();
    setPrize(p);
    setTicket("");
    setLookup(null);
    setError("");
    focusInput();
  }, []);

  useEffect(() => {
    loadCurrent();
  }, [loadCurrent]);

  const navigate = async (offset: number) => {
    if (!prize) return;
    const p = await api.navigatePrize(prize.id, offset);
    if (p) {
      setPrize(p);
      setTicket("");
      setLookup(null);
      setError("");
      focusInput();
    }
  };

  const doLookup = async () => {
    if (!ticket.trim()) return;
    setBusy(true);
    setError("");
    try {
      const res = await api.lookup(ticket.trim());
      setLookup(res);
    } catch (e) {
      setError((e as ApiError).message);
    } finally {
      setBusy(false);
    }
  };

  const confirm = async (opts: {
    allow_unsold?: boolean;
    allow_already_won?: boolean;
    manual_first_name?: string;
    manual_last_name?: string;
  } = {}) => {
    if (!prize) return;
    const needsAdmin =
      opts.allow_unsold ||
      opts.allow_already_won ||
      opts.manual_first_name ||
      opts.manual_last_name;
    if (needsAdmin && !ensureAdmin()) return;
    setBusy(true);
    setError("");
    try {
      await api.confirmWinner({
        prize_id: prize.id,
        ticket_number: ticket.trim(),
        device: "Drawing Console",
        ...opts,
      });
      // Winner broadcast to displays by the backend. Advance to next prize.
      await loadCurrent();
    } catch (e) {
      setError((e as ApiError).message);
    } finally {
      setBusy(false);
    }
  };

  const doRedraw = async () => {
    if (!prize || !ensureAdmin()) return;
    if (!window.confirm(`Redraw Prize #${prize.prize_number}? The current winner will be voided.`))
      return;
    try {
      const p = await api.redraw(prize.id, "Winner unavailable");
      setPrize(p);
      setLookup(null);
      setTicket("");
      focusInput();
    } catch (e) {
      setError((e as ApiError).message);
    }
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    // USB barcode scanners send the digits then an Enter key.
    if (e.key === "Enter") {
      e.preventDefault();
      doLookup();
    }
  };

  if (!prize) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center">
        <DemoBanner />
        <h1 className="text-4xl font-black">No prizes to draw</h1>
        <p className="text-slate-500 mt-4">
          Add prizes in{" "}
          <Link to="/admin/prizes" className="underline">
            Prize Management
          </Link>
          .
        </p>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <DemoBanner />
      <div className="mx-auto max-w-3xl p-4 sm:p-6">
        <div className="flex justify-between items-center mb-4">
          <Link to="/" className="text-slate-500 underline">
            Home
          </Link>
          <span className="text-lg text-slate-500">
            Session {prize.session_number}
          </span>
        </div>

        {/* Current prize */}
        <div className="card text-center mb-6">
          <div className="text-2xl text-slate-500">CURRENT PRIZE</div>
          <div className="text-6xl font-black text-purple-700">
            Prize #{prize.prize_number}
          </div>
          <div className="text-4xl font-bold mt-2">{prize.name}</div>
          {prize.status === "DRAWN" && prize.winner_name && (
            <div className="mt-3 text-green-700 text-2xl font-bold">
              Winner: {prize.winner_name} ({prize.winning_ticket})
            </div>
          )}
          {prize.status === "REDRAW_REQUIRED" && (
            <div className="mt-3 text-orange-600 text-xl font-bold">
              Needs redraw
            </div>
          )}
        </div>

        {/* Ticket entry */}
        <div className="card mb-6">
          <label className="label" htmlFor="ticket">
            Winning Ticket (scan or type, then Enter)
          </label>
          <input
            id="ticket"
            ref={inputRef}
            className="input-lg text-center text-5xl tracking-widest"
            value={ticket}
            autoFocus
            autoComplete="off"
            onChange={(e) => {
              setTicket(e.target.value);
              setLookup(null);
            }}
            onKeyDown={onKeyDown}
            aria-label="Winning ticket number"
          />
          <div className="grid grid-cols-2 gap-3 mt-4">
            <button className="btn-primary" onClick={doLookup} disabled={busy}>
              LOOK UP
            </button>
            <button
              className="btn-success"
              onClick={() => confirm()}
              disabled={busy || !lookup || lookup.status !== "ok"}
            >
              CONFIRM WINNER
            </button>
          </div>
        </div>

        {/* Lookup result */}
        {lookup && (
          <div className="card mb-6 text-center">
            {lookup.status === "ok" && (
              <>
                <div className="text-xl text-slate-500">Ticket</div>
                <div className="text-4xl font-black">
                  {lookup.ticket_number}
                </div>
                <div className="text-xl text-slate-500 mt-4">Buyer</div>
                <div className="text-5xl font-black text-blue-700">
                  {lookup.buyer?.display_name}
                </div>
              </>
            )}

            {lookup.status === "unknown" && (
              <UnknownTicket
                ticket={lookup.ticket_number}
                onTryAgain={() => {
                  setLookup(null);
                  setTicket("");
                  focusInput();
                }}
                onManual={(f, l) =>
                  confirm({ manual_first_name: f, manual_last_name: l })
                }
              />
            )}

            {lookup.status === "unsold" && (
              <div>
                <p className="text-2xl font-bold text-orange-600">
                  WARNING: Ticket {lookup.ticket_number} was not recorded as
                  sold.
                </p>
                <p className="text-lg mt-1">
                  Buyer on record: {lookup.buyer?.display_name}
                </p>
                <div className="grid grid-cols-2 gap-3 mt-4">
                  <button
                    className="btn-neutral"
                    onClick={() => {
                      setLookup(null);
                      setTicket("");
                      focusInput();
                    }}
                  >
                    Cancel
                  </button>
                  <button
                    className="btn-danger"
                    onClick={() => confirm({ allow_unsold: true })}
                  >
                    Admin Override
                  </button>
                </div>
              </div>
            )}

            {lookup.status === "already_won" && (
              <div>
                <p className="text-2xl font-bold text-red-600">
                  Ticket {lookup.ticket_number} has already won Prize #
                  {lookup.won_prize_number}.
                </p>
                <div className="grid grid-cols-2 gap-3 mt-4">
                  <button
                    className="btn-neutral"
                    onClick={() => {
                      setLookup(null);
                      setTicket("");
                      focusInput();
                    }}
                  >
                    Try Again
                  </button>
                  <button
                    className="btn-danger"
                    onClick={() => confirm({ allow_already_won: true })}
                  >
                    Admin Override
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {error && (
          <p className="text-red-600 font-bold text-xl text-center mb-4">
            {error}
          </p>
        )}

        {/* Navigation */}
        <div className="grid grid-cols-3 gap-3">
          <button className="btn-neutral" onClick={() => navigate(-1)}>
            ◀ PREVIOUS
          </button>
          <button className="btn-danger" onClick={doRedraw}>
            REDRAW
          </button>
          <button className="btn-neutral" onClick={() => navigate(1)}>
            NEXT ▶
          </button>
        </div>
      </div>
    </div>
  );
}

function UnknownTicket({
  ticket,
  onTryAgain,
  onManual,
}: {
  ticket: string;
  onTryAgain: () => void;
  onManual: (first: string, last: string) => void;
}) {
  const [manual, setManual] = useState(false);
  const [first, setFirst] = useState("");
  const [last, setLast] = useState("");

  return (
    <div>
      <p className="text-2xl font-bold text-red-600">
        Ticket {ticket} is not registered.
      </p>
      {!manual ? (
        <div className="grid grid-cols-2 gap-3 mt-4">
          <button className="btn-neutral" onClick={onTryAgain}>
            TRY AGAIN
          </button>
          <button className="btn-danger" onClick={() => setManual(true)}>
            ALLOW MANUAL WINNER
          </button>
        </div>
      ) : (
        <div className="mt-4 space-y-3 text-left">
          <p className="text-sm text-slate-500">
            Admin authorization required. Enter the winner's name:
          </p>
          <input
            className="input-lg"
            placeholder="First name"
            value={first}
            onChange={(e) => setFirst(e.target.value)}
          />
          <input
            className="input-lg"
            placeholder="Last name"
            value={last}
            onChange={(e) => setLast(e.target.value)}
          />
          <button
            className="btn-danger w-full"
            onClick={() => onManual(first, last)}
            disabled={!first && !last}
          >
            Confirm Manual Winner
          </button>
        </div>
      )}
    </div>
  );
}
