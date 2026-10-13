# -*- coding: utf-8 -*-
"""
Motor de generación de horarios UTC (sin dependencias de Streamlit).

Módulos, en el orden en que fluyen los datos:

    config          constantes: patrones de archivo, días, turnos, sedes, semanas
    carga           lectura de los Excel de entrada → DataFrame normalizado
    bloques         parseo de bloques UTC y su letra visible
    grilla          grilla semanal de 30 min y parseo de "HORARIOS DE LIGA"
    vistas          HTML por bloque / docente / salón
    reportes_excel  Excel auxiliares (mapeo de bloques, packages expandidos)
    generador       `generar_reportes()`: orquesta todo lo anterior por sede
    pipeline        `generar_por_grupos_semanas()`: repite el generador por
                    grupo de semanas y empaqueta un ZIP por sede
"""
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

from horarios.generador import generar_reportes  # noqa: E402
from horarios.pipeline import generar_por_grupos_semanas  # noqa: E402

__all__ = ["generar_reportes", "generar_por_grupos_semanas"]
