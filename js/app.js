// ── Config ────────────────────────────────────────────────────
const API_URL = "https://stelco-recon-api.onrender.com";

// ── State ─────────────────────────────────────────────────────
const state = {
  step:      1,
  location:  null,
  month:     null,
  date:      null,
  figures:   {},
  calcResult: null,
};

// ── File slots per location ────────────────────────────────────
const FILE_SLOTS = {
  male: [
    { key: "open_pdf",       label: "Opening Debtors Summary", icon: "📂", desc: "Debtors Summary As At [opening date]",  required: true  },
    { key: "close_pdf",      label: "Closing Debtors Summary", icon: "📁", desc: "Debtors Summary As At [closing date]", required: true  },
    { key: "sales_pdf",      label: "Sales Report",            icon: "📊", desc: "Sales Report for the month",           required: true  },
    { key: "misc_open_pdf",  label: "MISC Opening Summary",    icon: "📂", desc: "MISC Bills Debtors Summary (opening)", required: false },
    { key: "misc_close_pdf", label: "MISC Closing Summary",    icon: "📁", desc: "MISC Bills Debtors Summary (closing)", required: false },
    { key: "misc_sales_pdf", label: "MISC Sales Report",       icon: "📊", desc: "MISC Bills Sales Report",             required: false },
    { key: "recon_pdf",      label: "Payment Reconciliation",  icon: "🧾", desc: "Payment Reconciliation Report Summary",required: true  },
    { key: "collection_pdf", label: "Credits Summary",         icon: "💳", desc: "Cash Collection Credits Summary",     required: true  },
  ],
  hulhumale: [
    { key: "open_pdf",            label: "Opening Debtors Summary", icon: "📂", desc: "Debtors Summary As At [opening date]",  required: true  },
    { key: "close_pdf",           label: "Closing Debtors Summary", icon: "📁", desc: "Debtors Summary As At [closing date]", required: true  },
    { key: "sales_pdf",           label: "Sales Report",            icon: "📊", desc: "Sales Report for the month",           required: true  },
    { key: "misc_open_pdf",       label: "MISC Opening Summary",    icon: "📂", desc: "MISC Bills Debtors Summary (opening)", required: false },
    { key: "misc_close_pdf",      label: "MISC Closing Summary",    icon: "📁", desc: "MISC Bills Debtors Summary (closing)", required: false },
    { key: "misc_sales_pdf",      label: "MISC Sales Report",       icon: "📊", desc: "MISC Bills Sales Report",             required: false },
    { key: "recon_pdf",           label: "Payment Reconciliation",  icon: "🧾", desc: "Payment Reconciliation Report Summary",required: true  },
    { key: "collection_pdf",      label: "Credits Summary",         icon: "💳", desc: "Cash Collection Credits Summary",     required: true  },
    { key: "billing_pdf",         label: "Billing System Collection", icon: "🧮", desc: "Electric fee subtotal, excl. GST / cost of service / ERP", required: true },
    { key: "cash_collection_pdf", label: "Cash Collection Report",    icon: "🏦", desc: "Collections Dept report — Blueridge + WAMCO only",           required: true },
  ],
  thilafushi: [
    { key: "open_pdf",       label: "Opening Debtors Summary", icon: "📂", desc: "Debtors Summary As At [opening date]",  required: true  },
    { key: "close_pdf",      label: "Closing Debtors Summary", icon: "📁", desc: "Debtors Summary As At [closing date]", required: true  },
    { key: "sales_pdf",      label: "Sales Report",            icon: "📊", desc: "Sales Report for the month",           required: true  },
    { key: "misc_open_pdf",  label: "MISC Opening Summary",    icon: "📂", desc: "MISC Bills Debtors Summary (opening)", required: false },
    { key: "misc_close_pdf", label: "MISC Closing Summary",    icon: "📁", desc: "MISC Bills Debtors Summary (closing)", required: false },
    { key: "misc_sales_pdf", label: "MISC Sales Report",       icon: "📊", desc: "MISC Bills Sales Report",             required: false },
    { key: "recon_pdf",      label: "Payment Reconciliation",  icon: "🧾", desc: "Payment Reconciliation Report Summary",required: true  },
    { key: "collection_pdf", label: "Credits Summary",         icon: "💳", desc: "Cash Collection Credits Summary",     required: true  },
  ],
  gulhi_falhu: [
    { key: "open_pdf",       label: "Opening Debtors Summary", icon: "📂", desc: "Debtors Summary As At [opening date]",  required: true  },
    { key: "close_pdf",      label: "Closing Debtors Summary", icon: "📁", desc: "Debtors Summary As At [closing date]", required: true  },
    { key: "sales_pdf",      label: "Sales Report",            icon: "📊", desc: "Sales Report for the month",           required: true  },
    { key: "misc_open_pdf",  label: "MISC Opening Summary",    icon: "📂", desc: "MISC Bills Debtors Summary (opening)", required: false },
    { key: "misc_close_pdf", label: "MISC Closing Summary",    icon: "📁", desc: "MISC Bills Debtors Summary (closing)", required: false },
    { key: "misc_sales_pdf", label: "MISC Sales Report",       icon: "📊", desc: "MISC Bills Sales Report",             required: false },
    { key: "recon_pdf",      label: "Payment Reconciliation",  icon: "🧾", desc: "Payment Reconciliation Report Summary",required: true  },
    { key: "collection_pdf", label: "Credits Summary",         icon: "💳", desc: "Cash Collection Credits Summary",     required: true  },
  ],
};

