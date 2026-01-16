from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import json
import os
import sqlite3
from datetime import datetime

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(APP_DIR, "data")
DB_PATH = os.path.join(APP_DIR, "leads.sqlite3")

app = FastAPI(title="Taller Rapai Quiindy - Sitio Starter")

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
                mensaje TEXT NOT NULL,
                categoria TEXT,
                origen TEXT
            );
        """)
        conn.commit()

@app.on_event("startup")
def startup():
    init_db()

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    site = load_json("site.json")
    catalogo = load_json("catalogo.json")
    return templates.TemplateResponse("index.html", {
        "request": request,
        "site": site,
        "catalogo": catalogo
    })

@app.post("/lead")
def crear_lead(
    request: Request,
    nombre: str = Form(...),
    telefono: str = Form(""),
    categoria: str = Form(""),
    mensaje: str = Form(...),
    origen: str = Form("web")
):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO leads (created_at, nombre, telefono, mensaje, categoria, origen) VALUES (?, ?, ?, ?, ?, ?)",
            (datetime.utcnow().isoformat(), nombre.strip(), telefono.strip(), mensaje.strip(), categoria.strip(), origen.strip())
        )
        conn.commit()

    # AJAX?
    if request.headers.get("x-requested-with", "").lower() == "fetch":
        return JSONResponse({"ok": True})

    return RedirectResponse(url="/thanks", status_code=303)

@app.get("/thanks", response_class=HTMLResponse)
def thanks(request: Request):
    site = load_json("site.json")
    return templates.TemplateResponse("thanks.html", {"request": request, "site": site})

# Opcional (para ti): ver últimos leads rápidamente
@app.get("/_leads")
def ver_leads():
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT id, created_at, nombre, telefono, categoria, mensaje FROM leads ORDER BY id DESC LIMIT 50"
        ).fetchall()
    return JSONResponse([
        {"id": r[0], "created_at": r[1], "nombre": r[2], "telefono": r[3], "categoria": r[4], "mensaje": r[5]}
        for r in rows
    ])
