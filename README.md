# Visualizador y Generador de Horarios UTC 📅

Aplicación web y motor de procesamiento por lotes para la generación, consulta y descarga de horarios académicos de la Universidad Tres Culturas (UTC). Transforma reportes institucionales en hojas de horario interactivas en formato HTML (por bloque, docente y salón), acompañadas de cruces en Excel y empaquetadas en archivos ZIP por sede y grupo de semanas.

---

## 📑 Tabla de Contenidos

1. [Arquitectura del Proyecto](#-arquitectura-del-proyecto)
2. [Estructura de Archivos](#-estructura-de-archivos)
3. [Formatos de Entrada](#-formatos-de-entrada)
4. [Salidas Generadas](#-salidas-generadas)
5. [Instalación y Requisitos](#-instalación-y-requisitos)
6. [Modos de Ejecución](#-modos-de-ejecución)
   - [1. Aplicación Web Interactiva (Streamlit)](#1-aplicación-web-interactiva-streamlit)
   - [2. CLI Rápido (Todas las sedes)](#2-cli-rápido-todas-las-sedes)
   - [3. CLI con Filtro por Sede y Semanas](#3-cli-con-filtro-por-sede-y-semanas)
7. [Módulos y Responsabilidades](#-módulos-y-responsabilidades)
8. [Autenticación](#-autenticación)

---

## 🏛 Arquitectura del Proyecto

El proyecto está diseñado bajo una arquitectura desacoplada en tres capas principales:

```
┌────────────────────────────────────────────────────────┐
│                   INTERFAZ DE USUARIO                  │
│   app.py  ──>  ui/ (Streamlit, Pasos 1 a 6, Descargas) │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│                     MOTOR DE DOMINIO                   │
│   horarios/ (Carga, Bloques UTC, Grillas, Vistas HTML, │
│              Reportes Excel, Pipeline de semanas)      │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│                        RECURSOS                        │
│   assets/ (styles.css, template_horario.html, logos)   │
└────────────────────────────────────────────────────────┘
```

- **Motor Central (`horarios/`)**: Biblioteca pura de Python (sin dependencias de Streamlit) que encapsula la lógica de parseo, normalización de sedes, cálculo de bloques UTC, resolución de salones por día, armado de cuadrículas de tiempo y compresión.
- **Capa de Presentación (`ui/` + `app.py`)**: Interfaz web reactiva y moderna construida con Streamlit. Guía al usuario en un flujo paso a paso, gestiona la sesión temporal y ofrece previsualizaciones HTML embebidas.
- **Entradas CLI (`generar_reportes.py`, `run_filtrado.py`)**: Scripts directos de terminal pensados para automatización o ejecución rápida sin levantar un servidor web.

---

## 📂 Estructura de Archivos

```text
01visualizadorHorarios/
├── app.py                      # Punto de entrada de la aplicación web Streamlit
├── generar_reportes.py         # Punto de entrada CLI estándar
├── run_filtrado.py             # Punto de entrada CLI con filtros personalizados
├── requirements.txt            # Dependencias del proyecto
├── README.md                   # Esta documentación
│
├── assets/                     # Recursos visuales y plantillas
│   ├── downloading.gif         # Animación para confirmación de descargas
│   ├── logo_utc.png            # Logotipo oficial UTC para reportes y cabecera
│   ├── styles.css              # Hoja de estilos CSS de la aplicación web
│   └── template_horario.html   # Plantilla Jinja2 para la grilla semanal HTML
│
├── horarios/                   # Paquete con la lógica de negocio y procesamiento
│   ├── __init__.py             # API pública del motor de horarios
│   ├── config.py               # Constantes: turnos, días, grupos de semanas, sedes
│   ├── carga.py                # Lectura y unificación de archivos Excel (.xlsx)
│   ├── bloques.py              # Parseo de códigos UTC y asignación de letras
│   ├── grilla.py               # Cuadrícula de tiempo (30 min) y parseo de horarios
│   ├── vistas.py               # Generación de HTML por Bloque, Docente y Salón
│   ├── reportes_excel.py       # Cruces auxiliares (Mapeo y Packages expandidos)
│   ├── generador.py            # Orquestador general por sede (`generar_reportes`)
│   ├── pipeline.py             # Pipeline por semanas y compresión en ZIPs
│   └── utils.py                # Utilidades de texto, slugify y limpieza
│
└── ui/                         # Componentes de la interfaz de usuario (Streamlit)
    ├── __init__.py             # Módulo de UI
    ├── config.py               # Configuración de página y credenciales de acceso
    ├── auth.py                 # Inicio de sesión, control de acceso y logout
    ├── styles.py               # Inyección de estilos y helpers visuales
    ├── generacion.py           # Adaptador de progreso y gestión del workdir
    ├── descarga.py             # Modal interactivo y confirmación de descargas
    └── pasos.py                # Flujo visual guiado (Pasos 1 al 6)
```

---

## 📥 Formatos de Entrada

El motor acepta los siguientes archivos de entrada en formato Excel (`.xlsx`):

### 1. Reportes por Sede (Formato principal recomendado)
Archivos con patrón `Reporte Horarios y Paquetes - Proceso *.xlsx`.
Contienen la programación de asignaturas de cada plantel:
* **Columnas esperadas**: `CAMPUS PLANTEL`, `MODALIDAD`, `JORNADA`, `CARRERA`, `CURRICULO`, `ASIGNATURA`, `NOMBRE ASIGNATURA`, `GRUPO`, `LIGA`, `HORARIOS DE LIGA`, `ID DOCENTE`, `NOMBRE DOCENTE`, `SALA ASIGNADA`, `SEMANAS`, `PAQUETES DE LA LIGA`, `BLOQUES UTC`, `NIVELES BLOQUES`, `VACANTE DE PAQUETES`.

### 2. Reporte de Secciones (Salones reales por día y edificio)
Archivos con patrón `Resultados*Secciones*Proceso*.xlsx` (o archivos que contengan la palabra `secciones` en el nombre):
* **Columnas esperadas**: `SEDE`, `LIGAS`, `DIA`, `SALA`, `EDIFICIO` (opcional).
* **Propósito**: Corrige el salón único que reporta el archivo principal. Si una liga imparte clases en diferentes salones según el día de la semana, este archivo permite plasmar el aula y edificio exactos de cada sesión.

### 3. Excel Consolidado (Alternativa de respaldo)
Si no existen reportes individuales por sede, el sistema busca un archivo único consolidado (por defecto `entrada_unificada.xlsx` o cualquier `.xlsx` válido presente):
* **Columnas**: `codigo_plantel`, `codigo_modalidad`, `codigo_jornada`, `codigo_programa`, `codigo_curriculo`, `course_code`, `course_name`, `group_label`, `link_code`, `group_schedule`, `instructor_code`, `instructor_name`, `sala`, `packages`, `utc_block`, etc.

---

## 📤 Salidas Generadas

Por cada sede procesada se genera un archivo ZIP `Horarios_<SEDE>.zip` (o carpetas locales si se ejecuta vía CLI) con la siguiente organización:

```text
Horarios_<SEDE>/
├── profesor/
│   ├── 1_8/                       # Módulo 1: une materias de semanas 1–8 con las de 1–16
│   │                              # (<ID>_<NOMBRE>_<SEDE>.html)
│   └── 9_16/                      # Módulo 2: une materias de semanas 9–16 con las de 1–16
│                                  # (<ID>_<NOMBRE>_<SEDE>.html)
├── sala/
│   ├── 1_8/                       # Semanas 1 a 8 (ocupaciones 1–8 + ocupaciones de 1–16)
│   │                              # (<SEDE>_<SALON>.html)
│   └── 9_16/                      # Semanas 9 a 16 (ocupaciones 9–16 + ocupaciones de 1–16)
│                                  # (<SEDE>_<SALON>.html)
└── grupo/
    ├── 1_16/                      # Semanas 1 a 16: Bloques UTC semestrales
    │                              # (<SEDE>_<BLOQUE>.html)
    ├── 1_8/                       # Semanas 1 a 8: Bloques UTC modulares
    │                              # (<SEDE>_<BLOQUE>.html)
    └── 9_16/                      # Semanas 9 a 16: Bloques UTC modulares
                                   # (<SEDE>_<BLOQUE>.html)
```

> **📌 Nota sobre Profesores y Salas**:
> 1. **Profesor**: Cada docente cuenta con dos visualizadores (`1_8` y `9_16`) que integran su carga completa para ese módulo, uniendo sus asignaturas semestrales (`1–16`) con las modulares correspondientes.
> 2. **Sala**: Cada espacio físico cuenta con dos visualizadores (`1_8` y `9_16`). En ambos aparecen las ocupaciones del horario semestral (`1–16`) además de las modulares, asegurando que ninguna ocupación quede oculta para evitar duplicidades o cruces de aulas.
> 3. **Grupo**: Conserva los 3 bloques independientes (`1_16`, `1_8`, `9_16`) de los bloques UTC correspondientes al plan curricular de cada grupo.

Adicionalmente, se producen dos reportes de apoyo en Excel:
1. `Mapeo_Bloques_Transformados.xlsx`: Matriz de correspondencia entre el bloque original y la nomenclatura con letra asignada para cruces internos.
2. `Reporte_Packages_Expandidos.xlsx`: Cruce 1:1 de paquetes asignados por bloque.


---

## 🚀 Instalación y Requisitos

### Requisitos Previos
- Python 3.10 o superior (compatible con Python 3.11, 3.12 y 3.13).

### Instalación de Dependencias
Instale los paquetes requeridos usando `pip`:

```bash
pip install -r requirements.txt
```

El archivo `requirements.txt` incluye:
```text
pandas>=2.0
openpyxl>=3.1
jinja2>=3.1
streamlit>=1.35
```

---

## 🖥 Modos de Ejecución

### 1. Aplicación Web Interactiva (Streamlit)
Recomendado para usuarios finales. Permite cargar archivos vía drag & drop, seleccionar planteles visualmente, configurar filtros de semanas, descargar paquetes ZIP y previsualizar horarios renderizados:

```bash
streamlit run app.py
```

La interfaz consta de 6 pasos intuitivos:
1. **📁 Subir archivos**: Carga del Reporte de Horarios y opcionalmente el de Secciones.
2. **🏫 Seleccionar sedes**: Detección automática de campus presentes en los datos con posibilidad de agregar códigos personalizados.
3. **📅 Seleccionar semanas**: Selección de bloques de semanas (1–16, 1–8, 9–16).
4. **🚀 Generar horarios**: Resumen visual con métricas y barra de progreso en tiempo real.
5. **📥 Descargar resultados**: Botones con indicador de peso en MB y modal de confirmación.
6. **👁️ Vista previa**: Pestañas interactivas por sede para inspeccionar el horario de cualquier grupo, docente o salón directamente en pantalla.

### 2. CLI Rápido (Todas las sedes)
Ejecuta la generación directa para todos los archivos `.xlsx` ubicados en la carpeta actual:

```bash
python generar_reportes.py
```

Genera las carpetas `Horarios_<SEDE>/` (organizadas en profesor, sala y grupo) y los archivos ZIP individuales `Horarios_<SEDE>.zip`.

### 3. CLI con Filtro por Sede y Semanas
Permite ejecutar por terminal exactamente el mismo pipeline que la aplicación web, controlando sedes específicas:

```bash
python run_filtrado.py
```

> **Nota**: Para cambiar las sedes en este modo, edite la variable `SEDES_FILTRO` en `run_filtrado.py` (ejemplo: `SEDES_FILTRO = {"TOR", "CUA", "IZT"}`).

---

## 🧩 Módulos y Responsabilidades

| Módulo | Responsabilidad |
|---|---|
| `horarios.config` | Define rutas absolutas del proyecto, nombres de columnas, abreviaturas de días, turnos y grupos de semanas. |
| `horarios.carga` | Localiza y lee archivos Excel, normaliza nombres de columnas a un esquema canónico y construye el mapa de salones por día. |
| `horarios.bloques` | Analiza cadenas de bloques (`TOR1A1`, `TOR1A2`), agrupa por base y numera con letras consecutivas. |
| `horarios.grilla` | Parsea strings de horario (`Lu(07:00-09:00)`), calcula franjas de 30 minutos y genera la estructura de tabla con `rowspan`. |
| `horarios.vistas` | Construye los datos agregados para cada perspectiva (bloques UTC, docentes y aulas) y renderiza la plantilla HTML. |
| `horarios.reportes_excel` | Exporta los archivos Excel auxiliares de mapeo y expansión de paquetes. |
| `horarios.pipeline` | Itera sobre los grupos de semanas, invoca la generación y comprime el árbol final en archivos `.zip`. |
| `ui.styles` | Inyecta `assets/styles.css`, provee el logo en Base64 y maqueta los contenedores visuales de cada paso. |
| `ui.auth` | Valida credenciales, inicializa la sesión y asegura la limpieza de archivos temporales al salir. |
| `ui.descarga` | Despliega el diálogo modal de confirmación con animación y botón de re-descarga. |
| `ui.pasos` | Orquesta la presentación de los 6 pasos y la previsualización de HTML embebido. |

---

## 🔐 Autenticación

La aplicación web cuenta con una pantalla de acceso para proteger el entorno en despliegues compartidos o en la nube.

* **Usuario por defecto**: `programacion_academica`
* **Contraseña**: configurada en `ui/config.py` (`pacademica2026`)

Al presionar **Cerrar Sesión**, el sistema limpia automáticamente los directorios temporales generados en el servidor y restablece el estado de sesión.
