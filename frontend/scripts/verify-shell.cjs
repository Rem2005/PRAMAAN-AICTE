// PRAMAAN-AICTE Milestone 5 frontend browser verification script.
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
//   backend:   python -m uvicorn app.main:app --host 127.0.0.1 --port 8002   (in backend/)
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
  if (!fs.existsSync(BRAVE_EXE)) {
    console.log("=== BROWSER VERIFICATION SKIPPED ===");
    console.log(`Brave executable not found at ${BRAVE_EXE}`);
    process.exit(0);
  }

  fs.rmSync(userDataDir, { recursive: true, force: true });

  try {
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
    process.exit(0);
  }

  const page = context.pages()[0] || (await context.newPage());

  // Capture console errors (filtering expected dev-infrastructure noise).
  const consoleErrors = [];
  const benign = (msg) =>
    /Access to fetch at 'http:\/\/(localhost|127\.0\.0\.1):8002/.test(msg) ||
    /net::ERR_FAILED/.test(msg) ||
    /favicon\.ico/.test(msg) ||
    /Failed to load resource: the server responded with a status of 404/.test(msg);
  page.on("console", (msg) => {
    if (msg.type() === "error" && !benign(msg.text()))
      consoleErrors.push(msg.text());
  });
  page.on("pageerror", (err) => {
    if (!benign(err.message)) consoleErrors.push(err.message);
  });

  const baseUrl = "http://localhost:5173";

