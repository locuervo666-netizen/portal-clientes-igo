import streamlit as st
import pandas as pd
import gspread
import os
import urllib.parse
import json
import requests
import re
import random
import io
import json
import hashlib
import google.auth.transport.requests
import streamlit.components.v1 as components
from datetime import datetime, timedelta, timezone
from google.oauth2.credentials import Credentials

# 🚀 IMPORTAÇÃO DO AGGRID E DO AUTO-REFRESH SILENCIOSO
from st_aggrid import AgGrid, GridOptionsBuilder, ColumnsAutoSizeMode, JsCode
from streamlit_autorefresh import st_autorefresh

FUSO_BR = timezone(timedelta(hours=-3))
LOGO_IGO = "https://i.postimg.cc/x84nnjjq/IGO-LOGO.png"
ARQUIVO_PORTAL_CLIENTE_LOGIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "portal_cliente_login.json")
NOME_PLANILHA_LOGIN_PORTAL = "DB_IGO_Logistica"
NOME_ABA_LOGIN_PORTAL = "Usuarios_Portal_Cliente"
SCOPES_GOOGLE_LOGIN = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
LOGOS_POR_TOMADOR = {
    "GRALAB": "https://cdn.awsli.com.br/2702/2702264/logo/gralab-rbuogsxve7.png",
    "IGO_LOGISTICA": LOGO_IGO,
    "LABEST": "logo_labest.png",
    "DANILO.DUARTE": "logo_labest.png",
    "SYNVIA": LOGO_IGO,
    "SOUZA CRUZ": "souza cruz.png",
}


def normalizar_usuario_login(usuario):
    return str(usuario).strip().upper()


def gerar_hash_senha(senha):
    return hashlib.sha256(str(senha).encode('utf-8')).hexdigest()


def verificar_senha(senha_digitada, senha_hash):
    if not senha_hash:
        return False
    return gerar_hash_senha(senha_digitada) == str(senha_hash)


def normalizar_tomador_portal(tomador):
    tomador_norm = str(tomador).strip().upper() or "TODOS"
    return tomador_norm.replace("CAEP", "SYNVIA").replace("CUNHA", "GRALAB")


def obter_token_google_login():
    token_str = os.environ.get("google_token_json")
    if not token_str:
        try:
            token_str = st.secrets.get("google_token_json")
        except Exception:
            token_str = None
    return token_str


def abrir_planilha_login_portal():
    token_str = obter_token_google_login()
    if not token_str:
        return None
    try:
        token_info = json.loads(token_str)
        creds = Credentials.from_authorized_user_info(token_info, scopes=SCOPES_GOOGLE_LOGIN)
        gc = gspread.authorize(creds)
        return gc.open(NOME_PLANILHA_LOGIN_PORTAL)
    except Exception:
        return None


def usuarios_padrao_portal_cliente():
    return {
        "GRALAB": {
            "senha_hash": gerar_hash_senha("123"),
            "logo": "https://cdn.awsli.com.br/2702/2702264/logo/gralab-rbuogsxve7.png",
            "filtro": "GRALAB",
            "tomador": "GRALAB"
        },
        "IGO_LOGISTICA": {
            "senha_hash": gerar_hash_senha("admin"),
            "logo": LOGO_IGO,
            "filtro": "TODOS",
            "tomador": "TODOS"
        },
        "LOGISTICA.LABEST": {
            "senha_hash": gerar_hash_senha("123"),
            "logo": "logo_labest.png",
            "filtro": "LABEST",
            "tomador": "LABEST"
        },
        "DANILO.DUARTE": {
            "senha_hash": gerar_hash_senha("123"),
            "logo": "logo_labest.png",
            "filtro": "LABEST",
            "tomador": "LABEST"
        },
        "SYNVIA": {
            "senha_hash": gerar_hash_senha("123"),
            "logo": LOGO_IGO,
            "filtro": "SYNVIA",
            "tomador": "SYNVIA"
        },
        "LOGISTICA.BAT": {
            "senha_hash": gerar_hash_senha("123"),
            "logo": "souza cruz.png",
            "filtro": "SOUZA CRUZ",
            "tomador": "SOUZA CRUZ"
        }
    }


def montar_config_portal_cliente(senha_hash, tomador):
    tomador_norm = normalizar_tomador_portal(tomador)
    return {
        "senha_hash": str(senha_hash).strip(),
        "logo": obter_logo_por_tomador(tomador_norm),
        "filtro": tomador_norm,
        "tomador": tomador_norm,
    }


def carregar_usuarios_portal_cliente():
    usuarios = {}

    planilha = abrir_planilha_login_portal()
    if planilha:
        try:
            aba = planilha.worksheet(NOME_ABA_LOGIN_PORTAL)
            dados = aba.get_all_values()
            if len(dados) > 1:
                cabecalhos = [str(c).strip().upper() for c in dados[0]]
                idx_usuario = cabecalhos.index("USUARIO")
                idx_senha = cabecalhos.index("SENHA_HASH")
                idx_tomador = cabecalhos.index("TOMADOR")

                for linha in dados[1:]:
                    usuario = normalizar_usuario_login(linha[idx_usuario] if idx_usuario < len(linha) else "")
                    senha_hash = str(linha[idx_senha] if idx_senha < len(linha) else "").strip()
                    tomador = normalizar_tomador_portal(linha[idx_tomador] if idx_tomador < len(linha) else "TODOS")
                    if usuario and senha_hash:
                        usuarios[usuario] = montar_config_portal_cliente(senha_hash, tomador)
        except Exception:
            usuarios = {}

    if not usuarios and os.path.exists(ARQUIVO_PORTAL_CLIENTE_LOGIN):
        try:
            with open(ARQUIVO_PORTAL_CLIENTE_LOGIN, "r", encoding="utf-8") as f:
                dados = json.load(f)
            if isinstance(dados, dict):
                for usuario, info in dados.items():
                    user_norm = normalizar_usuario_login(usuario)
                    if not user_norm:
                        continue
                    if isinstance(info, dict):
                        senha_hash = str(info.get("senha_hash", "")).strip()
                        logo = str(info.get("logo", LOGO_IGO)).strip() or LOGO_IGO
                        filtro = str(info.get("filtro", "TODOS")).strip().upper() or "TODOS"
                        tomador = str(info.get("tomador", filtro)).strip().upper() or filtro
                    else:
                        senha_hash = gerar_hash_senha(str(info))
                        logo = LOGO_IGO
                        filtro = "TODOS"
                        tomador = "TODOS"
                    if senha_hash:
                        usuarios[user_norm] = montar_config_portal_cliente(senha_hash, tomador)
        except Exception:
            usuarios = {}
    if not usuarios:
        usuarios = usuarios_padrao_portal_cliente()
        with open(ARQUIVO_PORTAL_CLIENTE_LOGIN, "w", encoding="utf-8") as f:
            json.dump(usuarios, f, ensure_ascii=False, indent=2)
    return usuarios


def salvar_usuarios_portal_cliente(usuarios):
    with open(ARQUIVO_PORTAL_CLIENTE_LOGIN, "w", encoding="utf-8") as f:
        json.dump(usuarios, f, ensure_ascii=False, indent=2)


def obter_logo_por_tomador(tomador):
    tomador_norm = str(tomador).strip().upper()
    tomador_norm = tomador_norm.replace("CAEP", "SYNVIA").replace("CUNHA", "GRALAB")
    return LOGOS_POR_TOMADOR.get(tomador_norm, LOGO_IGO)

# =======================================================
# 🎨 1. CONFIGURAÇÃO DA PÁGINA E CSS BASE DO DASHBOARD
# =======================================================
st.set_page_config(
    page_title="Monitoramento IGO Logística",
    layout="wide",
    page_icon="🚚",
    initial_sidebar_state="expanded"
)

