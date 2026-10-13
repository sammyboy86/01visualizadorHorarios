# -*- coding: utf-8 -*-
"""
Modal y notificaciones de descarga interactiva con confirmación visual.
"""
import base64
import os
import streamlit as st

from horarios.config import ASSETS_DIR

# Compatibilidad con st.dialog (Streamlit >= 1.34) o st.experimental_dialog
if hasattr(st, "dialog"):
    _dialog_decorator = st.dialog
elif hasattr(st, "experimental_dialog"):
    _dialog_decorator = st.experimental_dialog
else:
    _dialog_decorator = None

_GIF_FILE = os.path.join(ASSETS_DIR, "downloading.gif")


def _cargar_gif_b64() -> str:
    if os.path.exists(_GIF_FILE):
        try:
            with open(_GIF_FILE, "rb") as f:
                return base64.b64encode(f.read()).decode()
        except Exception:
            pass
    return ""


_GIF_B64 = _cargar_gif_b64()


def _calcular_tamano_mb(file_path_or_blob) -> float:
    if isinstance(file_path_or_blob, str) and os.path.exists(file_path_or_blob):
        return os.path.getsize(file_path_or_blob) / (1024 * 1024)
    if isinstance(file_path_or_blob, (bytes, bytearray)):
        return len(file_path_or_blob) / (1024 * 1024)
    return 0.0


def render_dialog_content(filename: str, file_path_or_blob):
    """Contenido visual del modal de descarga."""
    size_mb = _calcular_tamano_mb(file_path_or_blob)

    gif_html = (
        f'<img src="data:image/gif;base64,{_GIF_B64}" alt="Descargando..." />'
        if _GIF_B64
        else '<span class="emoji">📥</span>'
    )

    st.markdown(
        f"""
        <div class="dl-modal">
            <div class="icon">{gif_html}</div>
            <h3>¡Descarga en proceso!</h3>
            <div class="file">{filename} &middot; {size_mb:.1f} MB</div>
            <p class="desc">
                Tu solicitud está siendo procesada. El archivo se está transfiriendo a tu equipo
                y se guardará en tu carpeta de descargas habitual.
            </p>
            <div class="ok">
                <span>✔</span> Solicitud enviada correctamente al navegador
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        if isinstance(file_path_or_blob, str) and os.path.exists(file_path_or_blob):
            with open(file_path_or_blob, "rb") as fp:
                data_to_dl = fp.read()
        else:
            data_to_dl = file_path_or_blob

        st.download_button(
            "⬇️ Descargar de nuevo",
            data=data_to_dl,
            file_name=filename,
            mime="application/zip",
            key=f"modal_redownload_{filename}",
            use_container_width=True,
            help="Haz clic si tu navegador bloqueó la descarga automática",
        )
    with c2:
        if st.button("Cerrar", key=f"modal_close_{filename}", use_container_width=True, type="primary"):
            st.rerun()


if _dialog_decorator:
    @_dialog_decorator("📥 Descarga en proceso")
    def _modal_dialog(filename: str, file_path_or_blob):
        render_dialog_content(filename, file_path_or_blob)


def show_download_dialog(filename: str, file_path_or_blob):
    """Muestra el modal interactivo y un toast de confirmación."""
    try:
        st.toast(f"📥 Descarga iniciada: {filename}", icon="📥")
    except Exception:
        pass

    if _dialog_decorator:
        _modal_dialog(filename, file_path_or_blob)
    else:
        st.info(f"📥 Descargando **{filename}**...")
        render_dialog_content(filename, file_path_or_blob)
