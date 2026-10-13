# -*- coding: utf-8 -*-
"""
Puente entre la UI y el motor `horarios`.

Maneja el directorio temporal de la sesión (donde se guardan los Excel subidos
y la salida) y traduce el progreso del pipeline a widgets de Streamlit.
"""
import os
import pathlib
import shutil
import tempfile

import streamlit as st

from horarios.pipeline import generar_por_grupos_semanas


# ═════════════════════════════════════════════════════════════
# Directorio de trabajo de la sesión
# ═════════════════════════════════════════════════════════════

def _workdir() -> str:
    """Directorio temporal de la sesión (se crea si no existe)."""
    wd = st.session_state.get("workdir", "")
    if not (wd and os.path.exists(wd)):
        wd = tempfile.mkdtemp(prefix="horarios_utc_")
        st.session_state.workdir = wd
    return wd


def borrar_workdir():
    """Elimina el directorio temporal de la sesión, si existe."""
    wd = st.session_state.get("workdir", "")
    if wd and os.path.exists(wd):
        shutil.rmtree(wd, ignore_errors=True)


def prepare_workdir(reporte, secciones=None) -> str:
    """Vacía el workdir y guarda en él los archivos subidos (con su nombre original).

    El motor detecta cada archivo por su nombre, así que no se renombran.
    """
    wd = pathlib.Path(_workdir())
    for item in wd.iterdir():
        shutil.rmtree(item) if item.is_dir() else item.unlink()

    for archivo in (reporte, secciones):
        if archivo:
            (wd / archivo.name).write_bytes(archivo.getbuffer())
    return str(wd)


# ═════════════════════════════════════════════════════════════
# Ejecución con barra de progreso
# ═════════════════════════════════════════════════════════════

def run_generation(wd: str, sedes: set, grupos: list) -> list[str]:
    """Ejecuta el pipeline mostrando progreso. Devuelve las rutas de los ZIP."""
    bar = st.progress(0, text="Iniciando…")
    status = st.empty()
    sedes_txt = ", ".join(sorted(sedes))

    def _on_progress(fraccion: float, mensaje: str):
        bar.progress(fraccion, text=mensaje)
        status.info(f"⏳ **{mensaje}** · Sedes: {sedes_txt}")

    zips = generar_por_grupos_semanas(wd, sedes, grupos, on_progress=_on_progress)

    bar.progress(1.0, text="✅ Completado")
    status.success(f"✅ ¡Generación completada! — {len(zips)} archivo(s) ZIP.")
    return zips
