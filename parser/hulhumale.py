"""
Hulhumale' PDF Parser
Collection formula: Billing System Collection + Blueridge + WAMCO
"""
import pdfplumber, re


def _extract_total(pdf_path: str) -> float:
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


def _extract_cash_collection(pdf_path: str) -> dict:
    """
    Extract from Hulhumale' Cash Collection Report:
    - Billing System Collection (electric fee subtotal — the 69,139,011.04 line)
    - Blueridge (Blue Ridge Other Collections)
    - WAMCO total
    """
    with pdfplumber.open(pdf_path) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)

    # Billing system electric fee subtotal
    # Appears as a standalone number before "397,900.45" type GST subtotal
    billing_match = re.search(
        r"([\d,]+\.\d{2})\s+[\d,]+\.\d{2}\s*\n.*?Grand total", text, re.DOTALL
    )
    # Fallback: look for the subtotal line pattern
    billing_matches = re.findall(r"\n([\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s*\n", text)

    # Blueridge
    blueridge_match = re.search(
        r"BLUE RIDGE OTHER COLLECTIONS\s*(?:\(MANAGEMENT FEE\))?\s*([\d,]+\.\d{2})", text
    )
    blueridge = float(blueridge_match.group(1).replace(",", "")) if blueridge_match else 0.0

    # WAMCO — look for WAMCO total in Other Collection table
    wamco_match = re.search(r"Total.*?([\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s*$", text, re.MULTILINE)
    # More reliable: find the grand total row of other collections
    other_total_match = re.search(r"(?:Grand total|GRAND TOTAL)\s+([\d,]+\.\d{2})", text)
    grand_total = float(other_total_match.group(1).replace(",", "")) if other_total_match else 0.0

    # WAMCO = Other Total - Blueridge - Security Deposits - Temp Deposits etc
    # Better: find WAMCO column total directly
    wamco_matches = re.findall(r"([\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s*\n\s*Total", text)

    # Direct search for WAMCO total from Other Collection table
    wamco_direct = re.search(
        r"([\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s*\n\s*(?:Total|Prepared by)", text
    )

    # Return raw values; let the user verify in the review step
    return {
        "billing_system": 0.0,   # will be filled by user review if regex fails
        "blueridge": blueridge,
        "wamco": 0.0,            # will be filled by user review if regex fails
        "grand_total": grand_total,
    }


def parse_hulhumale(files: dict) -> dict:
    figures = {}

    # Opening balance = April c/f (open.pdf is the April closing snapshot)
    figures["elec_bf"] = _extract_total(files["open"])
    figures["misc_bf"] = _extract_total(files["misc_open"])

    # Closing balances (system)
    figures["elec_close_system"] = _extract_total(files["close"])
    figures["misc_close_system"] = _extract_total(files["misc_close"])

    # Sales
    figures["elec_sales"] = _extract_sales_grand_total(files["sales"])
    figures["misc_sales"] = 0.0

    # Credits / Fine
    figures["elec_credits"] = _extract_credits_grand_total(files["collection"])
    figures["misc_credits"] = 0.0

    # Cash collection report (billing system + blueridge + wamco)
    if files.get("cash_collection"):
        cash = _extract_cash_collection(files["cash_collection"])
        figures["billing_system"] = cash["billing_system"]
        figures["blueridge"]      = cash["blueridge"]
        figures["wamco"]          = cash["wamco"]
    else:
        figures["billing_system"] = 0.0
        figures["blueridge"]      = 0.0
        figures["wamco"]          = 0.0

    # Collection formula: billing_system + blueridge + wamco
    figures["elec_collection"] = (
        figures["billing_system"] +
        figures["blueridge"] +
        figures["wamco"]
    )
    figures["misc_collection"] = 0.0

    return figures
