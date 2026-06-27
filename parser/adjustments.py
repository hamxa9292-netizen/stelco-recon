"""
parser/adjustments.py
---------------------
"Adjustment Detail" feature for the STELCO debtors reconciliation.

Identifies Adjustment (1) and its line-item detail by diffing a prior-month
CLOSING debtors CSV against the current-month OPENING debtors CSV (invoice-level
exports, keyed by INVOICE_NO).

Verified against the signed Mar-2026 Hulhumale' report: 224 line items,
total -549,252.56, zero invoice/amount mismatches.

Rule per invoice (summing BALANCE_AMT):
  * in OPEN only            -> +balance   "created after the report was taken"
  * in CLOSE only           -> -balance   "invoice cancelled"
  * in BOTH, balance moved   -> open-close  "amended after the report was taken"
  * cancel-and-replace (same account has one new + one cancelled invoice)
                            -> merged into one netted row.

Line items always sum to  Σ(open) - Σ(close)  =  Adjustment (1).
Positive raises opening debtors, negative lowers it.
"""

import csv
import io

ISLAND_BY_LOCATION = {
    "male":        "MALE'",
    "hulhumale":   "HULHUMALE'",
    "thilafushi":  "THILAFUSHI",
    "gulhi_falhu": "GULHI FALHU",
}


def _open_text(src):
    """Accept a filesystem path OR a file-like / Werkzeug FileStorage."""
    if hasattr(src, "read"):
        data = src.read()
        if isinstance(data, bytes):
            data = data.decode("latin-1")
        return io.StringIO(data)
    return open(src, newline="", encoding="latin-1")


def _load(src, island=None):
    """INVOICE_NO -> summed BALANCE_AMT, plus a representative source row."""
    bal, rows = {}, {}
    f = _open_text(src)
    try:
        for row in csv.DictReader(f):
            if island and (row.get("ISLAND_SNAME") or "").strip().upper() != island.upper():
                continue
            ino = (row.get("INVOICE_NO") or "").strip()
            if not ino:
                continue
            try:
                amt = float(row.get("BALANCE_AMT") or 0)
            except ValueError:
                amt = 0.0
            bal[ino] = bal.get(ino, 0.0) + amt
            rows[ino] = row
    finally:
        f.close()
    return bal, rows


def find_adjustments(close_src, open_src, island=None, merge_replacements=True):
    """Returns (line_items, summary)."""
    close, crows = _load(close_src, island)
    openf, orows = _load(open_src, island)

    added   = {i: openf[i] for i in openf if i not in close}
    removed = {i: close[i] for i in close if i not in openf}
    changed = {i: round(openf[i] - close[i], 2)
               for i in (openf.keys() & close.keys())
               if abs(openf[i] - close[i]) > 0.005}

    def meta(ino):
        r = orows.get(ino) or crows.get(ino) or {}
        return (
            (r.get("ACCOUNT_NO") or "").strip(),
            (r.get("ISLAND_SNAME") or "").strip(),
            (r.get("CAT_NAME") or "").strip(),
            (r.get("BILL_REF") or "").strip(),
        )

    by_acct_added, by_acct_removed = {}, {}
    for i in added:
        by_acct_added.setdefault(meta(i)[0], []).append(i)
    for i in removed:
        by_acct_removed.setdefault(meta(i)[0], []).append(i)

    items, paired_added, paired_removed = [], set(), set()

    if merge_replacements:
        for acct, add_list in by_acct_added.items():
            for new_i, old_i in zip(add_list, by_acct_removed.get(acct, [])):
                acc, isl, cat, ref = meta(new_i)
                items.append(dict(account=acc, island=isl, category=cat, bill_ref=ref,
                                  invoice_no=new_i, cancelled_invoice_no=old_i,
                                  amount=round(added[new_i] - removed[old_i], 2),
                                  reason="The invoice was cancelled and created after the report was taken"))
                paired_added.add(new_i)
                paired_removed.add(old_i)

    for i, v in added.items():
        if i in paired_added:
            continue
        acc, isl, cat, ref = meta(i)
        items.append(dict(account=acc, island=isl, category=cat, bill_ref=ref,
                          invoice_no=i, cancelled_invoice_no=None, amount=round(v, 2),
                          reason="The invoice was created after the report was taken"))

    for i, v in removed.items():
        if i in paired_removed:
            continue
        acc, isl, cat, ref = meta(i)
        items.append(dict(account=acc, island=isl, category=cat, bill_ref=ref,
                          invoice_no=i, cancelled_invoice_no=None, amount=round(-v, 2),
                          reason="Invoice cancelled"))

    for i, v in changed.items():
        acc, isl, cat, ref = meta(i)
        items.append(dict(account=acc, island=isl, category=cat, bill_ref=ref,
                          invoice_no=i, cancelled_invoice_no=None, amount=v,
                          reason="The invoice was amended after the report was taken"))

    items.sort(key=lambda x: (x["account"], x["invoice_no"]))
    summary = dict(
        close_total=round(sum(close.values()), 2),
        open_total=round(sum(openf.values()), 2),
        adjustment=round(sum(openf.values()) - sum(close.values()), 2),
        line_total=round(sum(it["amount"] for it in items), 2),
        n_created=len(added) - len(paired_added),
        n_cancelled=len(removed) - len(paired_removed),
        n_amended=len(changed),
        n_replacements=len(paired_added),
        n_rows=len(items),
    )
    return items, summary


def apply_to_figures(close_src, open_src, figures, location=None):
    """
    Run the diff and feed Adjustment (1) into the reconciliation figures dict.

    Sets:
        elec_bf     = prior-month closing total   (Balance b/f)
        elec_bfadj  = current-month opening total (Balance b/f after adjustment)
        elec_adj1   = elec_bfadj - elec_bf        (Adjustment (1))

    The calculator derives Adjustment (1) as (elec_bfadj - elec_bf), so setting
    the two balances makes the line tie automatically. Returns the detail items
    so the caller can build a downloadable annexure.
    """
    island = ISLAND_BY_LOCATION.get(location)
    items, summary = find_adjustments(close_src, open_src, island=island)
    figures["elec_bf"]    = summary["close_total"]
    figures["elec_bfadj"] = summary["open_total"]
    figures["elec_adj1"]  = summary["adjustment"]
    return items, summary
