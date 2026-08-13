import { ReactNode, useState } from "react";

import { api, getAdminPin, setAdminPin, clearAdminPin } from "../services/api";

/**
 * Gates admin-only screens behind the admin PIN. The PIN is validated against
 * the backend and cached in localStorage so a refresh does not log the admin
 * out (recoverable after an accidental refresh).
 */
export function AdminGate({ children }: { children: ReactNode }) {
  const [authed, setAuthed] = useState(getAdminPin() !== "");
  const [pin, setPin] = useState("");
  const [error, setError] = useState("");
  const [checking, setChecking] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setChecking(true);
    setError("");
    try {
      const res = await api.login(pin);
      if (res.role !== "admin") {
        setError("That PIN is not an admin PIN.");
        return;
      }
      setAdminPin(pin);
      setAuthed(true);
    } catch {
      setError("Incorrect PIN. Please try again.");
    } finally {
      setChecking(false);
    }
  };

  if (authed) {
    return (
      <>
        <div className="flex justify-end p-2">
          <button
            className="text-sm text-slate-500 underline"
            onClick={() => {
              clearAdminPin();
              setAuthed(false);
            }}
          >
            Lock admin
          </button>
        </div>
        {children}
      </>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-6">
      <form onSubmit={submit} className="card w-full max-w-md text-center">
        <h1 className="text-3xl font-black mb-6">Admin Access</h1>
        <label className="label text-left" htmlFor="admin-pin">
          Enter Admin PIN
        </label>
        <input
          id="admin-pin"
          className="input-lg text-center tracking-widest"
          type="password"
          inputMode="numeric"
          autoFocus
          value={pin}
          onChange={(e) => setPin(e.target.value)}
          aria-label="Admin PIN"
        />
        {error && <p className="mt-3 text-red-600 font-semibold">{error}</p>}
        <button
          className="btn-primary mt-6 w-full"
          type="submit"
          disabled={checking || !pin}
        >
          {checking ? "Checking…" : "Unlock"}
        </button>
      </form>
    </div>
  );
}
