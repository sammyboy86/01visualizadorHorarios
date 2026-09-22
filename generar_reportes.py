# -*- coding: utf-8 -*-
import os
import base64
import pathlib
import zipfile
import shutil
import logging
import re
import datetime as dt
from collections import defaultdict

import pandas as pd
import jinja2

# ---------- Config ----------
RUTA_ENTRADA = "entrada_unificada.xlsx"   # fallback si no hay reportes por sede
PATRON_REPORTE_SEDE = "Reporte Horarios y Paquetes - Proceso *.xlsx"
# AJUSTE: reporte con el salón REAL de cada sesión (una fila por LIGA + día). Se usa para
# corregir el salón único por liga que trae "Reporte Horarios y Paquetes".
PATRON_SECCIONES    = "Resultados*Secciones*Proceso*.xlsx"
TEMPLATE     = "template_horario.html"
LOGO_PATH    = "logo_utc.png"

DIA_LETRA = { "L":"Lunes", "M":"Martes", "W":"Miércoles", "J":"Jueves", "V":"Viernes", "S":"Sábado", "D":"Domingo" }
# AJUSTE: el reporte de Secciones codifica el día como número (1=Lunes ... 7=Domingo)
DIA_NUM_TO_LETRA = {1: "L", 2: "M", 3: "W", 4: "J", 5: "V", 6: "S", 7: "D"}
# Abreviaturas en reportes por sede (Lu, Ma, Mi, …)
DIA_PREFIX = {
    "L": "L", "M": "M", "W": "W", "J": "J", "V": "V", "S": "S", "D": "D", "F": "D",
    "LU": "L", "LUN": "L", "LUNES": "L",
    "MA": "M", "MAR": "M", "MARTES": "M",
    "MI": "W", "MIE": "W", "MIÉ": "W", "MIERCOLES": "W", "MIÉRCOLES": "W",
    "JU": "J", "JUE": "J", "JUEVES": "J",
    "VI": "V", "VIE": "V", "VIERNES": "V",
    "SA": "S", "SAB": "S", "SÁB": "S", "SABADO": "S", "SÁBADO": "S",
    "DO": "D", "DOM": "D", "DOMINGO": "D",
}

# AJUSTE: Todos los turnos configurados para iniciar a las 07:00
TURNOS = {
    "SABA":      ("07:00", "22:00"),
    "DOMI":      ("07:00", "22:00"),
    "SABAVESP":  ("07:00", "22:00"),
    "VESPE":     ("07:00", "22:00"),
    "NOCTJ":     ("07:00", "22:00"),
    "INTE":      ("07:00", "22:00"),
    "MATU":      ("07:00", "22:00"),
    "MATUBACH":  ("07:00", "22:00"),
    "MATUEXT":   ("07:00", "22:00"),
    "MEDOMI":    ("07:00", "22:00"),
    "MENOCTJ":   ("07:00", "22:00"),
    "MESABA":    ("07:00", "22:00"),
    "MESABAVESP":("07:00", "22:00"),
    "NOCT":      ("07:00", "22:00"),
    "VESP":      ("07:00", "22:00")
}

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# ---------- Utilidades base ----------
_SKIP_XLSX_KEYWORDS = (
    "template", "logo", "mapeo", "reporte_packages", "reporte horarios y paquetes",
    # AJUSTE: excluir el reporte de Secciones de la detección de "Excel consolidado"
    "resultados", "secciones",
)

def _is_skipped_xlsx(name: str) -> bool:
    low = name.lower()
    return any(k in low for k in _SKIP_XLSX_KEYWORDS)

def find_sede_report_excels() -> list:
    """Reportes individuales por sede: 'Reporte Horarios y Paquetes - Proceso NNN.xlsx'."""
    import glob
    files = []
    for f in glob.glob(PATRON_REPORTE_SEDE):
        if f.startswith("~$"):
            continue
        files.append(f)
    files.sort()
    return files

