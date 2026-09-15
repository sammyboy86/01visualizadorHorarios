# -*- coding: utf-8 -*-
"""
Visualizador de Horarios UTC — Aplicación Streamlit
===================================================
Wraps generar_reportes.py with a web UI:
  • Login gate
  • Excel file upload (Reporte + Secciones)
  • Sede / semana configuration
  • Generation with progress
  • ZIP download & inline HTML preview
"""
import streamlit as st
import streamlit.components.v1 as components
import os
import sys
import tempfile
import threading
import shutil
import pathlib
import zipfile
import re
import base64
import traceback

import pandas as pd

# ── Module setup ────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import generar_reportes as gen  # noqa: E402

# Preserve the *true* originals across Streamlit reruns.  Storing them
# on the module object itself guarantees we never accidentally save a
# monkey-patched version even if a previous run crashed mid-generation.
if not hasattr(gen, "_st_orig_load_data_unificado"):
    gen._st_orig_load_data_unificado = gen.load_data_unificado
if not hasattr(gen, "_st_orig_find_input_excel"):
    gen._st_orig_find_input_excel = gen.find_input_excel

_ORIG_LOAD = gen._st_orig_load_data_unificado
_ORIG_FIND = gen._st_orig_find_input_excel

_GEN_LOCK = threading.Lock()

