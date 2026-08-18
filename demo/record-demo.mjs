/**
 * Automated demo recorder for Picnic Raffle Manager.
 *
 * Drives a real Chromium browser through the whole raffle workflow and records
 * video automatically — including the public TV display updating live over
 * WebSockets when a winner is confirmed.
 *
 * Produces two videos in ./videos:
 *   - operator-*.webm : the volunteer walkthrough (sales -> drawing -> pickup)
 *   - display-*.webm  : the TV board reacting live to each confirmed winner
 *
 * Usage:
 *   BASE_URL=http://localhost:8000 ADMIN_PIN=1234 node record-demo.mjs
 *
 * Requires a running server. If the raffle is empty it is seeded automatically
 * (event, 3 stations, 20 prizes, sample sales) so the drawing has real tickets.
 */
import fs from "node:fs";
import { chromium } from "playwright";

// Use a pre-installed Chromium when one is provided (e.g. CI/sandbox images),
// otherwise let Playwright use the browser it manages itself.
const PRESET_CHROME = process.env.PW_CHROME || "/opt/pw-browsers/chromium";
const EXECUTABLE_PATH = fs.existsSync(PRESET_CHROME) ? PRESET_CHROME : undefined;

const BASE_URL = (process.env.BASE_URL || "http://localhost:8000").replace(/\/$/, "");
const ADMIN_PIN = process.env.ADMIN_PIN || "1234";
const VIEWPORT = { width: 1280, height: 720 };

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const PRIZE_NAMES = [
  "Chocolate Basket", "Restaurant Gift Card", "School Backpack", "Coffee Basket",
  "Wine Gift Set", "Toy Bundle", "Spa Day Package", "Grocery Gift Card",
  "Family Board Games", "Movie Night Basket", "Gardening Kit", "BBQ Grill Set",
  "Bakery Gift Box", "Bookstore Voucher", "Sports Equipment", "Handmade Quilt",
  "Electronics Bundle", "Pizza Party", "Ice Cream Basket", "Local Honey Set",
];

/** Seed the instance via the REST API if it has no prizes yet. */
async function seedIfEmpty(request) {
  const status = await (await request.get(`${BASE_URL}/api/setup/status`)).json();
  const prizes = await (await request.get(`${BASE_URL}/api/prizes`)).json();
  if (Array.isArray(prizes) && prizes.length > 0) {
    console.log("Instance already has data — skipping seed.");
    return;
  }
  const admin = { "X-Admin-Pin": ADMIN_PIN, "Content-Type": "application/json" };
  console.log("Seeding event, stations, prizes and sales…");

  if (!status.has_event) {
    await request.post(`${BASE_URL}/api/setup/wizard`, {
      headers: admin,
      data: {
        event_name: "Saint Paul VI Parish Picnic Raffle 2026",
        sessions: 2,
        stations: [
          { name: "Ticket Table 1", ticket_range_start: 5000, ticket_range_end: 5199, ticket_width: 6, active: true },
          { name: "Ticket Table 2", ticket_range_start: 5200, ticket_range_end: 5399, ticket_width: 6, active: true },
          { name: "Ticket Table 3", ticket_range_start: 5400, ticket_range_end: 5599, ticket_width: 6, active: true },
        ],
      },
    });
  }
  await request.post(`${BASE_URL}/api/admin/sales/open`, { headers: admin, data: {} });

  const lines = ["prize_number,name,session,pickup_station"];
  for (let i = 1; i <= 20; i++) {
    const s = i > 10 ? 2 : 1;
    const p = ["A", "B", "C"][(i - 1) % 3];
    lines.push(`${i},${PRIZE_NAMES[i - 1]},${s},${p}`);
  }
  await request.post(`${BASE_URL}/api/prizes/import`, {
    headers: admin,
    data: { content: lines.join("\n") },
  });

  const stations = await (await request.get(`${BASE_URL}/api/stations`)).json();
  const byRange = Object.fromEntries(stations.map((s) => [s.ticket_range_start, s.id]));
  const sale = (sid, first, last, qty) =>
    request.post(`${BASE_URL}/api/sales`, {
      headers: { "Content-Type": "application/json" },
      data: { station_id: sid, first_name: first, last_name: last, quantity: qty },
    });
  // Enough tickets that the on-camera draws resolve to real buyers.
  await sale(byRange[5000], "Mary", "Jones", 20);     // 005000-005019
  await sale(byRange[5000], "Robert", "Smith", 10);   // 005020-005029
  await sale(byRange[5200], "James", "Brown", 15);    // 005200-005214
  await sale(byRange[5400], "David", "Anderson", 25); // 005400-005424
  console.log("Seed complete.");
}

