import { useEffect, useState } from "react";

import { api } from "../services/api";
import type { AppConfig } from "../types";

let cached: AppConfig | null = null;

/** Loads (and caches) public app config. */
export function useConfig(): AppConfig | null {
  const [config, setConfig] = useState<AppConfig | null>(cached);

  useEffect(() => {
    if (cached) return;
    api
      .config()
      .then((c) => {
        cached = c;
        setConfig(c);
      })
      .catch(() => setConfig(null));
  }, []);

  return config;
}