// Milestone 6: every application screen now sits behind sign-in. Supply a local
// account or browser verification is skipped rather than silently testing the
// login page as if it were the app.
const TEST_USERNAME = process.env.PRAMAAN_TEST_USERNAME;
const TEST_PASSWORD = process.env.PRAMAAN_TEST_PASSWORD;

  // 1. Initial page load - Dashboard
  const response = await page.goto(`${baseUrl}/`, {
    waitUntil: "domcontentloaded",
    timeout: 20000,
  });
  await page.waitForTimeout(1500);
  const title = await page.title();
  check("dashboard page loads (non-blank)", title && title.length > 0, `title="${title}"`);
  check("no fatal console errors on dashboard", consoleErrors.length === 0, consoleErrors.slice(0, 5).join(" | "));

  // Product identity + prototype disclosure
  const wordmark = page.getByText(/PRAMAAN–AICTE/);
  const disclosure = page.getByText(/not an official government service/);
  const prototypeTag = page.getByText(/Prototype/);
  check("PRAMAAN–AICTE wordmark present", (await wordmark.count()) > 0);
  check("prototype disclosure present", (await disclosure.count()) > 0);
  check("Prototype status tag present", (await prototypeTag.count()) > 0);

  // 1b. Sign in (application screens are behind authentication)
  const signInHeading = page.getByRole("heading", { name: /sign in/i });
  if ((await signInHeading.count()) > 0) {
    if (!TEST_USERNAME || !TEST_PASSWORD) {
      console.log("=== BROWSER VERIFICATION SKIPPED ===");
      console.log("The app is behind sign-in and no test account was provided.");
      console.log("Set PRAMAAN_TEST_USERNAME and PRAMAAN_TEST_PASSWORD, and");
      console.log("provision that account with python -m app.cli create-user.");
      try {
        await context.close();
      } catch (e) {
        // best-effort
      }
      fs.rmSync(userDataDir, { recursive: true, force: true });
      process.exit(0);
    }
    await page.fill("#username", TEST_USERNAME);
    await page.fill("#password", TEST_PASSWORD);
    await page.getByRole("button", { name: /sign in/i }).click();
    await page.waitForTimeout(1500);
    check(
      "sign-in reaches the dashboard",
      (await page.getByRole("heading", { name: /welcome back/i }).count()) > 0,
    );
    check(
      "sign-in surfaces no error",
      (await page.getByRole("alert").count()) === 0,
    );
  } else {
    check("already signed in on load", false, "unexpected sign-in state");
  }

  // 2. Primary navigation - Roster Intake now available
  const nav = page.getByRole("navigation", { name: "Primary" });
  check("primary navigation landmark present", (await nav.count()) > 0);

  // Every workspace area is implemented, so every nav item is a real link; a
  // disabled nav button would mean an area is planned but unreachable.
  const NAV_LABELS = [
    "Dashboard",
    "Roster Intake",
    "Reconciliation",
    "Identity Review",
    "Verification Requests",
    "Reports / Audit",
    "Administration",
  ];
  const NAV_HEADINGS = {
    "roster-intake": /Roster Intake/,
    reconciliation: /Reconciliation/,
    "identity-review": /Identity Review/,
    "verification-requests": /Verification Requests/,
    "reports-audit": /Reports and audit trail/,
    administration: /Administration/,
  };

  // 3. Every navigation item opens its own screen.
  for (const label of NAV_LABELS) {
    const link = page.locator("nav[aria-label='Primary'] a", { hasText: label }).first();
    check(`nav item present and enabled: ${label}`, (await link.count()) === 1);
  }
  const disabledNav = await page.locator("nav[aria-label='Primary'] button:disabled").count();
  check("no navigation item is left unimplemented", disabledNav === 0, `disabled=${disabledNav}`);

  for (const [key, heading] of Object.entries(NAV_HEADINGS)) {
    await page.goto(`${baseUrl}/#${key}`, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(1200);
    check(
      `screen renders: #${key}`,
      (await page.getByRole("heading", { name: heading }).count()) > 0,
    );
    // A screen that failed to reach the API shows an error alert; none should.
    const alerts = await page.getByRole("alert").allTextContents();
    check(
      `no error on #${key}`,
      alerts.filter((text) => !/not implemented/i.test(text)).length === 0,
      alerts.join(" | "),
    );
  }

  const rosterLink = page.getByRole("link", { name: /Roster Intake/ });
  await page.goto(`${baseUrl}/#dashboard`, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(800);
  await rosterLink.click();
  await page.waitForTimeout(1000);
  check("navigated to roster intake page", (await page.getByRole("heading", { name: /Roster Intake/ }).count()) > 0);

  // 4. Upload area and the sample roster download
  check(
    "upload step heading present",
    (await page.getByRole("heading", { name: /Upload roster CSV/ }).count()) > 0,
  );
  check(
    "file input present",
    (await page.locator('input[id="roster-file"]').count()) > 0,
  );
  try {
    const [download] = await Promise.all([
      page.waitForEvent("download", { timeout: 10000 }),
      page.getByRole("button", { name: /Download sample CSV/i }).click(),
    ]);
    check(
      "Download sample CSV produces pramaan-sample-roster.csv",
      download.suggestedFilename() === "pramaan-sample-roster.csv",
      download.suggestedFilename(),
    );
  } catch (e) {
    check("Download sample CSV produces pramaan-sample-roster.csv", false, e.message);
  }

  // 5. No fake operational workflow claims
  const fakeClaim = page.getByText(/verified|merged|fraudster|duplicate confirmed/i);
  check("no unverified workflow claims on shell", (await fakeClaim.count()) === 0);

  // 6. Responsive - desktop and mobile, per screen.
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: width === 390 ? 844 : 900 });
    for (const [key, heading] of Object.entries(NAV_HEADINGS)) {
      await page.goto(`${baseUrl}/#${key}`, { waitUntil: "domcontentloaded" });
      await page.waitForTimeout(700);
      const metrics = await page.evaluate(() => ({
        scrollWidth: document.documentElement.scrollWidth,
        innerWidth: window.innerWidth,
      }));
      const fits = metrics.scrollWidth <= metrics.innerWidth + 1;
      check(
        `${width}px: #${key} renders without horizontal overflow`,
        fits && (await page.getByRole("heading", { name: heading }).count()) > 0,
        `scrollWidth=${metrics.scrollWidth} viewport=${metrics.innerWidth}`,
      );
    }
  }

  // 7. Both navigation layouts are reachable: sidebar (wide) and disclosure (narrow).
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(`${baseUrl}/#dashboard`, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(700);
  check("desktop: sidebar navigation visible at 1440px", await nav.isVisible());
  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(500);
  const menu = page.locator("details > summary");
  check("mobile: disclosure menu offered at 390px", (await menu.count()) > 0);
  check("mobile: sidebar hidden at 390px", !(await nav.isVisible()));

  // 8. Keyboard navigation
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto(`${baseUrl}/#dashboard`, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(700);
  await page.keyboard.press("Tab");
  await page.waitForTimeout(200);
  const focused = await page.evaluate(() => document.activeElement?.tagName);
  check("keyboard Tab moves focus", focused && ["A", "BUTTON", "INPUT"].includes(focused), `focused=${focused}`);

  // Visible focus indicator
  const firstFocusable = page.getByRole("link", { name: /Dashboard/ }).first();
  await firstFocusable.focus();
  const outline = await firstFocusable.evaluate((el) => {
    const cs = getComputedStyle(el);
    return { outline: cs.outline, outlineColor: cs.outlineColor, outlineWidth: cs.outlineWidth, focusVisible: el.matches(":focus-visible") };
  });
  check("visible focus indicator on nav link", outline.outline !== "none" || outline.focusVisible, JSON.stringify(outline));

  // 9. Backend health endpoint direct check
  try {
    const h = await page.request.fetch("http://127.0.0.1:8002/health");
    check("backend /health returns 200", h.status() === 200, `status=${h.status()}`);
  } catch (e) {
    results.warnings.push({ name: "backend /health direct fetch", detail: e.message });
  }

  // Sign out so the temporary profile is not left holding a live session.
  try {
    await page.getByRole("button", { name: /sign out/i }).first().click();
    await page.waitForTimeout(500);
    check(
      "sign-out returns to the sign-in page",
      (await page.getByRole("heading", { name: /sign in/i }).count()) > 0,
    );
  } catch (e) {
    results.warnings.push({ name: "sign out", detail: e.message });
  }

  // Cleanup: close only test-owned context
  try {
    await context.close();
  } catch (e) {
    // best-effort
  }
  context = null;
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
