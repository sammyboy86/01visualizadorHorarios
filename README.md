
# Generador de Reportes UTC — Por sede (reportes Proceso NNN)

Variante de `reporte_horarios/` que lee **reportes individuales por plantel** en lugar
de un Excel consolidado.

## Diferencia con `reporte_horarios/`

| | `reporte_horarios/` | `reporte_horarios_por_sede/` |
|---|---|---|
| Entrada | Un Excel consolidado | `Reporte Horarios y Paquetes - Proceso *.xlsx` |
| Filtro de sedes | Sobre el consolidado | Solo carga archivos de las sedes pedidas |
| Horarios | `L(07:00-08:00)` | También `Lu(07:00-08:00)`, `Mi(07:00-09:00)`, etc. |

## Qué hace
- Lee reportes por sede (`Reporte Horarios y Paquetes - Proceso NNN.xlsx`) y los
  concatena. Si no hay reportes por sede, usa un Excel consolidado como respaldo.
- Con `run_filtrado.py`, solo carga y genera visualizadores de las sedes en
  `SEDES_FILTRO`.
- Genera **HTML por BLOQUE** y **HTML por DOCENTE**, empaquetados en ZIP por sede.

## Entrada

### Reportes por sede (preferido)
Archivos con patrón `Reporte Horarios y Paquetes - Proceso *.xlsx`, columnas:
```
CAMPUS PLANTEL, MODALIDAD, JORNADA, CARRERA, CURRICULO, ASIGNATURA, NOMBRE ASIGNATURA,
GRUPO, LIGA, HORARIOS DE LIGA, ID DOCENTE, NOMBRE DOCENTE, SALA ASIGNADA, SEMANAS,
PAQUETES DE LA LIGA, BLOQUES UTC, NIVELES BLOQUES, VACANTE DE PAQUETES
```

### Excel consolidado (fallback)
```
codigo_plantel, codigo_modalidad, codigo_jornada, codigo_programa, codigo_curriculo,
course_code, course_name, group_label, link_code, group_schedule,
instructor_code, instructor_name, sala, packages, utc_block, packages_utc_blocks_vacancies
```

## Ejecución

1. Deja en esta carpeta:
   - `generar_reportes.py`, `template_horario.html`, `logo_utc.png`
   - Reportes por sede (`Reporte Horarios y Paquetes - Proceso *.xlsx`)

2. Instala dependencias:
```
pip install pandas openpyxl jinja2
```

3. Ejecuta:
```
python generar_reportes.py
```

O con filtro de sedes y semanas:
```
python run_filtrado.py
```
(Edita `SEDES_FILTRO` y `GRUPOS_SEMANAS` en `run_filtrado.py`.)

4. Revisa:
- Carpeta `salida_<SEDE>/grupos` y `salida_<SEDE>/docentes`
- ZIP `UTC_Reportes_SEDE_<SEDE>.zip` o `Horarios_<SEDE>.zip` (con `run_filtrado`)
