"""
Hulhumale' PDF Parser — precise regex patterns verified against real PDFs
Collection formula: Billing System (electric fee subtotal) + Blueridge + WAMCO

Billing System Collection now comes from its OWN uploaded report (files["billing"]).
The Cash Collection Report (files["cash_collection"]) is the Collections Dept
report, used only for Blueridge + WAMCO. If the dedicated billing file is not
uploaded, billing falls back to the cash-collection page-1 figure so nothing breaks.
"""
import pdfplumber, re


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


def _credits_total(path):
    with pdfplumber.open(path) as pdf:
        text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    m = re.search(r'GRAND TOTAL\s+([\d,]+\.\d{2})', text)
    return float(m.group(1).replace(",", "")) if m else 0.0


def _billing_system(path):
    """
    Electric-fee subtotal from the dedicated Billing System Collection PDF.
    The subtotal sits on its own line just above 'Total of other'/'Grand total'.
    Pattern: '69,139,011.04  397,900.45\nTotal of other'  -> first number.
    """
    with pdfplumber.open(path) as pdf:
        text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    # subtotal followed by the OTHERS column, then the 'Total of other'/'Grand' line
    m = re.search(r'([\d,]+\.\d{2})\s+[\d,]+\.\d{2}\s*\n(?:Total of other|Grand)', text)
    if m:
        return float(m.group(1).replace(",", ""))
    # fallback: subtotal alone on its own line above 'Total of other'/'Grand'
    m = re.search(r'\n([\d,]+\.\d{2})\s*\n(?:Total of other|Grand)', text)
    return float(m.group(1).replace(",", "")) if m else 0.0


def _cash_collection(path):
    """
    Extract from Hulhumale Cash Collection Report (Collections Dept report):
    - billing_system: electric fee subtotal (page 1) — kept for fallback only
    - blueridge: Blue Ridge Other Collections total (page 2)
    - wamco: WAMCO total (page 2)
    Pattern page1: '69,139,011.04  397,900.45\nTotal of other'
    Pattern page2: 'Total  36,100.00  -  86,950.00  -  499,200.00  3,996,221.26  4,618,471.26'
    """
    with pdfplumber.open(path) as pdf:
        pages = [p.extract_text() or "" for p in pdf.pages]
    page1 = pages[0] if pages else ""
    page2 = pages[1] if len(pages) > 1 else ""

    # Billing system electric fee subtotal (fallback source)
    billing_match = re.search(
        r'([\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s*\n(?:Total of other|Grand)',
        page1
    )
    billing_system = float(billing_match.group(1).replace(",", "")) if billing_match else 0.0

    # Blueridge + WAMCO from Total row on page 2
    # Format: Total  36,100.00  -  86,950.00  -  499,200.00  3,996,221.26  4,618,471.26
    total_row = re.search(
        r'Total\s+[\d,]+\.\d{2}\s+-\s+[\d,]+\.\d{2}\s+-\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})',
        page2
    )
    blueridge = float(total_row.group(1).replace(",", "")) if total_row else 0.0
    wamco     = float(total_row.group(2).replace(",", "")) if total_row else 0.0
    return billing_system, blueridge, wamco


def parse_hulhumale(files):
    elec_bf           = _total(files["open"]) if files.get("open") else 0.0
    misc_bf           = _total(files["misc_open"]) if files.get("misc_open") else 0.0
    elec_close_system = _total(files["close"]) if files.get("close") else 0.0
    misc_close_system = _total(files["misc_close"]) if files.get("misc_close") else 0.0
    elec_sales        = _grand_total(files["sales"]) if files.get("sales") else 0.0
    misc_sales        = _grand_total(files["misc_sales"]) if files.get("misc_sales") else 0.0
    elec_credits      = _credits_total(files["collection"]) if files.get("collection") else 0.0

    # Blueridge + WAMCO come from the Collections Dept cash collection report.
    _bs_from_cash, blueridge, wamco = (
        _cash_collection(files["cash_collection"])
        if files.get("cash_collection") else (0.0, 0.0, 0.0)
    )

    # Billing System Collection from its own report; fall back to the
    # cash-collection page-1 figure if the dedicated file isn't uploaded.
    billing_system = _billing_system(files["billing"]) if files.get("billing") else _bs_from_cash

    # Hulhumale formula: billing_system + blueridge + wamco
    elec_collection = billing_system + blueridge + wamco

    return {
        "elec_bf":           elec_bf,
        "misc_bf":           misc_bf,
        "elec_close_system": elec_close_system,
        "misc_close_system": misc_close_system,
        "elec_sales":        elec_sales,
        "misc_sales":        misc_sales,
        "elec_credits":      elec_credits,
        "misc_credits":      0.0,
        "billing_system":    billing_system,
        "blueridge":         blueridge,
        "wamco":             wamco,
        "elec_collection":   elec_collection,
        "misc_collection":   0.0,
    }