def find_secciones_excels() -> list:
    """Reporte(s) 'Resultados - Secciones - Proceso NNN.xlsx': trae, fila por fila,
    el salón real de cada sesión (LIGA + día), a diferencia del salón único por liga
    que trae 'Reporte Horarios y Paquetes'."""
    import glob
    files = [f for f in glob.glob(PATRON_SECCIONES) if not os.path.basename(f).startswith("~$")]
    files.sort()
    return files

# AJUSTE: mapa (SEDE, LIGA, día) -> salón real, construido a partir del reporte de Secciones.
# Es el complemento que le falta a "Reporte Horarios y Paquetes" para poder mostrar un
# salón distinto por día cuando la liga efectivamente cambia de salón entre sesiones.
def load_salones_por_liga_dia(sedes_filtro=None) -> dict:
    archivos = find_secciones_excels()
    if not archivos:
        logging.warning(
            "No se encontró el reporte de Secciones (patrón: %s). Se usará el salón único "
            "de la liga para todos sus días (comportamiento anterior, puede ser incorrecto "
            "si la liga cambia de salón entre sesiones).",
            PATRON_SECCIONES,
        )
        return {}

    sedes_f = {str(s) for s in sedes_filtro} if sedes_filtro else None
    mapa = {}
    conflictos = set()
    total_filas = 0

    for f in archivos:
        df = pd.read_excel(f, engine="openpyxl")
        faltantes = {"SEDE", "LIGAS", "DIA", "SALA"} - set(df.columns)
        if faltantes:
            logging.warning("Secciones %s: faltan columnas %s; se omite este archivo.", f, faltantes)
            continue
        if sedes_f:
            df = df[df["SEDE"].astype(str).isin(sedes_f)]
        for _, r in df.iterrows():
            total_filas += 1
            sala = r.get("SALA")
            if pd.isna(sala):
                continue
            dia_num = r.get("DIA")
            if pd.isna(dia_num):
                continue
            try:
                letra = DIA_NUM_TO_LETRA.get(int(dia_num))
            except (TypeError, ValueError):
                letra = None
            if letra is None:
                continue
            key = (str(r.get("SEDE")), str(r.get("LIGAS")).strip(), letra)
            sala = str(sala).strip()
            if key in mapa and mapa[key] != sala:
                conflictos.add(key)
            mapa[key] = sala  # si hay filas duplicadas (p.ej. una por semana) y difieren, gana la última

    if conflictos:
        logging.warning(
            "Secciones: %d combinaciones (SEDE, LIGA, día) tienen salones distintos entre "
            "filas repetidas; se usó el último valor leído. Ejemplos: %s",
            len(conflictos), sorted(conflictos)[:5],
        )
    logging.info(
        "Salones por día cargados desde Secciones: %d combinaciones (SEDE, LIGA, día) "
        "a partir de %d filas.",
        len(mapa), total_filas,
    )
    return mapa

def find_input_excel(prefer: str = None) -> str:
    import glob
    if prefer and os.path.exists(prefer):
        return prefer
    candidates = []
    for f in glob.glob("*.xlsx"):
        if f.startswith("~$") or _is_skipped_xlsx(f):
            continue
        candidates.append(f)
    if not candidates:
        raise FileNotFoundError("No se encontró ningún .xlsx de entrada en la carpeta actual.")
    if len(candidates) == 1:
        return candidates[0]
    candidates.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    return candidates[0]

