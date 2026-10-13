# -*- coding: utf-8 -*-
"""
Constantes de dominio del motor de horarios.

Todo lo que es "configurable" (patrones de archivo, sedes, grupos de semanas,
turnos, rutas de recursos) vive aquí para no tener valores mágicos repartidos
por el código.
"""
import os

# ── Rutas de recursos (plantilla HTML y logo) ───────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")

TEMPLATE_FILE = os.path.join(ASSETS_DIR, "template_horario.html")
LOGO_FILE = os.path.join(ASSETS_DIR, "logo_utc.png")

# ── Archivos de entrada ─────────────────────────────────────
# Excel consolidado de respaldo (solo si no hay reportes por sede).
RUTA_ENTRADA = "entrada_unificada.xlsx"
# Reportes individuales por sede.
PATRON_REPORTE_SEDE = "Reporte Horarios y Paquetes - Proceso *.xlsx"
# Reporte con el salón REAL de cada sesión (una fila por LIGA + día). Se usa para
# corregir el salón único por liga que trae "Reporte Horarios y Paquetes".
PATRON_SECCIONES = "Resultados*Secciones*Proceso*.xlsx"

# Palabras que descartan un .xlsx como candidato a "Excel consolidado".
SKIP_XLSX_KEYWORDS = (
    "template", "logo", "mapeo", "reporte_packages", "reporte horarios y paquetes",
    "resultados", "secciones",
)

# Nombres posibles de la columna de sede en los distintos formatos de entrada.
COLUMNAS_SEDE = ("CAMPUS PLANTEL", "codigo_plantel", "SEDE")

# Renombrado de columnas de entrada → esquema interno homogéneo.
COLUMNAS_INTERNAS = {
    # Excel consolidado (inglés)
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
    "edificio": "EDIFICIO",
    "packages": "PAQUETE",
    "utc_block": "UTC_BLOCK",
    "packages_utc_blocks_vacancies": "VACANTES_BLOQUE",
    "NIVEL": "NIVEL",
    # Reporte por sede (español)
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
    "EDIFICIO": "EDIFICIO",
    "EDIFICIO ASIGNADO": "EDIFICIO",
    "SEMANAS": "SEMANAS",
    "PAQUETES DE LA LIGA": "PAQUETE",
    "BLOQUES UTC": "UTC_BLOCK",
    "NIVELES BLOQUES": "NIVEL",
    "VACANTE DE PAQUETES": "VACANTES_BLOQUE",
}

# ── Días de la semana ───────────────────────────────────────
# Letra interna → nombre visible (el orden define las columnas de la grilla).
DIA_LETRA = {
    "L": "Lunes", "M": "Martes", "W": "Miércoles", "J": "Jueves",
    "V": "Viernes", "S": "Sábado", "D": "Domingo",
}
# El reporte de Secciones codifica el día como número (1=Lunes … 7=Domingo).
DIA_NUM_TO_LETRA = {1: "L", 2: "M", 3: "W", 4: "J", 5: "V", 6: "S", 7: "D"}
# Abreviaturas que aparecen en "HORARIOS DE LIGA" (Lu, Ma, Mi, …) → letra interna.
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

# ── Franja horaria de las grillas ───────────────────────────
HORA_INICIO = "07:00"
HORA_FIN = "22:00"
# Rango por turno (JORNADA). Hoy todos van de 07:00 a 22:00.
TURNOS = {
    turno: (HORA_INICIO, HORA_FIN)
    for turno in (
        "SABA", "DOMI", "SABAVESP", "VESPE", "NOCTJ", "INTE", "MATU", "MATUBACH",
        "MATUEXT", "MEDOMI", "MENOCTJ", "MESABA", "MESABAVESP", "NOCT", "VESP",
    )
}

# ── Sedes y grupos de semanas ───────────────────────────────
SEDES_CONOCIDAS = ["ARA", "CUA", "IZT", "PUE", "RPA", "TLA", "TOR", "TPN"]

# Semanas de materias semestrales (se imparten a lo largo de todo el periodo)
SEMANAS_SEMESTRALES = {"(1 - 15)", "(1 - 16)"}

# ── Jerarquía de carpetas y periodos por tipo de horario ─────
# Estructura de salida:
#   profesor/ -> 1_8, 9_16  (1_8 y 9_16 incluyen materias de 1_16)
#   sala/     -> 1_8, 9_16  (1_8 y 9_16 incluyen ocupaciones de 1_16)
#   grupo/    -> 1_16, 1_8, 9_16

# 1) PROFESOR: 1_8 y 9_16 (unen materias modulares con las semestrales)
PERIODOS_PROFESOR = [
    {
        "id": "1_8",
        "nombre": "Semanas 1 – 8",
        "subtitulo": "Módulo 1 (Semanas 1–8)",
        "filtro": {"(1 - 8)"} | SEMANAS_SEMESTRALES,
        "vacias": True,
    },
    {
        "id": "9_16",
        "nombre": "Semanas 9 – 16",
        "subtitulo": "Módulo 2 (Semanas 9–16)",
        "filtro": {"(9 - 15)", "(9 - 16)"} | SEMANAS_SEMESTRALES,
        "vacias": True,
    },
]

# 2) SALA: 1_8 y 9_16 (unen ocupaciones modulares con las ocupaciones de 1_16)
PERIODOS_SALA = [
    {
        "id": "1_8",
        "nombre": "Semanas 1 – 8",
        "subtitulo": "Módulo 1 (Semanas 1–8)",
        "filtro": {"(1 - 8)"} | SEMANAS_SEMESTRALES,
        "vacias": True,
    },
    {
        "id": "9_16",
        "nombre": "Semanas 9 – 16",
        "subtitulo": "Módulo 2 (Semanas 9–16)",
        "filtro": {"(9 - 15)", "(9 - 16)"} | SEMANAS_SEMESTRALES,
        "vacias": True,
    },
]

# 3) GRUPO: 1_16, 1_8, 9_16 (bloques UTC)
PERIODOS_GRUPO = [
    {
        "id": "1_16",
        "nombre": "Semanas 1 – 16",
        "subtitulo": "Semanas 1–16",
        "filtro": {"(1 - 15)", "(1 - 16)"},
        "vacias": True,
    },
    {
        "id": "1_8",
        "nombre": "Semanas 1 – 8",
        "subtitulo": "Semanas 1–8",
        "filtro": {"(1 - 8)"},
        "vacias": False,
    },
    {
        "id": "9_16",
        "nombre": "Semanas 9 – 16",
        "subtitulo": "Semanas 9–16",
        "filtro": {"(9 - 15)", "(9 - 16)"},
        "vacias": False,
    },
]

# Opciones para el selector de semanas de la interfaz web (Paso 3)
GRUPOS_SEMANAS = [
    {"id": "1_16", "nombre": "Semanas 1 – 16"},
    {"id": "1_8", "nombre": "Semanas 1 – 8"},
    {"id": "9_16", "nombre": "Semanas 9 – 16"},
]

# Categorías principales de salida
CATEGORIAS_HORARIO = ("profesor", "sala", "grupo")

# Alias de compatibilidad hacia atrás
MODULOS_DOCENTES = PERIODOS_PROFESOR



