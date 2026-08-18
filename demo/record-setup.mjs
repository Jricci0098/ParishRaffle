/**
 * Automated SETUP walkthrough recorder for Picnic Raffle Manager.
 *
 * Records the first-run/onboarding flow on an EMPTY instance:
 *   admin login -> setup wizard (event, ticket ranges, stations, sessions,
 *   review, start) -> prize management (manual add + CSV import) -> open sales
 *   -> ready to sell.
 *
 * Usage (point at a FRESH, empty server):
 *   BASE_URL=http://localhost:8001 ADMIN_PIN=1234 node record-setup.mjs
 *
 * Produces videos/setup-*.webm.
 */
import fs from "node:fs";
import { chromium } from "playwright";

const BASE_URL = (process.env.BASE_URL || "http://localhost:8001").replace(/\/$/, "");
const ADMIN_PIN = process.env.ADMIN_PIN || "1234";
const VIEWPORT = { width: 1280, height: 720 };

const PRESET_CHROME = process.env.PW_CHROME || "/opt/pw-browsers/chromium";
const EXECUTABLE_PATH = fs.existsSync(PRESET_CHROME) ? PRESET_CHROME : undefined;

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const PRIZE_CSV = [
  "prize_number,name,session,pickup_station",
  "1,Chocolate Basket,1,A",
  "2,Restaurant Gift Card,1,A",
  "3,School Backpack,1,B",
  "4,Coffee Basket,1,B",
  "5,Wine Gift Set,1,C",
  "6,Toy Bundle,1,C",
  "7,Spa Day Package,2,A",
  "8,Grocery Gift Card,2,B",
  "9,Family Board Games,2,B",
  "10,Movie Night Basket,2,C",
].join("\n");

async function main() {
  const browser = await chromium.launch({ headless: true, executablePath: EXECUTABLE_PATH });
  const context = await browser.newContext({
    viewport: VIEWPORT,
    recordVideo: { dir: "videos", size: VIEWPORT },
  });
  const page = await context.newPage();
  const type = (loc, text) => loc.pressSequentially(text, { delay: 60 });

  // 0) Land on the home screen.
  await page.goto(`${BASE_URL}/`, { waitUntil: "networkidle" });
  await sleep(2500);

  // 1) Admin login.
  await page.goto(`${BASE_URL}/admin`, { waitUntil: "networkidle" });
  await page.locator("#admin-pin").waitFor({ timeout: 8000 });
  await sleep(1200);
  await page.locator("#admin-pin").click();
  await type(page.locator("#admin-pin"), ADMIN_PIN);
  await sleep(600);
  await page.getByRole("button", { name: /Unlock/i }).click();
  await page.getByRole("heading", { name: /Admin Dashboard/i }).waitFor({ timeout: 8000 });
  await sleep(2000);

  // 2) Setup wizard.
  await page.getByRole("link", { name: /^Setup$/ }).click();
  await page.getByText(/Setup Wizard/i).waitFor({ timeout: 8000 });
  await sleep(1500);

  // Step 1 — event.
  const eventInput = page.locator("input.input-lg").first();
  await eventInput.click();
  await eventInput.fill("");
  await type(eventInput, "Saint Paul VI Parish Picnic Raffle 2026");
  await sleep(1200);
  await page.getByRole("button", { name: /^Next$/ }).click();
  await sleep(1500);

  // Step 2 — ticket ranges & stations (defaults shown).
  await sleep(2500);
  await page.getByRole("button", { name: /^Next$/ }).click();
  await sleep(1200);

  // Step 3 — sessions.
  await page.getByRole("button", { name: /2 Sessions/i }).click();
  await sleep(1500);
  await page.getByRole("button", { name: /^Next$/ }).click();
  await sleep(1200);

  // Step 4 — review & start.
  await sleep(2500);
  await page.getByRole("button", { name: /CREATE EVENT & START/i }).click();
  await page.waitForURL(/\/admin$/, { timeout: 10000 });
  await page.getByRole("heading", { name: /Admin Dashboard/i }).waitFor({ timeout: 8000 });
  await sleep(2500);

  // 3) Prize management — manual add + CSV import.
  await page.getByRole("link", { name: /^Prizes$/ }).click();
  await page.getByText(/Prize Management/i).waitFor({ timeout: 8000 });
  await sleep(1500);

  const addCard = page.locator(".card", { hasText: "Add Prize" }).first();
  const inputs = addCard.locator("input.input-lg");
  await inputs.nth(0).fill("1");
  await sleep(300);
  await type(inputs.nth(1), "Chocolate Basket");
  await inputs.nth(3).fill("A");
  await sleep(600);
  await addCard.getByRole("button", { name: /ADD PRIZE/i }).click();
  await sleep(2000);

  // Bulk CSV import (updates #1, creates the rest).
  const csv = page.getByPlaceholder(/prize_number/);
  await csv.click();
  await csv.fill(PRIZE_CSV);
  await sleep(1000);
  await page.getByRole("button", { name: /IMPORT PRIZES/i }).click();
  await page.getByText(/Imported:/i).waitFor({ timeout: 8000 });
  await sleep(2500);
  // Scroll to show the populated prize table.
  await page.mouse.wheel(0, 900);
  await sleep(2500);

  // 4) Open sales from the dashboard.
  await page.getByRole("link", { name: /Admin/i }).first().click();
  await page.getByRole("heading", { name: /Admin Dashboard/i }).waitFor({ timeout: 8000 });
  await sleep(1500);
  await page.getByRole("button", { name: /OPEN SALES/i }).click();
  await sleep(2500);

  // 5) Ready to sell — the sales station picker.
  await page.goto(`${BASE_URL}/sales`, { waitUntil: "networkidle" });
  await page.getByText(/Select This Station/i).waitFor({ timeout: 8000 });
  await sleep(3500);

  const video = page.video();
  await context.close();
  const p = video ? await video.path() : null;
  await browser.close();
  console.log("VIDEO_SETUP=" + p);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
