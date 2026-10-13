# -*- coding: utf-8 -*-
"""
Configuración propia de la interfaz (página y acceso).

Las constantes de dominio (sedes, grupos de semanas, rutas de recursos) están
en `horarios/config.py` para que el motor y la UI compartan una sola fuente.
"""
import streamlit as st

# ── Credenciales de acceso ──────────────────────────────────
AUTH_USER = "programacion_academica"
AUTH_PASSWORDS = {"pacademica2026", "pacaademica2026"}


def configure_page():
    """Configuración principal de Streamlit (debe ser la primera llamada a st.*)."""
    st.set_page_config(
        page_title="Horarios UTC",
        page_icon="📅",
        layout="centered",
        initial_sidebar_state="collapsed",
    )
