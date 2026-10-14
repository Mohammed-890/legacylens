"use strict";
const $ = (s) => document.querySelector(s);
const $$ = (s) => [...document.querySelectorAll(s)];
const escapeHTML = (v) =>
  String(v).replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
let project,
  demo,
  recorded,
  report,
  patch,
  selected,
  local = false,
  token = "",
  modelReady = false,
  imported = false,
  city = true,
  busy = false,
  investigationId = 0;
const pageCopy = {
  overview: [
    "System overview",
    "Make the invisible <em>visible.</em>",
    "From tangled source to a clear picture. Explore what connects, what breaks, and why.",
  ],
  investigation: [
    "Investigate",
    "Every answer needs <em>evidence.</em>",
    "Follow the source, inspect the tools, and keep uncertainty in view.",
  ],
  repair: [
    "Repair lab",
    "A change you can <em>prove.</em>",
    "Reproduce the failure. Review the patch. Verify the outcome.",
  ],
  evaluation: [
    "Evaluations",
    "Put the claims <em>to the test.</em>",
    "Transparent measurements, real outputs, and reproducible checks.",
  ],
};
function toast(message) {
  $("#toast").textContent = message;
  $("#toast").hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => ($("#toast").hidden = true), 5500);
}
function showPage(page) {
  if (!pageCopy[page]) page = "overview";
  $$(".page").forEach((el) => el.classList.toggle("active", el.id === page));
  $$(".nav-item").forEach((el) =>
    el.classList.toggle("active", el.dataset.page === page),
  );
  $("#crumb").textContent = pageCopy[page][0];
  $("#page-title").innerHTML = pageCopy[page][1];
  $("#page-description").textContent = pageCopy[page][2];
  if (location.hash !== "#" + page) history.replaceState(null, "", "#" + page);
}
async function request(path, data) {
  const response = await fetch(path, {
    method: data ? "POST" : "GET",
    headers: data
      ? { "Content-Type": "application/json", "X-LegacyLens-Token": token }
      : {},
    body: data ? JSON.stringify(data) : undefined,
  });
  if (!response.ok) {
    let message = "Request failed";
    try {
      message = (await response.json()).error || message;
    } catch {}
    throw new Error(message);
  }
  return response.json();
}
function saveFile(name, text, type = "text/plain") {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function source(path, line = 1) {
  $("#source-title").textContent = path + (line ? " · line " + line : "");
  const lines = project.files[path]?.split("\n") || ["File unavailable"];
  $("#source-code").textContent = lines
    .map(
      (l, i) =>
        `${String(i + 1).padStart(3)} ${i + 1 === line ? "→" : " "} ${l}`,
    )
    .join("\n");
  $("#source-dialog").showModal();
  $("#source-code").scrollTop = Math.max(0, (line - 6) * 21);
}
function getImpact(path) {
  const visited = new Set([path]);
  let queue = [path];
  while (queue.length) {
    const cur = queue.shift();
    project.edges.forEach((e) => {
      if (e.target === cur && !visited.has(e.source)) {
        visited.add(e.source);
        queue.push(e.source);
      }
    });
  }
  return [...visited].filter((p) => p !== path);
}
function renderStats() {
  const s = project.stats;
  $("#stats").innerHTML = [
    ["Source files", s.files, "indexed", "⌑"],
    ["Import links", project.edges.length, "static edges", "⌁"],
    ["Functions", s.functions, "discovered", "ƒ"],
    ["Review signals", s.findings, "need a look", "↯"],
  ]
    .map(
      ([title, note, sub, icon], i) =>
        `<div class="stat ${i === 3 ? "alert" : ""}"><div class="stat-top">${title}<span class="stat-icon">${icon}</span></div><strong>${String(note).padStart(2, "0")}</strong><small>${sub}</small></div>`,
    )
    .join("");
  $("#project-name").textContent = project.name;
  $("#fingerprint").textContent = "SHA " + project.fingerprint;
  $("#sidebar-repo").textContent = imported
    ? project.name
    : "northstar / billing-service";
}
function selectFile(id) {
  selected = id;
  renderMap();
  renderInspector();
}
function renderMap() {
  const nodes = project.nodes.slice(0, 40),
    positions = {};
  const count = nodes.length,
    cols = Math.ceil(Math.sqrt(count));
  nodes.forEach((n, i) => {
    const row = Math.floor(i / cols),
      col = i % cols;
    positions[n.id] = city
      ? { x: 320 + (col - row) * 77, y: 112 + (col + row) * 38 }
      : {
          x: 320 + Math.cos((i / count) * Math.PI * 2 - Math.PI / 2) * 220,
          y: 175 + Math.sin((i / count) * Math.PI * 2 - Math.PI / 2) * 120,
        };
  });
  let svg =
    '<svg viewBox="0 0 640 370" role="img" aria-label="Repository map. Buildings represent source files; lines represent Python imports."><defs><pattern id="grid" width="36" height="20" patternUnits="userSpaceOnUse" patternTransform="matrix(1,.5,-1,.5,320,20)"><path d="M 36 0 L 0 0 0 20" fill="none" stroke="#34432c" stroke-width=".6"/></pattern><marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#8aab69"/></marker></defs><rect width="640" height="370" fill="url(#grid)" opacity=".45"/>';
  project.edges.forEach((e) => {
    if (!positions[e.source] || !positions[e.target]) return;
    const a = positions[e.source],
      b = positions[e.target];
    svg += `<path d="M${a.x} ${a.y} Q${(a.x + b.x) / 2} ${Math.min(a.y, b.y) - 30} ${b.x} ${b.y}" class="edge ${e.target === selected || e.source === selected ? "selected" : ""}" marker-end="url(#arrow)"/>`;
  });
  [...nodes]
    .sort((a, b) => positions[a.id].y - positions[b.id].y)
    .forEach((n) => {
      const { x, y } = positions[n.id];
      const h = Math.min(82, 22 + n.lines * 1.05);
      const active = n.id === selected,
        orange = n.issues > 0,
        blue = n.kind !== "module";
      const top = orange ? "#b78558" : blue ? "#739391" : "#8aab67",
        left = orange ? "#6d4d32" : blue ? "#3c605b" : "#4b6737",
        right = orange ? "#493923" : blue ? "#304947" : "#334c28",
        stroke = active ? "#e0f5ab" : orange ? "#ad8256" : "#6e8b51";
      svg += `<g class="file-building" data-file="${escapeHTML(n.id)}" tabindex="0" role="button" aria-label="Inspect ${escapeHTML(n.id)}, ${n.lines} lines, ${n.issues} findings"><title>${escapeHTML(n.id)}</title>`;
      if (city) {
        svg += `<ellipse cx="${x}" cy="${y + 10}" rx="43" ry="17" fill="#0a1008" opacity=".65"/><path d="M${x - 24} ${y - h} L${x} ${y - h + 13} L${x} ${y + 13} L${x - 24} ${y}Z" fill="${left}" stroke="${stroke}" stroke-width=".7"/><path d="M${x} ${y - h + 13} L${x + 24} ${y - h} L${x + 24} ${y} L${x} ${y + 13}Z" fill="${right}" stroke="${stroke}" stroke-width=".7"/><path d="M${x - 24} ${y - h} L${x} ${y - h - 13} L${x + 24} ${y - h} L${x} ${y - h + 13}Z" fill="${top}" stroke="${stroke}" stroke-width="1"/>`;
        for (let k = 14; k < h; k += 12)
          svg += `<path d="M${x - 18} ${y - h + k} l5 3 M${x - 9} ${y - h + k + 5} l5 3 M${x + 6} ${y - h + k + 5} l5 -3 M${x + 15} ${y - h + k} l5 -3" stroke="${active ? "#dcf7a3" : "#a7c785"}" opacity=".5" stroke-width="3"/>`;
        if (active)
          svg += `<path d="M${x - 34} ${y + 3} L${x} ${y + 22} L${x + 34} ${y + 3}" fill="none" stroke="#d7ed9b" stroke-width="1.4"/>`;
      } else
        svg += `<rect x="${x - 38}" y="${y - 22}" width="76" height="44" rx="7" fill="${right}" stroke="${stroke}" stroke-width="${active ? 2 : 1}"/><text x="${x}" y="${y + 4}" text-anchor="middle">${n.lines} LOC</text>`;
      svg += `<text x="${x}" y="${y + (city ? 38 : 40)}" text-anchor="middle" class="${active ? "selected-label" : ""}">${escapeHTML(n.label.length > 18 ? n.label.slice(0, 16) + "…" : n.label)}</text></g>`;
    });
  svg += "</svg>";
  $("#map").innerHTML = svg;
  $$(".file-building").forEach((el) => {
    el.addEventListener("click", () => selectFile(el.dataset.file));
    el.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        selectFile(el.dataset.file);
      }
    });
  });
}
function renderInspector() {
  const n = project.nodes.find((n) => n.id === selected) || project.nodes[0];
  selected = n.id;
  const affected = getImpact(n.id);
  $("#inspector-content").innerHTML =
    `<div class="file-icon">${n.kind === "module" ? "ƒ" : n.kind === "database" ? "▤" : "≡"}</div><h3 class="file-title">${escapeHTML(n.label)}</h3><p class="file-sub">${escapeHTML(n.kind)} · ${n.lines} lines of source</p><div class="file-detail">Defined functions<strong>${n.functions.length}</strong></div><div class="file-detail">Importers affected<strong>${affected.length}</strong></div><div class="file-detail">Static findings<strong>${n.issues}</strong></div><h4>CHANGE IMPACT</h4>${
      affected.length
        ? affected
            .slice(0, 7)
            .map((p) => `<span class="impact-chip">${escapeHTML(p)}</span>`)
            .join("")
        : '<span class="muted">No importers found in this snapshot.</span>'
    }<button class="button" id="inspect-source">Read source <span>↗</span></button>${project.warnings.some((w) => w.path === n.id) ? '<p class="file-warning">Parse warning: imports may be incomplete.</p>' : ""}<p class="file-sub" style="">Import dependencies only. Building height reflects file length.</p>`;
  $("#inspect-source").onclick = () => source(n.id);
}
function renderFindings() {
  const fs = project.findings;
  $("#finding-count").textContent =
    `${fs.length} findings · ${project.warnings.length} parse warnings`;
  $("#findings").innerHTML = fs.length
    ? fs
        .map(
          (f) =>
            `<button class="finding-row" data-path="${escapeHTML(f.path)}" data-line="${f.line}"><span class="severity ${f.severity}">${f.severity}</span><strong>${escapeHTML(f.title)}</strong><code>${escapeHTML(f.path)}:${f.line}</code><span class="arrow">↗</span></button>`,
        )
        .join("")
    : '<p class="empty-copy">No configured rule matched. This is not a guarantee of correctness or security.</p>';
  $$(".finding-row").forEach(
    (el) =>
      (el.onclick = () => source(el.dataset.path, Number(el.dataset.line))),
  );
}
function renderProject() {
  selected = project.files["invoices.py"] ? "invoices.py" : project.nodes[0].id;
  renderStats();
  renderMap();
  renderInspector();
  renderFindings();
}
function lexicalSearch(question) {
  const terms = [
    ...new Set(question.toLowerCase().match(/[a-z][a-z0-9_]+/g) || []),
  ];
  return project.chunks
    .map((c) => ({
      ...c,
      score: terms.reduce(
        (s, t) => s + (c.path + " " + c.text).toLowerCase().split(t).length - 1,
        0,
      ),
    }))
    .filter((c) => c.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, 5);
}
async function investigateQuestion(question) {
  if (busy) return;
  busy = true;
  const myId = ++investigationId;
  $("#investigate-button").disabled = true;
  $("#investigate-button").textContent = "Investigating…";
  $("#answer").innerHTML =
    '<p class="busy">Reading source and collecting evidence…</p>';
  showPage("investigation");
  try {
    let result;
    if (local) {
      result = await request("/api/investigate", {
        project: imported ? project.fingerprint : "demo",
        question,
        use_llm: $("#use-llm").checked,
      });
    } else {
      const evidence = lexicalSearch(question);
      result = {
        mode: "browser-evidence",
        answer: evidence.length
          ? "These source windows match your question. Inspect the producer, consumer and runbook together before deciding the cause."
          : "No relevant evidence found. Try a file name, function or exact error.",
        evidence,
        trace: [
          {
            tool: "lexical_search",
            status: "complete",
            detail: `Matched ${evidence.length} source windows in the recorded repository snapshot.`,
          },
        ],
        limitation:
          "Browser demo uses keyword retrieval. Run locally with a configured provider for a live tool-calling investigation.",
      };
    }
    if (myId !== investigationId) return;
    $("#answer").innerHTML =
      `<div class="question-label">${escapeHTML(question)}</div><span class="tiny-label">${escapeHTML(result.mode)}</span><h3>Investigation findings</h3><p>${escapeHTML(result.answer)}</p><p class="muted">${escapeHTML(result.limitation || "")}</p>${result.usage ? `<p class="muted">${result.usage.input_tokens} input tokens · ${result.usage.output_tokens} output tokens${result.elapsed_ms ? " · " + (result.elapsed_ms / 1000).toFixed(1) + "s" : ""}</p>` : ""}`;
    $("#evidence").innerHTML =
      (result.trace || [])
        .map(
          (t) =>
            `<div class="trace-item"><strong>${t.status === "complete" ? "✓" : "!"} ${escapeHTML(t.tool)}</strong><p>${escapeHTML(t.detail)}</p></div>`,
        )
        .join("") +
      (result.evidence || [])
        .map(
          (c) =>
            `<article class="evidence-card"><div class="evidence-head"><span>${escapeHTML(c.id)}</span><button data-path="${escapeHTML(c.path)}" data-line="${c.start}">${escapeHTML(c.path)}:${c.start}–${c.end} ↗</button></div><pre>${escapeHTML(c.text)}</pre></article>`,
        )
        .join("");
    $$(".evidence-head button").forEach(
      (el) =>
        (el.onclick = () => source(el.dataset.path, Number(el.dataset.line))),
    );
  } catch (e) {
    $("#answer").innerHTML =
      `<h3>Investigation interrupted</h3><p>${escapeHTML(e.message)}</p><p class="muted">Your source is unchanged. Try local evidence mode.</p>`;
  } finally {
    busy = false;
    $("#investigate-button").disabled = false;
    $("#investigate-button").innerHTML = "Investigate <span>↗</span>";
  }
}
function renderPatch() {
  $("#diff").innerHTML = patch.diff
    .split("\n")
    .map(
      (l) =>
        `<span class="${l.startsWith("+") ? "added" : l.startsWith("-") ? "removed" : "context"}">${escapeHTML(l) || " "}</span>`,
    )
    .join("");
  if (!local) {
    $("#run-repair").innerHTML = "Replay verified repair <span>↗</span>";
    $("#repair-scope").textContent =
      "Hosted demo: replays recorded output from five real fixture tests. Run the local app to execute them yourself.";
  }
}
async function runRepair() {
  if (!$("#approve").checked) return;
  const btn = $("#run-repair");
  btn.disabled = true;
  btn.textContent = local ? "Running fixture tests…" : "Loading test evidence…";
  try {
    const result = local
      ? await request("/api/repair", { approved: true, proposal_id: patch.id })
      : recorded;
    $("#repair-results").innerHTML =
      `<div class="run-banner">${result.verified ? "✓ Repair verified" : "! Verification failed"}<small>${local ? "Executed now in a disposable directory" : "Recorded test replay · " + escapeHTML(result.recorded_at || "")} · ${result.tests} tests</small></div><div class="timeline-step"><span>01</span><div><strong>Original implementation: ${result.before.passed ? "passed" : "failed"}</strong><p>Exit code ${result.before.exit_code}. Failure reproduced before changing code.</p></div></div><div class="timeline-step"><span>02</span><div><strong>Approved patch applied</strong><p>Invoice field aligned with schema v2.</p></div></div><div class="timeline-step"><span>03</span><div><strong>Patched implementation: ${result.after.passed ? "passed" : "failed"}</strong><p>Exit code ${result.after.exit_code} · ${result.elapsed_ms} ms total execution time</p></div></div><details><summary>Original test output</summary><pre class="run-output">${escapeHTML(result.before.output)}</pre></details><details open><summary>Patched test output</summary><pre class="run-output">${escapeHTML(result.after.output)}</pre></details><p class="muted">${escapeHTML(result.environment)}</p>`;
    toast(
      local
        ? "Five fixture tests completed. Review the output."
        : "Showing recorded test evidence.",
    );
  } catch (e) {
    toast(e.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML =
      (local ? "Run verification again" : "Replay verified repair") +
      " <span>↗</span>";
  }
}
function renderEvaluations() {
  const passed = report.cases.filter((c) => c.passed).length;
  $("#eval-stats").innerHTML = [
    ["Checks passed", `${passed}/${report.cases.length}`, "recorded"],
    ["Rule coverage", report.rule_count, "static rules"],
    ["Repair suite", recorded.tests, "actual tests"],
    ["LLM benchmark", "—", "not evaluated"],
  ]
    .map(
      ([t, n, s]) =>
        `<div class="stat"><div class="stat-top">${t}</div><strong>${n}</strong><small>${s}</small></div>`,
    )
    .join("");
  $("#eval-date").textContent =
    report.generated_at.slice(0, 10) + " · Python " + report.python;
  $("#eval-table").innerHTML =
    '<table class="eval-table"><thead><tr><th>CASE</th><th>CHECK</th><th>RESULT</th></tr></thead><tbody>' +
    report.cases
      .map(
        (c) =>
          `<tr><td>${escapeHTML(c.id)}</td><td>${escapeHTML(c.name)}</td><td class="${c.passed ? "pass" : "fail"}">${c.passed ? "✓ PASS" : "✕ FAIL"}</td></tr>`,
      )
      .join("") +
    "</tbody></table>";
}
async function importFolder(event) {
  if (!local) {
    toast(
      "Repository import requires the local Python app. See GitHub for the one-command setup.",
    );
    return;
  }
  const chosen = [...event.target.files];
  if (!chosen.length) return;
  const files = {},
    accepted = /\.(py|sql|md|txt|json|yaml|yml|toml)$/i;
  let bytes = 0;
  try {
    for (const f of chosen) {
      const parts = (f.webkitRelativePath || f.name).split("/");
      const path = parts.length > 1 ? parts.slice(1).join("/") : f.name;
      if (
        parts.some(
          (p) =>
            p.startsWith(".") ||
            ["node_modules", "venv", "__pycache__"].includes(p),
        ) ||
        !accepted.test(path) ||
        f.name === "credentials.json"
      )
        continue;
      bytes += f.size;
      if (bytes > 2000000 || Object.keys(files).length >= 160)
        throw new Error("Import up to 160 supported files, 2 MB total.");
      files[path] = await f.text();
    }
    project = await request("/api/analyze", {
      files,
      name: (chosen[0].webkitRelativePath || chosen[0].name).split("/")[0],
    });
    imported = true;
    investigationId++;
    renderProject();
    $("#notice").hidden = false;
    $("#notice").textContent =
      "Imported repository · read-only analysis in local memory. Repair lab continues to use the bundled Northstar fixture.";
    $("#answer").innerHTML =
      "<h3>Repository ready.</h3><p>Ask a question about the imported source.</p>";
    $("#evidence").innerHTML = "";
    showPage("overview");
    toast(
      "Repository indexed. " + project.stats.files + " files ready to explore.",
    );
  } catch (e) {
    toast(e.message);
  }
  event.target.value = "";
}
async function init() {
  try {
    [demo, recorded, report, patch] = await Promise.all(
      ["demo.json", "repair.json", "evaluations.json", "proposal.json"].map(
        (p) => request(p),
      ),
    );
    try {
      const status = await request("/api/status");
      local = status.mode === "local";
      token = status.token;
      modelReady = status.llm;
    } catch {}
    project = demo;
    $("#mode").textContent = local ? "● LOCAL WORKSPACE" : "● INTERACTIVE DEMO";
    $("#agent-label").textContent = modelReady
      ? "AGENT AVAILABLE"
      : "LOCAL EVIDENCE";
    $("#use-llm").disabled = !modelReady;
    $("#llm-hint").textContent = modelReady
      ? "· sends source to configured provider"
      : "· no API key needed for evidence";
    renderProject();
    renderPatch();
    renderEvaluations();
    showPage(location.hash.slice(1));
  } catch (e) {
    $("#notice").hidden = false;
    $("#notice").textContent =
      "Workspace could not load. Serve this folder over HTTP and ensure demo assets were generated. " +
      e.message;
  }
}
$$(".nav-item").forEach((el) => (el.onclick = () => showPage(el.dataset.page)));
window.addEventListener("hashchange", () => showPage(location.hash.slice(1)));
$("#city-view").onclick = () => {
  city = true;
  $("#city-view").classList.add("active");
  $("#graph-view").classList.remove("active");
  renderMap();
};
$("#graph-view").onclick = () => {
  city = false;
  $("#graph-view").classList.add("active");
  $("#city-view").classList.remove("active");
  renderMap();
};
$("#about-button").onclick = () => $("#about-dialog").showModal();
$("#close-about").onclick = () => $("#about-dialog").close();
$("#close-source").onclick = () => $("#source-dialog").close();
$("#import-button").onclick = () =>
  local
    ? $("#folder-input").click()
    : toast(
        "Import runs in the local app. Open GitHub for setup instructions.",
      );
$("#folder-input").onchange = importFolder;
$("#reset-demo").onclick = () => {
  if (busy) return toast("Wait for the current investigation to finish.");
  project = demo;
  imported = false;
  $("#notice").hidden = true;
  $("#answer").innerHTML =
    "<h3>Northstar loaded.</h3><p>Ask a question about the billing service.</p>";
  $("#evidence").innerHTML = "";
  renderProject();
  showPage("overview");
};
$("#question-form").onsubmit = (e) => {
  e.preventDefault();
  const q = $("#question").value.trim();
  if (q) investigateQuestion(q);
};
$$("[data-question]").forEach(
  (el) =>
    (el.onclick = () => {
      $("#question").value = el.dataset.question;
      investigateQuestion(el.dataset.question);
    }),
);
$("#approve").onchange = () =>
  ($("#run-repair").disabled = !$("#approve").checked);
$("#run-repair").onclick = runRepair;
$("#download-patch").onclick = () =>
  saveFile("INC-042-invoice-schema.patch", patch.diff);
$("#download-report").onclick = () =>
  saveFile(
    "legacylens-evaluation.json",
    JSON.stringify(report, null, 2),
    "application/json",
  );
document.addEventListener("keydown", (e) => {
  if (["INPUT", "TEXTAREA"].includes(e.target.tagName) || $("dialog[open]"))
    return;
  const p = Object.keys(pageCopy)[Number(e.key) - 1];
  if (p) showPage(p);
});
init();
