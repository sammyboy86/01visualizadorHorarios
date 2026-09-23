# -*- coding: utf-8 -*-
"""
Configuración, rutas y constantes de la aplicación.
"""
import os
import streamlit as st

# ── Rutas del sistema ───────────────────────────────────────
MODULES_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(MODULES_DIR)

LOGO_FILE = os.path.join(PROJECT_ROOT, "logo_utc.png")
TEMPLATE_FILE = os.path.join(PROJECT_ROOT, "template_horario.html")

# ── Credenciales de acceso ──────────────────────────────────
AUTH_USER = "programacion_academica"
AUTH_PASSWORDS = {"pacademica2026", "pacaademica2026"}

# ── Sedes y configuraciones de semanas ──────────────────────
SEDES_CONOCIDAS = ["ARA", "CUA", "IZT", "PUE", "RPA", "TLA", "TOR", "TPN"]

GRUPOS_SEMANAS_CFG = [
    {
        "id": "sem_1_16",
        "nombre": "Semanas 1 – 16",
        "filtro": {"(1 - 15)", "(1 - 16)"},
        "vacias": True,
    },
    {
        "id": "sem_1_8",
        "nombre": "Semanas 1 – 8",
        "filtro": {"(1 - 8)"},
        "vacias": False,
    },
    {
        "id": "sem_9_16",
        "nombre": "Semanas 9 – 16",
        "filtro": {"(9 - 15)", "(9 - 16)"},
        "vacias": False,
    },
]


def configure_page():
    """Configuración principal de Streamlit (debe ejecutarse primero)."""
    st.set_page_config(
        page_title="Horarios UTC",
        page_icon="📅",
        layout="centered",
        initial_sidebar_state="collapsed",
    )