def load_data(path: str) -> pd.DataFrame:
    # Renombrar columnas a un esquema interno homogéneo (consolidado o reporte por sede)
    df = pd.read_excel(path, engine="openpyxl")
    ren = {
        "codigo_plantel": "SEDE",
        "codigo_modalidad": "MODALIDAD",
        "codigo_jornada": "JORNADA",
        "codigo_programa": "PROGRAMA",
        "codigo_curriculo": "CURRICULO",
        "course_code": "ASIGNATURA",
        "course_name": "NOMBRE",
        "group_label": "GROUP_LABEL",
        "link_code": "LIGA",
        "group_schedule": "GROUP_SCHEDULE",
        "instructor_code": "DOCENTE_ID",
        "instructor_name": "DOCENTE_NOMBRE",
        "sala": "SALA",
        "packages": "PAQUETE",
        "utc_block": "UTC_BLOCK",
        "packages_utc_blocks_vacancies": "VACANTES_BLOQUE",
        "NIVEL": "NIVEL",
        # Reporte por sede (columnas en español)
        "CAMPUS PLANTEL": "SEDE",
        "MODALIDAD": "MODALIDAD",
        "JORNADA": "JORNADA",
        "CARRERA": "PROGRAMA",
        "CURRICULO": "CURRICULO",
        "ASIGNATURA": "ASIGNATURA",
        "NOMBRE ASIGNATURA": "NOMBRE",
        "GRUPO": "GROUP_LABEL",
        "LIGA": "LIGA",
        "HORARIOS DE LIGA": "GROUP_SCHEDULE",
        "ID DOCENTE": "DOCENTE_ID",
        "NOMBRE DOCENTE": "DOCENTE_NOMBRE",
        "SALA ASIGNADA": "SALA",
        "SEMANAS": "SEMANAS",
        "PAQUETES DE LA LIGA": "PAQUETE",
        "BLOQUES UTC": "UTC_BLOCK",
        "NIVELES BLOQUES": "NIVEL",
        "VACANTE DE PAQUETES": "VACANTES_BLOQUE",
    }
    df = df.rename(columns=ren)
    return df

def _sedes_en_archivo(path: str) -> set:
    """Lee solo la columna de sede para decidir si el archivo entra al filtro."""
    header = pd.read_excel(path, engine="openpyxl", nrows=0)
    sede_col = None
    for c in header.columns:
        if str(c).strip() in ("CAMPUS PLANTEL", "codigo_plantel", "SEDE"):
            sede_col = c
            break
    if sede_col is None:
        return set()
    series = pd.read_excel(path, usecols=[sede_col], engine="openpyxl")[sede_col]
    return set(series.dropna().astype(str).unique())

def load_data_unificado(path_entrada=None, sedes_filtro=None) -> pd.DataFrame:
    """Carga reportes por sede y los concatena; si no hay, usa un Excel consolidado.

    sedes_filtro: set/list de códigos de plantel; solo carga archivos de esas sedes.
    """
    if sedes_filtro is not None:
        sedes_filtro = {str(s) for s in sedes_filtro}

    sede_files = find_sede_report_excels()
    if sede_files:
        dfs = []
        for f in sede_files:
            sedes_archivo = _sedes_en_archivo(f)
            if not sedes_archivo:
                logging.warning("Archivo sin sede identificable, se omite: %s", f)
                continue
            if sedes_filtro and not sedes_archivo.intersection(sedes_filtro):
                logging.info(
                    "Omitido %s: sede(s) %s fuera del filtro",
                    f, ", ".join(sorted(sedes_archivo)),
                )
                continue
            df = load_data(f)
            if df.empty:
                logging.warning("Archivo vacío, se omite: %s", f)
                continue
            if sedes_filtro:
                df = df[df["SEDE"].astype(str).isin(sedes_filtro)].copy()
                if df.empty:
                    continue
            sedes = sorted(df["SEDE"].dropna().astype(str).unique())
            logging.info("Cargado %s: %d filas, sede(s): %s", f, len(df), ", ".join(sedes))
            dfs.append(df)
        if not dfs:
            if sedes_filtro:
                raise ValueError(
                    "No se encontraron reportes por sede para: "
                    + ", ".join(sorted(sedes_filtro))
                )
            raise ValueError("Todos los reportes por sede están vacíos.")
        return pd.concat(dfs, ignore_index=True)

    path = path_entrada or find_input_excel(RUTA_ENTRADA)
    logging.info("Sin reportes por sede; usando consolidado: %s", path)
    df = load_data(path)
    if sedes_filtro:
        df = df[df["SEDE"].astype(str).isin(sedes_filtro)].copy()
        if df.empty:
            raise ValueError(
                "El consolidado no tiene filas para las sedes: "
                + ", ".join(sorted(sedes_filtro))
            )
    return df

