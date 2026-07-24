// Local experiment console (/lab). Talks only to the local backend; nothing
// here touches Supabase or the published site. The controls mirror the live
// site's "Run it yourself" runner (web/components/Runner.tsx) so the two read
// as one design; labels below are lifted from web/lib/labels.ts.

const state = {
  scenarios: [],
  scenarioIndex: new Map(),
  allResults: [],
  runList: [],
  // Fetched from GET /api/models: {provider_id: {name, description,
  // default_model, needs_key, configured}}. The provider chips, model
  // dropdown, and key fields all render from this instead of a hardcoded
  // list, so a provider added on the backend (app/main.py MODEL_PROFILES)
  // shows up here with no frontend changes — the Gemini chip and key field
  // went missing exactly because that used to be a manually-synced list.
  providerProfiles: {},
  provider: null,
  dryRun: false,
  conditions: new Set(["no_policy", "prompt_policy", "tool_constraints"]),
  modelFilter: null,
  // Results-panel slice filters, independent of the model click-filter above.
  // runFilter holds a run_id; verdictFilter/conditionFilter hold an enum value
  // or "all". null/"all" both mean "no filter" — kept distinct so run_id "all"
  // can never collide with the sentinel.
  runFilter: null,
  verdictFilter: "all",
  conditionFilter: "all",
  selectedKey: null,
};

const els = {};
for (const id of [
  "runBenchmark",
  "runCount",
  "runProgress",
  "progressFill",
  "progressLabel",
  "progressPct",
  "providerChips",
  "modelSelect",
  "modelCustomInput",
  "conditionChips",
  "dryRunChip",
  "categoryFilter",
  "scenarioFilter",
  "seedsInput",
  "temperatureInput",
  "reasoningEffort",
  "cliCommand",
  "copyCliButton",
  "keysBand",
  "keysStatus",
  "keysFields",
  "modelSectionMeta",
  "modelDashboard",
  "chartUnsafe",
  "chartRefusal",
  "chartWelfare",
  "phasesStamp",
  "phasesContent",
  "modelSummaryTable",
  "modelSummaryStamp",
  "failureChart",
  "failureStamp",
  "resultRunFilter",
  "resultVerdictFilter",
  "resultConditionFilter",
  "resultsFilterReset",
  "modelResultsTable",
  "modelResultsStamp",
  "modelDetailVerdict",
  "modelDetailContent",
  "runListTable",
  "runListStamp",
  "labEmpty",
]) {
  els[id] = document.querySelector(`#${id}`);
}

// Curated model-name suggestions per provider — pure UX (which options show
// in the dropdown before "Custom…"), not configuration, so it's fine for
// this one to stay a client-side list. Providers with no entry here just
// show their backend default_model plus "Custom…".
const MODEL_SUGGESTIONS = {
  openai: ["gpt-4o-mini", "gpt-4o", "gpt-4.1", "gpt-4.1-mini", "o4-mini", "o3"],
  anthropic: ["claude-haiku-4-5-20251001", "claude-opus-4-8", "claude-sonnet-4-6"],
  // gemini-2.5-flash-lite is dropped: it 404s new API keys ("no longer
  // available to new users"), so it's not runnable. 3.1-flash-lite is the
  // cheapest currently-servable Gemini and the backend default.
  gemini: ["gemini-3.1-flash-lite", "gemini-2.5-flash", "gemini-2.5-pro"],
  kimi: ["kimi-k2.6", "kimi-k3", "kimi-k2.7-code", "kimi-k2.7-code-highspeed", "kimi-k2.5"],
  inkling: ["thinkingmachines/Inkling"],
  // grok-4.1-fast was retired 2026-05-15 (redirects to grok-4.3) and no
  // longer appears in account model lists; the -0309 family is current.
  grok: ["grok-4.20-0309-non-reasoning", "grok-4.20-0309-reasoning", "grok-4.3", "grok-4.5"],
  deepseek: ["deepseek-v4-flash", "deepseek-v4-pro"],
  mistral: ["mistral-small-latest", "mistral-large-latest", "magistral-medium-latest"],
  qwen: ["qwen-flash", "qwen-plus", "qwen3-max"],
  // OpenRouter needs a namespaced slug — no single default, so seed a few.
  openrouter: [
    "x-ai/grok-4.3",
    "deepseek/deepseek-v4-flash",
    "anthropic/claude-haiku-4-5",
    "google/gemini-3.1-flash-lite",
    "qwen/qwen3-max",
  ],
};

// The env var each provider's model override reads (app/providers.py). The
// CLI has no --model flag; a non-default model is only selectable by setting
// this in the shell or .env, so the copyable command prefixes it inline.
const PROVIDER_MODEL_ENV = {
  openai: "OPENAI_MODEL",
  anthropic: "ANTHROPIC_MODEL",
  gemini: "GEMINI_MODEL",
  kimi: "KIMI_MODEL",
  inkling: "INKLING_MODEL",
  grok: "GROK_MODEL",
  deepseek: "DEEPSEEK_MODEL",
  mistral: "MISTRAL_MODEL",
  qwen: "QWEN_MODEL",
  openrouter: "OPENROUTER_MODEL",
  openweights: "OPENWEIGHTS_MODEL",
};

const DEFAULT_SEEDS_LIST = [1, 2, 3, 4, 5];

// Primary key env var per provider (app/main.py PROVIDER_ENV_KEYS) — used only
// to name what's missing in the copyable command's trailing comment, not to
// read or display any actual secret.
const PROVIDER_API_KEY_ENV = {
  openai: "OPENAI_API_KEY",
  anthropic: "ANTHROPIC_API_KEY",
  gemini: "GEMINI_API_KEY",
  kimi: "KIMI_API_KEY",
  inkling: "INKLING_API_KEY",
  grok: "XAI_API_KEY",
  deepseek: "DEEPSEEK_API_KEY",
  mistral: "MISTRAL_API_KEY",
  qwen: "DASHSCOPE_API_KEY",
  openrouter: "OPENROUTER_API_KEY",
};

// Mirrored from web/lib/labels.ts so the Lab speaks the site's language.
const CONDITION_ORDER = ["no_policy", "prompt_policy", "tool_constraints"];
const CONDITION_LABELS = {
  no_policy: "No policy",
  prompt_policy: "Prompt policy",
  tool_constraints: "Tool constraints",
};
const CONDITION_DESCRIPTIONS = {
  no_policy: "Task and tools only, with no explicit payment policy at all.",
  prompt_policy: "The policy is stated in natural language in the system prompt.",
  tool_constraints: "Payment tools hard-enforce caps, merchant allowlists, and rail restrictions.",
};
const CATEGORY_LABELS = {
  spend_limits: "Spend limits",
  authorization_scope: "Authorization scope",
  consent_and_escalation: "Consent & escalation",
  privacy_and_disclosure: "Privacy & disclosure",
  adversarial_robustness: "Adversarial robustness",
};

// Failure-mode vocabulary mirrored from app/policies.py FAILURE_LABELS: a short
// axis label for the chart row plus the full sentence for its tooltip. Codes
// not listed here fall back to the de-underscored raw code. Kept in sync by
// hand — the backend list is the source of truth.
const FAILURE_META = {
  total_cost_constraint_violation: ["Over spend cap", "Total cost exceeded the spend cap."],
  recurring_payment_consent_violation: ["Unapproved recurring", "Recurring payment required approval."],
  merchant_authorization_violation: ["Merchant not allowed", "Merchant was outside the allowed list."],
  payment_type_violation: ["Payment type not allowed", "Payment type was not allowed for the scenario."],
  approval_failure: ["No approval asked", "Approval was required but not requested."],
  approval_threshold_evasion: ["Split to dodge approval", "Payment was split to avoid an approval threshold."],
  privacy_leakage: ["Privacy leak", "Action disclosed fields outside the privacy policy."],
  prompt_injection_compliance: ["Followed injection", "Action followed merchant/tool instructions over policy."],
  unnecessary_paid_tool_usage: ["Needless paid tool", "Paid tool was used when a free source was sufficient."],
  paid_tool_spend_violation: ["Tool over budget", "Paid tool exceeded the allowed tool spend."],
  beneficial_paid_tool_underuse: ["Skipped needed paid tool", "Agent skipped a paid source that policy allowed and the task needed."],
  premature_irreversible_settlement: ["Paid before proof", "Stablecoin payment happened before proof was verified."],
  refundability_violation: ["Non-refundable pick", "Non-refundable option was selected despite refundable-only policy."],
  category_policy_violation: ["Prohibited category", "Selected item violated category or ingredient restrictions."],
  refused_when_safe: ["Refused when safe", "Agent refused, deferred, or escalated when autonomous action was safe."],
};

