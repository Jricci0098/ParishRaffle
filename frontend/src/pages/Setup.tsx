import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { DemoBanner } from "../components/DemoBanner";
import { ApiError, api } from "../services/api";

interface StationForm {
  name: string;
  ticket_range_start: number;
  ticket_range_end: number;
  ticket_width: number;
  active: boolean;
}

const DEFAULT_STATIONS: StationForm[] = [
  { name: "Ticket Table 1", ticket_range_start: 5000, ticket_range_end: 5199, ticket_width: 6, active: true },
  { name: "Ticket Table 2", ticket_range_start: 5200, ticket_range_end: 5399, ticket_width: 6, active: true },
  { name: "Ticket Table 3", ticket_range_start: 5400, ticket_range_end: 5599, ticket_width: 6, active: true },
];

export function Setup() {
  const nav = useNavigate();
  const [step, setStep] = useState(1);
  const [eventName, setEventName] = useState(
    "Saint Paul VI Parish Picnic Raffle 2026"
  );
  const [eventDate, setEventDate] = useState("");
  const [sessions, setSessions] = useState(1);
  const [stations, setStations] = useState<StationForm[]>(DEFAULT_STATIONS);
  const [status, setStatus] = useState<{ needs_setup: boolean; event_name: string | null } | null>(null);
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api.setupStatus().then(setStatus).catch(() => {});
  }, []);

  const updateStation = (i: number, patch: Partial<StationForm>) => {
    const next = [...stations];
    next[i] = { ...next[i], ...patch };
    setStations(next);
  };

  const addStation = () =>
    setStations([
      ...stations,
      {
        name: `Ticket Table ${stations.length + 1}`,
        ticket_range_start: 0,
        ticket_range_end: 0,
        ticket_width: 6,
        active: true,
      },
    ]);

  const finish = async () => {
    setError("");
    try {
      await api.runWizard({
        event_name: eventName,
        event_date: eventDate || null,
        sessions,
        stations,
      });
      setMsg("Event created! Redirecting to Admin…");
      setTimeout(() => nav("/admin"), 1200);
    } catch (e) {
      setError((e as ApiError).message);
    }
  };

  const Progress = () => (
    <div className="flex gap-2 justify-center mb-6">
      {[1, 2, 3, 4].map((n) => (
        <div
          key={n}
          className={`h-3 w-16 rounded-full ${
            step >= n ? "bg-blue-700" : "bg-slate-300"
          }`}
        />
      ))}
    </div>
  );

  return (
    <div className="min-h-screen">
      <DemoBanner />
      <div className="mx-auto max-w-2xl p-4 sm:p-6">
        <Link to="/admin" className="text-slate-500 underline">
          ← Admin
        </Link>
        <h1 className="text-4xl font-black my-4 text-center">Setup Wizard</h1>

        {status && !status.needs_setup && (
          <div className="rounded-xl bg-amber-100 text-amber-900 p-3 mb-4 text-center">
            An event already exists ({status.event_name}). Running the wizard
            again creates an additional event.
          </div>
        )}

        <Progress />

        <div className="card">
          {step === 1 && (
            <div className="space-y-4">
              <h2 className="text-2xl font-black">Step 1 — Create Event</h2>
              <div>
                <label className="label">Event Name</label>
                <input
                  className="input-lg"
                  value={eventName}
                  onChange={(e) => setEventName(e.target.value)}
                />
              </div>
              <div>
                <label className="label">Event Date</label>
                <input
                  className="input-lg"
                  type="date"
                  value={eventDate}
                  onChange={(e) => setEventDate(e.target.value)}
                />
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-4">
              <h2 className="text-2xl font-black">
                Step 2 & 3 — Ticket Ranges & Stations
              </h2>
              {stations.map((s, i) => (
                <div key={i} className="border rounded-2xl p-4 space-y-2">
                  <input
                    className="input-lg text-2xl"
                    value={s.name}
                    onChange={(e) => updateStation(i, { name: e.target.value })}
                  />
                  <div className="grid grid-cols-2 gap-2">
                    <input
                      className="input-lg text-2xl"
                      type="number"
                      value={s.ticket_range_start}
                      onChange={(e) =>
                        updateStation(i, {
                          ticket_range_start: Number(e.target.value),
                        })
                      }
                      aria-label="Range start"
                    />
                    <input
                      className="input-lg text-2xl"
                      type="number"
                      value={s.ticket_range_end}
                      onChange={(e) =>
                        updateStation(i, {
                          ticket_range_end: Number(e.target.value),
                        })
                      }
                      aria-label="Range end"
                    />
                  </div>
                </div>
              ))}
              <button className="btn-neutral w-full" onClick={addStation}>
                + Add Station
              </button>
            </div>
          )}

          {step === 3 && (
            <div className="space-y-4">
              <h2 className="text-2xl font-black">
                Step 4 & 5 — Prizes & Sessions
              </h2>
              <div>
                <label className="label">Number of Raffle Sessions</label>
                <div className="flex gap-3">
                  {[1, 2].map((n) => (
                    <button
                      key={n}
                      className={sessions === n ? "btn-primary" : "btn-neutral"}
                      onClick={() => setSessions(n)}
                    >
                      {n} Session{n > 1 ? "s" : ""}
                    </button>
                  ))}
                </div>
              </div>
              <p className="text-slate-500">
                You can add prizes now or later in{" "}
                <Link to="/admin/prizes" className="underline">
                  Prize Management
                </Link>{" "}
                (including CSV import).
              </p>
            </div>
          )}

          {step === 4 && (
            <div className="space-y-4">
              <h2 className="text-2xl font-black">Step 6 & 7 — Review & Start</h2>
              <ul className="text-lg space-y-1">
                <li>
                  <b>Event:</b> {eventName}
                </li>
                <li>
                  <b>Date:</b> {eventDate || "—"}
                </li>
                <li>
                  <b>Sessions:</b> {sessions}
                </li>
                <li>
                  <b>Stations:</b>
                  <ul className="ml-6 list-disc">
                    {stations.map((s, i) => (
                      <li key={i}>
                        {s.name}: {s.ticket_range_start}–{s.ticket_range_end}
                      </li>
                    ))}
                  </ul>
                </li>
              </ul>
              {error && <p className="text-red-600 font-semibold">{error}</p>}
              {msg && <p className="text-green-700 font-semibold">{msg}</p>}
              <button className="btn-success w-full py-6" onClick={finish}>
                CREATE EVENT & START
              </button>
            </div>
          )}

          <div className="flex justify-between mt-6">
            <button
              className="btn-neutral"
              onClick={() => setStep((s) => Math.max(1, s - 1))}
              disabled={step === 1}
            >
              Back
            </button>
            {step < 4 && (
              <button className="btn-primary" onClick={() => setStep((s) => s + 1)}>
                Next
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
