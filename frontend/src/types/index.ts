export interface Station {
  id: number;
  name: string;
  ticket_range_start: number;
  ticket_range_end: number;
  next_ticket_number: number;
  ticket_width: number;
  active: boolean;
  exhausted: boolean;
  range_start_display: string;
  range_end_display: string;
  next_ticket_display: string | null;
}

export interface Buyer {
  id: number | null;
  display_name: string;
  first_name?: string;
  last_name?: string;
}

export interface SaleResult {
  buyer: Buyer;
  station_id: number;
  station_name: string;
  quantity: number;
  ticket_numbers: string[];
  first_ticket: string;
  last_ticket: string;
  next_ticket: string | null;
}

export interface PrizeView {
  id: number;
  prize_number: number;
  name: string;
  description: string | null;
  session_number: number;
  pickup_station: string | null;
  status: "AVAILABLE" | "DRAWN" | "CLAIMED" | "REDRAW_REQUIRED";
  winner_name: string | null;
  winning_ticket: string | null;
  claimed: boolean;
}

export interface LookupResult {
  status: "ok" | "unknown" | "unsold" | "already_won";
  ticket_number: string;
  ticket_id?: number;
  sold?: boolean;
  buyer?: Buyer;
  won_prize_number?: number | null;
  won_prize_name?: string | null;
}

export interface AdminSummary {
  tickets_sold: number;
  buyers: number;
  prizes: number;
  prizes_drawn: number;
  claimed: number;
  unclaimed: number;
  current_session: number;
  sales_open: boolean;
  display_mode: string;
  session_1_status: string;
  session_2_status: string;
  announcement_text: string;
}

export interface AppConfig {
  app_name: string;
  demo_mode: boolean;
  display_rotation_seconds: number;
  new_winner_highlight_seconds: number;
  winners_per_page: number;
  allow_repeat_ticket_winners: boolean;
}

export interface DeviceInfo {
  name: string;
  role: string;
  last_seen: string;
}

export interface AuditEntry {
  id: number;
  created_at: string;
  action: string;
  device: string | null;
  role: string | null;
  details: string | null;
}

export type DisplayMode =
  | "LATEST"
  | "ALL"
  | "UNCLAIMED"
  | "SESSION_1"
  | "SESSION_2"
  | "ANNOUNCEMENT";
