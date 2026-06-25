# STELCO Debtors Reconciliation App

A web application that parses STELCO billing system PDFs and generates
Debtors Reconciliation Statement `.docx` reports for Male', Hulhumale',
Thilafushi and Gulhi Falhu.

---

## Project Structure

```
recon-app/
├── frontend/          # Static web UI (GitHub Pages)
│   ├── index.html     # Step-by-step wizard
│   ├── css/style.css
│   └── js/app.js
├── backend/           # FastAPI server
│   ├── main.py        # API routes (/parse, /generate)
│   ├── parser/
│   │   ├── male.py
│   │   ├── hulhumale.py
│   │   ├── thilafushi.py   # stub — formula TBD
│   │   └── gulhi_falhu.py  # stub — formula TBD
│   ├── reconciliation/
│   │   ├── calculator.py   # per-location formula logic
│   │   └── generator.py    # .docx builder
│   └── requirements.txt
└── README.md
```

---

## Collection Formulas (per location)

| Location     | Formula |
|---|---|
| Male'        | Total Realised − MISC Collections |
| Hulhumale'   | Billing System Collection + Blueridge + WAMCO |
| Thilafushi   | TBD |
| Gulhi Falhu  | TBD |

---

## Local Setup (Backend)

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

API will be available at: http://localhost:8000
Interactive docs: http://localhost:8000/docs

---

## Local Setup (Frontend)

Open `frontend/index.html` directly in a browser, or serve with:

```bash
cd frontend
python -m http.server 3000
```

Set the `API_URL` variable in `frontend/js/app.js` to `http://localhost:8000`.

---

## Deployment

### Backend — Render (free tier)
1. Push repo to GitHub
2. Go to [render.com](https://render.com) → New Web Service
3. Connect your GitHub repo
4. Settings:
   - **Root Directory:** `backend`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Copy the deployed URL

### Frontend — GitHub Pages
1. Go to repo Settings → Pages
2. Source: `main` branch → `/frontend` folder
3. Update `API_URL` in `js/app.js` to your Render backend URL
4. Access at: `https://<your-username>.github.io/<repo-name>/`

---

## Wizard Flow

1. **Select Location** — Male' / Hulhumale' / Thilafushi / Gulhi Falhu
2. **Upload PDFs** — labeled slots per required file
3. **Review Figures** — editable table of all extracted values
4. **Generate** — downloads the `.docx` report

---

## Required PDFs (per month)

| File | Description |
|---|---|
| `open.pdf` | Debtors Summary As At opening date |
| `close.pdf` | Debtors Summary As At closing date |
| `sales.pdf` | Sales Report |
| `misc_open.pdf` | MISC Bills Debtors Summary (opening) |
| `misc_close.pdf` | MISC Bills Debtors Summary (closing) |
| `misc_sales.pdf` | MISC Sales Report (Male' only) |
| `recon.pdf` | Payment Reconciliation Report Summary |
| `collection.pdf` | Cash Collection Credits Summary |
| `cash_collection.pdf` | Cash Collection Report (Hulhumale' only) |
