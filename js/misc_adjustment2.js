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

  async function generate() {
    var btn = document.getElementById("miscA2GenerateBtn");
    var status = document.getElementById("miscA2Status");
    btn.disabled = true;
    if (status) { status.className = "review-note"; status.textContent = "Working... (first call may wake the server, up to a minute)"; }

    // wake the server (free tier cold start)
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
      var summ = res.headers.get("X-MiscAdj2-Summary");
      var blob = await res.blob();
      var url = URL.createObjectURL(blob);
      var a = document.createElement("a");
      a.href = url;
      a.download = "MISC_Adjustment2.xlsx";
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
      if (status) {
        status.className = "review-note adj-status-ok";
        var extra = "";
        if (summ) { try { var s = JSON.parse(atob(summ)); extra = " " + s.n_rows + " bill(s), total " + Number(s.total).toLocaleString(undefined, {minimumFractionDigits:2, maximumFractionDigits:2}) + "."; } catch (e) {} }
        status.textContent = "Downloaded MISC_Adjustment2.xlsx." + extra;
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
