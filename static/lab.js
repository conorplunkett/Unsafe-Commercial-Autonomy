// Local experiment console (/lab). Talks only to the local backend; nothing
// here touches Supabase or the published site. The controls mirror the live
// site's "Run it yourself" runner (web/components/Runner.tsx) so the two read
// as one design; labels below are lifted from web/lib/labels.ts.

const state = {
  scenarios: [],
  scenarioIndex: new Map(),
  allResults: [],
  runList: [],
  provider: "openai",
  dryRun: false,
  conditions: new Set(["no_policy", "prompt_policy", "tool_constraints"]),
  modelFilter: null,
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
  "modelInput",
  "modelSuggestions",
  "conditionChips",
  "dryRunChip",
  "categoryFilter",
  "scenarioFilter",
  "seedsInput",
  "temperatureInput",
  "reasoningEffort",
  "keysBand",
  "keysStatus",
  "keyOpenai",
  "keyAnthropic",
  "modelSectionMeta",
  "modelDashboard",
  "chartUnsafe",
  "chartRefusal",
  "chartWelfare",
  "modelSummaryTable",
  "modelSummaryStamp",
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

// Providers the local harness can run. Model names pass straight through to the
// provider API; suggestions are a datalist, so any model name can be typed.
const PROVIDERS = [
  {
    id: "openai",
    label: "OpenAI",
    defaultModel: "gpt-4o-mini",
    suggestions: ["gpt-4o-mini", "gpt-4o", "gpt-4.1", "gpt-4.1-mini", "o4-mini", "o3"],
  },
  {
    id: "anthropic",
    label: "Anthropic",
    defaultModel: "claude-haiku-4-5-20251001",
    suggestions: ["claude-opus-4-8", "claude-sonnet-4-6", "claude-haiku-4-5-20251001"],
  },
  {
    id: "gemini",
    label: "Gemini",
    defaultModel: "gemini-2.5-flash-lite",
    suggestions: ["gemini-2.5-flash-lite", "gemini-2.5-flash", "gemini-2.5-pro"],
  },
  { id: "baseline_naive", label: "Naive baseline", defaultModel: null, suggestions: [] },
  { id: "openweights", label: "Open-weights", defaultModel: null, suggestions: [] },
];

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

// Scenario ids embed their source set (scn_v1_..., scn_v2_...; see
// app/data.py), so the phase a result was scored under can be read off the id
// without threading run.phase (which run_phase1_evaluation leaves unset).
function resultPhase(result) {
  const match = /^scn_v(\d+)_/.exec(result.scenario_id || "");
  return match ? `Phase ${match[1]}` : "Custom";
}

function phasesLabel(results) {
  const phases = [...new Set(results.map(resultPhase))].sort();
  return phases.join(" + ");
}

function summarize(results) {
  const count = (predicate) => results.filter(predicate).length;
  // Errored results carry a synthetic fallback action, not a real model
  // decision, so they are excluded from rate/welfare denominators (matches
  // app/metrics.py). They still drive the error rate.
  const scored = results.filter((result) => !result.error);
  const unsafeDenominator = scored.filter((result) => result.safe_to_act === false);
  const falseRefusalDenominator = scored.filter((result) => result.safe_to_act === true);
  const unsafeTotal = unsafeDenominator.length || scored.length || 1;
  const falseRefusalTotal = falseRefusalDenominator.length || scored.length || 1;
  const avgWelfare = scored.length
    ? scored.reduce((sum, result) => sum + result.user_welfare_score, 0) / scored.length
    : 0;
  return {
    total: results.length,
    unsafePaymentRate:
      unsafeDenominator.filter((result) => result.unsafe_payment).length / unsafeTotal,
    falseRefusalRate:
      falseRefusalDenominator.filter((result) => result.false_refusal).length / falseRefusalTotal,
    toolBlocksRate:
      count((result) => result.block_reasons && result.block_reasons.length) / (results.length || 1),
    errorRate: count((result) => result.error) / (results.length || 1),
    userWelfareScore: avgWelfare,
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

function saveKeys() {
  localStorage.setItem(
    KEY_STORAGE,
    JSON.stringify({
      openai: els.keyOpenai.value.trim(),
      anthropic: els.keyAnthropic.value.trim(),
    })
  );
  renderKeysStatus();
}

function renderKeysStatus() {
  const keys = loadKeys();
  const mark = (name, value) => `${name} ${value ? "✓" : "—"}`;
  els.keysStatus.textContent = `${mark("OpenAI", keys.openai)} · ${mark("Anthropic", keys.anthropic)}`;
}

/* ------------------------------------------------------------------ */
/* Controls                                                            */
/* ------------------------------------------------------------------ */

function providerProfile() {
  return PROVIDERS.find((entry) => entry.id === state.provider) || PROVIDERS[0];
}

function renderProviderChips() {
  els.providerChips.innerHTML = PROVIDERS.map(
    (entry) => `
      <button type="button" class="chip ${entry.id === state.provider ? "chip-on" : ""}" data-provider="${entry.id}">
        ${entry.label}
      </button>
    `
  ).join("");
}

function pickProvider(providerId) {
  state.provider = providerId;
  const profile = providerProfile();
  els.modelInput.value = profile.defaultModel || "";
  els.modelInput.disabled = !profile.defaultModel;
  els.modelInput.placeholder = profile.defaultModel || "—";
  els.modelSuggestions.innerHTML = profile.suggestions
    .map((model) => `<option value="${model}"></option>`)
    .join("");
  renderProviderChips();
  updateRunCount();
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
  const modelName = els.modelInput.value.trim() || null;
  const live = provider !== "baseline_naive" && !state.dryRun;
  let apiKey = null;
  if (live && (provider === "openai" || provider === "anthropic")) {
    apiKey = loadKeys()[provider] || null;
    if (!apiKey) {
      els.keysBand.open = true;
      (provider === "openai" ? els.keyOpenai : els.keyAnthropic).focus();
      failRun(`Paste your ${providerProfile().label} key first, or switch on Dry run.`);
      return;
    }
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
}

function modelGroups() {
  const groups = new Map();
  for (const result of state.allResults) {
    const label = modelLabel(result);
    if (!groups.has(label)) groups.set(label, []);
    groups.get(label).push(result);
  }
  const rows = [...groups.entries()].map(([label, results]) => ({
    label,
    results,
    runs: new Set(results.map((result) => result.run_id)).size,
    phases: phasesLabel(results),
    metrics: summarize(results),
  }));
  rows.sort((a, b) => b.metrics.unsafePaymentRate - a.metrics.unsafePaymentRate);
  return rows;
}

function renderModelChart(rows, chartEl, metricKey) {
  // All three metrics are rates, so bars share a fixed 0–100% scale rather
  // than stretching to the chart's max — a 5% rate must look like 5%.
  chartEl.innerHTML = rows
    .map((row) => {
      const value = row.metrics[metricKey];
      const width = Math.max(value * 100, value > 0 ? 1.5 : 0);
      return `
        <div class="bar-row" title="${row.label} · n=${row.metrics.total}">
          <span class="bar-name">${row.label}</span>
          <span class="bar-phase">${row.phases}</span>
          <div class="bar-track"><div class="bar-fill" style="width:${width}%"></div></div>
          <span class="bar-value">${percent(value)}</span>
        </div>
      `;
    })
    .join("");
}

function statusPill(verdict) {
  const label = verdict ? verdict.replaceAll("_", " ") : "none";
  return `<span class="status-pill status-${verdict || "safe"}">${label}</span>`;
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
      const conditionLabel = result.control_condition
        ? CONDITION_LABELS[result.control_condition] || result.control_condition.replaceAll("_", " ")
        : "legacy";
      return `
        <tr class="${selected}" data-result-key="${resultKey(result)}">
          <td>${statusPill(result.verdict)}</td>
          <td>${result.scenario_title}</td>
          <td>${modelLabel(result)}</td>
          <td>${conditionLabel}</td>
          <td>${failures}</td>
        </tr>
      `;
    })
    .join("");
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
  verdictEl.textContent = result.verdict.replaceAll("_", " ");
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

function renderRunList() {
  els.runListStamp.textContent = `${state.runList.length} stored`;
  els.runListTable.innerHTML = state.runList
    .map((run) => {
      const metrics = summarize(run.results);
      const models = [...new Set(run.results.map(modelLabel))].join(", ");
      return `
        <tr>
          <td>${compactTime(run.created_at)}</td>
          <td>${models}</td>
          <td>${phasesLabel(run.results)}</td>
          <td>${metrics.total}</td>
          <td>${percent(metrics.unsafePaymentRate)}</td>
          <td>${percent(metrics.falseRefusalRate)}</td>
          <td>${percent(metrics.userWelfareScore)}</td>
        </tr>
      `;
    })
    .join("");
}

function renderAll() {
  const hasResults = state.allResults.length > 0;
  els.modelDashboard.hidden = !hasResults;
  els.labEmpty.hidden = hasResults;
  if (!hasResults) {
    els.modelSectionMeta.textContent = "";
    return;
  }

  const rows = modelGroups();
  if (state.modelFilter && !rows.some((row) => row.label === state.modelFilter)) {
    state.modelFilter = null;
  }
  els.modelSectionMeta.textContent = `${state.allResults.length} results · ${state.runList.length} run${
    state.runList.length === 1 ? "" : "s"
  } · ${rows.length} model${rows.length === 1 ? "" : "s"}`;

  renderModelChart(rows, els.chartUnsafe, "unsafePaymentRate");
  renderModelChart(rows, els.chartRefusal, "falseRefusalRate");
  renderModelChart(rows, els.chartWelfare, "userWelfareScore");

  els.modelSummaryTable.innerHTML = rows
    .map((row) => {
      const selected = state.modelFilter === row.label ? "selected" : "";
      return `
        <tr class="${selected}" data-model="${row.label}">
          <td>${row.label}</td>
          <td>${row.phases}</td>
          <td>${row.metrics.total}</td>
          <td>${row.runs}</td>
          <td>${percent(row.metrics.unsafePaymentRate)}</td>
          <td>${percent(row.metrics.falseRefusalRate)}</td>
          <td>${percent(row.metrics.toolBlocksRate)}</td>
          <td>${percent(row.metrics.userWelfareScore)}</td>
        </tr>
      `;
    })
    .join("");
  els.modelSummaryStamp.textContent = state.modelFilter ? "Filtered — click again to clear" : "";

  const filtered = state.modelFilter
    ? state.allResults.filter((result) => modelLabel(result) === state.modelFilter)
    : state.allResults;
  els.modelResultsStamp.textContent = state.modelFilter
    ? `${state.modelFilter} · ${filtered.length} results`
    : `All models · ${filtered.length} results`;
  renderResultsTable(filtered);
  renderDetail(filtered);
  renderRunList();
}

/* ------------------------------------------------------------------ */
/* Events + init                                                       */
/* ------------------------------------------------------------------ */

function bindEvents() {
  els.runBenchmark.addEventListener("click", runExperiment);
  els.keyOpenai.addEventListener("input", saveKeys);
  els.keyAnthropic.addEventListener("input", saveKeys);
  els.providerChips.addEventListener("click", (event) => {
    const chip = event.target.closest("[data-provider]");
    if (chip) pickProvider(chip.dataset.provider);
  });
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
  });
  els.categoryFilter.addEventListener("change", () => {
    renderScenarioOptions();
    updateRunCount();
  });
  els.scenarioFilter.addEventListener("change", updateRunCount);
  els.seedsInput.addEventListener("input", updateRunCount);
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
}

async function init() {
  const keys = loadKeys();
  els.keyOpenai.value = keys.openai || "";
  els.keyAnthropic.value = keys.anthropic || "";
  renderKeysStatus();
  renderConditionChips();
  bindEvents();
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
