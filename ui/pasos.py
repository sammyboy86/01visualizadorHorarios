# -*- coding: utf-8 -*-
"""
Vistas y componentes paso a paso de la interfaz de usuario.
"""
import os
import pathlib
import traceback

import streamlit as st
import streamlit.components.v1 as components

from horarios.carga import detect_sedes
from horarios.config import GRUPOS_SEMANAS, SEDES_CONOCIDAS
from horarios.pipeline import carpeta_sede
from ui.auth import logout
from ui.descarga import show_download_dialog
from ui.generacion import prepare_workdir, run_generation
from ui.styles import (
    get_logo_b64,
    render_step_card_start,
    render_step_connector,
)


def render_header():
    """Renderiza la cabecera superior y el botón para cerrar sesión."""
    logo = get_logo_b64()
    lcol, rcol = st.columns([5, 1])
    with lcol:
        st.markdown(
            f"""<div class="app-hdr">
            <img src="data:image/png;base64,{logo}" alt="UTC">
            <div class="t">
                <h2>📅 Visualizador de Horarios</h2>
                <p>Genera reportes HTML de horarios por sede y grupo de semanas</p>
            </div></div>""",
            unsafe_allow_html=True,
        )
    with rcol:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            logout()


def step_1_upload():
    """Paso 1: Subida de archivos de reporte y secciones."""
    render_step_card_start(1, "📁 Subir archivos")

    col_a, col_b = st.columns(2)
    with col_a:
        reporte = st.file_uploader(
            "Reporte Horarios y Paquetes (.xlsx)",
            type=["xlsx"],
            key="up_rep",
            help="Reporte Horarios y Paquetes - Proceso NNN.xlsx",
        )
    with col_b:
        secciones = st.file_uploader(
            "Resultados Secciones (.xlsx) ",
            type=["xlsx"],
            key="up_sec",
            help="Resultados - Secciones - Proceso NNN.xlsx · salones y edificios por día",
        )

    if reporte:
        st.success(f"✅ **{reporte.name}** cargado correctamente")
    else:
        st.info("👆 Suba el reporte para continuar")

    render_step_connector()
    return reporte, secciones


def step_2_sedes(reporte):
    """Paso 2: Selección de sedes a procesar."""
    render_step_card_start(2, "🏫 Seleccionar sedes")

    detected = detect_sedes(reporte) if reporte else []
    options = sorted(set(SEDES_CONOCIDAS + detected))
    defaults = [s for s in (detected or ["TOR"]) if s in options]

    sel = st.multiselect("Sedes disponibles", options, default=defaults)
    custom = st.text_input("Agregar sede personalizada (código)", placeholder="Ej: MTY")
    sedes_final: set[str] = set(sel)
    if custom and custom.strip():
        sedes_final.add(custom.strip().upper())

    if sedes_final:
        st.success(f"✔ Sedes seleccionadas: **{', '.join(sorted(sedes_final))}**")
    else:
        st.info("Seleccione al menos una sede")

    render_step_connector()
    return sedes_final


def step_3_weeks():
    """Paso 3: Selección de bloques y grupos de semanas."""
    render_step_card_start(3, "📅 Seleccionar semanas")

    active: list[dict] = []
    gcols = st.columns(len(GRUPOS_SEMANAS))
    for gcol, g in zip(gcols, GRUPOS_SEMANAS):
        with gcol:
            if st.checkbox(g["nombre"], value=True, key=f"g_{g['id']}"):
                active.append(g)

    if active:
        st.success(f"✔ {len(active)} grupo(s) de semanas seleccionado(s)")
    else:
        st.info("Seleccione al menos un grupo de semanas")

    st.caption(
        "ℹ️ **Estructura organizada de salida:**\n"
        "- **profesor/**: `1_8` y `9_16` (materias modulares combinadas con semestrales 1–16)\n"
        "- **sala/**: `1_8` y `9_16` (ocupaciones modulares y ocupaciones semestrales 1–16)\n"
        "- **grupo/**: `1_16`, `1_8` y `9_16` (bloques UTC)"
    )

    render_step_connector()
    return active



def step_4_generate(reporte, secciones, sedes_final, active):
    """Paso 4: Resumen de configuración y ejecución del motor."""
    ready = bool(reporte and sedes_final and active)

    render_step_card_start(4, "🚀 Generar horarios")

    if ready:
        c1, c2, c3 = st.columns(3)
        c1.metric("Sedes", len(sedes_final))
        c2.metric("Grupos de semanas", len(active))
        c3.metric("Secciones", "✅ Incluido" if secciones else "⚠️ Sin archivo")
        st.markdown("")

    if not ready:
        missing = []
        if not reporte:
            missing.append("reporte")
        if not sedes_final:
            missing.append("sedes")
        if not active:
            missing.append("semanas")
        st.warning(f"⚠️ Complete los pasos anteriores: **{', '.join(missing)}**")

    clicked = st.button(
        "🚀 Generar Horarios",
        use_container_width=True,
        type="primary",
        disabled=not ready,
    )

    if clicked and ready:
        try:
            wd = prepare_workdir(reporte, secciones)
            zips = run_generation(wd, sedes_final, active)

            # Persistir rutas de resultados en el estado de sesión (ligero en RAM)
            st.session_state.res_zips = {
                os.path.basename(z): str(pathlib.Path(z).resolve()) for z in zips
            }
            st.session_state.res_sedes = sorted(sedes_final)
            st.session_state.res_wd = wd

        except Exception as exc:
            st.error(f"❌ Error: {exc}")
            st.code(traceback.format_exc())