# ── Page config (must be first Streamlit call) ──────────────
st.set_page_config(
    page_title="Horarios UTC",
    page_icon="📅",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── Constants ───────────────────────────────────────────────
LOGO_FILE     = os.path.join(SCRIPT_DIR, "logo_utc.png")
TEMPLATE_FILE = os.path.join(SCRIPT_DIR, "template_horario.html")

AUTH_USER = "programacion_academica"
AUTH_PASSWORDS = {"pacademica2026", "pacaademica2026"}

SEDES_CONOCIDAS = ["ARA", "CUA", "IZT", "PUE", "RPA", "TLA", "TOR", "TPN"]

GRUPOS_SEMANAS_CFG = [
    {"id": "sem_1_16", "nombre": "Semanas 1 – 16",
     "filtro": {"(1 - 15)", "(1 - 16)"}, "vacias": True},
    {"id": "sem_1_8",  "nombre": "Semanas 1 – 8",
     "filtro": {"(1 - 8)"},              "vacias": False},
    {"id": "sem_9_16", "nombre": "Semanas 9 – 16",
     "filtro": {"(9 - 15)", "(9 - 16)"}, "vacias": False},
]


# ═════════════════════════════════════════════════════════════
#  CSS & THEMING
# ═════════════════════════════════════════════════════════════
def _logo_b64() -> str:
    if os.path.exists(LOGO_FILE):
        with open(LOGO_FILE, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""


def _inject_css():
    st.markdown("""<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
    h1, h2, h3, h4 { font-family: 'Outfit', sans-serif !important; }

    /* ── Hide sidebar completely ── */
    section[data-testid="stSidebar"] { display: none !important; }
    button[data-testid="stSidebarCollapseButton"],
    button[data-testid="stSidebarNavButton"],
    [data-testid="collapsedControl"] { display: none !important; }

    /* ── Login ── */
    .login-wrap { display:flex; justify-content:center; padding-top:8vh; }
    .login-card {
        background: linear-gradient(145deg, rgba(26,29,41,.97), rgba(14,17,23,.99));
        border: 1px solid rgba(79,139,249,.2);
        border-radius: 24px; padding: 3rem 2.5rem 2rem;
        width:100%; max-width:440px;
        box-shadow: 0 24px 64px rgba(0,0,0,.55), 0 0 48px rgba(79,139,249,.08);
        text-align: center;
    }
    .login-card img {
        width:88px; margin-bottom:1.4rem;
        filter: drop-shadow(0 4px 12px rgba(79,139,249,.25));
    }
    .login-card .lc-title {
        font-family:'Outfit',sans-serif; font-size:1.5rem;
        font-weight:600; color:#fafafa; margin:0 0 .4rem;
    }
    .login-card .lc-sub {
        font-size:.88rem; color:#6b7280; margin:0 0 2rem;
    }

    /* ── App header ── */
    .app-hdr {
        background: linear-gradient(135deg,#1a1d29,#0e1117);
        border:1px solid rgba(79,139,249,.12); border-radius:16px;
        padding:1rem 1.5rem; margin-bottom:1.2rem;
        display:flex; align-items:center; gap:1rem;
    }
    .app-hdr img {
        width:48px;
        filter:drop-shadow(0 2px 8px rgba(79,139,249,.25));
    }
    .app-hdr .t h2 { font-size:1.15rem; margin:0; color:#fafafa; }
    .app-hdr .t p  { font-size:.78rem; margin:0; color:#6b7280; }

    /* ── Step cards ── */
    .step-card {
        background: linear-gradient(145deg, rgba(26,29,41,.7), rgba(14,17,23,.85));
        border: 1px solid rgba(79,139,249,.12);
        border-radius: 16px;
        padding: 1.5rem 1.8rem 1.2rem;
        margin-top: 0.6rem;
        margin-bottom: 0.4rem;
    }
    .step-header {
        display: flex; align-items: center; gap: .75rem;
        margin-bottom: 1rem;
    }
    .step-num {
        background: linear-gradient(135deg,#4f8bf9,#6c63ff);
        color: #fff; font-family:'Outfit',sans-serif;
        font-weight: 700; font-size: .85rem;
        width: 32px; height: 32px; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        flex-shrink: 0;
        box-shadow: 0 4px 12px rgba(79,139,249,.3);
    }
    .step-title {
        font-family:'Outfit',sans-serif; font-size: 1rem;
        font-weight: 600; color: #e0e0e0; margin: 0;
    }
    .step-connector {
        display: flex; justify-content: center;
        padding: .4rem 0;
    }
    .step-connector .line {
        width: 2px; height: 36px;
        background: linear-gradient(180deg, rgba(79,139,249,.35), rgba(79,139,249,.08));
        border-radius: 1px;
    }

    /* ── Metric cards ── */
    [data-testid="stMetric"] {
        background: rgba(26,29,41,.6);
        border:1px solid rgba(79,139,249,.1);
        border-radius:12px; padding:.8rem 1rem;
    }

    /* ── Primary buttons ── */
    button[kind="primary"] {
        background: linear-gradient(135deg,#4f8bf9,#6c63ff) !important;
        border:none !important; border-radius:10px !important;
        font-weight:600 !important; letter-spacing:.3px !important;
        box-shadow:0 4px 16px rgba(79,139,249,.3) !important;
        transition:all .25s ease !important;
    }
    button[kind="primary"]:hover {
        transform:translateY(-2px) !important;
        box-shadow:0 8px 24px rgba(79,139,249,.4) !important;
    }

    /* ── Logout button ── */
    .logout-row {
        display: flex; justify-content: flex-end;
        margin-bottom: .5rem;
    }
    </style>""", unsafe_allow_html=True)


def _step_card_start(num: int, title: str):
    """Render the opening of a styled step card."""
    st.markdown(
        f"""<div class="step-card"><div class="step-header">
        <div class="step-num">{num}</div>
        <div class="step-title">{title}</div>
        </div></div>""",
        unsafe_allow_html=True,
    )


def _step_connector():
    """Render a subtle vertical connector between steps."""
    st.markdown(
        '<div class="step-connector"><div class="line"></div></div>',
        unsafe_allow_html=True,
    )


# ═════════════════════════════════════════════════════════════
#  AUTHENTICATION
# ═════════════════════════════════════════════════════════════
def _logged_in() -> bool:
    return st.session_state.get("auth", False)


def _login_page():
    # Hide sidebar & top bar on the login screen
    st.markdown(
        '<style>section[data-testid="stSidebar"]{display:none}'
        "header{display:none}</style>",
        unsafe_allow_html=True,
    )

    logo = _logo_b64()
    _, col, _ = st.columns([1.2, 1, 1.2])
    with col:
        st.markdown(
            f"""
            <div class="login-wrap"><div class="login-card">
                <img src="data:image/png;base64,{logo}" alt="UTC">
                <div class="lc-title">Visualizador de Horarios</div>
                <div class="lc-sub">Programación Académica · UTC</div>
            </div></div>""",
            unsafe_allow_html=True,
        )

        with st.form("login_form", clear_on_submit=False):
            user = st.text_input("👤 Usuario", value="programacion_academica")
            pwd = st.text_input("🔒 Contraseña", type="password")
            go = st.form_submit_button(
                "Iniciar Sesión", use_container_width=True, type="primary"
            )
            if go:
                user_clean = (user or "").strip().lower()
                pwd_clean = (pwd or "").strip()
                if user_clean in ("", AUTH_USER.lower()) and pwd_clean in AUTH_PASSWORDS:
                    st.session_state.auth = True
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas. Verifique usuario y contraseña.")


# ═════════════════════════════════════════════════════════════
#  HELPERS
# ═════════════════════════════════════════════════════════════
def _detect_sedes(uploaded) -> list[str]:
    """Return sede codes found in the uploaded Excel (reads ≤1 000 rows)."""
    try:
        df = pd.read_excel(uploaded, engine="openpyxl", nrows=1000)
        uploaded.seek(0)
        for c in df.columns:
            if str(c).strip() in ("CAMPUS PLANTEL", "codigo_plantel", "SEDE"):
                return sorted(df[c].dropna().astype(str).unique().tolist())
    except Exception:
        pass
    return []


def _prepare_workdir(reporte, secciones=None) -> str:
    """Create/clean a temp workdir and populate it with uploads + assets."""
    if "workdir" not in st.session_state or not os.path.exists(
        st.session_state.get("workdir", "")
    ):
        st.session_state.workdir = tempfile.mkdtemp(prefix="horarios_utc_")

    wd = st.session_state.workdir

    # Wipe previous run
    for item in pathlib.Path(wd).iterdir():
        shutil.rmtree(item) if item.is_dir() else item.unlink()

    # Save uploads with their original names (must match glob patterns)
    (pathlib.Path(wd) / reporte.name).write_bytes(reporte.getbuffer())
    if secciones:
        (pathlib.Path(wd) / secciones.name).write_bytes(secciones.getbuffer())

    # Copy HTML template & logo
    shutil.copy2(TEMPLATE_FILE, wd)
    shutil.copy2(LOGO_FILE, wd)
    return wd


# ═════════════════════════════════════════════════════════════
#  GENERATION ENGINE  (mirrors run_filtrado.py)
# ═════════════════════════════════════════════════════════════
def _run(wd: str, sedes: set, grupos: list, bar, status) -> list[str]:
    """Execute schedule generation.  Returns list of absolute ZIP paths."""
    if not _GEN_LOCK.acquire(blocking=False):
        status.warning("⏳ Otro usuario está generando horarios. Esperando…")
        _GEN_LOCK.acquire()  # block until available

    saved = os.getcwd()
    gen.load_data_unificado = _ORIG_LOAD
    gen.find_input_excel = _ORIG_FIND

    try:
        os.chdir(wd)
        total = len(grupos) + 1  # +1 for the packaging step

        # ── per-grupo iteration ──
        for i, g in enumerate(grupos):
            bar.progress(i / total, text=f"Generando {g['nombre']}…")
            status.info(
                f"⏳ **{g['nombre']}** · Sedes: {', '.join(sorted(sedes))}"
            )

            # Build a *new* loader for this iteration (closure captures values)
            def _make_loader(sem, vac, sed):
                def _load(path_entrada=None, sedes_filtro=None):
                    df = _ORIG_LOAD(path_entrada, sedes_filtro=sed)
                    if "SEMANAS" in df.columns:
                        mask = df["SEMANAS"].astype(str).str.strip().isin(sem)
                        if vac:
                            mask = mask | df["SEMANAS"].isna()
                        df = df[mask].copy()
                    return df
                return _load

            gen.load_data_unificado = _make_loader(g["filtro"], g["vacias"], sedes)
            gen.generar_reportes(sedes_filtro=sedes)

            # Rename output folders → add suffix
            for sede in sedes:
                slug = re.sub(r'[\\/*?"<>| ]', "_", sede)
                src = pathlib.Path(f"salida_{slug}")
                dst = pathlib.Path(f"horarios_{slug}_{g['id']}")
                if dst.exists():
                    shutil.rmtree(dst)
                if src.exists():
                    src.rename(dst)
                for zp in pathlib.Path(".").glob(f"UTC_Reportes_SEDE_{slug}.zip"):
                    zp.unlink()

        # ── package by sede ──
        bar.progress((total - 1) / total, text="Empaquetando…")
        status.info("📦 Empaquetando archivos…")

        zips: list[str] = []
        for sede in sedes:
            slug = re.sub(r'[\\/*?"<>| ]', "_", sede)
            parent = pathlib.Path(f"Horarios_{slug}")
            if parent.exists():
                shutil.rmtree(parent)
            parent.mkdir()

            for g in grupos:
                src = pathlib.Path(f"horarios_{slug}_{g['id']}")
                if src.exists():
                    src.rename(parent / src.name)

            zpath = pathlib.Path(f"Horarios_{slug}.zip")
            if zpath.exists():
                zpath.unlink()
            with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
                for f in parent.rglob("*"):
                    zf.write(f, f.relative_to(parent.parent))
            zips.append(str(zpath.resolve()))

        bar.progress(1.0, text="✅ Completado")
        return zips

    finally:
        os.chdir(saved)
        gen.load_data_unificado = _ORIG_LOAD
        gen.find_input_excel = _ORIG_FIND
        _GEN_LOCK.release()


# ═════════════════════════════════════════════════════════════
#  MAIN APPLICATION — Vertical step-by-step flow
# ═════════════════════════════════════════════════════════════
def _app():
    logo = _logo_b64()

    # ── Header + logout ──
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
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  STEP 1 — Upload files
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    _step_card_start(1, "📁 Subir archivos")

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
            help="Resultados - Secciones - Proceso NNN.xlsx · salones por día",
        )

    if reporte:
        st.success(f"✅ **{reporte.name}** cargado correctamente")
    else:
        st.info("👆 Suba el reporte para continuar")

    _step_connector()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  STEP 2 — Select sedes
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    _step_card_start(2, "🏫 Seleccionar sedes")

    detected = _detect_sedes(reporte) if reporte else []
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

    _step_connector()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  STEP 3 — Select week groups
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    _step_card_start(3, "📅 Seleccionar semanas")

    active: list[dict] = []
    gcols = st.columns(len(GRUPOS_SEMANAS_CFG))
    for gcol, g in zip(gcols, GRUPOS_SEMANAS_CFG):
        with gcol:
            if st.checkbox(g["nombre"], value=True, key=f"g_{g['id']}"):
                active.append(g)

    if active:
        st.success(f"✔ {len(active)} grupo(s) de semanas seleccionado(s)")
    else:
        st.info("Seleccione al menos un grupo de semanas")

    _step_connector()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  STEP 4 — Summary & Generate
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    ready = bool(reporte and sedes_final and active)

    _step_card_start(4, "🚀 Generar horarios")

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

    # ── Generation ──
    if clicked and ready:
        try:
            wd = _prepare_workdir(reporte, secciones)
            bar = st.progress(0, text="Iniciando…")
            status = st.empty()

            zips = _run(wd, sedes_final, active, bar, status)

            status.success(
                f"✅ ¡Generación completada! — {len(zips)} archivo(s) ZIP."
            )

            # Persist results for the download / preview sections
            st.session_state.res_zips = {
                os.path.basename(z): pathlib.Path(z).read_bytes() for z in zips
            }
            st.session_state.res_sedes = sorted(sedes_final)
            st.session_state.res_wd = wd

        except Exception as exc:
            st.error(f"❌ Error: {exc}")
            st.code(traceback.format_exc())

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  STEP 5 — Downloads (only shown after generation)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    zips_data = st.session_state.get("res_zips", {})
    if zips_data:
        _step_connector()
        _step_card_start(5, "📥 Descargar resultados")

        cols = st.columns(min(len(zips_data), 4))
        for i, (name, blob) in enumerate(zips_data.items()):
            with cols[i % len(cols)]:
                st.download_button(
                    f"⬇️ {name}",
                    data=blob,
                    file_name=name,
                    mime="application/zip",
                    use_container_width=True,
                )
                st.caption(f"{len(blob) / 1024 / 1024:.1f} MB")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  STEP 6 — Preview (only shown after generation)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    wd = st.session_state.get("res_wd", "")
    res_sedes = st.session_state.get("res_sedes", [])

    if wd and res_sedes and os.path.exists(wd):
        _step_connector()
        _step_card_start(6, "👁️ Vista previa del horario")
        st.caption(
            "📌 Esta es solo una **vista previa** dentro del navegador. "
            "Descargue el ZIP para obtener los archivos finales."
        )

        tabs = st.tabs(res_sedes)

        for tab, sede in zip(tabs, res_sedes):
            with tab:
                slug = re.sub(r'[\\/*?"<>| ]', "_", sede)
                parent = pathlib.Path(wd) / f"Horarios_{slug}"
                if not parent.exists():
                    st.info("Sin archivos para esta sede.")
                    continue

                grp_files = sorted(parent.rglob("grupos/*.html"))
                doc_files = sorted(parent.rglob("docentes/*.html"))

                view = st.radio(
                    "Ver:", ["Bloques / Grupos", "Docentes"],
                    horizontal=True, key=f"v_{sede}",
                )
                files = grp_files if view == "Bloques / Grupos" else doc_files

                if not files:
                    st.info(f"No hay archivos de {view.lower()}.")
                else:
                    labels = [f.stem for f in files]
                    chosen = st.selectbox(
                        "Archivo:", labels, key=f"sel_{sede}_{view}"
                    )
                    idx = labels.index(chosen)
                    raw_html = files[idx].read_text("utf-8")
                    # Force white background so the schedule is readable
                    # inside Streamlit's dark-themed iframe
                    bg_style = (
                        '<style>html, body { background-color: #ffffff !important; '
                        'color: #000000 !important; }</style>'
                    )
                    if '</head>' in raw_html:
                        raw_html = raw_html.replace('</head>', bg_style + '</head>', 1)
                    else:
                        raw_html = bg_style + raw_html
                    components.html(raw_html, height=700, scrolling=True)


# ═════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═════════════════════════════════════════════════════════════
_inject_css()

if _logged_in():
    _app()
else:
    _login_page()
