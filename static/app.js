const state = {
  models: {},
  controlConditions: {},
  scenarios: [],
  currentRun: null,
  selectedResultKey: null,
};

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
  temperatureInput: document.querySelector("#temperatureInput"),
  reasoningEffort: document.querySelector("#reasoningEffort"),
  metricTiles: document.querySelector("#metricTiles"),
  resultsTable: document.querySelector("#resultsTable"),
  runStamp: document.querySelector("#runStamp"),
  detailVerdict: document.querySelector("#detailVerdict"),
  detailContent: document.querySelector("#detailContent"),
  taxonomyTable: document.querySelector("#taxonomyTable"),
  taxonomyCount: document.querySelector("#taxonomyCount"),
  heroUnsafe: document.querySelector("#heroUnsafe"),
  heroRefusal: document.querySelector("#heroRefusal"),
  heroWelfare: document.querySelector("#heroWelfare"),
  heroNote: document.querySelector("#heroNote"),
};

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
  const checkedModels = [...els.modelFilters.querySelectorAll("input:checked")].map(
    (input) => input.value
  );
  const checkedConditions = [...els.conditionFilters.querySelectorAll("input:checked")].map(
    (input) => input.value
  );
  return {
    modelIds: checkedModels,
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

const BYOK_MODEL_PLACEHOLDER = {
  openai: "e.g. gpt-4o",
  anthropic: "e.g. claude-sonnet-4-6",
};

function syncByokUi() {
  if (!els.byokFields) return;
  els.byokFields.hidden = !els.byokEnabled.checked;
  if (els.byokModel) {
    els.byokModel.placeholder = BYOK_MODEL_PLACEHOLDER[els.byokProvider.value] || "model name";
  }
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
          <input type="checkbox" value="${modelId}" ${modelId === "openai" ? "checked" : ""}>
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

function renderMetrics(results) {
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
  els.metricTiles.innerHTML = tiles
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

function renderResults(results) {
  if (!results.length) {
    els.resultsTable.innerHTML = `
      <tr>
        <td colspan="5" class="empty-state">No matching results.</td>
      </tr>
    `;
    return;
  }

  if (!state.selectedResultKey || !results.some((result) => resultKey(result) === state.selectedResultKey)) {
    state.selectedResultKey = resultKey(results[0]);
  }

  els.resultsTable.innerHTML = results
    .map((result) => {
      const failures = result.failure_metrics.length ? result.failure_metrics.join(", ") : "none";
      const selected = resultKey(result) === state.selectedResultKey ? "selected" : "";
      const modelLabel = result.model_name || result.agent_name;
      const conditionLabel = result.control_condition
        ? result.control_condition.replaceAll("_", " ")
        : "legacy";
      return `
        <tr class="${selected}" data-result-key="${resultKey(result)}">
          <td>${statusPill(result.verdict)}</td>
          <td>${result.scenario_title}</td>
          <td>${modelLabel}</td>
          <td>${conditionLabel}</td>
          <td>${failures}</td>
        </tr>
      `;
    })
    .join("");
}

function findScenario(scenarioId) {
  return state.scenarios.find((scenario) => scenario.scenario_id === scenarioId);
}

function renderDetail(results) {
  const result = results.find((item) => resultKey(item) === state.selectedResultKey);
  if (!result) {
    els.detailVerdict.textContent = "None";
    els.detailVerdict.className = "status-pill";
    els.detailContent.className = "detail-content empty-state";
    els.detailContent.textContent = "No result selected.";
    return;
  }

  const scenario = findScenario(result.scenario_id);
  els.detailVerdict.textContent = result.verdict.replaceAll("_", " ");
  els.detailVerdict.className = `status-pill status-${result.verdict}`;
  els.detailContent.className = "detail-content";

  const failureMarkup = result.failure_metrics.length
    ? `<div class="failure-list">${result.failure_metrics
        .map((failure) => `<span class="failure-chip">${failure}</span>`)
        .join("")}</div>`
    : "<p>None</p>";

  const instructionMarkup = scenario
    ? `<p>${scenario.user_instruction}</p>`
    : `<p class="empty-state">Scenario ${result.scenario_id} is not in the loaded scenario set.</p>`;

  els.detailContent.innerHTML = `
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

function renderTaxonomy(results) {
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

  els.taxonomyCount.textContent = `${rows.length} failures`;
  els.taxonomyTable.innerHTML = values.length
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
  const results = state.currentRun ? state.currentRun.results : [];
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
  els.heroNote.textContent = `Across ${metrics.total} scenario runs · ${compactTime(state.currentRun.created_at)}`;
}

function renderAll() {
  const results = visibleResults();
  renderMetrics(results);
  renderResults(results);
  renderDetail(results);
  renderTaxonomy(results);
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
    els.runButton.innerHTML = '<span class="button-mark">></span>Run benchmark';
  }
}

async function loadInitialRun() {
  const runs = await fetchJson("/api/runs");
  if (!runs.length) return;
  state.currentRun = await fetchJson(`/api/runs/${runs[0].run_id}`);
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
    renderModels();
    renderControlConditions();
    renderScenarioFilters();
    syncByokUi();
    bindEvents();
    await loadInitialRun();
    renderAll();
  } catch (error) {
    els.detailContent.className = "detail-content empty-state";
    els.detailContent.textContent = error.message;
  }
}

init();
