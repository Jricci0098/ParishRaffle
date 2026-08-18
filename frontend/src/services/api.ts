/**
 * Thin fetch wrapper for the raffle REST API.
 *
 * The admin PIN is kept in localStorage and sent on privileged calls. This is
 * deliberately lightweight security suitable for a trusted local network.
 */
import type {
  AdminSummary,
  AppConfig,
  AuditEntry,
  DeviceInfo,
  LookupResult,
  PrizeView,
  SaleResult,
  Station,
} from "../types";

export class ApiError extends Error {
  code: string;
  status: number;
  constructor(message: string, code: string, status: number) {
    super(message);
    this.code = code;
    this.status = status;
  }
}

const ADMIN_PIN_KEY = "raffle_admin_pin";
const VOL_PIN_KEY = "raffle_volunteer_pin";

export function setAdminPin(pin: string) {
  localStorage.setItem(ADMIN_PIN_KEY, pin);
}
export function getAdminPin(): string {
  return localStorage.getItem(ADMIN_PIN_KEY) || "";
}
export function clearAdminPin() {
  localStorage.removeItem(ADMIN_PIN_KEY);
}
export function setVolunteerPin(pin: string) {
  localStorage.setItem(VOL_PIN_KEY, pin);
}
export function getVolunteerPin(): string {
  return localStorage.getItem(VOL_PIN_KEY) || "";
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  admin?: boolean;
  volunteer?: boolean;
}

async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (opts.admin) headers["X-Admin-Pin"] = getAdminPin();
  if (opts.volunteer) headers["X-Pin"] = getVolunteerPin() || getAdminPin();

  const res = await fetch(`/api${path}`, {
    method: opts.method || "GET",
    headers,
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
  });

  if (!res.ok) {
    let code = "error";
    let message = `Request failed (${res.status})`;
    try {
      const data = await res.json();
      if (data?.error) {
        code = data.error.code;
        message = data.error.message;
      } else if (data?.detail) {
        message = data.detail;
      }
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(message, code, res.status);
  }
  if (res.status === 204) return undefined as T;
  const text = await res.text();
  return text ? JSON.parse(text) : (undefined as T);
}

