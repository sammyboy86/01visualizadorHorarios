# -*- coding: utf-8 -*-
"""
Reportes Excel auxiliares que acompañan a los horarios HTML:

* Mapeo_Bloques_Transformados.xlsx → bloque original ↔ bloque visible, por sede.
* Reporte_Packages_Expandidos.xlsx → una fila por (paquete, bloque), 1:1.
"""
import logging

import pandas as pd

from horarios.bloques import build_base_to_map_por_sede, replace_last_char, transformar_bloque
from horarios.utils import asegurar_columna_utc_block, split_lista


def generar_reporte_mapeo_bloques(df: pd.DataFrame, out_path: str) -> str | None:
    """Escribe la tabla SEDE / BLOQUE_ORIGINAL / BLOQUE_TRANSFORMADO."""
    rows = []
    for sede, base_map in build_base_to_map_por_sede(df).items():
        for base, num_to_letra in base_map.items():
            for num, letra in num_to_letra.items():
                rows.append({
                    "SEDE": sede,
                    "BLOQUE_ORIGINAL": f"{base}{num}",
                    "BLOQUE_TRANSFORMADO": replace_last_char(base, letra) + f" ({num})",
                })
    if not rows:
        return None
    pd.DataFrame(rows).drop_duplicates().to_excel(out_path, index=False)
    return out_path


def generar_reporte_packages_expandidos(df_base: pd.DataFrame, out_path: str) -> str | None:
    """Expande 'P1, P2' × 'B1, B2' en filas (P1, B1), (P2, B2)."""
    df_base = asegurar_columna_utc_block(df_base)

    col_sede = "SEDE" if "SEDE" in df_base.columns else "codigo_plantel"
    col_pkg = "PAQUETE" if "PAQUETE" in df_base.columns else "packages"
    col_blk = "UTC_BLOCK" if "UTC_BLOCK" in df_base.columns else "utc_block"

    mapa_por_sede = build_base_to_map_por_sede(df_base)

    rows = []
    for _, row in df_base.iterrows():
        pkgs = split_lista(row.get(col_pkg))
        blks = split_lista(row.get(col_blk))
        base_to_map = mapa_por_sede.get(str(row.get(col_sede)), {})
        for pkg, blk in zip(pkgs, blks):  # zip corta en la lista más corta
            rows.append({
                "codigo_plantel": row.get(col_sede),
                "packages": pkg,
                "utc_block_by_package": blk,
                "utc_block_transformado": transformar_bloque(blk, base_to_map),
            })

    if not rows:
        logging.info("Aviso: no se encontraron filas con packages/utc_block para expandir.")
        return None

    rep = pd.DataFrame(rows)
    for col in rep.columns:
        rep[col] = rep[col].astype(str).str.strip()
    rep.drop_duplicates().to_excel(out_path, index=False)
    return out_path
