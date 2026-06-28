// ── Adjustment tab ─────────────────────────────────────────────
// Independent of the reconciliation wizard. Diffs prior-month CLOSING
// vs current-month OPENING debtors CSVs and downloads the Adjustment
// Details .xlsx (with low-confidence rows flagged on a Review sheet).
const ADJ_API_URL = "https://stelco-recon-api.onrender.com";

const ADJ_LOCATIONS = {
  male: "Male'", hulhumale: "Hulhumale'", thilafushi: "Thilafushi", gulhi_falhu: "Gulhi Falhu",
};
const ADJ_SLOTS = [
  { key: "adj_close_csv", label: "Prior Month Closing Debtors", icon: "🧾",
    desc: "Previous month CLOSING debtors export (.csv)" },
  { key: "adj_open_csv",  label: "Current Month Opening Debtors", icon: "📄",
    desc: "This month OPENING debtors export (.csv)" },
];

const adjFiles = {};
const adjState = { location: "male", month: null };

function renderAdjustmentTab() {
  const grid = document.getElementById("adjUploadGrid");
  if (!grid) return;
  grid.innerHTML = "";
  ADJ_SLOTS.forEach(slot => {
    const div = document.createElement("div");
    div.className = "upload-slot";
    div.id = `adjslot_${slot.key}`;
    div.innerHTML = `
      <div class="slot-icon">${slot.icon}</div>
      <div class="slot-info">
        <div class="slot-name">${slot.label}</div>
        <div class="slot-desc">${slot.desc}</div>
      </div>
      <span class="slot-badge req">Required</span>
      <div class="file-input-wrap">
        <label class="file-btn" id="adjbtn_${slot.key}">
          Choose
          <input type="file" accept=".csv" data-key="${slot.key}" onchange="onAdjFileChosen(this)">
        </label>
      </div>`;
    grid.appendChild(div);
  });

  renderWorking();

  const loc = document.getElementById("adjLocation");
  if (loc) loc.addEventListener("change", e => { adjState.location = e.target.value; checkAdj(); });
  const mon = document.getElementById("adjMonth");
  if (mon) mon.addEventListener("change", e => { adjState.month = e.target.value; checkAdj(); });
}

// ── Step visualizer ────────────────────────────────────────────
const adjFmt = n => (n === null || n === undefined || isNaN(n)) ? ""
  : Number(n).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

// Each step mirrors the manual method; fill() derives its live value from the summary.
const WORK_STEPS = [
  { t: "Compare closing vs opening", d: "VLOOKUP each invoice's balance across both files",
    fill: s => `Closing ${adjFmt(s.close_total)} · Opening ${adjFmt(s.open_total)}` },
  { t: "Subtract & drop matches", d: "open − close per invoice; zero rows removed",
    fill: s => `${s.n_rows} adjustments · net ${adjFmt(s.total_adjustment)}` },
  { t: "Back-dated payment entries", d: "same invoice in both — balances netted",
    fill: s => `${s.reason_counts["Back Dated Payment Entry"] || 0} rows` },
  { t: "Cancelled & re-created invoices", d: "paired by account + ref (+ small-bill prints)",
    fill: s => `${s.reason_counts["The invoice was created after the report was taken"] || 0} created · `
             + `${s.reason_counts["The bill was amended after the report was taken"] || 0} amended · `
             + `${s.reason_counts["Small bill print"] || 0} small-bill` },
  { t: "Cancelled payments", d: "invoice with a payment entry and a balance",
    fill: s => `${s.reason_counts["Payment Cancelled Entry"] || 0} rows` },
  { t: "Finalise & flag", d: "build the file; flag low-confidence rows",
    fill: s => `Total ${adjFmt(s.total_adjustment)} · ${s.n_review} flagged` },
];

let workTimer = null;

function renderWorking() {
  const wrap = document.getElementById("adjWorking");
  if (!wrap) return;
  wrap.innerHTML = "";
  WORK_STEPS.forEach((st, i) => {
    const row = document.createElement("div");
    row.className = "work-step pending";
    row.id = `work_${i}`;
    row.innerHTML = `
      <div class="work-dot">${i + 1}</div>
      <div class="work-body">
        <div class="work-step-title">${st.t}</div>
        <div class="work-step-desc">${st.d}</div>
        <div class="work-step-val" id="workval_${i}"></div>
      </div>`;
    wrap.appendChild(row);
  });
}

function setWorkState(i, state) {
  const row = document.getElementById(`work_${i}`);
  if (!row) return;
  row.className = `work-step ${state}`;
  if (state !== "active" && state !== "error") row.querySelector(".work-dot").textContent = state === "done" ? "✓" : (i + 1);
}

