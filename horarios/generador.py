# -*- coding: utf-8 -*-
"""
Orquestador principal: Excel de entrada → carpetas HTML (+ ZIP) por sede.

Estructura de salida dentro de `Horarios_<SEDE>/`:
    profesor/
        1_8/     (materias 1–8 y semestrales 1–16 integradas)
        9_16/    (materias 9–16 y semestrales 1–16 integradas)
    sala/
        1_8/     (ocupaciones 1–8 y semestrales 1–16 integradas)
        9_16/    (ocupaciones 9–16 y semestrales 1–16 integradas)
    grupo/
        1_16/    (bloques de semanas 1–16)
        1_8/     (bloques de semanas 1–8)
        9_16/    (bloques de semanas 9–16)

Además se escriben en `workdir` los Excel auxiliares de mapeo y packages.
"""
import base64
import logging
import os
import pathlib
import shutil
import zipfile

import jinja2
import pandas as pd

from horarios.carga import load_data, load_data_unificado, load_salones_por_liga_dia
from horarios.config import (
    CATEGORIAS_HORARIO,
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

SUBCARPETAS = CATEGORIAS_HORARIO


def carpeta_salida(workdir, sede: str) -> pathlib.Path:
    """Carpeta donde `generar_reportes` deja los HTML de una sede."""
    return pathlib.Path(workdir) / f"Horarios_{slugify(sede)}"


def generar_reportes(
    path_entrada=None,
    template_path=TEMPLATE_FILE,
    logo_path=LOGO_FILE,
    sedes_filtro=None,
    workdir=None,
    loader=None,
    crear_zip=True,
    incluir_vistas=("profesor", "sala", "grupo"),
    modulo_docentes: dict | None = None,
):
    """Genera los horarios HTML organizados en profesor, sala y grupo.

    path_entrada      Excel concreto a leer (si se omite se buscan en `workdir`).
    sedes_filtro      set/list de sedes a procesar (None = todas).
    workdir           carpeta con los Excel de entrada y donde se escribe la salida.
    loader            función alternativa de carga, misma firma que `load_data_unificado`.
    crear_zip         si True, crea `Horarios_<SEDE>.zip` por sede.
    incluir_vistas    tupla con las vistas a generar ('profesor', 'sala', 'grupo').
    modulo_docentes   opcional para compatibilidad.
    """
    wd = workdir or "."
    template_path = _resolver(template_path, wd)
    logo_path = _resolver(logo_path, wd)

    df = _cargar_df(path_entrada, sedes_filtro, wd, loader)
    salones_map = load_salones_por_liga_dia(sedes_filtro=sedes_filtro, workdir=wd)
    template = jinja2.Template(pathlib.Path(template_path).read_text(encoding="utf8"))
    logo_b64 = "data:image/png;base64," + base64.b64encode(pathlib.Path(logo_path).read_bytes()).decode()

    # Normalizar nombres de vistas (compatibilidad con 'grupos', 'docentes', 'salones')
    raw_vistas = set(incluir_vistas)
    vistas_set = set()
    for v in raw_vistas:
        if v in ("grupos", "grupo"):
            vistas_set.add("grupo")
        elif v in ("docentes", "profesor"):
            vistas_set.add("profesor")
        elif v in ("salones", "sala"):
            vistas_set.add("sala")
        else:
            vistas_set.add(v)

    from horarios.pipeline import filtrar_semanas

    for sede in sorted(df["SEDE"].dropna().astype(str).unique()):
        carpeta = carpeta_salida(wd, sede)
        shutil.rmtree(carpeta, ignore_errors=True)
        carpeta.mkdir(parents=True, exist_ok=True)

        df_sede = df[df["SEDE"].astype(str) == sede].copy()

        # 1. PROFESOR
        if "profesor" in vistas_set:
            dir_prof = carpeta / "profesor"
            dir_prof.mkdir(parents=True, exist_ok=True)
            for p in PERIODOS_PROFESOR:
                out_p = dir_prof / p["id"]
                out_p.mkdir(parents=True, exist_ok=True)
                df_p = filtrar_semanas(df_sede, p["filtro"], p["vacias"])
                ctx_p = ContextoSede(
                    sede=sede,
                    df=df_p,
                    salones_map=salones_map,
                    template=template,
                    logo_b64=logo_b64,
                )
                generar_vista_docentes(ctx_p, out_p, modulo_nombre=p.get("subtitulo"))

        # 2. SALA (incluye ocupaciones de 1_16)
        if "sala" in vistas_set:
            dir_sala = carpeta / "sala"
            dir_sala.mkdir(parents=True, exist_ok=True)
            for p in PERIODOS_SALA:
                out_s = dir_sala / p["id"]
                out_s.mkdir(parents=True, exist_ok=True)
                df_s = filtrar_semanas(df_sede, p["filtro"], p["vacias"])
                ctx_s = ContextoSede(
                    sede=sede,
                    df=df_s,
                    salones_map=salones_map,
                    template=template,
                    logo_b64=logo_b64,
                )
                generar_vista_salones(ctx_s, out_s, subtitulo_turno=p.get("subtitulo"))

        # 3. GRUPO
        if "grupo" in vistas_set:
            dir_grupo = carpeta / "grupo"
            dir_grupo.mkdir(parents=True, exist_ok=True)
            for p in PERIODOS_GRUPO:
                out_g = dir_grupo / p["id"]
                out_g.mkdir(parents=True, exist_ok=True)
                df_g = filtrar_semanas(df_sede, p["filtro"], p["vacias"])
                ctx_g = ContextoSede(
                    sede=sede,
                    df=df_g,
                    salones_map=salones_map,
                    template=template,
                    logo_b64=logo_b64,
                )
                generar_vista_bloques(ctx_g, out_g, subtitulo_turno=p.get("subtitulo"))

        if crear_zip:
            _zip_carpeta_sede(pathlib.Path(wd) / f"{carpeta.name}.zip", carpeta)

    generar_reporte_mapeo_bloques(df.copy(), str(pathlib.Path(wd) / "Mapeo_Bloques_Transformados.xlsx"))
    try:
        generar_reporte_packages_expandidos(df.copy(), str(pathlib.Path(wd) / "Reporte_Packages_Expandidos.xlsx"))
    except Exception as e:
        print("Aviso: no se pudo generar Reporte_Packages_Expandidos.xlsx:", e)

    print("[OK] Proceso completado. Horarios organizados en profesor, sala y grupo generados.")


# ═════════════════════════════════════════════════════════════
# Helpers
# ═════════════════════════════════════════════════════════════

def _resolver(path: str, wd: str) -> str:
    """Rutas relativas se interpretan respecto a `wd`."""
    return path if os.path.isabs(path) else os.path.join(wd, path)


def _cargar_df(path_entrada, sedes_filtro, wd, loader) -> pd.DataFrame:
    if path_entrada:
        df = load_data(_resolver(path_entrada, wd))
        if sedes_filtro is not None:
            sedes_f = {str(s) for s in sedes_filtro}
            df = df[df["SEDE"].astype(str).isin(sedes_f)].copy()
    else:
        df = (loader or load_data_unificado)(path_entrada, sedes_filtro=sedes_filtro, workdir=wd)

    df = asegurar_columna_utc_block(df)
    if "UTC_BLOCK" not in df.columns:
        raise KeyError("No se encontró la columna 'UTC_BLOCK' en el Excel.")
    return df


def _zip_carpeta_sede(zip_path: pathlib.Path, carpeta: pathlib.Path) -> None:
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=1) as z:
        for f in carpeta.rglob("*"):
            if f.is_file():
                z.write(f, arcname=str(f.relative_to(carpeta.parent)))
    logging.debug("ZIP creado: %s", zip_path)
