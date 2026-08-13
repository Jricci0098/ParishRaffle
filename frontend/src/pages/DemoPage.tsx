import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { Confirm } from "../components/Confirm";
import { DemoBanner } from "../components/DemoBanner";
import { ApiError, api } from "../services/api";

export function DemoPage() {
  const [demoMode, setDemoMode] = useState(false);
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");
  const [buyers, setBuyers] = useState(100);
  const [tickets, setTickets] = useState(500);
  const [prizes, setPrizes] = useState(20);
  const [showReset, setShowReset] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.demoStatus().then((s) => setDemoMode(s.demo_mode)).catch(() => {});
  }, []);

  const generate = async () => {
    setBusy(true);
    setError("");
    try {
      await api.generateDemo(buyers, tickets, prizes);
      setMsg(`Generated ${buyers} buyers, ${tickets} tickets, ${prizes} prizes.`);
    } catch (e) {
      setError((e as ApiError).message);
    } finally {
      setBusy(false);
    }
  };

  const reset = async () => {
    setShowReset(false);
    setBusy(true);
    try {
      await api.resetDemo();
      setMsg("Demo data cleared.");
    } catch (e) {
      setError((e as ApiError).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen">
      <DemoBanner />
      <Confirm
        open={showReset}
        title="Reset all demo data?"
        message="This deletes everything in the demo database."
        danger
        confirmLabel="Reset"
        onConfirm={reset}
        onCancel={() => setShowReset(false)}
      />
      <div className="mx-auto max-w-2xl p-4 sm:p-6">
        <Link to="/admin" className="text-slate-500 underline">
          ← Admin
        </Link>
        <h1 className="text-4xl font-black my-6">Demo / Dry Run Mode</h1>

        {!demoMode ? (
          <div className="card">
            <p className="text-xl text-slate-600">
              The server is <b>not</b> running in demo mode. To do a safe dry run
              on a separate database, start the server with{" "}
              <code>DEMO_MODE=true</code> (see the README) and reload this page.
              Demo data generation is disabled to protect production data.
            </p>
          </div>
        ) : (
          <>
            {msg && <p className="text-green-700 font-semibold mb-2">{msg}</p>}
            {error && <p className="text-red-600 font-semibold mb-2">{error}</p>}

            <div className="card mb-6">
              <h2 className="text-2xl font-black mb-3">Generate Demo Data</h2>
              <div className="grid grid-cols-3 gap-3 mb-4">
                <div>
                  <label className="label">Buyers</label>
                  <input
                    className="input-lg"
                    type="number"
                    value={buyers}
                    onChange={(e) => setBuyers(Number(e.target.value))}
                  />
                </div>
                <div>
                  <label className="label">Tickets</label>
                  <input
                    className="input-lg"
                    type="number"
                    value={tickets}
                    onChange={(e) => setTickets(Number(e.target.value))}
                  />
                </div>
                <div>
                  <label className="label">Prizes</label>
                  <input
                    className="input-lg"
                    type="number"
                    value={prizes}
                    onChange={(e) => setPrizes(Number(e.target.value))}
                  />
                </div>
              </div>
              <button
                className="btn-primary w-full py-6"
                onClick={generate}
                disabled={busy}
              >
                GENERATE DEMO DATA
              </button>
            </div>

            <div className="card">
              <h2 className="text-2xl font-black mb-3">Reset</h2>
              <button
                className="btn-danger w-full py-6"
                onClick={() => setShowReset(true)}
                disabled={busy}
              >
                RESET DEMO
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
