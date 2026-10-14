# -*- coding: utf-8 -*-
"""
Vistas HTML de una sede: una grilla semanal por cada…

* BLOQUE UTC  → carpeta `grupos/`
* DOCENTE     → carpeta `docentes/`
* SALÓN       → carpeta `salones/`

Cada vista sigue el mismo patrón:
  1. agrupar las filas de la sede según la vista,
  2. acumular, por (día, inicio, fin), los datos a mostrar en la celda,
  3. armar la grilla con `construir_grilla` y renderizar la plantilla.
"""
import pathlib
from collections import defaultdict
from dataclasses import dataclass

import jinja2
import pandas as pd

from horarios.bloques import split_blocks
from horarios.carga import SalonesMap
from horarios.config import DIA_LETRA, HORA_FIN, HORA_INICIO, TURNOS
from horarios.grilla import construir_grilla, docente_fmt, parse_group_schedule, unir
from horarios.utils import formato_sala, slugify, valor_predominante


@dataclass
class ContextoSede:
    """Todo lo que necesitan las vistas para generar los HTML de una sede."""
    sede: str
    df: pd.DataFrame
    salones_map: SalonesMap
    template: jinja2.Template
    logo_b64: str

    @property
    def slug(self) -> str:
        return slugify(self.sede)

    def resolver_salon(self, row: pd.Series, dia: str) -> str | None:
        """Salón real de la sesión (reporte Secciones) o, si falta, el salón único de la liga."""
        liga = str(row.get("LIGA")).strip()
        sala = self.salones_map.get((str(self.sede), liga, dia))
        if sala is None and pd.notna(row.get("SALA")):
            sala = formato_sala(row.get("SALA"), row.get("EDIFICIO"))
        return sala

    def render(
        self,
        turno,
        titulo: str,
        grid: list[dict],
        etiqueta: str = "GRUPO",
        subtitulo_turno: str | None = None,
    ) -> str:
        titulo_encabezado = f"TURNO: {turno} - {self.sede}"
        if subtitulo_turno:
            titulo_encabezado = f"{titulo_encabezado} · {subtitulo_turno}"
        html = self.template.render(
            logo=self.logo_b64,
            titulo_turno=titulo_encabezado,
            grupo=titulo,
            dias=list(DIA_LETRA.values()),
            filas=grid,
        )
        if etiqueta != "GRUPO":
            html = html.replace("GRUPO:", f"{etiqueta}:")
            html = html.replace("<title>Horario Grupo", f"<title>Horario {etiqueta.capitalize()}")
        return html



# ═════════════════════════════════════════════════════════════
# Helpers de acumulación
# ═════════════════════════════════════════════════════════════

def _nuevo_contenido(*campos: str) -> defaultdict:
    return defaultdict(lambda: {c: set() for c in campos})


def _texto(row: pd.Series, col: str) -> str | None:
    """Valor de la columna como str, o None si está vacío."""
    v = row.get(col)
    return str(v) if pd.notna(v) else None


def _agregar(contenido: defaultdict, clave, campo: str, valor) -> None:
    """Agrega `valor` a la celda solo si existe (no crea celdas vacías)."""
    if valor is not None:
        contenido[clave][campo].add(valor)


def _bloques_de_fila(row: pd.Series) -> list[str]:
    return [tok.strip() for tok in str(row.get("UTC_BLOCK", "")).split(",") if str(tok).strip()]


def _hora_fin(fines: list[str]) -> str:
    """La grilla llega al menos hasta HORA_FIN, o más si alguna sesión termina después."""
    return max(max(fines), HORA_FIN) if fines else HORA_FIN


# ═════════════════════════════════════════════════════════════
# Vista por BLOQUE UTC
# ═════════════════════════════════════════════════════════════

def _celda_bloque(info: dict) -> str:
    return (
        f"<b>{unir(info['asig'])}</b><br>"
        f"{unir(info['alias'])}<br>"
        f"{docente_fmt(list(info['docentes']))}<br>"
        f"{unir(info['sala'])}"
    )


def generar_vista_bloques(
    ctx: ContextoSede,
    out_dir: pathlib.Path,
    subtitulo_turno: str | None = None,
) -> None:
    df = ctx.df
    for bloque in split_blocks(df["UTC_BLOCK"]):
        mask = df["UTC_BLOCK"].astype(str).apply(
            lambda s: any(tok.strip() == bloque for tok in str(s).split(","))
        )
        dfg = df[mask]

        turno = valor_predominante(dfg["JORNADA"], "GEN")
        h_ini, h_fin = TURNOS.get(str(turno), (HORA_INICIO, HORA_FIN))

        contenido = _nuevo_contenido("docentes", "sala", "asig", "alias")
        for _, r in dfg.iterrows():
            for d, start, end in parse_group_schedule(r["GROUP_SCHEDULE"]):
                clave = (DIA_LETRA.get(d, d), start, end)
                _agregar(contenido, clave, "docentes", _texto(r, "DOCENTE_NOMBRE"))
                _agregar(contenido, clave, "sala", ctx.resolver_salon(r, d) or None)
                _agregar(contenido, clave, "asig", _texto(r, "ASIGNATURA"))
                _agregar(contenido, clave, "alias", _texto(r, "NOMBRE"))

        grid = construir_grilla(contenido, h_ini, h_fin, _celda_bloque)
        # Se usa el identificador original del bloque para evitar colisiones entre variantes.
        html = ctx.render(turno, bloque, grid, subtitulo_turno=subtitulo_turno)
        (out_dir / f"{ctx.slug}_{slugify(bloque)}.html").write_text(html, "utf8")



