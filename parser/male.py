"""
Male' PDF Parser — verified against May 2026 real PDFs.

Balance b/f logic:
  - Balance b/f             = prior month Debtors c/f (from open.pdf of PRIOR month)
  - Balance b/f after adj   = open.pdf Total (current month system opening snapshot)
  - Adjustments (1)         = Balance b/f (after adj) - Balance b/f

Collection formula:
  Electricity = Total Realised - ALL "Collection Realised - MISC BILL" lines
  MISC        = Sum of ALL "Collection Realised - MISC BILL" lines

MISC BILL fix: process each PDF page separately to avoid page-break merge issues.
"""
import pdfplumber
import re


def _total(path):
    """Extract 'Total  xxx' — last occurrence, from Debtors Summary Report."""
    with pdfplumber.open(path) as pdf:
        text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    m = re.search(r'Total\s+([\d,]+\.\d{2})\s*\n', text)
    return float(m.group(1).replace(",", "")) if m else 0.0


def _grand_total(path):
    """Extract 'Grand Total  xxx' from Sales Report."""
    with pdfplumber.open(path) as pdf:
        text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    m = re.search(r'Grand [Tt]otal\s+([\d,]+\.\d{2})', text)
    return float(m.group(1).replace(",", "")) if m else 0.0


def _credits_grand_total(path):
    """Extract 'GRAND TOTAL  xxx' from Credits Summary."""
    with pdfplumber.open(path) as pdf:
        text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    m = re.search(r'GRAND TOTAL\s+([\d,]+\.\d{2})', text)
    return float(m.group(1).replace(",", "")) if m else 0.0


def _recon_totals(path):
    """
    Extract from Payment Reconciliation Report.
    Process each page separately to avoid page-break line merge issues.

    Returns (total_realised, misc_collections)
      total_realised   = last TOTAL COLLECTION figure (after reversals)
      misc_collections = sum of all 'Collection Realised - MISC BILL' lines
    """
    with pdfplumber.open(path) as pdf:
        pages = [p.extract_text() or "" for p in pdf.pages]

    # Last TOTAL COLLECTION = realised figure
    all_totals = []
    for page in pages:
        all_totals += re.findall(r'TOTAL COLLECTION\s+([\d,]+\.\d{2})', page)
    total_realised = float(all_totals[-1].replace(",", "")) if all_totals else 0.0

    # MISC BILL lines — per page, deduplicated by payment mode
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
    """
    Returns figures dict for the reconciliation calculator.

    elec_bfadj = open.pdf Total  → this IS 'Balance b/f (after adjustment)'
    elec_bf    = prior month c/f → this IS 'Balance b/f'
    elec_adj1  = elec_bfadj - elec_bf  (computed by calculator, not parser)

    The parser returns elec_bfadj from open.pdf.
    The frontend review step must also show elec_bf (prior c/f) for manual confirmation.
    """
    # open.pdf = current month system opening = Balance b/f (after adjustment)
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
        # Balance b/f (after adjustment) — from open.pdf
        "elec_bfadj":        elec_bfadj,
        "misc_bfadj":        misc_bfadj,
        # Balance b/f (prior month c/f) — user confirms in review step
        # Default to elec_bfadj; frontend overrides with prior c/f
        "elec_bf":           elec_bfadj,
        "misc_bf":           misc_bfadj,
        # Closings
        "elec_close_system": elec_close_system,
        "misc_close_system": misc_close_system,
        # Sales
        "elec_sales":        elec_sales,
        "misc_sales":        misc_sales,
        # Credits
        "elec_credits":      elec_credits,
        "misc_credits":      0.0,
        # Collection
        "total_realised":    total_realised,
        "misc_collections":  misc_coll,
        "elec_collection":   total_realised - misc_coll,
        "misc_collection":   misc_coll,
    }
