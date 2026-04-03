import streamlit as st
import pandas as pd
import io
import csv
import re
import unicodedata
import holidays
import os
import tempfile
import urllib.parse
import urllib.request
import requests
from datetime import datetime, timedelta, timezone
import random
import gspread
import uuid
from streamlit_autorefresh import st_autorefresh
from fpdf import FPDF

FUSO_BR = timezone(timedelta(hours=-3))

# =============================================================================
# 🔗 1. CONFIGURAÇÃO DA PÁGINA E AUTENTICAÇÃO
# =============================================================================
st.set_page_config(page_title="C.C.O - IGO Logística", layout="wide", page_icon="🚚", initial_sidebar_state="collapsed")

st_autorefresh(interval=120000, limit=None, key="refresh_timer")

# 🔥 CSS GLOBAL E BARRA DE TAREFAS
st.markdown("""
    <style>
    [data-testid="stToolbar"] { display: none !important; }
    .stAppDeployButton { display: none !important; }
    .stDeployButton { display: none !important; }
    [class^="viewerBadge"] { display: none !important; }
    [class*="viewerBadge"] { display: none !important; }
    iframe[src*="badge"] { display: none !important; }
    #MainMenu { display: none !important; }
    footer { display: none !important; }
    
    .block-container { padding-top: 2rem !important; padding-bottom: 120px !important; max-width: 96% !important; }
    [data-testid="stAppViewContainer"] { background-color: #FFFFFF !important; }
    
    div[data-testid="stRadio"] {
        position: fixed !important;
        bottom: 0 !important;
        left: 0 !important;
        width: 100vw !important;
        background-color: #0F172A !important;
        padding: 12px 0px !important;
        z-index: 999999 !important;
        box-shadow: 0px -10px 25px -5px rgba(0, 0, 0, 0.3) !important;
        border-top: 1px solid #1E293B !important;
        margin: 0 !important;
    }
    div[data-testid="stRadio"] > div {
        display: flex;
        flex-direction: row;
        flex-wrap: wrap;
        justify-content: center;
        gap: 8px;
    }
    div[data-testid="stRadio"] label {
        background-color: transparent !important;
        border: 1px solid transparent !important;
        padding: 6px 14px !important;
        border-radius: 8px !important;
        cursor: pointer !important;
        transition: all 0.2s ease !important;
        margin: 0 !important;
    }
    div[data-testid="stRadio"] label:hover { background-color: #1E293B !important; }
    div[data-testid="stRadio"] label p { color: #94A3B8 !important; font-weight: 600 !important; font-size: 13px !important; margin: 0 !important; }
    div[data-testid="stRadio"] label[data-checked="true"] { background-color: #38BDF8 !important; box-shadow: 0 0 10px rgba(56, 189, 248, 0.4) !important; }
    div[data-testid="stRadio"] label[data-checked="true"] p { color: #0F172A !important; font-weight: 800 !important; }
    
    /* FIX NATIVO PARA OCULTAR BOLINHAS DO RADIO BUTTON NO CELULAR */
    div[role="radiogroup"] label div:first-of-type { display: none !important; }
    div[role="radiogroup"] label input { display: none !important; }

    .dinamic-text { color: #0F172A !important; font-weight: 800; letter-spacing: -0.5px; }
    .dinamic-border { border-bottom: 2px solid #E2E8F0 !important; margin-bottom: 24px; padding-bottom: 8px; }
    
    div.st-key-kpi_total button, div.st-key-kpi_entregue button, div.st-key-kpi_pend button, div.st-key-kpi_frus button, div.st-key-kpi_atra button, div.st-key-kpi_hoje button { 
        border-radius: 8px !important; border: none !important; height: 70px !important; display: flex !important; flex-direction: column !important; justify-content: center !important; align-items: center !important; padding: 0px 5px !important; box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important;
    }
    div.st-key-kpi_total button { background: linear-gradient(135deg, #1E293B 0%, #334155 100%) !important; }
    div.st-key-kpi_entregue button { background: linear-gradient(135deg, #059669 0%, #10B981 100%) !important; }
    div.st-key-kpi_pend button { background: linear-gradient(135deg, #D97706 0%, #F59E0B 100%) !important; }
    div.st-key-kpi_frus button { background: linear-gradient(135deg, #991B1B 0%, #EF4444 100%) !important; }
    div.st-key-kpi_atra button { background: linear-gradient(135deg, #7F1D1D 0%, #B91C1C 100%) !important; }
    div.st-key-kpi_hoje button { background: linear-gradient(135deg, #0369A1 0%, #0EA5E9 100%) !important; }
    div.st-key-kpi_total button p, div.st-key-kpi_entregue button p, div.st-key-kpi_pend button p, div.st-key-kpi_frus button p, div.st-key-kpi_atra button p, div.st-key-kpi_hoje button p { 
        color: white !important; font-weight: 800 !important; font-size: 13px !important; margin: 0 !important; text-align: center !important; white-space: pre-wrap !important; line-height: 1.3 !important;
    }

    .stButton > button[kind="primary"] { background: #0284C7 !important; border: none !important; border-radius: 6px !important; font-weight: 700 !important; color: #FFFFFF !important;}
    .stButton > button[kind="primary"]:hover { background: #0369A1 !important; }
    </style>
""", unsafe_allow_html=True)

st.markdown("""<style>[data-testid="stSidebar"] { display: none !important; }</style>""", unsafe_allow_html=True)

if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

# =============================================================================
# 🔐 TELA DE LOGIN
# =============================================================================
if not st.session_state.autenticado:
    st.markdown("""
        <style>
        [data-testid="stForm"] { background: #FFFFFF; padding: 40px 30px; border-radius: 12px; box-shadow: 0 10px 25px rgba(0, 0, 0, 0.08); border: 1px solid #E2E8F0; max-width: 380px !important; margin: 8vh auto !important; }
        .login-header { text-align: center; margin-bottom: 25px; }
        .login-title { color: #0F172A; font-weight: 800; font-size: 20px; margin-top: 15px; letter-spacing: -0.5px; }
        .login-subtitle { color: #64748B; font-size: 13px; font-weight: 500; }
        </style>
    """, unsafe_allow_html=True)
    
    with st.form("form_login"):
        st.markdown("""
            <div class="login-header">
                <img src="https://i.postimg.cc/x84nnjjq/IGO-LOGO.png" width="160">
                <div class="login-title">PORTAL CORPORATIVO</div>
                <div class="login-subtitle">Autenticação de Operadores</div>
            </div>
        """, unsafe_allow_html=True)
        
        usuario = st.text_input("👤 Usuário")
        senha = st.text_input("🔑 Senha", type="password")
        st.markdown("<br>", unsafe_allow_html=True)
        submit = st.form_submit_button("ACESSAR SISTEMA", use_container_width=True, type="primary")
        
        if submit:
            logins_autorizados = {"robson.melo": "123", "william.bertoldo": "123"}
            if usuario in logins_autorizados and logins_autorizados[usuario] == senha:
                st.session_state.autenticado = True
                st.rerun()
            else:
                st.error("❌ Credenciais inválidas.")
    st.stop()

