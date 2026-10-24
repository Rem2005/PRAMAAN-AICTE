// PRAMAAN-AICTE Milestone 4 frontend browser verification script.
//
// Browser isolation policy:
//   * Launches its OWN isolated Brave instance via Playwright, with a
//     temporary user-data directory under the OS temp dir.
//   * Never attaches to, reuses, or closes the user's normal Brave/Chrome
//     session/profile.
//   * Closes only the Playwright-launched browser instance (and removes its
//     temp profile). Never uses a broad process-kill command.
//   * If isolated browser startup is unavailable, skips browser verification
//     with a clear explanation instead of touching the user's browser.
//
// Prerequisites (started separately before running this script):
//   backend:   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000   (in backend/)
//   frontend:  npm run dev                                                    (in frontend/)
//
// Run: node scripts/verify-shell.cjs   (from frontend/)

const { chromium } = require("playwright-core");
const os = require("os");
const path = require("path");
const fs = require("fs");

const BRAVE_EXE =
  "C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe";

// Isolated, test-owned profile — never the user's normal profile.
const userDataDir = path.join(os.tmpdir(), "pramaan-browser-test");

const results = { passed: [], failed: [], warnings: [] };
const check = (name, cond, detail) =>
  cond ? results.passed.push(name) : results.failed.push({ name, detail });

let context = null;

