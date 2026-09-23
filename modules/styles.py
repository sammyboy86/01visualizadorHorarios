# -*- coding: utf-8 -*-
"""
Estilos CSS, theming y componentes de interfaz reutilizables.
"""
import base64
import os
import streamlit as st
from modules.config import LOGO_FILE


def get_logo_b64() -> str:
    """Devuelve el logo UTC en formato base64."""
    if os.path.exists(LOGO_FILE):
        with open(LOGO_FILE, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""


def inject_app_css():
    """Inyecta las fuentes, reglas de CSS oscuro y estilos de tarjeta/botones."""
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
    .login-wrap {
        display:flex; justify-content:center;
        padding-top:10vh; padding-bottom:4vh;
    }
    .login-card {
        background: linear-gradient(145deg, rgba(26,29,41,.97), rgba(14,17,23,.99));
        border: 1px solid rgba(79,139,249,.2);
        border-radius: 24px;
        padding: 3.5rem 3rem 2.5rem;
        width:100%; max-width:480px;
        box-shadow: 0 24px 64px rgba(0,0,0,.55), 0 0 48px rgba(79,139,249,.08);
        text-align: center;
    }
    .login-card img {
        width:96px; margin-bottom:1.6rem;
        filter: drop-shadow(0 4px 12px rgba(79,139,249,.25));
    }
    .login-card .lc-title {
        font-family:'Outfit',sans-serif; font-size:1.6rem;
        font-weight:600; color:#fafafa; margin:0 0 .5rem;
    }
    .login-card .lc-sub {
        font-size:.92rem; color:#6b7280; margin:0 0 2.2rem;
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

    /* ── Downloading Modal ── */
    .utc-modal-overlay {
        position: fixed;
        inset: 0;
        background: rgba(10, 12, 18, 0.82);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 999999;
        opacity: 0;
        visibility: hidden;
        transition: opacity 0.25s cubic-bezier(0.16, 1, 0.3, 1), visibility 0.25s;
    }
    .utc-modal-overlay.active {
        opacity: 1;
        visibility: visible;
    }
    .utc-modal-card {
        background: linear-gradient(155deg, rgba(26, 29, 41, 0.98), rgba(14, 17, 23, 0.99));
        border: 1px solid rgba(79, 139, 249, 0.3);
        border-radius: 24px;
        padding: 2.2rem 2.4rem;
        width: 90%;
        max-width: 440px;
        text-align: center;
        position: relative;
        box-shadow: 0 24px 64px rgba(0, 0, 0, 0.65), 0 0 40px rgba(79, 139, 249, 0.15);
        transform: scale(0.92) translateY(12px);
        transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    }
    .utc-modal-overlay.active .utc-modal-card {
        transform: scale(1) translateY(0);
    }
    .utc-modal-close {
        position: absolute;
        top: 14px;
        right: 16px;
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        color: #94a3b8;
        width: 32px;
        height: 32px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        font-size: 1.2rem;
        line-height: 1;
        transition: all 0.2s ease;
    }
    .utc-modal-close:hover {
        background: rgba(255, 255, 255, 0.15);
        color: #ffffff;
        transform: scale(1.08);
    }
    .utc-modal-icon-wrap {
        display: flex;
        justify-content: center;
        margin-bottom: 1.2rem;
    }
    .utc-icon-circle {
        width: 76px;
        height: 76px;
        border-radius: 50%;
        background: linear-gradient(135deg, rgba(79, 139, 249, 0.15), rgba(108, 99, 255, 0.2));
        border: 2px solid rgba(79, 139, 249, 0.4);
        display: flex;
        align-items: center;
        justify-content: center;
        position: relative;
        box-shadow: 0 0 24px rgba(79, 139, 249, 0.3);
        transition: all 0.3s ease;
    }
    .utc-icon-circle.pulsing {
        animation: utc-pulse-glow 2s infinite ease-in-out;
    }
    @keyframes utc-pulse-glow {
        0%, 100% {
            box-shadow: 0 0 16px rgba(79, 139, 249, 0.3), 0 0 0 0 rgba(79, 139, 249, 0.2);
        }
        50% {
            box-shadow: 0 0 28px rgba(79, 139, 249, 0.55), 0 0 0 8px rgba(79, 139, 249, 0.1);
        }
    }
    .utc-icon-download {
        width: 36px;
        height: 36px;
        color: #4f8bf9;
        transition: all 0.3s ease;
    }
    .utc-icon-circle.pulsing .arrow-stem,
    .utc-icon-circle.pulsing .arrow-head {
        animation: utc-arrow-bounce 1.2s infinite ease-in-out;
    }
    @keyframes utc-arrow-bounce {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(4px); }
    }
    .utc-icon-circle.completed {
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.18), rgba(5, 150, 105, 0.25)) !important;
        border-color: #10b981 !important;
        box-shadow: 0 0 28px rgba(16, 185, 129, 0.4) !important;
        animation: none !important;
    }
    @keyframes utc-check-pop {
        0% { transform: scale(0.6); opacity: 0; }
        60% { transform: scale(1.15); opacity: 1; }
        100% { transform: scale(1); opacity: 1; }
    }
    .utc-icon-circle.completed svg {
        animation: utc-check-pop 0.35s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards;
    }
    .utc-modal-title {
        font-family: 'Outfit', sans-serif !important;
        font-size: 1.35rem;
        font-weight: 700;
        color: #fafafa;
        margin: 0 0 0.5rem 0;
    }
    .utc-modal-filename {
        display: inline-block;
        font-family: 'Inter', monospace;
        font-size: 0.85rem;
        font-weight: 600;
        color: #60a5fa;
        background: rgba(79, 139, 249, 0.12);
        border: 1px solid rgba(79, 139, 249, 0.25);
        border-radius: 8px;
        padding: 0.25rem 0.75rem;
        margin-bottom: 0.85rem;
        word-break: break-all;
    }
    .utc-modal-desc {
        font-family: 'Inter', sans-serif;
        font-size: 0.88rem;
        color: #94a3b8;
        line-height: 1.45;
        margin: 0 0 1.2rem 0;
    }
    .utc-progress-track {
        width: 100%;
        height: 6px;
        background: rgba(255, 255, 255, 0.08);
        border-radius: 999px;
        overflow: hidden;
        margin: 1rem 0;
        position: relative;
    }
    .utc-progress-bar {
        height: 100%;
        position: absolute;
        top: 0;
        left: 0;
        width: 35%;
        background: linear-gradient(90deg, #4f8bf9, #6c63ff, #60a5fa);
        border-radius: 999px;
        animation: utc-indeterminate 1.4s infinite ease-in-out;
        transition: all 0.3s ease;
    }
    @keyframes utc-indeterminate {
        0% { left: -35%; width: 35%; }
        50% { left: 25%; width: 50%; }
        100% { left: 100%; width: 35%; }
    }
    .utc-progress-bar.completed {
        animation: none !important;
        left: 0 !important;
        width: 100% !important;
        background: #10b981 !important;
        box-shadow: 0 0 12px rgba(16, 185, 129, 0.5);
    }
    .utc-status-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 0.82rem;
        font-weight: 500;
        color: #94a3b8;
        background: rgba(255, 255, 255, 0.04);
        padding: 0.35rem 0.85rem;
        border-radius: 999px;
        border: 1px solid rgba(255, 255, 255, 0.08);
    }
    .utc-status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #4f8bf9;
        box-shadow: 0 0 8px #4f8bf9;
        animation: utc-dot-blink 1s infinite alternate;
    }
    @keyframes utc-dot-blink {
        from { opacity: 0.3; }
        to { opacity: 1; }
    }
    .utc-status-badge.completed {
        color: #a7f3d0;
        border-color: rgba(16, 185, 129, 0.3);
        background: rgba(16, 185, 129, 0.08);
    }
    .utc-status-badge.completed .utc-status-dot {
        background: #10b981;
        box-shadow: 0 0 8px #10b981;
        animation: none;
    }
    .utc-btn-downloading {
        opacity: 0.7 !important;
        cursor: wait !important;
        pointer-events: none !important;
    }
    </style>""", unsafe_allow_html=True)


def render_step_card_start(num: int, title: str):
    """Renderiza el inicio de una tarjeta de paso estilizada."""
    st.markdown(
        f"""<div class="step-card"><div class="step-header">
        <div class="step-num">{num}</div>
        <div class="step-title">{title}</div>
        </div></div>""",
        unsafe_allow_html=True,
    )


def render_step_connector():
    """Renderiza un conector vertical sutil entre pasos."""
    st.markdown(
        '<div class="step-connector"><div class="line"></div></div>',
        unsafe_allow_html=True,
    )
