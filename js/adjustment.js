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

  const loc = document.getElementById("adjLocation");
  if (loc) loc.addEventListener("change", e => { adjState.location = e.target.value; checkAdj(); });
  const mon = document.getElementById("adjMonth");
  if (mon) mon.addEventListener("change", e => { adjState.month = e.target.value; checkAdj(); });
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
  status.textContent = "Waking up server, then generating… (first run can take ~60s)";

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

    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${adjState.location.toUpperCase()}_${adjState.month.replace("-", "_")}_Adjustment_Details.xlsx`;
    a.click();
    URL.revokeObjectURL(url);

    status.innerHTML =
      `✅ Generated. Total Adjustment: <strong>${Number(total).toLocaleString("en-US",{minimumFractionDigits:2})}</strong> · `
      + `${rows} rows · <strong>${review}</strong> flagged for review (see the Review sheet). `
      + `Two transaction-only entries ("bill value 0", "sale date &gt; payment date") can't be derived — add manually if needed.`;
  } catch (err) {
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