# =============================================================================
# 🔗 2. CONEXÃO COM A NUVEM E CÉREBRO DE DADOS
# =============================================================================
@st.cache_resource
def conectar_banco():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        if "google_token_json" in st.secrets:
            import json
            from google.oauth2.credentials import Credentials
            token_info = json.loads(st.secrets["google_token_json"])
            creds = Credentials.from_authorized_user_info(token_info, scopes)
            gc = gspread.authorize(creds)
            return gc.open("DB_IGO_Logistica")
        else:
            return None
    except Exception as e:
        return None

def carregar_dados_agentes(_planilha):
    if not _planilha: return pd.DataFrame()
    try:
        aba = _planilha.worksheet("Agentes")
        dados = aba.get_all_values()
        if len(dados) > 1: return pd.DataFrame(dados[1:], columns=dados[0])
    except Exception: pass
    return pd.DataFrame(columns=["ROTA MAPEADA", "LOGIN DO AGENTE", "NOME DO AGENTE", "TELEFONE"])

@st.cache_data(ttl=20)
def carregar_dados_completos(_planilha):
    if not _planilha: return pd.DataFrame()
    try:
        aba_m = _planilha.worksheet("Memoria_Sistema")
        dados_m = aba_m.get_all_values()
        if len(dados_m) > 1:
            df = pd.DataFrame(dados_m[1:], columns=dados_m[0])
            df.columns = df.columns.str.strip().str.upper() 
            df = df.loc[:, ~df.columns.duplicated()].copy()
            
            try:
                aba_app = _planilha.worksheet("App_Tarefas")
                dados_app = aba_app.get_all_values()
                if len(dados_app) > 1:
                    df_app = pd.DataFrame(dados_app[1:], columns=dados_app[0])
                    cols_limpas = [str(c).upper().strip().replace('?', '').replace(' ', '') for c in df_app.columns]
                    df_app.columns = cols_limpas
                    df_app = df_app.loc[:, ~df_app.columns.duplicated()].copy()
                    
                    cols_to_extract = ['PEDIDO', 'STATUS', 'OBSERVACOES']
                    if 'FOTO' in df_app.columns: cols_to_extract.append('FOTO')
                    if 'DATA_ENTREGA' in df_app.columns: cols_to_extract.append('DATA_ENTREGA')
                    
                    col_qr_app = next((c for c in ['QR_CODE', 'QRCODE', 'QR', 'CODIGO'] if c in df_app.columns), None)
                    if col_qr_app: cols_to_extract.append(col_qr_app)
                    
                    df_app_clean = df_app[[c for c in cols_to_extract if c in df_app.columns]].copy()
                    rename_map = {'STATUS': 'APP_STATUS', 'OBSERVACOES': 'APP_OBS', 'FOTO': 'APP_FOTO'}
                    if 'DATA_ENTREGA' in df_app.columns: rename_map['DATA_ENTREGA'] = 'APP_DATA_ENTREGA'
                    if col_qr_app: rename_map[col_qr_app] = 'APP_QR'
                    df_app_clean.rename(columns=rename_map, inplace=True)
                    
                    df_app_clean['PEDIDO'] = df_app_clean['PEDIDO'].astype(str).str.strip()
                    df_app_clean.drop_duplicates(subset=['PEDIDO'], keep='last', inplace=True)
                    
                    rom_mask = df_app_clean['PEDIDO'].str.startswith('ROM-', na=False)
                    rom_dict = df_app_clean[rom_mask].set_index('PEDIDO').to_dict('index')
                    
                    df['PEDIDO'] = df['PEDIDO'].astype(str).str.strip()
                    df = pd.merge(df, df_app_clean, on='PEDIDO', how='left')
                    
                    if 'APP_QR' in df.columns:
                        if 'QR_CODE' not in df.columns: df['QR_CODE'] = df['APP_QR']
                        else: df['QR_CODE'] = df.apply(lambda r: r['APP_QR'] if str(r.get('APP_QR','')).strip() and str(r.get('APP_QR','')).upper() != 'NAN' else r.get('QR_CODE', ''), axis=1)

                    def get_true_status(row):
                        s_db = str(row.get('STATUS', '')).strip().upper()
                        s_app = str(row.get('APP_STATUS', '')).strip().upper()
                        rom_id = str(row.get('ROMANEIO', '')).strip()
                        if rom_id in rom_dict:
                            s_rom = str(rom_dict[rom_id].get('APP_STATUS', '')).strip().upper()
                            if s_rom in ['ENTREGUE', 'FRUSTRADA', 'PROBLEMA', 'CANCELADO']: return s_rom
                        if s_db in ['ENTREGUE', 'CANCELADO', 'FRUSTRADA', 'PROBLEMA']: return s_db
                        if s_app in ['ENTREGUE', 'CANCELADO', 'FRUSTRADA', 'PROBLEMA']: return s_app
                        if s_db in ['EM ROTA DE ENTREGA', 'CONFERIDO']: return s_db
                        if s_app and s_app != 'NAN': return s_app
                        return s_db
                    df['STATUS'] = df.apply(get_true_status, axis=1)
                    
                    def get_true_data_entrega(row):
                        d_db = str(row.get('DATA_ENTREGA', '')).strip()
                        s_final = str(row.get('STATUS', '')).strip().upper()
                        rom_id = str(row.get('ROMANEIO', '')).strip()
                        if rom_id in rom_dict:
                            d_rom = str(rom_dict[rom_id].get('APP_DATA_ENTREGA', '')).strip()
                            if d_rom and d_rom.upper() != 'NAN': return d_rom
                        if s_final in ['ENTREGUE', 'FRUSTRADA', 'PROBLEMA'] and 'APP_DATA_ENTREGA' in row:
                            d_app = str(row.get('APP_DATA_ENTREGA', '')).strip()
                            if d_app and d_app.upper() != 'NAN': return d_app
                        return d_db if d_db.upper() != 'NAN' else ""
                    if 'DATA_ENTREGA' in df.columns or 'APP_DATA_ENTREGA' in df.columns: df['DATA_ENTREGA'] = df.apply(get_true_data_entrega, axis=1)

                    def get_true_foto(row):
                        f_db = str(row.get('FOTO', '')).strip()
                        f_app = str(row.get('APP_FOTO', '')).strip()
                        rom_id = str(row.get('ROMANEIO', '')).strip()
                        if rom_id in rom_dict:
                            f_rom = str(rom_dict[rom_id].get('APP_FOTO', '')).strip()
                            if f_rom and f_rom.upper() != 'NAN': return f_rom
                        if f_app and f_app.upper() != 'NAN': return f_app
                        return f_db
                    if 'APP_FOTO' in df.columns or len(rom_dict) > 0: df['FOTO'] = df.apply(get_true_foto, axis=1)
            except Exception: pass
            
            if 'DATA' in df.columns: df['DATA_OBJ'] = pd.to_datetime(df['DATA'], format='%d/%m/%Y', errors='coerce').dt.date
            return df
    except Exception: pass
    return pd.DataFrame()

