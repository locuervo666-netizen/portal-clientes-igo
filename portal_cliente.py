import streamlit as st
import pandas as pd
import gspread
import os
import urllib.parse
import json
import requests
import re
import random
import streamlit.components.v1 as components
from datetime import datetime, timedelta, timezone
from google.oauth2.credentials import Credentials

# 🚀 IMPORTAÇÃO DO AGGRID (Agora com suporte a JavaScript para o link da foto)
from st_aggrid import AgGrid, GridOptionsBuilder, ColumnsAutoSizeMode, JsCode

FUSO_BR = timezone(timedelta(hours=-3))
LOGO_IGO = "https://i.postimg.cc/x84nnjjq/IGO-LOGO.png"

# =======================================================
# 🎨 1. CONFIGURAÇÃO DA PÁGINA E CSS BASE
# =======================================================
st.set_page_config(
    page_title="Monitoramento IGO Logística",
    layout="wide",
    page_icon="🚚",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    [data-testid="stAppViewContainer"] {
        transition: background-color 0.3s ease;
        font-family: 'Inter', sans-serif;
        background-color: #FFFFFF !important;
    }

    /* ── SIDEBAR ── */
    [data-testid="stSidebar"],
    [data-testid="stSidebar"] > div:first-child {
        background-color: #ffffff !important;
        border-right: 1px solid #e2e8f0 !important;
    }
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] h3 {
        color: #1e293b !important;
    }
    [data-testid="stSidebar"] [data-testid="stForm"] {
        background-color: #f8fafc !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 12px !important;
        padding: 15px !important;
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

    /* ── BOTÃO PRIMÁRIO (LOGIN) AZUL PREMIUM ── */
    button[kind="primary"] {
        background-color: #3b82f6 !important;
        border-color: #3b82f6 !important;
        color: #ffffff !important;
        transition: all 0.3s ease !important;
    }
    
    button[kind="primary"]:hover {
        background-color: #2563eb !important;
        border-color: #2563eb !important;
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4) !important;
    }

    /* ── LAYOUT ── */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {background-color: transparent !important;}
    .block-container {
        padding-top: 1.2rem !important;
        padding-bottom: 1rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
    }

    /* ── KPI CARDS ── */
    .kpi-card {
        border-radius: 12px;
        padding: 14px 12px 12px;
        text-align: center;
        cursor: pointer;
        transition: all 0.2s ease;
        position: relative;
        overflow: hidden;
    }
    .kpi-card:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        transform: translateY(-2px);
    }
    .kpi-card.active {
        box-shadow: 0 0 0 2px #3b82f6;
    }
    .kpi-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin: 0 auto 8px;
    }
    .kpi-val {
        font-size: 26px;
        font-weight: 800;
        line-height: 1;
        color: #0f172a;
    }
    .kpi-label {
        font-size: 10px;
        font-weight: 600;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-top: 5px;
    }

    /* ── HEADER ── */
    .header-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 18px;
        padding-bottom: 14px;
        border-bottom: 1.5px solid #e2e8f0;
    }
    .header-title {
        font-size: 20px;
        font-weight: 800;
        color: #0f172a;
        letter-spacing: -0.3px;
    }
    .header-subtitle {
        font-size: 13px;
        color: #64748b;
        margin-top: 2px;
    }
    .sync-status {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 12px;
        color: #10b981;
        font-weight: 600;
        background: #f0fdf4;
        border: 1px solid #bbf7d0;
        border-radius: 99px;
        padding: 5px 12px;
    }
    .sync-dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background: #10b981;
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.4; }
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

    /* ── SEARCH ROW ── */
    .search-export-row {
        display: flex;
        gap: 10px;
        align-items: flex-end;
        margin-bottom: 8px;
    }

    </style>