def bloques_30(h_ini, h_fin):
    t0, t1 = [dt.datetime.strptime(t, "%H:%M") for t in (h_ini, h_fin)]
    while t0 < t1:
        nxt = t0 + dt.timedelta(minutes=30)
        yield f"{t0:%H:%M} - {nxt:%H:%M}"
        t0 = nxt

def make_grid(h_ini, h_fin):
    dias = list(DIA_LETRA.values())
    return [{"hora": blk, "celdas":[{"dia":d,"contenido":"","rowspan":1,"skip":False} for d in dias]} for blk in bloques_30(h_ini, h_fin)]

def place(grid, blks, idx, span, dia, txt):
    for off in range(span):
        cell = next(c for c in grid[idx+off]["celdas"] if c["dia"]==dia)
        if off==0:
            cell.update({"contenido":txt,"rowspan":span})
        else:
            cell["skip"]=True

def cleanup(grid):
    for row in grid:
        row["celdas"]=[c for c in row["celdas"] if not c.get("skip")]

def docente_fmt(nombres):
    if not nombres:
        return "<b>SIN DOCENTE ASIGNADO</b>"
    seen, out = set(), []
    for n in nombres:
        if pd.isna(n):
            continue
        if n not in seen:
            seen.add(n); out.append(n)
    return " / ".join(out) if out else "<b>SIN DOCENTE ASIGNADO</b>"

def parse_group_schedule(gs: str):
    out = []
    if pd.isna(gs):
        return out
    for token in str(gs).split():
        m = re.match(r"^([A-Za-zÁÉÍÓÚáéíóúÑñ]+)\((\d{2}:\d{2})-(\d{2}:\d{2})\)$", token)
        if m:
            d_raw, start, end = m.group(1), m.group(2), m.group(3)
            d = DIA_PREFIX.get(d_raw.upper(), d_raw.upper()[:1])
            d = "D" if d in ("D", "F") else d
            out.append((d, start, end))
    return out

def span_30m(start, end):
    t0 = dt.datetime.strptime(start,"%H:%M")
    t1 = dt.datetime.strptime(end,"%H:%M")
    return max(1, int((t1 - t0).seconds/1800))

def replace_last_char(base: str, letter: str) -> str:
    if not base:
        return letter
    return base[:-1] + letter

def split_blocks(series):
    vals = []
    for v in series.dropna().astype(str):
        vals.extend([s.strip() for s in v.split(",") if s.strip()])
    return sorted(set(vals))

def block_base_num(b):
    m = re.match(r"^(.*?)(\d+)$", str(b))
    if not m:
        return (str(b), None)
    return (m.group(1), int(m.group(2)))

# ---------- Mapeo base→{número: letra} por SEDE ----------
def build_base_to_map_por_sede(df: pd.DataFrame):
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    mapa_por_sede = {}
    for sede, dfx in df.groupby("SEDE"):
        base_to_nums = {}
        for b in split_blocks(dfx["UTC_BLOCK"]):
            base, num = block_base_num(b)
            if num is None:
                continue
            base_to_nums.setdefault(base, set()).add(num)
        base_to_map = {base: {n: letters[i] for i, n in enumerate(sorted(nums)) if i < len(letters)}
                       for base, nums in base_to_nums.items()}
        mapa_por_sede[str(sede)] = base_to_map
    return mapa_por_sede

# AJUSTE: Reporte de mapeo para cruces de datos
def generar_reporte_mapeo_bloques(df: pd.DataFrame, out_path: str):
    mapa_por_sede = build_base_to_map_por_sede(df)
    rows = []
    for sede, base_map in mapa_por_sede.items():
        for base, num_to_letra in base_map.items():
            for num, letra in num_to_letra.items():
                original = f"{base}{num}"
                transformado = replace_last_char(base, letra) + f" ({num})"
                rows.append({
                    "SEDE": sede,
                    "BLOQUE_ORIGINAL": original,
                    "BLOQUE_TRANSFORMADO": transformado
                })
    if rows:
        pd.DataFrame(rows).drop_duplicates().to_excel(out_path, index=False)
        return out_path
    return None

