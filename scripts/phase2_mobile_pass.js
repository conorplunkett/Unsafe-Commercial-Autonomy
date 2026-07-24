// Mobile pass for the Phase 2 web survey: walks every screen at 390x844
// (iPhone-class viewport) in TEST_MODE, asserts no horizontal overflow
// anywhere, reports the smallest tap target, and screenshots representative
// screens (intro, context, illustrated item, also-acceptable, attention,
// demographics).
//
// Usage: node scripts/phase2_mobile_pass.js [outdir] [path/to/phase2-survey.html]
// Needs playwright-core (npm i --no-save playwright-core) and a Chromium
// binary (override with PHASE2_CHROME=/path/to/chrome).
const { chromium } = require("playwright-core");
const fs = require("fs");
const path = require("path");

const CHROME = process.env.PHASE2_CHROME || "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";
const OUT = process.argv[2] || "/tmp/phase2-mobile";
const FILE = "file://" + path.resolve(process.argv[3] || "web/public/phase2-survey.html") + "?test=1";
const SITUATIONS = 50;

function fail(msg) { console.error("FAIL: " + msg); process.exit(1); }

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch({ executablePath: CHROME, headless: true });
  const page = await browser.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
  await page.goto(FILE);

  const overflows = [];
  async function checkOverflow(where) {
    const r = await page.evaluate(() => {
      const doc = document.documentElement;
      if (doc.scrollWidth <= doc.clientWidth + 1) return null;
      const over = [];
      document.querySelectorAll("body *").forEach(el => {
        const rect = el.getBoundingClientRect();
        if (rect.right > doc.clientWidth + 1 || rect.left < -1) {
          const cls = el.className && el.className.baseVal !== undefined ? el.className.baseVal : el.className || "";
          over.push(el.tagName + "." + cls + " right=" + Math.round(rect.right) + " left=" + Math.round(rect.left));
        }
      });
      return { sw: doc.scrollWidth, cw: doc.clientWidth, over: over.slice(0, 6) };
    });
    if (r) overflows.push(`${where}: scrollWidth ${r.sw} > ${r.cw}\n    ` + r.over.join("\n    "));
  }

  let minTap = Infinity;
  async function checkTaps() {
    const h = await page.evaluate(() =>
      Math.min(...[...document.querySelectorAll(".opt, button:not([disabled])")].filter(e => e.offsetParent && !e.closest("#testjump")).map(e => e.getBoundingClientRect().height), Infinity)
    );
    if (h < minTap) minTap = h;
  }

  await checkOverflow("intro");
  await page.screenshot({ path: OUT + "/m1-intro.png", fullPage: true });
  await page.click("#start");

  const shots = { context: false, illoItem: false, also: false, attention: false, demo: false };
  let situations = 0;

  for (let guard = 0; guard < 200; guard++) {
    const h1 = await page.$("h1");
    if (h1 && (await h1.textContent()).includes("Test run complete")) break;
    const label = await page.$(".step-label");
    const labelText = label ? (await label.textContent()).trim() : "";

    if (labelText.startsWith("Part ")) {
      await checkOverflow(labelText);
      if (!shots.context) { await page.screenshot({ path: OUT + "/m2-context.png", fullPage: true }); shots.context = true; }
      await page.click("#next");
      continue;
    }
    if (labelText.startsWith("Situation ")) {
      situations++;
      await checkOverflow(labelText);
      await checkTaps();
      const hasIllo = !!(await page.$(".illo svg"));
      const nOpts = (await page.$$(".opt[data-key]")).length;
      const isAtt = (await page.textContent(".card")).includes("reading carefully");
      if (hasIllo && nOpts === 4 && !shots.illoItem) { await page.screenshot({ path: OUT + "/m3-item-illustrated.png", fullPage: true }); shots.illoItem = true; }
      if (isAtt && !shots.attention) { await page.screenshot({ path: OUT + "/m5-attention.png", fullPage: true }); shots.attention = true; }
      await page.click(".opt[data-key]");
      const alsoNone = await page.$(".opt[data-also='__none__']");
      if (alsoNone) {
        await checkOverflow(labelText + " (also-acceptable)");
        if (!shots.also) { await page.screenshot({ path: OUT + "/m4-also-acceptable.png", fullPage: true }); shots.also = true; }
        await alsoNone.click();
      }
      await page.click("#next");
      continue;
    }
    if (labelText.startsWith("Last few questions")) {
      await checkOverflow(labelText);
      await checkTaps();
      if (!shots.demo) { await page.screenshot({ path: OUT + "/m6-demographics.png", fullPage: true }); shots.demo = true; }
      await page.click(".opt[data-key]");
      await page.click("#next");
      continue;
    }
    fail("unrecognized step; label=" + labelText);
  }

  await page.waitForSelector("h1:has-text('Test run complete')");
  await checkOverflow("done");

  if (situations !== SITUATIONS) fail("walked " + situations + ` situations, expected ${SITUATIONS}`);
  if (overflows.length) fail("horizontal overflow on " + overflows.length + " step(s):\n  " + overflows.join("\n  "));
  console.log(`MOBILE PASS OK: ${SITUATIONS} situations + intro/context/demographics/done at 390px, no horizontal overflow`);
  console.log("min tap-target height:", Math.round(minTap) + "px");
  console.log("screenshots in", OUT);
  await browser.close();
})().catch(e => { console.error("FAIL:", e); process.exit(1); });
