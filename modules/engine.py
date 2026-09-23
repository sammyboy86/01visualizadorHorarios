# -*- coding: utf-8 -*-
"""
Motor de generación de reportes y utilidades de procesamiento de archivos.
"""
import os
import pathlib
import re
import shutil
import tempfile
import zipfile

import pandas as pd
import streamlit as st

import generar_reportes as gen
from modules.config import LOGO_FILE, TEMPLATE_FILE


def detect_sedes(uploaded) -> list[str]:
    """Detecta los códigos de sede presentes en el Excel subido (≤1 000 filas)."""
    try:
        df = pd.read_excel(uploaded, engine="openpyxl", nrows=1000)
        uploaded.seek(0)
        for c in df.columns:
            if str(c).strip() in ("CAMPUS PLANTEL", "codigo_plantel", "SEDE"):
                return sorted(df[c].dropna().astype(str).unique().tolist())
    except Exception:
        pass
    return []


def prepare_workdir(reporte, secciones=None) -> str:
    """Crea/limpia un directorio de trabajo temporal con los archivos subidos."""
    if "workdir" not in st.session_state or not os.path.exists(
        st.session_state.get("workdir", "")
    ):
        st.session_state.workdir = tempfile.mkdtemp(prefix="horarios_utc_")

    wd = st.session_state.workdir

    # Limpiar ejecuciones previas
    for item in pathlib.Path(wd).iterdir():
        shutil.rmtree(item) if item.is_dir() else item.unlink()

    # Guardar archivos subidos manteniendo sus nombres originales
    (pathlib.Path(wd) / reporte.name).write_bytes(reporte.getbuffer())
    if secciones:
        (pathlib.Path(wd) / secciones.name).write_bytes(secciones.getbuffer())

    # Copiar plantilla HTML y logo
    shutil.copy2(TEMPLATE_FILE, wd)
    shutil.copy2(LOGO_FILE, wd)
    return wd


def run_generation(wd: str, sedes: set, grupos: list, bar, status) -> list[str]:
    """Ejecuta el filtrado y la generación de horarios. Devuelve rutas absolutas a los ZIPs."""
    total = len(grupos) + 1  # +1 para el empaquetado final
    wdp = pathlib.Path(wd)

    # ── Iteración por grupo de semanas ──
    for i, g in enumerate(grupos):
        bar.progress(i / total, text=f"Generando {g['nombre']}…")
        status.info(
            f"⏳ **{g['nombre']}** · Sedes: {', '.join(sorted(sedes))}"
        )

        def _make_loader(sem, vac, sed):
            def _load(path_entrada=None, sedes_filtro=None, workdir=None):
                df = gen.load_data_unificado(path_entrada, sedes_filtro=sed, workdir=workdir)
                if "SEMANAS" in df.columns:
                    mask = df["SEMANAS"].astype(str).str.strip().isin(sem)
                    if vac:
                        mask = mask | df["SEMANAS"].isna()
                    df = df[mask].copy()
                return df
            return _load

        loader = _make_loader(g["filtro"], g["vacias"], sedes)
        gen.generar_reportes(sedes_filtro=sedes, workdir=wd, loader=loader, crear_zip=False)

        # Renombrar carpetas de salida → sufijo de grupo
        for sede in sedes:
            slug = re.sub(r'[\\/*?"<>| ]', "_", sede)
            src = wdp / f"salida_{slug}"
            dst = wdp / f"horarios_{slug}_{g['id']}"
            if dst.exists():
                shutil.rmtree(dst)
            if src.exists():
                src.rename(dst)

    # ── Empaquetado por sede ──
    bar.progress((total - 1) / total, text="Empaquetando…")
    status.info("📦 Empaquetando archivos…")

    zips: list[str] = []
    for sede in sedes:
        slug = re.sub(r'[\\/*?"<>| ]', "_", sede)
        parent = wdp / f"Horarios_{slug}"
        if parent.exists():
            shutil.rmtree(parent)
        parent.mkdir()

        for g in grupos:
            src = wdp / f"horarios_{slug}_{g['id']}"
            if src.exists():
                src.rename(parent / src.name)

        zpath = wdp / f"Horarios_{slug}.zip"
        if zpath.exists():
            zpath.unlink()
        with zipfile.ZipFile(zpath, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=1) as zf:
            for f in parent.rglob("*"):
                zf.write(f, f.relative_to(parent.parent))
        zips.append(str(zpath.resolve()))

    bar.progress(1.0, text="✅ Completado")
    return zips