const LOCATION_NAMES = {
  male:        "Male'",
  hulhumale:   "Hulhumale'",
  thilafushi:  "Thilafushi",
  gulhi_falhu: "Gulhi Falhu",
};

// Review fields shown in step 3
const REVIEW_FIELDS = [
  { key: "elec_bf",           label: "Balance b/f (prior month c/f)",                               misc_key: "misc_bf"           },
  { key: "elec_adj1",         label: "Adjustments (1)",                                              misc_key: "misc_adj1",  optional: true },
  { key: "elec_sales",        label: "Total Sales/Additional Revenue",                               misc_key: "misc_sales"        },
  { key: "elec_credits",      label: "Credits / Fine",                                               misc_key: "misc_credits"      },
  { key: "elec_collection",   label: "Collection for the month",                                     misc_key: "misc_collection"   },
  { key: "elec_close_system", label: "Debtors Balance c/f (from close.pdf — verify at month-end)",  misc_key: "misc_close_system" },
];

// Hulhumale extra fields
const HULHUMALE_EXTRA = [
  { key: "billing_system", label: "Billing System Collection", misc_key: null },
  { key: "blueridge",      label: "Blueridge Collections",     misc_key: null },
  { key: "wamco",          label: "WAMCO Collections",         misc_key: null },
];

// ── Helpers ────────────────────────────────────────────────────
const fmt = (n) => {
  if (n === null || n === undefined || n === "") return "";
  const num = parseFloat(n);
  if (isNaN(num)) return String(n);
  const abs = Math.abs(num);
  const s = abs.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return num < 0 ? `(${s})` : s;
};

const parseNum = (s) => {
  if (!s) return 0;
  return parseFloat(String(s).replace(/[^0-9.-]/g, "")) || 0;
};

