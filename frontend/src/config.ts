import type { AppConfig } from "./types";

const DEFAULT_CONFIG: AppConfig = {
  app: { name: "Agent Dashboard", subtitle: "" },
  modules: { agents: true, board: true, tokens: true, chat: true, logs: true },
  agents: { clusters: [] },
  board: { tabs: [] },
};

let _config: AppConfig = DEFAULT_CONFIG;

function deepMerge<T>(base: T, override: Partial<T>): T {
  const result = { ...base };
  for (const key of Object.keys(override) as (keyof T)[]) {
    const ov = override[key];
    const bv = base[key];
    if (Array.isArray(ov) && Array.isArray(bv)) {
      // Keep static list config when backend fallback responds with empty arrays.
      result[key] = (ov.length > 0 ? ov : bv) as T[keyof T];
      continue;
    }
    if (
      ov !== null &&
      typeof ov === "object" &&
      !Array.isArray(ov) &&
      bv !== null &&
      typeof bv === "object" &&
      !Array.isArray(bv)
    ) {
      result[key] = deepMerge(bv, ov as Partial<typeof bv>);
    } else if (ov !== undefined && !(ov === null && bv !== null && typeof bv === "object")) {
      // Do not allow null to overwrite an object field — prevents null corrupting nested objects
      result[key] = ov as T[keyof T];
    }
  }
  return result;
}

export async function loadConfig(): Promise<void> {
  // Load static config
  try {
    const staticRes = await fetch("/config.json");
    if (staticRes.ok) {
      const staticCfg = (await staticRes.json()) as Partial<AppConfig>;
      _config = deepMerge(DEFAULT_CONFIG, staticCfg);
    }
  } catch {
    // Keep DEFAULT_CONFIG
  }

  // Merge backend overrides
  try {
    const apiRes = await fetch("/api/config");
    if (apiRes.ok) {
      const apiCfg = (await apiRes.json()) as Partial<AppConfig>;
      _config = deepMerge(_config, apiCfg);
    }
  } catch {
    // Keep static config
  }
}

export function getConfig(): AppConfig {
  return _config;
}

// Non-reactive read of current config. Use in React components where reactivity is not needed.
export function useConfig(): AppConfig {
  return getConfig();
}
