"""
reconciliation/adjustment2_generator.py

Adjustment (2) — the CLOSING-side plug on the Debtors Reconciliation Statement.

    Adj(2) = Closing - Opening_after_adj - Sales - Credits + Collection

Economic meaning: collection recorded that reduced NO open debtor balance
(payments landing on invoices already settled / off-ledger).

Two layers:
  1. VALUE       -> the identity above (exact; uses the 5 control totals the
                    recon statement already produces).
  2. ATTRIBUTION -> which realised bill payments reduced nothing: invoice
                    absent from BOTH the opening and closing debtor ledgers,
                    on a bill from before the recon month. Their sum should
                    equal the VALUE; any residual stays manual.

Inputs (path, text stream, or raw bytes all accepted):
  - Collection transaction CSV -> Collection total + candidate rows
  - Opening debtor detail CSV (invoice-level) -> membership test
  - Closing debtor detail CSV (invoice-level) -> membership test
  - Sales total, Credits total, Opening_after_adj, Closing -> control check (optional)

Collection CSV columns (observed):
  PAYMENT_NOX, CHQINF, ACCOUNT_NO, OLD_ACC_NO, AMT, COLLECT_AMOUNT, INVOICE_NO,
  PAYMENT_MODE, PAID_DATE, BILL_REF, ISLAND_SNAME, PAYLOC, TRANS_ISLAND,
  CAT_SNAME, USER_NAME, ACDES, CANCEL_DATE, ORD
    ORD=1 bill payments, ORD=2 credit payments, ORD>=3 deposits/settlements.
    CANCEL_DATE non-empty -> cancelled (excluded from realised).

Requires: openpyxl==3.1.5
"""

import csv
import io
import json
import base64
from dataclasses import dataclass, field
from typing import Optional, List, Tuple

# --- CONFIG: confirm against your debtor detail CSVs ------------------------
DEBTOR_INVOICE_COL = "INVOICE_NO"
DEBTOR_BALANCE_COL = "BALANCE_AMT"
ABSORB_EPSILON = 0.005


def _num(x):
    x = (x or "").strip().replace(",", "")
    if not x:
        return 0.0
    try:
        return float(x)
    except ValueError:
        return 0.0


def _period(bill_ref):
    """'2026/5-1' -> (2026, 5). None if unparseable."""
    br = (bill_ref or "").strip()
    if not br or "/" not in br:
        return None
    try:
        year, rest = br.split("/", 1)
        month = rest.split("-", 1)[0]
        return (int(year), int(month))
    except (ValueError, IndexError):
        return None


def _text(source):
    if hasattr(source, "read"):
        data = source.read()
        return data.decode("utf-8", "replace") if isinstance(data, (bytes, bytearray)) else data
    if isinstance(source, (bytes, bytearray)):
        return bytes(source).decode("utf-8", "replace")
    with open(source, encoding="utf-8", errors="replace", newline="") as f:
        return f.read()


def _reader(source):
    return csv.DictReader(io.StringIO(_text(source)))


# --- loaders ---------------------------------------------------------------
def load_collection_rows(source):
    return list(_reader(source))


def load_debtor_invoices(source, invoice_col=DEBTOR_INVOICE_COL,
                         balance_col=DEBTOR_BALANCE_COL):
    """{invoice_no: outstanding_balance} for rows carrying a non-zero balance."""
    out = {}
    for row in _reader(source):
        inv = (row.get(invoice_col) or "").strip()
        bal = _num(row.get(balance_col))
        if inv and abs(bal) > ABSORB_EPSILON:
            out[inv] = out.get(inv, 0.0) + bal
    return out


# --- core ------------------------------------------------------------------
@dataclass
class Adjustment2Result:
    recon_month: Tuple[int, int]
    value_from_identity: Optional[float]
    collection_realised: float
    unabsorbed_total: float
    residual_manual: Optional[float]
    unabsorbed_rows: List[dict] = field(default_factory=list)


def compute_realised_collection(coll_rows):
    total = 0.0
    for r in coll_rows:
        if (r.get("ORD") or "").strip() in ("1", "2") \
                and not (r.get("CANCEL_DATE") or "").strip():
            total += _num(r.get("COLLECT_AMOUNT"))
    return round(total, 2)


def identity_value(opening_after_adj, closing, sales, credits, collection):
    return round(closing - opening_after_adj - sales - credits + collection, 2)


