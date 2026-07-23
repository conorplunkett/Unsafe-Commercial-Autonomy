// Local experiment console (/lab). Talks only to the local backend; nothing
// here touches Supabase or the published site. The lander at / is rendered from
// the live site's code and is deliberately not reused here.

const state = {
  controlConditions: {},
  scenarios: [],
  scenarioIndex: new Map(),
  allResults: [],
  runList: [],
  modelFilter: null,
  selectedKey: null,
};

const els = {};
for (const id of [
  "runBenchmark",
  "runProgress",
  "progressFill",
  "progressLabel",
  "modelSelect",
  "conditionFilters",
  "categoryFilter",
  "scenarioFilter",
  "seedsInput",
  "temperatureInput",
  "reasoningEffort",
  "dryRun",
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

const RUN_BUTTON_LABEL =
  '<span class="button-mark" aria-hidden="true">' +
  '<svg viewBox="0 0 16 16" width="11" height="11" fill="currentColor">' +
  '<path d="M4.5 2.6v10.8a.8.8 0 0 0 1.22.68l8.5-5.4a.8.8 0 0 0 0-1.36L5.72 1.92A.8.8 0 0 0 4.5 2.6Z"/>' +
  "</svg></span>Run experiment";

// The model switcher encodes provider and model as "provider::model". Model
// names go straight through to the provider API; keep the lists in sync with
// what each provider serves. An empty model name means the provider default.
const MODEL_CHOICES = [
  { group: "Baselines", provider: "baseline_naive", models: [["", "Naive baseline (offline)"]] },
  {
    group: "OpenAI",
    provider: "openai",
    models: ["gpt-4o", "gpt-4o-mini", "gpt-4.1", "gpt-4.1-mini", "o4-mini", "o3"],
  },
  {
    group: "Anthropic",
    provider: "anthropic",
    models: ["claude-opus-4-8", "claude-sonnet-4-6", "claude-haiku-4-5-20251001"],
  },
  { group: "Open-weights", provider: "openweights", models: [["", "Configured local endpoint"]] },
];

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

function resultKey(result) {
  return `${result.run_id}::${result.scenario_id}::${result.model_id || result.agent_id}::${result.control_condition || "legacy"}::${result.seed || 0}`;
}

function modelLabel(result) {
  return result.model_name || result.agent_name || result.model_id || result.agent_id || "unknown";
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

function renderModelSelect() {
  els.modelSelect.innerHTML = MODEL_CHOICES.map((entry) => {
    const options = entry.models
      .map((model) => {
        const [value, label] = Array.isArray(model) ? model : [model, model];
        return `<option value="${entry.provider}::${value}">${label}</option>`;
      })
      .join("");
    return `<optgroup label="${entry.group}">${options}</optgroup>`;
  }).join("");
}

function selectedModel() {
  const [provider, ...rest] = (els.modelSelect.value || "baseline_naive::").split("::");
  return { provider, modelName: rest.join("::") || null };
}

function renderControlConditions() {
  els.conditionFilters.innerHTML = Object.entries(state.controlConditions)
    .map(
      ([conditionId, condition]) => `
        <label class="agent-check" title="${condition.description}">
          <input type="checkbox" value="${conditionId}" checked>
          <span>${condition.name}</span>
        </label>
      `
    )
    .join("");
}

function renderScenarioFilters() {
  const categories = [...new Set(state.scenarios.map((scenario) => scenario.category))].sort();
  els.categoryFilter.innerHTML = [
    '<option value="all">All categories</option>',
    ...categories.map((category) => `<option value="${category}">${category}</option>`),
  ].join("");
  els.scenarioFilter.innerHTML = [
    '<option value="all">All scenarios</option>',
    ...state.scenarios.map(
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

function selectedScenarioIds() {
  if (els.scenarioFilter.value !== "all") return [els.scenarioFilter.value];
  if (els.categoryFilter.value !== "all") {
    return state.scenarios
      .filter((scenario) => scenario.category === els.categoryFilter.value)
      .map((scenario) => scenario.scenario_id);
  }
  return null;
}

/* ------------------------------------------------------------------ */
/* Run + progress                                                      */
/* ------------------------------------------------------------------ */

function showProgress(completed, total, unit) {
  els.runProgress.hidden = false;
  const fraction = total ? completed / total : 0;
  els.progressFill.style.width = `${Math.round(fraction * 100)}%`;
  els.progressLabel.textContent = total
    ? `${completed} / ${total}${unit && unit !== "complete" ? ` · ${unit}` : ""}`
    : "Starting…";
}

function hideProgress() {
  els.runProgress.hidden = true;
}

function failRun(message) {
  els.progressLabel.textContent = message;
  els.progressFill.style.width = "0%";
}

async function runExperiment() {
  const { provider, modelName } = selectedModel();
  const dryRun = els.dryRun.checked;
  const live = provider !== "baseline_naive" && !dryRun;
  const keys = loadKeys();
  let apiKey = null;
  if (live && (provider === "openai" || provider === "anthropic")) {
    apiKey = keys[provider] || null;
    if (!apiKey) {
      els.keysBand.open = true;
      (provider === "openai" ? els.keyOpenai : els.keyAnthropic).focus();
      failRun(`Paste your ${provider === "openai" ? "OpenAI" : "Anthropic"} key first, or tick Dry run.`);
      els.runProgress.hidden = false;
      return;
    }
  }

  const conditions = [...els.conditionFilters.querySelectorAll("input:checked")].map(
    (input) => input.value
  );
  const temperature = Number.parseFloat(els.temperatureInput.value);

  els.runBenchmark.disabled = true;
  els.runBenchmark.textContent = "Running...";
  showProgress(0, 0, "");
  try {
    const job = await fetchJson("/api/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model_ids: [provider],
        control_conditions: conditions.length ? conditions : null,
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
      showProgress(status.completed, status.total, status.unit);
    } while (status.status === "running");

    if (status.status === "error") {
      failRun(`Run failed: ${status.error}`);
      return;
    }
    showProgress(status.total, status.total, "complete");
    await refreshData();
    renderAll();
    setTimeout(hideProgress, 1500);
  } catch (error) {
    failRun(`Run failed: ${error.message}`);
  } finally {
    els.runBenchmark.disabled = false;
    els.runBenchmark.innerHTML = RUN_BUTTON_LABEL;
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
        ? result.control_condition.replaceAll("_", " ")
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
  renderModelSelect();
  bindEvents();
  try {
    const [controlConditions, scenarios] = await Promise.all([
      fetchJson("/api/control-conditions"),
      fetchJson("/api/scenarios"),
    ]);
    state.controlConditions = controlConditions;
    state.scenarios = scenarios;
    const phase2Scenarios = await fetchJson("/api/phase2/scenarios").catch(() => []);
    for (const scenario of [...scenarios, ...phase2Scenarios]) {
      state.scenarioIndex.set(scenario.scenario_id, scenario);
    }
    renderControlConditions();
    renderScenarioFilters();
    await refreshData();
    renderAll();
  } catch (error) {
    els.labEmpty.hidden = false;
    els.labEmpty.textContent = error.message;
  }
}

init();