async function main() {
  const browser = await chromium.launch({
    headless: true,
    executablePath: EXECUTABLE_PATH,
  });
  const context = await browser.newContext({
    viewport: VIEWPORT,
    recordVideo: { dir: "videos", size: VIEWPORT },
  });

  await seedIfEmpty(context.request);

  // --- Public TV display: records the live board the whole time ---
  const display = await context.newPage();
  await display.goto(`${BASE_URL}/display`, { waitUntil: "networkidle" });
  await sleep(2500);

  // --- Operator page: walks the workflow ---
  const op = await context.newPage();

  // 1) Ticket sales
  await op.goto(`${BASE_URL}/sales`, { waitUntil: "networkidle" });
  await sleep(1500);
  await op.getByRole("button", { name: /Ticket Table 1/i }).first().click();
  await sleep(1500);
  await op.fill("#first", "Anna");
  await op.fill("#last", "Taylor");
  await sleep(600);
  await op.getByRole("button", { name: /^5$/ }).click();
  await sleep(800);
  await op.getByRole("button", { name: /COMPLETE SALE/i }).click();
  await op.getByText("SALE COMPLETE").waitFor({ timeout: 8000 });
  await sleep(2500);

  // 2) Drawing console — confirm three winners; the display reacts live.
  const draws = [
    { prize: 1, ticket: "005005" }, // Mary Jones
    { prize: 2, ticket: "005025" }, // Robert Smith
    { prize: 3, ticket: "005205" }, // James Brown
  ];
  for (const d of draws) {
    await op.goto(`${BASE_URL}/drawing`, { waitUntil: "networkidle" });
    await sleep(1200);
    const input = op.locator("#ticket");
    await input.click();
    await input.fill("");
    // Type like a scanner, then Enter triggers the lookup.
    await input.type(d.ticket, { delay: 90 });
    await sleep(400);
    await input.press("Enter");
    // Buyer name appears; confirm the winner.
    await op.getByRole("button", { name: /CONFIRM WINNER/i }).waitFor({ timeout: 8000 });
    await sleep(1500);
    await op.getByRole("button", { name: /CONFIRM WINNER/i }).click();
    // Let the display show the CONGRATULATIONS highlight, then the board.
    await sleep(9000);
  }

  // 3) Prize pickup — search and mark one prize picked up.
  await op.goto(`${BASE_URL}/pickup`, { waitUntil: "networkidle" });
  await sleep(1200);
  await op.fill("#pickup-search", "005005");
  await sleep(600);
  await op.getByRole("button", { name: /^SEARCH$/i }).click();
  await op.getByText(/PHYSICAL WINNING TICKET/i).waitFor({ timeout: 8000 });
  await sleep(2000);
  await op.getByRole("button", { name: /MARK AS PICKED UP/i }).click();
  await op.getByRole("button", { name: /YES.*MARK PICKED UP/i }).waitFor({ timeout: 8000 });
  await sleep(1200);
  await op.getByRole("button", { name: /YES.*MARK PICKED UP/i }).click();
  await op.getByText(/CLAIMED/i).first().waitFor({ timeout: 8000 });
  await sleep(2500);

  // 4) Final look at the live board.
  await display.bringToFront();
  await sleep(4000);

  // Finalize videos.
  const opVideo = op.video();
  const displayVideo = display.video();
  await context.close();

  const opPath = opVideo ? await opVideo.path() : null;
  const displayPath = displayVideo ? await displayVideo.path() : null;
  await browser.close();

  console.log("VIDEO_OPERATOR=" + opPath);
  console.log("VIDEO_DISPLAY=" + displayPath);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