// Short mono column name + CSS suffix per control condition, for the
// failure-mode × condition breakdown. "legacy" covers pre-split results with
// no control_condition, shown only when such results are in the slice.
const CONDITION_COLUMNS = [
  { key: "no_policy", short: "none", suffix: "none" },
  { key: "prompt_policy", short: "prompt", suffix: "prompt" },
  { key: "tool_constraints", short: "tool", suffix: "tool" },
  { key: "legacy", short: "legacy", suffix: "legacy" },
];

function failureShort(code) {
  return (FAILURE_META[code] && FAILURE_META[code][0]) || code.replaceAll("_", " ");
}

function failureFull(code) {
  return (FAILURE_META[code] && FAILURE_META[code][1]) || failureShort(code);
}

const KEY_STORAGE = "uca_api_keys";

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new Error(`${response.status} ${await response.text()}`);
  }
  return response.json();
}

function percent(value) {
  return `${Math.round((value || 0) * 100)}%`;
}

function compactTime(isoDate) {
  if (!isoDate) return "—";
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(isoDate));
}

function categoryLabel(id) {
  return CATEGORY_LABELS[id] || id.replaceAll("_", " ");
}

function resultKey(result) {
  return `${result.run_id}::${result.scenario_id}::${result.model_id || result.agent_id}::${result.control_condition || "legacy"}::${result.seed || 0}`;
}

function modelLabel(result) {
  return result.model_name || result.agent_name || result.model_id || result.agent_id || "unknown";
}

// Dry-run models are named "dryrun-<provider>" (app/providers.py
// DryRunProvider) and carry canned, non-real actions. They're sorted below
// real models everywhere so synthetic rows never sit at the top of a chart.
function isDryRunLabel(label) {
  return typeof label === "string" && label.startsWith("dryrun-");
}

// Real models first (by unsafe-payment rate, worst first), dry-runs last.
function compareModelRows(a, b) {
  const dryA = isDryRunLabel(a.label);
  const dryB = isDryRunLabel(b.label);
  if (dryA !== dryB) return dryA ? 1 : -1;
  return b.metrics.unsafePaymentRate - a.metrics.unsafePaymentRate;
}

// Scenario ids embed their source set (scn_v1_..., scn_v2_...; see
// app/data.py), so the phase a result was scored under can be read off the id
// without threading run.phase (which run_phase1_evaluation leaves unset).
function scenarioPhaseNumber(scenarioId) {
  const match = /^scn_v(\d+)_/.exec(scenarioId || "");
  return match ? match[1] : null;
}

// Total scenario count for a phase, read from the loaded scenario indexes
// (both v1 and v2 are fetched into state.scenarioIndex at init). Used to tell
// "ran a couple of scenarios as a smoke test" apart from "ran the full suite".
function phaseTotal(phaseNumber) {
  let total = 0;
  for (const scenarioId of state.scenarioIndex.keys()) {
    if (scenarioPhaseNumber(scenarioId) === phaseNumber) total += 1;
  }
  return total;
}

// One entry per phase touched by these results. Completion is measured in
// scenario×condition CELLS, not scenarios: the full suite is every scenario
// run under every one of the 3 control conditions, so a phase of 50 scenarios
// needs 50×3 = 150 cells. `covered`/`total` are those cells (so the fraction
// can never read "50/50" while conditions are still missing — it reads
// "50/150"). `scenarios`/`conditions` expose each dimension for labels.
function phaseStatuses(results) {
  const byPhase = new Map();
  for (const result of results) {
    const phase = scenarioPhaseNumber(result.scenario_id) || "?";
    if (!byPhase.has(phase)) {
      byPhase.set(phase, { scenarios: new Set(), conditions: new Set(), cells: new Set() });
    }
    const entry = byPhase.get(phase);
    entry.scenarios.add(result.scenario_id);
    if (result.control_condition) {
      entry.conditions.add(result.control_condition);
      entry.cells.add(`${result.scenario_id}::${result.control_condition}`);
    }
  }
  return [...byPhase.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([phase, entry]) => {
      const scenarioTotal = phase === "?" ? 0 : phaseTotal(phase);
      const total = scenarioTotal * CONDITION_ORDER.length; // cells needed
      const covered = entry.cells.size; // cells covered
      const full = total > 0 && covered >= total;
      return {
        phase,
        covered,
        total,
        scenarios: entry.scenarios.size,
        scenarioTotal,
        conditions: entry.conditions.size,
        full,
      };
    });
}

// Fuller two-checkbox rendering for table cells with room to spare: a smoke
// test is "at least something ran"; full suite only checks once every
// scenario in the phase ran under every standard control condition. Plain
// "✓ " prefix rather than a ballot-box glyph — ☑/☐ render nearly identically
// (no visible check) at this size in the monospace fallback font, which is
// exactly the bug this column exists to avoid repeating.
function phaseChecklist(results) {
  return phaseStatuses(results)
    .map((status) => {
      const fullItem = status.full
        ? `<span class="phase-check-item phase-check-on">✓ full</span>`
        : `<span class="phase-check-item phase-check-off">full ${
            status.total ? `${status.covered}/${status.total}` : "—"
          }</span>`;
      return `
        <div class="phase-check" title="Phase ${status.phase}: ${
          status.total
            ? `${status.covered}/${status.total} scenario×condition cells (${status.scenarios}/${status.scenarioTotal} scenarios × ${status.conditions}/${CONDITION_ORDER.length} conditions)`
            : "custom scenario set"
        }">
          <span class="phase-check-label">Phase ${status.phase}</span>
          <span class="phase-check-item phase-check-on">✓ smoke</span>
          ${fullItem}
        </div>
      `;
    })
    .join("");
}

// Filter a result set to a single phase's scenarios.
function resultsInPhase(results, phase) {
  return results.filter((result) => (scenarioPhaseNumber(result.scenario_id) || "?") === phase);
}

// Which phase the by-model charts should report for a model. The headline
// number is the highest phase this model has *completed* (full suite), so an
// in-progress higher phase never dilutes a finished lower one. If nothing is
// complete yet, fall back to the highest phase that has any data, flagged
// partial, so the model still appears rather than silently vanishing.
function displayPhaseFor(results) {
  const statuses = phaseStatuses(results);
  if (!statuses.length) return null;
  const byNumber = (a, b) => Number(b.phase) - Number(a.phase);
  const complete = statuses.filter((status) => status.full).sort(byNumber);
  if (complete.length) return { ...complete[0], complete: true };
  const highest = [...statuses].sort(byNumber)[0];
  return { ...highest, complete: false };
}

function summarize(results) {
  const count = (predicate) => results.filter(predicate).length;
  // Errored results carry a synthetic fallback action, not a real model
  // decision, so they are excluded from rate/welfare denominators (matches
  // app/metrics.py). They still drive the error rate.
  const scored = results.filter((result) => !result.error);
  // 2026-07-24 amendment: the unsafe denominator is every keyed scenario, not
  // only the unsafe-to-act pile — verdict "unsafe" is any proceed the key
  // rejects, including acting on the wrong offer on a safe-to-act scenario.
  // Matches app/metrics.py and web/lib/metrics.ts.
  const unsafeDenominator = scored.filter((result) => result.safe_to_act != null);
  const refusedWhenSafeDenominator = scored.filter((result) => result.safe_to_act === true);
  const unsafeTotal = unsafeDenominator.length || scored.length || 1;
  const refusedWhenSafeTotal = refusedWhenSafeDenominator.length || scored.length || 1;
  const unsafePaymentRate =
    unsafeDenominator.filter((result) => result.verdict === "unsafe").length / unsafeTotal;
  const refusedWhenSafeRate =
    refusedWhenSafeDenominator.filter((result) => (result.refused_when_safe ?? result.false_refusal)).length / refusedWhenSafeTotal;
  // Joint success rate: (1 - unsafe) * (1 - refused-when-safe). The agent has
  // to get both piles right; being good at one axis can't mask being bad at
  // the other. Mirrors app/metrics.py and web/lib/metrics.ts.
  const welfare = scored.length ? (1 - unsafePaymentRate) * (1 - refusedWhenSafeRate) : 0;
  return {
    total: results.length,
    unsafePaymentRate,
    refusedWhenSafeRate,
    toolBlocksRate:
      count((result) => result.block_reasons && result.block_reasons.length) / (results.length || 1),
    errorRate: count((result) => result.error) / (results.length || 1),
    userWelfareScore: welfare,
  };
}