function startWorkingAnimation() {
  renderWorking();
  let i = 0;
  setWorkState(0, "active");
  workTimer = setInterval(() => {
    setWorkState(i, "done");
    i++;
    if (i < WORK_STEPS.length) setWorkState(i, "active");
    else clearInterval(workTimer);
  }, 750);
}

function finishWorking(summary) {
  clearInterval(workTimer);
  WORK_STEPS.forEach((st, i) => {
    setWorkState(i, "done");
    const v = document.getElementById(`workval_${i}`);
    if (v) try { v.textContent = st.fill(summary); } catch (e) {}
  });
}

function errorWorking() {
  clearInterval(workTimer);
  for (let i = 0; i < WORK_STEPS.length; i++) {
    const row = document.getElementById(`work_${i}`);
    if (row && row.classList.contains("active")) { setWorkState(i, "error"); break; }
  }
}

function onAdjFileChosen(input) {
  const key = input.dataset.key;
  const file = input.files[0];
  if (!file) return;
  adjFiles[key] = file;
  document.getElementById(`adjslot_${key}`).classList.add("filled");
  const btn = document.getElementById(`adjbtn_${key}`);
  btn.classList.add("chosen");
  btn.childNodes[0].textContent = file.name.length > 16 ? file.name.slice(0, 14) + "…" : file.name;
  checkAdj();
}

function checkAdj() {
  const ready = adjFiles.adj_close_csv && adjFiles.adj_open_csv && adjState.month;
  const btn = document.getElementById("adjGenerateBtn");
  if (btn) btn.disabled = !ready;
}

async function generateAdjustment() {
  const btn = document.getElementById("adjGenerateBtn");
  const status = document.getElementById("adjStatus");
  btn.disabled = true;
  status.className = "review-note";
  status.textContent = "Waking up server, then generating… (first run can take ~60s)";
  startWorkingAnimation();

  try {
    try { await fetch(`${ADJ_API_URL}/`, { signal: AbortSignal.timeout(90000) }); } catch (e) {}

    const form = new FormData();
    form.append("location", adjState.location);
    form.append("adjustment_month", `${adjState.month}-01`); // YYYY-MM -> YYYY-MM-01
    form.append("adj_close_csv", adjFiles.adj_close_csv);
    form.append("adj_open_csv",  adjFiles.adj_open_csv);

    const res = await fetch(`${ADJ_API_URL}/adjustments`, {
      method: "POST", body: form, signal: AbortSignal.timeout(180000),
    });
    if (!res.ok) throw new Error(await res.text());

    const total  = res.headers.get("X-Adjustment-Total");
    const rows   = res.headers.get("X-Adjustment-Rows");
    const review = res.headers.get("X-Adjustment-Review");
    let summary = null;
    const sumHdr = res.headers.get("X-Adjustment-Summary");
    if (sumHdr) { try { summary = JSON.parse(atob(sumHdr)); } catch (e) {} }
    if (summary) finishWorking(summary);
    else { clearInterval(workTimer); WORK_STEPS.forEach((_, i) => setWorkState(i, "done")); }

    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${adjState.location.toUpperCase()}_${adjState.month.replace("-", "_")}_Adjustment_Details.xlsx`;
    a.click();
    URL.revokeObjectURL(url);

    status.className = "review-note adj-status-ok";
    status.innerHTML =
      `✅ Generated. Total Adjustment: <strong>${adjFmt(total)}</strong> · `
      + `${rows} rows · <strong>${review}</strong> flagged for review (see the Review sheet). `
      + `Two transaction-only entries ("bill value 0", "sale date &gt; payment date") can't be derived — add manually if needed.`;
  } catch (err) {
    errorWorking();
    status.className = "review-note adj-status-err";
    status.textContent = `Error: ${err.message}`;
  } finally {
    btn.disabled = false;
  }
}

// Tab switching: show #adjustmentTab / hide the reconciliation wizard
function showTab(name) {
  document.getElementById("reconTab").style.display   = name === "recon" ? "block" : "none";
  document.getElementById("adjustmentTab").style.display = name === "adjustment" ? "block" : "none";
  document.querySelectorAll(".top-tab").forEach(t =>
    t.classList.toggle("active", t.dataset.tab === name));
  if (name === "adjustment") renderAdjustmentTab();
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".top-tab").forEach(t =>
    t.addEventListener("click", () => showTab(t.dataset.tab)));
  const gen = document.getElementById("adjGenerateBtn");
  if (gen) gen.addEventListener("click", generateAdjustment);
});
