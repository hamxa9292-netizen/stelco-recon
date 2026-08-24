"""
reconciliation/csv_parser.py
Replaces the PDF parsers: computes the same `figures` dict the web app's
review step already expects, but straight from CSV exports.
"""
import csv, io


def _text(src):
    if hasattr(src, "read"):
        d = src.read()
        return d.decode("utf-8-sig", "replace") if isinstance(d, (bytes, bytearray)) else d
    if isinstance(src, (bytes, bytearray)):
        return bytes(src).decode("utf-8-sig", "replace")
    with open(src, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return fh.read()


def _rows(src):
    if src is None:
        return []
    return list(csv.DictReader(io.StringIO(_text(src))))


def _num(x):
    x = (x or "").strip().replace(",", "")
    try:
        return float(x) if x else 0.0
    except ValueError:
        return 0.0


def _find(fields, preferred, keys):
    fields = [f for f in (fields or []) if f]
    for f in fields:
        if f.strip().lstrip("\ufeff").upper() == preferred.upper():
            return f
    low = {f.strip().lstrip("\ufeff").lower(): f for f in fields}
    if preferred.lower() in low:
        return low[preferred.lower()]
    for f in fields:
        if any(k in f.strip().lower() for k in keys):
            return f
    return None


def _sum(rows, preferred, keys):
    if not rows:
        return 0.0
    col = _find(rows[0].keys(), preferred, keys)
    if not col:
        return 0.0
    return round(sum(_num(r.get(col)) for r in rows), 2)


ELEC_DESCRIPTIONS = {"ELECTRICITY SALE", "FINE", "CHARGES FROM PREV BILL"}


def _realised_collection(rows):
    if not rows:
        return 0.0
    hdr = rows[0].keys()
    c_ord = _find(hdr, "ORD", ["ord"])
    c_canc = _find(hdr, "CANCEL_DATE", ["cancel"])
    c_desc = _find(hdr, "DESCRIPTION", ["description", "cdt_desc"])
    c_amt = _find(hdr, "COLLECT_AMOUNT", ["collect_amount", "collect"])
    c_comp = _find(hdr, "AMOUNT", ["amount"])
    total = 0.0
    for r in rows:
        if c_canc and (r.get(c_canc) or "").strip():
            continue
        if c_ord:
            if (r.get(c_ord) or "").strip() in ("1", "2"):
                total += _num(r.get(c_amt))
        elif c_desc:
            if (r.get(c_desc) or "").strip().upper() in ELEC_DESCRIPTIONS:
                total += _num(r.get(c_comp) if c_comp else r.get(c_amt))
        else:
            total += _num(r.get(c_amt))
    return round(total, 2)


def parse_csv_figures(files, location, passthrough=None):
    passthrough = passthrough or {}
    open_rows = _rows(files.get("open_csv"))
    close_rows = _rows(files.get("close_csv"))
    sales_rows = _rows(files.get("sales_csv"))
    coll_rows = _rows(files.get("collection_csv"))
    credits_rows = _rows(files.get("credits_csv"))
    prior_rows = _rows(files.get("prior_close_csv"))

    elec_bfadj = _sum(open_rows, "BALANCE_AMT", ["balance", "outstand"])
    elec_close = _sum(close_rows, "BALANCE_AMT", ["balance", "outstand"])
    elec_sales = _sum(sales_rows, "AMOUNT", ["amount"])
    elec_credits = _sum(credits_rows, "AMOUNT", ["amount"])
    elec_billing = _realised_collection(coll_rows)

    if prior_rows:
        elec_bf = _sum(prior_rows, "BALANCE_AMT", ["balance", "outstand"])
    else:
        elec_bf = _num(passthrough.get("elec_bf")) or elec_bfadj

    blueridge = _num(passthrough.get("blueridge"))
    wamco = _num(passthrough.get("wamco"))
    if location == "hulhumale":
        elec_collection = round(elec_billing + blueridge + wamco, 2)
    else:
        elec_collection = elec_billing

    figures = {
        "elec_bf": elec_bf,
        "elec_bfadj": elec_bfadj,
        "elec_sales": elec_sales,
        "elec_credits": elec_credits,
        "elec_discount": _num(passthrough.get("elec_discount")),
        "elec_collection": elec_collection,
        "elec_close_system": elec_close,
    }

    misc_open = _rows(files.get("misc_open_csv"))
    misc_close = _rows(files.get("misc_close_csv"))
    misc_sales = _rows(files.get("misc_sales_csv"))
    misc_coll = _rows(files.get("misc_coll_csv"))
    if misc_open or misc_close:
        m_bfadj = _sum(misc_open, "BALANCE_AMT", ["balance", "outstand"])
        figures.update({
            "misc_bf": m_bfadj,
            "misc_bfadj": m_bfadj,
            "misc_sales": _sum(misc_sales, "ITM_AMOUNT", ["itm_amount", "amount"]),
            "misc_credits": _num(passthrough.get("misc_credits")),
            "misc_discount": _num(passthrough.get("misc_discount")),
            "misc_collection": _sum(misc_coll, "AMOUNT", ["amount"]),
            "misc_close_system": _sum(misc_close, "BALANCE_AMT", ["balance", "outstand"]),
        })
    else:
        for k in ("misc_bf", "misc_bfadj", "misc_sales", "misc_credits",
                  "misc_discount", "misc_collection", "misc_close_system"):
            figures[k] = _num(passthrough.get(k))

    if location == "hulhumale":
        figures["billing_system"] = elec_billing
        figures["blueridge"] = blueridge
        figures["wamco"] = wamco
    return figures