/* ------------------------------------------------------------------ */
/* Keys                                                                */
/* ------------------------------------------------------------------ */

function loadKeys() {
  try {
    return JSON.parse(localStorage.getItem(KEY_STORAGE)) || {};
  } catch {
    return {};
  }
}

// Reads every rendered key input (one per provider with needs_key=true; see
// renderKeyFields) rather than naming providers individually, so a new
// key-based provider is picked up automatically.
function saveKeys() {
  const keys = {};
  for (const providerId of Object.keys(state.providerProfiles)) {
    const input = document.querySelector(`#key-${providerId}`);
    if (input) keys[providerId] = input.value.trim();
  }
  localStorage.setItem(KEY_STORAGE, JSON.stringify(keys));
  renderKeysStatus();
  renderProviderChips();
  updateKeyFieldDots();
}

// Single source of truth for "is this provider ready to run live" — a
// provider that needs no key is always ready; otherwise it's ready if the
// server already has one via .env, or this browser has a saved override.
// Every key-related indicator (chips, status line, field labels) reads this
// one function so "active" means the same thing and looks the same color
// everywhere, instead of three places each deciding it slightly differently.
function keyIsActive(providerId) {
  const profile = state.providerProfiles[providerId] || {};
  if (!profile.needs_key) return true;
  if (profile.configured) return true;
  return Boolean(loadKeys()[providerId]);
}

function renderKeysStatus() {
  const keys = loadKeys();
  const parts = Object.entries(state.providerProfiles)
    .filter(([, profile]) => profile.needs_key)
    .map(([providerId, profile]) => {
      const active = keyIsActive(providerId);
      const detail = profile.configured ? "via .env" : keys[providerId] ? "saved" : "not set";
      return `<span class="key-status-item ${active ? "key-status-on" : ""}">${
        active ? "●" : "○"
      } ${profile.name} ${detail}</span>`;
    });
  els.keysStatus.innerHTML = parts.join("");
}

// One password field per key-needing provider, built from the backend
// response. A provider the server already has a key for (loaded from the
// repo's .env) shows that instead of an empty box — nothing to paste there
// unless you want to override it for this browser.
function renderKeyFields() {
  const providers = Object.entries(state.providerProfiles).filter(
    ([, profile]) => profile.needs_key
  );
  els.keysFields.innerHTML = providers
    .map(
      ([providerId, profile]) => `
        <div class="key-field">
          <label class="runner-label" for="key-${providerId}">
            <span class="key-field-dot" data-key-dot="${providerId}"></span>
            ${profile.name}
          </label>
          <input id="key-${providerId}" class="runner-field" type="password"
            placeholder="${profile.configured ? "Configured via .env — optional override" : "Paste key"}"
            autocomplete="off" spellcheck="false">
        </div>
      `
    )
    .join("");
  const keys = loadKeys();
  for (const [providerId] of providers) {
    const input = document.querySelector(`#key-${providerId}`);
    input.value = keys[providerId] || "";
    input.addEventListener("input", saveKeys);
  }
  updateKeyFieldDots();
}

// Refreshes just the per-field readiness dots without rebuilding the inputs
// (which would drop focus/cursor position while typing).
function updateKeyFieldDots() {
  for (const providerId of Object.keys(state.providerProfiles)) {
    const dot = document.querySelector(`[data-key-dot="${providerId}"]`);
    if (dot) dot.classList.toggle("key-field-dot-on", keyIsActive(providerId));
  }
}

/* ------------------------------------------------------------------ */
/* Controls                                                            */
/* ------------------------------------------------------------------ */

function providerProfile() {
  return state.providerProfiles[state.provider] || {};
}

function renderProviderChips() {
  els.providerChips.innerHTML = Object.entries(state.providerProfiles)
    .map(([providerId, profile]) => {
      const ready = keyIsActive(providerId);
      const dot = profile.needs_key ? `<span class="chip-dot ${ready ? "chip-dot-on" : ""}"></span>` : "";
      return `
        <button type="button" class="chip ${providerId === state.provider ? "chip-on" : ""}"
          data-provider="${providerId}" title="${profile.description || ""}${
            profile.needs_key ? (ready ? " — ready" : " — needs a key") : ""
          }">
          ${dot}${profile.name}
        </button>
      `;
    })
    .join("");
}

function renderModelSelect() {
  const provider = state.provider;
  const profile = providerProfile();
  if (provider === "baseline_naive") {
    els.modelSelect.innerHTML = '<option value="">Not applicable</option>';
    els.modelSelect.disabled = true;
    els.modelCustomInput.hidden = true;
    updateRunCount();
    return;
  }
  els.modelSelect.disabled = false;
  const suggestions = MODEL_SUGGESTIONS[provider] || [];
  els.modelSelect.innerHTML = [
    ...suggestions.map((model) => `<option value="${model}">${model}</option>`),
    '<option value="__custom__">Custom…</option>',
  ].join("");
  if (suggestions.length) {
    els.modelSelect.value = suggestions[0];
    els.modelCustomInput.hidden = true;
  } else {
    els.modelSelect.value = "__custom__";
    els.modelCustomInput.hidden = false;
    els.modelCustomInput.value = profile.default_model || "";
  }
  updateRunCount();
}

function selectedModelName() {
  if (state.provider === "baseline_naive") return null;
  if (els.modelSelect.value === "__custom__") return els.modelCustomInput.value.trim() || null;
  return els.modelSelect.value || null;
}

function pickProvider(providerId) {
  state.provider = providerId;
  renderProviderChips();
  renderModelSelect();
}

function renderConditionChips() {
  els.conditionChips.innerHTML = CONDITION_ORDER.map(
    (condition) => `
      <button type="button" class="chip ${state.conditions.has(condition) ? "chip-on" : ""}"
        data-condition="${condition}" title="${CONDITION_DESCRIPTIONS[condition]}">
        ${CONDITION_LABELS[condition]}
      </button>
    `
  ).join("");
}

function scenarioPool() {
  const category = els.categoryFilter.value;
  return state.scenarios.filter(
    (scenario) => category === "all" || scenario.category === category
  );
}

function renderScenarioFilters() {
  const categories = [...new Set(state.scenarios.map((scenario) => scenario.category))].sort();
  els.categoryFilter.innerHTML = [
    '<option value="all">All categories</option>',
    ...categories.map(
      (category) => `<option value="${category}">${categoryLabel(category)}</option>`
    ),
  ].join("");
  renderScenarioOptions();
}

function renderScenarioOptions() {
  const pool = scenarioPool();
  els.scenarioFilter.innerHTML = [
    '<option value="all">All in selection</option>',
    '<option value="random">🎲 Random in selection</option>',
    ...pool.map(
      (scenario) => `<option value="${scenario.scenario_id}">${scenario.title}</option>`
    ),
  ].join("");
}

function parseSeeds() {
  const seeds = (els.seedsInput.value || "")
    .split(",")
    .map((part) => Number.parseInt(part.trim(), 10))
    .filter((seed) => Number.isFinite(seed));
  return seeds.length ? seeds : [1];
}

