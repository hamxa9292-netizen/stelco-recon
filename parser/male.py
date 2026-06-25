"""
Male' PDF Parser — verified against real PDFs.

Logic:
  - elec_bfadj        = open.pdf Total  (Balance b/f after adjustment)
  - elec_bf           = prior month c/f (user confirms in review step)
  - elec_close_system = close.pdf Total (Debtors Balance c/f)
  - Adjustments (2)   = close.pdf - calculated c/f (auto-computed by calculator)

NOTE: close.pdf MUST be printed at month-end, not re-printed later.
Re-printed close.pdf may differ due to backdated postings.

Collection formula (Male'):
  Electricity = Total Realised - ALL "Collection Realised - MISC BILL" lines
  MISC        = Sum of ALL "Collection Realised - MISC BILL" lines
"""
import pdfplumber
import re


def _total(path):
    with pdfplumber.open(path) as pdf:
        text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    m = re.search(r'Total\s+([\d,]+\.\d{2})\s*\n', text)
    return float(m.group(1).replace(",", "")) if m else 0.0


def _grand_total(path):
    with pdfplumber.open(path) as pdf:
        text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    m = re.search(r'Grand [Tt]otal\s+([\d,]+\.\d{2})', text)
    return float(m.group(1).replace(",", "")) if m else 0.0


def _credits_grand_total(path):
    with pdfplumber.open(path) as pdf:
        text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    m = re.search(r'GRAND TOTAL\s+([\d,]+\.\d{2})', text)
    return float(m.group(1).replace(",", "")) if m else 0.0


def _recon_totals(path):
    """Process each page separately to avoid page-break line merge issues."""
    with pdfplumber.open(path) as pdf:
        pages = [p.extract_text() or "" for p in pdf.pages]

    all_totals = []
    for page in pages:
        all_totals += re.findall(r'TOTAL COLLECTION\s+([\d,]+\.\d{2})', page)
    total_realised = float(all_totals[-1].replace(",", "")) if all_totals else 0.0

    seen = {}
    for page in pages:
        matches = re.findall(
            r'Collection Realised - MISC BILL\s+([\w\s-]+?)\s+([\d]{1,3}(?:,\d{3})*\.\d{2})\s*\n',
            page
        )
        for mode, amount in matches:
            seen[mode.strip()] = float(amount.replace(",", ""))
    misc_total = sum(seen.values())

    return total_realised, misc_total


def parse_male(files: dict) -> dict:
    elec_bfadj        = _total(files["open"])          if files.get("open")         else 0.0
    misc_bfadj        = _total(files["misc_open"])     if files.get("misc_open")    else 0.0
    elec_close_system = _total(files["close"])         if files.get("close")        else 0.0
    misc_close_system = _total(files["misc_close"])    if files.get("misc_close")   else 0.0
    elec_sales        = _grand_total(files["sales"])   if files.get("sales")        else 0.0
    misc_sales        = _grand_total(files["misc_sales"]) if files.get("misc_sales") else 0.0
    elec_credits      = _credits_grand_total(files["collection"]) if files.get("collection") else 0.0

    total_realised, misc_coll = (
        _recon_totals(files["recon"]) if files.get("recon") else (0.0, 0.0)
    )

    return {
        "elec_bfadj":        elec_bfadj,
        "misc_bfadj":        misc_bfadj,
        "elec_bf":           elec_bfadj,   # default; override with prior c/f in review
        "misc_bf":           misc_bfadj,
        "elec_close_system": elec_close_system,  # from close.pdf
        "misc_close_system": misc_close_system,
        "elec_sales":        elec_sales,
        "misc_sales":        misc_sales,
        "elec_credits":      elec_credits,
        "misc_credits":      0.0,
        "total_realised":    total_realised,
        "misc_collections":  misc_coll,
        "elec_collection":   total_realised - misc_coll,
        "misc_collection":   misc_coll,
    }
