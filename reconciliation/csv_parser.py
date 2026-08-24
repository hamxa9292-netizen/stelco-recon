"""
reconciliation/csv_parser.py
Computes the same `figures` dict the web app's review step expects, from CSVs.
Streams each file (row by row) so 100k+ row files use minimal memory instead
of loading every row into a list.
"""
import csv, io

ELEC_DESCRIPTIONS = {"ELECTRICITY SALE", "FINE", "CHARGES FROM PREV BILL"}


def _text(src):
    if src is None:
        return None
    if hasattr(src, "read"):
        d = src.read()
        return d.decode("utf-8-sig", "replace") if isinstance(d, (bytes, bytearray)) else d
    if isinstance(src, (bytes, bytearray)):
        return bytes(src).decode("utf-8-sig", "replace")
    with open(src, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return fh.read()


def _num(x):
    x = (x or "").strip().replace(",", "")
    try:
        return float(x) if x else 0.0
    except ValueError:
        return 0.0


def _find_idx(header, preferred, keys):
    hs = [(h or "").strip().lstrip("\ufeff") for h in header]
    for i, h in enumerate(hs):
        if h.upper() == preferred.upper():
            return i
    low = {h.lower(): i for i, h in enumerate(hs)}
    if preferred.lower() in low:
        return low[preferred.lower()]
    for i, h in enumerate(hs):
        if any(k in h.lower() for k in keys):
            return i
    return None


def _reader(src):
    txt = _text(src)
    if txt is None:
        return None
    return csv.reader(io.StringIO(txt))


def _stream_sum(src, preferred, keys):
    """Sum one column, streaming - never holds all rows."""
    rdr = _reader(src)
    if rdr is None:
        return 0.0
    try:
        header = next(rdr)
    except StopIteration:
        return 0.0
    idx = _find_idx(header, preferred, keys)
    if idx is None:
        return 0.0
    total = 0.0
    for row in rdr:
        if idx < len(row):
            total += _num(row[idx])
    return round(total, 2)


def _stream_realised(src):
    """Realised collection: ORD 1+2 (cancelled excluded), or DESCRIPTION-filtered
    for no-ORD files. Streams row by row."""
    rdr = _reader(src)
    if rdr is None:
        return 0.0
    try:
        header = next(rdr)
    except StopIteration:
        return 0.0
    i_ord = _find_idx(header, "ORD", ["ord"])
    i_canc = _find_idx(header, "CANCEL_DATE", ["cancel"])
    i_desc = _find_idx(header, "DESCRIPTION", ["description", "cdt_desc"])
    i_amt = _find_idx(header, "COLLECT_AMOUNT", ["collect_amount", "collect"])
    i_comp = _find_idx(header, "AMOUNT", ["amount"])
    total = 0.0
    for row in rdr:
        if i_canc is not None and i_canc < len(row) and row[i_canc].strip():
            continue
        if i_ord is not None:
            o = row[i_ord].strip() if i_ord < len(row) else ""
            if o in ("1", "2") and i_amt is not None and i_amt < len(row):
                total += _num(row[i_amt])
        elif i_desc is not None:
            d = row[i_desc].strip().upper() if i_desc < len(row) else ""
            if d in ELEC_DESCRIPTIONS:
                col = i_comp if i_comp is not None else i_amt
                if col is not None and col < len(row):
                    total += _num(row[col])
        else:
            if i_amt is not None and i_amt < len(row):
                total += _num(row[i_amt])
    return round(total, 2)


def _misc_sales_total(src):
    """MISC sales = each invoice's INVTOT counted once (grouped by BILLNO).
    Robust to rows where a comma inside a description shifted the columns and
    zeroed ITM_AMOUNT. Falls back to summing ITM_AMOUNT if BILLNO/INVTOT
    are not present. When the file is clean, this equals SUM(ITM_AMOUNT)."""
    rdr = _reader(src)
    if rdr is None:
        return 0.0
    try:
        header = next(rdr)
    except StopIteration:
        return 0.0
    i_bill = _find_idx(header, "BILLNO", ["billno", "bill_no"])
    i_inv = _find_idx(header, "INVTOT", ["invtot", "inv_tot"])
    i_itm = _find_idx(header, "ITM_AMOUNT", ["itm_amount"])
    if i_bill is None or i_inv is None:
        if i_itm is None:
            return 0.0
        total = 0.0
        for row in rdr:
            if i_itm < len(row):
                total += _num(row[i_itm])
        return round(total, 2)
    per_bill = {}
    for row in rdr:
        b = row[i_bill].strip() if i_bill < len(row) else ""
        it = _num(row[i_inv]) if i_inv < len(row) else 0.0
        if not b:
            continue
        if it > per_bill.get(b, 0.0):   # one invoice total per bill; text-corrupted rows read as 0
            per_bill[b] = it
    return round(sum(per_bill.values()), 2)


def parse_csv_figures(files, location, passthrough=None):
    passthrough = passthrough or {}
    BAL = ("BALANCE_AMT", ["balance", "outstand"])

    elec_bfadj = _stream_sum(files.get("open_csv"), *BAL)
    elec_close = _stream_sum(files.get("close_csv"), *BAL)
    elec_sales = _stream_sum(files.get("sales_csv"), "AMOUNT", ["amount"])
    elec_credits = _stream_sum(files.get("credits_csv"), "AMOUNT", ["amount"])
    elec_billing = _stream_realised(files.get("collection_csv"))

    if files.get("prior_close_csv") is not None:
        elec_bf = _stream_sum(files.get("prior_close_csv"), *BAL)
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

    has_misc = files.get("misc_open_csv") is not None or files.get("misc_close_csv") is not None
    if has_misc:
        m_bfadj = _stream_sum(files.get("misc_open_csv"), *BAL)
        figures.update({
            "misc_bf": m_bfadj,
            "misc_bfadj": m_bfadj,
            "misc_sales": _misc_sales_total(files.get("misc_sales_csv")),
            "misc_credits": _num(passthrough.get("misc_credits")),
            "misc_discount": _num(passthrough.get("misc_discount")),
            "misc_collection": _stream_sum(files.get("misc_coll_csv"), "AMOUNT", ["amount"]),
            "misc_close_system": _stream_sum(files.get("misc_close_csv"), *BAL),
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
