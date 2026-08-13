import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { Sales } from "../pages/Sales";

/** Route fetch calls to canned JSON responses for the sales workflow. */
function mockFetch() {
  return vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === "string" ? input : input.toString();
    const json = (data: unknown) =>
      new Response(JSON.stringify(data), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });

    if (url.endsWith("/api/config")) return json({ demo_mode: false });
    if (url.endsWith("/api/stations"))
      return json([
        {
          id: 1,
          name: "Ticket Table 1",
          ticket_range_start: 5000,
          ticket_range_end: 5199,
          next_ticket_number: 5000,
          ticket_width: 6,
          active: true,
          exhausted: false,
          range_start_display: "005000",
          range_end_display: "005199",
          next_ticket_display: "005000",
        },
      ]);
    if (url.endsWith("/api/sales/status")) return json({ sales_open: true });
    if (url.match(/\/api\/stations\/1$/))
      return json({
        id: 1,
        name: "Ticket Table 1",
        ticket_range_start: 5000,
        ticket_range_end: 5199,
        next_ticket_number: 5020,
        ticket_width: 6,
        active: true,
        exhausted: false,
        range_start_display: "005000",
        range_end_display: "005199",
        next_ticket_display: "005020",
      });
    if (url.endsWith("/api/sales") && init?.method === "POST")
      return json({
        buyer: { id: 1, display_name: "Mary Jones" },
        station_id: 1,
        station_name: "Ticket Table 1",
        quantity: 20,
        ticket_numbers: ["005000", "005019"],
        first_ticket: "005000",
        last_ticket: "005019",
        next_ticket: "005020",
      });
    return json({});
  });
}

describe("Sales workflow", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.stubGlobal("fetch", mockFetch());
  });
  afterEach(() => vi.restoreAllMocks());

  it("selects a station, completes a sale, and shows confirmation", async () => {
    render(
      <MemoryRouter>
        <Sales />
      </MemoryRouter>
    );

    // Station picker appears.
    const stationBtn = await screen.findByRole("button", {
      name: /Ticket Table 1/i,
    });
    fireEvent.click(stationBtn);

    // Sales form appears with next ticket.
    await screen.findByText("005000");

    fireEvent.change(screen.getByLabelText(/First Name/i), {
      target: { value: "Mary" },
    });
    fireEvent.change(screen.getByLabelText(/Last Name/i), {
      target: { value: "Jones" },
    });
    fireEvent.click(screen.getByText("20"));
    fireEvent.click(screen.getByText("COMPLETE SALE"));

    // Confirmation screen.
    await waitFor(() =>
      expect(screen.getByText("SALE COMPLETE")).toBeInTheDocument()
    );
    expect(screen.getByText("Mary Jones")).toBeInTheDocument();
    expect(screen.getByText(/005000–005019/)).toBeInTheDocument();
  });
});
