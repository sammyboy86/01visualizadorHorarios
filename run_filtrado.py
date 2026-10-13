# -*- coding: utf-8 -*-
"""
CLI: genera horarios por sede y por grupo de semanas, y un ZIP por sede.

    python run_filtrado.py

Edite `SEDES_FILTRO` (y, si hace falta, `GRUPOS_SEMANAS` en `horarios/config.py`).
Solo se cargan los reportes "Proceso *.xlsx" de las sedes en SEDES_FILTRO.
Resultado: `Horarios_<SEDE>/` y `Horarios_<SEDE>.zip` en la carpeta del script.
"""
import os

from horarios.config import GRUPOS_SEMANAS
from horarios.pipeline import generar_por_grupos_semanas

SEDES_FILTRO = {"TOR"}
# SEDES_FILTRO = {"CUA", "IZT", "RPA", "PUE", "ARA", "TLA", "TPN"}

WORKDIR = os.path.dirname(os.path.abspath(__file__))


def _imprimir_progreso(fraccion: float, mensaje: str) -> None:
    print(f"\n{'=' * 60}\n  [{fraccion:4.0%}] {mensaje}  |  Sedes: {sorted(SEDES_FILTRO)}\n{'=' * 60}")


def main() -> None:
    zips = generar_por_grupos_semanas(WORKDIR, SEDES_FILTRO, GRUPOS_SEMANAS, on_progress=_imprimir_progreso)
    for z in zips:
        print(f"  {os.path.basename(z)} generado ({os.path.getsize(z) // 1024} KB)")
    print("\nProceso completo.")


if __name__ == "__main__":
    main()
