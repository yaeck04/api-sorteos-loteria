from fastapi import FastAPI, Request
from pydantic import BaseModel
import os
import json
import requests
from datetime import datetime

app = FastAPI()

EMAIL = "khloealba932@gmail.com"
PASSWORD = "Anabelyae04"

URLS_TXT = {
    ("GA", "M"): "https://www.lotterycorner.com/results/download/ga-cash-3-midday-2025.txt",
    ("GA", "E"): "https://www.lotterycorner.com/results/download/ga-cash-3-evening-2025.txt",
    ("GA", "N"): "https://www.lotterycorner.com/results/download/ga-cash-3-night-2025.txt",
    ("FL", "M"): "https://www.lotterycorner.com/results/download/fl-pick-3-midday-2025.txt",
    ("FL", "E"): "https://www.lotterycorner.com/results/download/fl-pick-3-evening-2025.txt",
    ("NY", "M"): "https://www.lotterycorner.com/results/download/ny-numbers-midday-2025.txt",
    ("NY", "E"): "https://www.lotterycorner.com/results/download/ny-numbers-evening-2025.txt",
}

PRIORIDAD = {
    "GA_M": 0, "FL_M": 1, "NY_M": 2,
    "GA_E": 3, "FL_E": 4, "NY_E": 5,
    "GA_N": 6
}


class UltimaEntrada(BaseModel):
    date: str  # "dd/mm/yy"
    state: str
    draw: str


def generar_fijos(numeros):
    partes = numeros.split("-")
    return [partes[1] + partes[2], partes[2] + partes[1]]


def login_y_descargar_archivos():
    session = requests.Session()
    login_url = "https://www.lotterycorner.com/insider/login"
    login_data = {"email": EMAIL, "pwd": PASSWORD}
    r = session.post(login_url, data=login_data)
    if "Logout" not in r.text:
        raise Exception("Login fallido")

    contenidos = {}
    for (estado, sorteo), url in URLS_TXT.items():
        r = session.get(url)
        r.raise_for_status()
        contenidos[(estado, sorteo)] = r.text
    return contenidos


def parsear_txt(texto, estado, sorteo):
    resultados = []
    lineas = texto.strip().splitlines()[1:]
    for linea in lineas:
        partes = linea.split(",")
        if len(partes) >= 2:
            fecha_str, numeros = partes[0].strip(), partes[1].strip()
            try:
                fecha = datetime.strptime(fecha_str, "%a %m/%d/%Y")
            except ValueError:
                continue

            if estado == "FL":
                digitos = numeros.split("-")
                if len(digitos) >= 3:
                    numeros = "-".join(digitos[:3])

            fecha_fmt = fecha.strftime("%d/%m/%y")
            resultados.append({
                "date": fecha_fmt,
                "state": estado,
                "draw": sorteo,
                "numbers": numeros,
                "fijos": generar_fijos(numeros)
            })
    return resultados


@app.post("/actualizar")
def actualizar_endpoint(payload: UltimaEntrada):
    combinaciones = {}
    try:
        txts = login_y_descargar_archivos()
    except Exception as e:
        return {"error": str(e)}

    nuevos = []
    fecha_ref = datetime.strptime(payload.date, "%d/%m/%y")
    encontrado = False

    for (estado, sorteo), texto in txts.items():
        datos = parsear_txt(texto, estado, sorteo)
        for s in datos:
            clave = f"{s['date']}-{s['state']}-{s['draw']}"
            s_fecha = datetime.strptime(s["date"], "%d/%m/%y")
            if (s_fecha > fecha_ref or
                (s_fecha == fecha_ref and s["state"] == payload.state and s["draw"] > payload.draw)):
                nuevos.append(s)

    nuevos.sort(key=lambda s: (
        datetime.strptime(s["date"], "%d/%m/%y"),
        PRIORIDAD.get(f"{s['state']}_{s['draw']}", 99)
    ))

    return {"nuevos": nuevos, "total": len(nuevos)}