// ── Reconciliation snapshot (live statement preview) ───────────
// Mirrors reconciliation/calculator.py row math for the right-side preview.
function computeRecon(f) {
  f = f || {};
  const g = k => parseNum(f[k]);
  const has = k => f[k] !== undefined && f[k] !== null && f[k] !== "";
  const e_bf = g("elec_bf"), m_bf = g("misc_bf");
  const e_bfadj = has("elec_bfadj") ? g("elec_bfadj") : e_bf;
  const m_bfadj = has("misc_bfadj") ? g("misc_bfadj") : m_bf;
  const e_sales = g("elec_sales"), m_sales = g("misc_sales");
  const e_cr = g("elec_credits"), m_cr = g("misc_credits");
  const e_disc = g("elec_discount"), m_disc = g("misc_discount");
  const e_coll = g("elec_collection"), m_coll = g("misc_collection");
  const e_cf = g("elec_close_system"), m_cf = g("misc_close_system");
  const e_sub1 = e_bfadj + e_sales, m_sub1 = m_bfadj + m_sales;
  const e_sub2 = e_sub1 + e_cr + e_disc, m_sub2 = m_sub1 + m_cr + m_disc;
  const e_adj2 = e_cf - (e_sub2 - e_coll), m_adj2 = m_cf - (m_sub2 - m_coll);
  return [
    { label: "Balance b/f",            e: e_bf,    m: m_bf },
    { label: "Adjustments (1)",        e: e_bfadj - e_bf, m: m_bfadj - m_bf },
    { label: "Balance b/f (adj.)",     e: e_bfadj, m: m_bfadj, bold: true },
    { label: "Total Sales",            e: e_sales, m: m_sales },
    { label: "",                       e: e_sub1,  m: m_sub1, sub: true },
    { label: "Credits / Fine",         e: e_cr,    m: m_cr },
    { label: "Discount",               e: e_disc,  m: m_disc },
    { label: "",                       e: e_sub2,  m: m_sub2, sub: true },
    { label: "Collection",             e: -e_coll, m: -m_coll },
    { label: "Adjustments (2)",        e: e_adj2,  m: m_adj2 },
    { label: "Debtors Balance c/f",    e: e_cf,    m: m_cf, final: true },
  ];
}

function renderSnapshot() {
  const el = document.getElementById("reconSnapshot");
  if (!el) return;
  const hasFigures = state.figures && Object.keys(state.figures).length > 0;
  const rows = computeRecon(state.figures);
  const monthStr = state.month
    ? new Date(state.month + "-01").toLocaleString("en-US", { month: "long", year: "numeric" })
    : "—";
  const loc = LOCATION_NAMES[state.location] || "—";
  let html = `<div class="snap-head"><span>${loc}</span><span>${monthStr}</span></div>`;
  html += `<table class="snap-table"><thead><tr><th></th><th>Elec.</th><th>MISC</th></tr></thead><tbody>`;
  for (const r of rows) {
    const cls = `${r.bold ? "snap-bold " : ""}${r.sub ? "snap-sub " : ""}${r.final ? "snap-final " : ""}`.trim();
    const ev = hasFigures ? fmt(r.e) : "—";
    const mv = hasFigures ? fmt(r.m) : "—";
    html += `<tr class="${cls}"><td>${r.label}</td><td>${ev}</td><td>${mv}</td></tr>`;
  }
  html += `</tbody></table>`;
  if (!hasFigures) html += `<div class="snap-hint">Preview — fills in after Parse Files</div>`;
  el.innerHTML = html;
}

// ── Step navigation ────────────────────────────────────────────
function goToStep(n) {
  state.step = n;
  document.querySelectorAll(".step-panel").forEach(p => p.classList.remove("active"));
  document.getElementById(`panel${n}`).classList.add("active");

  document.querySelectorAll(".step-item").forEach(item => {
    const s = parseInt(item.dataset.step);
    item.classList.remove("active", "done");
    if (s === n) item.classList.add("active");
    else if (s < n) item.classList.add("done");
  });

  window.scrollTo(0, 0);

  if (n === 3) startParsing();
  if (n === 4) renderSummary();
}

// ── STEP 1 ─────────────────────────────────────────────────────
document.querySelectorAll(".loc-card").forEach(card => {
  card.addEventListener("click", () => {
    document.querySelectorAll(".loc-card").forEach(c => c.classList.remove("selected"));
    card.classList.add("selected");
    state.location = card.dataset.location;
    checkStep1();
  });
});

document.getElementById("reportMonth").addEventListener("change", (e) => {
  state.month = e.target.value;
  checkStep1();
});
document.getElementById("reportDate").addEventListener("change", (e) => {
  state.date = e.target.value;
  checkStep1();
});

function checkStep1() {
  document.getElementById("step1Next").disabled = !(state.location && state.month && state.date);
}

