from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import tempfile, os, json, io
from parser.male import parse_male
from parser.hulhumale import parse_hulhumale
from parser.thilafushi import parse_thilafushi
from parser.gulhi_falhu import parse_gulhi_falhu
from parser.adjustments import find_adjustments, ISLAND_BY_LOCATION
from reconciliation.calculator import calculate
from reconciliation.generator import generate_docx
app = FastAPI(title="STELCO Debtors Reconciliation API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
PARSERS = {
    "male":       parse_male,
    "hulhumale":  parse_hulhumale,
    "thilafushi": parse_thilafushi,
    "gulhi_falhu":parse_gulhi_falhu,
}
@app.get("/")
def root():
    return {"status": "STELCO Recon API running"}
@app.post("/parse")
async def parse_files(
    location: str = Form(...),
    open_pdf:       UploadFile = File(...),
    close_pdf:      UploadFile = File(...),
    sales_pdf:      UploadFile = File(...),
    misc_open_pdf:  UploadFile = File(...),
    misc_close_pdf: UploadFile = File(...),
    misc_sales_pdf: UploadFile = File(None),
    recon_pdf:      UploadFile = File(...),
    collection_pdf: UploadFile = File(...),
    cash_collection_pdf: UploadFile = File(None),   # Hulhumale' only
):
    """
    Step 1 — Parse all uploaded PDFs and return extracted figures for review.
    """
    if location not in PARSERS:
        raise HTTPException(400, f"Unknown location: {location}")
    # Save uploads to temp files
    files = {}
    uploads = {
        "open":            open_pdf,
        "close":           close_pdf,
        "sales":           sales_pdf,
        "misc_open":       misc_open_pdf,
        "misc_close":      misc_close_pdf,
        "misc_sales":      misc_sales_pdf,
        "recon":           recon_pdf,
        "collection":      collection_pdf,
        "cash_collection": cash_collection_pdf,
    }
    tmp_dir = tempfile.mkdtemp()
    for key, upload in uploads.items():
        if upload is None:
            files[key] = None
            continue
        path = os.path.join(tmp_dir, f"{key}.pdf")
        content = await upload.read()
        with open(path, "wb") as f:
            f.write(content)
        files[key] = path
    try:
        figures = PARSERS[location](files)
        return {"location": location, "figures": figures}
    except Exception as e:
        raise HTTPException(500, f"Parse error: {str(e)}")
@app.post("/generate")
async def generate_report(
    location: str = Form(...),
    figures:  str = Form(...),   # JSON string of (possibly edited) figures
    report_date: str = Form(...),
):
    """
    Step 2 — Receive (reviewed/edited) figures, calculate reconciliation, generate .docx.
    """
    if location not in PARSERS:
        raise HTTPException(400, f"Unknown location: {location}")
    try:
        figs = json.loads(figures)
    except Exception:
        raise HTTPException(400, "Invalid figures JSON")
    try:
        result = calculate(location, figs)
        out_path = generate_docx(location, result, report_date)
        return FileResponse(
            out_path,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=f"{location.upper()}_{report_date.replace('-','_')}_Debtors_Reconciliation.docx"
        )
    except Exception as e:
        raise HTTPException(500, f"Generation error: {str(e)}")
# ──────────────────────────────────────────────────────────────────────
# ADJUSTMENT TAB — independent of the reconciliation flow above.
# Diffs prior-month CLOSING debtors vs current-month OPENING debtors and
# returns Adjustment (1) plus the full invoice-level detail.
# ──────────────────────────────────────────────────────────────────────
@app.post("/adjustments")
async def adjustments(
    location: str = Form(...),
    report_date: str = Form(None),
    recon_report:  UploadFile = File(None),   # current reconciliation report (.docx/.pdf) — for the annexure
    adj_close_csv: UploadFile = File(...),     # previous month CLOSING debtors export (.csv)
    adj_open_csv:  UploadFile = File(...),     # current month OPENING debtors export (.csv)
):
    if location not in ISLAND_BY_LOCATION:
        raise HTTPException(400, f"Unknown location: {location}")
    try:
        close_bytes = await adj_close_csv.read()
        open_bytes  = await adj_open_csv.read()
        items, summary = find_adjustments(
            io.BytesIO(close_bytes),
            io.BytesIO(open_bytes),
            island=ISLAND_BY_LOCATION[location],
        )
        return {
            "location": location,
            "report_date": report_date,
            "summary": summary,     # close_total, open_total, adjustment, counts...
            "detail": items,        # invoice-level rows
        }
    except Exception as e:
        raise HTTPException(500, f"Adjustment error: {str(e)}")