def step_5_downloads():
    """Paso 5: Descarga de los archivos ZIP generados con modal interactivo."""
    zips_data = st.session_state.get("res_zips", {})
    if not zips_data:
        return

    render_step_connector()
    render_step_card_start(5, "📥 Descargar resultados")

    # Extraer y CONSUMIR el disparador del modal para que solo se ejecute una vez por clic
    target_dl = st.session_state.pop("trigger_download_modal", None)

    # Banner informativo de la última descarga solicitada
    last_dl = st.session_state.get("last_downloaded")
    if last_dl and last_dl in zips_data:
        val = zips_data[last_dl]
        size_mb = os.path.getsize(val) / (1024 * 1024) if isinstance(val, str) and os.path.exists(val) else len(val) / (1024 * 1024)
        st.success(
            f"📥 **Descarga en proceso:** Se ha solicitado **{last_dl}** ({size_mb:.1f} MB). "
            f"El archivo se está guardando en tu equipo."
        )

    def _on_download_click(fname):
        st.session_state.trigger_download_modal = fname
        st.session_state.last_downloaded = fname

    cols = st.columns(min(len(zips_data), 4))
    for i, (name, val) in enumerate(zips_data.items()):
        size_mb = os.path.getsize(val) / (1024 * 1024) if isinstance(val, str) and os.path.exists(val) else len(val) / (1024 * 1024)
        with cols[i % len(cols)]:
            if isinstance(val, str) and os.path.exists(val):
                with open(val, "rb") as fp:
                    dl_bytes = fp.read()
            else:
                dl_bytes = val

            st.download_button(
                f"⬇️ {name}",
                data=dl_bytes,
                file_name=name,
                mime="application/zip",
                use_container_width=True,
                key=f"dl_btn_{name}",
                on_click=_on_download_click,
                args=(name,),
            )
            st.caption(f"{size_mb:.1f} MB")

    # Mostrar modal dialog interactivo SOLO si fue disparado en este clic específico
    if target_dl and target_dl in zips_data:
        show_download_dialog(target_dl, zips_data[target_dl])


def step_6_preview():
    """Paso 6: Vista previa interactiva de los horarios HTML generados."""
    wd = st.session_state.get("res_wd", "")
    res_sedes = st.session_state.get("res_sedes", [])

    if not (wd and res_sedes and os.path.exists(wd)):
        return

    render_step_connector()
    render_step_card_start(6, "👁️ Vista previa del horario")
    st.caption(
        "📌 Esta es solo una **vista previa** dentro del navegador. "
        "Descargue el ZIP para obtener la estructura completa de archivos."
    )

    tabs = st.tabs(res_sedes)

    nombres_periodo = {
        "1_16": "Semanas 1–16",
        "1_8": "Semanas 1–8 (Módulo 1)",
        "9_16": "Semanas 9–16 (Módulo 2)",
    }

    for tab, sede in zip(tabs, res_sedes):
        with tab:
            parent = carpeta_sede(wd, sede)
            if not parent.exists():
                st.info("Sin archivos para esta sede.")
                continue

            tipo_sel = st.radio(
                "Categoría:",
                ["Profesor", "Sala", "Grupo"],
                horizontal=True,
                key=f"tipo_{sede}",
            )

            folder_map = {
                "Profesor": "profesor",
                "Sala": "sala",
                "Grupo": "grupo",
            }
            folder_name = folder_map[tipo_sel]
            cat_dir = parent / folder_name

            if not cat_dir.exists():
                st.info(f"No hay horarios de {tipo_sel.lower()} generados.")
                continue

            subfolders = [
                d for d in cat_dir.iterdir()
                if d.is_dir() and any(d.glob("*.html"))
            ]
            subfolders.sort(key=lambda d: d.name)

            if not subfolders:
                st.info(f"No hay archivos en la categoría {tipo_sel.lower()}.")
                continue

            p_cols = st.columns([2, 5])
            with p_cols[0]:
                periodo_dir = st.selectbox(
                    "Periodo / Semanas:",
                    subfolders,
                    format_func=lambda d: nombres_periodo.get(d.name, d.name),
                    key=f"per_{sede}_{folder_name}",
                )

            html_files = sorted(periodo_dir.glob("*.html"), key=lambda f: f.stem)
            if not html_files:
                st.info(f"No hay archivos HTML en {periodo_dir.name}.")
                continue

            with p_cols[1]:
                chosen_file = st.selectbox(
                    "Archivo:",
                    html_files,
                    format_func=lambda f: f.stem,
                    key=f"sel_{sede}_{folder_name}_{periodo_dir.name}",
                )

            raw_html = chosen_file.read_text("utf-8")
            bg_style = (
                '<style>html, body { background-color: #ffffff !important; '
                'color: #000000 !important; }</style>'
            )
            if '</head>' in raw_html:
                raw_html = raw_html.replace('</head>', bg_style + '</head>', 1)
            else:
                raw_html = bg_style + raw_html
            components.html(raw_html, height=700, scrolling=True)



def render_main_app():
    """Flujo vertical principal de la aplicación."""
    render_header()
    reporte, secciones = step_1_upload()
    sedes_final = step_2_sedes(reporte)
    active = step_3_weeks()
    step_4_generate(reporte, secciones, sedes_final, active)
    step_5_downloads()
    step_6_preview()