document.getElementById("step1Next").addEventListener("click", () => {
  renderUploadSlots();
  document.getElementById("locationLabel").textContent = LOCATION_NAMES[state.location];
  renderSnapshot();
  goToStep(2);
});

// ── STEP 2 ─────────────────────────────────────────────────────
const uploadedFiles = {};

function renderUploadSlots() {
  const grid = document.getElementById("uploadGrid");
  grid.innerHTML = "";
  const slots = FILE_SLOTS[state.location] || [];

  slots.forEach(slot => {
    const div = document.createElement("div");
    div.className = "upload-slot" + (slot.required ? "" : " optional");
    div.id = `slot_${slot.key}`;
    div.innerHTML = `
      <div class="slot-icon">${slot.icon}</div>
      <div class="slot-info">
        <div class="slot-name">${slot.label}</div>
        <div class="slot-desc">${slot.desc}</div>
      </div>
      <span class="slot-badge ${slot.required ? "req" : "opt"}">${slot.required ? "Required" : "Optional"}</span>
      <div class="file-input-wrap">
        <label class="file-btn" id="btn_${slot.key}">
          Choose
          <input type="file" accept=".pdf" data-key="${slot.key}" onchange="onFileChosen(this)">
        </label>
      </div>`;
    grid.appendChild(div);
  });
}

function onFileChosen(input) {
  const key = input.dataset.key;
  const file = input.files[0];
  if (!file) return;
  uploadedFiles[key] = file;

  const slot = document.getElementById(`slot_${key}`);
  slot.classList.add("filled");
  const btn = document.getElementById(`btn_${key}`);
  btn.classList.add("chosen");
  btn.childNodes[0].textContent = file.name.length > 16 ? file.name.slice(0, 14) + "…" : file.name;

  checkStep2();
}

function checkStep2() {
  const slots = FILE_SLOTS[state.location] || [];
  const required = slots.filter(s => s.required).map(s => s.key);
  const allFilled = required.every(k => uploadedFiles[k]);
  document.getElementById("step2Next").disabled = !allFilled;
}

document.getElementById("step2Next").addEventListener("click", () => goToStep(3));

// ── STEP 3: Parse + Review ─────────────────────────────────────
async function startParsing() {
  document.getElementById("parsingStatus").style.display = "flex";
  document.getElementById("reviewWrap").style.display = "none";
  document.getElementById("step3Next").style.display = "none";

  // Step 1: Wake up the server first
  document.querySelector("#parsingStatus span").textContent = "Waking up server (may take ~60 seconds on first use)…";
  try { await fetch(`${API_URL}/`, { signal: AbortSignal.timeout(90000) }); } catch(e) {}

  // Step 2: Send the files for parsing
  document.querySelector("#parsingStatus span").textContent = "Parsing PDFs…";

  try {
    const form = new FormData();
    form.append("location", state.location);
    form.append("report_date", state.date);

    const slots = FILE_SLOTS[state.location] || [];
    for (const slot of slots) {
      if (uploadedFiles[slot.key]) {
        form.append(slot.key, uploadedFiles[slot.key]);
      }
    }

    const res = await fetch(`${API_URL}/parse`, {
      method: "POST",
      body: form,
      signal: AbortSignal.timeout(120000)  // 2 minute timeout
    });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    state.figures = data.figures || {};

  } catch (err) {
    // If backend unreachable, use empty figures so user can still enter manually
    console.warn("Parse failed, using empty figures:", err.message);
    state.figures = {};
  }

  renderReviewTable();
  renderSnapshot();
  document.getElementById("parsingStatus").style.display = "none";
  document.getElementById("reviewWrap").style.display = "block";
  document.getElementById("step3Next").style.display = "inline-block";
}

