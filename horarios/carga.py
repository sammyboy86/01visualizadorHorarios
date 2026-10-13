# -*- coding: utf-8 -*-
"""
Lectura de los Excel de entrada.

Fuentes soportadas (en orden de preferencia):
  1. Reportes por sede  → "Reporte Horarios y Paquetes - Proceso *.xlsx"
  2. Excel consolidado  → cualquier otro .xlsx de la carpeta (respaldo)
  3. Reporte Secciones  → "Resultados*Secciones*Proceso*.xlsx" (salón real por día)

Todas las tablas se devuelven con el esquema interno de `config.COLUMNAS_INTERNAS`.
"""
import glob
import logging
import os

import pandas as pd

from horarios.config import (
    COLUMNAS_INTERNAS,
    COLUMNAS_SEDE,
    DIA_NUM_TO_LETRA,
    PATRON_REPORTE_SEDE,
    PATRON_SECCIONES,
    RUTA_ENTRADA,
    SKIP_XLSX_KEYWORDS,
)
from horarios.utils import formato_sala

# Tipo del mapa de salones: (SEDE, LIGA, letra_día) → "SALA - EDIFICIO"
SalonesMap = dict[tuple[str, str, str], str]


# ═════════════════════════════════════════════════════════════
# Búsqueda de archivos
# ═════════════════════════════════════════════════════════════

def _es_temporal_office(path: str) -> bool:
    return os.path.basename(path).startswith("~$")


def find_sede_report_excels(workdir=None) -> list[str]:
    """Reportes individuales por sede: 'Reporte Horarios y Paquetes - Proceso NNN.xlsx'."""
    wd = workdir or "."
    files = [f for f in glob.glob(os.path.join(wd, PATRON_REPORTE_SEDE)) if not _es_temporal_office(f)]
    return sorted(files)


def find_secciones_excels(workdir=None) -> list[str]:
    """Reporte(s) 'Resultados - Secciones - Proceso NNN.xlsx'.

    Trae, fila por fila, el salón real de cada sesión (LIGA + día) y su edificio,
    a diferencia del salón único por liga que trae 'Reporte Horarios y Paquetes'.
    Si no hay coincidencias con el patrón, acepta cualquier .xlsx con 'secciones'
    en el nombre.
    """
    wd = workdir or "."
    files = [f for f in glob.glob(os.path.join(wd, PATRON_SECCIONES)) if not _es_temporal_office(f)]
    if not files:
        files = [
            f for f in glob.glob(os.path.join(wd, "*.xlsx"))
            if not _es_temporal_office(f) and "secciones" in os.path.basename(f).lower()
        ]
    return sorted(files)


def find_input_excel(prefer: str = None, workdir=None) -> str:
    """Excel consolidado de respaldo: `prefer` si existe, si no el .xlsx más reciente."""
    wd = workdir or "."
    if prefer:
        prefer_abs = prefer if os.path.isabs(prefer) else os.path.join(wd, prefer)
        if os.path.exists(prefer_abs):
            return prefer_abs

    candidates = []
    for f in glob.glob(os.path.join(wd, "*.xlsx")):
        low = os.path.basename(f).lower()
        if _es_temporal_office(f) or any(k in low for k in SKIP_XLSX_KEYWORDS):
            continue
        candidates.append(f)

    if not candidates:
        raise FileNotFoundError("No se encontró ningún .xlsx de entrada en la carpeta actual.")
    return max(candidates, key=os.path.getmtime)


# ═════════════════════════════════════════════════════════════
# Detección de sedes
# ═════════════════════════════════════════════════════════════

def _columna_sede(columns) -> str | None:
    return next((c for c in columns if str(c).strip() in COLUMNAS_SEDE), None)


def detect_sedes(archivo) -> list[str]:
    """Códigos de sede presentes en un Excel (lee ≤1 000 filas).

    `archivo` puede ser una ruta o un objeto tipo archivo (p. ej. un upload de
    Streamlit); en ese caso se rebobina para poder leerlo de nuevo después.
    """
    try:
        df = pd.read_excel(archivo, engine="openpyxl", nrows=1000)
        if hasattr(archivo, "seek"):
            archivo.seek(0)
        col = _columna_sede(df.columns)
        if col is not None:
            return sorted(df[col].dropna().astype(str).unique().tolist())
    except Exception:
        pass
    return []


def _sedes_en_archivo(path: str) -> set[str]:
    """Lee solo la columna de sede para decidir si el archivo entra al filtro."""
    header = pd.read_excel(path, engine="openpyxl", nrows=0)
    col = _columna_sede(header.columns)
    if col is None:
        return set()
    series = pd.read_excel(path, usecols=[col], engine="openpyxl")[col]
    return set(series.dropna().astype(str).unique())


# ═════════════════════════════════════════════════════════════
# Carga de datos principales
# ═════════════════════════════════════════════════════════════

def load_data(path: str) -> pd.DataFrame:
    """Lee un Excel y renombra sus columnas al esquema interno."""
    df = pd.read_excel(path, engine="openpyxl")
    df.columns = [str(c).strip() for c in df.columns]
    return df.rename(columns=COLUMNAS_INTERNAS)


def _filtrar_sedes(df: pd.DataFrame, sedes: set[str]) -> pd.DataFrame:
    return df[df["SEDE"].astype(str).isin(sedes)].copy()


