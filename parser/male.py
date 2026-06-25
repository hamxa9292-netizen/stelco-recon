"""
Male' PDF Parser — verified against May 2026 real PDFs.

Key fixes:
1. elec_bf = prior month c/f (passed via open.pdf total, which IS the system opening)
   The calculator must set elec_bf = April c/f and adj1 = open.pdf - April c/f
   Here we return elec_open (system opening) separately so the calculator can derive adj1.

2. MISC BILL lines extracted per-page (not joined) to avoid page-break merge issues.

Collection formula:
  Electricity = Total Realised - ALL "Collection Realised - MISC BILL" lines
  MISC        = Sum of ALL "Collection Realised - MISC BILL" lines
"""
import pdfplumber
import re


def _total(path):
    """Extract 'Total  xxx' from Debtors Summary Report."""
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
    Extract from Payment Reconciliation Report — process each page separately
    to avoid page-break line merging issues.

    Returns (total_realised, misc_collections)
    """
    with pdfplumber.open(path) as pdf:
        pages = [p.extract_text() or "" for p in pdf.pages]

    # Last TOTAL COLLECTION across all pages = realised figure
    all_totals = []
    for page in pages:
        all_totals += re.findall(r'TOTAL COLLECTION\s+([\d,]+\.\d{2})', page)
    total_realised = float(all_totals[-1].replace(",", "")) if all_totals else 0.0

    # MISC BILL lines — process per page, deduplicate by mode
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
    Parse all Male' PDFs and return figures dict.

    Note on elec_bf vs elec_open:
    - elec_open  = open.pdf Total  (system opening snapshot = balance after adj)
    - elec_bf    = prior month c/f (the actual Balance b/f shown on the report)
    - The calculator computes: adj1 = elec_open - elec_bf
    Both are returned so the calculator/frontend can use them correctly.
    """
    elec_open         = _total(files["open"])          if files.get("open")         else 0.0
    misc_open         = _total(files["misc_open"])     if files.get("misc_open")    else 0.0
    elec_close_system = _total(files["close"])         if files.get("close")        else 0.0
    misc_close_system = _total(files["misc_close"])    if files.get("misc_close")   else 0.0
    elec_sales        = _grand_total(files["sales"])   if files.get("sales")        else 0.0
    misc_sales        = _grand_total(files["misc_sales"]) if files.get("misc_sales") else 0.0
    elec_credits      = _credits_grand_total(files["collection"]) if files.get("collection") else 0.0

    total_realised, misc_coll = (
        _recon_totals(files["recon"]) if files.get("recon") else (0.0, 0.0)
    )

    # elec_bf and misc_bf: the parser returns the system opening.
    # The frontend review step shows these as "Balance b/f (system opening)".
    # The user/calculator must set the actual b/f = prior month c/f.
    # We return elec_open as elec_bf here; adj1 will be 0 until overridden.
    # For Male': the prior month c/f is always different from open.pdf
    # so the review step allows manual correction.
    return {
        "elec_open":         elec_open,        # system opening snapshot
        "elec_bf":           elec_open,        # default; override with prior c/f in review
        "misc_bf":           misc_open,
        "elec_close_system": elec_close_system,
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