function renderReviewTable() {
  const tbody = document.getElementById("reviewBody");
  tbody.innerHTML = "";

  let fields = [...REVIEW_FIELDS];
  if (state.location === "hulhumale") fields = [...HULHUMALE_EXTRA, ...fields];

  fields.forEach(field => {
    const elecVal = state.figures[field.key] ?? null;
    const miscVal = field.misc_key ? (state.figures[field.misc_key] ?? null) : null;
    const elecMissing = elecVal === null || elecVal === 0;

    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><strong>${field.label}</strong></td>
      <td>
        <input class="editable-field ${elecMissing ? "needs-input" : ""}"
               data-key="${field.key}"
               value="${elecVal !== null && elecVal !== 0 ? elecVal : ""}"
               placeholder="${elecMissing ? "Enter value" : ""}">
      </td>
      <td>
        ${field.misc_key
          ? `<input class="editable-field" data-key="${field.misc_key}" value="${miscVal !== null ? miscVal : 0}">`
          : `<span style="color:var(--muted)">—</span>`
        }
      </td>`;
    tbody.appendChild(tr);
  });

  // Live-update state on edit
  tbody.querySelectorAll(".editable-field").forEach(input => {
    input.addEventListener("change", () => {
      state.figures[input.dataset.key] = parseNum(input.value);
      input.classList.remove("needs-input");
      renderSnapshot();
    });
  });
}

// ── STEP 4: Summary + Generate ─────────────────────────────────
function renderSummary() {
  const monthStr = state.month
    ? new Date(state.month + "-01").toLocaleString("en-US", { month: "long", year: "numeric" })
    : "—";

  document.getElementById("summaryLocation").textContent = LOCATION_NAMES[state.location] || "—";
  document.getElementById("summaryMonth").textContent = monthStr;

  const grid = document.getElementById("summaryGrid");
  grid.innerHTML = "";

  const highlights = [
    { label: "ELECTRICITY Balance b/f",  val: state.figures["elec_bf"] },
    { label: "MISC Balance b/f",         val: state.figures["misc_bf"] },
    { label: "Electricity Sales",        val: state.figures["elec_sales"] },
    { label: "MISC Sales",               val: state.figures["misc_sales"] },
    { label: "Electricity Collection",   val: state.figures["elec_collection"] },
    { label: "System Closing (Elec)",    val: state.figures["elec_close_system"], highlight: true },
    { label: "System Closing (MISC)",    val: state.figures["misc_close_system"], highlight: true },
  ];

  highlights.forEach(item => {
    if (item.val === undefined || item.val === null) return;
    const div = document.createElement("div");
    div.className = "summary-item";
    div.innerHTML = `
      <div class="summary-item-label">${item.label}</div>
      <div class="summary-item-val ${item.highlight ? "highlight" : ""}">MRF ${fmt(item.val)}</div>`;
    grid.appendChild(div);
  });
}

async function generateReport() {
  const btn  = document.getElementById("generateBtn");
  const text = document.getElementById("generateBtnText");
  const successMsg = document.getElementById("successMsg");
  const errorMsg   = document.getElementById("errorMsg");

  btn.disabled = true;
  text.textContent = "Generating…";
  successMsg.style.display = "none";
  errorMsg.style.display   = "none";

  // Read latest values from review table inputs
  document.querySelectorAll("#reviewBody .editable-field").forEach(input => {
    state.figures[input.dataset.key] = parseNum(input.value);
  });

  const form = new FormData();
  form.append("location",    state.location);
  form.append("figures",     JSON.stringify(state.figures));
  form.append("report_date", state.date);

  try {
    const res = await fetch(`${API_URL}/generate`, {
      method: "POST",
      body: form,
      signal: AbortSignal.timeout(120000)
    });
    if (!res.ok) throw new Error(await res.text());

    const blob = await res.blob();
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement("a");
    const monthStr = state.month ? state.month.replace("-", "_") : "report";
    a.href     = url;
    a.download = `${state.location.toUpperCase()}_${monthStr}_Debtors_Reconciliation.docx`;
    a.click();
    URL.revokeObjectURL(url);

    successMsg.style.display = "block";
  } catch (err) {
    errorMsg.textContent = `Error: ${err.message}`;
    errorMsg.style.display = "block";
  } finally {
    btn.disabled = false;
    text.textContent = "⬇ Download .docx Report";
  }
}
