// js/adjustment2.js
// Self-contained Adjustment (2) tab. Depends on nothing in adjustment.js.
// Reuses the .adj-layout / .adj-right / .work-* CSS already in index.html.
(function () {
  "use strict";

  var API = (typeof API_URL !== "undefined")
    ? API_URL
    : "https://stelco-recon-api.onrender.com";

  var SLOTS = [
    { key: "collection_csv",   label: "Collection Report (CSV)", icon: "🧾",
      desc: "CollectionReport_inter — transaction-level payments" },
    { key: "open_debtors_csv", label: "Opening Debtors (CSV)",   icon: "📂",
      desc: "Prior-month closing debtor detail (invoice-level)" },
    { key: "close_debtors_csv",label: "Closing Debtors (CSV)",   icon: "📁",
      desc: "Current-month closing debtor detail (invoice-level)" },
  ];

  var files = {};
  var matrixTimer = null;

  // --- render upload slots -------------------------------------------------
  function renderSlots() {
    var grid = document.getElementById("adjustment2UploadGrid");
    if (!grid) return;
    grid.innerHTML = "";
    SLOTS.forEach(function (slot) {
      var div = document.createElement("div");
      div.className = "upload-slot";
      div.id = "a2slot_" + slot.key;
      div.innerHTML =
        '<div class="slot-icon">' + slot.icon + "</div>" +
        '<div class="slot-info">' +
          '<div class="slot-name">' + slot.label + "</div>" +
          '<div class="slot-desc">' + slot.desc + "</div>" +
        "</div>" +
        '<span class="slot-badge req">Required</span>' +
        '<div class="file-input-wrap">' +
          '<label class="file-btn" id="a2btn_' + slot.key + '">Choose' +
            '<input type="file" accept=".csv" data-key="' + slot.key +
            '" onchange="onAdj2FileChosen(this)"></label>' +
        "</div>";
      grid.appendChild(div);
    });
  }

  window.onAdj2FileChosen = function (input) {
    var key = input.dataset.key;
    var file = input.files[0];
    if (!file) return;
    files[key] = file;
    document.getElementById("a2slot_" + key).classList.add("filled");
    var btn = document.getElementById("a2btn_" + key);
    btn.classList.add("chosen");
    btn.childNodes[0].textContent =
      file.name.length > 16 ? file.name.slice(0, 14) + "…" : file.name;
    checkReady();
  };

  function checkReady() {
    var ready = SLOTS.every(function (s) { return files[s.key]; })
      && !!document.getElementById("adj2Month").value;
    document.getElementById("adj2GenerateBtn").disabled = !ready;
  }

  // --- working-steps visualizer (mirrors the Adjustment tab pattern) -------
  function renderSteps(steps, activeIndex, done) {
    var wrap = document.getElementById("adj2Working");
    if (!wrap) return;
    wrap.innerHTML = "";
    steps.forEach(function (s, i) {
      var st = "pending";
      if (done) st = "done";
      else if (i < activeIndex) st = "done";
      else if (i === activeIndex) st = "active";
      var div = document.createElement("div");
      div.className = "work-step " + st;
      div.innerHTML =
        '<div class="work-dot">' + (st === "done" ? "✓" : (i + 1)) + "</div>" +
        '<div class="work-body">' +
          '<div class="work-step-title">' + s.title + "</div>" +
          '<div class="work-step-desc">' + s.desc + "</div>" +
          '<div class="work-step-val">' + ((st !== "pending") ? (s.val || "") : "") + "</div>" +
        "</div>";
      wrap.appendChild(div);
    });
  }

  function animateSteps(steps) {
    var i = 0;
    renderSteps(steps, 0, false);
    if (matrixTimer) clearInterval(matrixTimer);
    matrixTimer = setInterval(function () {
      i++;
      if (i >= steps.length) { clearInterval(matrixTimer); renderSteps(steps, steps.length, true); }
      else renderSteps(steps, i, false);
    }, 450);
  }

  // --- matrix rain (own canvas id, inline-styled in the HTML block) --------
  function startMatrix() {
    var c = document.getElementById("matrix2Canvas");
    if (!c) return;
    var ctx = c.getContext("2d");
    function size() { c.width = c.offsetWidth; c.height = c.offsetHeight; }
    size();
    var glyphs = "01STELCO$0123456789".split("");
    var cols = Math.floor(c.width / 12);
    var drops = Array(cols).fill(1);
    function draw() {
      ctx.fillStyle = "rgba(6,12,8,0.10)";
      ctx.fillRect(0, 0, c.width, c.height);
      ctx.fillStyle = "#00ff41";
      ctx.font = "12px 'Courier New', monospace";
      for (var i = 0; i < drops.length; i++) {
        var t = glyphs[Math.floor(Math.random() * glyphs.length)];
        ctx.fillText(t, i * 12, drops[i] * 12);
        if (drops[i] * 12 > c.height && Math.random() > 0.975) drops[i] = 0;
        drops[i]++;
      }
    }
    if (c._raf) clearInterval(c._raf);
    c._raf = setInterval(draw, 55);
  }

  // --- generate ------------------------------------------------------------
  async function generate() {
    var btn = document.getElementById("adj2GenerateBtn");
    var status = document.getElementById("adj2Status");
    btn.disabled = true;
    status.className = "review-note";
    status.textContent = "Waking up server (may take ~60s on first use)…";

    try { await fetch(API + "/", { signal: AbortSignal.timeout(90000) }); } catch (e) {}

    status.textContent = "Reconciling collection against debtor ledgers…";
    var form = new FormData();
    form.append("collection_csv", files.collection_csv);
    form.append("open_debtors_csv", files.open_debtors_csv);
    form.append("close_debtors_csv", files.close_debtors_csv);
    form.append("recon_month", document.getElementById("adj2Month").value);
    ["opening_after_adj", "closing", "sales", "credits"].forEach(function (id) {
      var v = document.getElementById("a2_" + id).value.replace(/[^0-9.\-]/g, "");
      if (v !== "") form.append(id, v);
    });

    try {
      var res = await fetch(API + "/adjustments2", {
        method: "POST", body: form, signal: AbortSignal.timeout(120000),
      });
      if (!res.ok) throw new Error(await res.text());

      var hdr = res.headers.get("X-Adjustment2-Summary");
      if (hdr) {
        var summary = JSON.parse(decodeURIComponent(escape(atob(hdr))));
        animateSteps(summary.steps || []);
        var idv = summary.value_from_identity, resid = summary.residual_manual;
        var msg = summary.row_count + " unabsorbed row(s), MRF " +
          Number(summary.unabsorbed_total).toLocaleString("en-US", { minimumFractionDigits: 2 });
        if (idv != null) {
          msg += " · identity " + Number(idv).toLocaleString("en-US", { minimumFractionDigits: 2 }) +
                 " · residual " + Number(resid).toLocaleString("en-US", { minimumFractionDigits: 2 });
        }
        status.className = "review-note " + ((idv == null || Math.abs(resid) < 0.005) ? "adj-status-ok" : "adj-status-err");
        status.textContent = (idv == null || Math.abs(resid) < 0.005 ? "✅ " : "⚠ ") + msg;
      }

      var blob = await res.blob();
      var url = URL.createObjectURL(blob);
      var a = document.createElement("a");
      a.href = url;
      a.download = "Adjustment2_" + document.getElementById("adj2Month").value + ".xlsx";
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      status.className = "review-note adj-status-err";
      status.textContent = "Error: " + err.message;
    } finally {
      btn.disabled = false;
    }
  }

  // --- init on first show --------------------------------------------------
  function init() {
    renderSlots();
    startMatrix();
    var m = document.getElementById("adj2Month");
    if (m) m.addEventListener("change", checkReady);
    var b = document.getElementById("adj2GenerateBtn");
    if (b) b.addEventListener("click", generate);
  }

  // expose an initializer the tab-switcher can call the first time this tab opens
  window.initAdjustment2Tab = (function () {
    var once = false;
    return function () { if (!once) { once = true; init(); } startMatrix(); };
  })();

  document.addEventListener("DOMContentLoaded", function () {
    // if the tab is already visible on load, initialize immediately
    var tab = document.getElementById("adjustment2Tab");
    if (tab && tab.style.display !== "none") window.initAdjustment2Tab();
  });
})();
