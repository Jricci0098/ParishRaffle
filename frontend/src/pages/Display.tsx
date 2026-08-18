import { useCallback, useEffect, useRef, useState } from "react";

import { useConfig } from "../hooks/useConfig";
import { useWebSocket } from "../hooks/useWebSocket";
import { api } from "../services/api";
import type { PrizeView } from "../types";

type Mode =
  | "LATEST"
  | "ALL"
  | "UNCLAIMED"
  | "SESSION_1"
  | "SESSION_2"
  | "ANNOUNCEMENT";

const MODE_TITLES: Record<Mode, string> = {
  LATEST: "RAFFLE WINNERS",
  ALL: "ALL RAFFLE WINNERS",
  UNCLAIMED: "PLEASE CLAIM YOUR PRIZE",
  SESSION_1: "SESSION 1 WINNERS",
  SESSION_2: "SESSION 2 WINNERS",
  ANNOUNCEMENT: "ANNOUNCEMENT",
};

export function Display() {
  const config = useConfig();
  const [mode, setMode] = useState<Mode>("LATEST");
  const [announcement, setAnnouncement] = useState("");
  const [winners, setWinners] = useState<PrizeView[]>([]);
  const [page, setPage] = useState(0);
  const [highlight, setHighlight] = useState<PrizeView | null>(null);
  const highlightTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const perPage = config?.winners_per_page ?? 8;
  const rotation = (config?.display_rotation_seconds ?? 8) * 1000;
  const highlightSecs = config?.new_winner_highlight_seconds ?? 9;

  const load = useCallback(async (m: Mode) => {
    let data: PrizeView[] = [];
    if (m === "UNCLAIMED") {
      data = await api.unclaimed();
    } else if (m === "SESSION_1") {
      data = await api.winners(1);
    } else if (m === "SESSION_2") {
      data = await api.winners(2);
    } else if (m === "LATEST" || m === "ALL") {
      data = await api.winners();
    }
    // LATEST shows newest first.
    if (m === "LATEST") data = [...data].reverse();
    setWinners(data);
  }, []);

  const refreshState = useCallback(async () => {
    const state = await api.state();
    const m = (state.display_mode as Mode) || "LATEST";
    setMode(m);
    setAnnouncement(state.announcement_text || "");
    await load(m);
  }, [load]);

  useEffect(() => {
    refreshState();
  }, [refreshState]);

  useWebSocket({
    deviceName: "TV Display",
    role: "display",
    onEvent: (msg) => {
      if (msg.event === "display.mode.changed") {
        const m = (msg.data.mode as Mode) || "LATEST";
        setMode(m);
        setAnnouncement((msg.data.announcement_text as string) || "");
        load(m);
      } else if (msg.event === "winner.created") {
        const w = msg.data as unknown as PrizeView;
        setHighlight(w);
        if (highlightTimer.current) clearTimeout(highlightTimer.current);
        highlightTimer.current = setTimeout(
          () => setHighlight(null),
          highlightSecs * 1000
        );
        load(mode);
      } else if (
        msg.event === "prize.claimed" ||
        msg.event === "winner.redrawn"
      ) {
        load(mode);
      }
    },
  });

  // Auto-rotate pages.
  const pages = Math.max(1, Math.ceil(winners.length / perPage));
  useEffect(() => {
    if (pages <= 1) {
      setPage(0);
      return;
    }
    const id = setInterval(() => setPage((p) => (p + 1) % pages), rotation);
    return () => clearInterval(id);
  }, [pages, rotation]);

  useEffect(
    () => () => {
      if (highlightTimer.current) clearTimeout(highlightTimer.current);
    },
    []
  );

  const visible = winners.slice(page * perPage, page * perPage + perPage);

  // ----- New winner highlight overlay -----
  if (highlight) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-br from-yellow-400 to-orange-500 text-white text-center p-8 animate-pulse">
        <div className="text-6xl font-black mb-8">🎉 CONGRATULATIONS! 🎉</div>
        <div className="text-[10rem] leading-none font-black">
          {highlight.winner_name}
        </div>
        <div className="text-6xl mt-8 font-bold">
          Prize #{highlight.prize_number} — {highlight.name}
        </div>
        <div className="text-4xl mt-4 opacity-90">
          Ticket #{highlight.winning_ticket}
        </div>
      </div>
    );
  }

  // ----- Announcement mode -----
  if (mode === "ANNOUNCEMENT") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900 text-white text-center p-12">
        <div className="text-[7rem] leading-tight font-black">
          {announcement || "Welcome!"}
        </div>
      </div>
    );
  }

  // ----- Winner board -----
  return (
    <div className="min-h-screen bg-slate-900 text-white flex flex-col">
      <header className="bg-blue-800 py-6 text-center">
        <h1 className="text-6xl font-black tracking-wide">
          {MODE_TITLES[mode]}
        </h1>
      </header>

      <main className="flex-1 p-8">
        {visible.length === 0 ? (
          <div className="h-full flex items-center justify-center text-5xl text-slate-400">
            Winners will appear here as they are drawn…
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {visible.map((w) => (
              <div
                key={w.id}
                className={`rounded-3xl p-8 ${
                  w.claimed ? "bg-slate-700/60" : "bg-slate-800"
                }`}
              >
                <div className="text-6xl font-black">{w.winner_name}</div>
                <div className="text-4xl mt-3 text-blue-300">
                  Ticket #{w.winning_ticket}
                </div>
                <div className="text-3xl mt-2 text-slate-300">
                  Prize #{w.prize_number} — {w.name}
                </div>
                {w.pickup_station && (
                  <div className="text-2xl mt-2 text-emerald-300">
                    Pickup: {w.pickup_station}
                  </div>
                )}
                {mode === "UNCLAIMED" && (
                  <div className="text-2xl mt-2 text-orange-300 font-bold">
                    UNCLAIMED
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </main>

      {pages > 1 && (
        <footer className="text-center py-4 text-3xl text-slate-400">
          Page {page + 1} of {pages}
        </footer>
      )}
    </div>
  );
}
