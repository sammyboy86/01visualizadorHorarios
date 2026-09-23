# -*- coding: utf-8 -*-
"""
Runner: genera horarios por sede y por grupo de semanas.
Solo carga los reportes Proceso *.xlsx de las sedes en SEDES_FILTRO.
"""
import os, glob, shutil, pathlib, pandas as pd
import generar_reportes as gen


SEDES_FILTRO = {"TOR"}
# SEDES_FILTRO = {"CUA", "IZT", "RPA", "PUE", "ARA", "TLA", "TPN"}

# (sufijo_carpeta, set_de_semanas, incluir_vacias)
GRUPOS_SEMANAS = [
    ("sem_1_16",  {"(1 - 15)", "(1 - 16)"},  True),
    ("sem_1_8",   {"(1 - 8)"},               False),
    ("sem_9_16",  {"(9 - 15)", "(9 - 16)"},  False),
]

# --- Directorio base del script ---
_script_dir = os.path.dirname(os.path.abspath(__file__))

# --- Ejecutar un grupo de semanas ---
def ejecutar_grupo(sufijo, semanas_filtro, incluir_vacias):
    print(f"\n{'='*60}")
    print(f"  Grupo: {sufijo}  |  Sedes: {sorted(SEDES_FILTRO)}  |  Semanas: {semanas_filtro}")
    print(f"{'='*60}")

    def _filtrar_semanas(df):
        print(f"  Filas cargadas: {len(df)}")
        if "SEMANAS" in df.columns:
            mask = df["SEMANAS"].astype(str).str.strip().isin(semanas_filtro)
            if incluir_vacias:
                mask = mask | df["SEMANAS"].isna()
            df = df[mask].copy()
            print(f"  Filas por semanas: {len(df)}")
        return df

    def _load_unificado_filtrada(path_entrada=None, sedes_filtro=None, workdir=None):
        df = gen.load_data_unificado(path_entrada, sedes_filtro=SEDES_FILTRO, workdir=workdir)
        return _filtrar_semanas(df)

    gen.generar_reportes(sedes_filtro=SEDES_FILTRO, workdir=_script_dir, loader=_load_unificado_filtrada)

    # Renombrar carpetas y ZIPs generados
    for sede in SEDES_FILTRO:
        import re
        sede_slug = re.sub(r'[\/*?"<>| ]', "_", sede)

        src_dir = pathlib.Path(_script_dir) / f"salida_{sede_slug}"
        dst_dir = pathlib.Path(_script_dir) / f"horarios_{sede_slug}_{sufijo}"
        if dst_dir.exists():
            shutil.rmtree(dst_dir)
        if src_dir.exists():
            src_dir.rename(dst_dir)

        src_zip = pathlib.Path(_script_dir) / f"UTC_Reportes_SEDE_{sede_slug}.zip"
        if src_zip.exists():
            src_zip.unlink()

    print(f"  Carpetas renombradas con sufijo _{sufijo}")

# --- Loop principal ---
for sufijo, semanas, vacias in GRUPOS_SEMANAS:
    ejecutar_grupo(sufijo, semanas, vacias)


# --- Agrupar carpetas de semanas por sede y comprimir ---
import re, zipfile
print("\nAgrupando carpetas por sede...")
_sdp = pathlib.Path(_script_dir)
for sede in SEDES_FILTRO:
    sede_slug = re.sub(r'[\/*?"<>| ]', "_", sede)
    parent = _sdp / f"Horarios_{sede_slug}"
    if parent.exists():
        shutil.rmtree(parent)
    parent.mkdir()

    for sufijo, _, _ in GRUPOS_SEMANAS:
        src = _sdp / f"horarios_{sede_slug}_{sufijo}"
        if src.exists():
            src.rename(parent / src.name)

    # Comprimir la carpeta padre
    zip_path = _sdp / f"Horarios_{sede_slug}.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in parent.rglob("*"):
            zf.write(file, file.relative_to(parent.parent))
    print(f"  {zip_path.name} generado ({zip_path.stat().st_size // 1024} KB)")

print("\nProceso completo.")