""", unsafe_allow_html=True)

CLIENTES_CONFIG = {
    "GRALAB": {
        "senha": "123",
        "logo": "https://cdn.awsli.com.br/2702/2702264/logo/gralab-rbuogsxve7.png",
        "filtro": "GRALAB"
    },
    "IGO_LOGISTICA": {
        "senha": "admin",
        "logo": LOGO_IGO,
        "filtro": "TODOS"
    },
    "LOGISTICA.LABEST": {
        "senha": "123",
        "logo": "logo_labest.png",
        "filtro": "LABEST"
    },
    "SYNVIA": {
        "senha": "123",
        "logo": LOGO_IGO,
        "filtro": "SYNVIA"
    },
    "LOGISTICA.BAT": {
        "senha": "123",
        "logo": "souza cruz.png",
        "filtro": "SOUZA CRUZ"
    }
}

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

@st.cache_data(ttl=30)
def carregar_dados_nuvem():
    try:
        gc = conectar_banco_seguro()
        if not gc:
            return pd.DataFrame()
        planilha = gc.open("DB_IGO_Logistica")
        aba_m = planilha.worksheet("Memoria_Sistema")
        dados_m = aba_m.get_all_values()

        if len(dados_m) > 1:
            df = pd.DataFrame(dados_m[1:], columns=dados_m[0])
            df.columns = df.columns.str.strip().str.upper()
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

                    # 🔥 PASSO 1 AQUI: ADICIONAMOS AS NOVAS COLUNAS
                    cols_to_extract = ['PEDIDO']
                    if 'STATUS'       in df_app.columns: cols_to_extract.append('STATUS')
                    if 'OBSERVACOES'  in df_app.columns: cols_to_extract.append('OBSERVACOES')
                    if 'FOTO'         in df_app.columns: cols_to_extract.append('FOTO')
                    if 'FOTO_COLETA'  in df_app.columns: cols_to_extract.append('FOTO_COLETA')
                    if 'FOTO_ENTREGA' in df_app.columns: cols_to_extract.append('FOTO_ENTREGA')
                    if 'DATA'         in df_app.columns: cols_to_extract.append('DATA')
                    if 'DATA_ENTREGA' in df_app.columns: cols_to_extract.append('DATA_ENTREGA')
                    if 'RECEBEDOR'    in df_app.columns: cols_to_extract.append('RECEBEDOR')
                    
                    col_nome = None
                    for c in ['DETALHES', 'CONTATO', 'NOME', 'PESSOA', 'INFORMANTE']:
                        if c in df_app.columns:
                            cols_to_extract.append(c)
                            col_nome = c
                            break
                    
                    cols_to_extract = list(set(cols_to_extract))
                    df_app_clean = df_app[cols_to_extract].copy()

                    # 🔥 PASSO 2 AQUI: RENOMEAMOS PRO NOVO DICIONÁRIO
                    rename_dict = {
                        'STATUS': 'A_ST',
                        'OBSERVACOES': 'A_OB',
                        'FOTO': 'A_FO',
                        'FOTO_COLETA': 'A_FOTO_COL',
                        'FOTO_ENTREGA': 'A_FOTO_ENT',
                        'DATA': 'A_DT',
                        'DATA_ENTREGA': 'A_DT_ENTREGA',
                        'RECEBEDOR': 'A_REC'
                    }
                    if col_nome:
                        rename_dict[col_nome] = 'A_CONTATO'
                    df_app_clean.rename(columns=rename_dict, inplace=True)

                    # Inteligência de Romaneios
                    rom_mask = df_app_clean['PEDIDO'].str.startswith('ROM-', na=False)
                    rom_dict = df_app_clean[rom_mask].set_index('PEDIDO').to_dict('index')

                    df_app_clean.drop_duplicates(subset=['PEDIDO'], keep='last', inplace=True)

                    df['PEDIDO'] = df['PEDIDO'].astype(str).str.strip()
                    df = pd.merge(df, df_app_clean, on='PEDIDO', how='left')

                    # Função de cruzamento robusto para Romaneios
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

                    # 🔥 PASSO 3 AQUI: REGRA DE OURO DA FOTO (COLETA > ENTREGA > GERAL)
                    def definir_foto_prioritaria(r):
                        f_col = get_app_val(r, 'A_FOTO_COL')
                        f_ent = get_app_val(r, 'A_FOTO_ENT')
                        f_gen = get_app_val(r, 'A_FO')
                        
                        if not f_col: f_col = str(r.get('FOTO_COLETA', '')).strip()
                        if not f_ent: f_ent = str(r.get('FOTO_ENTREGA', '')).strip()
                        if not f_gen: f_gen = str(r.get('FOTO', '')).strip()
                        
                        if f_col and f_col.upper() != 'NAN': return f_col
                        if f_ent and f_ent.upper() != 'NAN': return f_ent
                        if f_gen and f_gen.upper() != 'NAN': return f_gen
                        return ""

                    df['FOTO_FINAL'] = df.apply(definir_foto_prioritaria, axis=1)

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

            if 'DATA' in df.columns:
                df['DATA_OBJ'] = pd.to_datetime(
                    df['DATA'], format='%d/%m/%Y', errors='coerce'
                ).dt.date
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
        st.warning(f"Erro ao carregar locais: {e}")
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
    except Exception:
        return False

# ── Session State ──────────────────────────────────────
if 'logado'     not in st.session_state: st.session_state.logado     = False
if 'filtro_kpi' not in st.session_state: st.session_state.filtro_kpi = "TODOS"

# ── Helpers de status ──────────────────────────────────
def get_st(row):
    s = str(row.get('STATUS_RESOLVIDO', row.get('STATUS', ''))).strip().upper()
    if 'AGUARDANDO' in s: return '🔒 Aguardando Aprovação'
    if 'RECUSA'     in s: return '❌ Solicitação Recusada'
    if 'ENTREGUE'   in s: return '✅ Entregue'
    if 'COLETADO'   in s: return '📦 Coletado'
    if 'ROTA DE COLETA' in s: return '🚐 Rota de Coleta'
    if 'ROTA'       in s: return '🚚 Em Rota de Entrega'
    if 'CONFERIDO'  in s: return '☑️ Conferido'
    if 'FRUSTRADA'  in s: return '⚠️ Frustrada'
    if 'CANCELADO'  in s: return '🚫 Cancelado'
    if 'PROBLEMA'   in s: return '🚨 Problema'
    return '⏳ Pendente'

KPI_DOT_COLOR = {
    "TODOS":      "#3b82f6",
    "ENTREGUE":   "#22c55e",
    "FRUSTRADA":  "#ef4444", 
    "PENDENTE":   "#f59e0b",
    "Aguardando": "#64748b",
    "HOJE":       "#8b5cf6",
}

KPI_BG_COLOR = {
    "TODOS":      "#eff6ff",
    "ENTREGUE":   "#f0fdf4",
    "FRUSTRADA":  "#fef2f2",
    "PENDENTE":   "#fffbeb",
    "Aguardando": "#f8fafc",
    "HOJE":       "#f5f3ff",
}

KPI_META = [
    ("TODOS",      "📦 Total",        "kpi_total"),
    ("ENTREGUE",   "✅ Entregues",    "kpi_entregue"),
    ("FRUSTRADA",  "❌ Frustradas",   "kpi_frus"),
    ("PENDENTE",   "⏳ Pendentes",    "kpi_pend"),
    ("Aguardando", "⏱️ Aguard. CCO",  "kpi_aguardando"),
    ("HOJE",       "📅 Hoje",         "kpi_hoje"),
]

def get_detalhes(row):
    obs_master = str(row.get('OBSERVACOES', '')).strip()
    obs_app    = str(row.get('OBS_APP_FINAL', '')).strip()
    contato    = str(row.get('CONTATO_FINAL', '')).strip()
    recebedor  = str(row.get('RECEBEDOR_FINAL', '')).strip()
    status     = str(row.get('STATUS_DISPLAY', '')).upper()

    if 'ENTREGUE' in status:
        if recebedor: return f"Recebedor(a): {recebedor}"
        elif contato: return f"Recebedor(a): {contato}"
        else: return "-"

    if 'FRUSTRADA' in status or 'PROBLEMA' in status:
        obs_limpa = re.sub(r'\[COLETA:.*?\]', '', obs_app, flags=re.IGNORECASE).strip()
        if not obs_limpa:
            obs_limpa = re.sub(r'\[COLETA:.*?\]', '', obs_master, flags=re.IGNORECASE).strip()

        if obs_limpa and obs_limpa.upper() != 'NAN':
            texto = obs_limpa
            if contato and contato.upper() != 'NAN':
                texto += f" (Informante: {contato})"
            return texto
        elif contato and contato.upper() != 'NAN':
            return f"Motivo/Informante: {contato}"
        else:
            return obs_master if obs_master else "-"

    obs_final = obs_app if obs_app and obs_app.upper() != 'NAN' else obs_master
    if obs_final.upper() == 'NAN': obs_final = ""

    if not obs_final and not contato: return "-"
    if obs_final and contato and obs_final.upper() != contato.upper():
        return f"{obs_final} (Informante: {contato})"
    return obs_final if obs_final else f"Informante: {contato}"

def definir_prioridade_portal(status_str):
    s = str(status_str).upper()
    if 'ATRASADO'  in s: return 1
    if 'PENDENTE'  in s: return 2
    if 'COLETADO'  in s: return 3
    if 'ROTA'      in s: return 4
    if 'ENTREGUE'  in s: return 5
    return 6

def tratar_foto(x):
    xs = str(x).strip()
    if not xs or xs.upper() in ['NAN', 'NONE']:
        return ""
    if xs.startswith("http"):
        return xs
    return (
        f"https://www.appsheet.com/template/gettablefileurl"
        f"?appName=APPIGOLOGISTICA-153047553&tableName=App_Tarefas&fileName={xs}"
    )

# =======================================================
# 🔐 3. LOGIN
# =======================================================
if not st.session_state.logado:
    st.markdown("""
        <style>
        [data-testid="stAppViewContainer"] { background-color: #FFFFFF !important; }
        </style>
    """, unsafe_allow_html=True)

    _, c2, _ = st.columns([1, 1.1, 1])
    with c2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        with st.container(border=True):
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.image(LOGO_IGO, use_container_width=True)

            st.markdown(
                "<h3 style='text-align:center;color:#1e293b;margin-top:-10px;"
                "margin-bottom:20px;font-size:18px;font-weight:700;'>Portal do Cliente</h3>",
                unsafe_allow_html=True
            )

            u = st.text_input("👤 Usuário").upper().strip()
            s = st.text_input("🔒 Senha", type="password")
            st.markdown("<br>", unsafe_allow_html=True)

            if st.button("🚀 Acessar Sistema", type="primary", use_container_width=True):
                if u in CLIENTES_CONFIG and s == CLIENTES_CONFIG[u]["senha"]:
                    st.session_state.logado  = True
                    st.session_state.cliente = u
                    st.rerun()
                else:
                    st.error("❌ Credenciais Incorretas")

# =======================================================
# 🖥️ 4. PAINEL PRINCIPAL
# =======================================================
else:
    components.html(
        "<script>setTimeout(function(){ window.parent.location.reload(); }, 300000);</script>",
        height=0, width=0
    )

    conf              = CLIENTES_CONFIG[st.session_state.cliente]
    hoje_br           = datetime.now(FUSO_BR).date()
    nome_tomador_oficial = conf["filtro"] if conf["filtro"] != "TODOS" else "MATRIZ IGO"

    # ── SIDEBAR ────────────────────────────────────────
    with st.sidebar:
        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 4, 1])
        with col2:
            try:
                st.image(conf["logo"], use_container_width=True)
            except Exception:
                st.markdown(
                    f"<h3 style='text-align:center;'>{st.session_state.cliente}</h3>",
                    unsafe_allow_html=True
                )
        
        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("<p style='font-size: 11px; font-weight: 800; color: #64748B; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 5px;'>Filtros de Visão</p>", unsafe_allow_html=True)
        with st.container(border=True):
            datas_sel = st.date_input(
                "🗓️ Período:",
                value=(hoje_br - timedelta(days=15), hoje_br),
                format="DD/MM/YYYY"
            )
            holder_cidades = st.empty()

        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("<p style='font-size: 11px; font-weight: 800; color: #64748B; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 5px;'>Suporte e Relatórios</p>", unsafe_allow_html=True)
        
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
                                texto_final += f"💬 *Mensagem:* {msg_chamado}\n\n⏳ _Acesse o C.C.O. para responder._"
                                
                                enviar_whatsapp_zapi_cliente("5511947996371", texto_final)
                                st.success(f"✅ Ticket {tkt_id} aberto com sucesso! Acompanhe na aba 'Meus Chamados'.")
                            except Exception as e:
                                st.error(f"Erro ao criar ticket: {e}")

        holder_exportar = st.empty()

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<p style='font-size: 11px; font-weight: 800; color: #64748B; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 5px;'>Sistema</p>", unsafe_allow_html=True)
        if st.button("🚪 Sair com Segurança", use_container_width=True, type="secondary"):
            st.session_state.logado = False
            st.rerun()

    # ── HEADER ─────────────────────────────────────────
    agora_str = datetime.now(FUSO_BR).strftime('%H:%M')
    st.markdown(f"""
        <div class="header-container">
            <div>
                <div class="header-title">Monitoramento Logístico</div>
                <div class="header-subtitle">{st.session_state.cliente} · {hoje_br.strftime('%d/%m/%Y')}</div>
            </div>
            <div class="sync-status">
                <span class="sync-dot"></span> Online · {agora_str}
            </div>
        </div>
    """, unsafe_allow_html=True)

    # ── DADOS ───────────────────────────────────────────
    df_raw = carregar_dados_nuvem()

    if df_raw.empty:
        st.info("Aguardando novas informações do C.C.O na base de dados...")
    else:
        if conf["filtro"] == "TODOS":
            df_cliente = df_raw.copy()
        else:
            df_cliente = df_raw[
                df_raw['TOMADOR'].str.upper().str.strip() == conf["filtro"]
            ].copy()

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
                st.warning(
                    f"Nenhum pedido registrado sob a titularidade '{conf['filtro']}'."
                )
            else:
                with holder_cidades:
                    cidades_sel = st.multiselect(
                        "📍 Cidades:",
                        sorted(df_cliente['CIDADE'].dropna().unique().tolist())
                    )

                df_cliente['STATUS_DISPLAY'] = df_cliente.apply(get_st, axis=1)
                df_cliente['DETALHES']       = df_cliente.apply(get_detalhes, axis=1)

                df_f = df_cliente.copy()
                if isinstance(datas_sel, (tuple, list)) and len(datas_sel) == 2:
                    df_f = df_f[
                        (df_f['DATA_OBJ'] >= datas_sel[0]) &
                        (df_f['DATA_OBJ'] <= datas_sel[1])
                    ]
                if cidades_sel:
                    df_f = df_f[df_f['CIDADE'].isin(cidades_sel)]

                df_f['DT_LIMITE_OBJ'] = pd.to_datetime(
                    df_f['DATA_LIMITE'], format='%d/%m/%Y', errors='coerce'
                ).dt.date

                mask_atrasado = (
                    (~df_f['STATUS_DISPLAY'].str.contains(
                        'Entregue|Frustrada|Cancelado|Aguardando|Recusada',
                        case=False, na=False
                    )) &
                    (df_f['DT_LIMITE_OBJ'] < hoje_br) &
                    (df_f['DT_LIMITE_OBJ'].notnull())
                )
                df_f.loc[mask_atrasado, 'STATUS_DISPLAY'] = (
                    df_f.loc[mask_atrasado, 'STATUS_DISPLAY'] + ' 🚨 ATRASADO'
                )

                n_vals = {
                    "TODOS":      len(df_f),
                    "ENTREGUE":   len(df_f[df_f['STATUS_DISPLAY'].str.contains('Entregue', case=False)]),
                    "FRUSTRADA":  len(df_f[df_f['STATUS_DISPLAY'].str.contains('Frustrada', case=False)]),
                    "PENDENTE":   len(df_f[df_f['STATUS_DISPLAY'].str.contains('Pendente|Rota|Coletado', case=False, na=False)]),
                    "Aguardando": len(df_f[df_f['STATUS_DISPLAY'].str.contains('Aguardando', case=False)]),
                    "HOJE":       len(df_f[df_f['DATA_OBJ'] == hoje_br]),
                }

                cols_kpi = st.columns(6)
                for col, (filtro, label, key) in zip(cols_kpi, KPI_META):
                    is_active = st.session_state.filtro_kpi == filtro
                    dot_color = KPI_DOT_COLOR[filtro]
                    bg_color  = KPI_BG_COLOR[filtro]

                    borda = f"2px solid {dot_color}" if is_active else f"1px solid {dot_color}40"
                    valor = n_vals[filtro]

                    partes = label.split(' ', 1)
                    emoji_card = partes[0]
                    texto_card = partes[1] if len(partes) > 1 else label

                    with col:
                        st.markdown(f"""
                            <div class="kpi-card"
                                 style="background-color: {bg_color}; border: {borda}; text-align: left; padding: 16px; border-radius: 16px; height: 95px;">
                                <div style="position: absolute; right: -5px; bottom: -15px; font-size: 65px; opacity: 0.12; z-index: 0; line-height: 1;">
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

                        if st.button(label, key=key, use_container_width=True, help=f"Filtrar por: {texto_card}"):
                            st.session_state.filtro_kpi = filtro
                            st.rerun()

                st.markdown("""
                    <style>
                    div.st-key-kpi_total, div.st-key-kpi_entregue, div.st-key-kpi_frus, 
                    div.st-key-kpi_pend, div.st-key-kpi_aguardando, div.st-key-kpi_hoje {
                        margin-top: -110px !important; position: relative; z-index: 999; opacity: 0 !important;
                    }
                    div.st-key-kpi_total button, div.st-key-kpi_entregue button, div.st-key-kpi_frus button, 
                    div.st-key-kpi_pend button, div.st-key-kpi_aguardando button, div.st-key-kpi_hoje button {
                        height: 105px !important; cursor: pointer !important;
                    }
                    </style>
                """, unsafe_allow_html=True)

                df_h = df_f[df_f['DATA_OBJ'] == hoje_br]
                if not df_h.empty:
                    n_fim  = len(df_h[df_h['STATUS_DISPLAY'].str.contains(
                        'Entregue|Frustrada|Cancelado|Recusada|Coletado', case=False
                    )])
                    n_tot  = len(df_h)
                    pct    = round((n_fim / n_tot) * 100) if n_tot else 0
                    bar_w  = pct

                    st.markdown(f"""
                        <div class="progress-block">
                            <div class="progress-header">
                                <span class="progress-title">🎯 Progresso de Hoje</span>
                                <span class="progress-pct">{pct}% concluído — {n_fim} de {n_tot} pedidos</span>
                            </div>
                            <div class="progress-bar-bg">
                                <div style="height:6px;width:{bar_w}%;background:#22c55e; border-radius:99px;transition:width 0.6s ease;"></div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    st.info("Nenhum pedido despachado para hoje.")

                col_busca, col_export = st.columns([5, 1])
                with col_busca:
                    busca = st.text_input(
                        "🔎 Busca Rápida:",
                        placeholder="Buscar por pedido, laboratório, cidade...",
                        label_visibility="collapsed"
                    )
                with col_export:
                    holder_download = st.empty()

                df_grid = df_f.copy()
                if st.session_state.filtro_kpi != "TODOS":
                    if st.session_state.filtro_kpi == "HOJE":
                        df_grid = df_grid[df_grid['DATA_OBJ'] == hoje_br]
                    elif st.session_state.filtro_kpi == "PENDENTE":
                        df_grid = df_grid[df_grid['STATUS_DISPLAY'].str.contains('Pendente|Rota|Coletado', case=False, na=False)]
                    else:
                        df_grid = df_grid[
                            df_grid['STATUS_DISPLAY'].str.contains(
                                st.session_state.filtro_kpi, case=False
                            )
                        ]

                if busca:
                    df_grid = df_grid[
                        df_grid.astype(str)
                        .apply(lambda x: x.str.lower().str.contains(busca.lower()))
                        .any(axis=1)
                    ]

                if not df_grid.empty:
                    df_grid['PRIORIDADE'] = df_grid['STATUS_DISPLAY'].apply(
                        definir_prioridade_portal
                    )
                    df_grid = df_grid.sort_values(
                        by=['PRIORIDADE', 'DATA_OBJ', 'PEDIDO'],
                        ascending=[True, False, False]
                    ).drop(columns=['PRIORIDADE'])

                    df_final = df_grid.copy()
                    df_final['COMPROVANTE'] = df_final['FOTO_FINAL'].apply(tratar_foto)

                    if 'UF' not in df_final.columns:
                        df_final['UF'] = ""

                    df_final['CIDADE_UF'] = df_final.apply(
                        lambda r: (
                            f"{str(r.get('CIDADE','')).strip()}/{str(r.get('UF','')).strip()}"
                            if str(r.get('UF', '')).strip() and str(r.get('UF', '')).upper() != 'NAN'
                            else str(r.get('CIDADE', '')).strip()
                        ),
                        axis=1
                    )

                    for col in df_final.columns:
                        df_final[col] = (
                            df_final[col]
                            .astype(str)
                            .replace(["nan", "NaN", "None", "none", "<NA>", "NaT"], "")
                        )

                    colunas_visiveis = [
                        'PEDIDO', 'DATA', 'LABORATORIO', 'CIDADE_UF',
                        'DATA_LIMITE', 'DATA_EFETIVA', 'STATUS_DISPLAY',
                        'DETALHES', 'COMPROVANTE'
                    ]

                    if st.session_state.cliente == "LOGISTICA.LABEST":
                        colunas_visiveis.insert(3, 'CNPJ')

                    colunas_visiveis = [
                        c for c in colunas_visiveis if c in df_final.columns
                    ]

                    # 🔥 JAVASCRIPT CORRIGIDO: CRIA O ELEMENTO REAL DO BOTÃO 🔥
                    link_jscode = JsCode("""
                    function(params) {
                        if (params.value && params.value !== '') {
                            // Cria a caixa (div) para centralizar
                            let div = document.createElement('div');
                            div.style.display = 'flex';
                            div.style.justifyContent = 'center';
                            div.style.alignItems = 'center';
                            div.style.height = '100%';
                            
                            // Cria o link clicável (a)
                            let a = document.createElement('a');
                            a.href = params.value;
                            a.target = '_blank'; // Abre em nova guia
                            a.style.textDecoration = 'none';
                            a.style.fontSize = '20px';
                            a.title = 'Ver Foto do Comprovante';
                            a.innerText = '📷'; // O Emoji
                            
                            // Junta tudo e joga na tela
                            div.appendChild(a);
                            return div;
                        }
                        return '';
                    }
                    """)

                    gb = GridOptionsBuilder.from_dataframe(df_final[colunas_visiveis])
                    gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=15)
                    gb.configure_default_column(resizable=True, filterable=True, sortable=True)

                    gb.configure_column("PEDIDO", header_name="📦 Pedido", width=120)
                    gb.configure_column("DATA", header_name="📅 Data Coleta", width=130)
                    gb.configure_column("LABORATORIO", header_name="🔬 Ponto de Coleta")
                    if 'CNPJ' in colunas_visiveis:
                        gb.configure_column("CNPJ", header_name="🏢 CNPJ")
                    gb.configure_column("CIDADE_UF", header_name="📍 Cidade / UF")
                    gb.configure_column("DATA_LIMITE", header_name="🎯 Previsão", width=120)
                    gb.configure_column("DATA_EFETIVA", header_name="🏁 Entrega", width=120)
                    gb.configure_column("STATUS_DISPLAY", header_name="🚦 Status")
                    gb.configure_column("DETALHES", header_name="💬 Atualizações")
                    
                    # Aplica o código Javascript na coluna de comprovante
                    gb.configure_column("COMPROVANTE", header_name="📎 Anexo", cellRenderer=link_jscode, width=100)

                    gridOptions = gb.build()

                    # 🔥 CSS MÁGICO: ADICIONA AS LINHAS VERTICAIS SEPARANDO AS COLUNAS 🔥
                    custom_css = {
                        ".ag-header-cell": {"border-right": "1px solid #e2e8f0 !important"},
                        ".ag-cell": {"border-right": "1px solid #e2e8f0 !important"}
                    }

                    AgGrid(
                        df_final[colunas_visiveis],
                        gridOptions=gridOptions,
                        theme="alpine",
                        columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS,
                        height=550,
                        allow_unsafe_jscode=True, # Necessário para o script do Emoji rodar
                        custom_css=custom_css     # Aplica as linhas separadoras
                    )

                    # ── EXPORTAÇÃO CSV ────────
                    mapa_csv = {
                        'PEDIDO': 'Pedido',
                        'DATA': 'Data Coleta',
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
                df_cli_locais = df_locais[
                    df_locais['TOMADOR'].str.upper().str.strip() == nome_tomador_oficial.upper().strip()
                ]
                if df_cli_locais.empty:
                    st.warning(
                        f"Nenhum ponto de coleta cadastrado para {nome_tomador_oficial}."
                    )
                else:
                    with st.container(border=True):
                        with st.form("form_nova_coleta", clear_on_submit=True):
                            lista_labs = sorted(df_cli_locais['LABORATORIO'].unique().tolist())
                            lab_sel    = st.selectbox(
                                "📍 Selecione o Ponto de Coleta (Laboratório):",
                                ["Selecione..."] + lista_labs
                            )

                            if lab_sel != "Selecione...":
                                local_data  = df_cli_locais[
                                    df_cli_locais['LABORATORIO'] == lab_sel
                                ].iloc[0]
                                end_fmt = (
                                    f"{local_data.get('ENDERECO','')}, "
                                    f"{local_data.get('NUMERO','')} — "
                                    f"{local_data.get('BAIRRO','')}"
                                )
                                cid_fmt = (
                                    f"{local_data.get('CIDADE','')}/{local_data.get('UF','')} "
                                    f"| CEP: {local_data.get('CEP','')}"
                                )
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
                            data_minima = (
                                agora_sp.date()
                                if agora_sp.hour < 10
                                else agora_sp.date() + timedelta(days=1)
                            )
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

                            if st.form_submit_button(
                                "🚀 Enviar Solicitação ao C.C.O.",
                                type="primary",
                                use_container_width=True
                            ):
                                if lab_sel == "Selecione...":
                                    st.error("⚠️ Selecione um Ponto de Coleta válido.")
                                elif data_coleta.weekday() >= 5:
                                    st.error(
                                        "⚠️ Coletas não são realizadas aos finais de semana. Escolha um dia útil."
                                    )
                                else:
                                    with st.spinner("Registrando pedido e notificando o C.C.O..."):
                                        try:
                                            gc       = conectar_banco_seguro()
                                            planilha = gc.open("DB_IGO_Logistica")
                                            aba_m    = planilha.worksheet("Memoria_Sistema")
                                            dados_m  = aba_m.get_all_values()

                                            df_m_temp = pd.DataFrame(
                                                dados_m[1:], columns=dados_m[0]
                                            )
                                            prox_id = obter_proximo_id(df_m_temp)

                                            nova_linha_dict = {
                                                'DATA':       data_coleta.strftime("%d/%m/%Y"),
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
                                            linha_append = [
                                                nova_linha_dict.get(c, "") for c in cabecalhos
                                            ]
                                            aba_m.append_row(
                                                linha_append,
                                                value_input_option='USER_ENTERED'
                                            )

                                            texto_zap = (
                                                f"🔔 *NOVA SOLICITAÇÃO DE COLETA* 🔔\n\n"
                                                f"🏢 *Cliente:* {nome_tomador_oficial}\n"
                                                f"🔬 *Local:* {local_data['LABORATORIO']}\n"
                                                f"📍 *Cidade:* {local_data.get('CIDADE','')} - "
                                                f"{local_data.get('UF','')}\n"
                                                f"📅 *Data Desejada:* "
                                                f"{data_coleta.strftime('%d/%m/%Y')}\n"
                                                f"📦 *ID do Pedido:* {prox_id}\n\n"
                                                f"Acesse o painel do C.C.O para aprovar ou recusar."
                                            )
                                            enviar_whatsapp_zapi_cliente(
                                                "5511947996371", texto_zap
                                            )

                                            st.success(
                                                f"🎉 Pedido #{prox_id} criado para "
                                                f"{data_coleta.strftime('%d/%m/%Y')}. "
                                                f"Aguardando aprovação do C.C.O."
                                            )
                                            carregar_dados_nuvem.clear()

                                        except Exception as e:
                                            st.error(f"Erro ao processar solicitação: {e}")

        # ===================================================
        # ABA 3 · ACOMPANHAMENTO DOS CHAMADOS
        # ===================================================
        with tab_chamados:
            st.markdown("### 🎧 Histórico de Atendimento")
            st.markdown("<p style='color:#64748b;font-size:13px;margin-top:-8px;'>Acompanhe a resolução das suas solicitações junto ao nosso C.C.O.</p>", unsafe_allow_html=True)
            
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
                                    <p style="margin: 0; font-size: 13px; color: #0f172a;"><b>Resposta do C.C.O:</b> {row['RESPOSTA'] if row.get('RESPOSTA', '') else '<i>Aguardando análise de um de nossos agentes...</i>'}</p>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                else:
                    st.info("Nenhum chamado registrado no banco de dados.")
            except Exception:
                st.info("A base de chamados será inicializada na sua primeira solicitação.")