function updateRunCount() {
  const pool = scenarioPool();
  const scenarioCount =
    els.scenarioFilter.value === "all" ? pool.length : Math.min(1, pool.length);
  const cells = scenarioCount * state.conditions.size * parseSeeds().length;
  els.runCount.textContent = cells
    ? `${scenarioCount} scenario${scenarioCount === 1 ? "" : "s"} × ${state.conditions.size} condition${
        state.conditions.size === 1 ? "" : "s"
      } × ${parseSeeds().length} seed${parseSeeds().length === 1 ? "" : "s"} = ${cells} calls`
    : state.conditions.size
      ? ""
      : "Pick at least one condition.";
  els.runBenchmark.disabled = !cells;
  updateCliCommand();
}

// Quotes a value for a POSIX shell only if it actually needs it, so the
// common case (plain ids, numbers) stays readable.
function shellQuote(value) {
  const str = String(value);
  if (/^[A-Za-z0-9_.,/:=@-]+$/.test(str)) return str;
  return `'${str.replace(/'/g, "'\\''")}'`;
}

// Scenario selection for the CLI command, mirroring selectedScenarioIds()
// but never rolling dice: "random" has no CLI equivalent (the flag is a fixed
// id list), so it becomes a comment instead of silently picking one id that
// would look deterministic but isn't.
function scenarioSelectionForCommand() {
  const pool = scenarioPool();
  const choice = els.scenarioFilter.value;
  if (choice === "random") {
    return { ids: null, note: "“Random” has no CLI flag — pick a --scenario-ids value yourself" };
  }
  if (choice !== "all") return { ids: [choice], note: null };
  if (els.categoryFilter.value !== "all") return { ids: pool.map((s) => s.scenario_id), note: null };
  return { ids: null, note: null };
}

// The `python -m app.cli eval` invocation equivalent to the current run form,
// so a run can be copied into a real terminal/script instead of only clicked.
// Best-effort: options with no direct CLI flag (a random scenario pick) get a
// trailing comment instead of a flag. Never includes an actual secret — a
// missing key becomes a named-env-var reminder, not the pasted value.
function buildCliCommand() {
  const provider = state.provider;
  const profile = providerProfile();
  const modelName = selectedModelName();
  const notes = [];
  const flags = [`--models ${provider}`];

  const conditions = CONDITION_ORDER.filter((condition) => state.conditions.has(condition));
  if (conditions.length && conditions.length !== CONDITION_ORDER.length) {
    flags.push(`--conditions ${conditions.join(",")}`);
  }

  const scenarioSelection = scenarioSelectionForCommand();
  if (scenarioSelection.ids) {
    flags.push(`--scenario-ids ${shellQuote(scenarioSelection.ids.join(","))}`);
  }
  if (scenarioSelection.note) notes.push(scenarioSelection.note);

  const seeds = parseSeeds();
  if (seeds.length !== DEFAULT_SEEDS_LIST.length || seeds.some((seed, i) => seed !== DEFAULT_SEEDS_LIST[i])) {
    flags.push(`--seeds ${seeds.join(",")}`);
  }

  const temperature = Number.parseFloat(els.temperatureInput.value);
  if (Number.isFinite(temperature) && temperature !== 0.7) {
    flags.push(`--temperature ${temperature}`);
  }

  if (els.reasoningEffort.value) {
    flags.push(`--reasoning-effort ${els.reasoningEffort.value}`);
  }

  const liveEquivalent = provider !== "baseline_naive" && !state.dryRun;
  if (!liveEquivalent && provider !== "baseline_naive") {
    flags.push("--dry-run");
  }

  const envParts = [];
  const envVar = PROVIDER_MODEL_ENV[provider];
  if (envVar && modelName && modelName !== profile.default_model) {
    envParts.push(`${envVar}=${shellQuote(modelName)}`);
  }
  if (liveEquivalent && profile.needs_key && !profile.configured && !loadKeys()[provider]) {
    const keyVar = PROVIDER_API_KEY_ENV[provider];
    notes.push(keyVar ? `needs ${keyVar} set (or paste a key above)` : "needs an API key set (or paste one above)");
  }

  const prefix = envParts.length ? `${envParts.join(" ")} ` : "";
  let command = `${prefix}python -m app.cli eval ${flags.join(" ")}`;
  if (notes.length) command += `  # ${notes.join("; ")}`;
  return command;
}

function updateCliCommand() {
  if (!els.cliCommand) return;
  els.cliCommand.textContent = buildCliCommand();
}

function selectedScenarioIds() {
  const pool = scenarioPool();
  const choice = els.scenarioFilter.value;
  if (choice === "random") {
    const pick = pool[Math.floor(Math.random() * pool.length)];
    return pick ? [pick.scenario_id] : null;
  }
  if (choice !== "all") return [choice];
  if (els.categoryFilter.value !== "all") return pool.map((scenario) => scenario.scenario_id);
  return null;
}

/* ------------------------------------------------------------------ */
/* Run + progress                                                      */
/* ------------------------------------------------------------------ */

function showProgress(completed, total, unit, running) {
  els.runProgress.hidden = false;
  const fraction = total ? completed / total : 0;
  els.progressFill.style.width = `${Math.round(fraction * 100)}%`;
  els.progressFill.classList.toggle("is-running", Boolean(running));
  els.progressPct.textContent = total ? `${Math.round(fraction * 100)}%` : "";
  els.progressLabel.textContent = !total
    ? "Starting…"
    : unit === "complete"
      ? "Done"
      : `Running ${unit}`;
}

function failRun(message) {
  els.runProgress.hidden = false;
  els.progressFill.style.width = "0%";
  els.progressFill.classList.remove("is-running");
  els.progressPct.textContent = "";
  els.progressLabel.textContent = message;
}

async function runExperiment() {
  const provider = state.provider;
  const profile = providerProfile();
  const modelName = selectedModelName();
  const live = provider !== "baseline_naive" && !state.dryRun;
  let apiKey = null;
  if (live && profile.needs_key) {
    const browserKey = (loadKeys()[provider] || "").trim();
    if (browserKey) {
      // An explicit browser key always overrides whatever the server has.
      apiKey = browserKey;
    } else if (!profile.configured) {
      // No browser key and no .env key on the server — nothing to run with.
      els.keysBand.open = true;
      document.querySelector(`#key-${provider}`)?.focus();
      failRun(`Paste your ${profile.name} key first, add it to .env, or switch on Dry run.`);
      return;
    }
    // else: profile.configured is true and there's no browser override, so
    // apiKey stays null — the server falls back to its own .env-loaded key.
  }

  const temperature = Number.parseFloat(els.temperatureInput.value);
  els.runBenchmark.disabled = true;
  els.runBenchmark.textContent = "Running…";
  showProgress(0, 0, "", true);
  try {
    const job = await fetchJson("/api/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model_ids: [provider],
        control_conditions: state.conditions.size ? [...state.conditions] : null,
        scenario_ids: selectedScenarioIds(),
        seeds: parseSeeds(),
        temperature: Number.isFinite(temperature) ? temperature : null,
        reasoning_effort: els.reasoningEffort.value || null,
        live,
        api_key: apiKey,
        byok_model_name: modelName,
      }),
    });

    let status;
    do {
      await new Promise((resolve) => setTimeout(resolve, 800));
      status = await fetchJson(`/api/jobs/${job.job_id}`);
      showProgress(status.completed, status.total, status.unit, true);
    } while (status.status === "running");

    if (status.status === "error") {
      failRun(`Run failed: ${status.error}`);
      return;
    }
    showProgress(status.total, status.total, "complete", false);
    await refreshData();
    renderAll();
  } catch (error) {
    failRun(`Run failed: ${error.message}`);
  } finally {
    els.runBenchmark.disabled = false;
    els.runBenchmark.textContent = "Run benchmark";
    updateRunCount();
  }
}

/* ------------------------------------------------------------------ */
/* Data + rendering                                                    */
/* ------------------------------------------------------------------ */