planilha_db = conectar_banco()
DF_AGENTES = carregar_dados_agentes(planilha_db)
FERIADOS_BR = holidays.Brazil()
CLIENTES_AUTORIZADOS = ["CUNHA", "CAEP", "SAPIENS", "GRALAB", "SYNVIA", "INNOVATOX", "LABEST", "AIRLAB", "UNILABOR", "SODRE", "BRASILIENSE", "MB_CAEP"]
hoje_br = datetime.now(FUSO_BR).date() 

def despachar_para_appsheet(lista_pedidos_dicts):
    if planilha_db is None or not lista_pedidos_dicts: return False
    try:
        aba = planilha_db.worksheet("App_Tarefas")
        linhas = []
        for p in lista_pedidos_dicts:
            mot = str(p.get('MOTORISTA', p.get('AGENTE_RAW', '')))
            linhas.append([
                str(uuid.uuid4())[:8].upper(), str(p.get('PEDIDO','')), mot, "PENDENTE",
                str(p.get('ENDERECO','')), str(p.get('NUMERO','')), str(p.get('BAIRRO','')), str(p.get('CIDADE','')), str(p.get('CEP','')),
                "", "", str(p.get('LABORATORIO','')), str(p.get('TOMADOR','')), "", str(p.get('ROMANEIO',''))
            ])
        aba.append_rows(linhas)
        return True
    except Exception: return False

def padronizar_texto(texto):
    if pd.isna(texto) or not texto: return ""
    return unicodedata.normalize('NFKD', str(texto).strip()).encode('ASCII', 'ignore').decode('utf-8').upper()

def tratar_texto_global(texto):
    if pd.isna(texto): return ""
    t = padronizar_texto(texto)
    if t in ['0', '0.0', 'NAN', 'NONE', 'NAT']: return ""
    return t[:-2] if t.endswith('.0') else t

def limpar_nome_local_rota(texto): return tratar_texto_global(texto).split('/')[0].split('-')[0].strip()

def obter_login_agente(cidade, bairro, laboratorio, endereco="", base_rotas_df=pd.DataFrame()):
    if base_rotas_df.empty: return ""
    rotas_dict = {padronizar_texto(str(row['ROTA MAPEADA']).upper().replace(" ➔ ", "---").replace(" -> ", "---")): str(row['LOGIN DO AGENTE']).lower().strip() for _, row in base_rotas_df.iterrows()}
    cid, bai, lab, end = limpar_nome_local_rota(cidade), limpar_nome_local_rota(bairro), tratar_texto_global(laboratorio), tratar_texto_global(endereco)
    for c in [f"{cid}---{bai}---{end}", f"{cid}---{bai}---{lab}", f"{cid}---{lab}", f"{cid}---{bai}", cid]:
        if c in rotas_dict: return rotas_dict[c]
    return ""

def calcular_sla_dias(uf, cidade):
    uf, cidade = str(uf).upper().strip(), tratar_texto_global(str(cidade))
    if uf == 'SP': return 1
    if uf == 'RJ': return 2 if cidade in ['ANGRA DOS REIS', 'CAMPOS DOS GOYTACAZES'] else 1
    return 2 if uf in ['GO', 'DF', 'SC', 'RS'] else 3 

def calcular_data_limite(data_ini, prazo):
    try:
        dt = pd.to_datetime(data_ini, format="%d/%m/%Y")
        add = 0
        while add < prazo:
            dt += timedelta(days=1)
            if dt.weekday() < 5 and dt not in FERIADOS_BR: add += 1
        return dt.strftime("%d/%m/%Y")
    except: return data_ini

