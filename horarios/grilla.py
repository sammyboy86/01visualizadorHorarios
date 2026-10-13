# -*- coding: utf-8 -*-
"""
Grilla semanal de 30 minutos y parseo de horarios.

Una grilla es una lista de filas (una por franja de 30 min). Cada fila tiene una
celda por día; una sesión ocupa `rowspan` filas y las celdas que "tapa" se
eliminan con `cleanup` antes de renderizar la plantilla HTML.
"""
import datetime as dt
import re
from typing import Callable

import pandas as pd

from horarios.config import DIA_LETRA, DIA_PREFIX

# Sesión: (letra_día, "HH:MM" inicio, "HH:MM" fin)
Sesion = tuple[str, str, str]
# Clave de celda: (nombre_día, inicio, fin)
ClaveCelda = tuple[str, str, str]

_RE_SESION = re.compile(r"^([A-Za-zÁÉÍÓÚáéíóúÑñ]+)\((\d{2}:\d{2})-(\d{2}:\d{2})\)$")

SIN_DOCENTE = "<b>SIN DOCENTE ASIGNADO</b>"


# ═════════════════════════════════════════════════════════════
# Parseo
# ═════════════════════════════════════════════════════════════

def parse_group_schedule(gs) -> list[Sesion]:
    """'Lu(07:00-09:00) Mi(07:00-09:00)' → [('L','07:00','09:00'), ('W','07:00','09:00')]."""
    out = []
    if pd.isna(gs):
        return out
    for token in str(gs).split():
        m = _RE_SESION.match(token)
        if not m:
            continue
        d_raw, start, end = m.groups()
        d = DIA_PREFIX.get(d_raw.upper(), d_raw.upper()[:1])
        d = "D" if d in ("D", "F") else d
        out.append((d, start, end))
    return out


def bloques_30(h_ini: str, h_fin: str):
    """Genera las etiquetas 'HH:MM - HH:MM' de cada franja de 30 min."""
    t0, t1 = (dt.datetime.strptime(t, "%H:%M") for t in (h_ini, h_fin))
    while t0 < t1:
        nxt = t0 + dt.timedelta(minutes=30)
        yield f"{t0:%H:%M} - {nxt:%H:%M}"
        t0 = nxt


def span_30m(start: str, end: str) -> int:
    """Cantidad de franjas de 30 min que ocupa una sesión (mínimo 1)."""
    t0 = dt.datetime.strptime(start, "%H:%M")
    t1 = dt.datetime.strptime(end, "%H:%M")
    return max(1, int((t1 - t0).seconds / 1800))


# ═════════════════════════════════════════════════════════════
# Construcción de la grilla
# ═════════════════════════════════════════════════════════════

def make_grid(h_ini: str, h_fin: str) -> list[dict]:
    dias = list(DIA_LETRA.values())
    return [
        {"hora": blk, "celdas": [{"dia": d, "contenido": "", "rowspan": 1, "skip": False} for d in dias]}
        for blk in bloques_30(h_ini, h_fin)
    ]


def place(grid: list[dict], idx: int, span: int, dia: str, txt: str) -> None:
    """Coloca `txt` en (fila idx, día) ocupando `span` filas."""
    for off in range(span):
        cell = next(c for c in grid[idx + off]["celdas"] if c["dia"] == dia)
        if off == 0:
            cell.update({"contenido": txt, "rowspan": span})
        else:
            cell["skip"] = True


def cleanup(grid: list[dict]) -> None:
    """Quita las celdas tapadas por un rowspan."""
    for row in grid:
        row["celdas"] = [c for c in row["celdas"] if not c.get("skip")]


def construir_grilla(
    contenido: dict[ClaveCelda, dict],
    h_ini: str,
    h_fin: str,
    formatear: Callable[[dict], str],
) -> list[dict]:
    """Arma una grilla completa a partir de {(día, inicio, fin): info}.

    `formatear(info)` devuelve el HTML de la celda. Las sesiones que empiezan
    fuera de la franja horaria se ignoran.
    """
    grid = make_grid(h_ini, h_fin)
    franjas = list(bloques_30(h_ini, h_fin))
    for (dia, start, end), info in contenido.items():
        idx = next((k for k, b in enumerate(franjas) if b.startswith(start)), None)
        if idx is None:
            continue
        place(grid, idx, span_30m(start, end), dia, formatear(info))
    cleanup(grid)
    return grid


# ═════════════════════════════════════════════════════════════
# Formato de celdas
# ═════════════════════════════════════════════════════════════

def docente_fmt(nombres) -> str:
    """Nombres únicos (en orden) separados por ' / ', o aviso si no hay docente."""
    seen, out = set(), []
    for n in nombres or []:
        if pd.isna(n) or n in seen:
            continue
        seen.add(n)
        out.append(n)
    return " / ".join(out) if out else SIN_DOCENTE


def unir(valores) -> str:
    """Valores ordenados y separados por coma."""
    return ", ".join(sorted(valores))
