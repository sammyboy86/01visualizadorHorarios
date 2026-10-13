# -*- coding: utf-8 -*-
"""
CLI: genera los horarios HTML de todas las sedes de la carpeta actual.

    python generar_reportes.py

Lee los Excel de entrada del directorio de trabajo y genera `Horarios_<SEDE>/`
(con profesor, sala y grupo) y `Horarios_<SEDE>.zip`. Para filtrar por sedes use
`run_filtrado.py`.

La lógica vive en el paquete `horarios/`; este archivo solo se mantiene como
punto de entrada (y por compatibilidad con `import generar_reportes`).
"""
from horarios.carga import (  # noqa: F401  (re-exportados por compatibilidad)
    find_input_excel,
    find_secciones_excels,
    find_sede_report_excels,
    load_data,
    load_data_unificado,
    load_salones_por_liga_dia,
)
from horarios.generador import generar_reportes

if __name__ == "__main__":
    generar_reportes()
