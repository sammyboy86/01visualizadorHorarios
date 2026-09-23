# -*- coding: utf-8 -*-
"""
Modal y notificaciones de descarga interactiva.
"""
import os
import streamlit as st

# Compatibilidad con st.dialog (Streamlit >= 1.34) o st.experimental_dialog
if hasattr(st, "dialog"):
    _dialog_decorator = st.dialog
elif hasattr(st, "experimental_dialog"):
    _dialog_decorator = st.experimental_dialog
else:
    _dialog_decorator = None


def render_dialog_content(filename: str, file_path_or_blob):
    """Contenido visual del modal de descarga."""
    size_mb = 0.0
    if isinstance(file_path_or_blob, str) and os.path.exists(file_path_or_blob):
        size_mb = os.path.getsize(file_path_or_blob) / (1024 * 1024)
    elif isinstance(file_path_or_blob, (bytes, bytearray)):
        size_mb = len(file_path_or_blob) / (1024 * 1024)

    st.markdown(
        f"""
        <div style="text-align: center; padding: 0.5rem 0 1rem 0;">
            <div style="width: 76px; height: 76px; margin: 0 auto 1.2rem auto; border-radius: 50%;
                        background: linear-gradient(135deg, rgba(79,139,249,0.18), rgba(108,99,255,0.25));
                        border: 2px solid rgba(79,139,249,0.4); display: flex; align-items: center;
                        justify-content: center; box-shadow: 0 0 24px rgba(79,139,249,0.35);">
                <span style="font-size: 2.3rem;">📥</span>
            </div>
            <h3 style="margin: 0 0 0.5rem 0; color: #fafafa; font-family: 'Outfit', sans-serif;">
                ¡Descarga en proceso!
            </h3>
            <div style="display: inline-block; background: rgba(79,139,249,0.12);
                        border: 1px solid rgba(79,139,249,0.3); border-radius: 8px;
                        padding: 0.35rem 0.9rem; color: #60a5fa; font-weight: 600;
                        font-family: monospace; font-size: 0.95rem; margin-bottom: 1rem;">
                {filename} &middot; {size_mb:.1f} MB
            </div>
            <p style="color: #94a3b8; font-size: 0.92rem; line-height: 1.5; margin-bottom: 1.2rem;">
                Tu solicitud está siendo procesada. El archivo se está transfiriendo a tu equipo
                y se guardará en tu carpeta de descargas habitual.
            </p>
            <div style="background: rgba(16,185,129,0.1); border: 1px solid rgba(16,185,129,0.3);
                        border-radius: 10px; padding: 0.6rem 1rem; color: #a7f3d0;
                        font-size: 0.88rem; font-weight: 500; display: flex; align-items: center;
                        justify-content: center; gap: 0.5rem; margin-bottom: 1.4rem;">
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
            st.session_state.just_downloaded = None
            st.rerun()


if _dialog_decorator:
    @_dialog_decorator("📥 Descarga en proceso")
    def _modal_dialog(filename: str, file_path_or_blob):
        render_dialog_content(filename, file_path_or_blob)


def show_download_dialog(filename: str, file_path_or_blob):
    """Muestra el modal de descarga interactivo y un toast de confirmación."""
    try:
        st.toast(f"📥 Descarga iniciada: {filename}", icon="📥")
    except Exception:
        pass

    if _dialog_decorator:
        _modal_dialog(filename, file_path_or_blob)
    else:
        st.info(f"📥 Descargando **{filename}**...")
        render_dialog_content(filename, file_path_or_blob)