def attribute(coll_rows, debt_open, debt_close, recon_month):
    """Realised ORD=1 payments on prior-period bills absent from both ledgers."""
    rows = []
    for r in coll_rows:
        if (r.get("ORD") or "").strip() != "1":
            continue
        if (r.get("CANCEL_DATE") or "").strip():
            continue
        inv = (r.get("INVOICE_NO") or "").strip()
        if not inv:
            continue
        per = _period(r.get("BILL_REF"))
        if per is None or per >= recon_month:
            continue
        if inv in debt_open or inv in debt_close:
            continue
        rows.append({
            "invoice_no": inv,
            "account_no": (r.get("ACCOUNT_NO") or "").strip(),
            "bill_ref": (r.get("BILL_REF") or "").strip(),
            "amount": round(_num(r.get("COLLECT_AMOUNT")), 2),
            "paid_date": (r.get("PAID_DATE") or "").strip(),
            "payment_mode": (r.get("PAYMENT_MODE") or "").strip(),
            "category": (r.get("CAT_SNAME") or "").strip(),
        })
    return rows


def reconcile(coll_rows, debt_open, debt_close, recon_month,
              opening_after_adj=None, closing=None, sales=None, credits=None):
    collection = compute_realised_collection(coll_rows)
    rows = attribute(coll_rows, debt_open, debt_close, recon_month)
    attributed = round(sum(r["amount"] for r in rows), 2)
    if None in (opening_after_adj, closing, sales, credits):
        value = residual = None
    else:
        value = identity_value(opening_after_adj, closing, sales, credits, collection)
        residual = round(value - attributed, 2)
    return Adjustment2Result(
        recon_month=recon_month,
        value_from_identity=value,
        collection_realised=collection,
        unabsorbed_total=attributed,
        residual_manual=residual,
        unabsorbed_rows=sorted(rows, key=lambda r: -abs(r["amount"])),
    )


# --- visualizer summary (base64 JSON header, like X-Adjustment-Summary) -----
def summary_steps(result: Adjustment2Result):
    fmt = lambda v: ("—" if v is None else f"{v:,.2f}")
    return [
        {"title": "Load collection ledger",
         "desc": "ORD 1+2, cancelled dropped",
         "val": f"MRF {result.collection_realised:,.2f}"},
        {"title": "Load opening debtors", "desc": "invoice-level balances",
         "val": "loaded"},
        {"title": "Load closing debtors", "desc": "invoice-level balances",
         "val": "loaded"},
        {"title": "Scan unabsorbed payments",
         "desc": "prior-period bill, off both ledgers",
         "val": f"{len(result.unabsorbed_rows)} row(s)"},
        {"title": "Sum -> Adjustment (2)", "desc": "attributed total",
         "val": f"MRF {result.unabsorbed_total:,.2f}"},
        {"title": "Check vs identity", "desc": "residual stays manual",
         "val": f"id {fmt(result.value_from_identity)} / res {fmt(result.residual_manual)}"},
    ]


def summary_b64(result: Adjustment2Result):
    payload = {
        "recon_month": f"{result.recon_month[0]}-{result.recon_month[1]:02d}",
        "value_from_identity": result.value_from_identity,
        "collection_realised": result.collection_realised,
        "unabsorbed_total": result.unabsorbed_total,
        "residual_manual": result.residual_manual,
        "row_count": len(result.unabsorbed_rows),
        "steps": summary_steps(result),
    }
    return base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")


# --- xlsx ------------------------------------------------------------------
def _fill_workbook(result: Adjustment2Result):
    from openpyxl import Workbook
    from openpyxl.styles import Font
    wb = Workbook()
    ws = wb.active
    ws.title = "Summary"
    bold = Font(bold=True)
    ws["A1"] = "Adjustment (2) - Reconciliation"; ws["A1"].font = bold
    ws["A3"] = "Recon month";           ws["B3"] = f"{result.recon_month[0]}-{result.recon_month[1]:02d}"
    ws["A4"] = "Adj(2) (identity)";     ws["B4"] = result.value_from_identity
    ws["A5"] = "Realised collection";   ws["B5"] = result.collection_realised
    ws["A6"] = "Attributed (itemised)"; ws["B6"] = result.unabsorbed_total
    ws["A7"] = "Residual (manual)";     ws["B7"] = result.residual_manual
    for c in ("A3", "A4", "A5", "A6", "A7"):
        ws[c].font = bold
    d = wb.create_sheet("Unabsorbed")
    d.append(["Invoice No", "Account No", "Bill Ref", "Amount",
              "Paid Date", "Payment Mode", "Category"])
    for c in d[1]:
        c.font = bold
    for row in result.unabsorbed_rows:
        d.append([row["invoice_no"], row["account_no"], row["bill_ref"],
                  row["amount"], row["paid_date"], row["payment_mode"], row["category"]])
    return wb


def generate_xlsx_bytes(result: Adjustment2Result):
    buf = io.BytesIO()
    _fill_workbook(result).save(buf)
    buf.seek(0)
    return buf


def generate_xlsx(result: Adjustment2Result, out_path):
    _fill_workbook(result).save(out_path)
    return out_path
