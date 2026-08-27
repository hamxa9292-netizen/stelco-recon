/* MISC Adjustment (2) tab — itemises the MISC Adj(2) by bill reference.
   Mirrors adjustment2.js. Uploads the four MISC CSVs, calls /misc_adjustments2,
   downloads the returned .xlsx. Self-contained; no shared state needed. */
(function () {
  var API = (typeof API_URL !== "undefined") ? API_URL : "";

  var SLOTS = [
    { key: "misc_open_csv",  label: "MISC Opening (CSV)",   icon: "📂",
      desc: "Current-month MISC opening (= prior-month MISC closing)", required: true },
    { key: "misc_close_csv", label: "MISC Closing (CSV)",   icon: "📁",
      desc: "Current-month MISC closing debtors", required: true },
    { key: "misc_sales_csv", label: "MISC Sales (CSV)",     icon: "📊",
      desc: "Current-month MISC sales", required: false },
    { key: "misc_coll_csv",  label: "MISC Collection (CSV)", icon: "🧾",
      desc: "MISC reconciled collection (Misc_Bills)", required: false },
  ];

  var files = {};

  function renderSlots() {
    var grid = document.getElementById("miscA2UploadGrid");
    if (!grid) return;
    grid.innerHTML = "";
    SLOTS.forEach(function (slot) {
      var div = document.createElement("div");
      div.className = "upload-slot";
      div.id = "ma2slot_" + slot.key;
      div.innerHTML =
        '<div class="slot-icon">' + slot.icon + "</div>" +
        '<div class="slot-info">' +
          '<div class="slot-name">' + slot.label + "</div>" +
          '<div class="slot-desc">' + slot.desc + "</div>" +
        "</div>" +
        (slot.required
          ? '<span class="slot-badge req">Required</span>'
          : '<span class="slot-badge opt">Optional</span>') +
        '<label class="file-btn" id="ma2btn_' + slot.key + '">Choose' +
          '<input type="file" accept=".csv" data-key="' + slot.key +
          '" onchange="onMiscA2FileChosen(this)"></label>';
      grid.appendChild(div);
    });
  }

  window.onMiscA2FileChosen = function (input) {
    var key = input.dataset.key;
    if (!input.files || !input.files[0]) return;
    files[key] = input.files[0];
    document.getElementById("ma2slot_" + key).classList.add("filled");
    var btn = document.getElementById("ma2btn_" + key);
    if (btn) { btn.classList.add("chosen"); btn.childNodes[0].nodeValue = input.files[0].name; }
    checkReady();
  };

  function checkReady() {
    var ready = SLOTS.filter(function (s) { return s.required; })
                     .every(function (s) { return files[s.key]; });
    var b = document.getElementById("miscA2GenerateBtn");
    if (b) b.disabled = !ready;
  }

  function fmt(n) {
    return Number(n).toLocaleString(undefined, {minimumFractionDigits:2, maximumFractionDigits:2});
  }

  function renderResults(data) {
    var box = document.getElementById("miscA2Results");
    if (!box) return;
    if (!data.rows || !data.rows.length) {
      box.innerHTML = '<p class="review-note adj-status-ok">No MISC adjustments this month - the ledger ties out.</p>';
      return;
    }
    var html = '<div class="snap-title">MISC ADJUSTMENT (2)</div>';
    data.rows.forEach(function (r) {
      var amt = Number(r.adjustment);
      var cls = amt < 0 ? "" : "";
      html +=
        '<div style="padding:10px 0;border-bottom:1px solid var(--line-soft,#1E2745);">' +
          '<div style="display:flex;justify-content:space-between;gap:10px;">' +
            '<span style="font-weight:600;">' + r.bill_ref + '</span>' +
            '<span class="work-step-val" style="color:' + (amt<0?"var(--arc-amber,#FFB020)":"var(--arc-cyan,#2DE2E6)") + ';">' + fmt(amt) + '</span>' +
          '</div>' +
          '<div class="slot-desc">acct ' + (r.account_no||"-") + (r.category?(" &middot; "+r.category):"") + '</div>' +
          '<div class="slot-desc">' + r.reason + '</div>' +
        '</div>';
    });
    html += '<div style="display:flex;justify-content:space-between;padding-top:10px;font-weight:700;">' +
              '<span>TOTAL Adj(2)</span><span class="work-step-val">' + fmt(data.total) + '</span></div>';
    box.innerHTML = html;
  }

  function downloadXlsx(b64) {
    try {
      var bin = atob(b64), len = bin.length, bytes = new Uint8Array(len);
      for (var i = 0; i < len; i++) bytes[i] = bin.charCodeAt(i);
      var blob = new Blob([bytes], {type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"});
      var url = URL.createObjectURL(blob);
      var a = document.createElement("a");
      a.href = url; a.download = "MISC_Adjustment2.xlsx";
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {}
  }

  async function generate() {
    var btn = document.getElementById("miscA2GenerateBtn");
    var status = document.getElementById("miscA2Status");
    btn.disabled = true;
    if (status) { status.className = "review-note"; status.textContent = "Working... (first call may wake the server, up to a minute)"; }

    try { await fetch(API + "/", { signal: AbortSignal.timeout(90000) }); } catch (e) {}

    var form = new FormData();
    SLOTS.forEach(function (s) { if (files[s.key]) form.append(s.key, files[s.key]); });

    try {
      var res = await fetch(API + "/misc_adjustments2", {
        method: "POST", body: form, signal: AbortSignal.timeout(120000),
      });
      if (!res.ok) {
        var msg = "";
        try { msg = (await res.json()).detail; } catch (e) {}
        throw new Error(msg || ("Server returned " + res.status));
      }
      var data = await res.json();
      renderResults(data);
      if (data.xlsx_b64) window._miscA2Xlsx = data.xlsx_b64;
      if (status) {
        status.className = "review-note adj-status-ok";
        status.innerHTML = data.n_rows + ' bill(s), total ' + fmt(data.total) +
          '. <button type="button" class="btn-link" id="miscA2DownloadBtn">Download .xlsx</button>';
        var dl = document.getElementById("miscA2DownloadBtn");
        if (dl) dl.addEventListener("click", function () { downloadXlsx(window._miscA2Xlsx); });
      }
    } catch (err) {
      if (status) { status.className = "review-note adj-status-err"; status.textContent = "Failed: " + err.message; }
    } finally {
      btn.disabled = false;
    }
  }

  function init() {
    renderSlots();
    var b = document.getElementById("miscA2GenerateBtn");
    if (b) b.addEventListener("click", generate);
    checkReady();
  }

  window.initMiscAdj2Tab = (function () {
    var once = false;
    return function () { if (!once) { once = true; init(); } };
  })();

  document.addEventListener("DOMContentLoaded", function () {
    var tab = document.getElementById("miscAdj2Tab");
    if (tab && tab.style.display !== "none") window.initMiscAdj2Tab();
  });
})();