# ═════════════════════════════════════════════════════════════
# Vista por DOCENTE
# ═════════════════════════════════════════════════════════════

def _celda_docente(info: dict) -> str:
    bloques = unir(info["bloques"]) if info["bloques"] else "(sin bloque)"
    return (
        f"<b>{bloques}</b><br>"
        f"{unir(info['asig'])}<br>"
        f"{unir(info['alias'])}<br>"
        f"{unir(info['sala'])}"
    )


def generar_vista_docentes(
    ctx: ContextoSede,
    out_dir: pathlib.Path,
    modulo_nombre: str | None = None,
    sufijo_archivo: str | None = None,
) -> None:
    # Se agrupa por ID DOCENTE (único) y no por nombre, para no mezclar
    # docentes distintos que compartan el mismo nombre.
    for doc_id, dfd in ctx.df.groupby("DOCENTE_ID"):
        if pd.isna(doc_id):
            continue

        nombres = dfd["DOCENTE_NOMBRE"].dropna()
        doc_nombre = nombres.mode().iat[0] if not nombres.empty else str(doc_id)

        fines = [e for gs in dfd["GROUP_SCHEDULE"].dropna().astype(str) for (_, _, e) in parse_group_schedule(gs)]
        h_ini, h_fin = HORA_INICIO, _hora_fin(fines)

        contenido = _nuevo_contenido("bloques", "asig", "alias", "sala")
        for _, r in dfd.iterrows():
            bloques = _bloques_de_fila(r)
            for d, start, end in parse_group_schedule(r["GROUP_SCHEDULE"]):
                clave = (DIA_LETRA.get(d, d), start, end)
                for b in bloques:
                    _agregar(contenido, clave, "bloques", b)
                _agregar(contenido, clave, "asig", _texto(r, "ASIGNATURA"))
                _agregar(contenido, clave, "alias", _texto(r, "NOMBRE"))
                _agregar(contenido, clave, "sala", ctx.resolver_salon(r, d) or None)

        grid = construir_grilla(contenido, h_ini, h_fin, _celda_docente)
        turno = valor_predominante(dfd["JORNADA"], "MIXTO")
        html = ctx.render(
            turno,
            str(doc_nombre),
            grid,
            etiqueta="DOCENTE",
            subtitulo_turno=modulo_nombre,
        )
        # Nombre de archivo basado en ID, nombre y sufijo de módulo si aplica
        partes = [str(doc_nombre),str(doc_id)]
        if sufijo_archivo:
            partes.append(str(sufijo_archivo))
        nombre_archivo = slugify("_".join(partes))
        (out_dir / f"{nombre_archivo}_{ctx.slug}.html").write_text(html, "utf8")



# ═════════════════════════════════════════════════════════════
# Vista por SALÓN
# ═════════════════════════════════════════════════════════════

def _celda_salon(info: dict) -> str:
    bloques = unir(info["bloques"]) if info["bloques"] else "(sin bloque)"
    return (
        f"<b>{bloques}</b><br>"
        f"{unir(info['asig'])}<br>"
        f"{unir(info['alias'])}<br>"
        f"{docente_fmt(list(info['docentes']))}"
    )


def generar_vista_salones(
    ctx: ContextoSede,
    out_dir: pathlib.Path,
    subtitulo_turno: str | None = None,
) -> None:
    # {salón: [(letra_día, inicio, fin, fila), …]}
    sesiones_por_salon = defaultdict(list)
    for _, r in ctx.df.iterrows():
        for d, start, end in parse_group_schedule(r["GROUP_SCHEDULE"]):
            salon = ctx.resolver_salon(r, d)
            if salon:
                sesiones_por_salon[salon].append((d, start, end, r))

    for salon, sesiones in sorted(sesiones_por_salon.items()):
        h_ini, h_fin = HORA_INICIO, _hora_fin([end for (_, _, end, _) in sesiones])

        contenido = _nuevo_contenido("bloques", "asig", "alias", "docentes")
        for d, start, end, r in sesiones:
            clave = (DIA_LETRA.get(d, d), start, end)
            for b in _bloques_de_fila(r):
                _agregar(contenido, clave, "bloques", b)
            _agregar(contenido, clave, "asig", _texto(r, "ASIGNATURA"))
            _agregar(contenido, clave, "alias", _texto(r, "NOMBRE"))
            _agregar(contenido, clave, "docentes", _texto(r, "DOCENTE_NOMBRE"))

        grid = construir_grilla(contenido, h_ini, h_fin, _celda_salon)
        turno = valor_predominante(ctx.df["JORNADA"], "MIXTO")
        html = ctx.render(
            turno,
            str(salon),
            grid,
            etiqueta="SALÓN",
            subtitulo_turno=subtitulo_turno,
        )
        (out_dir / f"{ctx.slug}_{slugify(salon)}.html").write_text(html, "utf8")

