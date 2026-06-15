const state = {
  models: {},
  controlConditions: {},
  scenarios: [],
  scenarioIndex: new Map(),
  currentRun: null,
  selectedResultKey: null,
  officialRun: null,
  officialSelectedKey: null,
  officialRuns: [],
  officialRunId: null,
};

// Read-only Supabase config for published "Official run" results. The "Run it
// yourself" flow ignores this entirely and uses the local backend.
const SUPA = window.UCA_CONFIG || {};

function supabaseConfigured() {
  return Boolean(SUPA.supabaseUrl && SUPA.supabasePublishableKey);
}

async function supabaseGet(query) {
  const base = SUPA.supabaseUrl.replace(/\/$/, "");
  const table = SUPA.benchmarkTable || "benchmark_runs";
  const response = await fetch(`${base}/rest/v1/${table}?${query}`, {
    headers: {
      apikey: SUPA.supabasePublishableKey,
      Authorization: `Bearer ${SUPA.supabasePublishableKey}`,
    },
  });
  if (!response.ok) {
    throw new Error(`Supabase ${response.status} ${await response.text()}`);
  }
  return response.json();
}

async function fetchPublishedRunList() {
  return supabaseGet(
    "select=run_id,created_at,published_at,phase,label&order=published_at.desc"
  );
}

async function fetchPublishedRun(runId) {
  const rows = await supabaseGet(
    `select=payload&run_id=eq.${encodeURIComponent(runId)}&limit=1`
  );
  return rows.length ? rows[0].payload : null;
}

const els = {
  runButton: document.querySelector("#runBenchmark"),
  modelFilters: document.querySelector("#modelFilters"),
  conditionFilters: document.querySelector("#conditionFilters"),
  categoryFilter: document.querySelector("#categoryFilter"),
  scenarioFilter: document.querySelector("#scenarioFilter"),
  liveRun: document.querySelector("#liveRun"),
  byokEnabled: document.querySelector("#byokEnabled"),
  byokFields: document.querySelector("#byokFields"),
  byokProvider: document.querySelector("#byokProvider"),
  byokModel: document.querySelector("#byokModel"),
  byokKey: document.querySelector("#byokKey"),
  modelGroup: document.querySelector(".provider-group"),
  modelPickerHint: document.querySelector("#modelPickerHint"),
  modelOverrideNote: document.querySelector("#modelOverrideNote"),
  temperatureInput: document.querySelector("#temperatureInput"),
  reasoningEffort: document.querySelector("#reasoningEffort"),
  metricTiles: document.querySelector("#metricTiles"),
  resultsTable: document.querySelector("#resultsTable"),
  runStamp: document.querySelector("#runStamp"),
  detailVerdict: document.querySelector("#detailVerdict"),
  detailContent: document.querySelector("#detailContent"),
  taxonomyTable: document.querySelector("#taxonomyTable"),
  taxonomyCount: document.querySelector("#taxonomyCount"),
  // official (read-only) dashboard elements
  officialRunStamp: document.querySelector("#officialRunStamp"),
  officialRunSelect: document.querySelector("#officialRunSelect"),
  officialRunSelectLabel: document.querySelector(".run-select-label"),
  officialMetricTiles: document.querySelector("#officialMetricTiles"),
  officialAblation: document.querySelector("#officialAblation"),
  officialAblationTable: document.querySelector("#officialAblationTable"),
  officialResultsTable: document.querySelector("#officialResultsTable"),
  officialDetailVerdict: document.querySelector("#officialDetailVerdict"),
  officialDetailContent: document.querySelector("#officialDetailContent"),
  officialTaxonomyTable: document.querySelector("#officialTaxonomyTable"),
  officialTaxonomyCount: document.querySelector("#officialTaxonomyCount"),
  heroUnsafe: document.querySelector("#heroUnsafe"),
  heroRefusal: document.querySelector("#heroRefusal"),
  heroWelfare: document.querySelector("#heroWelfare"),
  heroNote: document.querySelector("#heroNote"),
};

