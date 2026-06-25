"""
Male' PDF Parser — precise regex patterns verified against real PDFs
"""
import pdfplumber, re


def _total(path):
    with pdfplumber.open(path) as pdf:
        text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    m = re.search(r'Total\s+([\d,]+\.\d{2})\s*\n', text)
    return float(m.group(1).replace(",", "")) if m else 0.0


def _grand_total(path):
    """Sales report: 'Grand Total 73,117,008.93' on one line."""
    with pdfplumber.open(path) as pdf:
        text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    m = re.search(r'Grand [Tt]otal\s+([\d,]+\.\d{2})', text)
    return float(m.group(1).replace(",", "")) if m else 0.0


def _credits_total(path):
    with pdfplumber.open(path) as pdf:
        text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    m = re.search(r'GRAND TOTAL\s+([\d,]+\.\d{2})', text)
    return float(m.group(1).replace(",", "")) if m else 0.0


def _recon_totals(path):
    """Returns (total_realised, misc_collections)."""
    with pdfplumber.open(path) as pdf:
        text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    # Last TOTAL COLLECTION = realised figure (page 2)
    totals = re.findall(r'TOTAL COLLECTION\s+([\d,]+\.\d{2})', text)
    total_realised = float(totals[-1].replace(",", "")) if totals else 0.0
    # MISC BILL collections
    misc_lines = re.findall(r'Collection Realised - MISC BILL\s+\S+\s+([\d,]+\.\d{2})', text)
    misc_total = sum(float(v.replace(",", "")) for v in misc_lines)
    return total_realised, misc_total


def parse_male(files):
    elec_bf           = _total(files["open"]) if files.get("open") else 0.0
    misc_bf           = _total(files["misc_open"]) if files.get("misc_open") else 0.0
    elec_close_system = _total(files["close"]) if files.get("close") else 0.0
    misc_close_system = _total(files["misc_close"]) if files.get("misc_close") else 0.0
    elec_sales        = _grand_total(files["sales"]) if files.get("sales") else 0.0
    misc_sales        = _grand_total(files["misc_sales"]) if files.get("misc_sales") else 0.0
    elec_credits      = _credits_total(files["collection"]) if files.get("collection") else 0.0

    total_realised, misc_coll = _recon_totals(files["recon"]) if files.get("recon") else (0.0, 0.0)

    # Male' formula: Electricity = Total Realised - MISC Collections
    elec_collection = total_realised - misc_coll
    misc_collection = misc_coll

    return {
        "elec_bf":           elec_bf,
        "misc_bf":           misc_bf,
        "elec_close_system": elec_close_system,
        "misc_close_system": misc_close_system,
        "elec_sales":        elec_sales,
        "misc_sales":        misc_sales,
        "elec_credits":      elec_credits,
        "misc_credits":      0.0,
        "total_realised":    total_realised,
        "misc_collections":  misc_coll,
        "elec_collection":   elec_collection,
        "misc_collection":   misc_collection,
    }
