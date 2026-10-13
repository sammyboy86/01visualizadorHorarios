# -*- coding: utf-8 -*-
"""
Pipeline principal de generación y ordenamiento de horarios por sede y periodo.

Organización de directorios dentro de `Horarios_<SEDE>/`:

    Horarios_<SEDE>/
    ├── profesor/
    │   ├── 1_8/     (materias de semanas 1–8 unidas con las de 1–16)
    │   └── 9_16/    (materias de semanas 9–16 unidas con las de 1–16)
    ├── sala/
    │   ├── 1_8/     (ocupaciones de sala de semanas 1–8 y ocupaciones de 1–16)
    │   └── 9_16/    (ocupaciones de sala de semanas 9–16 y ocupaciones de 1–16)
    └── grupo/
        ├── 1_16/    (bloques UTC de semanas 1–16)
        ├── 1_8/     (bloques UTC de semanas 1–8)
        └── 9_16/    (bloques UTC de semanas 9–16)

Cada sede se empaqueta en `Horarios_<SEDE>.zip`.
"""
import base64
import logging
import os
import pathlib
import shutil
import zipfile
from typing import Callable, Iterable

import jinja2
import pandas as pd

from horarios.carga import load_data_unificado, load_salones_por_liga_dia
from horarios.config import (
    LOGO_FILE,
    PERIODOS_GRUPO,
    PERIODOS_PROFESOR,
    PERIODOS_SALA,
    TEMPLATE_FILE,
)
from horarios.reportes_excel import (
    generar_reporte_mapeo_bloques,
    generar_reporte_packages_expandidos,
)
from horarios.utils import asegurar_columna_utc_block, slugify
from horarios.vistas import (
    ContextoSede,
    generar_vista_bloques,
    generar_vista_docentes,
    generar_vista_salones,
)

ProgresoFn = Callable[[float, str], None]


def carpeta_sede(workdir, sede: str) -> pathlib.Path:
    """Carpeta raíz de una sede con la jerarquía profesor, sala y grupo."""
    return pathlib.Path(workdir) / f"Horarios_{slugify(sede)}"


def filtrar_semanas(
    df: pd.DataFrame,
    semanas: set[str] | Iterable[str],
    incluir_vacias: bool,
) -> pd.DataFrame:
    """Filtra el DataFrame dejando filas en `semanas` y opcionalmente vacías/NaN."""
    if "SEMANAS" not in df.columns:
        return df
    semanas_norm = {str(s).strip() for s in semanas}
    val_norm = df["SEMANAS"].astype(str).str.strip()
    mask = val_norm.isin(semanas_norm)
    if incluir_vacias:
        mask = mask | df["SEMANAS"].isna() | val_norm.isin(["", "nan", "None", "<NA>"])
    return df[mask].copy()