# CSS do Dashboard
CSS_DASHBOARD = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    :root {
        --igo-bg-soft: #f3f7ff;
        --igo-surface: #ffffff;
        --igo-surface-2: #f8fbff;
        --igo-line: #dbe3ef;
        --igo-text: #0f172a;
        --igo-muted: #64748b;
        --igo-brand: #2563eb;
        --igo-brand-2: #1d4ed8;
        --igo-shadow-lg: 0 14px 34px rgba(15, 23, 42, 0.11);
    }
    [data-testid="stAppViewContainer"] {
        transition: background-color 0.3s ease;
        font-family: 'Inter', sans-serif;
        background: #fafbfc !important;
        padding-left: 0.3rem !important;
        padding-right: 0.3rem !important;
    }
    [data-testid="stAppViewContainer"] [data-testid="stVerticalBlockBorderWrapper"] {
        gap: 3px !important;
    }
    [data-testid="stAppViewContainer"] [data-testid="stColumn"] {
        padding-left: 1px !important;
        padding-right: 1px !important;
    }
    [data-testid="stAppViewContainer"] .st-gl {
        gap: 0.3rem !important;
    }
    [data-testid="stAppViewContainer"] [data-testid="stElementContainer"] {
        padding-left: 0px !important;
        padding-right: 0px !important;
    }

    [data-testid="stApp"] {
        color: var(--igo-text);
    }

    /* ── SIDEBAR ── */
    [data-testid="stSidebar"],
    [data-testid="stSidebar"] > div:first-child {
        background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%) !important;
        border-right: 1px solid #dbe3ef !important;
        padding: 12px 8px !important;
        overflow-y: auto !important;
        overflow-x: hidden !important;
        max-height: 100vh !important;
    }
    [data-testid="stSidebar"] > div:first-child > div {
        gap: 0px !important;
        overflow: visible !important;
    }

    /* Sidebar com rolagem vertical visivel */
    [data-testid="stSidebar"] {
        scrollbar-width: auto !important;
    }
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] h3 {
        color: #1e293b !important;
    }
    [data-testid="stSidebar"] .sidebar-premium-shell {
        background: linear-gradient(145deg, #0f172a 0%, #1e293b 58%, #334155 100%);
        border-radius: 16px;
        padding: 12px 12px 10px 12px;
        margin-bottom: 10px;
        box-shadow: 0 8px 20px rgba(15, 23, 42, 0.12);
        border: 1px solid rgba(148, 163, 184, 0.22);
    }
    [data-testid="stSidebar"] .sidebar-premium-kicker {
        font-size: 11px;
        font-weight: 800;
        letter-spacing: 1.2px;
        text-transform: uppercase;
        color: #93c5fd;
        margin-bottom: 4px;
    }
    [data-testid="stSidebar"] .sidebar-premium-title {
        font-size: 18px;
        font-weight: 900;
        color: #f8fafc;
        line-height: 1.1;
        margin-bottom: 4px;
    }
    [data-testid="stSidebar"] .sidebar-premium-subtitle {
        font-size: 12px;
        color: #cbd5e1;
        line-height: 1.4;
    }
    [data-testid="stSidebar"] [data-testid="stForm"] {
        background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%) !important;
        border: 1px solid #dbe3ef !important;
        border-radius: 12px !important;
        padding: 10px !important;
        box-shadow: 0 3px 8px rgba(15, 23, 42, 0.03) !important;
    }
    [data-testid="stSidebar"] section > div {
        background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%) !important;
        border-radius: 12px !important;
        padding: 10px !important;
        margin-bottom: 6px !important;
        border: 1px solid #e2e8f0 !important;
        box-shadow: 0 2px 6px rgba(15, 23, 42, 0.02) !important;
    }
    [data-testid="stSidebar"] [data-testid="stForm"] input,
    [data-testid="stSidebar"] [data-testid="stForm"] textarea {
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 6px !important;
        color: #1e293b !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
    }
    [data-testid="stSidebar"] [data-testid="stForm"] input:focus,
    [data-testid="stSidebar"] [data-testid="stForm"] textarea:focus {
        border-color: #3b82f6 !important;
        box-shadow: 0 0 0 1px #3b82f6 !important;
    }
    [data-testid="stSidebar"] [data-testid="stContainer"] {
        gap: 0px !important;
    }
    [data-testid="stSidebar"] .st-gl, [data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] {
        gap: 0px !important;
    }
    [data-testid="stSidebar"] .stSpacer {
        display: none !important;
    }
    [data-testid="stSidebar"] .stButton > button,
    [data-testid="stSidebar"] [data-testid="stFormSubmitButton"] > button {
        border-radius: 8px !important;
        border: 1px solid #93c5fd !important;
        background: linear-gradient(180deg, #eff6ff 0%, #dbeafe 100%) !important;
        color: #0f172a !important;
        font-weight: 700 !important;
        box-shadow: 0 2px 6px rgba(37, 99, 235, 0.08) !important;
        transition: all 0.2s ease !important;
        min-height: 36px !important;
    }
    [data-testid="stSidebar"] .stButton > button:hover,
    [data-testid="stSidebar"] [data-testid="stFormSubmitButton"] > button:hover {
        transform: translateY(-1px) !important;
        border-color: #60a5fa !important;
        background: linear-gradient(180deg, #dbeafe 0%, #bfdbfe 100%) !important;
        box-shadow: 0 8px 18px rgba(37, 99, 235, 0.18) !important;
    }
    [data-testid="stSidebar"] .stPopover button {
        border-radius: 10px !important;
    }
    [data-testid="stSidebar"] .stDateInput input,
    [data-testid="stSidebar"] .stDateInput button,
    [data-testid="stSidebar"] .stDateInput [role="button"] {
        border-radius: 10px !important;
        border: 1px solid #cbd5e1 !important;
        background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%) !important;
        color: #0f172a !important;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05) !important;
    }
    [data-testid="stSidebar"] .stDateInput input:focus {
        border-color: #93c5fd !important;
        box-shadow: 0 0 0 1px #93c5fd !important;
    }
    [data-testid="stSidebar"] [data-baseweb="popover"] {
        border-radius: 14px !important;
        overflow: hidden !important;
        box-shadow: 0 18px 40px rgba(15, 23, 42, 0.18) !important;
    }

    .status-online-chip {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
        border: 1px solid #bbf7d0;
        background: linear-gradient(180deg, #f0fdf4 0%, #dcfce7 100%);
        border-radius: 10px;
        padding: 8px 10px;
        margin: 4px 0 8px 0;
    }
    .status-online-left {
        display: flex;
        align-items: center;
        gap: 6px;
        min-width: 0;
    }
    .status-online-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #22c55e;
        box-shadow: 0 0 0 3px rgba(34, 197, 94, 0.18);
    }
    .status-online-text {
        font-size: 11px;
        font-weight: 800;
        color: #166534;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        white-space: nowrap;
    }
    .status-online-time {
        font-size: 11px;
        font-weight: 700;
        color: #14532d;
        white-space: nowrap;
    }

    /* ── LAYOUT ── */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {background-color: transparent !important;}
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
        display: block !important;
        max-width: 100%;
    }

    .kpi-deck-shell {
        background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
        border: 1px solid rgba(203, 213, 225, 0.6);
        border-radius: 12px;
        padding: 12px 12px 8px 12px;
        box-shadow: 0 6px 20px rgba(15, 23, 42, 0.05), inset 0 1px 0 rgba(255,255,255,0.95);
        margin-bottom: 3px;
        backdrop-filter: blur(8px);
    }

    .toolbar-shell {
        background: linear-gradient(180deg, #f9fafb 0%, #f3f4f6 100%);
        border: 1px solid rgba(203, 213, 225, 0.5);
        border-radius: 12px;
        padding: 8px 10px;
        box-shadow: 0 4px 12px rgba(15, 23, 42, 0.04), inset 0 1px 0 rgba(255,255,255,0.95);
        margin-bottom: 3px;
        backdrop-filter: blur(8px);
    }

    .section-kicker {
        font-size: 10px;
        font-weight: 800;
        color: #64748b;
        letter-spacing: 0.8px;
        text-transform: uppercase;
        margin-bottom: 4px;
        margin-top: 6px;
    }

    /* ── KPI CARDS ── */
    .kpi-card {
        border-radius: 12px;
        padding: 16px 18px;
        text-align: left;
        cursor: pointer;
        transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
        position: relative;
        overflow: hidden;
        min-height: 102px;
        backdrop-filter: blur(8px);
        border: 1.5px solid rgba(203, 213, 225, 0.5);
        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08), inset 0 1px 0 rgba(255,255,255,0.8);
    }
    .kpi-card::after {
        content: "";
        position: absolute;
        width: 100%;
        height: 100%;
        top: 0;
        left: 0;
        background: radial-gradient(circle at 120% -20%, rgba(255,255,255,0.6) 0%, rgba(255,255,255,0) 70%);
        filter: blur(20px);
        pointer-events: none;
        border-radius: 12px;
    }
    .kpi-card::before {
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 2px;
        background: linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.7) 50%, rgba(255,255,255,0) 100%);
        border-radius: 12px 12px 0 0;
    }
    .kpi-card:hover {
        box-shadow: 0 16px 40px rgba(15, 23, 42, 0.15), inset 0 1px 0 rgba(255,255,255,0.9);
        transform: translateY(-6px);
        border-color: rgba(203, 213, 225, 0.8);
        filter: brightness(1.08) saturate(1.1);
    }
    .kpi-card:active {
        transform: translateY(-3px);
        box-shadow: 0 12px 24px rgba(15, 23, 42, 0.12), inset 0 1px 0 rgba(255,255,255,0.8);
    }

    /* ── HEADER ── */
    .header-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 6px;
        padding: 12px 14px;
        border: 1px solid rgba(203, 213, 225, 0.6);
        border-radius: 12px;
        background: linear-gradient(135deg, #f0f9ff 0%, #f1f5f9 100%);
        box-shadow: 0 6px 20px rgba(15, 23, 42, 0.05), inset 0 1px 0 rgba(255,255,255,0.95);
        backdrop-filter: blur(8px);
    }
    .header-title {
        font-size: 20px;
        font-weight: 700;
        color: #0f172a;
        letter-spacing: -0.4px;
        margin: 0;
    }
    .header-subtitle {
        font-size: 11px;
        color: var(--igo-muted);
        margin-top: 2px;
        font-weight: 600;
        letter-spacing: 0.3px;
        text-transform: uppercase;
    }
    .sync-status {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 12px;
        color: #166534;
        font-weight: 600;
        background: linear-gradient(135deg, rgba(240, 253, 244, 0.99) 0%, rgba(220, 252, 231, 0.98) 100%);
        border: 1px solid rgba(132, 204, 22, 0.3);
        border-radius: 8px;
        padding: 6px 12px;
        box-shadow: 0 4px 12px rgba(34, 197, 94, 0.08), inset 0 1px 0 rgba(255,255,255,0.8);
        backdrop-filter: blur(10px);
    }
    .sync-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: #22c55e;
        box-shadow: none;
        animation: none;
    }
    
    /* ── PROGRESS BAR ── */
    .progress-block {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 12px 16px;
        margin: 4px 0 8px;
    }
    .progress-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
    }
    .progress-title {
        font-size: 12px;
        font-weight: 600;
        color: #475569;
    }
    .progress-pct {
        font-size: 12px;
        font-weight: 700;
        color: #0f172a;
    }
    .progress-bar-bg {
        height: 6px;
        background: #f1f5f9;
        border-radius: 99px;
        overflow: hidden;
    }

    /* ── PROGRESS BLOCK SIDEBAR ── */
    .progress-block-sidebar {
        background: linear-gradient(135deg, #ffffff 0%, #f8fafc 52%, #eff6ff 100%);
        border: 1px solid #bfdbfe;
        border-radius: 16px;
        padding: 14px;
        margin: 8px 0;
        overflow: hidden;
        box-shadow: 0 12px 26px rgba(37, 99, 235, 0.16);
    }
    .progress-block-sidebar-content {
        position: relative;
        z-index: 1;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 10px;
    }
    .progress-title-sidebar {
        font-size: 12px;
        font-weight: 700;
        color: #0f172a;
    }
    .progress-number-sidebar {
        font-size: 42px;
        font-weight: 900;
        color: #0f172a;
        line-height: 1;
    }
    .progress-bars-container {
        display: flex;
        gap: 8px;
        align-items: flex-end;
        justify-content: center;
        height: 120px;
    }
    .progress-bar-wifi {
        width: 12px;
        border-radius: 4px 4px 0 0;
        transition: all 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
        opacity: 0.3;
        background: #cbd5e1;
    }
    .progress-bar-wifi.active-1 { height: 24px; opacity: 1; background: #ef4444; }
    .progress-bar-wifi.active-2 { height: 40px; opacity: 1; background: #f59e0b; }
    .progress-bar-wifi.active-3 { height: 56px; opacity: 1; background: #f59e0b; }
    .progress-bar-wifi.active-4 { height: 80px; opacity: 1; background: #22c55e; }
    .progress-bar-wifi.active-5 { height: 100px; opacity: 1; background: #22c55e; }
    .progress-text-sidebar {
        font-size: 12px;
        color: #475569;
        font-weight: 500;
    }
    
    /* ── PROGRESS STATUS BOX ── */
    .progress-status-box {
        padding: 10px 14px;
        border-radius: 12px;
        text-align: center;
        transition: all 0.4s ease;
        font-weight: 700;
        margin-top: 6px;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 4px;
        border: 2px solid;
    }
    .progress-status-box.low {
        background: #fee2e2;
        color: #991b1b;
        border-color: #fca5a5;
        box-shadow: 0 4px 12px rgba(239, 68, 68, 0.15);
    }
    .progress-status-box.medium {
        background: #fef3c7;
        color: #92400e;
        border-color: #fcd34d;
        box-shadow: 0 4px 12px rgba(245, 158, 11, 0.15);
    }
    .progress-status-box.high {
        background: #dcfce7;
        color: #166534;
        border-color: #86efac;
        box-shadow: 0 4px 12px rgba(34, 197, 94, 0.15);
    }
    .progress-status-number {
        font-size: 26px;
        line-height: 1;
    }
    .progress-status-label {
        font-size: 10px;
        opacity: 0.9;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    [data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 14px !important;
        border: 1px solid #dbe3ef !important;
        background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%) !important;
        box-shadow: 0 8px 18px rgba(15, 23, 42, 0.08) !important;
    }

    [data-baseweb="tab-list"] {
        background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
        border: 1px solid rgba(203, 213, 225, 0.6);
        border-radius: 12px;
        padding: 4px;
        box-shadow: 0 4px 12px rgba(15, 23, 42, 0.04), inset 0 1px 0 rgba(255,255,255,0.95);
        margin-bottom: 4px !important;
        backdrop-filter: blur(8px);
    }

    button[role="tab"] {
        border-radius: 8px !important;
        font-weight: 600 !important;
        min-height: 32px !important;
        font-size: 13px !important;
        transition: all 0.3s ease !important;
    }

    button[role="tab"][aria-selected="true"] {
        background: linear-gradient(135deg, #ffffff 0%, #eff6ff 100%) !important;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.12), inset 0 1px 0 rgba(255,255,255,0.8) !important;
        color: #1d4ed8 !important;
        font-weight: 700 !important;
    }

    @media (max-width: 980px) {
        .header-container {
            flex-direction: column;
            align-items: flex-start;
            gap: 10px;
        }
        .kpi-card {
            min-height: 92px;
            padding: 14px;
        }
    }

    /* ── SCROLL NATURAL DA TELA ── */
    html, body, [data-testid="stAppViewContainer"], [data-testid="stAppViewMain"] {
        overflow-y: auto !important;
        overflow-x: hidden !important;
        max-height: none !important;
        height: auto !important;
    }

    .block-container {
        min-height: 100vh !important;
        height: auto !important;
        max-height: none !important;
        display: flex !important;
        flex-direction: column !important;
        padding-top: 0.5rem !important; 
        padding-bottom: 0.5rem !important;
        overflow: visible !important;
    }

    @media (max-width: 768px) {
        .block-container {
            min-height: 100vh !important;
            padding: 0.45rem 0.65rem 0.85rem !important;
            max-width: 100% !important;
        }

        .header-container {
            align-items: flex-start;
            flex-direction: column;
            gap: 8px;
            padding: 10px;
            margin-bottom: 6px;
        }

        .header-title {
            font-size: 17px;
        }

        .header-subtitle {
            font-size: 10px;
            line-height: 1.35;
        }

        .sync-status {
            flex-wrap: wrap;
            width: 100%;
            justify-content: space-between;
            padding: 6px 9px;
        }

        div[data-testid="stHorizontalBlock"] {
            flex-wrap: wrap !important;
            gap: 0.6rem !important;
        }

        div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
            flex: 1 1 calc(50% - 0.6rem) !important;
            min-width: calc(50% - 0.6rem) !important;
        }

        .kpi-deck-shell {
            padding: 8px 7px 5px;
            border-radius: 10px;
        }

        .kpi-card {
            min-height: 78px;
            padding: 11px 12px;
        }

        .kpi-card > div:first-of-type {
            font-size: 10px !important;
        }

        .kpi-card > div:last-of-type {
            font-size: 24px !important;
        }

        div.st-key-kpi_total,
        div.st-key-kpi_entregue,
        div.st-key-kpi_frus,
        div.st-key-kpi_coletado,
        div.st-key-kpi_pend,
        div.st-key-kpi_aguardando,
        div.st-key-kpi_hoje {
            margin-top: -82px !important;
        }

        div.st-key-kpi_total button,
        div.st-key-kpi_entregue button,
        div.st-key-kpi_frus button,
        div.st-key-kpi_coletado button,
        div.st-key-kpi_pend button,
        div.st-key-kpi_aguardando button,
        div.st-key-kpi_hoje button {
            height: 78px !important;
        }

        .toolbar-shell {
            padding: 7px;
            border-radius: 10px;
        }

        .toolbar-shell div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:first-child {
            flex: 1 1 100% !important;
            min-width: 100% !important;
        }

        .toolbar-shell div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-child(n+2) {
            flex: 1 1 calc(33.333% - 0.6rem) !important;
            min-width: calc(33.333% - 0.6rem) !important;
        }

        .toolbar-shell div.stButton > button {
            min-height: 42px !important;
            padding-left: 5px !important;
            padding-right: 5px !important;
        }

        div.stButton > button,
        div[data-testid="stFormSubmitButton"] > button {
            min-height: 44px !important;
            white-space: normal !important;
            line-height: 1.2 !important;
        }

        [data-testid="stTabs"] [data-baseweb="tab-list"] {
            overflow-x: auto !important;
            scrollbar-width: thin;
        }

        [data-testid="stTabs"] button[role="tab"] {
            flex: 0 0 auto !important;
            min-height: 36px !important;
            font-size: 11px !important;
            padding: 0 10px !important;
        }

        .ag-theme-alpine {
            min-height: 360px !important;
            width: 100% !important;
            max-width: 100% !important;
            border-radius: 10px !important;
        }

        .ag-theme-alpine .ag-header-cell-text,
        .ag-theme-alpine .ag-cell {
            font-size: 12px !important;
        }

        .ag-theme-alpine .ag-row {
            min-height: 42px !important;
        }

        .progress-block-sidebar {
            padding: 11px;
            border-radius: 12px;
        }

        [data-testid="stDataFrame"],
        [data-testid="stTable"] {
            overflow-x: auto !important;
        }
    }

    [data-testid="stTabs"] {
        display: flex;
        flex-direction: column;
        flex-grow: 1;
        overflow: hidden;
    }

    [data-testid="stTabView"] {
        flex-grow: 1;
        display: flex;
        flex-direction: column;
        overflow: hidden !important;
        padding-bottom: 0 !important;
    }

    .ag-theme-alpine {
        height: 100% !important;
        min-height: 400px; 
        display: flex;
        flex-direction: column;
    }

    /* ── AJUSTE DE ENQUADRAMENTO DO BLOCO DE PROGRESSO + LOGOUT ── */
    div.st-key-btn_logout_sidebar {
        position: static !important;
        margin-top: 10px !important;
        width: 100% !important;
    }

    /* ── BOTÕES DA BARRA DA GRID (BUSCAR + CSV) ── */
    .st-key-btn_busca_grid button,
    .st-key-btn_download_grid_limpo button {
        background: linear-gradient(180deg, #60a5fa 0%, #3b82f6 100%) !important;
        border: 1px solid #2563eb !important;
        border-radius: 10px !important;
        transition: all 0.2s ease !important;
    }
    .st-key-btn_busca_grid button p,
    .st-key-btn_download_grid_limpo button p {
        color: #ffffff !important;
        font-weight: 700 !important;
    }
    .st-key-btn_busca_grid button:hover,
    .st-key-btn_download_grid_limpo button:hover {
        background: linear-gradient(180deg, #3b82f6 0%, #2563eb 100%) !important;
        border-color: #1d4ed8 !important;
        box-shadow: 0 8px 18px rgba(37, 99, 235, 0.28) !important;
        transform: translateY(-1px) !important;
    }

    .st-key-btn_refresh_grid button {
        background: linear-gradient(180deg, #f8fafc 0%, #e2e8f0 100%) !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 999px !important;
        color: #475569 !important;
        font-weight: 800 !important;
        min-height: 38px !important;
        transition: all 0.2s ease !important;
    }
    .st-key-btn_refresh_grid button:hover {
        background: linear-gradient(180deg, #eef2f7 0%, #dbe3ef 100%) !important;
        border-color: #94a3b8 !important;
        color: #334155 !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 14px rgba(15, 23, 42, 0.12) !important;
    }

    /* ── BOTÃO DE FECHAR DETALHES (VERMELHO) ── */
    .st-key-fechar_detalhes_btn button {
        background: linear-gradient(180deg, #ef4444 0%, #dc2626 100%) !important;
        border: 1px solid #b91c1c !important;
        transition: all 0.2s ease !important;
    }
    .st-key-fechar_detalhes_btn button p {
        color: #ffffff !important;
        font-weight: 700 !important;
    }
    .st-key-fechar_detalhes_btn button:hover {
        background: linear-gradient(180deg, #dc2626 0%, #991b1b 100%) !important;
        border-color: #7f1d1d !important;
        box-shadow: 0 4px 12px rgba(220, 38, 38, 0.4) !important;
        transform: translateY(-1px) !important;
    }
    </style>
"""

CLIENTES_CONFIG = carregar_usuarios_portal_cliente()


def normalizar_chave_cliente(valor):
    """Normaliza e valida a chave de cliente usada na autenticação/sessão."""
    if valor is None:
        return None
    chave = str(valor).strip().upper()
    return chave if chave in CLIENTES_CONFIG else None

# =======================================================
# 🔗 2. MOTOR DE DADOS
# =======================================================
@st.cache_resource
def conectar_banco_seguro():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    try:
        token_str = os.environ.get("google_token_json")
        if not token_str:
            try:
                token_str = st.secrets.get("google_token_json")
            except Exception:
                pass
        if not token_str:
            return None
        token_info = json.loads(token_str)
        creds = Credentials.from_authorized_user_info(token_info, scopes=scopes)
        return gspread.authorize(creds)
    except Exception as e:
        st.warning(f"Erro ao conectar ao banco: {e}")
        return None

# =======================================================
# ✅ FOTO_COLETA e FOTO_ENTREGA são copiadas automaticamente pelo Apps Script
# Aqui apenas lemos os valores de App_Tarefas

@st.cache_data(ttl=43200) # Cache de 12 horas para a tabela de Agentes (economiza muita cota)
def carregar_agentes_nuvem():
    try:
        gc = conectar_banco_seguro()
        if not gc: return {}
        planilha = gc.open("DB_IGO_Logistica")
        aba_agentes = planilha.worksheet("Agentes")
        dados_agentes = aba_agentes.get_all_values()
        if len(dados_agentes) > 1:
            df_ag = pd.DataFrame(dados_agentes[1:], columns=dados_agentes[0])
            df_ag.columns = [str(c).upper().strip() for c in df_ag.columns]
            
            id_col = next((c for c in df_ag.columns if any(x in c for x in ['ID', 'USUARIO', 'EMAIL', 'LOGIN'])), df_ag.columns[0])
            nome_col = next((c for c in df_ag.columns if 'NOME' in c), df_ag.columns[1])
            
            return dict(zip(df_ag[id_col].astype(str).str.strip().str.lower(), df_ag[nome_col].astype(str).str.strip()))
    except Exception:
        pass
    return {}

@st.cache_data(ttl=180) # 🔥 Aumentado para 3 minutos: Evita baixar tudo de novo só porque o usuário demorou lendo o popup
def carregar_dados_nuvem(cliente_filtro):
    try:
        gc = conectar_banco_seguro()
        if not gc:
            return pd.DataFrame()
        
        planilha = gc.open("DB_IGO_Logistica")
        
        # 1. Carregar Agentes para mapeamento usando a função cacheada
        dict_agentes = carregar_agentes_nuvem()

        aba_m = planilha.worksheet("Memoria_Sistema")
        
        # =======================================================
        # 🚀 OTIMIZAÇÃO GVIZ API (FILTRO NO SERVIDOR DO GOOGLE)
        # =======================================================
        df = pd.DataFrame()
        cabecalhos = aba_m.row_values(1)
        
        try:
            # Descobre a letra da coluna TOMADOR (ex: 3 -> C)
            idx_tomador = cabecalhos.index("TOMADOR") + 1
            def col_num_to_letter(n):
                letra = ""
                while n > 0:
                    n, rem = divmod(n - 1, 26)
                    letra = chr(65 + rem) + letra
                return letra
            
            col_letra = col_num_to_letter(idx_tomador)
            
            # Monta a instrução SQL para enviar ao Google (Com UPPER para evitar erros de maiúsculas)
            if cliente_filtro == "TODOS":
                query = "SELECT *"
            elif cliente_filtro == "LABEST":
                query = f"SELECT * WHERE UPPER({col_letra}) = 'LABEST' OR UPPER({col_letra}) = 'UNILABOR'"
            else:
                query = f"SELECT * WHERE UPPER({col_letra}) = '{cliente_filtro.upper()}'"
                
            query_encoded = urllib.parse.quote(query)
            url = f"https://docs.google.com/spreadsheets/d/{planilha.id}/gviz/tq?tqx=out:csv&gid={aba_m.id}&tq={query_encoded}"
            
            request_auth = google.auth.transport.requests.Request()
            gc.auth.refresh(request_auth)
            
            headers = {"Authorization": f"Bearer {gc.auth.token}"}
            # Adicionado timeout de 15 segundos para evitar travamento do Streamlit
            resposta = requests.get(url, headers=headers, timeout=15)
            
            if resposta.status_code == 200:
                df = pd.read_csv(io.StringIO(resposta.text), dtype=str)
                df.columns = df.columns.str.strip().str.upper()
            else:
                raise Exception("Falha na API GViz")
                
        except Exception as e:
            # 🛟 MODO DE SEGURANÇA: Se a API falhar, recua para o método antigo
            dados_m = aba_m.get_all_values()
            if len(dados_m) > 1:
                df = pd.DataFrame(dados_m[1:], columns=dados_m[0])
                df.columns = df.columns.str.strip().str.upper()

        if not df.empty:
            df = df.loc[:, ~df.columns.duplicated()]

            # 🧹 HIGIENIZAÇÃO DE DADOS OFICIAL
            if 'TOMADOR' in df.columns:
                df['TOMADOR'] = df['TOMADOR'].str.replace('CAEP', 'SYNVIA').str.replace('CUNHA', 'GRALAB')
            if 'CIDADE' in df.columns:
                df['CIDADE'] = df['CIDADE'].str.replace('Brodosqui', 'Brodowski', case=False).str.replace('BRODOSQUI', 'BRODOWSKI')

            try:
                aba_app = planilha.worksheet("App_Tarefas")
                dados_app = aba_app.get_all_values()
                
                if len(dados_app) > 1:
                    df_app = pd.DataFrame(dados_app[1:], columns=dados_app[0])
                    df_app.columns = [
                        str(c).upper().strip().replace(' ', '').replace('?', '')
                        for c in df_app.columns
                    ]

                    cols_to_extract = ['PEDIDO']
                    if 'STATUS'       in df_app.columns: cols_to_extract.append('STATUS')
                    if 'OBSERVACOES'  in df_app.columns: cols_to_extract.append('OBSERVACOES')
                    if 'FOTO'         in df_app.columns: cols_to_extract.append('FOTO')
                    if 'FOTO_COLETA'  in df_app.columns: cols_to_extract.append('FOTO_COLETA')
                    if 'FOTO_ENTREGA' in df_app.columns: cols_to_extract.append('FOTO_ENTREGA')
                    if 'DATA'         in df_app.columns: cols_to_extract.append('DATA')
                    if 'DATA_ENTREGA' in df_app.columns: cols_to_extract.append('DATA_ENTREGA')
                    if 'RECEBEDOR'    in df_app.columns: cols_to_extract.append('RECEBEDOR')
                    if 'HORA_STATUS'  in df_app.columns: cols_to_extract.append('HORA_STATUS')
                    if 'HORA_COLETA'  in df_app.columns: cols_to_extract.append('HORA_COLETA')
                    if 'HORA_ENTREGA' in df_app.columns: cols_to_extract.append('HORA_ENTREGA')
                    
                    # Identificar coluna de motorista (flexível)
                    col_mot = None
                    for c in ['MOTORISTA', 'USUARIO', 'EMAIL', 'AGENTE', 'CONDUTOR', 'NOME_MOTORISTA']:
                        if c in df_app.columns:
                            col_mot = c
                            cols_to_extract.append(col_mot)
                            break

                    # Identificar coluna de contato
                    col_nome = None
                    for c in ['DETALHES', 'CONTATO', 'NOME', 'PESSOA', 'INFORMANTE']:
                        if c in df_app.columns:
                            col_nome = c
                            cols_to_extract.append(col_nome)
                            break
                    
                    cols_to_extract = list(set(cols_to_extract))
                    df_app_clean = df_app[cols_to_extract].copy()

                    rename_dict = {
                        'STATUS': 'A_ST',
                        'OBSERVACOES': 'A_OB',
                        'FOTO': 'A_FO',
                        'FOTO_COLETA': 'A_FOTO_COL',
                        'FOTO_ENTREGA': 'A_FOTO_ENT',
                        'DATA': 'A_DT',
                        'DATA_ENTREGA': 'A_DT_ENTREGA',
                        'RECEBEDOR': 'A_REC',
                        'HORA_STATUS': 'A_HORA_STATUS',
                        'HORA_COLETA': 'A_HORA_COLETA',
                        'HORA_ENTREGA': 'A_HORA_ENTREGA'
                    }
                    if col_nome: rename_dict[col_nome] = 'A_CONTATO'
                    if col_mot: rename_dict[col_mot] = 'A_MOTORISTA'
                        
                    df_app_clean.rename(columns=rename_dict, inplace=True)

                    # 🔥 LÓGICA DE MOTORISTA DUPLO (COLETA VS ENTREGA) 🔥
                    if 'A_MOTORISTA' in df_app_clean.columns:
                        coleta_mask = df_app_clean['A_ST'].str.contains('COLETADO', case=False, na=False)
                        entrega_mask = df_app_clean['A_ST'].str.contains('ENTREGUE|CONFERIDO', case=False, na=False)
                        
                        mot_coleta_dict = df_app_clean[coleta_mask].set_index('PEDIDO')['A_MOTORISTA'].to_dict()
                        mot_entrega_dict = df_app_clean[entrega_mask].set_index('PEDIDO')['A_MOTORISTA'].to_dict()
                    else:
                        mot_coleta_dict = {}
                        mot_entrega_dict = {}

                    rom_mask = df_app_clean['PEDIDO'].str.startswith('ROM-', na=False)
                    rom_dict = df_app_clean[rom_mask].set_index('PEDIDO').to_dict('index')

                    df_app_clean.drop_duplicates(subset=['PEDIDO'], keep='last', inplace=True)

                    df['PEDIDO'] = df['PEDIDO'].astype(str).str.strip()
                    df = pd.merge(df, df_app_clean, on='PEDIDO', how='left')

                    df['MOTORISTA_COLETA_ID'] = df['PEDIDO'].map(mot_coleta_dict).fillna(df['A_MOTORISTA'] if 'A_MOTORISTA' in df.columns else '')
                    df['MOTORISTA_ENTREGA_ID'] = df['PEDIDO'].map(mot_entrega_dict).fillna('')

                    # Tradutor de IDs para Nomes Reais (Aba Agentes)
                    def traduzir_agente(ag_id):
                        if not ag_id or str(ag_id).upper() == 'NAN': return ""
                        ag_clean = str(ag_id).strip().lower()
                        return dict_agentes.get(ag_clean, str(ag_id).strip())

                    df['MOTORISTA_COLETA'] = df['MOTORISTA_COLETA_ID'].apply(traduzir_agente)
                    df['MOTORISTA_ENTREGA'] = df['MOTORISTA_ENTREGA_ID'].apply(traduzir_agente)

                    def get_app_val(row, col_app):
                        val = str(row.get(col_app, '')).strip()
                        rom_id = str(row.get('ROMANEIO', '')).strip()
                        if rom_id in rom_dict:
                            rom_val = str(rom_dict[rom_id].get(col_app, '')).strip()
                            if rom_val and rom_val.upper() != 'NAN':
                                return rom_val
                        return val if val.upper() != 'NAN' else ""

                    df['RECEBEDOR_FINAL'] = df.apply(lambda r: get_app_val(r, 'A_REC'), axis=1)
                    df['OBS_APP_FINAL']   = df.apply(lambda r: get_app_val(r, 'A_OB'), axis=1)
                    df['CONTATO_FINAL']   = df.apply(lambda r: get_app_val(r, 'A_CONTATO'), axis=1)
                    df['HORA_APP_FINAL']  = df.apply(lambda r: get_app_val(r, 'A_HORA_STATUS'), axis=1)

                    # Restaurando a função pois o get_app_hora ainda precisa dela
                    def extrair_hora(hora_str):
                        h = str(hora_str).strip()
                        if not h or h.upper() == 'NAN': return ""
                        if " " in h: h = h.split(" ")[-1]
                        parts = h.split(":")
                        if len(parts) >= 2: return f"{parts[0].zfill(2)}:{parts[1].zfill(2)}"
                        return h

                    # Extração vetorizada super rápida (Regex) para HORA_LIMPA
                    if 'A_HORA_STATUS' in df.columns:
                        df['HORA_LIMPA'] = df['A_HORA_STATUS'].astype(str).str.extract(r'(\d{2}:\d{2})')[0].fillna("")
                    else:
                        df['HORA_LIMPA'] = ""

                    # 🕐 EXTRAÇÃO DE HORAS DE COLETA E ENTREGA
                    def get_app_hora(row, col_hora_app, col_dt_app):
                        """Extrai hora do campo direto ou da coluna de data completa"""
                        h = get_app_val(row, col_hora_app)
                        if h and h.upper() != 'NAN':
                            return extrair_hora(h)
                        
                        # Se não tiver hora, tenta extrair da coluna de data
                        dt_str = get_app_val(row, col_dt_app)
                        if dt_str and dt_str.upper() != 'NAN' and " " in dt_str:
                            partes = dt_str.split(" ")
                            if len(partes) >= 2:
                                return extrair_hora(partes[1])
                        return ""

                    df['HORA_COLETA_REAL'] = df.apply(lambda r: get_app_hora(r, 'A_HORA_COLETA', 'A_DT'), axis=1)
                    df['HORA_ENTREGA_REAL'] = df.apply(lambda r: get_app_hora(r, 'A_HORA_ENTREGA', 'A_DT_ENTREGA'), axis=1)
                    
                    # Se não encontrou hora de entrega, usa HORA_LIMPA (que é extraída do A_HORA_STATUS)
                    df['HORA_ENTREGA_REAL'] = df.apply(
                        lambda r: r['HORA_LIMPA'] if (not r['HORA_ENTREGA_REAL'] or r['HORA_ENTREGA_REAL'] == '') else r['HORA_ENTREGA_REAL'],
                        axis=1
                    )

                    # Tratamento vetorizado das fotos (Instantâneo)
                    for col_foto in ['A_FO', 'A_FOTO_COL', 'A_FOTO_ENT']:
                        if col_foto not in df.columns:
                            df[col_foto] = pd.NA
                        else:
                            df[col_foto] = df[col_foto].astype(str).replace(['NAN', 'nan', '', 'None'], pd.NA)

                    # Foto Final (Prioridade)
                    df['FOTO_FINAL'] = df['A_FO'].combine_first(df['A_FOTO_COL']).combine_first(df['A_FOTO_ENT']).fillna("")
                    
                    # Fotos Separadas
                    df['FOTO_COLETA'] = df['A_FO'].combine_first(df['A_FOTO_COL']).fillna("")
                    df['FOTO_ENTREGA'] = df['A_FOTO_ENT'].fillna("")

                    def get_true_status_portal(row):
                        s_db  = str(row.get('STATUS', '')).strip().upper()
                        s_app = str(row.get('A_ST', '')).strip().upper()
                        rom_id = str(row.get('ROMANEIO', '')).strip()

                        if rom_id in rom_dict:
                            s_rom = str(rom_dict[rom_id].get('A_ST', '')).strip().upper()
                            if s_rom in ['ENTREGUE', 'FRUSTRADA', 'PROBLEMA', 'CANCELADO']:
                                return s_rom

                        if s_db  in ['ENTREGUE', 'CANCELADO', 'FRUSTRADA', 'PROBLEMA']: return s_db
                        if s_app in ['ENTREGUE', 'CANCELADO', 'FRUSTRADA', 'PROBLEMA']: return s_app
                        if s_db  in ['EM ROTA DE ENTREGA', 'CONFERIDO', 'COLETADO']:    return s_db
                        if s_app == 'COLETADO': return s_app
                        if s_app and s_app != 'NAN': return s_app
                        return s_db

                    df['STATUS_RESOLVIDO'] = df.apply(get_true_status_portal, axis=1)

                    def get_true_data_entrega_portal(row):
                        s_final = str(row.get('STATUS_RESOLVIDO', '')).upper()
                        if s_final not in ['ENTREGUE', 'FRUSTRADA']:
                            return "-"

                        d_db   = str(row.get('DATA_ENTREGA', '')).strip()
                        rom_id = str(row.get('ROMANEIO', '')).strip()

                        if rom_id in rom_dict:
                            d_rom = str(rom_dict[rom_id].get('A_DT_ENTREGA', '')).strip()
                            if d_rom and d_rom.upper() != 'NAN':
                                return d_rom

                        if 'A_DT_ENTREGA' in row:
                            d_app = str(row.get('A_DT_ENTREGA', '')).strip()
                            if d_app and d_app.upper() != 'NAN':
                                return d_app

                        return d_db if d_db.upper() != 'NAN' else "-"

                    df['DATA_EFETIVA'] = df.apply(get_true_data_entrega_portal, axis=1)

            except Exception as e:
                st.warning(f"Aviso AppSheet: {e}")
                df['STATUS_RESOLVIDO'] = df['STATUS']
                df['DATA_EFETIVA'] = "-"
                df['HORA_LIMPA'] = "" 
                df['MOTORISTA_COLETA'] = ""
                df['MOTORISTA_ENTREGA'] = ""
                # 🛡️ Fallback: Garante que o painel continue funcionando mesmo sem fotos
                df['FOTO_FINAL'] = ""
                df['FOTO_COLETA'] = ""
                df['FOTO_ENTREGA'] = ""

            if 'DATA' in df.columns:
                # 🔥 CORREÇÃO DA DATA APLICADA AQUI 🔥
                df['DATA_OBJ'] = pd.to_datetime(df['DATA'], dayfirst=True, errors='coerce').dt.date

            # 🔐 BLINDAGEM FINAL: garante isolamento por TOMADOR mesmo em fallback
            if 'TOMADOR' in df.columns and cliente_filtro != "TODOS":
                tomador_norm = (
                    df['TOMADOR']
                    .astype(str)
                    .str.upper()
                    .str.strip()
                    .str.replace(r'\s+', ' ', regex=True)
                )

                if cliente_filtro == "LABEST":
                    tomadores_permitidos = {"LABEST", "UNILABOR"}
                else:
                    tomadores_permitidos = {
                        str(cliente_filtro)
                        .upper()
                        .strip()
                        .replace('  ', ' ')
                    }

                df = df.loc[tomador_norm.isin(tomadores_permitidos)].copy()
            
        return df

    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def carregar_base_locais():
    try:
        gc = conectar_banco_seguro()
        if not gc:
            return pd.DataFrame()
        planilha = gc.open("DB_IGO_Logistica")
        aba = planilha.worksheet("Base_Clientes_Locais")
        dados = aba.get_all_values()
        
        if len(dados) > 1:
            df = pd.DataFrame(dados[1:], columns=dados[0])
            return df[df['STATUS'].str.upper() == 'ATIVO']
        return pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()

def obter_proximo_id(df):
    if df is None or df.empty or 'PEDIDO' not in df.columns:
        return 1
    try:
        nums = df['PEDIDO'].astype(str).str.extract(r'^(\d+)')[0].dropna().astype(int)
        return int(nums.max() + 1) if not nums.empty else 1
    except Exception:
        return 1

def enviar_whatsapp_zapi_cliente(telefone_destino, texto_mensagem):
    INSTANCIA    = "3F14E62A63D2B28DC385B20DE66F3711"
    TOKEN        = "2321563615C4242CB6031504"
    CLIENT_TOKEN = "Ffaa43dcff1e14f0e985c91e92b24ed89S"
    
    tel_limpo = re.sub(r'\D', '', str(telefone_destino))
    if not tel_limpo.startswith('55') and len(tel_limpo) in [10, 11]:
        tel_limpo = '55' + tel_limpo
        
    url = f"https://api.z-api.io/instances/{INSTANCIA}/token/{TOKEN}/send-text"
    payload = {"phone": tel_limpo, "message": texto_mensagem}
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Client-Token": CLIENT_TOKEN
    }
    try:
        requests.post(url, json=payload, headers=headers)
        return True
    except:
        return False

# ── Session State (Controle Seguro do Modal) ──
if 'logado' not in st.session_state:
    st.session_state.logado = False

if 'cliente' not in st.session_state:
    st.session_state.cliente = None

token_cliente = normalizar_chave_cliente(st.query_params.get("token_cli"))
if not st.session_state.logado and token_cliente:
    st.session_state.logado = True
    st.session_state.cliente = token_cliente

if st.session_state.logado:
    cliente_sessao = normalizar_chave_cliente(st.session_state.cliente)
    if not cliente_sessao:
        st.session_state.logado = False
        st.session_state.cliente = None
        st.query_params.clear()
        st.rerun()
    st.session_state.cliente = cliente_sessao

if 'filtro_kpi' not in st.session_state: st.session_state.filtro_kpi = "TODOS"
if 'linha_clicada' not in st.session_state: st.session_state.linha_clicada = None
if 'pedido_modal' not in st.session_state: st.session_state.pedido_modal = None
if 'modal_aberto' not in st.session_state: st.session_state.modal_aberto = False
if 'modal_fechado' not in st.session_state: st.session_state.modal_fechado = False
if 'modal_renderizado_antes' not in st.session_state: st.session_state.modal_renderizado_antes = False
if 'modal_foi_renderizado' not in st.session_state: st.session_state.modal_foi_renderizado = False
if 'ignorar_selecao_grid' not in st.session_state: st.session_state.ignorar_selecao_grid = False
if 'busca_grid_input' not in st.session_state: st.session_state.busca_grid_input = ""
if 'busca_grid_aplicada' not in st.session_state: st.session_state.busca_grid_aplicada = ""

def aplicar_busca_grid():
    st.session_state.busca_grid_aplicada = st.session_state.busca_grid_input.strip()

# =======================================================
# ⚙️ FUNÇÕES AUXILIARES (AGORA NO LUGAR CERTO!)
# =======================================================
def get_st(row):
    s = str(row.get('STATUS_RESOLVIDO', row.get('STATUS', ''))).strip().upper()
    if 'AGUARDANDO' in s: return '🔒 Aguardando Confirmação'
    if 'RECUSA'     in s: return '❌ Recusado'
    if 'ENTREGUE'   in s: return '✅ Entregue'
    if 'COLETADO'   in s:
        # 🚚 Se foi coletado após 18h, mostrar como "Em Transferência"
        hora_atual = datetime.now(FUSO_BR).hour
        if hora_atual >= 18:
            return '🚚 Em Transferência'
        return '📦 Coletado'
    if 'ROTA DE COLETA' in s: return '🚐 Indo Coletar'
    if 'ROTA'       in s: return '🚚 Saiu para Entrega'
    if 'CONFERIDO'  in s: return '☑️ Recebido na Base'
    if 'FRUSTRADA'  in s: return '⚠️ Insucesso'
    if 'CANCELADO'  in s: return '🚫 Cancelado'
    if 'PROBLEMA'   in s: return '🚨 Ocorrência'
    return '⏳ Pendente'

def get_detalhes(row):
    obs_master = str(row.get('OBSERVACOES', '')).strip()
    obs_app    = str(row.get('OBS_APP_FINAL', '')).strip()
    contato    = str(row.get('CONTATO_FINAL', '')).strip()
    recebedor  = str(row.get('RECEBEDOR_FINAL', '')).strip()
    status     = str(row.get('STATUS_DISPLAY', '')).upper()
    hora       = str(row.get('HORA_LIMPA', '')).strip()
    dt_efetiva = str(row.get('DATA_EFETIVA', '')).strip()

    dt_curta = dt_efetiva
    if len(dt_efetiva) >= 10: 
        dt_curta = dt_efetiva[:5] 

    str_coleta = f"Coletado às {hora}" if hora else ""

    if 'ENTREGUE' in status:
        rec_final = recebedor if recebedor else contato if contato else ""
        dt_str = f" em {dt_curta}" if dt_curta and dt_curta != "-" else ""
        texto_entrega = f"Entregue para {rec_final}{dt_str}" if rec_final else f"Entregue{dt_str}"
        if str_coleta:
            return f"{str_coleta} / {texto_entrega}"
        return texto_entrega

    if 'FRUSTRADA' in status or 'PROBLEMA' in status:
        obs_limpa = re.sub(r'\[COLETA:.*?\]', '', obs_app, flags=re.IGNORECASE).strip()
        if not obs_limpa:
            obs_limpa = re.sub(r'\[COLETA:.*?\]', '', obs_master, flags=re.IGNORECASE).strip()

        texto_frustrada = ""
        if obs_limpa and obs_limpa.upper() != 'NAN':
            texto_frustrada = obs_limpa
            if contato and contato.upper() != 'NAN':
                texto_frustrada += f" (Informante: {contato})"
        elif contato and contato.upper() != 'NAN':
            texto_frustrada = f"Motivo/Informante: {contato}"
        else:
            texto_frustrada = obs_master if obs_master else ""

        if hora:
            if texto_frustrada and texto_frustrada != "-":
                return f"Ocorrência às {hora} / {texto_frustrada}"
            return f"Ocorrência registrada às {hora}"
        return texto_frustrada if texto_frustrada else "-"
        
    if 'COLETADO' in status or 'ROTA' in status:
        return str_coleta if str_coleta else "-"

    obs_final = obs_app if obs_app and obs_app.upper() != 'NAN' else obs_master
    if obs_final.upper() == 'NAN': obs_final = ""

    if not obs_final and not contato: return "-"
    if obs_final and contato and obs_final.upper() != contato.upper():
        return f"{obs_final} (Informante: {contato})"
    return obs_final if obs_final else f"Informante: {contato}"

def definir_prioridade_portal(status_str):
    s = str(status_str).upper()
    if 'PENDENTE' in s or 'AGUARDANDO' in s: return 1
    if 'ROTA DE COLETA' in s: return 2
    if 'COLETADO' in s: return 3
    if 'FRUSTRADA' in s or 'PROBLEMA' in s or 'RECUSA' in s or 'ATRASADO' in s: return 4
    if 'CONFERIDO' in s: return 5
    if 'ROTA DE ENTREGA' in s or 'EM ROTA' in s: return 6
    if 'ENTREGUE' in s: return 7
    return 8 

def tratar_foto(x):
    xs = str(x).strip()
    if not xs or xs.upper() in ['NAN', 'NONE']: return ""
    if xs.startswith("http"): return xs
    return f"https://www.appsheet.com/template/gettablefileurl?appName=APPIGOLOGISTICA-153047553&tableName=App_Tarefas&fileName={xs}"

KPI_DOT_COLOR = { "TODOS": "#2563eb", "ENTREGUE": "#16a34a", "FRUSTRADA": "#dc2626", "COLETADO": "#0ea5e9", "PENDENTE": "#d97706", "Aguardando": "#475569", "HOJE": "#7c3aed" }
KPI_BG_COLOR = { "TODOS": "#dbeafe", "ENTREGUE": "#dcfce7", "FRUSTRADA": "#fee2e2", "COLETADO": "#e0f2fe", "PENDENTE": "#fef3c7", "Aguardando": "#f1f5f9", "HOJE": "#ede9fe" }
KPI_META = [("TODOS", "📦 Total", "kpi_total"), ("ENTREGUE", "✅ Entregues", "kpi_entregue"), ("FRUSTRADA", "❌ Insucessos", "kpi_frus"), ("COLETADO", "🚐 Coletados", "kpi_coletado"), ("PENDENTE", "⏳ Pendentes", "kpi_pend"), ("Aguardando", "🎧 Chamados", "kpi_aguardando"), ("HOJE", "📅 Hoje", "kpi_hoje")]

# =======================================================
# 🎨 ESTILOS E CONSTANTES DO MODAL (REFATORADO)
# =======================================================
MODAL_COLORS = {
    "entregue": "#10B981",
    "pendente": "#F59E0B",
    "erro": "#EF4444",
    "coletado": "#3B82F6",
    "barra_ok": "#10b981",
    "barra_erro": "#ef4444",
    "barra_default": "#3b82f6",
    "brand": "#2563eb",
    "text": "#0f172a",
    "muted": "#64748b",
    "border": "#e2e8f0"
}

MODAL_STYLES = {
    "header": "font-size:11px; font-weight:700; color:#2563eb; text-transform:uppercase; margin:0; letter-spacing:0.5px;",
    "titulo": "font-size:14px; font-weight:700; margin:2px 0 12px 0;",
    "subtitulo": "font-size:13px; color:#1e293b; margin:2px 0 12px 0; font-weight:500;",
    "card_container": "background:#f8fafc; padding:12px; border-radius:12px; border:1px solid #e2e8f0; box-shadow:0 1px 2px rgba(0,0,0,0.02);",
    "badge_label": "font-size:12px; font-weight:700; color:#64748b; text-transform:uppercase; margin:0 0 8px 0;",
}

# =======================================================
# 🔧 FUNÇÕES HELPER PARA O MODAL
# =======================================================
def get_status_color(status_str):
    """Retorna a cor correta baseada no status"""
    s = str(status_str).upper()
    if "ENTREGUE" in s:
        return MODAL_COLORS["entregue"]
    if any(x in s for x in ["FRUSTRADA", "PROBLEMA", "CANCELADO", "ATRASADO", "RECUSA"]):
        return MODAL_COLORS["erro"]
    if "COLETADO" in s or "ROTA" in s:
        return MODAL_COLORS["coletado"]
    return MODAL_COLORS["pendente"]

def get_progress_step(status_str):
    """Retorna o passo da barra de progresso (1-4)"""
    s = str(status_str).upper()
    
    if any(x in s for x in ["FRUSTRADA", "PROBLEMA", "CANCELADO", "RECUSA"]):
        if "ROTA DE COLETA" in s or "COLETADO" in s:
            return 2
        return 1
    
    if "ROTA DE COLETA" in s:
        return 2
    elif any(x in s for x in ["COLETADO", "ROTA DE ENTREGA", "EM ROTA", "CONFERIDO"]):
        return 3
    elif "ENTREGUE" in s:
        return 4
    return 1

def limpar_valor(valor, padrao=""):
    """Limpa e valida um valor do banco"""
    v = str(valor).strip() if valor else ""
    return padrao if v.upper() in ['NAN', 'NONE', ''] else v

def formatar_endereco(pedido_data):
    """Formata endereço completo"""
    end_rua = limpar_valor(pedido_data.get('ENDERECO', ''))
    end_num = limpar_valor(pedido_data.get('NUMERO', ''))
    end_bairro = limpar_valor(pedido_data.get('BAIRRO', ''))
    end_cid_uf = limpar_valor(pedido_data.get('CIDADE_UF', 'N/A'), 'N/A')
    
    partes = []
    if end_rua: partes.append(end_rua)
    if end_num: partes.append(f"nº {end_num}")
    if end_bairro: partes.append(end_bairro)
    
    return ", ".join(partes) + f" — {end_cid_uf}" if partes else end_cid_uf

def formatar_motorista(pedido_data, status_str):
    """Formata dados de motorista (coleta vs entrega)"""
    s = str(status_str).upper()
    mot_coleta = limpar_valor(pedido_data.get('MOTORISTA_COLETA', ''), 'Equipe IGO')
    mot_entrega = limpar_valor(pedido_data.get('MOTORISTA_ENTREGA', ''), mot_coleta)
    
    if any(x in s for x in ["ENTREGUE", "CONFERIDO"]) and mot_coleta != mot_entrega:
        return {
            "duplo": True,
            "coleta": mot_coleta,
            "entrega": mot_entrega
        }
    return {
        "duplo": False,
        "coleta": mot_coleta,
        "entrega": mot_coleta
    }

# =======================================================
# 📱 FUNÇÕES DE RENDERIZAÇÃO DO MODAL
# =======================================================
def render_header_status(pedido_data, status):
    """Renderiza cabeçalho com pedido e barra de status"""
    cor = get_status_color(status)
    step = get_progress_step(status)
    cor_barra = MODAL_COLORS["barra_ok"] if step == 4 else (MODAL_COLORS["barra_erro"] if step == 1 and "FRUSTRADA" in status else MODAL_COLORS["barra_default"])
    
    # Cabeçalho
    c_h1, c_h2 = st.columns([3, 1])
    c_h1.subheader(f"Pedido: {pedido_data.get('PEDIDO', 'N/A')}")
    c_h2.markdown(f"<div style='text-align:center; background:{cor}; color:white; padding:8px; border-radius:10px; font-weight:bold; font-size:12px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>{status}</div>", unsafe_allow_html=True)
    
    # Barra de Progresso
    html_barra = f"""
    <div style='display:flex;justify-content:space-between;position:relative;margin:15px 0 35px 0;'>
        <div style='position:absolute;top:12px;left:0;right:0;height:4px;background:#e2e8f0;z-index:1;'></div>
        <div style='position:absolute;top:12px;left:0;width:{(step-1)*33.3}%;height:4px;background:{cor_barra};z-index:2;transition:width 0.5s;'></div>
        <div style='z-index:3;text-align:center;width:60px;'><div style='width:28px;height:28px;background:{cor_barra if step >= 1 else "#e2e8f0"};color:white;border-radius:50%;line-height:28px;margin:0 auto;font-size:14px;box-shadow:0 2px 4px rgba(0,0,0,0.1);'>✓</div><div style='font-size:11px;margin-top:5px;font-weight:600;color:{"#0f172a" if step >= 1 else "#64748b"};'>Pedido</div></div>
        <div style='z-index:3;text-align:center;width:60px;'><div style='width:28px;height:28px;background:{cor_barra if step >= 2 else "#e2e8f0"};color:white;border-radius:50%;line-height:28px;margin:0 auto;font-size:14px;box-shadow:0 2px 4px rgba(0,0,0,0.1);'>{"!" if step==2 and "FRUSTRADA" in status else "🚐"}</div><div style='font-size:11px;margin-top:5px;font-weight:600;color:{"#0f172a" if step >= 2 else "#64748b"};'>Em Rota</div></div>
        <div style='z-index:3;text-align:center;width:60px;'><div style='width:28px;height:28px;background:{cor_barra if step >= 3 else "#e2e8f0"};color:white;border-radius:50%;line-height:28px;margin:0 auto;font-size:14px;box-shadow:0 2px 4px rgba(0,0,0,0.1);'>📦</div><div style='font-size:11px;margin-top:5px;font-weight:600;color:{"#0f172a" if step >= 3 else "#64748b"};'>Coletado</div></div>
        <div style='z-index:3;text-align:center;width:60px;'><div style='width:28px;height:28px;background:{cor_barra if step >= 4 else "#e2e8f0"};color:white;border-radius:50%;line-height:28px;margin:0 auto;font-size:14px;box-shadow:0 2px 4px rgba(0,0,0,0.1);'>✅</div><div style='font-size:11px;margin-top:5px;font-weight:600;color:{"#0f172a" if step >= 4 else "#64748b"};'>Entregue</div></div>
    </div>
    """
    st.markdown(html_barra, unsafe_allow_html=True)

def render_info_dados_pedido(pedido_data, status):
    """Renderiza seção de dados do pedido (cliente, endereço, datas)"""
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<p style='" + MODAL_STYLES['header'] + "'>🏢 Cliente (Ponto de Coleta)</p>", unsafe_allow_html=True)
    st.markdown(f"<p style='font-size:14px; font-weight:700; background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; margin:2px 0 12px 0;'>{pedido_data.get('LABORATORIO', 'N/A')}</p>", unsafe_allow_html=True)
    
    st.markdown("<p style='" + MODAL_STYLES['header'] + "'>📍 Endereço de Coleta</p>", unsafe_allow_html=True)
    st.markdown(f"<p style='" + MODAL_STYLES['subtitulo'] + "'>{formatar_endereco(pedido_data)}</p>", unsafe_allow_html=True)
    
    st.markdown("<p style='" + MODAL_STYLES['header'] + "'>📅 Datas da Corrida</p>", unsafe_allow_html=True)
    timeline = render_timeline(pedido_data, status)
    st.markdown(timeline, unsafe_allow_html=True)
    
    st.markdown("<p style='" + MODAL_STYLES['header'] + "'>🎯 SLA Acordado</p>", unsafe_allow_html=True)
    data_limite = limpar_valor(pedido_data.get('DATA_LIMITE', '---'), "Não definida")
    st.markdown(f"<p style='font-size:13px; color:#1e293b; margin:2px 0 12px 0;'>📌 Previsão: <b style='color:#2563eb;'>{data_limite}</b></p>", unsafe_allow_html=True)

def render_motorista(pedido_data, status):
    """Renderiza seção de motorista"""
    mot_info = formatar_motorista(pedido_data, status)
    
    st.markdown("<p style='" + MODAL_STYLES['header'] + "'>👤 Motorista (Entregador)</p>", unsafe_allow_html=True)
    
    if mot_info["duplo"]:
        motorista_html = f"<p style='margin:2px 0 12px 0;font-size:13px;font-weight:600;color:#334155;'>📦 Coleta: <span style='color:#3b82f6;'>{mot_info['coleta']}</span><br>✅ Entrega: <span style='color:#3b82f6;'>{mot_info['entrega']}</span></p>"
    else:
        motorista_html = f"<p style='margin:2px 0 12px 0;font-size:14px;font-weight:700;color:#3b82f6;'>🚐 {mot_info['coleta']}</p>"
    
    st.markdown(motorista_html, unsafe_allow_html=True)
    
    st.markdown("<p style='" + MODAL_STYLES['header'] + "'>📈 Nível de Serviço (Local)</p>", unsafe_allow_html=True)
    st.markdown(f"<p style='font-size:13px; color:#1e293b; margin:2px 0 0 0; font-weight:500;'>{pedido_data.get('SLA_LAB', 'Em mapeamento')} <br> {pedido_data.get('OTD_LAB', '')}</p>", unsafe_allow_html=True)

def render_timeline(pedido_data, status):
    """Renderiza timeline de datas e horas"""
    data_efetiva = limpar_valor(pedido_data.get('DATA_EFETIVA', '---')).replace(" 00:00:00", "")
    hora_coleta = limpar_valor(pedido_data.get('HORA_COLETA_REAL', ''))
    hora_entrega = limpar_valor(pedido_data.get('HORA_ENTREGA_REAL', '')) or limpar_valor(pedido_data.get('HORA_LIMPA', ''))
    data_limite = limpar_valor(pedido_data.get('DATA_LIMITE', '---'), "Não definida")
    
    s = str(status).upper()
    
    # 🔥 AJUSTE: Se a hora não foi achada de primeira, mas o status é coleta/rota, pega a última hora registrada!
    if not hora_coleta and any(x in s for x in ["COLETADO", "ROTA"]):
        hora_coleta = limpar_valor(pedido_data.get('HORA_LIMPA', ''))
    
    hora_coleta_str = f" às {hora_coleta}" if hora_coleta else ""
    hora_entrega_str = f" às {hora_entrega}" if hora_entrega else ""
    
    # Calcular selo prazo
    selo_prazo = ""
    if any(x in s for x in ["ENTREGUE", "CONFERIDO"]) and data_limite != "Não definida" and data_efetiva and data_efetiva != "---":
        try:
            partes_ef = data_efetiva.split('/')
            partes_lim = data_limite.split('/')
            if len(partes_ef) == 3 and len(partes_lim) == 3:
                ano_ef = int(partes_ef[2]) if int(partes_ef[2]) >= 100 else int(partes_ef[2]) + 2000
                ano_lim = int(partes_lim[2]) if int(partes_lim[2]) >= 100 else int(partes_lim[2]) + 2000
                dt_ef = datetime(ano_ef, int(partes_ef[1]), int(partes_ef[0])).date()
                dt_lim = datetime(ano_lim, int(partes_lim[1]), int(partes_lim[0])).date()
                
                if dt_ef <= dt_lim:
                    selo_prazo = "<span style='background:#dcfce7; color:#166534; padding:2px 6px; border-radius:4px; font-size:11px; font-weight:bold; margin-left:5px;'>No Prazo</span>"
                else:
                    dias = (dt_ef - dt_lim).days
                    selo_prazo = f"<span style='background:#fee2e2; color:#991b1b; padding:2px 6px; border-radius:4px; font-size:11px; font-weight:bold; margin-left:5px;'>Atrasado {dias} dia(s)</span>"
        except:
            pass
    
    # Renderizar timeline conforme status (agora com a coleta aparecendo também no insucesso)
    if any(x in s for x in ["ENTREGUE", "CONFERIDO"]):
        return f"<p style='margin:2px 0 12px 0;font-size:13px;color:#334155;'>📦 Coleta: <b>{pedido_data.get('DATA', '---')}{hora_coleta_str}</b><br>✅ Entrega: <b>{data_efetiva}{hora_entrega_str}</b> {selo_prazo}</p>"
    elif any(x in s for x in ["COLETADO", "ROTA"]):
        return f"<p style='margin:2px 0 12px 0;font-size:13px;color:#334155;'>📦 Coleta: <b>{pedido_data.get('DATA', '---')}{hora_coleta_str}</b><br>⏳ Entrega: <i>Em trânsito para o destino...</i></p>"
    elif any(x in s for x in ["FRUSTRADA", "PROBLEMA"]):
        return f"<p style='margin:2px 0 12px 0;font-size:13px;color:#334155;'>📦 Coleta: <b>{pedido_data.get('DATA', '---')}{hora_coleta_str}</b><br><span style='color:#ef4444;'>❌ Tentativa: <b>{data_efetiva}{hora_entrega_str}</b></span></p>"
    else:
        return f"<p style='margin:2px 0 12px 0;font-size:13px;color:#334155;'>⏳ Previsão de Coleta: <b>{pedido_data.get('ETA_LAB', 'Em mapeamento')}</b></p>"

def render_historico_ponto(pedido_data, df_historico):
    """Renderiza histórico do ponto de coleta"""
    if df_historico is None or df_historico.empty:
        return
    
    lab_atual = pedido_data.get('LABORATORIO', '')
    df_lab = df_historico[df_historico['LABORATORIO'] == lab_atual].copy()
    df_lab = df_lab[df_lab['STATUS_DISPLAY'].str.contains('Entregue|Frustrada|Cancelado|Coletado|Recusada|Conferido', case=False, na=False)]
    df_lab = df_lab.sort_values('DATA', ascending=False).head(5)
    
    if df_lab.empty:
        return
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<p style='font-size:11px; font-weight:700; color:#64748b; text-transform:uppercase; margin:0;'>📋 Histórico do Ponto (Últimas 5)</p>", unsafe_allow_html=True)
    
    st.markdown("""
        <style>
        .historico-badge {
            display: inline-block;
            padding: 6px 10px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 600;
            margin-right: 8px;
            white-space: nowrap;
        }
        .historico-badge-sucesso { background: #dcfce7; color: #166534; border: 1px solid #86efac; }
        .historico-badge-frustrada { background: #fee2e2; color: #991b1b; border: 1px solid #fca5a5; }
        .historico-badge-em-rota { background: #dbeafe; color: #1e40af; border: 1px solid #93c5fd; }
        .historico-legenda { background: #f8fafc; padding: 8px; border-radius: 6px; font-size: 10px; color: #64748b; margin-top: 8px; line-height: 1.6; }
        </style>
    """, unsafe_allow_html=True)
    
    for _, row in df_lab.iterrows():
        status_hist = str(row.get('STATUS_DISPLAY', '')).upper()
        if 'ENTREGUE' in status_hist or 'CONFERIDO' in status_hist:
            classe, emoji = 'historico-badge-sucesso', '✅'
        elif any(x in status_hist for x in ['FRUSTRADA', 'PROBLEMA', 'CANCELADO', 'RECUSA']):
            classe, emoji = 'historico-badge-frustrada', '❌'
        else:
            classe, emoji = 'historico-badge-em-rota', '🚐'
        
        st.markdown(f"<span class='historico-badge {classe}'>{emoji} {row.get('PEDIDO', 'N/A')}</span> <span style='font-size:10px; color:#64748b;'>{row.get('DATA', '')}</span>", unsafe_allow_html=True)
    
    st.markdown("<div class='historico-legenda'><b>Legenda:</b> ✅ Entregue | ❌ Frustrada/Cancelada | 🚐 Em Rota/Coletada</div>", unsafe_allow_html=True)

def render_comprovantes(pedido_data, status):
    """Renderiza seção de comprovantes com fotos"""
    foto_coleta = tratar_foto(limpar_valor(pedido_data.get('FOTO_COLETA', '')))
    foto_entrega = tratar_foto(limpar_valor(pedido_data.get('FOTO_ENTREGA', '')))
    foto_gen = limpar_valor(pedido_data.get('COMPROVANTE', ''))
    
    # Se tiver fotos separadas
    if (foto_coleta and foto_coleta.startswith("http")) or (foto_entrega and foto_entrega.startswith("http")):
        if foto_coleta and foto_coleta.startswith("http"):
            st.markdown(f"<div style='{MODAL_STYLES['card_container']}'><p style='{MODAL_STYLES['badge_label']}'>📸 Comprovante de Coleta</p></div>", unsafe_allow_html=True)
            st.image(foto_coleta, use_container_width=True)
            try:
                response = requests.get(foto_coleta, timeout=5)
                if response.status_code == 200:
                    nome = foto_coleta.split('/')[-1] if '/' in foto_coleta else f"coleta_{pedido_data.get('PEDIDO', 'pedido')}.jpg"
                    if '.' not in nome: nome = f"{nome}.jpg"
                    st.download_button("⬇️ Baixar Comprovante de Coleta", response.content, nome, "image/jpeg", use_container_width=True, key="download_coleta")
            except:
                st.markdown(f"<p style='text-align:center; color:#64748b; font-size:12px;'>📎 <a href='{foto_coleta}' target='_blank'>Abrir em nova aba</a></p>", unsafe_allow_html=True)
        
        if foto_entrega and foto_entrega.startswith("http"):
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(f"<div style='{MODAL_STYLES['card_container']}'><p style='{MODAL_STYLES['badge_label']}'>📸 Comprovante de Entrega</p></div>", unsafe_allow_html=True)
            st.image(foto_entrega, use_container_width=True)
            try:
                response = requests.get(foto_entrega, timeout=5)
                if response.status_code == 200:
                    nome = foto_entrega.split('/')[-1] if '/' in foto_entrega else f"entrega_{pedido_data.get('PEDIDO', 'pedido')}.jpg"
                    if '.' not in nome: nome = f"{nome}.jpg"
                    st.download_button("⬇️ Baixar Comprovante de Entrega", response.content, nome, "image/jpeg", use_container_width=True, key="download_entrega")
            except:
                st.markdown(f"<p style='text-align:center; color:#64748b; font-size:12px;'>📎 <a href='{foto_entrega}' target='_blank'>Abrir em nova aba</a></p>", unsafe_allow_html=True)
    
    # Fallback para foto genérica
    elif foto_gen and foto_gen.startswith("http"):
        st.markdown(f"<div style='background:#f8fafc; padding:16px; border-radius:12px; border:1px solid #e2e8f0; box-shadow:0 1px 2px rgba(0,0,0,0.02);'><p style='font-size:12px; font-weight:700; color:#64748b; text-transform:uppercase; margin:0 0 12px 0;'>📸 Canhoto da Operação</p></div>", unsafe_allow_html=True)
        st.image(foto_gen, use_container_width=True)
        try:
            response = requests.get(foto_gen, timeout=5)
            if response.status_code == 200:
                nome = foto_gen.split('/')[-1] if '/' in foto_gen else f"canhoto_{pedido_data.get('PEDIDO', 'pedido')}.jpg"
                if '.' not in nome: nome = f"{nome}.jpg"
                st.download_button("⬇️ Baixar Canhoto", response.content, nome, "image/jpeg", use_container_width=True)
        except:
            st.markdown(f"<p style='text-align:center; color:#64748b; font-size:12px;'>📎 <a href='{foto_gen}' target='_blank'>Abrir em nova aba</a></p>", unsafe_allow_html=True)
    
    # Sem fotos
    elif any(x in status for x in ["FRUSTRADA", "PROBLEMA", "CANCELADO"]):
        st.warning("📷 Nenhuma foto da ocorrência foi anexada na justificativa.")
    else:
        st.info("📷 **Aguardando anexo do canhoto da operação.**")

def render_observacoes(pedido_data, status):
    """Renderiza seção de observações/justificativas"""
    st.markdown("<br>", unsafe_allow_html=True)
    if any(x in status for x in ["FRUSTRADA", "PROBLEMA", "CANCELADO"]):
        st.error(f"**⚠️ Motivo da Ocorrência:**\n\n{pedido_data.get('DETALHES', 'Motivo não informado no aplicativo.')}")
    else:
        st.info(f"**💬 Atualizações da Base:**\n\n{pedido_data.get('DETALHES', 'Nenhuma observação pendente.')}")

# =======================================================
# 📑 FUNÇÕES PARA RENDERIZAR AS ABAS
# =======================================================
def render_tab_dados_principais(pedido_data, status):
    """ABA 1: Dados Principais - Reorganizada por Urgência e Atores"""
    # ⏱️ LINHA 1: Urgência e Prazos (Sinais Vitais no Topo)
    col1, col2, col3 = st.columns(3)
    data_limite = limpar_valor(pedido_data.get('DATA_LIMITE', '---'), "Não definida")
    
    with col1:
        with st.container(border=True):
            st.markdown("<p style='" + MODAL_STYLES['header'] + "'>🎯 Previsão / SLA</p>", unsafe_allow_html=True)
            st.markdown(f"<p style='font-size:15px; color:{MODAL_COLORS['brand']}; font-weight:700; margin:8px 0;'>{data_limite}</p>", unsafe_allow_html=True)
            st.markdown(f"<p style='font-size:11px; color:#64748b;'>Prazo limite acordado</p>", unsafe_allow_html=True)
            
    with col2:
        with st.container(border=True):
            st.markdown("<p style='" + MODAL_STYLES['header'] + "'>📈 Nível de Serviço</p>", unsafe_allow_html=True)
            st.markdown(f"<p style='font-size:13px; color:#334155; font-weight:600; margin:8px 0;'>{pedido_data.get('SLA_LAB', 'Em mapeamento')}</p>", unsafe_allow_html=True)
            
    with col3:
        with st.container(border=True):
            st.markdown("<p style='" + MODAL_STYLES['header'] + "'>⭐ Performance Geral</p>", unsafe_allow_html=True)
            st.markdown(f"<p style='font-size:13px; color:#334155; font-weight:600; margin:8px 0;'>{pedido_data.get('OTD_LAB', 'Sem histórico')}</p>", unsafe_allow_html=True)

    st.divider()

    # 🚐 LINHA 2: Atores e Logística Física (Quem, Onde e Quem Leva)
    c_cli, c_end, c_mot = st.columns([1, 1.5, 1])
    
    with c_cli:
        with st.container(border=True):
            st.markdown("<p style='" + MODAL_STYLES['header'] + "'>🏢 Ponto de Coleta</p>", unsafe_allow_html=True)
            st.markdown(f"<p style='font-size:14px; font-weight:700; color:#334155; margin:8px 0;'>{pedido_data.get('LABORATORIO', 'N/A')}</p>", unsafe_allow_html=True)
            
    with c_end:
        with st.container(border=True):
            st.markdown("<p style='" + MODAL_STYLES['header'] + "'>📍 Endereço de Coleta</p>", unsafe_allow_html=True)
            st.markdown(f"<p style='font-size:12px; color:#334155; margin:8px 0; font-weight:500; line-height:1.4;'>{formatar_endereco(pedido_data)}</p>", unsafe_allow_html=True)
            
    with c_mot:
        with st.container(border=True):
            st.markdown("<p style='" + MODAL_STYLES['header'] + "'>👤 Motorista(s)</p>", unsafe_allow_html=True)
            mot_info = formatar_motorista(pedido_data, status)
            if mot_info["duplo"]:
                st.markdown(f"<p style='margin:4px 0; font-size:11px; color:#334155;'><b>📦 Col:</b> {mot_info['coleta']}<br><b>✅ Ent:</b> {mot_info['entrega']}</p>", unsafe_allow_html=True)
            else:
                st.markdown(f"<p style='font-size:13px; color:#2563eb; font-weight:700; margin:8px 0;'>🚐 {mot_info['coleta']}</p>", unsafe_allow_html=True)

    st.divider()

    # 📅 LINHA 3: Timeline da Operação (Fatos Executados no Rodapé)
    with st.container(border=True):
        st.markdown("<p style='" + MODAL_STYLES['header'] + "'>📅 Timeline da Operação</p>", unsafe_allow_html=True)
        timeline = render_timeline(pedido_data, status)
        st.markdown(timeline, unsafe_allow_html=True)

def render_tab_comprovantes(pedido_data, status):
    """ABA 2: Comprovantes - Fotos de Coleta e Entrega (Layout Amigável + Ultra Rápido)"""
    foto_coleta = tratar_foto(limpar_valor(pedido_data.get('FOTO_COLETA', '')))
    foto_entrega = tratar_foto(limpar_valor(pedido_data.get('FOTO_ENTREGA', '')))
    foto_gen = limpar_valor(pedido_data.get('COMPROVANTE', ''))
    
    # Se tiver fotos separadas
    if (foto_coleta and foto_coleta.startswith("http")) or (foto_entrega and foto_entrega.startswith("http")):
        if foto_coleta and foto_coleta.startswith("http"):
            st.markdown("<p style='" + MODAL_STYLES['header'] + "'>📸 Comprovante de Coleta</p>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.image(foto_coleta, use_container_width=True, caption="Foto tirada no momento da coleta")
                # ✨ BOTÃO HTML INSTANTÂNEO (Fim do travamento do requests.get)
                botao_coleta_html = f"""
                    <a href="{foto_coleta}" target="_blank" style="text-decoration: none;">
                        <div style="width: 100%; text-align: center; padding: 8px; margin-top: 5px; border-radius: 8px; border: 1px solid #cbd5e1; background: #ffffff; color: #0f172a; font-size: 13px; font-weight: 600; cursor: pointer; transition: 0.2s; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
                            🔍 Visualizar / Salvar Coleta
                        </div>
                    </a>
                """
                st.markdown(botao_coleta_html, unsafe_allow_html=True)
        
        if foto_entrega and foto_entrega.startswith("http"):
            st.divider()
            st.markdown("<p style='" + MODAL_STYLES['header'] + "'>📸 Comprovante de Entrega</p>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.image(foto_entrega, use_container_width=True, caption="Foto tirada no momento da entrega")
                # ✨ BOTÃO HTML INSTANTÂNEO (Fim do travamento do requests.get)
                botao_entrega_html = f"""
                    <a href="{foto_entrega}" target="_blank" style="text-decoration: none;">
                        <div style="width: 100%; text-align: center; padding: 8px; margin-top: 5px; border-radius: 8px; border: 1px solid #cbd5e1; background: #ffffff; color: #0f172a; font-size: 13px; font-weight: 600; cursor: pointer; transition: 0.2s; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
                            🔍 Visualizar / Salvar Entrega
                        </div>
                    </a>
                """
                st.markdown(botao_entrega_html, unsafe_allow_html=True)
    
    # Fallback para foto genérica
    elif foto_gen and foto_gen.startswith("http"):
        st.markdown("<p style='" + MODAL_STYLES['header'] + "'>📸 Canhoto da Operação</p>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image(foto_gen, use_container_width=True, caption="Comprovante da operação")
            # ✨ BOTÃO HTML INSTANTÂNEO (Fim do travamento do requests.get)
            botao_gen_html = f"""
                <a href="{foto_gen}" target="_blank" style="text-decoration: none;">
                    <div style="width: 100%; text-align: center; padding: 8px; margin-top: 5px; border-radius: 8px; border: 1px solid #cbd5e1; background: #ffffff; color: #0f172a; font-size: 13px; font-weight: 600; cursor: pointer; transition: 0.2s; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
                        🔍 Visualizar / Salvar Canhoto
                    </div>
                </a>
            """
            st.markdown(botao_gen_html, unsafe_allow_html=True)
    
    # Sem fotos
    elif any(x in status for x in ["FRUSTRADA", "PROBLEMA", "CANCELADO"]):
        st.warning("📷 Nenhuma foto da ocorrência foi anexada na justificativa.")
    else:
        st.info("📷 **Aguardando anexo do canhoto da operação.**\n\nAs fotos serão anexadas após a conclusão da operação.")

def render_tab_historico(pedido_data, df_historico):
    """ABA 3: Histórico - Carregado apenas quando a aba é selecionada"""
    st.markdown("<br>", unsafe_allow_html=True)
    
    # O processamento pesado só ocorre aqui, dentro da aba
    if df_historico is None or df_historico.empty:
        st.info("📋 Nenhum histórico disponível.")
        return
    
    lab_atual = pedido_data.get('LABORATORIO', '')
    # O filtro é rápido em DataFrames pequenos
    df_lab = df_historico[df_historico['LABORATORIO'] == lab_atual].copy()
    df_lab = df_lab[df_lab['STATUS_DISPLAY'].str.contains('Entregue|Frustrada|Cancelado|Coletado|Recusada|Conferido', case=False, na=False)]
    df_lab = df_lab.sort_values('DATA', ascending=False).head(5)
    
    if df_lab.empty:
        st.info("📋 Nenhum histórico encontrado para este ponto.")
        return
    
    # ✨ AJUSTE 3: Título corrigido para puxar o nome do laboratório real
    st.markdown(f"<p style='{MODAL_STYLES['header']}'>📋 Últimas 5 Operações de {lab_atual}</p>", unsafe_allow_html=True)
    
    # Criar tabela de histórico
    historico_dados = []
    for _, row in df_lab.iterrows():
        # ✨ AJUSTE 1: A coluna STATUS_DISPLAY já tem o emoji de origem, então usamos ela direto!
        status_hist = str(row.get('STATUS_DISPLAY', ''))
        
        # ✨ AJUSTE 2: Resgatando a data E a hora da operação
        data_hist = str(row.get('DATA', '')).strip()
        hora_hist = str(row.get('HORA_LIMPA', '')).strip()
        data_completa = f"{data_hist} às {hora_hist}" if hora_hist else data_hist
        
        historico_dados.append({
            "Status": status_hist,
            "Pedido": row.get('PEDIDO', 'N/A'),
            "Data": data_completa,
            "Motorista": limpar_valor(row.get('MOTORISTA_COLETA', ''), '---')
        })
    
    # Exibir como dataframe
    st.dataframe(
        pd.DataFrame(historico_dados),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Status": st.column_config.TextColumn("Status", width="medium"),
            "Pedido": st.column_config.TextColumn("Pedido", width="small"),
            "Data": st.column_config.TextColumn("Data e Hora da Coleta", width="medium"),
            "Motorista": st.column_config.TextColumn("Motorista", width="medium"),
        }
    )
    
    st.caption(f"📊 Mostrando {len(historico_dados)} operações | 📍 Ponto: {lab_atual}")

def render_tab_observacoes(pedido_data, status):
    """ABA 4: Observações - Motivos e Detalhes (Agora com a Hora)"""
    st.markdown("<p style='" + MODAL_STYLES['header'] + "'>📝 Detalhes da Operação</p>", unsafe_allow_html=True)
    
    # Resgata a hora que o status/observação foi registrado no AppSheet
    hora = limpar_valor(pedido_data.get('HORA_LIMPA', ''))
    rodape_hora = f"\n\n---\n**🕒 Horário do Registro:** {hora}" if hora else ""
    
    if any(x in status for x in ["FRUSTRADA", "PROBLEMA", "CANCELADO"]):
        with st.container(border=True):
            st.error(f"**⚠️ Motivo da Ocorrência**\n\n{pedido_data.get('DETALHES', 'Motivo não informado no aplicativo.')}{rodape_hora}")
    else:
        with st.container(border=True):
            st.info(f"**💬 Atualizações da Base**\n\n{pedido_data.get('DETALHES', 'Nenhuma observação pendente.')}{rodape_hora}")

# =======================================================
# 🪟 FUNÇÃO DO POP-UP MEGAZORD (REFATORADA COM ABAS)
# =======================================================
@st.dialog("📋 Detalhes da Operação", width="large", dismissible=False)
def modal_detalhes_pedido(pedido_data, df_historico=None):
    """
    🪟 MODAL REFATORADO COM ABAS - Estrutura Limpa e Organizada
    
    Renderiza detalhes completos de uma operação/pedido com sistema de ABAS:
    - 📋 ABA 1: DADOS PRINCIPAIS (Cliente, Endereço, Timeline, SLA, Motorista)
    - 📷 ABA 2: COMPROVANTES (Fotos de Coleta e Entrega)
    - 📊 ABA 3: HISTÓRICO (Últimas operações do ponto)
    - ⚠️ ABA 4: OBSERVAÇÕES (Motivos/Detalhes)
    """
    status = str(pedido_data.get('STATUS_DISPLAY', '')).upper()
    
    # 🎯 Renderizar Cabeçalho + Barra de Progresso
    render_header_status(pedido_data, status)
    
    # 📑 Sistema de ABAS
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Dados Principais",
        "📷 Comprovantes",
        "📊 Histórico",
        "⚠️ Observações"
    ])
    
    # ABA 1: Dados Principais
    with tab1:
        st.markdown("<br>", unsafe_allow_html=True)
        render_tab_dados_principais(pedido_data, status)
    
    # ABA 2: Comprovantes
    with tab2:
        st.markdown("<br>", unsafe_allow_html=True)
        render_tab_comprovantes(pedido_data, status)
    
    # ABA 3: Histórico
    with tab3:
        st.markdown("<br>", unsafe_allow_html=True)
        render_tab_historico(pedido_data, df_historico)
    
    # ABA 4: Observações
    with tab4:
        st.markdown("<br>", unsafe_allow_html=True)
        render_tab_observacoes(pedido_data, status)
    
    # 🔘 Botão Fechar (fora das abas)
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 🔥 CSS específico para deixar este botão vermelho e com destaque
    st.markdown("""
        <style>
        div.st-key-fechar_detalhes_btn > button {
            background: linear-gradient(180deg, #ef4444 0%, #dc2626 100%) !important;
            color: #ffffff !important;
            border: 1px solid #b91c1c !important;
            font-weight: 700 !important;
            transition: all 0.2s ease !important;
        }
        div.st-key-fechar_detalhes_btn > button:hover {
            background: linear-gradient(180deg, #dc2626 0%, #991b1b 100%) !important;
            border-color: #7f1d1d !important;
            box-shadow: 0 4px 12px rgba(220, 38, 38, 0.4) !important;
            transform: translateY(-1px) !important;
            color: #ffffff !important;
        }
        </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([3, 2, 3])
    with col2:
        if st.button("✖️ Fechar Detalhes", key="fechar_detalhes_btn", use_container_width=True):
            # 🔥 Notificação instantânea tira a sensação de travamento
            st.toast("Limpando grid e atualizando painel...", icon="💨")
            
            st.session_state.modal_aberto = False
            st.session_state.pedido_modal = None
            st.session_state.linha_clicada = None
            st.session_state.modal_fechado = True
            st.session_state.ignorar_selecao_grid = True
            st.session_state.grid_key += 1 # 🔥 Limpa a seleção da grid
            st.rerun()
# 🔥 ADICIONE ESTA FUNÇÃO NAS SUAS FUNÇÕES AUXILIARES
@st.cache_data(ttl=600)
def calcular_metricas_laboratorio(df):
    """Calcula SLA, OTD e ETA apenas quando necessário"""
    lab_stats = {}
    for lab in df['LABORATORIO'].unique():
        if not lab or pd.isna(lab): continue
        df_lab = df[df['LABORATORIO'] == lab]
        
        sucessos = len(df_lab[df_lab['STATUS_DISPLAY'].str.contains('Entregue|Coletado', case=False, na=False)])
        frustradas = len(df_lab[df_lab['STATUS_DISPLAY'].str.contains('Frustrada|Problema|Cancelado|Recusa', case=False, na=False)])
        total_finalizados = sucessos + frustradas
        
        # OTD (On-Time Delivery)
        df_entregues = df_lab[df_lab['STATUS_DISPLAY'].str.contains('Entregue|Conferido', case=False, na=False)]
        total_entregues = len(df_entregues)
        no_prazo = 0
        for _, row in df_entregues.iterrows():
            try:
                dt_ef = pd.to_datetime(str(row.get('DATA_EFETIVA','')).replace(" 00:00:00", "").strip(), format='%d/%m/%Y').date()
                dt_lim = pd.to_datetime(str(row.get('DATA_LIMITE','')).strip(), format='%d/%m/%Y').date()
                if dt_ef <= dt_lim: no_prazo += 1
            except: pass
            
        otd_pct = round((no_prazo / total_entregues) * 100) if total_entregues > 0 else 0
        pct_suc = round((sucessos / total_finalizados) * 100) if total_finalizados > 0 else 0
        pct_fru = round((frustradas / total_finalizados) * 100) if total_finalizados > 0 else 0
        
        # ETA (Média de horas)
        df_hora = df_lab[df_lab['HORA_LIMPA'].str.contains(r'^\d{2}:\d{2}$', regex=True, na=False) & df_lab['STATUS_DISPLAY'].str.contains('Entregue|Coletado', case=False, na=False)]
        eta_str = "Pouco histórico"
        if len(df_hora) >= 3:
            mins = df_hora['HORA_LIMPA'].apply(lambda x: int(x.split(':')[0])*60 + int(x.split(':')[1]))
            med_min = int(mins.median())
            eta_str = f"Entre {max(0, med_min-15)//60:02d}:{(max(0, med_min-15)%60):02d} e {(min(1440, med_min+15)//60):02d}:{(min(1440, med_min+15)%60):02d}"
            
        lab_stats[lab] = {
            'SLA': f"🟢 {pct_suc}% Sucesso | 🔴 {pct_fru}% Frustradas" if total_finalizados >= 5 else "Em mapeamento",
            'ETA': eta_str,
            'OTD': f"🎯 {otd_pct}% Entregues no Prazo" if total_entregues > 0 else "Sem entregas"
        }
    return lab_stats

# =======================================================
# 🔐 3. TELA DE LOGIN (MODELO BLINDADO E CENTRALIZADO)
# =======================================================
if not st.session_state.logado:
    st.markdown("""
        <style>
        [data-testid="stSidebar"] { display: none; }
        header { display: none !important; }
        
        [data-testid="stAppViewContainer"] { 
            background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%) !important;
            font-family: 'Inter', sans-serif;
        }

        .block-container {
            display: flex !important;
            flex-direction: column !important;
            justify-content: center !important;
            align-items: center !important;
            min-height: 100vh !important;
            padding: 0 !important;
            max-width: 100% !important;
        }

        [data-testid="stForm"] {
            background-color: #ffffff !important;
            padding: 40px !important;
            border-radius: 20px !important;
            box-shadow: 0 15px 35px -5px rgba(0,0,0,0.1), 0 5px 15px rgba(0,0,0,0.05) !important;
            border: none !important;
        }

        .login-title { text-align: center; font-size: 22px; font-weight: 800; color: #0f172a; margin-top: 15px; margin-bottom: 5px; }
        .login-subtitle { text-align: center; font-size: 13px; color: #64748b; margin-bottom: 30px; }
        
        .stTextInput > div > div > input { border-radius: 8px !important; }
        .stTextInput > label { font-size: 12px !important; font-weight: 600 !important; color: #475569 !important; }

        [data-testid="stFormSubmitButton"] > button {
            height: 48px !important;
            font-weight: 700 !important; 
            font-size: 14px !important; 
            border-radius: 8px !important; 
            background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%) !important;
            color: #ffffff !important;
            border: none !important;
            width: 100% !important;
            margin-top: 15px !important;
            transition: all 0.2s ease !important;
        }
        [data-testid="stFormSubmitButton"] > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(59, 130, 246, 0.3) !important;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<br><br><br><br>", unsafe_allow_html=True)

    _, col_login, _ = st.columns([1, 1.2, 1])
    
    with col_login:
        with st.form("form_login", clear_on_submit=False):
            
            col_espaco1, col_logo, col_espaco2 = st.columns([1, 1.5, 1])
            with col_logo:
                st.image(LOGO_IGO, use_container_width=True)
                
            st.markdown('<div class="login-title">Acesse sua conta</div>', unsafe_allow_html=True)
            st.markdown('<div class="login-subtitle">Portal de Painel de Rastreio</div>', unsafe_allow_html=True)
            
            u = st.text_input("👤 Usuário", placeholder="Digite seu usuário").upper().strip()
            s = st.text_input("🔒 Senha", type="password", placeholder="••••••••••••")
            
            submit = st.form_submit_button("🚀 Entrar no Painel")
            
            if submit:
                conf_usuario = CLIENTES_CONFIG.get(u)
                if conf_usuario and verificar_senha(s, conf_usuario.get("senha_hash", "")):
                    st.session_state.logado = True
                    st.session_state.cliente = u
                    st.query_params["token_cli"] = u
                    st.rerun()
                else:
                    st.error("❌ Credenciais Incorretas. Tente novamente.")

# =======================================================
# 🖥️ 4. PAINEL PRINCIPAL (DASHBOARD)
# =======================================================
else:
    st.markdown(CSS_DASHBOARD, unsafe_allow_html=True)
    st_autorefresh(interval=300000, limit=None, key="autorefresh_dados")

    components.html("""
        <script>
        const parentDoc = window.parent.document;
        const dict = {
            "Su": "Dom", "Mo": "Seg", "Tu": "Ter", "We": "Qua", "Th": "Qui", "Fr": "Sex", "Sa": "Sáb",
            "January": "Janeiro", "February": "Fevereiro", "March": "Março", "April": "Abril", "May": "Maio", 
            "June": "Junho", "July": "Julho", "August": "Agosto", "September": "Setembro", "October": "Outubro", 
            "November": "Novembro", "December": "Dezembro",
            "Today": "Hoje", "Clear": "Limpar",
            "Choose options": "Escolha as cidades...",
            "Select all": "Selecionar todas",
            "Clear all": "Limpar tudo",
            "No results": "Nenhuma cidade encontrada"
        };
        const observer = new MutationObserver(() => {
            const targets = parentDoc.querySelectorAll('[data-baseweb="calendar"], [data-baseweb="popover"], [data-testid="stMultiSelect"]');
            targets.forEach(target => {
                const walker = parentDoc.createTreeWalker(target, 4, null, false);
                let node;
                while (node = walker.nextNode()) {
                    let text = node.nodeValue.trim();
                    if (dict[text]) { node.nodeValue = node.nodeValue.replace(text, dict[text]); }
                }
            });
        });
        observer.observe(parentDoc.body, { childList: true, subtree: true });
        </script>
        """, height=0, width=0)

    conf              = CLIENTES_CONFIG[st.session_state.cliente]
    hoje_br           = datetime.now(FUSO_BR).date()
    hora_atual_br     = datetime.now(FUSO_BR).strftime('%H:%M:%S')
    nome_tomador_oficial = conf["filtro"] if conf["filtro"] != "TODOS" else "MATRIZ IGO"
    logo_tomador = obter_logo_por_tomador(conf.get("tomador", conf.get("filtro", "TODOS")))

    # ── SIDEBAR ────────────────────────────────────────
    with st.sidebar:
        col1, col2, col3 = st.columns([1, 4, 1])
        with col2:
            try:
                st.image(logo_tomador, use_container_width=True)
            except Exception:
                st.markdown(f"<h3 style='text-align:center;'>{st.session_state.cliente}</h3>", unsafe_allow_html=True)

        st.markdown(
            f"""
            <div class="status-online-chip">
                <div class="status-online-left">
                    <span class="status-online-dot"></span>
                    <span class="status-online-text">Online</span>
                </div>
                <span class="status-online-time">{hora_atual_br}</span>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        st.markdown("<p class='section-kicker'>Filtros de Visão</p>", unsafe_allow_html=True)
        
        with st.container(border=False):
            st.markdown("<p style='font-size: 14px; font-weight: 700; color: #1e293b; margin-bottom: 5px;'>🗓️ Período de Análise</p>", unsafe_allow_html=True)
            c1_dt, c2_dt = st.columns(2)
            # Alterado de 15 para 7 dias para carregar mais rápido inicialmente
            dt_inicio = c1_dt.date_input("De:", value=hoje_br - timedelta(days=3), format="DD/MM/YYYY")
            dt_fim    = c2_dt.date_input("Até:", value=hoje_br, format="DD/MM/YYYY")
            datas_sel = (dt_inicio, dt_fim)
            holder_cidades = st.empty()

        st.markdown("<p class='section-kicker'>Suporte e Relatórios</p>", unsafe_allow_html=True)
        
        with st.popover("🎧 Abrir Chamado ao Suporte", use_container_width=True):
            st.markdown("📄 **Novo Chamado de Atendimento**")
            with st.form("form_chamado_zap", clear_on_submit=True):
                pedido_chamado = st.text_input("Número do Pedido (Opcional):")
                msg_chamado    = st.text_area("Sua Mensagem *:", placeholder="Ex: Preciso de urgência neste pedido...")
                 
                if st.form_submit_button("🚀 Enviar Solicitação", type="primary", use_container_width=True):
                    if not msg_chamado.strip():
                        st.error("Digite uma mensagem!")
                    else:
                        with st.spinner("Gerando ticket e notificando a base..."):
                            tkt_id = f"TKT-{random.randint(10000, 99999)}"
                            data_tkt = datetime.now(FUSO_BR).strftime('%d/%m/%Y %H:%M')
                            try:
                                gc = conectar_banco_seguro()
                                planilha = gc.open("DB_IGO_Logistica")
                                try:
                                    aba_chamados = planilha.worksheet("Base_Chamados")
                                except:
                                    aba_chamados = planilha.add_worksheet(title="Base_Chamados", rows="100", cols="7")
                                    aba_chamados.update("A1", [["TICKET", "DATA", "TOMADOR", "PEDIDO", "MENSAGEM", "STATUS", "RESPOSTA"]])
                                
                                linha_ticket = [tkt_id, data_tkt, nome_tomador_oficial, pedido_chamado, msg_chamado, "🟡 EM ANÁLISE", ""]
                                aba_chamados.append_row(linha_ticket)
                                
                                texto_final = (
                                    f"🚨 *NOVO TICKET DE SUPORTE* [{tkt_id}]\n\n"
                                    f"🏢 *Cliente:* {nome_tomador_oficial}\n"
                                )
                                if pedido_chamado:
                                    texto_final += f"📦 *Pedido:* {pedido_chamado}\n"
                                texto_final += f"💬 *Mensagem:* {msg_chamado}\n\n⏳ _Acesse o Torre de Controle para responder._"
                                
                                # 🔥 Notifica os números especificados para acompanhamento dos chamados
                                numeros_notificacao_chamados = ["5511997163954", "5511984911231"]
                                for numero in numeros_notificacao_chamados:
                                    enviar_whatsapp_zapi_cliente(numero, texto_final)
                                st.success(f"✅ Ticket {tkt_id} aberto com sucesso! Acompanhe na aba 'Meus Chamados'.")
                            except Exception as e:
                                st.error(f"Erro ao criar ticket: {e}")

        holder_exportar = st.empty()

    

    # ── DADOS ───────────────────────────────────────────
    filtro_atual = conf["filtro"]
    
    # Chama a função nova passando o filtro do cliente
    df_cliente = carregar_dados_nuvem(filtro_atual)

    if df_cliente.empty:
        st.info("Aguardando novas informações do Torre de Controle na base de dados...")
    else:
        # 🔥 MOTOR DE ETA E SLA (CÁLCULO 100% E OTD PONTUALIDADE) 🔥
        df_cliente['STATUS_DISPLAY'] = df_cliente.apply(get_st, axis=1)
        
        lab_stats = {}
        for lab in df_cliente['LABORATORIO'].unique():
            if not lab or pd.isna(lab): continue
            df_lab = df_cliente[df_cliente['LABORATORIO'] == lab]
            
            sucessos = len(df_lab[df_lab['STATUS_DISPLAY'].str.contains('Entregue|Coletado', case=False, na=False)])
            frustradas = len(df_lab[df_lab['STATUS_DISPLAY'].str.contains('Frustrada|Problema|Cancelado|Recusa', case=False, na=False)])
            
            total_finalizados = sucessos + frustradas
            
            if total_finalizados > 0:
                pct_sucesso = round((sucessos / total_finalizados) * 100)
                pct_frustrada = round((frustradas / total_finalizados) * 100)
            else:
                pct_sucesso = 0
                pct_frustrada = 0
                
            # CÁLCULO DO OTD (ON-TIME DELIVERY)
            df_entregues = df_lab[df_lab['STATUS_DISPLAY'].str.contains('Entregue|Conferido', case=False, na=False)]
            total_entregues = len(df_entregues)
            otd_sucesso = 0
            
            if total_entregues > 0:
                no_prazo = 0
                for _, row in df_entregues.iterrows():
                    try:
                        dt_ef = pd.to_datetime(str(row.get('DATA_EFETIVA','')).replace(" 00:00:00", "").strip(), format='%d/%m/%Y').date()
                        dt_lim = pd.to_datetime(str(row.get('DATA_LIMITE','')).strip(), format='%d/%m/%Y').date()
                        if dt_ef <= dt_lim:
                            no_prazo += 1
                    except:
                        pass
                otd_sucesso = round((no_prazo / total_entregues) * 100)
            
            df_hora = df_lab[df_lab['HORA_LIMPA'].str.contains(r'^\d{2}:\d{2}$', regex=True, na=False) & df_lab['STATUS_DISPLAY'].str.contains('Entregue|Coletado', case=False, na=False)]
            eta_str = "Em mapeamento (Pouco histórico)"
            
            if len(df_hora) >= 3:
                mins = df_hora['HORA_LIMPA'].apply(lambda x: int(x.split(':')[0])*60 + int(x.split(':')[1]))
                med_min = int(mins.median())
                min_start = max(0, med_min - 15)
                min_end = min(1440, med_min + 15)
                h_s, m_s = divmod(min_start, 60)
                h_e, m_e = divmod(min_end, 60)
                eta_str = f"Entre {h_s:02d}:{m_s:02d} e {h_e:02d}:{m_e:02d}"
                
            lab_stats[lab] = {
                'SLA': f"🟢 {pct_sucesso}% Sucesso | 🔴 {pct_frustrada}% Frustradas" if total_finalizados >= 5 else "Em mapeamento (Poucas coletas)",
                'ETA': eta_str,
                'OTD': f"🎯 {otd_sucesso}% Entregues no Prazo" if total_entregues > 0 else "Sem entregas finalizadas"
            }

        df_cliente['SLA_LAB'] = df_cliente['LABORATORIO'].apply(lambda x: lab_stats.get(x, {}).get('SLA', 'Em mapeamento'))
        df_cliente['ETA_LAB'] = df_cliente['LABORATORIO'].apply(lambda x: lab_stats.get(x, {}).get('ETA', 'Em mapeamento'))
        df_cliente['OTD_LAB'] = df_cliente['LABORATORIO'].apply(lambda x: lab_stats.get(x, {}).get('OTD', 'Sem entregas finalizadas'))
        
        # 🔥 A FUNÇÃO ESTÁ AQUI NOVAMENTE 🔥
        df_cliente['DETALHES'] = df_cliente.apply(get_detalhes, axis=1)

        tab_grid, tab_solicitar, tab_chamados = st.tabs([
            "📊 Meus Pedidos e Monitoramento",
            "➕ Solicitar Nova Coleta",
            "🎧 Meus Chamados"
        ])

        # ===================================================
        # ABA 1 · GRID E MONITORAMENTO
        # ===================================================
        with tab_grid:
            if df_cliente.empty:
                st.warning(f"Nenhum pedido registrado sob a titularidade '{conf['filtro']}'.")
            else:
                with holder_cidades:
                    cidades_sel = st.multiselect(
                        "📍 Cidades:",
                        sorted(df_cliente['CIDADE'].dropna().unique().tolist()),
                        placeholder="Escolha as cidades..."
                    )

                df_f = df_cliente.copy()
                
                if isinstance(datas_sel, (tuple, list)) and len(datas_sel) == 2:
                    df_f = df_f[(df_f['DATA_OBJ'] >= datas_sel[0]) & (df_f['DATA_OBJ'] <= datas_sel[1])]
                
                if cidades_sel:
                    df_f = df_f[df_f['CIDADE'].isin(cidades_sel)]

                df_f['DT_LIMITE_OBJ'] = pd.to_datetime(df_f['DATA_LIMITE'], format='%d/%m/%Y', errors='coerce').dt.date

                mask_atrasado = (
                    (~df_f['STATUS_DISPLAY'].str.contains('Entregue|Insucesso|Cancelado|Aguardando|Recusado|Ocorrência', case=False, na=False)) &
                    (df_f['DT_LIMITE_OBJ'] < hoje_br) &
                    (df_f['DT_LIMITE_OBJ'].notnull())
                )
                df_f.loc[mask_atrasado, 'STATUS_DISPLAY'] = df_f.loc[mask_atrasado, 'STATUS_DISPLAY'] + ' 🚨 ATRASADO'

                n_vals = {
                    "TODOS":      len(df_f),
                    "ENTREGUE":   len(df_f[df_f['STATUS_DISPLAY'].str.contains('Entregue', case=False)]),
                    "FRUSTRADA":  len(df_f[df_f['STATUS_DISPLAY'].str.contains('Insucesso|Ocorrência|Cancelado|Recusado', case=False, na=False)]),
                    "COLETADO":   len(df_f[df_f['STATUS_DISPLAY'].str.contains('Coletado|Rota', case=False, na=False)]),
                    "PENDENTE":   len(df_f[df_f['STATUS_DISPLAY'].str.contains('Pendente', case=False, na=False)]),
                    "Aguardando": len(df_f[df_f['STATUS_DISPLAY'].str.contains('Aguardando', case=False)]),
                    "HOJE":       len(df_f[df_f['DATA_OBJ'] == hoje_br]),
                }

                st.markdown("<div class='kpi-deck-shell'>", unsafe_allow_html=True)
                cols_kpi = st.columns(7, gap="small") 
                for col, (filtro, label, key) in zip(cols_kpi, KPI_META):
                    is_active = st.session_state.filtro_kpi == filtro
                    dot_color = KPI_DOT_COLOR[filtro]
                    bg_color  = KPI_BG_COLOR[filtro]

                    borda = f"1px solid {dot_color}" if is_active else f"1px solid {bg_color}"
                    valor = n_vals[filtro]

                    partes = label.split(' ', 1)
                    emoji_card = partes[0]
                    texto_card = partes[1] if len(partes) > 1 else label

                    with col:
                        st.markdown(f"""
                            <div class="kpi-card" style="background-color: {bg_color}; border: {borda};">
                                <div style="position: absolute; right: -5px; bottom: -15px; font-size: 65px; opacity: 0.25; z-index: 0; line-height: 1; filter: drop-shadow(0px 2px 2px rgba(0,0,0,0.1));">
                                    {emoji_card}
                                </div>
                                <div style="position: relative; z-index: 1;">
                                    <div style="font-size: 11px; font-weight: 800; color: {dot_color}; text-transform: uppercase; letter-spacing: 0.5px;">
                                        {texto_card}
                                    </div>
                                    <div style="font-size: 28px; font-weight: 900; color: #0F172A; margin-top: 2px; line-height: 1;">
                                        {valor}
                                    </div>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)

                        # 🔥 CORREÇÃO 1: Botão padrão do Streamlit para resgatar o clique no CSS
                        if st.button(label, key=key, help=f"Filtrar por: {texto_card}", use_container_width=True):
                            st.session_state.filtro_kpi = filtro
                            st.rerun()

                st.markdown("""
                    <style>
                    div.st-key-kpi_total, div.st-key-kpi_entregue, div.st-key-kpi_frus, 
                    div.st-key-kpi_coletado, div.st-key-kpi_pend, div.st-key-kpi_aguardando, div.st-key-kpi_hoje {
                        margin-top: -106px !important; position: relative; z-index: 999; opacity: 0 !important;
                    }
                    div.st-key-kpi_total button, div.st-key-kpi_entregue button, div.st-key-kpi_frus button, 
                    div.st-key-kpi_coletado button, div.st-key-kpi_pend button, div.st-key-kpi_aguardando button, div.st-key-kpi_hoje button {
                        height: 102px !important; cursor: pointer !important;
                    }
                    </style>
                """, unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

                df_h = df_f[df_f['DATA_OBJ'] == hoje_br]
                if not df_h.empty:
                    n_fim = len(df_h[df_h['STATUS_DISPLAY'].str.contains('Entregue|Insucesso|Ocorrência|Cancelado|Recusado|Coletado|Em Transferência', case=False, na=False)])
                    n_tot  = len(df_h)
                    pct    = round((n_fim / n_tot) * 100) if n_tot else 0
                else:
                    n_fim = 0
                    n_tot = 0
                    pct = 0

                # Determinar a cor dinâmica baseada no percentual (Bateria)
                if pct <= 30:
                    cor_bateria = "#ef4444"  # Vermelho (Baixo)
                    status_class = "low"
                    status_label = "⚠️ Baixo Progresso"
                elif pct <= 70:
                    cor_bateria = "#f59e0b"  # Amarelo/Laranja (Médio)
                    status_class = "medium"
                    status_label = "⏳ Em Progresso"
                else:
                    cor_bateria = "#22c55e"  # Verde (Bom/Excelente)
                    status_class = "high"
                    status_label = "✅ Excelente"

                # Novo SVG Circular para Progresso com Caixa de Status
                bateria_html = f"""<div class="progress-block-sidebar">
<div class="progress-block-sidebar-content" style="text-align: center;">
<div class="progress-title-sidebar" style="margin-bottom: 12px;">&#128267; Progresso de Hoje</div>
<div style="position: relative; width: 112px; height: 112px; margin: 0 auto;">
<svg viewBox="0 0 36 36" style="width: 100%; height: 100%; display: block;">
<path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="#f1f5f9" stroke-width="3.5" stroke-linecap="round" />
<path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="{cor_bateria}" stroke-width="3.5" stroke-dasharray="{pct}, 100" stroke-linecap="round" style="transition: stroke-dasharray 1s ease-out, stroke 0.5s ease;" />
</svg>
<div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); display: flex; flex-direction: column; align-items: center; justify-content: center;">
<div style="font-size: 26px; font-weight: 900; color: #0f172a; line-height: 1;">{pct}%</div>
</div>
</div>
<div class="progress-status-box {status_class}">
<div class="progress-status-number">{n_fim}/{n_tot}</div>
<div class="progress-status-label">{status_label}</div>
</div>
<div class="progress-text-sidebar" style="margin-top: 4px; font-size: 11px; font-weight: 500; color: #64748b;">
Pedidos movimentados hoje
</div>
</div>
</div>"""

                st.sidebar.markdown(bateria_html, unsafe_allow_html=True)

                st.sidebar.markdown("<br>", unsafe_allow_html=True)
                if st.sidebar.button("🚪 Sair com Segurança", use_container_width=True, type="secondary", key="btn_logout_sidebar"):
                    st.session_state.logado = False
                    st.query_params.clear() 
                    st.rerun()



                st.markdown("<div class='toolbar-shell'>", unsafe_allow_html=True)
                col_busca, col_btn_refresh, col_btn_busca, col_export = st.columns([6, 0.55, 1, 1], gap="small")
                with col_busca:
                    st.text_input(
                        "Buscar",
                        placeholder="🔎 Buscar por pedido, laboratório, cidade...",
                        key="busca_grid_input",
                        label_visibility="collapsed",
                        on_change=aplicar_busca_grid
                    )
                with col_btn_refresh:
                    if st.button("⟳", use_container_width=True, key="btn_refresh_grid", help="Atualizar dados"):
                        carregar_dados_nuvem.clear()
                        st.rerun()
                with col_btn_busca:
                    if st.button("🔎 Buscar", use_container_width=True, key="btn_busca_grid"):
                        aplicar_busca_grid()
                with col_export:
                    holder_download = st.empty()
                st.markdown("</div>", unsafe_allow_html=True)

                df_grid = df_f.copy()
                
                if st.session_state.filtro_kpi != "TODOS":
                    if st.session_state.filtro_kpi == "HOJE":
                        df_grid = df_grid[df_grid['DATA_OBJ'] == hoje_br]
                    elif st.session_state.filtro_kpi == "PENDENTE":
                        df_grid = df_grid[df_grid['STATUS_DISPLAY'].str.contains('Pendente', case=False, na=False)]
                    elif st.session_state.filtro_kpi == "COLETADO":
                        df_grid = df_grid[df_grid['STATUS_DISPLAY'].str.contains('Coletado|Rota', case=False, na=False)]
                    elif st.session_state.filtro_kpi == "FRUSTRADA":
                        df_grid = df_grid[df_grid['STATUS_DISPLAY'].str.contains('Insucesso|Ocorrência|Cancelado|Recusado', case=False, na=False)]
                    elif st.session_state.filtro_kpi == "ENTREGUE":
                        df_grid = df_grid[df_grid['STATUS_DISPLAY'].str.contains('Entregue|Conferido', case=False, na=False)]
                    else:
                        df_grid = df_grid[df_grid['STATUS_DISPLAY'].str.contains(st.session_state.filtro_kpi, case=False, na=False)]

                busca_aplicada = st.session_state.busca_grid_aplicada
                if busca_aplicada:
                    df_grid = df_grid[df_grid.astype(str).apply(
                        lambda x: x.str.lower().str.contains(busca_aplicada.lower(), na=False, regex=False)
                    ).any(axis=1)]

                if not df_grid.empty:
                    df_grid['PRIORIDADE'] = df_grid['STATUS_DISPLAY'].apply(definir_prioridade_portal)
                    
                    df_grid = df_grid.sort_values(
                        by=['DATA_OBJ', 'PRIORIDADE', 'PEDIDO'], 
                        ascending=[False, True, False]
                    ).drop(columns=['PRIORIDADE'])

                    df_final = df_grid.copy()
                    df_final['COMPROVANTE'] = df_final['FOTO_FINAL'].apply(tratar_foto)
                    
                    # 🔥 A LUPA ESTÁ NO FINAL E ÚNICA 🔥
                    df_final['ACAO'] = '🔍 Abrir'

                    if 'UF' not in df_final.columns:
                        df_final['UF'] = ""

                    df_final['CIDADE_UF'] = df_final.apply(
                        lambda r: f"{str(r.get('CIDADE','')).strip()}/{str(r.get('UF','')).strip()}" if str(r.get('UF', '')).strip() and str(r.get('UF', '')).upper() != 'NAN' else str(r.get('CIDADE', '')).strip(),
                        axis=1
                    )

                    # 🔥 ENCURTANDO O ANO NAS DATAS DA GRID E REMOVENDO HORA DA ENTREGA 🔥
                    for col in ['DATA', 'DATA_EFETIVA', 'DATA_LIMITE']:
                        if col in df_final.columns:
                            if col == 'DATA_EFETIVA':
                                df_final[col] = df_final[col].astype(str).apply(lambda x: x.split(' ')[0] if x and str(x).lower() != 'nan' else '')
                            df_final[col] = df_final[col].astype(str).apply(lambda x: re.sub(r'/20(\d{2})(?!\d)', r'/\1', x))

                    for col in df_final.columns:
                        df_final[col] = df_final[col].astype(str).replace(["nan", "NaN", "None", "none", "<NA>", "NaT"], "")

                    # DETALHES RETIRADO DA LISTA VISÍVEL DA GRID (Isso garante que ela fique escondida na tabela e vá apenas para o Pop-up)
                    colunas_visiveis = [
                        'DATA', 'PEDIDO', 'LABORATORIO', 'BAIRRO', 'CIDADE_UF',
                        'DATA_LIMITE', 'DATA_EFETIVA', 'STATUS_DISPLAY',
                        'COMPROVANTE', 'ACAO'
                    ]

                    if st.session_state.cliente == "LOGISTICA.LABEST":
                        colunas_visiveis.insert(3, 'CNPJ')

                    colunas_visiveis = [c for c in colunas_visiveis if c in df_final.columns]

                    link_jscode = JsCode("""
                    class EmojiLinkRenderer {
                      init(params) {
                        this.eGui = document.createElement('div');
                        this.eGui.style.cssText = 'display: flex; justify-content: center; align-items: center; height: 100%;';
                        
                        if (params.value && params.value !== '') {
                          let a = document.createElement('a');
                          a.href = params.value;
                          a.target = '_blank';
                          a.innerHTML = '📷';
                          a.title = 'Clique para abrir o anexo completo';
                          a.style.cssText = 'text-decoration: none; font-size: 20px; transition: transform 0.2s; cursor: pointer;';
                          
                          let previewContainer = document.createElement('div');
                          previewContainer.style.cssText = 'position: fixed; display: none; z-index: 99999; pointer-events: none;';
                          
                          let preview = document.createElement('img');
                          preview.src = params.value;
                          preview.style.cssText = 'max-width: 350px; max-height: 350px; border-radius: 12px; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.4); border: 3px solid white; display: block;';
                          
                          let timeOverlay = document.createElement('div');
                          let statusText = params.data && params.data.STATUS_DISPLAY ? params.data.STATUS_DISPLAY : '';
                          timeOverlay.innerHTML = statusText;
                          timeOverlay.style.cssText = 'position: absolute; bottom: 10px; left: 50%; transform: translateX(-50%); background: rgba(15, 23, 42, 0.9); color: #fff; padding: 5px 12px; border-radius: 99px; font-family: Inter, sans-serif; font-size: 12px; font-weight: bold; white-space: nowrap; box-shadow: 0 4px 10px rgba(0,0,0,0.3);';

                          previewContainer.appendChild(preview);
                          if (statusText) { previewContainer.appendChild(timeOverlay); }
                          document.body.appendChild(previewContainer);
                          
                          a.onmouseover = (e) => {
                            a.style.transform = 'scale(1.3)';
                            previewContainer.style.display = 'block';
                            previewContainer.style.left = (e.clientX + 20) + 'px';
                            previewContainer.style.top = (e.clientY + 20) + 'px';
                          };
                          
                          a.onmousemove = (e) => {
                            previewContainer.style.left = (e.clientX + 20) + 'px';
                            previewContainer.style.top = (e.clientY + 20) + 'px';
                          };
                          
                          a.onmouseout = () => {
                            a.style.transform = 'scale(1)';
                            previewContainer.style.display = 'none';
                          };

                          this.eGui.appendChild(a);
                          this.previewElement = previewContainer; 
                        }
                      }
                      getGui() { return this.eGui; }
                      
                      destroy() {
                        if (this.previewElement && this.previewElement.parentNode) {
                          this.previewElement.parentNode.removeChild(this.previewElement);
                        }
                      }
                    }
                    """)

                    status_jscode = JsCode("""
                    class StatusBadgeRenderer {
                      init(params) {
                        this.eGui = document.createElement('div');
                        this.eGui.style.cssText = 'display: flex; align-items: center; height: 100%;';
                        
                        let badge = document.createElement('span');
                        badge.style.cssText = 'display: inline-flex; align-items: center; justify-content: center; padding: 4px 10px; border-radius: 99px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; height: 22px;';
                        
                        let status = params.value ? params.value.toUpperCase() : '';
                        let text = params.value || '';
                        
                        if (status.includes('ENTREGUE') || status.includes('CONFERIDO')) {
                          badge.style.backgroundColor = '#dcfce7';
                          badge.style.color = '#166534'; 
                          badge.style.border = '1px solid #bbf7d0';
                        } else if (status.includes('FRUSTRADA') || status.includes('PROBLEMA') || status.includes('ATRASADO') || status.includes('RECUSA')) {
                          badge.style.backgroundColor = '#fee2e2';
                          badge.style.color = '#991b1b'; 
                          badge.style.border = '1px solid #fecaca';
                        } else if (status.includes('COLETADO') || status.includes('ROTA')) {
                          badge.style.backgroundColor = '#dbeafe';
                          badge.style.color = '#1e40af'; 
                          badge.style.border = '1px solid #bfdbfe';
                        } else if (status.includes('PENDENTE')) {
                          badge.style.backgroundColor = '#fef3c7';
                          badge.style.color = '#b45309'; 
                          badge.style.border = '1px solid #fde68a';
                        } else {
                          badge.style.backgroundColor = '#f1f5f9';
                          badge.style.color = '#475569'; 
                          badge.style.border = '1px solid #e2e8f0';
                        }
                        
                        badge.innerText = text;
                        this.eGui.appendChild(badge);
                      }
                      getGui() { return this.eGui; }
                    }
                    """)

                    gb = GridOptionsBuilder.from_dataframe(df_final[colunas_visiveis])
                    gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=50)
                    gb.configure_default_column(resizable=True, filterable=True, sortable=True)

                    gb.configure_selection(
                        selection_mode="single", 
                        use_checkbox=False, 
                        suppressRowClickSelection=False,
                        suppressRowDeselection=True # Impede bugs
                    )

                    # Chave dinâmica para limpar a grid ao fechar a foto
                    if 'grid_key' not in st.session_state:
                        st.session_state.grid_key = 0

                    gb.configure_column("PEDIDO", header_name="📦 Pedido", width=120)
                    gb.configure_column("DATA", header_name="📅 Data Coleta", width=130)
                    gb.configure_column("LABORATORIO", header_name="🔬 Ponto de Coleta")
                    gb.configure_column("BAIRRO", header_name="🏘️ Bairro")
                    if 'CNPJ' in colunas_visiveis:
                        gb.configure_column("CNPJ", header_name="🏢 CNPJ")
                    gb.configure_column("CIDADE_UF", header_name="📍 Cidade / UF")
                    gb.configure_column("DATA_LIMITE", header_name="🎯 Previsão", width=120)
                    gb.configure_column("DATA_EFETIVA", header_name="🏁 Entrega", width=120)
                    gb.configure_column("STATUS_DISPLAY", header_name="🚦 Status", cellRenderer=status_jscode, width=150)
                    gb.configure_column("COMPROVANTE", header_name="📎 Anexo", cellRenderer=link_jscode, width=100)
                    gb.configure_column("ACAO", header_name="💬 Atualizações", width=120, cellStyle={'cursor': 'pointer', 'color': '#3b82f6', 'font-weight': 'bold'})

                    gridOptions = gb.build()

                    custom_css = {
                        ".ag-header": {
                            "background": "linear-gradient(180deg, #f8fafc 0%, #e2e8f0 100%) !important",
                            "border-bottom": "1px solid #cbd5e1 !important",
                            "min-height": "48px !important"
                        },
                        ".ag-header-cell-text": {
                            "color": "#0f172a !important",
                            "font-weight": "800 !important",
                            "font-size": "12px !important",
                            "text-transform": "uppercase !important",
                            "letter-spacing": "0.4px !important"
                        },
                        ".ag-header-cell": {
                            "border-right": "1px solid #dbe3ef !important",
                            "padding-top": "6px !important",
                            "padding-bottom": "6px !important"
                        },
                        ".ag-cell": {
                            "border-right": "1px solid #eef2f7 !important",
                            "border-bottom": "1px solid #eef2f7 !important",
                            "display": "flex",
                            "align-items": "center",
                            "font-size": "13px !important"
                        },
                        ".ag-cell-focus": {"border": "none !important", "outline": "none !important"},
                        ".ag-row:hover": {
                            "background-color": "#dbeafe !important",
                            "cursor": "pointer",
                            "transition": "all 0.2s",
                            "box-shadow": "inset 3px 0 0 #2563eb"
                        },
                        ".ag-row": {
                            "transition": "background-color 0.22s ease"
                        },
                        ".ag-row-odd": {
                            "background": "linear-gradient(90deg, #ffffff 0%, #fbfdff 100%) !important"
                        },
                        ".ag-row-even": {
                            "background": "linear-gradient(90deg, #f8fafc 0%, #f1f5f9 100%) !important"
                        },
                        ".ag-paging-panel": {
                            "border-top": "1px solid #dbe3ef !important",
                            "background": "#f8fafc !important",
                            "padding": "8px 12px !important"
                        },
                        ".ag-theme-alpine": {
                            "--ag-font-family": "Inter, sans-serif",
                            "--ag-font-size": "13px",
                            "--ag-row-height": "38px",
                            "--ag-header-height": "42px",
                            "border": "1px solid #dbe3ef",
                            "border-radius": "12px",
                            "overflow": "hidden",
                            "box-shadow": "0 8px 22px rgba(15, 23, 42, 0.08)"
                        },
                        ".ag-body-viewport": {
                            "overflow-y": "auto !important",
                            "overflow-x": "hidden !important"
                        },
                        ".ag-body-horizontal-scroll": {
                            "overflow-x": "auto !important"
                        }
                    }

                    # 🔒 DETECTA FECHAMENTO DO MODAL POR X OU ESC (ANTES de renderizar a grid)
                    # Se o modal estava aberto antes, mas agora não deveria ser renderizado, significa que foi fechado por outro meio
                    if st.session_state.modal_renderizado_antes and not (st.session_state.modal_aberto and st.session_state.pedido_modal):
                        st.session_state.modal_fechado = True
                        st.session_state.pedido_modal = None
                        st.session_state.linha_clicada = None
                        st.session_state.ignorar_selecao_grid = True  # Ignora a seleção que está na grid
                        st.session_state.modal_renderizado_antes = False
                        st.session_state.grid_key += 1 # 🔥 Limpa a seleção da grid
                        st.rerun()  # Força rerun para aplicar a flag ANTES de renderizar a grid

                    ag_response = AgGrid(
                        df_final[colunas_visiveis],
                        gridOptions=gridOptions,
                        theme="alpine",
                        columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS,
                        height=625,
                        allow_unsafe_jscode=True,
                        custom_css=custom_css,
                        update_mode="SELECTION_CHANGED",
                        key=f"grid_portal_{st.session_state.grid_key}"
                    )
                    
                    # 🔥 CONTROLE BLINDADO DE SELEÇÃO E MODAL 🔥
                    selected_rows = ag_response.get('selected_rows')
                    
                    # Se acabamos de fechar o modal, ignora qualquer seleção anterior na grid
                    if st.session_state.ignorar_selecao_grid:
                        st.session_state.ignorar_selecao_grid = False
                        selected_rows = None  # Força a grid a não ter seleção
                    
                    # Se o modal foi fechado recentemente, ignora a seleção anterior e desativa a flag
                    if st.session_state.modal_fechado:
                        st.session_state.modal_fechado = False
                        st.session_state.modal_aberto = False
                    elif selected_rows is not None and len(selected_rows) > 0:
                        if isinstance(selected_rows, pd.DataFrame):
                            dados_da_linha = selected_rows.iloc[0].to_dict()
                        else:
                            dados_da_linha = selected_rows[0]
                        
                        pedido_atual = dados_da_linha.get('PEDIDO')
                        
                        # Se o cliente clicar num pedido, a gente abre o Modal
                        if st.session_state.pedido_modal != pedido_atual:
                            st.session_state.linha_clicada = pedido_atual
                            st.session_state.pedido_modal = pedido_atual
                            st.session_state.modal_aberto = True
                            st.rerun()
                    else:
                        # Se a Grid devolver "vazio" (porque o usuário clicou de novo na mesma linha para desmarcar)
                        # Nós limpamos a memória para permitir um novo clique!
                        st.session_state.modal_aberto = False
                        st.session_state.pedido_modal = None
                        st.session_state.linha_clicada = None

                    # Abre o Modal
                    if st.session_state.modal_aberto and st.session_state.pedido_modal:
                        # Sempre buscar na df_final inteira, pois a grid omite dados do dicionário
                        dados_completos_linha = df_final[df_final['PEDIDO'] == st.session_state.pedido_modal].iloc[0].to_dict()
                        st.session_state.modal_renderizado_antes = True  # Marca que o modal foi renderizado
                        
                        # 🔥 MEGA OTIMIZAÇÃO: Filtra apenas o histórico do laboratório clicado ANTES de carregar a janela
                        lab_alvo = dados_completos_linha.get('LABORATORIO', '')
                        df_hist_leve = df_final[df_final['LABORATORIO'] == lab_alvo] if lab_alvo else pd.DataFrame()
                        
                        modal_detalhes_pedido(dados_completos_linha, df_hist_leve)
                        
                        # Evita reabrir automaticamente em refresh quando o usuário fecha pelo X.
                        # O próximo clique na grid volta a abrir normalmente.
                        st.session_state.modal_aberto = False


                    # ── EXPORTAÇÃO CSV ────────
                    mapa_csv = {
                        'PEDIDO': 'Pedido',
                        'DATA': 'Data Coleta',
                        'HORA_LIMPA': 'Hora Coleta',  # 🔥 NOVA COLUNA ADICIONADA AQUI 🔥
                        'LABORATORIO': 'Ponto de Coleta',
                        'CIDADE': 'Cidade',
                        'UF': 'UF',
                        'DATA_LIMITE': 'Previsão',
                        'DATA_EFETIVA': 'Entrega',
                        'STATUS_DISPLAY': 'Status',
                        'DETALHES': 'Atualizações'
                    }
                    
                    if st.session_state.cliente == "LOGISTICA.LABEST":
                        mapa_csv['CNPJ'] = 'CNPJ'

                    colunas_csv_finais = [c for c in mapa_csv.keys() if c in df_final.columns]
                    df_export = df_final[colunas_csv_finais].rename(columns=mapa_csv)

                    if 'CNPJ' in df_export.columns:
                        df_export['CNPJ'] = df_export['CNPJ'].astype(str).apply(lambda x: f'="{x}"' if x.strip() else '')

                    csv = df_export.to_csv(index=False, sep=';').encode('utf-8-sig')
                    
                    with holder_download:
                        st.download_button(
                            "⬇️ CSV",
                            data=csv,
                            file_name=f"Relatorio_{st.session_state.cliente}.csv",
                            use_container_width=True,
                            help="Exportar relatório simplificado",
                            key="btn_download_grid_limpo"
                        )

                    with holder_exportar:
                        st.download_button(
                             "📥 Exportar Relatório",
                            data=csv,
                            file_name=f"Relatorio_{st.session_state.cliente}.csv",
                            use_container_width=True,
                            key="btn_export_sidebar_limpo"
                        )

        # ===================================================
        # ABA 2 · AUTOATENDIMENTO DE COLETA
        # ===================================================
        with tab_solicitar:
            st.markdown("### ➕ Nova Solicitação de Coleta")
            st.markdown(
                "<p style='color:#64748b;font-size:13px;margin-top:-8px;margin-bottom:16px;'>"
                "Escolha o ponto de coleta desejado. Solicitações após as 10:00 são agendadas "
                "automaticamente para o próximo dia útil."
                "</p>",
                unsafe_allow_html=True
            )

            df_locais = carregar_base_locais()
            if df_locais.empty:
                st.warning("O banco de dados de locais de coleta ainda não foi sincronizado.")
            else:
                df_cli_locais = df_locais[df_locais['TOMADOR'].str.upper().str.strip() == nome_tomador_oficial.upper().strip()]
                
                if df_cli_locais.empty:
                    st.warning(f"Nenhum ponto de coleta cadastrado para {nome_tomador_oficial}.")
                else:
                    with st.container(border=False):
                        with st.form("form_nova_coleta", clear_on_submit=True):
                            lista_labs = sorted(df_cli_locais['LABORATORIO'].unique().tolist())
                            lab_sel    = st.selectbox(
                                "📍 Selecione o Ponto de Coleta (Laboratório):",
                                ["Selecione..."] + lista_labs
                            )

                            if lab_sel != "Selecione...":
                                local_data  = df_cli_locais[df_cli_locais['LABORATORIO'] == lab_sel].iloc[0]
                                end_fmt = f"{local_data.get('ENDERECO','')}, {local_data.get('NUMERO','')} — {local_data.get('BAIRRO','')}"
                                cid_fmt = f"{local_data.get('CIDADE','')}/{local_data.get('UF','')} | CEP: {local_data.get('CEP','')}"
                                st.markdown(f"""
                                    <div style="background:#f0f9ff;border-left:4px solid #3b82f6; padding:12px 15px;border-radius:4px;margin-bottom:15px;">
                                        <p style="margin:0;font-size:11px;color:#64748b;font-weight:700;">
                                            DESTINO CONFIRMADO
                                        </p>
                                        <p style="margin:4px 0 0;font-size:13px;color:#0f172a;">
                                            <b>{end_fmt}</b><br>{cid_fmt}
                                        </p>
                                    </div>
                                """, unsafe_allow_html=True)

                            agora_sp    = datetime.now(FUSO_BR)
                            data_minima = agora_sp.date() + timedelta(days=1)  # 🔥 Sempre D+1 em dias úteis
                            
                            while data_minima.weekday() >= 5:
                                data_minima += timedelta(days=1)

                            c1, _ = st.columns(2)
                            data_coleta = c1.date_input(
                                "📅 Data Desejada para Coleta:",
                                min_value=data_minima,
                                value=data_minima,
                                format="DD/MM/YYYY"
                            )
                            obs = st.text_area(
                                "📝 Observações / Instruções (Opcional):",
                                placeholder="Ex: Procurar por Fulano, coletar na recepção...",
                                height=100
                            )

                            if st.form_submit_button("🚀 Enviar Solicitação ao Torre de Controle.", type="primary", use_container_width=True):
                                if lab_sel == "Selecione...":
                                    st.error("⚠️ Selecione um Ponto de Coleta válido.")
                                elif data_coleta.weekday() >= 5:
                                    st.error("⚠️ Coletas não são realizadas aos finais de semana. Escolha um dia útil.")
                                else:
                                    with st.spinner("Registrando pedido e notificando o Torre de Controle..."):
                                        try:
                                            gc       = conectar_banco_seguro()
                                            planilha = gc.open("DB_IGO_Logistica")
                                            aba_m    = planilha.worksheet("Memoria_Sistema")
                                            dados_m  = aba_m.get_all_values()

                                            df_m_temp = pd.DataFrame(dados_m[1:], columns=dados_m[0])
                                            
                                            # 🛑 INÍCIO DA TRAVA DE DUPLICIDADE (IDEMPOTÊNCIA) 🛑
                                            data_formatada = data_coleta.strftime("%d/%m/%Y")
                                            
                                            filtro_duplicidade = df_m_temp[
                                                (df_m_temp['TOMADOR'] == nome_tomador_oficial) &
                                                (df_m_temp['LABORATORIO'] == local_data['LABORATORIO']) &
                                                (df_m_temp['DATA'] == data_formatada) &
                                                (df_m_temp['STATUS'] == 'AGUARDANDO APROVAÇÃO')
                                            ]
                                            
                                            if not filtro_duplicidade.empty:
                                                st.warning("⚠️ Solicitação já recebida! Já existe um pedido idêntico aguardando aprovação para este local e data.")
                                                st.stop() # Interrompe o script para impedir a criação do pedido duplicado
                                            # 🛑 FIM DA TRAVA 🛑

                                            prox_id = obter_proximo_id(df_m_temp)

                                            nova_linha_dict = {
                                                'DATA':       data_formatada,
                                                'PEDIDO':     str(prox_id),
                                                'TOMADOR':    nome_tomador_oficial,
                                                'LABORATORIO':local_data['LABORATORIO'],
                                                'CNPJ':       local_data.get('CNPJ', ''),
                                                'ENDERECO':   local_data.get('ENDERECO', ''),
                                                'NUMERO':     local_data.get('NUMERO', ''),
                                                'BAIRRO':     local_data.get('BAIRRO', ''),
                                                'CIDADE':     local_data.get('CIDADE', ''),
                                                'UF':         local_data.get('UF', ''),
                                                'CEP':        local_data.get('CEP', ''),
                                                'STATUS':     'AGUARDANDO APROVAÇÃO',
                                                'OBSERVACOES':obs
                                            }

                                            cabecalhos   = dados_m[0]
                                            linha_append = [nova_linha_dict.get(c, "") for c in cabecalhos]
                                            aba_m.append_row(linha_append, value_input_option='USER_ENTERED')

                                            texto_zap = (
                                                f"🔔 *NOVA SOLICITAÇÃO DE COLETA* 🔔\n\n"
                                                f"🏢 *Cliente:* {nome_tomador_oficial}\n"
                                                f"🔬 *Local:* {local_data['LABORATORIO']}\n"
                                                f"📍 *Cidade:* {local_data.get('CIDADE','')} - {local_data.get('UF','')}\n"
                                                f"📅 *Data Desejada:* {data_coleta.strftime('%d/%m/%Y')}\n"
                                                f"📦 *ID do Pedido:* {prox_id}\n\n"
                                                f"Acesse o painel do Torre de Controle para aprovar ou recusar."
                                            )
                                            numeros_notificacao = ["5511947996371", "5511997163954", "5511984911231"]
                                            for numero in numeros_notificacao:
                                                enviar_whatsapp_zapi_cliente(numero, texto_zap)

                                            st.success(f"🎉 Pedido #{prox_id} criado para {data_coleta.strftime('%d/%m/%Y')}. Aguardando aprovação do Torre de Controle.")
                                            carregar_dados_nuvem.clear()

                                        except Exception as e:
                                            st.error(f"Erro ao processar solicitação: {e}")

        # ===================================================
        # ABA 3 · ACOMPANHAMENTO DOS CHAMADOS
        # ===================================================
        with tab_chamados:
            st.markdown("### 🎧 Histórico de Atendimento")
            st.markdown("<p style='color:#64748b;font-size:13px;margin-top:-8px;'>Acompanhe a resolução das suas solicitações junto ao nosso Torre de Controle.</p>", unsafe_allow_html=True)
            
            try:
                gc = conectar_banco_seguro()
                planilha = gc.open("DB_IGO_Logistica")
                aba_chamados = planilha.worksheet("Base_Chamados")
                dados_tkt = aba_chamados.get_all_values()
                
                if len(dados_tkt) > 1:
                    df_tkt = pd.DataFrame(dados_tkt[1:], columns=dados_tkt[0])
                    df_cli_tkt = df_tkt[df_tkt['TOMADOR'] == nome_tomador_oficial]
                    
                    if df_cli_tkt.empty:
                        st.info("Você ainda não possui nenhum chamado de suporte aberto.")
                    else:
                        df_cli_tkt = df_cli_tkt.iloc[::-1]
                        
                        for idx, row in df_cli_tkt.iterrows():
                            cor_borda = "#3b82f6" if "ANÁLISE" in row['STATUS'] else "#22c55e"
                            fundo_resp = "#f8fafc" if "ANÁLISE" in row['STATUS'] else "#f0fdf4"
                            
                            st.markdown(f"""
                            <div style="border: 1px solid #e2e8f0; border-left: 4px solid {cor_borda}; border-radius: 8px; padding: 15px; margin-bottom: 15px; background: white;">
                                <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                                    <span style="font-weight: 800; color: #0f172a;">🎫 Ticket {row['TICKET']}</span>
                                    <span style="font-size: 12px; font-weight: 700; background: #f1f5f9; padding: 4px 10px; border-radius: 99px;">{row['STATUS']}</span>
                                </div>
                                <p style="font-size: 12px; color: #64748b; margin-bottom: 5px;"><b>Data:</b> {row['DATA']} | <b>Pedido Ref:</b> {row['PEDIDO']}</p>
                                <p style="font-size: 14px; color: #334155;"><b>Sua Mensagem:</b> {row['MENSAGEM']}</p>
                                <div style="background: {fundo_resp}; padding: 12px; border-radius: 6px; margin-top: 10px; border: 1px solid #e2e8f0;">
                                    <p style="margin: 0; font-size: 13px; color: #0f172a;"><b>Resposta do Torre de Controle:</b> {row['RESPOSTA'] if row.get('RESPOSTA', '') else '<i>Aguardando análise de um de nossos agentes...</i>'}</p>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                else:
                    st.info("Nenhum chamado registrado no banco de dados.")
            except Exception:
                st.info("A base de chamados será inicializada na sua primeira solicitação.")
