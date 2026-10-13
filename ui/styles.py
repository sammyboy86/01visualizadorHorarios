# -*- coding: utf-8 -*-
"""
Estilos globales y componentes visuales reutilizables.

El CSS vive en `assets/styles.css`; aquí solo se inyecta y se definen
pequeños helpers HTML (logo, tarjetas de paso, conectores).
"""
import base64
import os
from functools import lru_cache

import streamlit as st

from horarios.config import ASSETS_DIR, LOGO_FILE

CSS_FILE = os.path.join(ASSETS_DIR, "styles.css")


@lru_cache(maxsize=1)
def get_logo_b64() -> str:
    """Logo UTC en base64 (cadena vacía si no existe)."""
    if os.path.exists(LOGO_FILE):
        with open(LOGO_FILE, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""


@lru_cache(maxsize=1)
def _leer_css() -> str:
    with open(CSS_FILE, encoding="utf-8") as f:
        return f.read()


def inject_app_css():
    """Inyecta fuentes, tema oscuro y estilos de tarjetas/botones."""
    st.markdown(f"<style>{_leer_css()}</style>", unsafe_allow_html=True)


def render_step_card_start(num: int, title: str):
    """Cabecera estilizada de un paso: círculo numerado + título."""
    st.markdown(
        f"""<div class="step-card"><div class="step-header">
        <div class="step-num">{num}</div>
        <div class="step-title">{title}</div>
        </div></div>""",
        unsafe_allow_html=True,
    )


def render_step_connector():
    """Línea vertical sutil entre pasos."""
    st.markdown(
        '<div class="step-connector"><div class="line"></div></div>',
        unsafe_allow_html=True,
    )