def generar_por_grupos_semanas(
    workdir,
    sedes: Iterable[str] | None = None,
    grupos: list[dict] | None = None,
    on_progress: ProgresoFn | None = None,
) -> list[str]:
    """Genera la estructura de horarios completa (profesor, sala, grupo) y empaqueta un ZIP por sede.

    Retorna la lista de rutas absolutas de los archivos ZIP generados.
    """
    wd = pathlib.Path(workdir or ".")
    progreso = on_progress or (lambda _f, _m: None)
    sedes_filtro = {str(s).strip().upper() for s in sedes} if sedes else None

    # 1. Cargar datos consolidados y mapa de salones reales
    progreso(0.02, "Cargando datos y reportes de secciones…")
    df_total = load_data_unificado(sedes_filtro=sedes_filtro, workdir=str(wd))
    df_total = asegurar_columna_utc_block(df_total)
    salones_map = load_salones_por_liga_dia(sedes_filtro=sedes_filtro, workdir=str(wd))

    # Cargar plantilla y logo
    template_path = wd / TEMPLATE_FILE if not os.path.isabs(TEMPLATE_FILE) else pathlib.Path(TEMPLATE_FILE)
    if not template_path.exists():
        template_path = pathlib.Path(TEMPLATE_FILE)
    template = jinja2.Template(template_path.read_text(encoding="utf8"))

    logo_path = wd / LOGO_FILE if not os.path.isabs(LOGO_FILE) else pathlib.Path(LOGO_FILE)
    if not logo_path.exists():
        logo_path = pathlib.Path(LOGO_FILE)
    logo_b64 = "data:image/png;base64," + base64.b64encode(logo_path.read_bytes()).decode()

    # 2. Determinar periodos activos según selección
    active_ids = {g["id"] for g in grupos} if grupos else {"1_16", "1_8", "9_16"}

    # Grupo maneja 1_16, 1_8 y 9_16
    periodos_grupo = [p for p in PERIODOS_GRUPO if p["id"] in active_ids]

    # Profesor y Sala manejan 1_8 y 9_16 (ambos incluyen semanas 1–16)
    if {"1_8", "9_16"} & active_ids:
        periodos_profesor = [p for p in PERIODOS_PROFESOR if p["id"] in active_ids]
        periodos_sala = [p for p in PERIODOS_SALA if p["id"] in active_ids]
    else:
        periodos_profesor = list(PERIODOS_PROFESOR)
        periodos_sala = list(PERIODOS_SALA)

    # Sedes a procesar
    sedes_encontradas = sorted(df_total["SEDE"].dropna().astype(str).unique())
    if sedes_filtro:
        sedes_lista = [s for s in sedes_encontradas if s in sedes_filtro]
    else:
        sedes_lista = sedes_encontradas

    if not sedes_lista:
        logging.warning("No se encontraron sedes para procesar.")
        return []

    # Cálculo de pasos para la barra de progreso
    tareas_por_sede = len(periodos_profesor) + len(periodos_sala) + len(periodos_grupo) + 1
    total_pasos = (len(sedes_lista) * tareas_por_sede) + 1
    paso = 0
    zips = []

    # 3. Generación por cada sede
    for sede in sedes_lista:
        df_sede = df_total[df_total["SEDE"].astype(str) == sede].copy()
        parent = carpeta_sede(wd, sede)

        if parent.exists():
            shutil.rmtree(parent, ignore_errors=True)
        parent.mkdir(parents=True, exist_ok=True)

        dir_prof = parent / "profesor"
        dir_sala = parent / "sala"
        dir_grupo = parent / "grupo"

        # ── 3.A PROFESOR (1_8, 9_16 - ambos con 1_16 integrado) ────
        for p in periodos_profesor:
            progreso(paso / total_pasos, f"{sede} · Profesor ({p['nombre']})…")
            paso += 1
            out_dir = dir_prof / p["id"]
            out_dir.mkdir(parents=True, exist_ok=True)
            df_p = filtrar_semanas(df_sede, p["filtro"], p["vacias"])
            ctx_p = ContextoSede(
                sede=sede,
                df=df_p,
                salones_map=salones_map,
                template=template,
                logo_b64=logo_b64,
            )
            generar_vista_docentes(ctx_p, out_dir, modulo_nombre=p.get("subtitulo"))

        # ── 3.B SALA (1_8, 9_16 - con ocupaciones de 1_16 integradas) ──
        for p in periodos_sala:
            progreso(paso / total_pasos, f"{sede} · Sala ({p['nombre']})…")
            paso += 1
            out_dir = dir_sala / p["id"]
            out_dir.mkdir(parents=True, exist_ok=True)
            df_s = filtrar_semanas(df_sede, p["filtro"], p["vacias"])
            ctx_s = ContextoSede(
                sede=sede,
                df=df_s,
                salones_map=salones_map,
                template=template,
                logo_b64=logo_b64,
            )
            generar_vista_salones(ctx_s, out_dir, subtitulo_turno=p.get("subtitulo"))

        # ── 3.C GRUPO (1_16, 1_8, 9_16) ───────────────────────────
        for p in periodos_grupo:
            progreso(paso / total_pasos, f"{sede} · Grupo ({p['nombre']})…")
            paso += 1
            out_dir = dir_grupo / p["id"]
            out_dir.mkdir(parents=True, exist_ok=True)
            df_g = filtrar_semanas(df_sede, p["filtro"], p["vacias"])
            ctx_g = ContextoSede(
                sede=sede,
                df=df_g,
                salones_map=salones_map,
                template=template,
                logo_b64=logo_b64,
            )
            generar_vista_bloques(ctx_g, out_dir, subtitulo_turno=p.get("subtitulo"))

        # ── 3.D EMPAQUETADO ZIP POR SEDE ───────────────────────────
        progreso(paso / total_pasos, f"{sede} · Comprimiendo ZIP…")
        paso += 1
        zpath = wd / f"{parent.name}.zip"
        if zpath.exists():
            zpath.unlink()
        with zipfile.ZipFile(zpath, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=1) as zf:
            for f in parent.rglob("*"):
                if f.is_file():
                    zf.write(f, f.relative_to(parent.parent))
        zips.append(str(zpath.resolve()))

    # 4. Reportes auxiliares en Excel
    progreso((total_pasos - 1) / total_pasos, "Generando reportes auxiliares en Excel…")
    try:
        generar_reporte_mapeo_bloques(df_total.copy(), str(wd / "Mapeo_Bloques_Transformados.xlsx"))
    except Exception as exc:
        logging.warning("No se pudo generar Mapeo_Bloques_Transformados.xlsx: %s", exc)

    try:
        generar_reporte_packages_expandidos(df_total.copy(), str(wd / "Reporte_Packages_Expandidos.xlsx"))
    except Exception as exc:
        logging.warning("No se pudo generar Reporte_Packages_Expandidos.xlsx: %s", exc)

    progreso(1.0, "Completado")
    return zips