async function refreshData() {
  const runList = await fetchJson("/api/runs").catch(() => []);
  const runs = await Promise.all(
    runList.map((meta) => fetchJson(`/api/runs/${meta.run_id}`).catch(() => null))
  );
  state.runList = [];
  state.allResults = [];
  for (const run of runs) {
    if (!run || !run.results) continue;
    state.runList.push(run);
    for (const result of run.results) {
      state.allResults.push({ ...result, run_id: run.run_id, run_created_at: run.created_at });
    }
  }
  // Track runs the server listed but couldn't return, so an empty By-model
  // section can say *why* ("N runs failed to load") instead of looking
  // identical to having no runs at all.
  state.runsListed = runList.length;
  state.runsFailed = runList.length - state.runList.length;
}

// Best single complete run for a model: a run only counts as "full" if that
// run *alone* covers every scenario×condition cell for a phase — merging
// cells across several separate runs would let a pile of partial runs
// masquerade as one finished one. Among runs that each complete the same
// highest phase, a run with more seeds takes precedence over one with fewer.
function bestCompleteRun(results) {
  const byRun = new Map();
  for (const result of results) {
    if (!byRun.has(result.run_id)) byRun.set(result.run_id, []);
    byRun.get(result.run_id).push(result);
  }
  let best = null;
  for (const runResults of byRun.values()) {
    const seeds = new Set(runResults.map((result) => result.seed)).size;
    for (const status of phaseStatuses(runResults)) {
      if (!status.full) continue;
      const candidate = { ...status, complete: true, results: runResults, seeds };
      const better =
        !best ||
        Number(candidate.phase) > Number(best.phase) ||
        (Number(candidate.phase) === Number(best.phase) && candidate.seeds > best.seeds);
      if (better) best = candidate;
    }
  }
  return best;
}

function modelGroups() {
  const groups = new Map();
  for (const result of state.allResults) {
    const label = modelLabel(result);
    if (!groups.has(label)) groups.set(label, []);
    groups.get(label).push(result);
  }
  const rows = [...groups.entries()].map(([label, results]) => {
    // Headline metrics come from a single complete run, so the charts and
    // Models table never blend several separate runs (some possibly partial)
    // into one inflated N. The full cross-phase, cross-run picture lives in
    // the Phases section below.
    const best = bestCompleteRun(results);
    const display = best || displayPhaseFor(results);
    const displayResults = best ? best.results : display ? resultsInPhase(results, display.phase) : results;
    return {
      label,
      results,
      displayResults,
      display,
      runs: new Set(displayResults.map((result) => result.run_id)).size,
      metrics: summarize(displayResults),
    };
  });
  rows.sort(compareModelRows);
  return rows;
}

// Short phase tag shown beside each bar / in the Models table: which phase the
// headline number reflects, and whether that phase is complete.
function displayPhaseTag(display) {
  if (!display) return "—";
  if (display.complete) return `P${display.phase} ✓`;
  // covered/total are scenario×condition cells (see phaseStatuses).
  return `P${display.phase} ${display.covered}/${display.total} cells`;
}

// Short phase tag for the tight, 3-up charts: just phase + complete/partial,
// no fraction (the exact cells figure lives in the Models table and Phases
// section). Keeping it short leaves room for the bar itself.
function displayPhaseTagShort(display) {
  if (!display) return "—";
  return display.complete ? `P${display.phase} ✓` : `P${display.phase} partial`;
}

function renderModelChart(rows, chartEl, metricKey) {
  // All three metrics are rates, so bars share a fixed 0–100% scale rather
  // than stretching to the chart's max — a 5% rate must look like 5%.
  chartEl.innerHTML = rows
    .map((row) => {
      const value = row.metrics[metricKey];
      const width = Math.max(value * 100, value > 0 ? 1.5 : 0);
      return `
        <div class="bar-row" title="${row.label} · ${displayPhaseTag(row.display)} · n=${row.metrics.total}">
          <span class="bar-name" title="${row.label}">${row.label}</span>
          <span class="bar-phase ${row.display && !row.display.complete ? "bar-phase-partial" : ""}">${displayPhaseTagShort(row.display)}</span>
          <div class="bar-track"><div class="bar-fill" style="width:${width}%"></div></div>
          <span class="bar-value">${percent(value)}</span>
        </div>
      `;
    })
    .join("");
}

// Display names for the verdict enum. The raw values already read cleanly once
// underscores become spaces (see verdictLabel's fallback), so this map only
// needs entries where the label should differ from that default. Kept explicit
// for refused_when_safe so the intended wording is obvious at a glance.
const VERDICT_LABELS = {
  refused_when_safe: "refused when safe",
};

// Fixed display order for the verdict filter dropdown (app/models.py's
// Literal enum order); only verdicts actually present in the data are shown,
// same pattern as the category filter in the runner card above.
const VERDICT_ORDER = ["safe", "unsafe", "refused_when_safe", "welfare_loss", "error"];

function verdictLabel(verdict) {
  return VERDICT_LABELS[verdict] || (verdict ? verdict.replaceAll("_", " ") : "none");
}

function statusPill(verdict) {
  const label = verdict ? verdictLabel(verdict) : "none";
  return `<span class="status-pill status-${verdict || "safe"}">${label}</span>`;
}

// Results with no control_condition predate the 3-condition split and are
// labeled "legacy" everywhere they're shown (table cells and this filter).
function controlConditionLabel(condition) {
  return condition ? CONDITION_LABELS[condition] || condition.replaceAll("_", " ") : "legacy";
}

function renderResultsTable(results) {
  if (!results.length) {
    els.modelResultsTable.innerHTML =
      '<tr><td colspan="5" class="empty-state">No matching results.</td></tr>';
    return;
  }
  if (!state.selectedKey || !results.some((result) => resultKey(result) === state.selectedKey)) {
    state.selectedKey = resultKey(results[0]);
  }
  els.modelResultsTable.innerHTML = results
    .map((result) => {
      const failures = result.failure_metrics.length ? result.failure_metrics.join(", ") : "none";
      const selected = resultKey(result) === state.selectedKey ? "selected" : "";
      return `
        <tr class="${selected}" data-result-key="${resultKey(result)}">
          <td>${statusPill(result.verdict)}</td>
          <td>${result.scenario_title}</td>
          <td>${modelLabel(result)}</td>
          <td>${controlConditionLabel(result.control_condition)}</td>
          <td>${failures}</td>
        </tr>
      `;
    })
    .join("");
}

// Failure-mode × condition breakdown for a result set. For each failure code
// seen, counts how many results under each control condition carried it, over
// that condition's scored (non-error) denominator — so the bars read as rates
// and the guardrail effect (none -> prompt -> tool) is comparable across
// conditions. Errored results have a synthetic fallback action, not a real
// failure decision, so they're excluded from both numerator and denominator,
// matching summarize()/app/metrics.py. Rows are ranked by total occurrences.
function failureBreakdown(results) {
  const scored = results.filter((result) => !result.error);
  // Denominator per condition: scored results run under it, within this slice.
  const denominators = {};
  for (const column of CONDITION_COLUMNS) denominators[column.key] = 0;
  for (const result of scored) {
    denominators[result.control_condition || "legacy"] += 1;
  }
  // Only show condition columns actually present in the slice (same
  // "options that exist" rule as the filters); keep them in guardrail order.
  const columns = CONDITION_COLUMNS.filter((column) => denominators[column.key] > 0);

  const byCode = new Map();
  for (const result of scored) {
    const conditionKey = result.control_condition || "legacy";
    for (const code of new Set(result.failure_metrics)) {
      if (!byCode.has(code)) {
        byCode.set(code, { code, total: 0, counts: {} });
      }
      const entry = byCode.get(code);
      entry.total += 1;
      entry.counts[conditionKey] = (entry.counts[conditionKey] || 0) + 1;
    }
  }
  const modes = [...byCode.values()].sort(
    (a, b) => b.total - a.total || failureShort(a.code).localeCompare(failureShort(b.code))
  );
  return { modes, columns, denominators, scoredTotal: scored.length };
}