# ---------- Reporte Packages 1:1 ----------
def _split_list(cell):
    if pd.isna(cell):
        return []
    return [str(x).strip() for x in str(cell).split(",") if str(x).strip()]

def _transformar_bloque_con_mapa(blk: str, base_to_map: dict) -> str:
    m = re.match(r"^(.*?)(\d+)$", str(blk).strip())
    if not m:
        return str(blk)
    base, num = m.group(1), int(m.group(2))
    letra = base_to_map.get(base, {}).get(num, "")
    base_vis = replace_last_char(base, letra) if letra else base
    return f"{base_vis} ({num})"

def generar_reporte_packages_expandidos(df_base: pd.DataFrame, out_path: str):
    if "UTC_BLOCK" not in df_base.columns:
        for c in list(df_base.columns):
            if str(c).strip().lower() == "utc_block":
                df_base = df_base.rename(columns={c: "UTC_BLOCK"})
                break

    col_sede = "SEDE" if "SEDE" in df_base.columns else "codigo_plantel"
    col_pkg  = "PAQUETE" if "PAQUETE" in df_base.columns else "packages"
    col_blk  = "UTC_BLOCK" if "UTC_BLOCK" in df_base.columns else "utc_block"

    mapa_por_sede = build_base_to_map_por_sede(df_base)

    rows = []
    for _, row in df_base.iterrows():
        pkgs = _split_list(row.get(col_pkg))
        blks = _split_list(row.get(col_blk))
        n = min(len(pkgs), len(blks))
        if n == 0:
            continue
        sede_val = str(row.get(col_sede))
        base_to_map = mapa_por_sede.get(sede_val, {})
        for pkg, blk in zip(pkgs[:n], blks[:n]):
            rows.append({
                "codigo_plantel": row.get(col_sede),
                "packages": pkg,
                "utc_block_by_package": blk,
                "utc_block_transformado": _transformar_bloque_con_mapa(blk, base_to_map)
            })

    if not rows:
        logging.info("Aviso: no se encontraron filas con packages/utc_block para expandir.")
        return None

    rep = pd.DataFrame(rows)[[
        "codigo_plantel","packages","utc_block_by_package","utc_block_transformado"
    ]]

    for col in ["codigo_plantel","packages","utc_block_by_package","utc_block_transformado"]:
        rep[col] = rep[col].astype(str).str.strip()
    rep = rep.drop_duplicates()

    rep.to_excel(out_path, index=False)
    return out_path

