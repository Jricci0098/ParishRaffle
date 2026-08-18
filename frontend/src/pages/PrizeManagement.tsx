import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { Confirm } from "../components/Confirm";
import { DemoBanner } from "../components/DemoBanner";
import { ApiError, api } from "../services/api";
import type { PrizeView } from "../types";

const BLANK = {
  prize_number: 0,
  name: "",
  description: "",
  session_number: 1,
  pickup_station: "",
};

export function PrizeManagement() {
  const [prizes, setPrizes] = useState<PrizeView[]>([]);
  const [form, setForm] = useState<typeof BLANK>({ ...BLANK });
  const [editingId, setEditingId] = useState<number | null>(null);
  const [csv, setCsv] = useState("");
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");
  const [deleteId, setDeleteId] = useState<number | null>(null);

  const load = useCallback(async () => {
    setPrizes(await api.prizes());
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const save = async () => {
    setError("");
    try {
      if (editingId) {
        await api.updatePrize(editingId, form);
        setMsg(`Prize #${form.prize_number} updated.`);
      } else {
        await api.createPrize(form);
        setMsg(`Prize #${form.prize_number} added.`);
      }
      setForm({ ...BLANK });
      setEditingId(null);
      await load();
    } catch (e) {
      setError((e as ApiError).message);
    }
  };

  const edit = (p: PrizeView) => {
    setEditingId(p.id);
    setForm({
      prize_number: p.prize_number,
      name: p.name,
      description: p.description || "",
      session_number: p.session_number,
      pickup_station: p.pickup_station || "",
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const remove = async () => {
    if (deleteId === null) return;
    const id = deleteId;
    setDeleteId(null);
    try {
      await api.deletePrize(id);
      await load();
    } catch (e) {
      setError((e as ApiError).message);
    }
  };

  const move = async (index: number, dir: -1 | 1) => {
    const next = [...prizes];
    const target = index + dir;
    if (target < 0 || target >= next.length) return;
    [next[index], next[target]] = [next[target], next[index]];
    setPrizes(next);
    await api.reorderPrizes(next.map((p) => p.id));
  };

  const doImport = async () => {
    setError("");
    try {
      const res = await api.importPrizes(csv);
      setMsg(`Imported: ${res.created} created, ${res.updated} updated.`);
      setCsv("");
      await load();
    } catch (e) {
      setError((e as ApiError).message);
    }
  };

  return (
    <div className="min-h-screen">
      <DemoBanner />
      <Confirm
        open={deleteId !== null}
        title="Delete this prize?"
        message="Only prizes that have not been drawn can be deleted."
        danger
        confirmLabel="Delete"
        onConfirm={remove}
        onCancel={() => setDeleteId(null)}
      />
      <div className="mx-auto max-w-5xl p-4 sm:p-6">
        <div className="flex justify-between mb-4">
          <Link to="/admin" className="text-slate-500 underline">
            ← Admin
          </Link>
        </div>
        <h1 className="text-4xl font-black mb-6">Prize Management</h1>

        {msg && <p className="text-green-700 font-semibold mb-2">{msg}</p>}
        {error && <p className="text-red-600 font-semibold mb-2">{error}</p>}

        {/* Add / edit form */}
        <div className="card mb-6">
          <h2 className="text-2xl font-black mb-3">
            {editingId ? "Edit Prize" : "Add Prize"}
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="label">Prize Number</label>
              <input
                className="input-lg"
                type="number"
                value={form.prize_number || ""}
                onChange={(e) =>
                  setForm({ ...form, prize_number: Number(e.target.value) })
                }
              />
            </div>
            <div>
              <label className="label">Name</label>
              <input
                className="input-lg"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
            </div>
            <div>
              <label className="label">Session</label>
              <input
                className="input-lg"
                type="number"
                value={form.session_number}
                onChange={(e) =>
                  setForm({ ...form, session_number: Number(e.target.value) })
                }
              />
            </div>
            <div>
              <label className="label">Pickup Station</label>
              <input
                className="input-lg"
                value={form.pickup_station}
                onChange={(e) =>
                  setForm({ ...form, pickup_station: e.target.value })
                }
              />
            </div>
            <div className="md:col-span-2">
              <label className="label">Description</label>
              <input
                className="input-lg"
                value={form.description}
                onChange={(e) =>
                  setForm({ ...form, description: e.target.value })
                }
              />
            </div>
          </div>
          <div className="flex gap-3 mt-4">
            <button className="btn-primary flex-1" onClick={save}>
              {editingId ? "SAVE CHANGES" : "ADD PRIZE"}
            </button>
            {editingId && (
              <button
                className="btn-neutral"
                onClick={() => {
                  setEditingId(null);
                  setForm({ ...BLANK });
                }}
              >
                Cancel
              </button>
            )}
          </div>
        </div>

        {/* CSV import */}
        <div className="card mb-6">
          <h2 className="text-2xl font-black mb-3">CSV Import</h2>
          <p className="text-slate-500 mb-2">
            Columns: <code>prize_number,name,session,pickup_station</code>
          </p>
          <textarea
            className="input-lg text-lg font-mono"
            rows={4}
            placeholder={"prize_number,name,session,pickup_station\n1,Chocolate Basket,1,A"}
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
          <button className="btn-primary w-full mt-3" onClick={doImport} disabled={!csv.trim()}>
            IMPORT PRIZES
          </button>
        </div>

        {/* Prize list */}
        <div className="card overflow-x-auto">
          <h2 className="text-2xl font-black mb-3">
            Prizes ({prizes.length})
          </h2>
          <table className="w-full text-left">
            <thead>
              <tr className="border-b-2 border-slate-200 text-slate-500">
                <th className="py-2 pr-2">#</th>
                <th className="py-2 pr-2">Name</th>
                <th className="py-2 pr-2">Sess.</th>
                <th className="py-2 pr-2">Pickup</th>
                <th className="py-2 pr-2">Status</th>
                <th className="py-2 pr-2">Order</th>
                <th className="py-2 pr-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {prizes.map((p, i) => (
                <tr key={p.id} className="border-b border-slate-100">
                  <td className="py-2 pr-2 font-bold">{p.prize_number}</td>
                  <td className="py-2 pr-2">{p.name}</td>
                  <td className="py-2 pr-2">{p.session_number}</td>
                  <td className="py-2 pr-2">{p.pickup_station || "—"}</td>
                  <td className="py-2 pr-2">
                    <span className="text-sm font-semibold">{p.status}</span>
                  </td>
                  <td className="py-2 pr-2 whitespace-nowrap">
                    <button onClick={() => move(i, -1)} aria-label="Move up">
                      ⬆
                    </button>{" "}
                    <button onClick={() => move(i, 1)} aria-label="Move down">
                      ⬇
                    </button>
                  </td>
                  <td className="py-2 pr-2 whitespace-nowrap">
                    <button
                      className="text-blue-700 underline mr-3"
                      onClick={() => edit(p)}
                    >
                      Edit
                    </button>
                    <button
                      className="text-red-600 underline disabled:opacity-30"
                      onClick={() => setDeleteId(p.id)}
                      disabled={p.status !== "AVAILABLE"}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