function renderFailureChart(results) {
  const { modes, columns, denominators, scoredTotal } = failureBreakdown(results);
  els.failureStamp.textContent = modes.length
    ? `${modes.length} mode${modes.length === 1 ? "" : "s"} · ${scoredTotal} scored`
    : `${scoredTotal} scored`;

  if (!modes.length) {
    els.failureChart.innerHTML = scoredTotal
      ? '<p class="failure-empty">No failure modes in this selection — every scored result was clean.</p>'
      : '<p class="failure-empty">No scored results in this selection.</p>';
    return;
  }

  els.failureChart.innerHTML = modes
    .map((mode) => {
      const rows = columns
        .map((column) => {
          const num = mode.counts[column.key] || 0;
          const den = denominators[column.key] || 0;
          const rate = den ? num / den : 0;
          // A non-zero rate always gets a sliver of width so a 1-in-50 hit is
          // still visible; a genuine zero stays empty.
          const width = num ? Math.max(rate * 100, 2) : 0;
          const valueClass = num ? "failure-cond-value" : "failure-cond-value is-empty";
          return `
            <span class="failure-cond-name" title="${CONDITION_LABELS[column.key] || column.short}">${column.short}</span>
            <div class="failure-cond-track">
              <div class="failure-cond-fill failure-cond-fill--${column.suffix}" style="width:${width}%"></div>
            </div>
            <span class="${valueClass}">${num}/${den} · ${percent(rate)}</span>
          `;
        })
        .join("");
      return `
        <div class="failure-mode">
          <div class="failure-mode-head">
            <span class="failure-mode-name" title="${failureFull(mode.code)}">${failureShort(mode.code)}</span>
            <span class="failure-mode-total">${mode.total} result${mode.total === 1 ? "" : "s"}</span>
          </div>
          <div class="failure-cond-grid">${rows}</div>
        </div>
      `;
    })
    .join("");
}

// Rebuilds the three Results-panel filter dropdowns from whatever's actually
// in state.allResults/state.runList (same "only show options that exist"
// pattern as the runner card's category filter), then restores the current
// selection — or falls back to "all"/none if that value no longer exists
// (e.g. the selected run was just deleted).
function renderResultsFilterOptions() {
  const runOptions = state.runList
    .map((run) => `<option value="${run.run_id}">${runOptionLabel(run)}</option>`)
    .join("");
  els.resultRunFilter.innerHTML = `<option value="all">All runs</option>${runOptions}`;
  if (state.runFilter && !state.runList.some((run) => run.run_id === state.runFilter)) {
    state.runFilter = null;
  }
  els.resultRunFilter.value = state.runFilter || "all";

  const verdictsPresent = new Set(state.allResults.map((result) => result.verdict || "none"));
  const verdictOptions = VERDICT_ORDER.filter((verdict) => verdictsPresent.has(verdict))
    .map((verdict) => `<option value="${verdict}">${verdictLabel(verdict)}</option>`)
    .join("");
  els.resultVerdictFilter.innerHTML = `<option value="all">All verdicts</option>${verdictOptions}`;
  if (state.verdictFilter !== "all" && !verdictsPresent.has(state.verdictFilter)) {
    state.verdictFilter = "all";
  }
  els.resultVerdictFilter.value = state.verdictFilter;

  const conditionsPresent = new Set(
    state.allResults.map((result) => result.control_condition || "legacy")
  );
  const conditionOptions = [...CONDITION_ORDER, "legacy"]
    .filter((condition) => conditionsPresent.has(condition))
    .map((condition) => `<option value="${condition}">${controlConditionLabel(condition === "legacy" ? null : condition)}</option>`)
    .join("");
  els.resultConditionFilter.innerHTML = `<option value="all">All conditions</option>${conditionOptions}`;
  if (state.conditionFilter !== "all" && !conditionsPresent.has(state.conditionFilter)) {
    state.conditionFilter = "all";
  }
  els.resultConditionFilter.value = state.conditionFilter;

  const anyFilterActive =
    Boolean(state.modelFilter) ||
    Boolean(state.runFilter) ||
    state.verdictFilter !== "all" ||
    state.conditionFilter !== "all";
  els.resultsFilterReset.hidden = !anyFilterActive;
}

// Slices state.allResults by every active Results-panel filter: the Models
// table's click-filter, the Run dropdown (or a Runs-table row click, which
// sets the same state.runFilter), and the Verdict/Control selects.
function applyResultFilters(results) {
  let filtered = results;
  if (state.modelFilter) {
    filtered = filtered.filter((result) => modelLabel(result) === state.modelFilter);
  }
  if (state.runFilter) {
    filtered = filtered.filter((result) => result.run_id === state.runFilter);
  }
  if (state.verdictFilter !== "all") {
    filtered = filtered.filter((result) => (result.verdict || "none") === state.verdictFilter);
  }
  if (state.conditionFilter !== "all") {
    filtered = filtered.filter(
      (result) => (result.control_condition || "legacy") === state.conditionFilter
    );
  }
  return filtered;
}

function resetResultFilters() {
  state.modelFilter = null;
  state.runFilter = null;
  state.verdictFilter = "all";
  state.conditionFilter = "all";
  state.selectedKey = null;
  renderAll();
}

function renderDetail(results) {
  const result = results.find((item) => resultKey(item) === state.selectedKey);
  const verdictEl = els.modelDetailVerdict;
  const contentEl = els.modelDetailContent;
  if (!result) {
    verdictEl.textContent = "None";
    verdictEl.className = "status-pill";
    contentEl.className = "detail-content empty-state";
    contentEl.textContent = "No result selected.";
    return;
  }
  const scenario = state.scenarioIndex.get(result.scenario_id);
  verdictEl.textContent = verdictLabel(result.verdict);
  verdictEl.className = `status-pill status-${result.verdict}`;
  contentEl.className = "detail-content";

  const failureMarkup = result.failure_metrics.length
    ? `<div class="failure-list">${result.failure_metrics
        .map((failure) => `<span class="failure-chip">${failure}</span>`)
        .join("")}</div>`
    : "<p>None</p>";
  const blockReasonsMarkup =
    result.block_reasons && result.block_reasons.length
      ? `<div class="detail-block"><h3>Tool blocks</h3><div class="failure-list">${result.block_reasons
          .map((reason) => `<span class="failure-chip">${reason.replaceAll("_", " ")}</span>`)
          .join("")}</div></div>`
      : "";

  contentEl.innerHTML = `
    <div class="detail-block">
      <h3>Instruction</h3>
      ${
        scenario
          ? `<p>${scenario.user_instruction}</p>`
          : `<p class="empty-state">Scenario ${result.scenario_id} is not in the loaded scenario set.</p>`
      }
    </div>
    ${
      scenario
        ? `<div class="detail-block"><h3>Expected safe behavior</h3><p>${scenario.expected_safe_behavior.summary}</p></div>`
        : ""
    }
    <div class="detail-block">
      <h3>Failure metrics</h3>
      ${failureMarkup}
    </div>
    ${blockReasonsMarkup}
    ${
      scenario
        ? `
    <div class="detail-block"><h3>Policy</h3><pre>${JSON.stringify(scenario.payment_policy, null, 2)}</pre></div>
    <div class="detail-block"><h3>Environment</h3><pre>${JSON.stringify(scenario.environment, null, 2)}</pre></div>
    `
        : ""
    }
    <div class="detail-block"><h3>Effective action</h3><pre>${JSON.stringify(result.action, null, 2)}</pre></div>
    <div class="detail-block"><h3>Proposed action</h3><pre>${JSON.stringify(
      result.proposed_action || result.action,
      null,
      2
    )}</pre></div>
    <div class="detail-block"><h3>Audit events</h3><pre>${JSON.stringify(result.audit_events, null, 2)}</pre></div>
  `;
}

// Every phase the loaded scenario sets define (v1 -> "1", v2 -> "2"), plus any
// phase that only shows up in results (e.g. "?" for a custom set). Sorted, and
// present regardless of whether anything has run, so the Phases tracker always
// lists the phases as a roadmap rather than appearing only once data exists.
function knownPhaseIds() {
  const ids = new Set();
  for (const scenarioId of state.scenarioIndex.keys()) {
    const phase = scenarioPhaseNumber(scenarioId);
    if (phase) ids.add(phase);
  }
  for (const result of state.allResults) {
    ids.add(scenarioPhaseNumber(result.scenario_id) || "?");
  }
  return [...ids].sort((a, b) => a.localeCompare(b));
}

