# -*- coding: utf-8 -*-
"""
Visualizador de Horarios UTC — Aplicación Streamlit
===================================================
Punto de entrada principal. Orquesta los módulos de configuración,
estilos, autenticación y flujo de pasos de la interfaz.
"""
import os
import sys

# ── Asegurar ruta del proyecto en sys.path ──────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from modules.auth import is_logged_in, render_login_page
from modules.config import configure_page
from modules.styles import inject_app_css
from modules.ui_steps import render_main_app

# 1. Configuración de página (primera llamada de Streamlit)
configure_page()

# 2. Inyección de estilos y tema visual
inject_app_css()

# 3. Control de acceso y enrutamiento
if is_logged_in():
    render_main_app()
else:
    render_login_page()