// Mirrors the run button markup in index.html so the play icon survives a
// run-and-reset cycle.
const RUN_BUTTON_LABEL =
  '<span class="button-mark" aria-hidden="true">' +
  '<svg viewBox="0 0 16 16" width="11" height="11" fill="currentColor">' +
  '<path d="M4.5 2.6v10.8a.8.8 0 0 0 1.22.68l8.5-5.4a.8.8 0 0 0 0-1.36L5.72 1.92A.8.8 0 0 0 4.5 2.6Z"/>' +
  "</svg></span>Run benchmark";

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`${response.status} ${body}`);
  }
  return response.json();
}

function percent(value) {
  return `${Math.round((value || 0) * 100)}%`;
}

function compactTime(isoDate) {
  if (!isoDate) return "No run";
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(isoDate));
}

function resultKey(result) {
  return `${result.scenario_id}::${result.model_id || result.agent_id}::${result.control_condition || "legacy"}::${result.seed || 0}`;
}

function currentFilters() {
  const selectedModel = els.modelFilters.querySelector("input:checked");
  const checkedConditions = [...els.conditionFilters.querySelectorAll("input:checked")].map(
    (input) => input.value
  );
  return {
    modelIds: selectedModel ? [selectedModel.value] : [],
    controlConditions: checkedConditions,
    category: els.categoryFilter.value,
    scenarioId: els.scenarioFilter.value,
    live: els.liveRun.checked,
    temperature: els.temperatureInput ? Number.parseFloat(els.temperatureInput.value) : null,
    reasoningEffort: els.reasoningEffort ? els.reasoningEffort.value || null : null,
    byok: {
      enabled: els.byokEnabled ? els.byokEnabled.checked : false,
      provider: els.byokProvider ? els.byokProvider.value : "openai",
      model: els.byokModel ? els.byokModel.value.trim() : "",
      key: els.byokKey ? els.byokKey.value.trim() : "",
    },
  };
}

// Curated per-provider model lists for the bring-your-own-key dropdown. The
// chosen value is passed straight through to the provider API as the model
// name, so keep these in sync with what each provider currently serves.
const BYOK_MODELS = {
  openai: ["gpt-4o", "gpt-4o-mini", "gpt-4.1", "gpt-4.1-mini", "o4-mini", "o3"],
  anthropic: ["claude-opus-4-8", "claude-sonnet-4-6", "claude-haiku-4-5-20251001"],
};

const BYOK_KEY_PLACEHOLDER = {
  openai: "sk-...",
  anthropic: "sk-ant-...",
};

function populateByokModels() {
  if (!els.byokModel || !els.byokProvider) return;
  const previous = els.byokModel.value;
  const models = BYOK_MODELS[els.byokProvider.value] || [];
  els.byokModel.innerHTML = models
    .map((modelName) => `<option value="${modelName}">${modelName}</option>`)
    .join("");
  if (models.includes(previous)) {
    els.byokModel.value = previous;
  }
}

function syncByokUi() {
  if (!els.byokFields) return;
  const enabled = els.byokEnabled.checked;
  els.byokFields.hidden = !enabled;
  populateByokModels();
  if (els.byokKey && els.byokProvider) {
    els.byokKey.placeholder = BYOK_KEY_PLACEHOLDER[els.byokProvider.value] || "API key";
  }
  // With your own key the model comes from the key section, so the top model
  // picker would only conflict — disable it and explain why.
  els.modelFilters
    .querySelectorAll("input")
    .forEach((input) => (input.disabled = enabled));
  if (els.modelGroup) els.modelGroup.classList.toggle("is-disabled", enabled);
  if (els.modelPickerHint) els.modelPickerHint.hidden = enabled;
  if (els.modelOverrideNote) els.modelOverrideNote.hidden = !enabled;
}

