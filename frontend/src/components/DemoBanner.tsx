import { useConfig } from "../hooks/useConfig";

/** Prominent banner shown whenever the app runs against the demo database. */
export function DemoBanner() {
  const config = useConfig();
  if (!config?.demo_mode) return null;
  return (
    <div className="bg-amber-400 text-amber-950 text-center py-2 text-xl font-black tracking-widest uppercase">
      ⚠ Demo Mode — practice data only
    </div>
  );
}