# ---------- Generador principal ----------
def generar_reportes(path_entrada=None, template_path=TEMPLATE, logo_path=LOGO_PATH, sedes_filtro=None):
    if path_entrada:
        df = load_data(path_entrada)
        if sedes_filtro is not None:
            sedes_f = {str(s) for s in sedes_filtro}
            df = df[df["SEDE"].astype(str).isin(sedes_f)].copy()
    else:
        df = load_data_unificado(sedes_filtro=sedes_filtro)

    if "UTC_BLOCK" not in df.columns:
        for c in list(df.columns):
            if str(c).strip().lower() == "utc_block":
                df = df.rename(columns={c: "UTC_BLOCK"})
                break
    if "UTC_BLOCK" not in df.columns:
        raise KeyError("No se encontró la columna 'UTC_BLOCK' en el Excel.")

    # AJUSTE: salón real por (SEDE, LIGA, día), tomado del reporte de Secciones.
    # Complementa a "Reporte Horarios y Paquetes", que solo trae un salón por liga.
    salones_map = load_salones_por_liga_dia(sedes_filtro=sedes_filtro)

    template = jinja2.Template(open(template_path, encoding="utf8").read())
    logo_b64 = "data:image/png;base64," + base64.b64encode(open(logo_path,"rb").read()).decode()

    sedes = sorted(df["SEDE"].dropna().astype(str).unique())
    mapa_por_sede = build_base_to_map_por_sede(df)

    for sede_actual in sedes:
        sede_slug = re.sub(r"[\/*?\"<>| ]", "_", sede_actual)
        carpeta = pathlib.Path(f"salida_{sede_slug}")
        out_g = carpeta / "grupos"; out_d = carpeta / "docentes"
        shutil.rmtree(carpeta, ignore_errors=True)
        out_g.mkdir(parents=True); out_d.mkdir()

        df_sede = df[df["SEDE"].astype(str) == str(sede_actual)].copy()
        base_to_map = mapa_por_sede.get(str(sede_actual), {})

        # ===================== POR BLOQUE (UTC_BLOCK) =========================
        all_blocks = split_blocks(df_sede["UTC_BLOCK"])

        for block in all_blocks:
            base, num = block_base_num(block)
            mask = df_sede["UTC_BLOCK"].astype(str).apply(lambda s: any(tok.strip()==block for tok in str(s).split(",")))
            dfg = df_sede[mask].copy()

            turno = dfg["JORNADA"].mode().iat[0] if not dfg["JORNADA"].isna().all() else "GEN"
            # AJUSTE: Franja horaria desde las 07:00
            h_ini, h_fin = TURNOS.get(str(turno), ("07:00","22:00"))
            grid = make_grid(h_ini, h_fin); blks = list(bloques_30(h_ini, h_fin))

            header_nombre = block  # usar identificador original: evita colisiones entre variantes (A, V, etc.)

            bloques_map = defaultdict(lambda: {"docentes": set(), "sala": set(), "asig": set(), "alias": set()})
            for _, r in dfg.iterrows():
                liga_r = str(r.get("LIGA")).strip()
                for (d, start, end) in parse_group_schedule(r["GROUP_SCHEDULE"]):
                    key = (DIA_LETRA.get(d, d), start, end)
                    if pd.notna(r.get("DOCENTE_NOMBRE")): bloques_map[key]["docentes"].add(str(r.get("DOCENTE_NOMBRE")))
                    # AJUSTE: salón correcto = el de Secciones para (sede, liga, día); si esa
                    # combinación no aparece ahí, se usa el salón único de la liga como respaldo.
                    sala_dia = salones_map.get((str(sede_actual), liga_r, d))
                    if sala_dia is None and pd.notna(r.get("SALA")):
                        sala_dia = str(r.get("SALA"))
                    if sala_dia:
                        bloques_map[key]["sala"].add(sala_dia)
                    if pd.notna(r.get("ASIGNATURA")):      bloques_map[key]["asig"].add(str(r.get("ASIGNATURA")))
                    if pd.notna(r.get("NOMBRE")):          bloques_map[key]["alias"].add(str(r.get("NOMBRE")))

            for (dia, start, end), info in bloques_map.items():
                try:
                    i = next(k for k,b in enumerate(blks) if b.startswith(start))
                except StopIteration:
                    continue
                span = span_30m(start, end)
                txt = (f"<b>{', '.join(sorted(info['asig']))}</b><br>"
                       f"{', '.join(sorted(info['alias']))}<br>"
                       f"{docente_fmt(list(info['docentes']))}<br>"
                       f"{', '.join(sorted(info['sala']))}")
                place(grid, blks, i, span, dia, txt)

            cleanup(grid)
            safe_block = re.sub(r"[\/*?\"<>| ]","_", block)  # usar bloque original para evitar colisiones de nombre
            fname = f"{sede_slug}_{safe_block}.html"
            html  = template.render(logo=logo_b64, titulo_turno=f"TURNO: {turno} - {sede_actual}",
                                    grupo=header_nombre, dias=list(DIA_LETRA.values()), filas=grid)
            (out_g / fname).write_text(html, "utf8")

        # ===================== POR DOCENTE (BLOQUES visibles) =================
        # AJUSTE: se agrupa por ID DOCENTE (único) y no por NOMBRE DOCENTE para evitar
        # colisiones entre docentes distintos que compartan el mismo nombre.
        for doc_id, dfd in df_sede.groupby("DOCENTE_ID"):
            if pd.isna(doc_id):
                continue

            # Nombre visible: el más frecuente dentro del grupo (respaldo: el propio ID)
            nombres_validos = dfd["DOCENTE_NOMBRE"].dropna()
            doc_nombre = nombres_validos.mode().iat[0] if not nombres_validos.empty else str(doc_id)

            # AJUSTE: Franja horaria desde las 07:00
            h_ini = "07:00"
            _maxs = [e for _gs in dfd["GROUP_SCHEDULE"].dropna().astype(str) for (_d, _s, e) in parse_group_schedule(_gs)]
            h_fin = max(max(_maxs), "22:00") if _maxs else "22:00"

            grid = make_grid(h_ini, h_fin); blks = list(bloques_30(h_ini, h_fin))

            content_map = defaultdict(lambda: {"bloques": set(), "asig": set(), "alias": set(), "sala": set()})
            for _, r in dfd.iterrows():
                liga_r = str(r.get("LIGA")).strip()
                utc_blocks = [tok.strip() for tok in str(r.get("UTC_BLOCK","")).split(",") if str(tok).strip()]
                bloques_visibles = [tok for tok in utc_blocks]
                for (d, start, end) in parse_group_schedule(r["GROUP_SCHEDULE"]):
                    key = (DIA_LETRA.get(d, d), start, end)
                    for vis in bloques_visibles:
                        content_map[key]["bloques"].add(vis)
                    if pd.notna(r.get("ASIGNATURA")): content_map[key]["asig"].add(str(r.get("ASIGNATURA")))
                    if pd.notna(r.get("NOMBRE")):     content_map[key]["alias"].add(str(r.get("NOMBRE")))
                    # AJUSTE: mismo criterio que en la sección "por bloque" (grupos): salón real
                    # por (sede, liga, día), con respaldo al salón único de la liga si falta el dato.
                    sala_dia = salones_map.get((str(sede_actual), liga_r, d))
                    if sala_dia is None and pd.notna(r.get("SALA")):
                        sala_dia = str(r.get("SALA"))
                    if sala_dia:
                        content_map[key]["sala"].add(sala_dia)

            for (dia, start, end), info in content_map.items():
                try:
                    i = next(k for k,b in enumerate(blks) if b.startswith(start))
                except StopIteration:
                    continue
                span = span_30m(start, end)
                bloques_fmt = ", ".join(sorted(info["bloques"])) if info["bloques"] else "(sin bloque)"
                txt = (
                    f"<b>{bloques_fmt}</b><br>"
                    f"{', '.join(sorted(info['asig']))}<br>"
                    f"{', '.join(sorted(info['alias']))}<br>"
                    f"{', '.join(sorted(info['sala']))}"
                )
                place(grid, blks, i, span, dia, txt)

            cleanup(grid)
            # Nombre de archivo basado en ID DOCENTE para evitar colisiones
            safe = re.sub(r"[\/*?\"<>| ]","_", str(doc_id))
            # AJUSTE: Mantiene el encabezado original con el nombre del docente
            turno_doc = dfd["JORNADA"].mode().iat[0] if not dfd["JORNADA"].isna().all() else "MIXTO"
            html = template.render(logo=logo_b64, titulo_turno=f"TURNO: {turno_doc} - {sede_actual}",
                                   grupo=str(doc_nombre), dias=list(DIA_LETRA.values()), filas=grid).replace("GRUPO:","DOCENTE:")
            (out_d / f"{safe}_{sede_slug}.html").write_text(html, "utf8")

        # Empaquetar sede
        zip_name = f"UTC_Reportes_SEDE_{sede_slug}.zip"
        with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as z:
            for f in out_g.glob("*.html"): z.write(f, arcname=f"grupos/{f.name}")
            for f in out_d.glob("*.html"): z.write(f, arcname=f"docentes/{f.name}")

    # AJUSTE: Generación de reportes finales (Mapeo y Packages)
    generar_reporte_mapeo_bloques(df.copy(), "Mapeo_Bloques_Transformados.xlsx")
    try:
        generar_reporte_packages_expandidos(df.copy(), "Reporte_Packages_Expandidos.xlsx")
    except Exception as e:
        print("Aviso: no se pudo generar Reporte_Packages_Expandidos.xlsx:", e)

    print("[OK] Proceso completado. Horarios desde las 07:00 y archivos Excel generados.")

if __name__ == "__main__":
    generar_reportes()
