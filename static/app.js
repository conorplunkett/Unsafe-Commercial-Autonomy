const state = {
  agents: {},
  scenarios: [],
  currentRun: null,
  selectedResultKey: null,
};

const els = {
  runButton: document.querySelector("#runBenchmark"),
  agentFilters: document.querySelector("#agentFilters"),
  categoryFilter: document.querySelector("#categoryFilter"),
  scenarioFilter: document.querySelector("#scenarioFilter"),
  metricTiles: document.querySelector("#metricTiles"),
  resultsTable: document.querySelector("#resultsTable"),
  runStamp: document.querySelector("#runStamp"),
  detailVerdict: document.querySelector("#detailVerdict"),
  detailContent: document.querySelector("#detailContent"),
  taxonomyTable: document.querySelector("#taxonomyTable"),
  taxonomyCount: document.querySelector("#taxonomyCount"),
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
  return `${result.scenario_id}::${result.agent_id}`;
}

function currentFilters() {
  const checkedAgents = [...els.agentFilters.querySelectorAll("input:checked")].map(
    (input) => input.value
  );
  return {
    agentIds: checkedAgents,
    category: els.categoryFilter.value,
    scenarioId: els.scenarioFilter.value,
  };
}

function visibleResults() {
  if (!state.currentRun) return [];
  const filters = currentFilters();
  return state.currentRun.results.filter((result) => {
    const agentMatch = filters.agentIds.length === 0 || filters.agentIds.includes(result.agent_id);
    const categoryMatch = filters.category === "all" || result.category === filters.category;
    const scenarioMatch = filters.scenarioId === "all" || result.scenario_id === filters.scenarioId;
    return agentMatch && categoryMatch && scenarioMatch;
  });
}

function summarize(results) {
  const total = results.length || 1;
  const count = (predicate) => results.filter(predicate).length;
  const avgWelfare = results.length
    ? results.reduce((sum, result) => sum + result.user_welfare_score, 0) / results.length
    : 0;
  return {
    total: results.length,
    unsafePaymentRate: count((result) => result.unsafe_payment) / total,
    falseRefusalRate: count((result) => result.false_refusal) / total,
    approvalFailureRate:
      count((result) =>
        result.failure_metrics.some((failure) =>
          ["approval_failure", "approval_threshold_evasion"].includes(failure)
        )
      ) / total,
    privacyLeakageRate:
      count((result) => result.failure_metrics.includes("privacy_leakage")) / total,
    paidToolOveruseRate:
      count((result) => result.failure_metrics.includes("unnecessary_paid_tool_usage")) / total,
    userWelfareScore: avgWelfare,
  };
}

function renderAgents() {
  els.agentFilters.innerHTML = Object.entries(state.agents)
    .map(
      ([agentId, agent]) => `
        <label class="agent-check" title="${agent.description}">
          <input type="checkbox" value="${agentId}" checked>
          <span>${agent.name}</span>
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
    ["Approval failure", percent(metrics.approvalFailureRate)],
    ["Privacy leakage", percent(metrics.privacyLeakageRate)],
    ["Paid-tool overuse", percent(metrics.paidToolOveruseRate)],
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
        <td colspan="4" class="empty-state">No matching results.</td>
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
      return `
        <tr class="${selected}" data-result-key="${resultKey(result)}">
          <td>${statusPill(result.verdict)}</td>
          <td>${result.scenario_title}</td>
          <td>${result.agent_name}</td>
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

  els.detailContent.innerHTML = `
    <div class="detail-block">
      <h3>Instruction</h3>
      <p>${scenario.user_instruction}</p>
    </div>
    <div class="detail-block">
      <h3>Policy</h3>
      <pre>${JSON.stringify(scenario.payment_policy, null, 2)}</pre>
    </div>
    <div class="detail-block">
      <h3>Environment</h3>
      <pre>${JSON.stringify(scenario.environment, null, 2)}</pre>
    </div>
    <div class="detail-block">
      <h3>Agent action</h3>
      <pre>${JSON.stringify(result.action, null, 2)}</pre>
    </div>
    <div class="detail-block">
      <h3>Expected safe behavior</h3>
      <p>${scenario.expected_safe_behavior.summary}</p>
    </div>
    <div class="detail-block">
      <h3>Failure metrics</h3>
      ${failureMarkup}
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
        agent: result.agent_name,
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

function renderAll() {
  const results = visibleResults();
  renderMetrics(results);
  renderResults(results);
  renderDetail(results);
  renderTaxonomy(results);
  els.runStamp.textContent = state.currentRun ? compactTime(state.currentRun.created_at) : "No run";
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

  els.runButton.disabled = true;
  els.runButton.textContent = "Running...";
  try {
    state.currentRun = await fetchJson("/api/runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        agent_ids: filters.agentIds.length ? filters.agentIds : null,
        scenario_ids: selectedScenarioIds,
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
  els.agentFilters.addEventListener("change", renderAll);
  els.categoryFilter.addEventListener("change", renderAll);
  els.scenarioFilter.addEventListener("change", renderAll);
  els.resultsTable.addEventListener("click", (event) => {
    const row = event.target.closest("tr[data-result-key]");
    if (!row) return;
    state.selectedResultKey = row.dataset.resultKey;
    renderAll();
  });
}

async function init() {
  try {
    const [agents, scenarios] = await Promise.all([
      fetchJson("/api/agents"),
      fetchJson("/api/scenarios"),
    ]);
    state.agents = agents;
    state.scenarios = scenarios;
    renderAgents();
    renderScenarioFilters();
    bindEvents();
    await loadInitialRun();
    renderAll();
  } catch (error) {
    els.detailContent.className = "detail-content empty-state";
    els.detailContent.textContent = error.message;
  }
}

init();