def load_data_unificado(path_entrada=None, sedes_filtro=None, workdir=None) -> pd.DataFrame:
    """Carga los reportes por sede y los concatena; si no hay, usa un Excel consolidado.

    sedes_filtro: set/list de códigos de plantel; solo se cargan archivos de esas sedes.
    """
    if sedes_filtro is not None:
        sedes_filtro = {str(s) for s in sedes_filtro}

    sede_files = find_sede_report_excels(workdir=workdir)
    if sede_files:
        return _cargar_reportes_por_sede(sede_files, sedes_filtro)
    return _cargar_consolidado(path_entrada, sedes_filtro, workdir)


def _cargar_reportes_por_sede(sede_files: list[str], sedes_filtro: set[str] | None) -> pd.DataFrame:
    dfs = []
    for f in sede_files:
        sedes_archivo = _sedes_en_archivo(f)
        if not sedes_archivo:
            logging.warning("Archivo sin sede identificable, se omite: %s", f)
            continue
        if sedes_filtro and not sedes_archivo.intersection(sedes_filtro):
            logging.info("Omitido %s: sede(s) %s fuera del filtro", f, ", ".join(sorted(sedes_archivo)))
            continue

        df = load_data(f)
        if df.empty:
            logging.warning("Archivo vacío, se omite: %s", f)
            continue
        if sedes_filtro:
            df = _filtrar_sedes(df, sedes_filtro)
            if df.empty:
                continue

        sedes = sorted(df["SEDE"].dropna().astype(str).unique())
        logging.info("Cargado %s: %d filas, sede(s): %s", f, len(df), ", ".join(sedes))
        dfs.append(df)

    if not dfs:
        if sedes_filtro:
            raise ValueError("No se encontraron reportes por sede para: " + ", ".join(sorted(sedes_filtro)))
        raise ValueError("Todos los reportes por sede están vacíos.")
    return pd.concat(dfs, ignore_index=True)


def _cargar_consolidado(path_entrada, sedes_filtro: set[str] | None, workdir) -> pd.DataFrame:
    path = path_entrada or find_input_excel(RUTA_ENTRADA, workdir=workdir)
    logging.info("Sin reportes por sede; usando consolidado: %s", path)
    df = load_data(path)
    if sedes_filtro:
        df = _filtrar_sedes(df, sedes_filtro)
        if df.empty:
            raise ValueError("El consolidado no tiene filas para las sedes: " + ", ".join(sorted(sedes_filtro)))
    return df


# ═════════════════════════════════════════════════════════════
# Salón real por (SEDE, LIGA, día) — reporte de Secciones
# ═════════════════════════════════════════════════════════════

def load_salones_por_liga_dia(sedes_filtro=None, workdir=None) -> SalonesMap:
    """Construye el mapa (SEDE, LIGA, día) → salón real (+ edificio si existe).

    Es el complemento que le falta a "Reporte Horarios y Paquetes" para poder
    mostrar un salón distinto por día cuando la liga cambia de salón entre sesiones.
    """
    archivos = find_secciones_excels(workdir=workdir)
    if not archivos:
        logging.warning(
            "No se encontró el reporte de Secciones (patrón: %s). Se usará el salón único "
            "de la liga para todos sus días (comportamiento anterior, puede ser incorrecto "
            "si la liga cambia de salón entre sesiones).",
            PATRON_SECCIONES,
        )
        return {}

    sedes_f = {str(s) for s in sedes_filtro} if sedes_filtro else None
    mapa: SalonesMap = {}
    conflictos = set()
    total_filas = 0

    for f in archivos:
        df = pd.read_excel(f, engine="openpyxl")
        df.columns = [str(c).strip() for c in df.columns]
        faltantes = {"SEDE", "LIGAS", "DIA", "SALA"} - set(df.columns)
        if faltantes:
            logging.warning("Secciones %s: faltan columnas %s; se omite este archivo.", f, faltantes)
            continue
        if sedes_f:
            df = df[df["SEDE"].astype(str).isin(sedes_f)]

        col_edificio = next(
            (c for c in df.columns if str(c).strip().upper() in ("EDIFICIO", "EDIFICIO ASIGNADO")),
            None,
        )

        for _, r in df.iterrows():
            total_filas += 1
            letra = _letra_dia(r.get("DIA"))
            if pd.isna(r.get("SALA")) or letra is None:
                continue

            edificio = r.get(col_edificio) if col_edificio else None
            texto_sala = formato_sala(r.get("SALA"), edificio)
            if not texto_sala:
                continue

            key = (str(r.get("SEDE")), str(r.get("LIGAS")).strip(), letra)
            if key in mapa and mapa[key] != texto_sala:
                conflictos.add(key)
            mapa[key] = texto_sala  # si hay filas duplicadas que difieren, gana la última

    if conflictos:
        logging.warning(
            "Secciones: %d combinaciones (SEDE, LIGA, día) tienen salones/edificios distintos entre "
            "filas repetidas; se usó el último valor leído. Ejemplos: %s",
            len(conflictos), sorted(conflictos)[:5],
        )
    logging.info(
        "Salones y edificios por día cargados desde Secciones: %d combinaciones (SEDE, LIGA, día) "
        "a partir de %d filas.",
        len(mapa), total_filas,
    )
    return mapa


def _letra_dia(dia_num) -> str | None:
    """1 → 'L', 2 → 'M', … ; None si el valor no es un día válido."""
    if pd.isna(dia_num):
        return None
    try:
        return DIA_NUM_TO_LETRA.get(int(dia_num))
    except (TypeError, ValueError):
        return None