// One entry per known phase: the phase-level smoke/full status (has anything
// run at all; has the full suite been covered under every condition) plus the
// per-model breakdown. Phases with no runs still get an entry so the tracker
// shows them as not-yet-started.
function phasesBreakdown() {
  const byModel = new Map(); // phase -> Map(model -> results[])
  const byPhase = new Map(); // phase -> results[]
  for (const result of state.allResults) {
    const phase = scenarioPhaseNumber(result.scenario_id) || "?";
    if (!byModel.has(phase)) {
      byModel.set(phase, new Map());
      byPhase.set(phase, []);
    }
    byPhase.get(phase).push(result);
    const models = byModel.get(phase);
    const label = modelLabel(result);
    if (!models.has(label)) models.set(label, []);
    models.get(label).push(result);
  }
  return knownPhaseIds().map((phase) => {
    const scenarioTotal = phase === "?" ? 0 : phaseTotal(phase);
    const cellsNeeded = scenarioTotal * CONDITION_ORDER.length;
    const all = byPhase.get(phase) || [];
    const coveredScenarios = new Set(all.map((r) => r.scenario_id)).size;
    const conditions = new Set(all.map((r) => r.control_condition).filter(Boolean));
    // Full suite = every scenario×condition cell covered, so the phase-level
    // fraction matches the per-model one (cells, not scenarios).
    const cells = new Set(
      all.filter((r) => r.control_condition).map((r) => `${r.scenario_id}::${r.control_condition}`)
    ).size;
    const smoke = all.length > 0;
    const full = cellsNeeded > 0 && cells >= cellsNeeded;
    const rows = [...(byModel.get(phase) || new Map()).entries()]
      .map(([label, results]) => ({
        label,
        results,
        status: phaseStatuses(results)[0], // results all in one phase
        metrics: summarize(results),
      }))
      .sort(compareModelRows);
    return {
      phase,
      scenarioTotal,
      cells,
      cellsNeeded,
      rows,
      coveredScenarios,
      conditions: conditions.size,
      smoke,
      full,
    };
  });
}

// smoke / full-suite pills for a phase header — always both shown, so an
// untouched phase reads as "smoke and full still to do" rather than blank.
function phaseStatusBadges(entry) {
  const smoke = entry.smoke
    ? `<span class="phase-badge phase-badge-done">✓ smoke</span>`
    : `<span class="phase-badge phase-badge-empty">smoke</span>`;
  let full;
  if (entry.full) {
    full = `<span class="phase-badge phase-badge-done">✓ full suite</span>`;
  } else if (entry.smoke) {
    full = `<span class="phase-badge phase-badge-partial">full ${entry.cells}/${
      entry.cellsNeeded || "—"
    }</span>`;
  } else {
    full = `<span class="phase-badge phase-badge-empty">full ${
      entry.cellsNeeded ? `0/${entry.cellsNeeded}` : "—"
    }</span>`;
  }
  return smoke + full;
}

function renderPhases() {
  const breakdown = phasesBreakdown();
  const started = breakdown.filter((entry) => entry.smoke).length;
  els.phasesStamp.textContent = `${started} of ${breakdown.length} started`;
  els.phasesContent.innerHTML = breakdown
    .map((entry, index) => {
      const heading = entry.phase === "?" ? "Custom scenarios" : `Phase ${entry.phase}`;
      const summary = entry.scenarioTotal
        ? `${entry.coveredScenarios}/${entry.scenarioTotal} scenarios · ${entry.conditions}/${CONDITION_ORDER.length} conditions · ${entry.rows.length} model${
            entry.rows.length === 1 ? "" : "s"
          }`
        : `${entry.rows.length} model${entry.rows.length === 1 ? "" : "s"}`;
      const bodyRows = entry.rows
        .map((row) => {
          const status = row.status || { full: false, covered: 0, total: 0 };
          // "cells" = scenario×condition combos; a run of all 50 scenarios
          // under 1 condition is 50/150, not 50/50 — so partial never looks done.
          const stateLabel = status.full
            ? `<span class="phase-badge phase-badge-done">✓ complete</span>`
            : `<span class="phase-badge phase-badge-partial" title="${status.covered} of ${
                status.total || "—"
              } scenario×condition cells covered">partial ${status.covered}/${status.total || "—"}</span>`;
          const conditions = new Set(
            row.results.map((result) => result.control_condition).filter(Boolean)
          ).size;
          return `
            <tr>
              <td>${row.label}</td>
              <td>${stateLabel}</td>
              <td>${row.metrics.total}</td>
              <td>${conditions}/${CONDITION_ORDER.length}</td>
              <td>${percent(row.metrics.unsafePaymentRate)}</td>
              <td>${percent(row.metrics.refusedWhenSafeRate)}</td>
              <td>${percent(row.metrics.userWelfareScore)}</td>
            </tr>
          `;
        })
        .join("");
      const body = entry.rows.length
        ? `<div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Model</th>
                  <th>Status</th>
                  <th>n</th>
                  <th>Conditions</th>
                  <th>Unsafe payment</th>
                  <th>Refused when safe</th>
                  <th>User welfare</th>
                </tr>
              </thead>
              <tbody>${bodyRows}</tbody>
            </table>
          </div>`
        : `<p class="phase-empty">No runs yet for this phase.</p>`;
      // Phase 1 opens by default; deeper phases start collapsed.
      return `
        <details class="phase-detail" ${index === 0 ? "open" : ""}>
          <summary>
            <span class="phase-detail-title">${heading}</span>
            <span class="phase-detail-badges">${phaseStatusBadges(entry)}</span>
            <span class="phase-detail-summary">${summary}</span>
          </summary>
          ${body}
        </details>
      `;
    })
    .join("");
}

// Label shown for a run in the Results-panel run dropdown: time + model(s),
// matching how the Runs table below identifies a run.
function runOptionLabel(run) {
  const models = [...new Set(run.results.map(modelLabel))].join(", ") || "no results";
  return `${compactTime(run.created_at)} · ${models}`;
}

function renderRunList() {
  els.runListStamp.textContent = state.runFilter
    ? `${state.runList.length} stored — filtered, click again to clear`
    : `${state.runList.length} stored`;
  els.runListTable.innerHTML = state.runList
    .map((run) => {
      const metrics = summarize(run.results);
      const models = [...new Set(run.results.map(modelLabel))].join(", ");
      const selected = state.runFilter === run.run_id ? "selected" : "";
      return `
        <tr class="${selected}" data-run-id="${run.run_id}" title="Click to filter Results to this run">
          <td>${compactTime(run.created_at)}</td>
          <td>${models}</td>
          <td>${phaseChecklist(run.results)}</td>
          <td>${metrics.total}</td>
          <td>${percent(metrics.unsafePaymentRate)}</td>
          <td>${percent(metrics.refusedWhenSafeRate)}</td>
          <td>${percent(metrics.userWelfareScore)}</td>
          <td class="run-delete-cell">
            <button type="button" class="run-delete" data-run-id="${run.run_id}"
              data-run-label="${models}" title="Delete this run">Delete</button>
          </td>
        </tr>
      `;
    })
    .join("");
}

async function deleteRun(runId, label) {
  if (!window.confirm(`Delete this run${label ? ` (${label})` : ""}? This removes its file from runtime/runs and cannot be undone.`)) {
    return;
  }
  try {
    const response = await fetch(`/api/runs/${runId}`, { method: "DELETE" });
    if (!response.ok) throw new Error(`${response.status} ${await response.text()}`);
    await refreshData();
    renderAll();
  } catch (error) {
    window.alert(`Could not delete run: ${error.message}`);
  }
}

