// Headless desktop walkthrough of the Phase 2 web survey in TEST_MODE.
// Walks intro -> 5 context parts -> 50 situations -> 5 demographic steps ->
// done, and asserts structure and the final payload shape. Nothing is
// written: ?test=1 short-circuits submission.
//
// Usage: node scripts/phase2_walkthrough.js [path/to/survey.html]
// Needs playwright-core (npm i --no-save playwright-core) and a Chromium
// binary (override with PHASE2_CHROME=/path/to/chrome).
const { chromium } = require("playwright-core");
const path = require("path");

const CHROME = process.env.PHASE2_CHROME || "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";
const FILE = "file://" + path.resolve(process.argv[2] || "web/public/survey.html") + "?test=1";

// Instrument constants, kept in one place so a redesign updates one block.
const SITUATIONS = 50;
const SCENARIOS = 44;
const PARTS = 5;
const DEMOGRAPHICS = 5;
const ILLUSTRATED = 33;      // everything except the 5 attention checks and the 12 mockup-exempt items
const ATTENTION_IDS = ["att_1", "att_2", "att_3", "att_4", "att_5"];

function fail(msg) { console.error("FAIL: " + msg); process.exit(1); }

(async () => {
  const browser = await chromium.launch({ executablePath: CHROME, headless: true });
  const page = await browser.newPage();
  let payload = null;
  page.on("console", async (msg) => {
    if (msg.text().startsWith("TEST MODE")) {
      const arg = msg.args()[1];
      if (arg) payload = await arg.jsonValue();
    }
  });
  await page.goto(FILE);

  if (!(await page.textContent("h1")).includes("Help build an AI safety benchmark")) fail("intro missing");
  if (!(await page.textContent(".card")).includes(`${SITUATIONS} short situations`)) fail(`intro count is not ${SITUATIONS}`);
  await page.click("#start");

  const seenParts = [];
  const seenSituations = [];
  const alsoSeen = { shown: 0, skipped: 0 };
  const illoSeen = { with: 0, without: 0 };
  let demoSeen = 0;

  for (let guard = 0; guard < 200; guard++) {
    const h1 = await page.$("h1");
    if (h1 && (await h1.textContent()).includes("Test run complete")) break;
    const label = await page.$(".step-label");
    const h2 = await page.$("h2");
    const labelText = label ? (await label.textContent()).trim() : "";

    if (labelText.startsWith("Part ")) {
      seenParts.push((await h2.textContent()).trim());
      await page.click("#next");
      continue;
    }
    if (labelText.startsWith("Situation ")) {
      const m = labelText.match(/^Situation (\d+) of (\d+)$/);
      if (!m) fail("bad situation label: " + labelText);
      if (Number(m[2]) !== SITUATIONS) fail("situation denominator is " + m[2]);
      seenSituations.push(Number(m[1]));
      if (await page.$(".illo svg")) illoSeen.with++; else illoSeen.without++;
      if (!(await page.isDisabled("#next"))) fail("Next enabled before selection at " + labelText);
      await page.click(".opt[data-key]"); // first (shuffled) option
      const alsoNone = await page.$(".opt[data-also='__none__']");
      if (alsoNone) {
        alsoSeen.shown++;
        if (!(await page.isDisabled("#next"))) fail("Next enabled before also-acceptable at " + labelText);
        await alsoNone.click();
      } else {
        alsoSeen.skipped++;
      }
      if (await page.isDisabled("#next")) fail("Next still disabled after answering at " + labelText);
      await page.click("#next");
      continue;
    }
    if (labelText.startsWith("Last few questions")) {
      demoSeen++;
      if (!(await page.isDisabled("#next"))) fail("demographics Next enabled before selection at " + labelText);
      await page.click(".opt[data-key]");
      if (await page.isDisabled("#next")) fail("demographics Next still disabled after answering at " + labelText);
      await page.click("#next");
      continue;
    }
    fail("unrecognized step; label=" + labelText);
  }

  await page.waitForSelector("h1:has-text('Test run complete')");

  if (seenParts.length !== PARTS) fail(`expected ${PARTS} context parts, saw ` + seenParts.length + ": " + seenParts.join(" | "));
  if (seenSituations.length !== SITUATIONS) fail(`expected ${SITUATIONS} situations, saw ` + seenSituations.length);
  if (!seenSituations.every((n, i) => n === i + 1)) fail("situation numbering not sequential: " + seenSituations.join(","));
  if (alsoSeen.shown !== SCENARIOS || alsoSeen.skipped !== SITUATIONS - SCENARIOS) fail(`also-acceptable shown/skipped = ${alsoSeen.shown}/${alsoSeen.skipped}`);
  if (demoSeen !== DEMOGRAPHICS) fail(`expected ${DEMOGRAPHICS} demographic questions, saw ` + demoSeen);
  if (illoSeen.with !== ILLUSTRATED) fail(`illustrations with/without = ${illoSeen.with}/${illoSeen.without}, expected ${ILLUSTRATED}/${SITUATIONS - ILLUSTRATED}`);

  if (!payload) fail("no TEST MODE payload captured");
  const votes = Object.keys(payload.votes || {});
  if (votes.length !== SCENARIOS) fail("payload votes count " + votes.length);
  if (votes.some(id => !id.startsWith("scn_v2_"))) fail("non-scenario id in votes");
  const slotSet = new Set(["proceed_trap", "proceed_safe", "ask_approval", "refuse"]);
  for (const [id, v] of Object.entries(payload.votes)) if (!slotSet.has(v)) fail(`vote ${id}=${v} not a slot key`);
  if (Object.keys(payload.also_acceptable || {}).length !== SCENARIOS) fail("also_acceptable count wrong");
  for (const attId of ATTENTION_IDS) {
    if (!payload.attention || !payload.attention[attId] || typeof payload.attention[attId].passed !== "boolean") fail(`attention.${attId} malformed`);
  }
  if (!payload.industry) fail("industry missing from payload");
  if (!payload.meta || payload.meta.survey_version !== "v2_web_r3") fail("survey_version wrong: " + (payload.meta || {}).survey_version);
  if (!payload.meta.calibration || !("cal_1" in payload.meta.calibration)) fail("meta.calibration.cal_1 missing");
  if (!Array.isArray(payload.question_order) || payload.question_order.length !== SITUATIONS) fail("question_order length wrong");
  const batchFlat = (payload.meta.batches || []).flatMap(b => b.question_ids);
  if (JSON.stringify(batchFlat) !== JSON.stringify(payload.question_order)) fail("meta.batches does not concatenate to question_order");
  if (payload.meta.batches.length !== PARTS) fail("meta.batches length wrong");

  console.log("WALKTHROUGH OK");
  console.log("parts:", seenParts.join(" | "));
  console.log("illustrations:", illoSeen.with, "with /", illoSeen.without, "without");
  console.log(`votes: ${SCENARIOS} slot-keyed; attention: ${ATTENTION_IDS.join(",")}; industry:`, payload.industry, "; version:", payload.meta.survey_version);
  await browser.close();
})().catch(e => { console.error("FAIL:", e); process.exit(1); });
