# -*- coding: utf-8 -*-
"""
Bloques UTC: parseo y "transformación" a su forma visible.

Un bloque como `TOR1A3` se descompone en base `TOR1A` + número `3`. Dentro de
cada sede, los números de una misma base se ordenan y se les asigna una letra
(A, B, C…), que reemplaza el último carácter de la base:

    TOR1A1 → TOR1A (1)      TOR1A3 → TOR1B (3)
"""
import re
import string

import pandas as pd

# Mapa por sede: {sede: {base: {numero: letra}}}
MapaBloques = dict[str, dict[str, dict[int, str]]]

_RE_BASE_NUM = re.compile(r"^(.*?)(\d+)$")


def split_blocks(series: pd.Series) -> list[str]:
    """Todos los bloques distintos de una columna 'B1, B2' (ordenados)."""
    vals = []
    for v in series.dropna().astype(str):
        vals.extend(s.strip() for s in v.split(",") if s.strip())
    return sorted(set(vals))


def block_base_num(bloque) -> tuple[str, int | None]:
    """'TOR1A3' → ('TOR1A', 3);  sin número final → (bloque, None)."""
    m = _RE_BASE_NUM.match(str(bloque))
    if not m:
        return (str(bloque), None)
    return (m.group(1), int(m.group(2)))


def replace_last_char(base: str, letter: str) -> str:
    """Reemplaza el último carácter de `base` por `letter`."""
    if not base:
        return letter
    return base[:-1] + letter


def build_base_to_map_por_sede(df: pd.DataFrame) -> MapaBloques:
    """Asigna una letra a cada número de bloque, por sede y por base."""
    letters = string.ascii_uppercase
    mapa_por_sede: MapaBloques = {}
    for sede, dfx in df.groupby("SEDE"):
        base_to_nums: dict[str, set[int]] = {}
        for b in split_blocks(dfx["UTC_BLOCK"]):
            base, num = block_base_num(b)
            if num is not None:
                base_to_nums.setdefault(base, set()).add(num)
        mapa_por_sede[str(sede)] = {
            base: {n: letters[i] for i, n in enumerate(sorted(nums)) if i < len(letters)}
            for base, nums in base_to_nums.items()
        }
    return mapa_por_sede


def transformar_bloque(bloque: str, base_to_map: dict[str, dict[int, str]]) -> str:
    """'TOR1A3' → 'TOR1B (3)' usando el mapa de la sede."""
    m = _RE_BASE_NUM.match(str(bloque).strip())
    if not m:
        return str(bloque)
    base, num = m.group(1), int(m.group(2))
    letra = base_to_map.get(base, {}).get(num, "")
    base_vis = replace_last_char(base, letra) if letra else base
    return f"{base_vis} ({num})"