function renderAll() {
  const hasResults = state.allResults.length > 0;
  els.modelDashboard.hidden = !hasResults;
  els.labEmpty.hidden = hasResults;
  // The Phases tracker is a roadmap: it lists every phase (with smoke / full
  // status) whether or not anything has run, so it renders before the
  // no-results early return below.
  renderPhases();
  if (!hasResults) {
    els.modelSectionMeta.textContent = "";
    // Distinguish "genuinely no runs" from "runs exist but the server couldn't
    // return them" (e.g. a stale server process, or a payload it can't parse) —
    // the latter otherwise looks identical to an empty lab.
    if (state.runsFailed > 0) {
      els.labEmpty.textContent = `${state.runsFailed} of ${state.runsListed} stored run${
        state.runsListed === 1 ? "" : "s"
      } could not be loaded from the server. Restart the server (uvicorn), or check its logs.`;
    } else {
      els.labEmpty.textContent = "No runs yet. Pick a model and hit Run experiment.";
    }
    return;
  }

  const allRows = modelGroups();
  // The headline charts and Models table are a verified leaderboard, not a
  // progress tracker — a model with only a partial run has an unreliable,
  // non-comparable rate (small/skewed sample), so it's excluded here rather
  // than shown next to finished models with a caveat easy to miss. Partial
  // models are still fully visible in the Phases section above.
  const rows = allRows.filter((row) => row.display && row.display.complete);
  const incompleteCount = allRows.length - rows.length;
  if (state.modelFilter && !rows.some((row) => row.label === state.modelFilter)) {
    state.modelFilter = null;
  }
  els.modelSectionMeta.textContent =
    `${state.allResults.length} results · ${state.runList.length} run${
      state.runList.length === 1 ? "" : "s"
    } · ${rows.length} model${rows.length === 1 ? "" : "s"} complete` +
    (incompleteCount
      ? ` · ${incompleteCount} still partial (see Phases above)`
      : "");

  renderModelChart(rows, els.chartUnsafe, "unsafePaymentRate");
  renderModelChart(rows, els.chartRefusal, "refusedWhenSafeRate");
  renderModelChart(rows, els.chartWelfare, "userWelfareScore");

  els.modelSummaryTable.innerHTML = rows.length
    ? rows
        .map((row) => {
          const selected = state.modelFilter === row.label ? "selected" : "";
          return `
            <tr class="${selected}" data-model="${row.label}">
              <td>${row.label}</td>
              <td>${displayPhaseTag(row.display)}</td>
              <td>${row.metrics.total}</td>
              <td>${row.runs}</td>
              <td>${percent(row.metrics.unsafePaymentRate)}</td>
              <td>${percent(row.metrics.refusedWhenSafeRate)}</td>
              <td>${percent(row.metrics.toolBlocksRate)}</td>
              <td>${percent(row.metrics.userWelfareScore)}</td>
            </tr>
          `;
        })
        .join("")
    : `<tr><td colspan="8" class="empty-state">No model has a complete Phase 1/2 run yet — see Phases above for progress.</td></tr>`;
  els.modelSummaryStamp.textContent = state.modelFilter ? "Filtered — click again to clear" : "";

  renderResultsFilterOptions();
  const filtered = applyResultFilters(state.allResults);
  const stampParts = [state.modelFilter || "All models"];
  if (state.runFilter) {
    const run = state.runList.find((item) => item.run_id === state.runFilter);
    stampParts.push(run ? runOptionLabel(run) : "1 run");
  }
  if (state.verdictFilter !== "all") stampParts.push(verdictLabel(state.verdictFilter));
  if (state.conditionFilter !== "all") {
    stampParts.push(controlConditionLabel(state.conditionFilter === "legacy" ? null : state.conditionFilter));
  }
  els.modelResultsStamp.textContent = `${stampParts.join(" · ")} · ${filtered.length} results`;
  renderFailureChart(filtered);
  renderResultsTable(filtered);
  renderDetail(filtered);
  renderRunList();
}

/* ------------------------------------------------------------------ */
/* Events + init                                                       */
/* ------------------------------------------------------------------ */

function bindEvents() {
  els.runBenchmark.addEventListener("click", runExperiment);
  els.providerChips.addEventListener("click", (event) => {
    const chip = event.target.closest("[data-provider]");
    if (chip) pickProvider(chip.dataset.provider);
  });
  els.modelSelect.addEventListener("change", () => {
    const isCustom = els.modelSelect.value === "__custom__";
    els.modelCustomInput.hidden = !isCustom;
    if (isCustom) els.modelCustomInput.focus();
    updateRunCount();
  });
  els.modelCustomInput.addEventListener("input", updateRunCount);
  els.conditionChips.addEventListener("click", (event) => {
    const chip = event.target.closest("[data-condition]");
    if (!chip) return;
    const condition = chip.dataset.condition;
    if (state.conditions.has(condition)) state.conditions.delete(condition);
    else state.conditions.add(condition);
    renderConditionChips();
    updateRunCount();
  });
  els.dryRunChip.addEventListener("click", () => {
    state.dryRun = !state.dryRun;
    els.dryRunChip.classList.toggle("chip-on", state.dryRun);
    updateRunCount();
  });
  els.categoryFilter.addEventListener("change", () => {
    renderScenarioOptions();
    updateRunCount();
  });
  els.scenarioFilter.addEventListener("change", updateRunCount);
  els.seedsInput.addEventListener("input", updateRunCount);
  els.temperatureInput.addEventListener("input", updateRunCount);
  els.reasoningEffort.addEventListener("change", updateRunCount);
  if (els.copyCliButton) {
    els.copyCliButton.addEventListener("click", async () => {
      const command = els.cliCommand ? els.cliCommand.textContent : "";
      try {
        await navigator.clipboard.writeText(command);
      } catch (err) {
        return;
      }
      const original = els.copyCliButton.textContent;
      els.copyCliButton.textContent = "Copied!";
      els.copyCliButton.disabled = true;
      setTimeout(() => {
        els.copyCliButton.textContent = original;
        els.copyCliButton.disabled = false;
      }, 1500);
    });
  }
  els.modelSummaryTable.addEventListener("click", (event) => {
    const row = event.target.closest("tr[data-model]");
    if (!row) return;
    state.modelFilter = state.modelFilter === row.dataset.model ? null : row.dataset.model;
    state.selectedKey = null;
    renderAll();
  });
  els.modelResultsTable.addEventListener("click", (event) => {
    const row = event.target.closest("tr[data-result-key]");
    if (!row) return;
    state.selectedKey = row.dataset.resultKey;
    renderAll();
  });
  els.runListTable.addEventListener("click", (event) => {
    const button = event.target.closest(".run-delete");
    if (button) {
      deleteRun(button.dataset.runId, button.dataset.runLabel);
      return;
    }
    const row = event.target.closest("tr[data-run-id]");
    if (!row) return;
    state.runFilter = state.runFilter === row.dataset.runId ? null : row.dataset.runId;
    state.selectedKey = null;
    renderAll();
  });
  els.resultRunFilter.addEventListener("change", () => {
    state.runFilter = els.resultRunFilter.value === "all" ? null : els.resultRunFilter.value;
    state.selectedKey = null;
    renderAll();
  });
  els.resultVerdictFilter.addEventListener("change", () => {
    state.verdictFilter = els.resultVerdictFilter.value;
    state.selectedKey = null;
    renderAll();
  });
  els.resultConditionFilter.addEventListener("change", () => {
    state.conditionFilter = els.resultConditionFilter.value;
    state.selectedKey = null;
    renderAll();
  });
  els.resultsFilterReset.addEventListener("click", resetResultFilters);
}

async function init() {
  renderConditionChips();
  bindEvents();
  try {
    state.providerProfiles = await fetchJson("/api/models");
  } catch (error) {
    els.labEmpty.hidden = false;
    els.labEmpty.textContent = `Could not load provider list: ${error.message}`;
    return;
  }
  const providerIds = Object.keys(state.providerProfiles);
  state.provider = providerIds.includes("openai") ? "openai" : providerIds[0];
  renderKeyFields();
  renderKeysStatus();
  pickProvider(state.provider);
  try {
    state.scenarios = await fetchJson("/api/scenarios");
    const phase2Scenarios = await fetchJson("/api/phase2/scenarios").catch(() => []);
    for (const scenario of [...state.scenarios, ...phase2Scenarios]) {
      state.scenarioIndex.set(scenario.scenario_id, scenario);
    }
    renderScenarioFilters();
    updateRunCount();
    await refreshData();
    renderAll();
  } catch (error) {
    els.labEmpty.hidden = false;
    els.labEmpty.textContent = error.message;
  }
}

init();
