import { Link } from "react-router-dom";

import { DemoBanner } from "../components/DemoBanner";
import { useConfig } from "../hooks/useConfig";

const tiles = [
  { to: "/sales", label: "Ticket Sales", emoji: "🎟️", color: "bg-blue-700" },
  { to: "/drawing", label: "Drawing Console", emoji: "🎲", color: "bg-purple-700" },
  { to: "/display", label: "TV Display", emoji: "📺", color: "bg-slate-800" },
  { to: "/pickup", label: "Prize Pickup", emoji: "🎁", color: "bg-green-700" },
  { to: "/unclaimed", label: "Unclaimed", emoji: "📋", color: "bg-orange-600" },
  { to: "/admin", label: "Admin", emoji: "⚙️", color: "bg-red-700" },
];

export function Home() {
  const config = useConfig();
  return (
    <div className="min-h-screen">
      <DemoBanner />
      <div className="mx-auto max-w-4xl p-6">
        <h1 className="text-5xl font-black text-center my-8">
          {config?.app_name || "Picnic Raffle Manager"}
        </h1>
        <p className="text-center text-xl text-slate-500 mb-10">
          Choose this device's screen
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
          {tiles.map((t) => (
            <Link
              key={t.to}
              to={t.to}
              className={`${t.color} text-white rounded-3xl p-10 text-center shadow-lg hover:brightness-110 transition`}
            >
              <div className="text-6xl mb-3">{t.emoji}</div>
              <div className="text-3xl font-black">{t.label}</div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
