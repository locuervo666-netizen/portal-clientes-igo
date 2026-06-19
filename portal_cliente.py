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
import google.auth.transport.requests
import streamlit.components.v1 as components
from datetime import datetime, timedelta, timezone
from google.oauth2.credentials import Credentials

# 🚀 IMPORTAÇÃO DO AGGRID E DO AUTO-REFRESH SILENCIOSO
from st_aggrid import AgGrid, GridOptionsBuilder, ColumnsAutoSizeMode, JsCode
from streamlit_autorefresh import st_autorefresh
from streamlit_shadcn_ui import button, input as shadcn_input

FUSO_BR = timezone(timedelta(hours=-3))
LOGO_IGO = "https://i.postimg.cc/x84nnjjq/IGO-LOGO.png"

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
    [data-testid="stAppViewContainer"] {
        transition: background-color 0.3s ease;
        font-family: 'Inter', sans-serif;
        background-color: #FFFFFF !important;
    }

    /* ── SIDEBAR ── */
    [data-testid="stSidebar"],
    [data-testid="stSidebar"] > div:first-child {
        background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%) !important;
        border-right: 1px solid #dbe3ef !important;
    }
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] h3 {
        color: #1e293b !important;
    }
    [data-testid="stSidebar"] .sidebar-premium-shell {
        background: linear-gradient(145deg, #0f172a 0%, #1e293b 58%, #334155 100%);
        border-radius: 18px;
        padding: 14px 14px 12px 14px;
        margin-bottom: 14px;
        box-shadow: 0 14px 30px rgba(15, 23, 42, 0.18);
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
        border-radius: 14px !important;
        padding: 14px !important;
        box-shadow: 0 6px 16px rgba(15, 23, 42, 0.05) !important;
    }
    [data-testid="stSidebar"] section > div {
        background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%) !important;
        border-radius: 14px !important;
        padding: 14px !important;
        margin-bottom: 10px !important;
        border: 1px solid #e2e8f0 !important;
        box-shadow: 0 6px 14px rgba(15, 23, 42, 0.04) !important;
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
    [data-testid="stSidebar"] .stButton > button,
    [data-testid="stSidebar"] [data-testid="stFormSubmitButton"] > button {
        border-radius: 10px !important;
        border: 1px solid #93c5fd !important;
        background: linear-gradient(180deg, #eff6ff 0%, #dbeafe 100%) !important;
        color: #0f172a !important;
        font-weight: 700 !important;
        box-shadow: 0 4px 10px rgba(37, 99, 235, 0.10) !important;
        transition: all 0.2s ease !important;
        min-height: 42px !important;
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

    /* ── LAYOUT ── */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {background-color: transparent !important;}
    .block-container {
        padding-top: 1.2rem !important;
        padding-bottom: 1rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        display: block !important;
    }

    /* ── KPI CARDS ── */
    .kpi-card {
        border-radius: 12px;
        padding: 16px;
        text-align: left;
        cursor: pointer;
        transition: all 0.2s ease;
        position: relative;
        overflow: hidden;
        height: 95px;
    }
    .kpi-card:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        transform: translateY(-2px);
    }
    .kpi-card.active {
        box-shadow: 0 0 0 2px #3b82f6;
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
        color: #166534;
        font-weight: 600;
        background: linear-gradient(135deg, #dcfce7 0%, #f0fdf4 100%);
        border: 1px solid #86efac;
        border-radius: 99px;
        padding: 5px 12px;
        box-shadow: 0 4px 12px rgba(34, 197, 94, 0.12);
    }
    .sync-dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background: #22c55e;
        box-shadow: 0 0 0 3px rgba(34, 197, 94, 0.18);
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

    /* ── PROGRESS BLOCK SIDEBAR ── */
    .progress-block-sidebar {
        background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
        border: 1px solid #dbeafe;
        border-radius: 14px;
        padding: 16px;
        margin: 12px 0;
        overflow: hidden;
        box-shadow: 0 10px 24px rgba(37, 99, 235, 0.10);
    }
    .progress-block-sidebar-content {
        position: relative;
        z-index: 1;
    }
    .progress-title-sidebar {
        font-size: 12px;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 6px;
    }
    .progress-number-sidebar {
        font-size: 28px;
        font-weight: 900;
        color: #0f172a;
        line-height: 1;
        margin: 4px 0;
    }
    .progress-bar-fill {
        height: 6px;
        border-radius: 99px;
        transition: width 0.6s ease;
        box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.18), 0 4px 12px rgba(59, 130, 246, 0.16);
    }
    .progress-text-sidebar {
        font-size: 12px;
        color: #475569;
        font-weight: 500;
        margin-bottom: 4px;
    }
    </style>
"""

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
    "DANILO.DUARTE": {
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
def carregar_dados_nuvem(cliente_filtro):
    try:
        gc = conectar_banco_seguro()
        if not gc:
            return pd.DataFrame()
        
        planilha = gc.open("DB_IGO_Logistica")
        
        # 1. Carregar Agentes para mapeamento (Nomes Reais)
        dict_agentes = {}
        try:
            aba_agentes = planilha.worksheet("Agentes")
            dados_agentes = aba_agentes.get_all_values()
            if len(dados_agentes) > 1:
                df_ag = pd.DataFrame(dados_agentes[1:], columns=dados_agentes[0])
                df_ag.columns = [str(c).upper().strip() for c in df_ag.columns]
                
                # Identifica colunas flexíveis de ID e Nome
                id_col = None
                nome_col = None
                for c in df_ag.columns:
                    if 'NOME' in c: nome_col = c
                    elif any(x in c for x in ['ID', 'USUARIO', 'EMAIL', 'LOGIN']): id_col = c
                
                if not id_col: id_col = df_ag.columns[0]
                if not nome_col: nome_col = df_ag.columns[1]
                
                dict_agentes = dict(zip(df_ag[id_col].astype(str).str.strip().str.lower(), df_ag[nome_col].astype(str).str.strip()))
        except Exception as e:
            pass # Segue sem quebrar se a aba não for encontrada

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
            resposta = requests.get(url, headers=headers)
            
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
                        'HORA_STATUS': 'A_HORA_STATUS'
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

                    def extrair_hora(hora_str):
                        h = str(hora_str).strip()
                        if not h or h.upper() == 'NAN': return ""
                        if " " in h: h = h.split(" ")[-1]
                        parts = h.split(":")
                        if len(parts) >= 2: return f"{parts[0].zfill(2)}:{parts[1].zfill(2)}"
                        return h
                    df['HORA_LIMPA'] = df['HORA_APP_FINAL'].apply(extrair_hora)

                    def defining_foto_prioritaria(r):
                        f_col = get_app_val(r, 'A_FOTO_COL')
                        f_ent = get_app_val(r, 'A_FOTO_ENT')
                        f_gen = get_app_val(r, 'A_FO')
                        
                        if f_col and f_col.upper() != 'NAN': return f_col
                        if f_ent and f_ent.upper() != 'NAN': return f_ent
                        if f_gen and f_gen.upper() != 'NAN': return f_gen
                        return ""

                    df['FOTO_FINAL'] = df.apply(defining_foto_prioritaria, axis=1)

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

            if 'DATA' in df.columns:
                # 🔥 CORREÇÃO DA DATA APLICADA AQUI 🔥
                df['DATA_OBJ'] = pd.to_datetime(df['DATA'], dayfirst=True, errors='coerce').dt.date
            
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
    if "token_cli" in st.query_params:
        st.session_state.logado = True
        st.session_state.cliente = st.query_params["token_cli"]
    else:
        st.session_state.logado = False

if 'filtro_kpi' not in st.session_state: st.session_state.filtro_kpi = "TODOS"
if 'linha_clicada' not in st.session_state: st.session_state.linha_clicada = None
if 'pedido_modal' not in st.session_state: st.session_state.pedido_modal = None
if 'modal_aberto' not in st.session_state: st.session_state.modal_aberto = False
if 'modal_fechado' not in st.session_state: st.session_state.modal_fechado = False
if 'modal_renderizado_antes' not in st.session_state: st.session_state.modal_renderizado_antes = False
if 'modal_foi_renderizado' not in st.session_state: st.session_state.modal_foi_renderizado = False
if 'ignorar_selecao_grid' not in st.session_state: st.session_state.ignorar_selecao_grid = False

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
# 🪟 FUNÇÃO DO POP-UP MEGAZORD
# =======================================================
@st.dialog("📋 Detalhes da Operação", width="large")
def modal_detalhes_pedido(pedido_data, df_historico=None):
    status = str(pedido_data.get('STATUS_DISPLAY', '')).upper()
    cor_etiqueta = "#10B981" if "ENTREGUE" in status else "#F59E0B"
    if any(x in status for x in ["FRUSTRADA", "PROBLEMA", "CANCELADO", "ATRASADO", "RECUSA"]): cor_etiqueta = "#EF4444"
    if "COLETADO" in status or "ROTA" in status: cor_etiqueta = "#3B82F6"

    # 🎯 CABEÇALHO COM PEDIDO E STATUS
    c_h1, c_h2 = st.columns([3, 1])
    c_h1.subheader(f"Pedido: {pedido_data.get('PEDIDO', 'N/A')}")
    c_h2.markdown(f"<div style='text-align:center; background:{cor_etiqueta}; color:white; padding:8px; border-radius:10px; font-weight:bold; font-size:12px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>{status}</div>", unsafe_allow_html=True)
    
    # 🔄 BARRA DE PROGRESSO
    step = 1
    cor_barra = "#3b82f6" 
    if any(x in status for x in ["FRUSTRADA", "PROBLEMA", "CANCELADO", "RECUSA"]):
        cor_barra = "#ef4444" 
        if "ROTA DE COLETA" in status or "COLETADO" in status: step = 2
    else:
        if "ROTA DE COLETA" in status: step = 2
        elif "COLETADO" in status or "ROTA DE ENTREGA" in status or "EM ROTA" in status or "CONFERIDO" in status: step = 3
        elif "ENTREGUE" in status: step = 4; cor_barra = "#10b981" 

    html_barra = (
        f"<div style='display:flex;justify-content:space-between;position:relative;margin:15px 0 35px 0;'>"
        f"<div style='position:absolute;top:12px;left:0;right:0;height:4px;background:#e2e8f0;z-index:1;'></div>"
        f"<div style='position:absolute;top:12px;left:0;width:{(step-1)*33.3}%;height:4px;background:{cor_barra};z-index:2;transition:width 0.5s;'></div>"
        f"<div style='z-index:3;text-align:center;width:60px;'><div style='width:28px;height:28px;background:{cor_barra if step >= 1 else '#e2e8f0'};color:white;border-radius:50%;line-height:28px;margin:0 auto;font-size:14px;box-shadow:0 2px 4px rgba(0,0,0,0.1);'>✓</div><div style='font-size:11px;margin-top:5px;font-weight:600;color:{'#0f172a' if step >= 1 else '#64748b'};'>Pedido</div></div>"
        f"<div style='z-index:3;text-align:center;width:60px;'><div style='width:28px;height:28px;background:{cor_barra if step >= 2 else '#e2e8f0'};color:white;border-radius:50%;line-height:28px;margin:0 auto;font-size:14px;box-shadow:0 2px 4px rgba(0,0,0,0.1);'>{'!' if step==2 and cor_barra=='#ef4444' else '🚐'}</div><div style='font-size:11px;margin-top:5px;font-weight:600;color:{'#0f172a' if step >= 2 else '#64748b'};'>Em Rota</div></div>"
        f"<div style='z-index:3;text-align:center;width:60px;'><div style='width:28px;height:28px;background:{cor_barra if step >= 3 else '#e2e8f0'};color:white;border-radius:50%;line-height:28px;margin:0 auto;font-size:14px;box-shadow:0 2px 4px rgba(0,0,0,0.1);'>📦</div><div style='font-size:11px;margin-top:5px;font-weight:600;color:{'#0f172a' if step >= 3 else '#64748b'};'>Coletado</div></div>"
        f"<div style='z-index:3;text-align:center;width:60px;'><div style='width:28px;height:28px;background:{cor_barra if step >= 4 else '#e2e8f0'};color:white;border-radius:50%;line-height:28px;margin:0 auto;font-size:14px;box-shadow:0 2px 4px rgba(0,0,0,0.1);'>✅</div><div style='font-size:11px;margin-top:5px;font-weight:600;color:{'#0f172a' if step >= 4 else '#64748b'};'>Entregue</div></div>"
        f"</div>"
    )
    st.markdown(html_barra, unsafe_allow_html=True)

    # 📍 PREPARAR DADOS DE ENDEREÇO
    end_rua = str(pedido_data.get('ENDERECO', '')).strip()
    end_num = str(pedido_data.get('NUMERO', '')).strip()
    end_bairro = str(pedido_data.get('BAIRRO', '')).strip()
    end_cid_uf = str(pedido_data.get('CIDADE_UF', 'N/A')).strip()

    partes_end = []
    if end_rua and end_rua.upper() not in ['NAN', 'NONE', '']: partes_end.append(end_rua)
    if end_num and end_num.upper() not in ['NAN', 'NONE', '']: partes_end.append(f"nº {end_num}")
    if end_bairro and end_bairro.upper() not in ['NAN', 'NONE', '']: partes_end.append(end_bairro)

    endereco_completo = ", ".join(partes_end) + f" — {end_cid_uf}" if partes_end else end_cid_uf

    # 👤 PREPARAR DADOS DE MOTORISTA
    mot_coleta = str(pedido_data.get('MOTORISTA_COLETA', '')).strip()
    mot_entrega = str(pedido_data.get('MOTORISTA_ENTREGA', '')).strip()
    if not mot_coleta or mot_coleta.upper() == 'NAN': mot_coleta = 'Equipe IGO'
    if not mot_entrega or mot_entrega.upper() == 'NAN': mot_entrega = mot_coleta 

    if any(x in status for x in ["ENTREGUE", "CONFERIDO"]) and mot_coleta != mot_entrega:
        motorista_html = f"<p style='margin:2px 0 12px 0;font-size:13px;font-weight:600;color:#334155;'>📦 Coleta: <span style='color:#3b82f6;'>{mot_coleta}</span><br>✅ Entrega: <span style='color:#3b82f6;'>{mot_entrega}</span></p>"
    else:
        motorista_html = f"<p style='margin:2px 0 12px 0;font-size:14px;font-weight:700;color:#3b82f6;'>🚐 {mot_coleta}</p>"

    # 📅 PREPARAR DADOS DE DATA E PRAZO
    data_efetiva = str(pedido_data.get('DATA_EFETIVA', '---')).replace(" 00:00:00", "").strip()
    
    # Reconstrói a data se estiver no formato curto (da GRID) para calcular certo no Popup
    if len(data_efetiva.split('/')) == 3 and len(data_efetiva.split('/')[2]) == 2:
        partes = data_efetiva.split('/')
        data_efetiva = f"{partes[0]}/{partes[1]}/20{partes[2]}"
        
    hora_limpa = str(pedido_data.get('HORA_LIMPA', '')).strip()
    hora_str = f" às {hora_limpa}" if hora_limpa else ""
    
    data_limite = str(pedido_data.get('DATA_LIMITE', '---')).strip()
    if not data_limite or data_limite.upper() == 'NAN': data_limite = "Não definida"

    selo_prazo = ""
    if any(x in status for x in ["ENTREGUE", "CONFERIDO"]) and data_limite != "Não definida" and data_efetiva != "---":
        try:
            ano_ef = int(data_efetiva.split('/')[2])
            ano_lim = int(data_limite.split('/')[2])
            if ano_ef < 100: ano_ef += 2000
            if ano_lim < 100: ano_lim += 2000
            
            dt_ef_obj = datetime(ano_ef, int(data_efetiva.split('/')[1]), int(data_efetiva.split('/')[0])).date()
            dt_lim_obj = datetime(ano_lim, int(data_limite.split('/')[1]), int(data_limite.split('/')[0])).date()
            
            if dt_ef_obj <= dt_lim_obj:
                selo_prazo = "<span style='background:#dcfce7; color:#166534; padding:2px 6px; border-radius:4px; font-size:11px; font-weight:bold; margin-left:5px;'>No Prazo</span>"
            else:
                dias_atraso = (dt_ef_obj - dt_lim_obj).days
                selo_prazo = f"<span style='background:#fee2e2; color:#991b1b; padding:2px 6px; border-radius:4px; font-size:11px; font-weight:bold; margin-left:5px;'>Atrasado {dias_atraso} dia(s)</span>"
        except:
            pass

    if any(x in status for x in ["ENTREGUE", "CONFERIDO"]):
        timeline_html = f"<p style='margin:2px 0 12px 0;font-size:13px;color:#334155;'>📦 Coleta: <b>{pedido_data.get('DATA', '---')}</b><br>✅ Entrega: <b>{data_efetiva}{hora_str}</b> {selo_prazo}</p>"
    elif any(x in status for x in ["COLETADO", "ROTA"]):
        timeline_html = f"<p style='margin:2px 0 12px 0;font-size:13px;color:#334155;'>📦 Coleta: <b>{pedido_data.get('DATA', '---')}{hora_str}</b><br>⏳ Entrega: <i>Em trânsito para o destino...</i></p>"
    elif any(x in status for x in ["FRUSTRADA", "PROBLEMA"]):
        timeline_html = f"<p style='margin:2px 0 12px 0;font-size:13px;color:#ef4444;'>❌ Tentativa: <b>{data_efetiva}{hora_str}</b></p>"
    else:
        timeline_html = f"<p style='margin:2px 0 12px 0;font-size:13px;color:#334155;'>⏳ Previsão de Coleta: <b>{pedido_data.get('ETA_LAB', 'Em mapeamento')}</b></p>"

    # =====================================
    # 📐 LAYOUT EM 2 COLUNAS
    # Coluna Esquerda: Dados do Pedido
    # Coluna Direita: Comprovante com Download
    # =====================================
    col_esquerda, col_direita = st.columns([1, 1])
    
    # 📋 COLUNA ESQUERDA - DADOS DO PEDIDO
    with col_esquerda:
        # Container com borda cinza
        with st.container(border=True):
            # 🏢 Tomador
            st.markdown("<p style='font-size:11px; font-weight:700; color:#2563eb; text-transform:uppercase; margin:0; letter-spacing:0.5px;'>🏢 Cliente (Embarcador)</p>", unsafe_allow_html=True)
            st.markdown(f"<p style='font-size:14px; font-weight:700; background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; margin:2px 0 12px 0;'>{pedido_data.get('LABORATORIO', 'N/A')}</p>", unsafe_allow_html=True)
            
            # 📍 Endereço
            st.markdown("<p style='font-size:11px; font-weight:700; color:#2563eb; text-transform:uppercase; margin:0; letter-spacing:0.5px;'>📍 Endereço de Entrega</p>", unsafe_allow_html=True)
            st.markdown(f"<p style='font-size:13px; color:#1e293b; margin:2px 0 12px 0; font-weight:500;'>{endereco_completo}</p>", unsafe_allow_html=True)
            
            # 📅 Datas
            st.markdown("<p style='font-size:11px; font-weight:700; color:#2563eb; text-transform:uppercase; margin:0; letter-spacing:0.5px;'>📅 Datas da Corrida</p>", unsafe_allow_html=True)
            st.markdown(timeline_html, unsafe_allow_html=True)
            
            # 🎯 Prazo
            st.markdown("<p style='font-size:11px; font-weight:700; color:#2563eb; text-transform:uppercase; margin:0; letter-spacing:0.5px;'>🎯 SLA Acordado</p>", unsafe_allow_html=True)
            st.markdown(f"<p style='font-size:13px; color:#1e293b; margin:2px 0 12px 0;'>📌 Previsão: <b style='color:#2563eb;'>{data_limite}</b></p>", unsafe_allow_html=True)
            
            # 👤 Motorista
            st.markdown("<p style='font-size:11px; font-weight:700; color:#2563eb; text-transform:uppercase; margin:0; letter-spacing:0.5px;'>👤 Motorista (Entregador)</p>", unsafe_allow_html=True)
            st.markdown(motorista_html, unsafe_allow_html=True)
            
            # 📈 Confiabilidade
            st.markdown("<p style='font-size:11px; font-weight:700; color:#2563eb; text-transform:uppercase; margin:0; letter-spacing:0.5px;'>📈 Nível de Serviço (Local)</p>", unsafe_allow_html=True)
            st.markdown(f"<p style='font-size:13px; color:#1e293b; margin:2px 0 0 0; font-weight:500;'>{pedido_data.get('SLA_LAB', 'Em mapeamento')} <br> {pedido_data.get('OTD_LAB', '')}</p>", unsafe_allow_html=True)
            
            # 📊 HISTÓRICO DO PONTO DE COLETA
            if df_historico is not None and not df_historico.empty:
                lab_atual = pedido_data.get('LABORATORIO', '')
                df_lab_historico = df_historico[df_historico['LABORATORIO'] == lab_atual].copy()
                df_lab_historico = df_lab_historico[df_lab_historico['STATUS_DISPLAY'].str.contains('Entregue|Frustrada|Cancelado|Coletado|Recusada|Conferido', case=False, na=False)]
                df_lab_historico = df_lab_historico.sort_values('DATA', ascending=False).head(5)
                
                if not df_lab_historico.empty:
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown("<p style='font-size:11px; font-weight:700; color:#64748b; text-transform:uppercase; margin:0;'>📋 Histórico do Ponto (Últimas 5)</p>", unsafe_allow_html=True)
                    
                    # CSS para os badges de histórico
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
                        .historico-badge-sucesso {
                            background: #dcfce7;
                            color: #166534;
                            border: 1px solid #86efac;
                        }
                        .historico-badge-frustrada {
                            background: #fee2e2;
                            color: #991b1b;
                            border: 1px solid #fca5a5;
                        }
                        .historico-badge-em-rota {
                            background: #dbeafe;
                            color: #1e40af;
                            border: 1px solid #93c5fd;
                        }
                        .historico-legenda {
                            background: #f8fafc;
                            padding: 8px;
                            border-radius: 6px;
                            font-size: 10px;
                            color: #64748b;
                            margin-top: 8px;
                            line-height: 1.6;
                        }
                        </style>
                    """, unsafe_allow_html=True)
                    
                    # Renderiza cada item separadamente
                    for idx, row in df_lab_historico.iterrows():
                        pedido_hist = row.get('PEDIDO', 'N/A')
                        status_hist = str(row.get('STATUS_DISPLAY', '')).upper()
                        data_hist = row.get('DATA', '')
                        
                        if 'ENTREGUE' in status_hist or 'CONFERIDO' in status_hist:
                            classe = 'historico-badge-sucesso'
                            emoji = '✅'
                        elif 'FRUSTRADA' in status_hist or 'PROBLEMA' in status_hist or 'CANCELADO' in status_hist or 'RECUSA' in status_hist:
                            classe = 'historico-badge-frustrada'
                            emoji = '❌'
                        else:
                            classe = 'historico-badge-em-rota'
                            emoji = '🚐'
                        
                        st.markdown(f"<span class='historico-badge {classe}'>{emoji} {pedido_hist}</span> <span style='font-size:10px; color:#64748b;'>{data_hist}</span>", unsafe_allow_html=True)
                    
                    # Legenda dos ícones
                    st.markdown("""
                        <div class='historico-legenda'>
                            <b>Legenda:</b> ✅ Entregue | ❌ Frustrada/Cancelada | 🚐 Em Rota/Coletada
                        </div>
                    """, unsafe_allow_html=True)
        
        # 💬 ATUALIZAÇÕES E JUSTIFICATIVAS
        st.markdown("<br>", unsafe_allow_html=True)
        if any(x in status for x in ["FRUSTRADA", "PROBLEMA", "CANCELADO"]):
            st.error(f"**⚠️ Motivo da Ocorrência:**\n\n{pedido_data.get('DETALHES', 'Motivo não informado no aplicativo.')}")
        else:
            st.info(f"**💬 Atualizações da Base:**\n\n{pedido_data.get('DETALHES', 'Nenhuma observação pendente.')}")

    # 📷 COLUNA DIREITA - COMPROVANTE
    with col_direita:
        foto = pedido_data.get('COMPROVANTE', '')
        
        if foto and str(foto).startswith("http"):
            st.markdown(f"<div style='background:#f8fafc; padding:16px; border-radius:12px; border:1px solid #e2e8f0; box-shadow:0 1px 2px rgba(0,0,0,0.02);'><p style='font-size:12px; font-weight:700; color:#64748b; text-transform:uppercase; margin:0 0 12px 0;'>📸 Canhoto da Entrega</p></div>", unsafe_allow_html=True)
            st.image(foto, use_container_width=True)
            
            # 🔽 BOTÃO DE DOWNLOAD
            # Extrair nome do arquivo da URL ou usar um padrão
            try:
                nome_arquivo = foto.split('/')[-1] if '/' in foto else f"canhoto_{pedido_data.get('PEDIDO', 'pedido')}.jpg"
                # Se não tiver extensão, adiciona
                if '.' not in nome_arquivo:
                    nome_arquivo = f"{nome_arquivo}.jpg"
            except:
                nome_arquivo = f"canhoto_{pedido_data.get('PEDIDO', 'pedido')}.jpg"
            
            try:
                response = requests.get(foto, timeout=5)
                if response.status_code == 200:
                    st.download_button(
                        label="⬇️ Baixar Canhoto",
                        data=response.content,
                        file_name=nome_arquivo,
                        mime="image/jpeg",
                        use_container_width=True
                    )
            except:
                st.markdown(f"<p style='text-align:center; color:#64748b; font-size:12px;'>📎 <a href='{foto}' target='_blank'>Abrir em nova aba</a></p>", unsafe_allow_html=True)
                
        elif any(x in status for x in ["FRUSTRADA", "PROBLEMA", "CANCELADO"]):
            st.warning("📷 Nenhuma foto da ocorrência foi anexada na justificativa.")
        else:
            st.info("📷 **Aguardando anexo do canhoto da operação.**")

    st.markdown("<br>", unsafe_allow_html=True)

    # 🔘 BOTÃO DE FECHAR (shadcn-ui)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if button("✖️ Fechar Detalhes", key="fechar_detalhes_btn", variant="secondary"):
            st.session_state.modal_aberto = False
            st.session_state.pedido_modal = None
            st.session_state.linha_clicada = None
            st.session_state.modal_fechado = True  # Flag para ignorar a próxima seleção
            st.session_state.ignorar_selecao_grid = True  # Ignora seleção da grid nos próximos frames
            st.session_state.grid_key = st.session_state.get('grid_key', 0) + 1 # Força a tabela a piscar e esquecer
            st.rerun()


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
                if u in CLIENTES_CONFIG and s == CLIENTES_CONFIG[u]["senha"]:
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
    nome_tomador_oficial = conf["filtro"] if conf["filtro"] != "TODOS" else "MATRIZ IGO"

    # ── SIDEBAR ────────────────────────────────────────
    with st.sidebar:
        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 4, 1])
        with col2:
            try:
                st.image(conf["logo"], use_container_width=True)
            except Exception:
                st.markdown(f"<h3 style='text-align:center;'>{st.session_state.cliente}</h3>", unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<p style='font-size: 11px; font-weight: 800; color: #64748B; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 5px;'>Filtros de Visão</p>", unsafe_allow_html=True)
        
        with st.container(border=True):
            st.markdown("<p style='font-size: 14px; font-weight: 700; color: #1e293b; margin-bottom: 5px;'>🗓️ Período de Análise</p>", unsafe_allow_html=True)
            c1_dt, c2_dt = st.columns(2)
            dt_inicio = c1_dt.date_input("De:", value=hoje_br - timedelta(days=15), format="DD/MM/YYYY")
            dt_fim    = c2_dt.date_input("Até:", value=hoje_br, format="DD/MM/YYYY")
            datas_sel = (dt_inicio, dt_fim)
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
                                texto_final += f"💬 *Mensagem:* {msg_chamado}\n\n⏳ _Acesse o Torre de Controle para responder._"
                                
                                # 🔥 Notifica os números especificados para acompanhamento dos chamados
                                numeros_notificacao_chamados = ["5511997163954", "5511984911231"]
                                for numero in numeros_notificacao_chamados:
                                    enviar_whatsapp_zapi_cliente(numero, texto_final)
                                st.success(f"✅ Ticket {tkt_id} aberto com sucesso! Acompanhe na aba 'Meus Chamados'.")
                            except Exception as e:
                                st.error(f"Erro ao criar ticket: {e}")

        holder_exportar = st.empty()

    # ── HEADER ─────────────────────────────────────────
    agora_str = datetime.now(FUSO_BR).strftime('%H:%M')
    st.markdown(f"""
        <div class="header-container">
            <div>
                <div class="header-title">Painel de Rastreio</div>
                <div class="header-subtitle">{st.session_state.cliente} · {hoje_br.strftime('%d/%m/%Y')}</div>
            </div>
            <div class="sync-status">
                <span class="sync-dot"></span> Online · {agora_str}
            </div>
        </div>
    """, unsafe_allow_html=True)

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
                    "FRUSTRADA":  len(df_f[df_f['STATUS_DISPLAY'].str.contains('Frustrada', case=False)]),
                    "COLETADO":   len(df_f[df_f['STATUS_DISPLAY'].str.contains('Coletado|Rota', case=False, na=False)]),
                    "PENDENTE":   len(df_f[df_f['STATUS_DISPLAY'].str.contains('Pendente', case=False, na=False)]),
                    "Aguardando": len(df_f[df_f['STATUS_DISPLAY'].str.contains('Aguardando', case=False)]),
                    "HOJE":       len(df_f[df_f['DATA_OBJ'] == hoje_br]),
                }

                cols_kpi = st.columns(7) 
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
                        margin-top: -110px !important; position: relative; z-index: 999; opacity: 0 !important;
                    }
                    div.st-key-kpi_total button, div.st-key-kpi_entregue button, div.st-key-kpi_frus button, 
                    div.st-key-kpi_coletado button, div.st-key-kpi_pend button, div.st-key-kpi_aguardando button, div.st-key-kpi_hoje button {
                        height: 105px !important; cursor: pointer !important;
                    }
                    </style>
                """, unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                df_h = df_f[df_f['DATA_OBJ'] == hoje_br]
                if not df_h.empty:
                    n_fim = len(df_h[df_h['STATUS_DISPLAY'].str.contains('Entregue|Frustrada|Cancelado|Recusada|Coletado|Em Transferência', case=False)])
                    n_tot  = len(df_h)
                    pct    = round((n_fim / n_tot) * 100) if n_tot else 0
                else:
                    n_fim = 0
                    n_tot = 0
                    pct = 0

                if pct >= 80:
                    bar_color = '#22c55e'
                elif pct >= 50:
                    bar_color = '#f59e0b'
                else:
                    bar_color = '#ef4444'

                st.sidebar.markdown(f"""
                    <div class="progress-block-sidebar">
                        <div class="progress-block-sidebar-content">
                            <div class="progress-title-sidebar">🎯 Progresso de Hoje</div>
                            <div class="progress-number-sidebar">{pct}%</div>
                            <div class="progress-text-sidebar">{n_fim} de {n_tot} pedidos concluídos hoje</div>
                            <div class="progress-bar-bg">
                                <div class="progress-bar-fill" style="width:{pct}%;background:{bar_color};"></div>
                            </div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

                st.sidebar.markdown("<br>", unsafe_allow_html=True)
                if st.sidebar.button("🚪 Sair com Segurança", use_container_width=True, type="secondary"):
                    st.session_state.logado = False
                    st.query_params.clear() 
                    st.rerun()

                col_busca, col_export = st.columns([6, 1], gap="small")
                with col_busca:
                    busca = shadcn_input(placeholder="🔎 Buscar por pedido, laboratório, cidade...", key="busca_grid_input")
                with col_export:
                    holder_download = st.empty()

                df_grid = df_f.copy()
                
                if st.session_state.filtro_kpi != "TODOS":
                    if st.session_state.filtro_kpi == "HOJE":
                        df_grid = df_grid[df_grid['DATA_OBJ'] == hoje_br]
                    elif st.session_state.filtro_kpi == "PENDENTE":
                        df_grid = df_grid[df_grid['STATUS_DISPLAY'].str.contains('Pendente', case=False, na=False)]
                    elif st.session_state.filtro_kpi == "COLETADO":
                        df_grid = df_grid[df_grid['STATUS_DISPLAY'].str.contains('Coletado|Rota', case=False, na=False)]
                    else:
                        df_grid = df_grid[df_grid['STATUS_DISPLAY'].str.contains(st.session_state.filtro_kpi, case=False)]

                if busca:
                    df_grid = df_grid[df_grid.astype(str).apply(lambda x: x.str.lower().str.contains(busca.lower())).any(axis=1)]

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
                    gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=15)
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
                        st.rerun()  # Força rerun para aplicar a flag ANTES de renderizar a grid

                    ag_response = AgGrid(
                        df_final[colunas_visiveis],
                        gridOptions=gridOptions,
                        theme="alpine",
                        columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS,
                        height=550,
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
                        st.session_state.pedido_modal = None
                        st.session_state.linha_clicada = None

                    # Abre o Modal
                    if st.session_state.modal_aberto and st.session_state.pedido_modal:
                        # Sempre buscar na df_final inteira, pois a grid omite dados do dicionário
                        dados_completos_linha = df_final[df_final['PEDIDO'] == st.session_state.pedido_modal].iloc[0].to_dict()
                        st.session_state.modal_renderizado_antes = True  # Marca que o modal foi renderizado
                        modal_detalhes_pedido(dados_completos_linha, df_final)


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
                    with st.container(border=True):
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
