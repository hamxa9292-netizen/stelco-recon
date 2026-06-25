"""
Male' PDF Parser
Extracts all figures needed for the Debtors Reconciliation Statement.
"""
import pdfplumber, re


def _extract_total(pdf_path: str) -> float:
    """Return the grand/summary Total from a debtors summary PDF."""
    with pdfplumber.open(pdf_path) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    match = re.search(r"Total\s+([\d,]+\.\d{2})", text)
    if match:
        return float(match.group(1).replace(",", ""))
    raise ValueError(f"Could not find Total in {pdf_path}")


def _extract_sales_grand_total(pdf_path: str) -> float:
    with pdfplumber.open(pdf_path) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    match = re.search(r"Grand Total\s+([\d,]+\.\d{2})", text)
    if match:
        return float(match.group(1).replace(",", ""))
    raise ValueError(f"Could not find Grand Total in {pdf_path}")


def _extract_credits_grand_total(pdf_path: str) -> float:
    with pdfplumber.open(pdf_path) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    match = re.search(r"GRAND TOTAL\s+([\d,]+\.\d{2})", text)
    if match:
        return float(match.group(1).replace(",", ""))
    raise ValueError(f"Could not find GRAND TOTAL in {pdf_path}")


def _extract_recon_totals(pdf_path: str) -> dict:
    """
    Extract from Payment Reconciliation Report:
    - Total Collection (realised, page 2)
    - MISC Collections (sum of Collection Realised - MISC BILL lines)
    """
    with pdfplumber.open(pdf_path) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)

    # Total Collection Realised (last occurrence)
    totals = re.findall(r"TOTAL COLLECTION\s+([\d,]+\.\d{2})", text)
    total_realised = float(totals[-1].replace(",", "")) if totals else 0.0

    # MISC BILL lines
    misc_lines = re.findall(
        r"Collection Realised - MISC BILL\s+\S+\s+([\d,]+\.\d{2})", text
    )
    misc_total = sum(float(v.replace(",", "")) for v in misc_lines)

    return {
        "total_realised": total_realised,
        "misc_collections": misc_total,
    }


def parse_male(files: dict) -> dict:
    """
    Returns a dict of all extracted figures for Male' reconciliation.
    """
    figures = {}

    # Opening balance (Electricity) — from open.pdf
    figures["elec_open"] = _extract_total(files["open"])

    # Opening balance (MISC) — from misc_open.pdf
    figures["misc_open"] = _extract_total(files["misc_open"])

    # Previous month closing (for b/f) — same as open for Male'
    # The b/f is taken as the system opening snapshot
    figures["elec_bf"] = figures["elec_open"]
    figures["misc_bf"] = figures["misc_open"]

    # Closing balances (system)
    figures["elec_close_system"] = _extract_total(files["close"])
    figures["misc_close_system"] = _extract_total(files["misc_close"])

    # Sales
    figures["elec_sales"] = _extract_sales_grand_total(files["sales"])
    figures["misc_sales"] = (
        _extract_sales_grand_total(files["misc_sales"])
        if files.get("misc_sales") else 0.0
    )

    # Credits / Fine
    figures["elec_credits"] = _extract_credits_grand_total(files["collection"])
    figures["misc_credits"] = 0.0

    # Recon totals
    recon = _extract_recon_totals(files["recon"])
    figures["total_realised"]   = recon["total_realised"]
    figures["misc_collections"] = recon["misc_collections"]

    # Collection for the month
    # Male' formula: Total Realised - MISC Collections
    figures["elec_collection"] = recon["total_realised"] - recon["misc_collections"]
    figures["misc_collection"]  = recon["misc_collections"]

    return figures
