# -*- coding: utf-8 -*-
"""
Lógica de autenticación, control de acceso y cierre de sesión.
"""
import os
import shutil
import streamlit as st
from modules.config import AUTH_PASSWORDS, AUTH_USER
from modules.styles import get_logo_b64


def is_logged_in() -> bool:
    """Verifica si el usuario actual está autenticado."""
    return st.session_state.get("auth", False)


def logout():
    """Limpia el directorio temporal y las variables de sesión antes de salir."""
    wd = st.session_state.get("workdir", "")
    if wd and os.path.exists(wd):
        shutil.rmtree(wd, ignore_errors=True)
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.rerun()


def render_login_page():
    """Renderiza la pantalla de inicio de sesión."""
    st.markdown(
        '<style>'
        'section[data-testid="stSidebar"]{display:none}'
        'header{display:none}'
        '</style>',
        unsafe_allow_html=True,
    )

    logo = get_logo_b64()
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
        st.markdown("")  # spacer
        pwd = st.text_input("🔒 Contraseña", type="password")
        st.markdown("")  # spacer
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