def gerar_excel_memoria(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Relatorio', index=False)
        writer.sheets['Relatorio'].hide_gridlines(2)
    return output.getvalue()

def obter_proximo_id(df):
    if df is None or df.empty or 'PEDIDO' not in df.columns: return 100000
    try:
        nums = df['PEDIDO'].astype(str).str.extract(r'^(\d{5,7})$')[0].dropna().astype(int)
        return int(nums.max()) + 1 if not nums.empty else 100000
    except: return 100000

def calc_status_display(row):
    status_final = str(row.get('STATUS', '')).strip().upper()
    previsao = str(row.get('DATA_LIMITE', '')).strip()
    res = '⏳ Pendente'
    if 'ENTREGUE' in status_final: res = '✅ Entregue'
    elif 'COLETADO' in status_final: res = '📦 Coletado'
    elif 'ROTA' in status_final: res = '🚚 Em Rota'
    elif 'CONFERIDO' in status_final: res = '☑️ Conferido'
    elif 'FRUSTRADA' in status_final: res = '❌ Frustrada'
    elif 'CANCELADO' in status_final: res = '🚫 Cancelado'
    elif 'PROBLEMA' in status_final: res = '🚨 Problema'
    if '✅' not in res and '🚫' not in res and '❌' not in res and previsao:
        try:
            if datetime.strptime(previsao, "%d/%m/%Y").date() < hoje_br: res = f"{res} ⚠️ ATRASADO"
        except: pass
    return res

if 'filtro_kpi_admin' not in st.session_state: st.session_state.filtro_kpi_admin = "TODOS"

# =============================================================================
# 🎨 3. CABEÇALHO LIMPO
# =============================================================================
col_logo, col_title, col_logout = st.columns([1, 4, 1], vertical_alignment="center")
with col_logo: st.image("https://i.postimg.cc/x84nnjjq/IGO-LOGO.png", width=140)
with col_title:
    st.markdown("<h2 style='color: #0F172A; font-weight: 800; margin: 0; text-align: center;'>PAINEL GERENCIAL</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #64748B; margin: 0; text-align: center; font-weight: 600;'>Centro de Controle Operacional - IGO Logística</p>", unsafe_allow_html=True)
with col_logout:
    if st.button("🚪 Sair", use_container_width=True):
        st.session_state.autenticado = False
        st.cache_data.clear(); st.cache_resource.clear(); st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# =============================================================================
# 🖥️ BARRA DE TAREFAS FIXA NO RODAPÉ
# =============================================================================
menu = st.radio("Navegação:", ["📊 Dashboard", "📝 Manual", "📥 Lotes", "🔬 Triagem", "📱 Zap", "📁 Relatórios", "⚙️ Rotas"], horizontal=True, label_visibility="collapsed")

# =============================================================================
# 🚀 MÓDULO 1: DASHBOARD (TOTALMENTE NATIVO E À PROVA DE FALHAS)
# =============================================================================
if menu == "📊 Dashboard":
    df_raw = carregar_dados_completos(planilha_db)
    if not df_raw.empty:
        df_raw['FOTO_URL'] = df_raw['FOTO'].apply(lambda x: f"https://www.appsheet.com/template/gettablefileurl?appName=APPIGOLOGISTICA-153047553&tableName=App_Tarefas&fileName={str(x).strip()}" if str(x).strip() and str(x).upper() not in ['NAN', 'NONE', ''] else "")
        df_raw['STATUS_DISPLAY'] = df_raw.apply(calc_status_display, axis=1)
        if 'DATA_LIMITE' in df_raw.columns: df_raw['DATA_LIMITE'] = df_raw['DATA_LIMITE'].fillna("").astype(str)
        if 'DATA_ENTREGA' in df_raw.columns: df_raw['DATA_ENTREGA'] = df_raw['DATA_ENTREGA'].fillna("").astype(str)

        col_f1, col_f2 = st.columns(2)
        f_cli = col_f1.selectbox("🏢 Filtrar por Tomador:", ["Todos"] + CLIENTES_AUTORIZADOS)
        f_data = col_f2.date_input("📅 Período de Análise:", value=(hoje_br - timedelta(days=2), hoje_br), format="DD/MM/YYYY")
        
        df_f = df_raw.copy()
        if f_cli != "Todos": df_f = df_f[df_f['TOMADOR'] == f_cli]
        if isinstance(f_data, tuple) and len(f_data) == 2: df_f = df_f[(df_f['DATA_OBJ'] >= f_data[0]) & (df_f['DATA_OBJ'] <= f_data[1])]

        n_tot = len(df_f)
        n_ent = len(df_f[df_f['STATUS_DISPLAY'].str.contains('Entregue')])
        n_pend = len(df_f[df_f['STATUS_DISPLAY'].str.contains('Pendente')])
        n_frus = len(df_f[df_f['STATUS_DISPLAY'].str.contains('Frustrada')])
        n_atra = len(df_f[df_f['STATUS_DISPLAY'].str.contains('ATRASADO')])
        n_hoje = len(df_f[df_f['DATA_OBJ'] == hoje_br])

        c1, c2, c3, c4, c5, c6 = st.columns(6)
        def set_kpi(v): st.session_state.filtro_kpi_admin = v
        c1.button(f"📦 TOTAL\n{n_tot}", key="kpi_total", use_container_width=True, on_click=set_kpi, args=("TODOS",))
        c2.button(f"✅ ENTREGUES\n{n_ent}", key="kpi_entregue", use_container_width=True, on_click=set_kpi, args=("ENTREGUE",))
        c3.button(f"⏳ PENDENTES\n{n_pend}", key="kpi_pend", use_container_width=True, on_click=set_kpi, args=("PENDENTE",))
        c4.button(f"❌ FRUSTRADAS\n{n_frus}", key="kpi_frus", use_container_width=True, on_click=set_kpi, args=("FRUSTRADA",))
        c5.button(f"🚨 ATRASADOS\n{n_atra}", key="kpi_atra", use_container_width=True, on_click=set_kpi, args=("ATRASADO",))
        c6.button(f"📅 HOJE\n{n_hoje}", key="kpi_hoje", use_container_width=True, on_click=set_kpi, args=("HOJE",))

        st.markdown("<br>", unsafe_allow_html=True)
        busca = st.text_input("🔎 Busca Rápida:", placeholder="Digite para filtrar...")

        df_grid = df_f.copy()
        if st.session_state.filtro_kpi_admin == "ENTREGUE": df_grid = df_grid[df_grid['STATUS_DISPLAY'].str.contains('Entregue')]
        elif st.session_state.filtro_kpi_admin == "PENDENTE": df_grid = df_grid[df_grid['STATUS_DISPLAY'].str.contains('Pendente')]
        elif st.session_state.filtro_kpi_admin == "FRUSTRADA": df_grid = df_grid[df_grid['STATUS_DISPLAY'].str.contains('Frustrada')]
        elif st.session_state.filtro_kpi_admin == "ATRASADO": df_grid = df_grid[df_grid['STATUS_DISPLAY'].str.contains('ATRASADO')]
        elif st.session_state.filtro_kpi_admin == "HOJE": df_grid = df_grid[df_grid['DATA_OBJ'] == hoje_br]
        
        if busca: df_grid = df_grid[df_grid.astype(str).apply(lambda x: busca.upper() in x.str.upper().values, axis=1)]

        # 🔥 AQUI ESTÁ A TABELA NATIVA DO STREAMLIT (NÃO CRASHA DE JEITO NENHUM)
        colunas_mostrar = ['DATA', 'PEDIDO', 'TOMADOR', 'LABORATORIO', 'BAIRRO', 'CIDADE', 'UF', 'STATUS_DISPLAY', 'DATA_LIMITE', 'FOTO_URL', 'AGENTE_RAW', 'DATA_ENTREGA']
        df_show = df_grid[[c for c in colunas_mostrar if c in df_grid.columns]].copy()
        df_show.insert(0, "SELECIONAR", False)
        
        st.markdown(f"<p style='color:#059669; font-weight:600; font-size:12px; margin-bottom: 5px;'>🟢 Sincronizado: {datetime.now(FUSO_BR).strftime('%H:%M:%S')}</p>", unsafe_allow_html=True)
        
        # Desenha a tabela com Checkbox
        df_editado = st.data_editor(
            df_show,
            hide_index=True,
            use_container_width=True,
            height=450,
            disabled=[c for c in df_show.columns if c != "SELECIONAR"],
            column_config={
                "SELECIONAR": st.column_config.CheckboxColumn("✔", default=False, width="small"),
                "FOTO_URL": st.column_config.LinkColumn("📸 FOTO", display_text="Ver Link", width="small")
            }
        )
        
        # Capta os selecionados da tabela
        selecionados_df = df_editado[df_editado["SELECIONAR"] == True]
        tem_sel = not selecionados_df.empty
        p_ids = selecionados_df["PEDIDO"].astype(str).tolist() if tem_sel else []

        st.markdown("""
            <style>
            div[data-testid="stPopover"] > button, button[kind="secondary"] { border-radius: 6px !important; height: 32px !important; border: 1px solid #CBD5E1 !important; background-color: #FFFFFF !important; color: #475569 !important; font-weight: 600 !important;}
            div[data-testid="stPopover"] > button:hover, button[kind="secondary"]:hover { border-color: #0284C7 !important; color: #0369A1 !important; background-color: #F0F9FF !important; }
            </style>
        """, unsafe_allow_html=True)
        
        col_b2, col_b3, col_b4, col_b5 = st.columns(4)
        
        with col_b2.popover("📲 Dar Baixa Manual", use_container_width=True):
            if not tem_sel: st.warning("Marque o(s) pedido(s) na tabela primeiro!")
            else:
                status_baixa = st.selectbox("Novo Status:", ["ENTREGUE ✅", "PROBLEMA 🚨", "CANCELADO ❌", "PENDENTE ⏳"])
                data_baixa = st.date_input("Data da Ocorrência:", format="DD/MM/YYYY", value=hoje_br)
                tem_entregue = df_grid[df_grid['PEDIDO'].isin(p_ids)]['STATUS_DISPLAY'].str.contains('Entregue').any()
                senha_reversao = st.text_input("🔑 Senha (Desfazer):", type="password") if tem_entregue else ""
                if st.button("Confirmar Baixa", type="primary", use_container_width=True):
                    status_limpo = status_baixa.split(" ")[0].upper()
                    if tem_entregue and status_limpo != 'ENTREGUE' and senha_reversao != '123': st.error("❌ Senha incorreta!")
                    else:
                        with st.spinner("Atualizando..."):
                            try:
                                aba = planilha_db.worksheet("Memoria_Sistema")
                                dados_aba = aba.get_all_values()
                                df_nuvem = pd.DataFrame(dados_aba[1:], columns=dados_aba[0])
                                mascara = df_nuvem['PEDIDO'].isin(p_ids)
                                df_nuvem.loc[mascara, 'STATUS'] = status_limpo
                                if status_limpo == "ENTREGUE": df_nuvem.loc[mascara, 'DATA_ENTREGA'] = data_baixa.strftime("%d/%m/%Y")
                                elif status_limpo == "PENDENTE": df_nuvem.loc[mascara, 'DATA_ENTREGA'] = ""
                                aba.update("A1", [df_nuvem.columns.tolist()] + df_nuvem.fillna("").astype(str).values.tolist())
                                carregar_dados_completos.clear(); st.success("Atualizado!"); st.rerun()
                            except Exception as e: st.error(f"Erro: {e}")

        with col_b3.popover("👯 Clonar Pedidos", use_container_width=True):
            if not tem_sel: st.warning("Marque o(s) pedido(s) na tabela primeiro!")
            else:
                clone_data = st.date_input("Nova Data:", format="DD/MM/YYYY", value=hoje_br)
                clone_mot = st.selectbox("Agente:", ["Manter Original"] + (sorted(DF_AGENTES['LOGIN DO AGENTE'].unique().tolist()) if not DF_AGENTES.empty else []))
                if st.button("Confirmar Clone", type="primary", use_container_width=True):
                    with st.spinner("Clonando..."):
                        try:
                            aba = planilha_db.worksheet("Memoria_Sistema")
                            df_nuvem = pd.DataFrame(aba.get_all_values()[1:], columns=aba.get_all_values()[0])
                            prox_id = obter_proximo_id(df_nuvem)
                            clones_app = []
                            for pid in p_ids:
                                l_orig = df_nuvem[df_nuvem['PEDIDO'] == pid].iloc[0].copy()
                                novo_id = str(prox_id); prox_id += 1
                                l_orig['PEDIDO'] = novo_id; l_orig['DATA'] = clone_data.strftime("%d/%m/%Y"); l_orig['STATUS'] = "PENDENTE"; l_orig['DATA_ENTREGA'] = ""; l_orig['ROMANEIO'] = ""
                                if clone_mot != "Manter Original": l_orig['AGENTE_RAW'] = clone_mot
                                df_nuvem = pd.concat([df_nuvem, pd.DataFrame([l_orig])], ignore_index=True)
                                if str(l_orig.get('AGENTE_RAW','')).strip(): clones_app.append({'PEDIDO': novo_id, 'MOTORISTA': l_orig['AGENTE_RAW'], 'ENDERECO': l_orig.get('ENDERECO',''), 'NUMERO': l_orig.get('NUMERO',''), 'BAIRRO': l_orig.get('BAIRRO',''), 'CIDADE': l_orig.get('CIDADE',''), 'CEP': l_orig.get('CEP',''), 'LABORATORIO': l_orig.get('LABORATORIO',''), 'TOMADOR': l_orig.get('TOMADOR','')})
                            aba.update("A1", [df_nuvem.columns.tolist()] + df_nuvem.fillna("").astype(str).values.tolist())
                            if clones_app: despachar_para_appsheet(clones_app)
                            carregar_dados_completos.clear(); st.success("Clonado!"); st.rerun()
                        except Exception as e: st.error(f"Erro: {e}")

        with col_b4.popover("🔄 Trocar Motorista", use_container_width=True):
            if not tem_sel: st.warning("Marque o(s) pedido(s) na tabela primeiro!")
            else:
                novo_mot = st.selectbox("Novo Agente:", sorted(DF_AGENTES['LOGIN DO AGENTE'].unique().tolist()) if not DF_AGENTES.empty else [])
                if st.button("Confirmar Troca", type="primary", use_container_width=True):
                    with st.spinner("Trocando..."):
                        try:
                            aba = planilha_db.worksheet("Memoria_Sistema")
                            df_nuvem = pd.DataFrame(aba.get_all_values()[1:], columns=aba.get_all_values()[0])
                            mask = df_nuvem['PEDIDO'].isin(p_ids)
                            df_nuvem.loc[mask, 'AGENTE_RAW'] = novo_mot
                            df_nuvem.loc[mask, 'STATUS'] = "PENDENTE"
                            aba.update("A1", [df_nuvem.columns.tolist()] + df_nuvem.fillna("").astype(str).values.tolist())
                            lista_app = []
                            for _, r in df_nuvem[mask].iterrows(): lista_app.append({'PEDIDO': r['PEDIDO'], 'MOTORISTA': novo_mot, 'ENDERECO': r.get('ENDERECO',''), 'NUMERO': r.get('NUMERO',''), 'BAIRRO': r.get('BAIRRO',''), 'CIDADE': r.get('CIDADE',''), 'CEP': r.get('CEP',''), 'LABORATORIO': r.get('LABORATORIO',''), 'TOMADOR': r.get('TOMADOR','')})
                            despachar_para_appsheet(lista_app)
                            carregar_dados_completos.clear(); st.success("Trocado!"); st.rerun()
                        except Exception as e: st.error(f"Erro: {e}")

        if col_b5.button("🔄 Atualizar Painel", use_container_width=True):
            carregar_dados_completos.clear(); st.rerun()

# =============================================================================
# 📝 MÓDULO MANUAL (BLINDADO)
# =============================================================================
elif menu == "📝 Manual":
    st.markdown("<div class='dinamic-border'><h3 class='dinamic-text' style='margin:0;'>📝 Inserir Novo Pedido Manual</h3></div>", unsafe_allow_html=True)
    def limpar_entrada(texto):
        if pd.isna(texto) or texto is None: return ""
        return padronizar_texto(str(texto).replace('\n', ' ').replace('\r', ' ').replace('"', '').replace("'", "").replace(';', ',').strip())

    if 'm_rua' not in st.session_state: st.session_state['m_rua'] = ""
    if 'm_bai' not in st.session_state: st.session_state['m_bai'] = ""
    if 'm_cid' not in st.session_state: st.session_state['m_cid'] = ""
    if 'm_uf' not in st.session_state: st.session_state['m_uf'] = ""

    with st.container(border=True):
        st.markdown("#### 📍 Busca Inteligente de Endereço")
        cc1, cc2, cc3 = st.columns([2, 1, 3], vertical_alignment="bottom")
        cep_input = cc1.text_input("Digite o CEP", max_chars=9)
        if cc2.button("🔍 Buscar CEP", use_container_width=True):
            cep_limpo = re.sub(r'\D', '', cep_input)
            if len(cep_limpo) == 8:
                try:
                    resp = requests.get(f"https://viacep.com.br/ws/{cep_limpo}/json/").json()
                    if "erro" not in resp:
                        st.session_state['m_rua'] = limpar_entrada(resp.get("logradouro", ""))
                        st.session_state['m_bai'] = limpar_entrada(resp.get("bairro", ""))
                        st.session_state['m_cid'] = limpar_entrada(resp.get("localidade", ""))
                        st.session_state['m_uf'] = limpar_entrada(resp.get("uf", ""))
                        st.rerun()
                    else: st.error("❌ CEP não encontrado.")
                except: st.error("Erro na API ViaCEP.")
        
        st.markdown("---")
        col1, col2 = st.columns(2)
        m_tomador = col1.selectbox("Laboratório Solicitante *", ["Selecione..."] + CLIENTES_AUTORIZADOS)
        m_data = col2.date_input("Data do Pedido *", format="DD/MM/YYYY", value=hoje_br)
        m_lab = st.text_input("Ponto de Coleta *")
        m_rua = st.text_input("Logradouro *", value=st.session_state['m_rua'])
        col3, col4, col5 = st.columns([2, 2, 1])
        m_bai = col3.text_input("Bairro *", value=st.session_state['m_bai'])
        m_cid = col4.text_input("Cidade *", value=st.session_state['m_cid'])
        m_uf = col5.text_input("UF *", value=st.session_state['m_uf'])
        m_agente_escolha = st.selectbox("Agente:", ["Automático (Por Rota)"] + (sorted(DF_AGENTES['LOGIN DO AGENTE'].unique().tolist()) if not DF_AGENTES.empty else []))
        
        if st.button("🚀 Injetar na Base", type="primary", use_container_width=True):
            if m_tomador == "Selecione..." or not m_cid or not m_lab or not m_rua or not m_bai: st.error("⚠️ Preencha os campos obrigatórios!")
            else:
                with st.spinner("Salvando..."):
                    lab_limpo, rua_limpa, bai_limpo, cid_limpa, uf_limpa = limpar_entrada(m_lab), limpar_entrada(m_rua), limpar_entrada(m_bai), limpar_entrada(m_cid), limpar_entrada(m_uf)
                    m_agente = obter_login_agente(cid_limpa, bai_limpo, lab_limpo, rua_limpa, DF_AGENTES) if m_agente_escolha == "Automático (Por Rota)" else m_agente_escolha
                    m_prazo = calcular_sla_dias(uf_limpa, cid_limpa)
                    m_limite = calcular_data_limite(m_data.strftime("%d/%m/%Y"), m_prazo)
                    try:
                        aba_memoria = planilha_db.worksheet("Memoria_Sistema")
                        df_nuvem = pd.DataFrame(aba_memoria.get_all_values()[1:], columns=aba_memoria.get_all_values()[0])
                        m_pedido = str(obter_proximo_id(df_nuvem))
                        novo_ped = pd.DataFrame([{'DATA': m_data.strftime("%d/%m/%Y"), 'PEDIDO': m_pedido, 'TOMADOR': m_tomador, 'LABORATORIO': lab_limpo, 'ENDERECO': rua_limpa, 'NUMERO': "", 'BAIRRO': bai_limpo, 'CIDADE': cid_limpa, 'UF': uf_limpa, 'CEP': limpar_entrada(cep_input), 'STATUS': 'PENDENTE', 'AGENTE_RAW': m_agente, 'PRAZO_DIAS': m_prazo, 'DATA_LIMITE': m_limite, 'DATA_ENTREGA': "", 'FOTO': "", 'ROMANEIO': ""}])
                        df_atual = pd.concat([df_nuvem, novo_ped], ignore_index=True) if not df_nuvem.empty else novo_ped
                        aba_memoria.update("A1", [df_atual.columns.tolist()] + df_atual.fillna("").astype(str).values.tolist())
                        if m_agente: despachar_para_appsheet([novo_ped.iloc[0].to_dict()])
                        st.success(f"🎉 Pedido {m_pedido} criado!")
                        st.session_state['m_rua'] = ""; st.session_state['m_bai'] = ""; st.session_state['m_cid'] = ""; st.session_state['m_uf'] = ""
                        carregar_dados_completos.clear()
                    except Exception as e: st.error(f"Erro ao salvar: {e}")

# =============================================================================
# ➕ MÓDULO Lotes E 🔬 Triagem E OUTROS (ADAPTADOS PARA NATIVO)
# =============================================================================
elif menu == "📥 Lotes":
    st.markdown("<div class='dinamic-border'><h3 class='dinamic-text' style='margin:0;'>➕ Central de Importação de Lotes</h3></div>", unsafe_allow_html=True)
    if "df_preview" not in st.session_state: st.session_state.df_preview = pd.DataFrame()
    with st.container(border=True):
        c1, c2, c3 = st.columns([1, 1, 2])
        with c1: tom = st.selectbox("🏢 Tomador Central:", ["Selecione..."] + CLIENTES_AUTORIZADOS)
        with c2: dt_c = st.date_input("📅 Data da Rota:", format="DD/MM/YYYY", value=hoje_br)
        txt = st.text_area("📋 Cole os dados da planilha do cliente (Ctrl+V):", height=150)
        if st.columns([1, 2])[0].button("🔍 Processar Matriz", type="primary", use_container_width=True):
            if not txt or tom == "Selecione...": st.warning("Preencha o Tomador e cole os dados!")
            else:
                try:
                    delim = '\t' if '\t' in txt else (';' if ';' in txt else ',')
                    df_raw_import = pd.read_csv(io.StringIO(txt), sep=delim, header=None, dtype=str).fillna("")
                    idx_h = max((sum(1 for kw in ['PEDIDO', 'CIDADE', 'LABORAT', 'ENDERE', 'BAIRRO'] if kw in " ".join(df_raw_import.iloc[i].astype(str).values).upper()), i) for i in range(min(15, len(df_raw_import))))[1]
                    df_limpo = df_raw_import.iloc[idx_h+1:].copy()
                    df_limpo.columns = [str(c).strip() for c in df_raw_import.iloc[idx_h].values]
                    for col in df_limpo.columns: df_limpo[col] = df_limpo[col].apply(tratar_texto_global)
                    mapa = {}
                    for c in df_limpo.columns:
                        cl = ''.join(e for e in unicodedata.normalize('NFKD', str(c).upper().strip()).encode('ASCII', 'ignore').decode('utf-8') if e.isalnum()) 
                        if any(x in cl for x in ['PEDIDO', 'SOLICITA', 'CODIGO']) or cl == 'ID': mapa[c] = 'PEDIDO'
                        elif any(x in cl for x in ['LABORAT', 'CLINIC', 'POSTO', 'NOME', 'CLIENTE']): mapa[c] = 'LABORATORIO'
                        elif any(x in cl for x in ['ENDERE', 'RUA', 'LOGRADOURO']): mapa[c] = 'ENDERECO'
                        elif any(x in cl for x in ['NUM', 'NRO']) or cl in ['N', 'NO']: mapa[c] = 'NUMERO'
                        elif 'BAIRRO' in cl: mapa[c] = 'BAIRRO'
                        elif any(x in cl for x in ['CIDADE', 'MUNIC']): mapa[c] = 'CIDADE'
                        elif any(x in cl for x in ['ESTADO', 'UF']): mapa[c] = 'UF'
                        elif 'CEP' in cl: mapa[c] = 'CEP'
                    df_limpo.rename(columns=mapa, inplace=True)
                    for c in ['PEDIDO', 'LABORATORIO', 'CEP', 'ENDERECO', 'NUMERO', 'BAIRRO', 'CIDADE', 'UF']:
                        if c not in df_limpo.columns: df_limpo[c] = ""
                    df_limpo['TOMADOR'] = tom; df_limpo['DATA'] = dt_c.strftime("%d/%m/%Y")
                    df_limpo['AGENTE_RAW'] = df_limpo.apply(lambda r: obter_login_agente(r['CIDADE'], r['BAIRRO'], r['LABORATORIO'], r['ENDERECO'], DF_AGENTES), axis=1)
                    st.session_state.df_preview = df_limpo[df_limpo['LABORATORIO'].str.strip() != ""][['DATA', 'TOMADOR', 'PEDIDO', 'LABORATORIO', 'ENDERECO', 'NUMERO', 'BAIRRO', 'CIDADE', 'UF', 'CEP', 'AGENTE_RAW']]
                    st.rerun()
                except Exception as e: st.error(f"Erro: {e}")

    if not st.session_state.df_preview.empty:
        st.markdown("---")
        df_preview = st.session_state.df_preview
        df_err = df_preview[(df_preview['AGENTE_RAW'].astype(str).str.strip() == "") | (df_preview['AGENTE_RAW'].astype(str).str.upper() == "NAN")]
        df_ok = df_preview[~((df_preview['AGENTE_RAW'].astype(str).str.strip() == "") | (df_preview['AGENTE_RAW'].astype(str).str.upper() == "NAN"))]
        
        if not df_err.empty:
            st.error(f"🚨 {len(df_err)} pedido(s) sem motorista. Corrija na gaveta abaixo.")
            with st.form("form_correcao_agentes"):
                correcoes = {}
                for idx, row in df_err.iterrows():
                    st.markdown(f"**Cód:** {row['PEDIDO']} | **Local:** {row['LABORATORIO']} | **Logradouro:** {row['ENDERECO']} - {row['BAIRRO']}, {row['CIDADE']}")
                    correcoes[idx] = st.selectbox(f"Motorista:", ["Selecione..."] + sorted(DF_AGENTES['LOGIN DO AGENTE'].unique().tolist()), key=f"fix_mot_{idx}")
                if st.form_submit_button("Validar Correções", type="primary"):
                    for idx, novo_mot in correcoes.items():
                        if novo_mot != "Selecione...": st.session_state.df_preview.at[idx, 'AGENTE_RAW'] = novo_mot
                    st.rerun()
        else:
            st.success("✅ Tudo validado!")
            st.dataframe(df_ok, hide_index=True, use_container_width=True, height=350) # Tabela nativa
            if st.columns([1, 2])[0].button("🚀 INJETAR NO BANCO", type="primary", use_container_width=True):
                with st.spinner("Processando..."):
                    try:
                        aba = planilha_db.worksheet("Memoria_Sistema")
                        df_up = pd.DataFrame(aba.get_all_values()[1:], columns=aba.get_all_values()[0])
                        prox_id = obter_proximo_id(df_up)
                        for idx, row in df_ok.iterrows():
                            if not str(row['PEDIDO']).strip() or str(row['PEDIDO']).upper() == 'NAN': df_ok.at[idx, 'PEDIDO'] = str(prox_id); prox_id += 1
                        df_ok['PRAZO_DIAS'] = df_ok.apply(lambda r: calcular_sla_dias(r['UF'], r['CIDADE']), axis=1)
                        df_ok['DATA_LIMITE'] = df_ok.apply(lambda r: calcular_data_limite(r['DATA'], int(r['PRAZO_DIAS'])), axis=1)
                        df_ok['STATUS'] = 'PENDENTE'; df_ok['DATA_ENTREGA'] = ''; df_ok['FOTO'] = ''; df_ok['ROMANEIO'] = ''
                        df_up = pd.concat([df_up, df_ok], ignore_index=True)
                        aba.update("A1", [df_up.columns.tolist()] + df_up.fillna("").astype(str).values.tolist())
                        lista_app = [r.to_dict() for _, r in df_ok.iterrows() if str(r.get('AGENTE_RAW','')).strip()]
                        despachar_para_appsheet(lista_app)
                        st.session_state.df_preview = pd.DataFrame(); carregar_dados_completos.clear(); st.rerun()
                    except Exception as e: st.error(f"Erro: {e}")

elif menu == "🔬 Triagem":
    st.markdown("<div class='dinamic-border'><h3 class='dinamic-text' style='margin:0;'>🔬 Terminal de Triagem e Expedição</h3></div>", unsafe_allow_html=True)
    df_raw = carregar_dados_completos(planilha_db)
    if not df_raw.empty:
        t1, t2, t3 = st.tabs(["📦 1. Validação Manual Lote", "🚚 2. Gerar Romaneio", "🕒 3. Histórico"])
        
        with t1:
            df_fila = df_raw[df_raw['STATUS'].astype(str).str.upper() == 'COLETADO'][['DATA', 'PEDIDO', 'TOMADOR', 'LABORATORIO', 'CIDADE', 'STATUS']].copy()
            if not df_fila.empty:
                df_fila.insert(0, "✔", False)
                st_edit_fila = st.data_editor(df_fila, hide_index=True, disabled=[c for c in df_fila.columns if c != "✔"], use_container_width=True, height=350)
                sel_fila = st_edit_fila[st_edit_fila["✔"]]
                if st.button("✅ Enviar Selecionados para Despacho", type="primary"):
                    if sel_fila.empty: st.warning("Selecione na tabela!")
                    else:
                        with st.spinner("Atualizando..."):
                            try:
                                aba = planilha_db.worksheet("Memoria_Sistema")
                                df_nuvem = pd.DataFrame(aba.get_all_values()[1:], columns=aba.get_all_values()[0])
                                df_nuvem.loc[df_nuvem['PEDIDO'].isin(sel_fila['PEDIDO'].astype(str)), 'STATUS'] = 'CONFERIDO'
                                aba.update("A1", [df_nuvem.columns.tolist()] + df_nuvem.fillna("").astype(str).values.tolist())
                                carregar_dados_completos.clear(); st.rerun()
                            except Exception as e: st.error(f"Erro: {e}")
            else: st.info("Salão vazio.")

        with t2:
            df_conf = df_raw[df_raw['STATUS'].astype(str).str.upper() == 'CONFERIDO'].copy()
            if not df_conf.empty:
                col_rom = ['DATA', 'PEDIDO', 'TOMADOR', 'LABORATORIO', 'CIDADE', 'UF']
                df_conf_show = df_conf[col_rom].copy()
                df_conf_show.insert(0, "✔", False)
                st_edit_rom = st.data_editor(df_conf_show, hide_index=True, disabled=[c for c in df_conf_show.columns if c != "✔"], use_container_width=True, height=300)
                sel_rom = st_edit_rom[st_edit_rom["✔"]]
                
                c_mot, c_data, c_btn = st.columns([2, 1, 2])
                mot = c_mot.selectbox("👤 Motorista:", ["Selecione..."] + sorted(DF_AGENTES['LOGIN DO AGENTE'].unique().tolist()) if not DF_AGENTES.empty else ["Selecione..."])
                dt = c_data.date_input("📅 Data:", value=hoje_br)
                if c_btn.button("🚚 Despachar Lote", type="primary", use_container_width=True):
                    if sel_rom.empty or mot == "Selecione...": st.warning("Marque pedidos e informe motorista.")
                    else:
                        with st.spinner("Gerando..."):
                            id_rom = f"ROM-{datetime.now().strftime('%d%m')}-{random.randint(100,999)}"
                            pids = sel_rom['PEDIDO'].astype(str).tolist()
                            try:
                                aba = planilha_db.worksheet("Memoria_Sistema")
                                df_nuvem = pd.DataFrame(aba.get_all_values()[1:], columns=aba.get_all_values()[0])
                                mask = df_nuvem['PEDIDO'].isin(pids)
                                df_nuvem.loc[mask, 'STATUS'] = 'EM ROTA DE ENTREGA'
                                df_nuvem.loc[mask, 'ROMANEIO'] = id_rom
                                df_nuvem.loc[mask, 'DATA'] = dt.strftime("%d/%m/%Y")
                                df_nuvem.loc[mask, 'AGENTE_RAW'] = mot
                                aba.update("A1", [df_nuvem.columns.tolist()] + df_nuvem.fillna("").astype(str).values.tolist())
                                despachar_para_appsheet([{'PEDIDO': id_rom, 'MOTORISTA': mot, 'ENDERECO': "LOTE", 'NUMERO': str(len(pids)), 'BAIRRO': "BASE", 'CIDADE': "BASE", 'CEP': "---", 'LABORATORIO': "LOTE", 'TOMADOR': "LOTE", 'ROMANEIO': id_rom}])
                                carregar_dados_completos.clear(); st.success(f"Lote {id_rom} criado!")
                                st.rerun()
                            except Exception as e: st.error(f"Erro: {e}")

        with t3:
            df_hist = df_raw[df_raw['STATUS'].astype(str).str.upper().isin(['CONFERIDO', 'EM ROTA DE ENTREGA', 'ENTREGUE', 'FRUSTRADA', 'PROBLEMA', 'CANCELADO'])].copy()
            if not df_hist.empty: st.dataframe(df_hist[['DATA', 'PEDIDO', 'TOMADOR', 'LABORATORIO', 'STATUS', 'AGENTE_RAW']], hide_index=True, use_container_width=True, height=400)
    else: st.warning("Banco vazio.")

elif menu == "📱 Zap":
    st.markdown("<div class='dinamic-border'><h3 class='dinamic-text' style='margin:0;'>📱 Central Tática de Comunicação</h3></div>", unsafe_allow_html=True)
    df_raw = carregar_dados_completos(planilha_db)
    if not df_raw.empty:
        data_filtro = st.date_input("📅 Data:", value=hoje_br)
        df_pendentes = df_raw[(df_raw['DATA_OBJ'] == data_filtro) & (df_raw['STATUS'].astype(str).str.upper() == 'PENDENTE')].copy()
        if not df_pendentes.empty:
            dict_telefones = {str(row.get('LOGIN DO AGENTE', '')).strip().lower(): re.sub(r'\D', '', str(row.get('TELEFONE', ''))) for _, row in DF_AGENTES.iterrows()} if not DF_AGENTES.empty else {}
            for agente in df_pendentes['AGENTE_RAW'].dropna().unique():
                if not str(agente).strip(): continue
                df_agente = df_pendentes[df_pendentes['AGENTE_RAW'] == agente]
                tel = dict_telefones.get(str(agente).strip().lower(), "")
                with st.expander(f"👤 {str(agente).upper()} | Volumes: {len(df_agente)}"):
                    st.dataframe(df_agente[['PEDIDO', 'LABORATORIO']], hide_index=True, use_container_width=True)
                    if tel:
                        msg = f"Rota IGO: {len(df_agente)} pedidos.\n" + "\n".join([f"- {r['PEDIDO']} ({r['LABORATORIO']})" for _, r in df_agente.iterrows()])
                        st.link_button("📲 Enviar WhatsApp", f"https://api.whatsapp.com/send?phone={tel}&text={urllib.parse.quote(msg)}", type="primary")

elif menu == "📁 Relatórios":
    st.markdown("<div class='dinamic-border'><h3 class='dinamic-text' style='margin:0;'>📥 Central de Exportação</h3></div>", unsafe_allow_html=True)
    df_raw = carregar_dados_completos(planilha_db)
    if not df_raw.empty:
        st.download_button("📥 Extração Completa (Excel)", data=gerar_excel_memoria(df_raw), file_name=f"Base_Completa.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary")

elif menu == "⚙️ Rotas":
    st.markdown("<div class='dinamic-border'><h3 class='dinamic-text' style='margin:0;'>⚙️ Matriz de Rotas e Equipe</h3></div>", unsafe_allow_html=True)
    tab_ag, tab_rota, tab_admin = st.tabs(["👤 Novo Agente", "📍 Nova Rota", "⚠️ Área Administrativa"])
    
    with tab_ag:
        with st.form("f_ag"):
            lg, nm, tl = st.text_input("Login"), st.text_input("Nome"), st.text_input("Telefone")
            if st.form_submit_button("Salvar"):
                planilha_db.worksheet("Agentes").append_row(["SEM ROTA", lg.lower().strip(), nm.upper().strip(), re.sub(r'\D', '', tl)])
                carregar_dados_agentes.clear(); st.success("Salvo!")
                
    with tab_rota:
        with st.form("f_rt"):
            cd, lg2 = st.text_input("Cidade"), st.selectbox("Agente", sorted(DF_AGENTES['LOGIN DO AGENTE'].unique().tolist()) if not DF_AGENTES.empty else [])
            if st.form_submit_button("Salvar"):
                dados = DF_AGENTES[DF_AGENTES['LOGIN DO AGENTE'] == lg2].iloc[0]
                planilha_db.worksheet("Agentes").append_row([limpar_nome_local_rota(cd), lg2, dados['NOME DO AGENTE'], dados['TELEFONE']])
                carregar_dados_agentes.clear(); st.success("Salvo!")
                
    with tab_admin:
        st.warning("⚠️ ZERAR BANCO (INÍCIO DE PRODUÇÃO)")
        senha = st.text_input("Senha Admin:", type="password")
        if st.button("LIMPAR BASE COMPLETA", type="primary"):
            if senha == "123":
                aba_m = planilha_db.worksheet("Memoria_Sistema")
                h_m = aba_m.get_all_values()[0]
                aba_m.clear(); aba_m.update("A1", [h_m])
                try:
                    aba_a = planilha_db.worksheet("App_Tarefas")
                    h_a = aba_a.get_all_values()[0]
                    aba_a.clear(); aba_a.update("A1", [h_a])
                except: pass
                carregar_dados_completos.clear(); st.success("Banco Zerado!"); st.rerun()
            else: st.error("Senha Incorreta")