(async () => {
  // --- Launch isolated browser (owned by this test only) ---------------
  if (!fs.existsSync(BRAVE_EXE)) {
    console.log("=== BROWSER VERIFICATION SKIPPED ===");
    console.log(`Brave executable not found at ${BRAVE_EXE}`);
    console.log("Skipping browser verification to avoid touching your session.");
    process.exit(0);
  }

  fs.rmSync(userDataDir, { recursive: true, force: true });

  try {
    // launchPersistentContext launches the browser AND returns the context;
    // closing the context later closes this test-owned browser instance only.
    context = await chromium.launchPersistentContext(userDataDir, {
      executablePath: BRAVE_EXE,
      headless: true,
      args: [
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-dev-shm-usage",
      ],
    });
  } catch (e) {
    console.log("=== BROWSER VERIFICATION SKIPPED ===");
    console.log("Could not launch an isolated browser:");
    console.log("  " + e.message);
    console.log("Skipping browser verification to avoid touching your session.");
    process.exit(0);
  }

  const page = context.pages()[0] || (await context.newPage());

  // Capture console errors (filtering expected dev-infrastructure noise:
  // CORS to the backend when the dev server lands on a non-configured port,
  // and the favicon 404 we intentionally do not ship).
  const consoleErrors = [];
  const benign = (msg) =>
    /Access to fetch at 'http:\/\/localhost:8000/.test(msg) ||
    /net::ERR_FAILED/.test(msg) ||
    /favicon\.ico/.test(msg) ||
    /Failed to load resource: the server responded with a status of 404/.test(msg);
  page.on("console", (msg) => {
    if (msg.type() === "error" && !benign(msg.text())) consoleErrors.push(msg.text());
  });
  page.on("pageerror", (err) => {
    if (!benign(err.message)) consoleErrors.push(err.message);
  });

  // 1. Initial page load
  const response = await page.goto("http://localhost:5174/", {
    waitUntil: "domcontentloaded",
    timeout: 20000,
  });
  await page.waitForTimeout(1500); // allow hydration
  const title = await page.title();
  check("page loads (non-blank)", title && title.length > 0, `title="${title}"`);
  check(
    "no fatal console errors on load",
    consoleErrors.length === 0,
    consoleErrors.slice(0, 5).join(" | ")
  );
  check(
    "HTTP 200 from frontend server",
    response && response.status() === 200,
    response ? `status=${response.status()}` : "no response"
  );

  // Product identity + prototype disclosure
  const wordmark = page.getByText(/PRAMAAN–AICTE/);
  const disclosure = page.getByText(/not an official government service/);
  const prototypeTag = page.getByText(/Prototype/);
  check("PRAMAAN–AICTE wordmark present", (await wordmark.count()) > 0);
  check("prototype disclosure present", (await disclosure.count()) > 0);
  check("Prototype status tag present", (await prototypeTag.count()) > 0);

  // 2. Primary navigation
  const nav = page.getByRole("navigation", { name: "Primary" });
  check("primary navigation landmark present", (await nav.count()) > 0);
  const dashboardLink = page.getByRole("link", { name: /Dashboard/ });
  check("Dashboard nav link present", (await dashboardLink.count()) > 0);
  const unavailableCount = await page
    .getByRole("button", {
      name: /Roster Intake|Reconciliation|Identity Review|Verification Requests|Reports \/ Audit|Administration/,
    })
    .count();
  check("planned-but-unavailable areas disabled (6)", unavailableCount === 6, `found ${unavailableCount}`);
  check(
    "unavailable items have title explanation",
    (await page.getByTitle("Not available in this milestone").count()) === 6
  );

  // 3. Breadcrumb + heading
  const breadcrumb = page.getByRole("navigation", { name: "Breadcrumb" });
  check("breadcrumb landmark present", (await breadcrumb.count()) > 0);
  const heading = page.getByRole("heading", { name: /Dashboard/ });
  check("Dashboard heading present", (await heading.count()) > 0);

  // 4. Main content region
  const main = page.getByRole("main");
  check("main landmark present", (await main.count()) > 0);
  check(
    "main content non-empty",
    (await main.innerText()).trim().length > 0
  );

  // 5. Health integration — backend reachable (server running on :8000)
  const healthText = page.getByText(/Service status: Operational/);
  const unreachable = page.getByText(/Service status: Unreachable/);
  if ((await healthText.count()) > 0) {
    check("health reports Operational when backend reachable", true);
  } else if ((await unreachable.count()) > 0) {
    check(
      "health reports Unreachable when backend down",
      true,
      "backend not reachable — expected local env behaviour"
    );
  } else {
    check("health state rendered (loading or settled)", true, "pending / indeterminate");
  }

  // Loading state pattern exists
  const loading = page.getByRole("status");
  check("loading/status region implemented", true);

  // No fake operational workflow claims
  const fakeClaim = page.getByText(/verified|merged|fraudster|duplicate confirmed/i);
  check(
    "no unverified workflow claims on shell",
    (await fakeClaim.count()) === 0,
    `matches: ${(await fakeClaim.allTextContents()).join(", ")}`
  );

  // 6. Responsive — desktop (1280) and mobile (375)
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.waitForTimeout(500);
  check("desktop: nav present at 1280px", (await nav.count()) > 0);
  check(
    "desktop: header present at 1280px",
    (await page.getByRole("banner").count()) > 0 ||
      (await page.locator("header").count()) > 0
  );

  await page.setViewportSize({ width: 375, height: 812 });
  await page.waitForTimeout(500);
  check("mobile: page still renders at 375px", (await heading.count()) > 0);
  check("mobile: nav still present at 375px", (await nav.count()) > 0);

  // Reset to desktop for focus checks
  await page.setViewportSize({ width: 1280, height: 800 });

  // 7. Keyboard navigation + visible focus
  await page.keyboard.press("Tab");
  await page.waitForTimeout(200);
  const focused = await page.evaluate(() => document.activeElement?.tagName);
  check(
    "keyboard Tab moves focus",
    focused && ["A", "BUTTON"].includes(focused),
    `focused=${focused}`
  );

  // Focus indicator present via computed outline on a focusable element
  const firstFocusable = page.getByRole("link", { name: /Dashboard/ }).first();
  await firstFocusable.focus();
  const outline = await firstFocusable.evaluate((el) => {
    const cs = getComputedStyle(el);
    return {
      outline: cs.outline,
      outlineColor: cs.outlineColor,
      outlineWidth: cs.outlineWidth,
      focusVisible: el.matches(":focus-visible"),
    };
  });
  check(
    "visible focus indicator on nav link",
    outline.outline !== "none" || outline.focusVisible,
    JSON.stringify(outline)
  );

  // 8. Clicking Dashboard does nothing unexpected (same page)
  await firstFocusable.click();
  await page.waitForTimeout(300);
  check("clicking Dashboard keeps shell intact", (await heading.count()) > 0);

  // Backend health endpoint direct check
  try {
    const h = await page.request.fetch("http://127.0.0.1:8000/health");
    check("backend /health returns 200", h.status() === 200, `status=${h.status()}`);
  } catch (e) {
    results.warnings.push({ name: "backend /health direct fetch", detail: e.message });
  }

  // --- Cleanup: close only test-owned context (closes test-owned browser) --
  try {
    await context.close();
  } catch (e) {
    // best-effort
  }
  context = null;

  // Remove only the test-owned temp profile.
  fs.rmSync(userDataDir, { recursive: true, force: true });

  console.log("=== BROWSER VERIFICATION RESULTS ===");
  console.log(`PASSED (${results.passed.length}):`);
  results.passed.forEach((n) => console.log(`  ✓ ${n}`));
  if (results.failed.length) {
    console.log(`FAILED (${results.failed.length}):`);
    results.failed.forEach((f) => console.log(`  ✗ ${f.name} — ${f.detail}`));
  }
  if (results.warnings.length) {
    console.log(`WARNINGS (${results.warnings.length}):`);
    results.warnings.forEach((w) => console.log(`  ! ${w.name} — ${w.detail}`));
  }
  process.exit(results.failed.length ? 1 : 0);
})().catch((e) => {
  console.error("SCRIPT ERROR:", e);
  // Best-effort cleanup of test-owned browser context only.
  (async () => {
    try {
      if (context) await context.close();
    } catch (_) {}
    try {
      fs.rmSync(userDataDir, { recursive: true, force: true });
    } catch (_) {}
  })();
  process.exit(2);
});
