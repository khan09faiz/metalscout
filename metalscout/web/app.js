// MetalScout dashboard. Plain JS, no build step.
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const safeUrl = (u) => (/^https?:\/\//i.test(u || "") ? u : "#");
const src = (u) => (u ? ` <a class="src" href="${esc(safeUrl(u))}" target="_blank" rel="noopener">source</a>` : "");
const STAGES = ["lead", "contacted", "replied", "quoted", "won", "lost", "not_fit"];
let LEADS = [], wasRunning = false;

async function api(path, opts) {
  const r = await fetch(path, opts);
  return r.json();
}

// ---------- tabs
document.querySelectorAll(".tabs button").forEach((b) =>
  b.addEventListener("click", () => {
    document.querySelectorAll(".tabs button").forEach((x) => x.classList.toggle("on", x === b));
    document.querySelectorAll("main > section").forEach((s) => (s.hidden = s.id !== "tab-" + b.dataset.tab));
    if (b.dataset.tab === "signals") loadSignals();
    if (b.dataset.tab === "runs") loadRuns();
    if (b.dataset.tab === "agents") loadAgents();
  })
);

// ---------- status
async function loadStatus() {
  const s = await api("/api/status");
  $("#biz").textContent = s.business;
  const c = s.counts;
  $("#kLeads").textContent = c.leads; $("#kA").textContent = c.A; $("#kB").textContent = c.B;
  $("#kNew").textContent = c.new_today; $("#kSig").textContent = c.signals; $("#kQueue").textContent = c.queued;
  $("#kAI").textContent = c.ai_leads ?? 0;
  $("#kNext").textContent = s.next_run;
  const lr = s.last_run;
  $("#kLast").textContent = lr ? `last: ${lr.started_h} (${lr.status})` : "no runs yet";
  const st = $("#runstate");
  st.textContent = s.running ? "running…" : lr ? `last run ${lr.status}` : "idle";
  st.className = "pill " + (s.running ? "running" : lr && lr.status === "failed" ? "failed" : "");
  $("#runBtn").disabled = s.running;
  $("#runBtn").textContent = s.running ? "Running…" : "Find leads now";
  if (wasRunning || s.running) loadLeads();
  if (wasRunning && !s.running) loadRuns();
  wasRunning = s.running;
}

// ---------- leads
async function loadLeads() {
  LEADS = await api("/api/leads?all=1");
  const metals = [...new Set(LEADS.flatMap((l) => l.metals))].sort();
  const sel = $("#metal"), cur = sel.value;
  sel.innerHTML = '<option value="">All metals</option>' + metals.map((m) => `<option ${m === cur ? "selected" : ""}>${esc(m)}</option>`).join("");
  renderLeads();
}

function renderLeads() {
  const q = $("#q").value.toLowerCase(), tier = $("#tier").value, metal = $("#metal").value;
  const rows = LEADS.filter((l) =>
    ($("#showTraders").checked || l.org_type !== "trader") &&
    (!tier || l.tier === tier) && (!metal || l.metals.includes(metal)) &&
    (!$("#onlyNew").checked || l.is_new) &&
    (!$("#withContact").checked || l.emails.length || l.phones.length) &&
    (!q || JSON.stringify([l.name, l.domain, l.metals, l.reasons, l.found_via]).toLowerCase().includes(q))
  );
  $("#count").textContent = `${rows.length} shown`;
  $("#empty").hidden = LEADS.length > 0;
  $("#leadRows").innerHTML = rows.map((l) => `<tr data-id="${l.id}">
    <td><span class="t ${l.tier}">${l.tier}</span></td><td>${l.score}</td>
    <td><b>${esc(l.name)}</b>${l.is_new ? '<span class="new-badge">new</span>' : ""}${l.ai && l.ai.has_any ? '<span class="ai-badge">AI</span>' : ""}<br><span class="muted">${esc(l.domain)}</span>${l.org_type === "trader" ? '<br><span class="trader">trader</span>' : ""}</td>
    <td>${esc(l.metals.join(", "))}</td>
    <td>${l.quantity.map((x) => esc(x.value)).join("<br>")}</td>
    <td>${l.emails.slice(0, 2).map((x) => esc(x.value) + src(x.source)).join("<br>")}</td>
    <td>${l.phones.slice(0, 2).map((x) => esc(x.value) + src(x.source)).join("<br>")}</td>
    <td class="muted">${esc(l.reasons.join("; "))}</td>
    <td>${esc(l.stage)}</td></tr>`).join("");
}
["#q", "#tier", "#metal", "#onlyNew", "#withContact", "#showTraders"].forEach((s) => $(s).addEventListener("input", renderLeads));

$("#leadRows").addEventListener("click", (e) => {
  if (e.target.closest("a")) return;
  const tr = e.target.closest("tr");
  if (tr) openLead(LEADS.find((l) => l.id === +tr.dataset.id));
});

function list(title, items) {
  if (!items.length) return "";
  return `<h4>${title}</h4><ul>${items.map((x) => `<li>${esc(x.value)}${src(x.source)}${x.evidence && x.evidence !== "own domain" && x.evidence !== "other domain" ? `<span class="ev">“${esc(x.evidence)}”</span>` : ""}</li>`).join("")}</ul>`;
}

function openLead(l) {
  $("#drawerBody").innerHTML = `
    <h2>${esc(l.name)}</h2>
    <a href="${esc(safeUrl(l.website))}" target="_blank" rel="noopener">${esc(l.domain)}</a> · <span class="t ${l.tier}">${l.tier}</span> ${l.score}/100 · ${esc(l.org_type)}
    <h4>Why</h4><p>${esc(l.reasons.join("; "))}</p>
    <h4>Metals</h4><p>${esc(l.metals.join(", ") || "none seen")}</p>
    ${list("Quantity", l.quantity)}${list("Emails", l.emails)}${list("Phones", l.phones)}
    ${list("GSTIN", l.gstin)}${list("CIN", l.cin)}${list("Udyam", l.udyam)}${list("IEC", l.iec)}
    ${l.certifications.length ? `<h4>Certifications</h4><p>${esc(l.certifications.join(", "))}</p>` : ""}
    ${l.contact_page ? `<h4>Contact page</h4><a href="${esc(safeUrl(l.contact_page))}" target="_blank" rel="noopener">${esc(l.contact_page)}</a>` : ""}
    ${l.vendor_page ? `<h4>Vendor / procurement page</h4><a href="${esc(safeUrl(l.vendor_page))}" target="_blank" rel="noopener">${esc(l.vendor_page)}</a>` : ""}
    ${aiSection(l.ai)}
    <h4>Found via</h4><p class="muted">${esc(l.found_via)} · first seen ${esc(l.first_seen)} · checked ${esc(l.last_profiled)} · ${l.pages_read} pages read</p>
    <h4>Pipeline stage</h4>
    <select id="dStage">${STAGES.map((s) => `<option ${s === l.stage ? "selected" : ""}>${s}</option>`).join("")}</select>
    <h4>Notes</h4><textarea id="dNotes" rows="4">${esc(l.notes)}</textarea>
    <button class="primary" id="dSave">Save</button> <span id="dMsg" class="muted"></span>`;
  $("#drawer").hidden = false;
  $("#dSave").onclick = async () => {
    await api(`/api/lead/${l.id}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ stage: $("#dStage").value, notes: $("#dNotes").value }) });
    l.stage = $("#dStage").value; l.notes = $("#dNotes").value; $("#dMsg").textContent = "saved"; renderLeads();
  };
}
function aiSection(ai) {
  if (!ai || !ai.has_any) return "";
  const o = ai.org_type;
  const draft = ai.outreach;
  return `<div class="aibox"><h4>AI analysis (every fact verified on the site)</h4>
    ${o ? `<p>Type: <b>${esc(o.value)}</b> (${Math.round((o.confidence || 0) * 100)}% sure)${src(o.source)}<span class="ev">“${esc(o.evidence)}”</span></p>` : ""}
    ${list("Raw materials", ai.materials)}${list("Volume", ai.volume)}${list("Products", ai.products)}
    ${list("People", ai.people)}${list("Buying signals", ai.buying_signals)}
    ${draft ? `<h4>Draft first email (not sent)</h4>${draft.warning ? `<p class="warn">⚠ ${esc(draft.warning)}. These figures are not in the facts found on the site; check them before sending.</p>` : ""}<div class="draft" id="dDraft"><b>${esc(draft.subject)}</b>\n\n${esc(draft.body)}</div>
      <button id="copyDraft">Copy email</button>` : ""}</div>`;
}
document.addEventListener("click", (e) => {
  if (e.target.id === "copyDraft") {
    navigator.clipboard.writeText($("#dDraft").innerText).then(() => (e.target.textContent = "Copied"));
  }
});
$("#closeDrawer").onclick = () => ($("#drawer").hidden = true);
document.addEventListener("keydown", (e) => e.key === "Escape" && ($("#drawer").hidden = true));

// ---------- signals / runs
async function loadSignals() {
  const s = await api("/api/signals");
  $("#sigRows").innerHTML = s.map((r) => `<tr><td>${r.intent}</td><td>${esc(r.kind)}${r.restricted ? '<br><span class="muted">not opened</span>' : ""}</td>
    <td><a href="${esc(safeUrl(r.url))}" target="_blank" rel="noopener">${esc(r.title || r.url)}</a><br><span class="muted">${esc((r.snippet || "").slice(0, 180))}</span></td>
    <td>${esc(r.metals.join(", "))}${agentItems(r.agent)}</td><td>${esc(r.quantity.join("; "))}</td>
    <td>${esc([...r.emails, ...r.phones].join(", "))}</td><td class="muted">${esc(r.first_seen)}</td></tr>`).join("") ||
    '<tr><td colspan="7" class="empty">No buyer signals yet.</td></tr>';
}

function agentItems(a) {
  if (!a || a.is_buyer_request === undefined) return "";
  if (!a.is_buyer_request) return '<br><span class="muted">AI: not a buy request</span>';
  const items = (a.items || []).map((i) => [i.metal, i.spec, i.quantity].filter(Boolean).join(" ")).join("; ");
  return `<br><span class="ai-badge">AI</span> ${esc(a.buyer || "buyer?")}${items ? ": " + esc(items) : ""}${a.deadline ? " · due " + esc(a.deadline) : ""}`;
}

async function loadAgents() {
  const d = await api("/api/agents");
  $("#agentCards").innerHTML = d.agents.map((a) => `<div class="card"><h4>${esc(a.name)} <span class="tier">${esc(a.tier)}</span></h4>
    <div class="muted">${esc(a.job)}</div>
    <div class="nums"><div><b>${a.calls}</b>calls</div><div><b>${a.ok}</b>ok</div><div><b>${a.rejected}</b>rejected</div></div>
    <div class="models">${esc(a.models.join(", ") || (a.tier === "rules" ? "no model" : "not run yet"))}</div></div>`).join("");
  $("#providers").innerHTML = d.providers.map((p) => `<span class="chip ${p.configured ? "on" : "off"}">${esc(p.name)}${p.configured ? " ✓" : ""}</span>`).join("");
  $("#modelRows").innerHTML = d.by_model.map((s) => `<tr><td>${esc(s.agent)}</td><td>${esc(s.provider)}</td><td>${esc(s.model)}</td>
    <td>${s.calls}</td><td>${s.ok}</td><td>${s.rejected}</td><td>${Math.round(s.avg_ms || 0)} ms</td></tr>`).join("") ||
    '<tr><td colspan="7" class="empty">No agent calls yet.</td></tr>';
}

async function loadRuns() {
  const runs = await api("/api/runs");
  $("#runRows").innerHTML = runs.map((r) => {
    const s = r.stats || {};
    return `<tr><td>${esc(r.id)}</td><td>${esc(r.trigger)}</td><td>${esc(r.status)}</td><td>${s.queries ?? "–"}</td><td>${s.new_companies ?? "–"}</td>
      <td>${s.profiled ?? "–"}</td><td>${s.profile_failed ?? "–"}</td><td>${s.new_signals ?? "–"}</td>
      <td>${s.agent_facts ?? "–"} / ${s.agent_rejected ?? "–"}</td>
      <td class="muted">${esc((r.errors || []).slice(0, 3).join(" | "))}</td></tr>`;
  }).join("") || '<tr><td colspan="10" class="empty">No runs yet.</td></tr>';
  $("#log").textContent = (await api("/api/log")).join("");
}

// ---------- actions
async function startRun(stages) {
  $("#runBtn").disabled = true;
  const r = await fetch("/api/run", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(stages ? { stages } : {}) });
  if (r.status === 409) alert("A run is already in progress.");
  setTimeout(loadStatus, 1500);
}
$("#runBtn").onclick = () => startRun();

async function addSites(profileNow) {
  const urls = $("#urls").value.split(/\s+/).filter(Boolean);
  if (!urls.length) return;
  const r = await api("/api/add", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ urls }) });
  $("#addMsg").textContent = `${r.added} new site(s) queued`;
  $("#urls").value = "";
  if (profileNow) startRun("profile,export");
  loadStatus();
}
$("#addBtn").onclick = () => addSites(false);
$("#profileBtn").onclick = () => addSites(true);

loadStatus(); loadLeads();
setInterval(loadStatus, 5000);
