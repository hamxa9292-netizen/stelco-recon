"""
Thilafushi PDF Parser - verified against the May 2026 reports.

Reconciliation (electricity only; Thilafushi has no MISC bills):
  Balance b/f   = Opening Debtors Summary Total        (open.pdf)
  Total Sales   = Sales Report Grand Total             (sales.pdf)
  Credits/Fine  = Cash Collection Credits GRAND TOTAL  (collection.pdf)
  Collection    = final TOTAL COLLECTION (Realised)    (recon.pdf)
  Debtors c/f   = Closing Debtors Summary Total        (close.pdf)

Verified May 2026:
  32,951,105.31 + 3,324,380.60 + 1.12 - 3,334,736.24 = 32,940,750.79
  -> Adjustments(2) = 0.00

MISC slots are optional and parsed only if uploaded, so the same screen can
handle a future month where Thilafushi does have MISC bills.
"""
import pdfplumber
import re


def _text(path):
    with pdfplumber.open(path) as pdf:
        return "\n".join(p.extract_text() or "" for p in pdf.pages)


def _total(path):
    """Grand 'Total <amount>' line of a Debtors Summary Report."""
    m = re.search(r'Total\s+([\d,]+\.\d{2})\s*\n', _text(path))
    return float(m.group(1).replace(",", "")) if m else 0.0


def _grand_total(path):
    """
    Sales Report 'Grand Total'. The value can sit on the same line OR be pushed
    below an 'Authorized By' block. Require thousands separators first so a stray
    date can't match; fall back to any decimal for small totals.
    """
    text = _text(path)
    m = re.search(r'Grand\s+Total[\s\S]*?(\d{1,3}(?:,\d{3})+\.\d{2})', text)
    if m:
        return float(m.group(1).replace(",", ""))
    m = re.search(r'Grand\s+Total[\s\S]*?([\d,]+\.\d{2})', text)
    return float(m.group(1).replace(",", "")) if m else 0.0


def _credits_total(path):
    """'GRAND TOTAL <amount>' from the Cash Collection Credits Summary."""
    m = re.search(r'GRAND TOTAL\s+([\d,]+\.\d{2})', _text(path))
    return float(m.group(1).replace(",", "")) if m else 0.0


def _collection_realised(path):
    """
    Payment Reconciliation Report has two 'TOTAL COLLECTION' lines: the first is
    gross, the second (after 'Effects not cleared') is the realised figure. Use
    the LAST occurrence = Collections Realised.
    """
    vals = re.findall(r'TOTAL COLLECTION\s+([\d,]+\.\d{2})', _text(path))
    return float(vals[-1].replace(",", "")) if vals else 0.0


def parse_thilafushi(files):
    elec_bf           = _total(files["open"])  if files.get("open")  else 0.0
    elec_close_system = _total(files["close"]) if files.get("close") else 0.0
    elec_sales        = _grand_total(files["sales"]) if files.get("sales") else 0.0
    elec_credits      = _credits_total(files["collection"]) if files.get("collection") else 0.0
    elec_collection   = _collection_realised(files["recon"]) if files.get("recon") else 0.0

    # MISC is optional at Thilafushi; parsed only if those files are uploaded.
    misc_bf           = _total(files["misc_open"])  if files.get("misc_open")  else 0.0
    misc_close_system = _total(files["misc_close"]) if files.get("misc_close") else 0.0
    misc_sales        = _grand_total(files["misc_sales"]) if files.get("misc_sales") else 0.0

    return {
        "elec_bf":           elec_bf,
        "misc_bf":           misc_bf,
        "elec_close_system": elec_close_system,
        "misc_close_system": misc_close_system,
        "elec_sales":        elec_sales,
        "misc_sales":        misc_sales,
        "elec_credits":      elec_credits,
        "misc_credits":      0.0,
        "elec_collection":   elec_collection,
        "misc_collection":   0.0,
    }