function visibleResults() {
  if (!state.currentRun) return [];
  const filters = currentFilters();
  const runModelIds = new Set(state.currentRun.results.map((result) => result.model_id).filter(Boolean));
  const runConditions = new Set(
    state.currentRun.results.map((result) => result.control_condition).filter(Boolean)
  );
  const activeModelIds = filters.modelIds.filter((modelId) => runModelIds.has(modelId));
  const activeConditions = filters.controlConditions.filter((condition) => runConditions.has(condition));
  return state.currentRun.results.filter((result) => {
    const modelMatch = activeModelIds.length === 0 || activeModelIds.includes(result.model_id);
    const conditionMatch =
      activeConditions.length === 0 || activeConditions.includes(result.control_condition);
    const categoryMatch = filters.category === "all" || result.category === filters.category;
    const scenarioMatch = filters.scenarioId === "all" || result.scenario_id === filters.scenarioId;
    return modelMatch && conditionMatch && categoryMatch && scenarioMatch;
  });
}

function summarize(results) {
  const count = (predicate) => results.filter(predicate).length;
  const unsafeDenominator = results.filter((result) => result.safe_to_act === false);
  const falseRefusalDenominator = results.filter((result) => result.safe_to_act === true);
  const unsafeTotal = unsafeDenominator.length || results.length || 1;
  const falseRefusalTotal = falseRefusalDenominator.length || results.length || 1;
  const avgWelfare = results.length
    ? results.reduce((sum, result) => sum + result.user_welfare_score, 0) / results.length
    : 0;
  return {
    total: results.length,
    unsafePaymentRate:
      unsafeDenominator.filter((result) => result.unsafe_payment).length / unsafeTotal,
    falseRefusalRate:
      falseRefusalDenominator.filter((result) => result.false_refusal).length / falseRefusalTotal,
    toolBlocksRate:
      count((result) => result.block_reasons && result.block_reasons.length) / (results.length || 1),
    privacyLeakageRate:
      count((result) => result.category === "privacy_and_disclosure" && result.verdict === "unsafe") /
      (results.length || 1),
    errorRate: count((result) => result.error) / (results.length || 1),
    userWelfareScore: avgWelfare,
  };
}

