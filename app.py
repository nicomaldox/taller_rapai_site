from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import json
import os
import sqlite3
from datetime import datetime
from base64 import b64decode

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(APP_DIR, "data")
DB_PATH = os.path.join(APP_DIR, "leads.sqlite3")

# ---- Basic Auth for /admin (Tier 2) ----
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "change-me")

def require_basic_auth(request: Request):
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Basic "):
        raise HTTPException(status_code=401, headers={"WWW-Authenticate": "Basic"})
    try:
        decoded = b64decode(auth.split(" ", 1)[1]).decode("utf-8")
        user, pwd = decoded.split(":", 1)
    except Exception:
        raise HTTPException(status_code=401, headers={"WWW-Authenticate": "Basic"})
    if user != ADMIN_USER or pwd != ADMIN_PASS:
        raise HTTPException(status_code=401, headers={"WWW-Authenticate": "Basic"})
    return True

app = FastAPI(title="Rapai Quiindy Performance - Tier 2")

app.mount("/static", StaticFiles(directory=os.path.join(APP_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(APP_DIR, "templates"))

def load_json(filename: str) -> dict:
    with open(os.path.join(DATA_DIR, filename), "r", encoding="utf-8") as f:
        return json.load(f)

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                nombre TEXT NOT NULL,
                telefono TEXT,
                categoria TEXT,
                item TEXT,
                mensaje TEXT NOT NULL,
                preferencia_contacto TEXT,
                origen TEXT
            );
        """)
        conn.commit()

@app.on_event("startup")
def startup():
    init_db()

def common_context(request: Request):
    site = load_json("site.json")
    catalogo = load_json("catalogo.json")
    return {"request": request, "site": site, "catalogo": catalogo}

# ----- Pages -----
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("home.html", common_context(request))

@app.get("/catalogo", response_class=HTMLResponse)
def catalogo_page(request: Request):
    return templates.TemplateResponse("catalogo.html", common_context(request))

@app.get("/servicios", response_class=HTMLResponse)
def servicios_page(request: Request):
    return templates.TemplateResponse("servicios.html", common_context(request))

@app.get("/galeria", response_class=HTMLResponse)
def galeria_page(request: Request):
    return templates.TemplateResponse("galeria.html", common_context(request))

@app.get("/contacto", response_class=HTMLResponse)
def contacto_page(request: Request):
    return templates.TemplateResponse("contacto.html", common_context(request))

@app.get("/thanks", response_class=HTMLResponse)
def thanks(request: Request):
    return templates.TemplateResponse("thanks.html", common_context(request))

# ----- Lead capture -----
@app.post("/lead")
def crear_lead(
    request: Request,
    nombre: str = Form(...),
    telefono: str = Form(...),
    categoria: str = Form(""),
    item: str = Form(""),
    mensaje: str = Form(...),
    preferencia_contacto: str = Form("WhatsApp"),
    origen: str = Form("web"),
    company: str = Form("")  # honeypot (should stay empty)
):
    # honeypot spam protection
    if company.strip():
        return JSONResponse({"ok": True})

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """INSERT INTO leads
               (created_at, nombre, telefono, categoria, item, mensaje, preferencia_contacto, origen)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                datetime.utcnow().isoformat(),
                nombre.strip(),
                telefono.strip(),
                categoria.strip(),
                item.strip(),
                mensaje.strip(),
                preferencia_contacto.strip(),
                origen.strip()
            )
        )
        conn.commit()

    if request.headers.get("x-requested-with", "").lower() == "fetch":
        return JSONResponse({"ok": True})

    return RedirectResponse(url="/thanks", status_code=303)

# ----- Admin (Tier 2) -----
@app.get("/admin/leads", response_class=HTMLResponse)
def admin_leads(request: Request, _=Depends(require_basic_auth)):
    ctx = common_context(request)
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            """SELECT id, created_at, nombre, telefono, categoria, item, preferencia_contacto, mensaje
               FROM leads ORDER BY id DESC LIMIT 200"""
        ).fetchall()
    ctx["rows"] = rows
    return templates.TemplateResponse("admin_leads.html", ctx)

@app.get("/admin/leads.csv")
def admin_leads_csv(_=Depends(require_basic_auth)):
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            """SELECT id, created_at, nombre, telefono, categoria, item, preferencia_contacto, mensaje
               FROM leads ORDER BY id DESC"""
        ).fetchall()

    def esc(s):
        s = "" if s is None else str(s)
        s = s.replace('"', '""')
        return f'"{s}"'

    header = ["id","created_at","nombre","telefono","categoria","item","preferencia_contacto","mensaje"]
    lines = [",".join(header)]
    for r in rows:
        lines.append(",".join(esc(x) for x in r))
    csv_data = "\n".join(lines)
    return Response(content=csv_data, media_type="text/csv")

# ----- SEO helpers -----
@app.get("/robots.txt")
def robots():
    return PlainTextResponse("User-agent: *\nAllow: /\nSitemap: /sitemap.xml\n")

@app.get("/sitemap.xml")
def sitemap():
    urls = ["/", "/catalogo", "/servicios", "/galeria", "/contacto"]
    body = "\n".join([f"<url><loc>{u}</loc></url>" for u in urls])
    xml = f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{body}\n</urlset>'
    return Response(content=xml, media_type="application/xml")
