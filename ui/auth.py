# -*- coding: utf-8 -*-
"""
Autenticación: pantalla de login, verificación de sesión y logout.
"""
import streamlit as st

from ui.config import AUTH_PASSWORDS, AUTH_USER
from ui.generacion import borrar_workdir
from ui.styles import get_logo_b64


def is_logged_in() -> bool:
    """True si el usuario actual ya inició sesión."""
    return st.session_state.get("auth", False)


def logout():
    """Borra el directorio temporal y todo el estado de sesión."""
    borrar_workdir()
    st.session_state.clear()
    st.rerun()


def _credenciales_validas(user: str, pwd: str) -> bool:
    user_clean = (user or "").strip().lower()
    pwd_clean = (pwd or "").strip()
    return user_clean in ("", AUTH_USER.lower()) and pwd_clean in AUTH_PASSWORDS


def render_login_page():
    """Pantalla de inicio de sesión."""
    st.markdown(
        '<style>section[data-testid="stSidebar"]{display:none} header{display:none}</style>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <div class="login-wrap"><div class="login-card">
            <img src="data:image/png;base64,{get_logo_b64()}" alt="UTC">
            <div class="lc-title">Visualizador de Horarios</div>
            <div class="lc-sub">Programación Académica · UTC</div>
        </div></div>""",
        unsafe_allow_html=True,
    )

    with st.form("login_form", clear_on_submit=False):
        user = st.text_input("👤 Usuario", value=AUTH_USER)
        st.markdown("")  # espaciador
        pwd = st.text_input("🔒 Contraseña", type="password")
        st.markdown("")  # espaciador
        if st.form_submit_button("Iniciar Sesión", use_container_width=True, type="primary"):
            if _credenciales_validas(user, pwd):
                st.session_state.auth = True
                st.rerun()
            else:
                st.error("Credenciales incorrectas. Verifique usuario y contraseña.")