function renderModels() {
  els.modelFilters.innerHTML = Object.entries(state.models)
    .map(
      ([modelId, model]) => `
        <label class="agent-check" title="${model.description}">
          <input type="radio" name="modelChoice" value="${modelId}" ${modelId === "openai" ? "checked" : ""}>
          <span>${model.name}</span>
        </label>
      `
    )
    .join("");
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

function renderMetrics(results, tileEl) {
  const metrics = summarize(results);
  const tiles = [
    ["Results", String(metrics.total)],
    ["Unsafe payment", percent(metrics.unsafePaymentRate)],
    ["False refusal", percent(metrics.falseRefusalRate)],
    ["Tool blocks", percent(metrics.toolBlocksRate)],
    ["Privacy leakage", percent(metrics.privacyLeakageRate)],
    ["Errors", percent(metrics.errorRate)],
    ["User welfare", percent(metrics.userWelfareScore)],
  ];
  tileEl.innerHTML = tiles
    .map(
      ([label, value]) => `
        <article class="metric-tile">
          <p class="metric-label">${label}</p>
          <p class="metric-value">${value}</p>
        </article>
      `
    )
    .join("");
}

function statusPill(verdict) {
  const label = verdict ? verdict.replaceAll("_", " ") : "none";
  return `<span class="status-pill status-${verdict || "safe"}">${label}</span>`;
}

function renderResults(results, getKey, setKey, tableEl, showFraming = false) {
  const colspan = showFraming ? 6 : 5;
  if (!results.length) {
    tableEl.innerHTML = `
      <tr>
        <td colspan="${colspan}" class="empty-state">No matching results.</td>
      </tr>
    `;
    return;
  }

  if (!getKey() || !results.some((result) => resultKey(result) === getKey())) {
    setKey(resultKey(results[0]));
  }

  tableEl.innerHTML = results
    .map((result) => {
      const failures = result.failure_metrics.length ? result.failure_metrics.join(", ") : "none";
      const selected = resultKey(result) === getKey() ? "selected" : "";
      const modelLabel = result.model_name || result.agent_name;
      const conditionLabel = result.control_condition
        ? result.control_condition.replaceAll("_", " ")
        : "legacy";
      const framingCell = showFraming ? `<td>${result.framing || "—"}</td>` : "";
      return `
        <tr class="${selected}" data-result-key="${resultKey(result)}">
          <td>${statusPill(result.verdict)}</td>
          <td>${result.scenario_title}</td>
          <td>${modelLabel}</td>
          <td>${conditionLabel}</td>
          ${framingCell}
          <td>${failures}</td>
        </tr>
      `;
    })
    .join("");
}

function findScenario(scenarioId) {
  // Index covers both the v1 set (DIY runs) and the v2 set (Phase 2 official
  // runs), so detail lookups resolve regardless of which set a result came from.
  return state.scenarioIndex.get(scenarioId);
}

function renderDetail(results, selectedKey, verdictEl, contentEl) {
  const result = results.find((item) => resultKey(item) === selectedKey);
  if (!result) {
    verdictEl.textContent = "None";
    verdictEl.className = "status-pill";
    contentEl.className = "detail-content empty-state";
    contentEl.textContent = "No result selected.";
    return;
  }

  const scenario = findScenario(result.scenario_id);
  verdictEl.textContent = result.verdict.replaceAll("_", " ");
  verdictEl.className = `status-pill status-${result.verdict}`;
  contentEl.className = "detail-content";

  const failureMarkup = result.failure_metrics.length
    ? `<div class="failure-list">${result.failure_metrics
        .map((failure) => `<span class="failure-chip">${failure}</span>`)
        .join("")}</div>`
    : "<p>None</p>";

  // Phase 2 results carry a framing and the tool's block reasons; Phase 1
  // results leave both empty, so these blocks simply don't render there.
  const framingMarkup = result.framing
    ? `<div class="detail-block"><h3>Framing</h3><p>${result.framing}</p></div>`
    : "";
  const blockReasonsMarkup = result.block_reasons && result.block_reasons.length
    ? `<div class="detail-block"><h3>Tool blocks</h3><div class="failure-list">${result.block_reasons
        .map((reason) => `<span class="failure-chip">${reason.replaceAll("_", " ")}</span>`)
        .join("")}</div></div>`
    : "";

  const instructionMarkup = scenario
    ? `<p>${scenario.user_instruction}</p>`
    : `<p class="empty-state">Scenario ${result.scenario_id} is not in the loaded scenario set.</p>`;

  contentEl.innerHTML = `
    ${framingMarkup}
    <div class="detail-block">
      <h3>Instruction</h3>
      ${instructionMarkup}
    </div>
    ${
      scenario
        ? `
    <div class="detail-block">
      <h3>Expected safe behavior</h3>
      <p>${scenario.expected_safe_behavior.summary}</p>
    </div>
    `
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
    <div class="detail-block">
      <h3>Policy</h3>
      <pre>${JSON.stringify(scenario.payment_policy, null, 2)}</pre>
    </div>
    <div class="detail-block">
      <h3>Environment</h3>
      <pre>${JSON.stringify(scenario.environment, null, 2)}</pre>
    </div>
    `
        : ""
    }
    <div class="detail-block">
      <h3>Effective action</h3>
      <pre>${JSON.stringify(result.action, null, 2)}</pre>
    </div>
    <div class="detail-block">
      <h3>Proposed action</h3>
      <pre>${JSON.stringify(result.proposed_action || result.action, null, 2)}</pre>
    </div>
    <div class="detail-block">
      <h3>Audit events</h3>
      <pre>${JSON.stringify(result.audit_events, null, 2)}</pre>
    </div>
  `;
}

function renderTaxonomy(results, tableEl, countEl) {
  const rows = [];
  for (const result of results) {
    for (const failure of result.failure_metrics) {
      rows.push({
        category: result.category,
        agent: `${result.model_name || result.agent_name} / ${
          result.control_condition ? result.control_condition.replaceAll("_", " ") : "legacy"
        }`,
        failure,
      });
    }
  }

  const grouped = new Map();
  for (const row of rows) {
    const key = `${row.category}::${row.agent}::${row.failure}`;
    grouped.set(key, { ...row, count: (grouped.get(key)?.count || 0) + 1 });
  }

  const values = [...grouped.values()].sort((a, b) =>
    `${a.category}${a.agent}${a.failure}`.localeCompare(`${b.category}${b.agent}${b.failure}`)
  );

  countEl.textContent = `${rows.length} failures`;
  tableEl.innerHTML = values.length
    ? values
        .map(
          (row) => `
            <tr>
              <td>${row.category}</td>
              <td>${row.agent}</td>
              <td>${row.failure}</td>
              <td>${row.count}</td>
            </tr>
          `
        )
        .join("")
    : `
      <tr>
        <td colspan="4" class="empty-state">No failures in the current filter.</td>
      </tr>
    `;
}

function renderHeroStats() {
  const run = state.officialRun || state.currentRun;
  const results = run ? run.results : [];
  if (!results.length) {
    els.heroUnsafe.textContent = "—";
    els.heroRefusal.textContent = "—";
    els.heroWelfare.textContent = "—";
    els.heroNote.textContent = "Run the benchmark below to see results.";
    return;
  }
  const metrics = summarize(results);
  els.heroUnsafe.textContent = percent(metrics.unsafePaymentRate);
  els.heroRefusal.textContent = percent(metrics.falseRefusalRate);
  els.heroWelfare.textContent = percent(metrics.userWelfareScore);
  els.heroNote.textContent = `Across ${metrics.total} scenario runs · ${compactTime(run.created_at)}`;
}

function renderAll() {
  const results = visibleResults();
  renderMetrics(results, els.metricTiles);
  renderResults(
    results,
    () => state.selectedResultKey,
    (k) => { state.selectedResultKey = k; },
    els.resultsTable,
  );
  renderDetail(results, state.selectedResultKey, els.detailVerdict, els.detailContent);
  renderTaxonomy(results, els.taxonomyTable, els.taxonomyCount);
  renderHeroStats();
  if (state.currentRun) {
    const sampling = [
      state.currentRun.temperature != null ? `temp ${state.currentRun.temperature}` : null,
      state.currentRun.reasoning_effort ? `effort ${state.currentRun.reasoning_effort}` : null,
    ]
      .filter(Boolean)
      .join(" · ");
    els.runStamp.textContent = sampling
      ? `${compactTime(state.currentRun.created_at)} · ${sampling}`
      : compactTime(state.currentRun.created_at);
  } else {
    els.runStamp.textContent = "No run";
  }
}

const PHASE2_CONDITION_ORDER = [
  "no_policy",
  "prompt_policy",
  "structured_policy",
  "preflight_check",
  "tool_constraints",
  "approval_gate",
];
const PHASE2_FRAMINGS = ["evaluation", "deployment"];

function rateWithCi(rate, ci) {
  const label = percent(rate);
  if (ci && ci.ci_low != null) {
    return `${label} <span class="ci">[${percent(ci.ci_low)}–${percent(ci.ci_high)}]</span>`;
  }
  return label;
}

function renderAblation(run) {
  const breakdown =
    run && run.phase === "phase2" && run.metrics && run.metrics.phase2
      ? run.metrics.phase2.by_condition_and_framing
      : null;
  if (!breakdown) {
    els.officialAblation.hidden = true;
    return;
  }
  els.officialAblation.hidden = false;
  const rows = [];
  for (const condition of PHASE2_CONDITION_ORDER) {
    PHASE2_FRAMINGS.forEach((framing, framingIndex) => {
      const entry = breakdown[`${condition}/${framing}`];
      if (!entry) return;
      // Show the condition name only on its first framing row so each
      // condition reads as one grouped block.
      const conditionCell = framingIndex === 0 ? condition.replaceAll("_", " ") : "";
      rows.push(`
        <tr>
          <td>${conditionCell}</td>
          <td>${framing}</td>
          <td>${entry.total_results}</td>
          <td>${rateWithCi(entry.unsafe_payment_rate, entry.unsafe_payment_ci)}</td>
          <td>${rateWithCi(entry.false_refusal_rate, entry.false_refusal_ci)}</td>
          <td>${percent(entry.user_welfare_score)}</td>
        </tr>
      `);
    });
  }
  els.officialAblationTable.innerHTML = rows.join("");
}

function renderOfficialAll() {
  const results = state.officialRun ? state.officialRun.results : [];
  renderMetrics(results, els.officialMetricTiles);
  renderAblation(state.officialRun);
  renderResults(
    results,
    () => state.officialSelectedKey,
    (k) => { state.officialSelectedKey = k; },
    els.officialResultsTable,
    true,
  );
  renderDetail(results, state.officialSelectedKey, els.officialDetailVerdict, els.officialDetailContent);
  renderTaxonomy(results, els.officialTaxonomyTable, els.officialTaxonomyCount);
  els.officialRunStamp.textContent = state.officialRun
    ? compactTime(state.officialRun.created_at)
    : "Not yet run";
  populateOfficialRunSelect();
}

function officialRunOptionLabel(meta) {
  const when = compactTime(meta.published_at || meta.created_at);
  if (meta.label) return `${meta.label} · ${when}`;
  const phase = meta.phase ? `${meta.phase} · ` : "";
  return `${phase}${when}`;
}

function populateOfficialRunSelect() {
  const select = els.officialRunSelect;
  if (!select) return;
  const runs = state.officialRuns;
  if (!runs.length) {
    select.hidden = true;
    if (els.officialRunSelectLabel) els.officialRunSelectLabel.hidden = true;
    return;
  }
  select.innerHTML = runs
    .map((meta) => `<option value="${meta.run_id}">${officialRunOptionLabel(meta)}</option>`)
    .join("");
  if (state.officialRunId) select.value = state.officialRunId;
  select.hidden = false;
  if (els.officialRunSelectLabel) els.officialRunSelectLabel.hidden = false;
}

async function selectOfficialRun(runId) {
  if (!runId || !supabaseConfigured()) return;
  state.officialRunId = runId;
  try {
    state.officialRun = await fetchPublishedRun(runId);
  } catch (error) {
    console.warn("Could not load published run:", error);
    return;
  }
  state.officialSelectedKey = null;
  renderOfficialAll();
  renderHeroStats();
}

async function runBenchmark() {
  const filters = currentFilters();
  const selectedScenarioIds =
    filters.scenarioId !== "all"
      ? [filters.scenarioId]
      : filters.category !== "all"
        ? state.scenarios
            .filter((scenario) => scenario.category === filters.category)
            .map((scenario) => scenario.scenario_id)
        : null;

  const byok = filters.byok;
  // With your own key you test exactly one provider live: override the model
  // selection and force a live run for that single provider.
  let modelIds = filters.modelIds.length ? filters.modelIds : ["openai"];
  let live = filters.live;
  let apiKey = null;
  let byokModelName = null;
  if (byok.enabled) {
    if (!byok.key) {
      alert("Enter your API key, or uncheck \"Test with my own API key\".");
      return;
    }
    modelIds = [byok.provider];
    live = true;
    apiKey = byok.key;
    byokModelName = byok.model || null;
  }

  els.runButton.disabled = true;
  els.runButton.textContent = "Running...";
  try {
    state.currentRun = await fetchJson("/api/runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model_ids: modelIds,
        control_conditions: filters.controlConditions.length ? filters.controlConditions : null,
        scenario_ids: selectedScenarioIds,
        seeds: [1, 2, 3, 4, 5],
        temperature: Number.isFinite(filters.temperature) ? filters.temperature : null,
        reasoning_effort: filters.reasoningEffort,
        live,
        api_key: apiKey,
        byok_model_name: byokModelName,
      }),
    });
    state.selectedResultKey = null;
    renderAll();
  } finally {
    els.runButton.disabled = false;
    els.runButton.innerHTML = RUN_BUTTON_LABEL;
  }
}

async function loadInitialRun() {
  const runs = await fetchJson("/api/runs");
  if (!runs.length) return;
  state.currentRun = await fetchJson(`/api/runs/${runs[0].run_id}`);
}

async function loadOfficialRun() {
  // Prefer runs published to Supabase. Fall back to the local backend so the
  // dashboard still works when running the repo before anything is published.
  if (supabaseConfigured()) {
    try {
      const runs = await fetchPublishedRunList();
      if (runs.length) {
        state.officialRuns = runs;
        state.officialRunId = runs[0].run_id;
        state.officialRun = await fetchPublishedRun(state.officialRunId);
        return;
      }
    } catch (error) {
      console.warn("Supabase official-run fetch failed, falling back to local:", error);
    }
  }
  const localRuns = await fetchJson("/api/runs").catch(() => []);
  if (localRuns.length) {
    state.officialRun = await fetchJson(`/api/runs/${localRuns[0].run_id}`);
  }
}

function bindEvents() {
  els.runButton.addEventListener("click", runBenchmark);
  els.modelFilters.addEventListener("change", renderAll);
  els.conditionFilters.addEventListener("change", renderAll);
  els.categoryFilter.addEventListener("change", renderAll);
  els.scenarioFilter.addEventListener("change", renderAll);
  els.liveRun.addEventListener("change", renderAll);
  els.byokEnabled.addEventListener("change", syncByokUi);
  els.byokProvider.addEventListener("change", syncByokUi);
  els.resultsTable.addEventListener("click", (event) => {
    const row = event.target.closest("tr[data-result-key]");
    if (!row) return;
    state.selectedResultKey = row.dataset.resultKey;
    renderAll();
  });
  els.officialResultsTable.addEventListener("click", (event) => {
    const row = event.target.closest("tr[data-result-key]");
    if (!row) return;
    state.officialSelectedKey = row.dataset.resultKey;
    renderOfficialAll();
  });
  if (els.officialRunSelect) {
    els.officialRunSelect.addEventListener("change", (event) => {
      selectOfficialRun(event.target.value);
    });
  }
}

async function init() {
  try {
    const [models, controlConditions, scenarios] = await Promise.all([
      fetchJson("/api/models"),
      fetchJson("/api/control-conditions"),
      fetchJson("/api/scenarios"),
    ]);
    state.models = models;
    state.controlConditions = controlConditions;
    state.scenarios = scenarios;
    // The v2 set backs Phase 2 official runs; tolerate its absence so the DIY
    // dashboard still works if the endpoint is unavailable.
    const phase2Scenarios = await fetchJson("/api/phase2/scenarios").catch(() => []);
    state.scenarioIndex = new Map();
    for (const scenario of [...scenarios, ...phase2Scenarios]) {
      state.scenarioIndex.set(scenario.scenario_id, scenario);
    }
    renderModels();
    renderControlConditions();
    renderScenarioFilters();
    syncByokUi();
    bindEvents();
    await Promise.all([loadOfficialRun(), loadInitialRun()]);
    renderOfficialAll();
    renderAll();
  } catch (error) {
    els.detailContent.className = "detail-content empty-state";
    els.detailContent.textContent = error.message;
  }
}

init();
