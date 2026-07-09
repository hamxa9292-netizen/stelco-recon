"""
reconciliation/adjustment2_generator.py

Adjustment (2) — the CLOSING-side plug on the Debtors Reconciliation Statement.

    Adj(2) = Closing - Opening_after_adj - Sales - Credits + Collection

Economic meaning: collection recorded that reduced NO open debtor balance
(payments landing on invoices already settled / off-ledger).

Two layers:
  1. VALUE       -> the identity above (exact; uses the 5 control totals the
                    recon statement already produces). Opening MUST be the
                    Balance b/f AFTER adjustment, not before.
  2. ATTRIBUTION -> realised bill payments that reduced nothing: invoice
                    absent from BOTH the opening and closing debtor ledgers,
                    on a bill from before the recon month.

Robustness:
  - CSVs are read as utf-8-sig so a BOM on the header row can't hide the
    first column (a common cause of an empty ledger).
  - The invoice/balance columns are auto-detected if the configured names
    aren't present.
  - If no balance column is found, membership falls back to "invoice present
    in the debtor file" (a debtors report only lists accounts that owe).
  - Opening/closing invoice counts are reported so an empty load is visible.

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
    """Return CSV text with any BOM stripped (utf-8-sig)."""
    if hasattr(source, "read"):
        data = source.read()
        if isinstance(data, (bytes, bytearray)):
            return bytes(data).decode("utf-8-sig", "replace")
        return data.lstrip("\ufeff") if isinstance(data, str) else data
    if isinstance(source, (bytes, bytearray)):
        return bytes(source).decode("utf-8-sig", "replace")
    with open(source, encoding="utf-8-sig", errors="replace", newline="") as f:
        return f.read()


def _reader(source):
    return csv.DictReader(io.StringIO(_text(source)))


def _detect_col(fieldnames, preferred, keywords):
    fields = [f for f in (fieldnames or []) if f is not None]
    for f in fields:
        if f.strip() == preferred:
            return f
    low = {f.strip().lower(): f for f in fields}
    if preferred.strip().lower() in low:
        return low[preferred.strip().lower()]
    for f in fields:
        if any(k in f.strip().lower() for k in keywords):
            return f
    return None


# --- loaders ---------------------------------------------------------------
def load_collection_rows(source):
    return list(_reader(source))


def load_debtor_invoices(source, invoice_col=DEBTOR_INVOICE_COL,
                         balance_col=DEBTOR_BALANCE_COL):
    """{invoice_no: outstanding_balance} for invoices carrying an open balance.

    If no balance column can be found, every listed invoice is treated as
    on-ledger (a debtors report only lists accounts that owe)."""
    rows = list(_reader(source))
    if not rows:
        return {}
    fields = list(rows[0].keys())
    inv_col = _detect_col(fields, invoice_col, ["invoice"])
    bal_col = _detect_col(fields, balance_col, ["balance", "outstand", "o/s", "closing"])
    out = {}
    for r in rows:
        inv = (r.get(inv_col) or "").strip() if inv_col else ""
        if not inv:
            continue
        if bal_col is not None:
            b = _num(r.get(bal_col))
            if b <= ABSORB_EPSILON:      # only POSITIVE (owed) balances are open debtors;
                continue                 # a credit / zero balance is not something a payment reduced
            out[inv] = out.get(inv, 0.0) + b
        else:
            out.setdefault(inv, 0.0)
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
    open_count: int = 0
    close_count: int = 0


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
        open_count=len(debt_open),
        close_count=len(debt_close),
    )


# --- visualizer summary (base64 JSON header, like X-Adjustment-Summary) -----
def summary_steps(result: Adjustment2Result):
    fmt = lambda v: ("—" if v is None else f"{v:,.2f}")
    return [
        {"title": "Load collection ledger", "desc": "ORD 1+2, cancelled dropped",
         "val": f"MRF {result.collection_realised:,.2f}"},
        {"title": "Load opening debtors", "desc": "invoice-level balances",
         "val": f"{result.open_count:,} invoices"},
        {"title": "Load closing debtors", "desc": "invoice-level balances",
         "val": f"{result.close_count:,} invoices"},
        {"title": "Scan unabsorbed payments", "desc": "prior-period bill, off both ledgers",
         "val": f"{len(result.unabsorbed_rows):,} row(s)"},
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
        "open_count": result.open_count,
        "close_count": result.close_count,
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
    ws["A8"] = "Opening invoices";      ws["B8"] = result.open_count
    ws["A9"] = "Closing invoices";      ws["B9"] = result.close_count
    for c in ("A3", "A4", "A5", "A6", "A7", "A8", "A9"):
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