export const api = {
  // Config & auth
  config: () => request<AppConfig>("/config"),
  login: (pin: string) =>
    request<{ role: string }>("/auth/login", { method: "POST", body: { pin } }),

  // Stations
  stations: () => request<Station[]>("/stations"),
  station: (id: number) => request<Station>(`/stations/${id}`),
  createStation: (body: unknown) =>
    request<Station>("/stations", { method: "POST", body, admin: true }),
  updateStation: (id: number, body: unknown) =>
    request<Station>(`/stations/${id}`, {
      method: "PATCH",
      body,
      admin: true,
    }),
  deleteStation: (id: number) =>
    request(`/stations/${id}`, { method: "DELETE", admin: true }),

  // Sales
  createSale: (body: unknown) =>
    request<SaleResult>("/sales", { method: "POST", body }),
  undoSale: (station_id: number) =>
    request("/sales/undo", { method: "POST", body: { station_id }, admin: true }),
  manualEntry: (body: unknown) =>
    request<{ ticket_numbers: string[] }>("/sales/manual", {
      method: "POST",
      body,
      admin: true,
    }),
  salesStatus: () => request<{ sales_open: boolean }>("/sales/status"),

  // Tickets
  ticket: (num: string) => request(`/tickets/${encodeURIComponent(num)}`),

  // Prizes
  prizes: (session?: number) =>
    request<PrizeView[]>(`/prizes${session ? `?session=${session}` : ""}`),
  currentPrize: () => request<PrizeView | null>("/prizes/current"),
  navigatePrize: (id: number, offset: number) =>
    request<PrizeView | null>(`/prizes/navigate/${id}?offset=${offset}`),
  createPrize: (body: unknown) =>
    request<PrizeView>("/prizes", { method: "POST", body, admin: true }),
  updatePrize: (id: number, body: unknown) =>
    request<PrizeView>(`/prizes/${id}`, {
      method: "PATCH",
      body,
      admin: true,
    }),
  deletePrize: (id: number) =>
    request(`/prizes/${id}`, { method: "DELETE", admin: true }),
  reorderPrizes: (ordered_ids: number[]) =>
    request("/prizes/reorder", {
      method: "POST",
      body: { ordered_ids },
      admin: true,
    }),
  importPrizes: (content: string) =>
    request<{ created: number; updated: number; errors: string[] }>(
      "/prizes/import",
      { method: "POST", body: { content }, admin: true }
    ),
  importTicketsRaw: (content: string) =>
    request<{ created: number; skipped: number; errors: string[] }>(
      "/imports/tickets",
      { method: "POST", body: { content }, admin: true }
    ),

  // Draws
  lookup: (ticket_number: string) =>
    request<LookupResult>("/draws/lookup", {
      method: "POST",
      body: { ticket_number },
    }),
  confirmWinner: (body: unknown) =>
    request<PrizeView>("/draws", { method: "POST", body, admin: true }),

  // Claims & winners
  winners: (session?: number) =>
    request<PrizeView[]>(`/winners${session ? `?session=${session}` : ""}`),
  unclaimed: () => request<PrizeView[]>("/winners/unclaimed"),
  searchWinners: (q: string) =>
    request<PrizeView[]>(`/winners/search?q=${encodeURIComponent(q)}`),
  claim: (id: number, verified_by: string) =>
    request<PrizeView>(`/prizes/${id}/claim`, {
      method: "POST",
      body: { verified_by },
    }),
  redraw: (id: number, reason: string) =>
    request<PrizeView>(`/prizes/${id}/redraw`, {
      method: "POST",
      body: { reason },
      admin: true,
    }),

  // Admin
  summary: () => request<AdminSummary>("/admin/summary"),
  state: () => request<Record<string, string>>("/admin/state"),
  openSales: () =>
    request("/admin/sales/open", { method: "POST", admin: true }),
  closeSales: () =>
    request("/admin/sales/close", { method: "POST", admin: true }),
  startSession: (session_number: number) =>
    request("/admin/session/start", {
      method: "POST",
      body: { session_number },
      admin: true,
    }),
  endSession: (session_number: number) =>
    request("/admin/session/end", {
      method: "POST",
      body: { session_number },
      admin: true,
    }),
  setDisplay: (mode: string, announcement_text?: string) =>
    request("/admin/display", {
      method: "POST",
      body: { mode, announcement_text },
      admin: true,
    }),
  devices: () => request<DeviceInfo[]>("/admin/devices"),
  audit: (limit = 200) => request<AuditEntry[]>(`/admin/audit?limit=${limit}`),
  createBackup: () =>
    request<{ path: string; created: boolean }>("/admin/backup", {
      method: "POST",
      admin: true,
    }),

  // Setup
  setupStatus: () =>
    request<{
      needs_setup: boolean;
      has_event: boolean;
      event_name: string | null;
      station_count: number;
      prize_count: number;
    }>("/setup/status"),
  runWizard: (body: unknown) =>
    request("/setup/wizard", { method: "POST", body, admin: true }),

  // Demo
  demoStatus: () => request<{ demo_mode: boolean }>("/demo/status"),
  generateDemo: (buyers = 100, tickets = 500, prizes = 20) =>
    request(
      `/demo/generate?buyers=${buyers}&tickets=${tickets}&prizes=${prizes}`,
      { method: "POST", admin: true }
    ),
  resetDemo: () => request("/demo/reset", { method: "POST", admin: true }),
};

/** URL for a CSV report download (opened directly by the browser). */
export function reportUrl(name: string): string {
  return `/api/reports/${name}`;
}

/** URL for the backup download (admin PIN appended is not needed; the button
 * uses fetch with the header instead — see AdminDashboard). */
export const BACKUP_DOWNLOAD_PATH = "/api/admin/backup/download";
