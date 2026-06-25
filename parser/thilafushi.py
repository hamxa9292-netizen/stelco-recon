"""
Thilafushi PDF Parser — stub, to be configured once formula is confirmed.
"""
import pdfplumber, re


def _extract_total(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    match = re.search(r"Total\s+([\d,]+\.\d{2})", text)
    return float(match.group(1).replace(",", "")) if match else 0.0


def _extract_grand_total(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    match = re.search(r"Grand Total\s+([\d,]+\.\d{2})", text)
    return float(match.group(1).replace(",", "")) if match else 0.0


def parse_thilafushi(files: dict) -> dict:
    """Stub — returns raw extracted values; formula TBD."""
    return {
        "elec_bf":           _extract_total(files["open"]),
        "misc_bf":           _extract_total(files["misc_open"]),
        "elec_close_system": _extract_total(files["close"]),
        "misc_close_system": _extract_total(files["misc_close"]),
        "elec_sales":        _extract_grand_total(files["sales"]),
        "misc_sales":        _extract_grand_total(files["misc_sales"]) if files.get("misc_sales") else 0.0,
        "elec_credits":      0.0,
        "misc_credits":      0.0,
        "elec_collection":   0.0,   # to be confirmed and filled in review step
        "misc_collection":   0.0,
    }
