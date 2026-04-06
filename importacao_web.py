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
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, GridUpdateMode
from fpdf import FPDF

FUSO_BR = timezone(timedelta(hours=-3))

# =============================================================================
# 🔗 1. CONFIGURAÇÃO DA PÁGINA E AUTENTICAÇÃO
# =============================================================================
st.set_page_config(page_title="C.C.O - IGO Logística", layout="wide", page_icon="🚚", initial_sidebar_state="collapsed")

st_autorefresh(interval=120000, limit=None, key="refresh_timer")

# 🔥 CSS GLOBAL DA BARRA DE TAREFAS E LIMPEZA DA NUVEM
st.markdown("""
    <style>
    /* Oculta as ferramentas da nuvem do Streamlit */
    [data-testid="stToolbar"] { display: none !important; }
    .stAppDeployButton { display: none !important; }
    .stDeployButton { display: none !important; }
    [class^="viewerBadge"] { display: none !important; }
    [class*="viewerBadge"] { display: none !important; }
    iframe[src*="badge"] { display: none !important; }
    #MainMenu { display: none !important; }
    footer { display: none !important; }
    
    /* Configuração da Tela Inteira com fundo BRANCO PURO */
    .block-container { padding-top: 2rem !important; padding-bottom: 120px !important; max-width: 96% !important; }
    [data-testid="stAppViewContainer"] { background-color: #FFFFFF !important; }
    
    /* ========================================================= */
    /* 🖥️ BARRA DE TAREFAS FIXA NO RODAPÉ (TASKBAR) 🖥️ */
    /* ========================================================= */
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
        gap: 10px;
    }
    div[data-testid="stRadio"] label {
        background-color: transparent !important;
        border: 1px solid transparent !important;
        padding: 8px 20px !important;
        border-radius: 8px !important;
        cursor: pointer !important;
        transition: all 0.2s ease !important;
        margin: 0 !important;
    }
    div[data-testid="stRadio"] label:hover {
        background-color: #1E293B !important;
    }
    div[data-testid="stRadio"] label p {
        color: #94A3B8 !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        margin: 0 !important;
    }
    div[data-testid="stRadio"] label[data-checked="true"] {
        background-color: #38BDF8 !important;
        box-shadow: 0 0 10px rgba(56, 189, 248, 0.4) !important;
    }
    div[data-testid="stRadio"] label[data-checked="true"] p {
        color: #0F172A !important;
        font-weight: 800 !important;
    }
    div[role="radiogroup"] label div[data-testid="stRadio-radio"] { display: none !important; }

    /* Textos e Botões Gerais */
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
    
    [data-testid="stVerticalBlock"] > [style*="flex-direction: column;"] > [data-testid="stVerticalBlock"] { 
        background: #FFFFFF; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.02); border: 1px solid #E2E8F0; 
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("""<style>[data-testid="stSidebar"] { display: none !important; }</style>""", unsafe_allow_html=True)

if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

# =============================================================================
# 🔐 TELA DE LOGIN (ESTILO ERP PROFISSIONAL)
# =============================================================================
if not st.session_state.autenticado:
    st.markdown("""
        <style>
        [data-testid="stForm"] {
            background: #FFFFFF;
            padding: 40px 30px;
            border-radius: 12px;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.08);
            border: 1px solid #E2E8F0;
            max-width: 380px !important;
            margin: 8vh auto !important; 
        }
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
            logins_autorizados = {
                "robson.melo": "123",
                "william.bertoldo": "123"
            }
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
        caminho_windows = r"C:\Users\elcic\IGO_Logistica_Sistema"
        cred_win = os.path.join(caminho_windows, "credentials.json")
        token_win = os.path.join(caminho_windows, "token.json")
        
        if os.path.exists(cred_win):
            gc = gspread.oauth(credentials_filename=cred_win, authorized_user_filename=token_win)
            return gc.open("DB_IGO_Logistica")

        elif "google_token_json" in st.secrets:
            import json
            from google.oauth2.credentials import Credentials
            token_info = json.loads(st.secrets["google_token_json"])
            creds = Credentials.from_authorized_user_info(token_info, scopes)
            gc = gspread.authorize(creds)
            return gc.open("DB_IGO_Logistica")
        else:
            st.error("❌ Credenciais não encontradas (Local ou Secrets).")
            return None
    except Exception as e:
        st.error(f"Erro na conexão: {e}")
        return None

# 🔥 FUNÇÃO DE TITÂNIO: Impede colunas bagunçadas no Google Sheets
def atualizar_planilha_memoria(df_atualizada, worksheet):
    colunas_padrao = ['DATA', 'PEDIDO', 'TOMADOR', 'LABORATORIO', 'ENDERECO', 'NUMERO', 'BAIRRO', 'CIDADE', 'UF', 'CEP', 'STATUS', 'AGENTE_RAW', 'PRAZO_DIAS', 'DATA_LIMITE', 'DATA_ENTREGA', 'FOTO', 'ROMANEIO']
    df_atualizada.columns = [str(c).strip().upper() for c in df_atualizada.columns]
    df_atualizada = df_atualizada.loc[:, ~df_atualizada.columns.duplicated()].copy()
    
    for col in colunas_padrao:
        if col not in df_atualizada.columns:
            df_atualizada[col] = ""
            
    extra_cols = [c for c in df_atualizada.columns if c not in colunas_padrao]
    df_final = df_atualizada[colunas_padrao + extra_cols]
    
    worksheet.clear()
    worksheet.update("A1", [df_final.columns.tolist()] + df_final.fillna("").astype(str).values.tolist())

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
                    
                    col_qr_app = None
                    for c in ['QR_CODE', 'QRCODE', 'QR', 'CODIGO']:
                        if c in df_app.columns:
                            col_qr_app = c
                            break
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
                        if 'QR_CODE' not in df.columns:
                            df['QR_CODE'] = df['APP_QR']
                        else:
                            df['QR_CODE'] = df.apply(lambda r: r['APP_QR'] if str(r.get('APP_QR','')).strip() and str(r.get('APP_QR','')).upper() != 'NAN' else r.get('QR_CODE', ''), axis=1)

                    def get_true_status(row):
                        s_db = str(row.get('STATUS', '')).strip().upper()
                        s_app = str(row.get('APP_STATUS', '')).strip().upper()
                        rom_id = str(row.get('ROMANEIO', '')).strip()
                        
                        if rom_id in rom_dict:
                            s_rom = str(rom_dict[rom_id].get('APP_STATUS', '')).strip().upper()
                            if s_rom in ['ENTREGUE', 'FRUSTRADA', 'PROBLEMA', 'CANCELADO']:
                                return s_rom
                                
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
                            if d_rom and d_rom.upper() != 'NAN':
                                return d_rom

                        if s_final in ['ENTREGUE', 'FRUSTRADA', 'PROBLEMA'] and 'APP_DATA_ENTREGA' in row:
                            d_app = str(row.get('APP_DATA_ENTREGA', '')).strip()
                            if d_app and d_app.upper() != 'NAN':
                                return d_app
                        
                        return d_db if d_db.upper() != 'NAN' else ""
                        
                    if 'DATA_ENTREGA' in df.columns or 'APP_DATA_ENTREGA' in df.columns:
                        df['DATA_ENTREGA'] = df.apply(get_true_data_entrega, axis=1)

                    def get_true_foto(row):
                        f_db = str(row.get('FOTO', '')).strip()
                        f_app = str(row.get('APP_FOTO', '')).strip()
                        rom_id = str(row.get('ROMANEIO', '')).strip()
                        
                        if rom_id in rom_dict:
                            f_rom = str(rom_dict[rom_id].get('APP_FOTO', '')).strip()
                            if f_rom and f_rom.upper() != 'NAN':
                                return f_rom
                                
                        if f_app and f_app.upper() != 'NAN': return f_app
                        return f_db
                        
                    if 'APP_FOTO' in df.columns or len(rom_dict) > 0:
                        df['FOTO'] = df.apply(get_true_foto, axis=1)
                        
            except Exception: pass
            
            if 'DATA' in df.columns: df['DATA_OBJ'] = pd.to_datetime(df['DATA'], format='%d/%m/%Y', errors='coerce').dt.date
            return df
    except Exception: pass
    return pd.DataFrame()

# ======== VARIÁVEIS GLOBAIS ========
planilha_db = conectar_banco()
DF_AGENTES = carregar_dados_agentes(planilha_db)
FERIADOS_BR = holidays.Brazil()
CLIENTES_AUTORIZADOS = ["CUNHA", "CAEP", "SAPIENS", "GRALAB", "SYNVIA", "INNOVATOX", "LABEST", "AIRLAB", "UNILABOR", "SODRE", "BRASILIENSE", "MB_CAEP"]
hoje_br = datetime.now(FUSO_BR).date() 
bg_app = "#FFFFFF"
border_c = "#E2E8F0"

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
    texto_str = str(texto).strip()
    texto_sem_acento = unicodedata.normalize('NFKD', texto_str).encode('ASCII', 'ignore').decode('utf-8')
    return texto_sem_acento.upper()

def tratar_texto_global(texto):
    if pd.isna(texto): return ""
    t = padronizar_texto(texto)
    if t in ['0', '0.0', 'NAN', 'NONE', 'NAT']: return ""
    return t[:-2] if t.endswith('.0') else t

def limpar_nome_local_rota(texto):
    t = tratar_texto_global(texto)
    return t.split('/')[0].split('-')[0].strip()

def obter_login_agente(cidade, bairro, laboratorio, endereco="", base_rotas_df=pd.DataFrame()):
    if base_rotas_df.empty: return ""
    
    rotas_dict = {}
    for _, row in base_rotas_df.iterrows():
        rota_banco = str(row['ROTA MAPEADA']).upper()
        rota_banco = rota_banco.replace(" ➔ ", "---").replace(" -> ", "---")
        rota_limpa = padronizar_texto(rota_banco)
        rotas_dict[rota_limpa] = str(row['LOGIN DO AGENTE']).lower().strip()
    
    cid = limpar_nome_local_rota(cidade)
    bai = limpar_nome_local_rota(bairro)
    lab = tratar_texto_global(laboratorio)
    end = tratar_texto_global(endereco)
    
    chaves = [
        f"{cid}---{bai}---{end}",
        f"{cid}---{bai}---{lab}",
        f"{cid}---{lab}",
        f"{cid}---{bai}",
        cid
    ]
    
    for c in chaves:
        if c in rotas_dict: 
            return rotas_dict[c]
    return ""

def calcular_sla_dias(uf, cidade):
    uf, cidade = str(uf).upper().strip(), tratar_texto_global(str(cidade))
    if uf == 'SP': return 1
    if uf == 'RJ': return 2 if cidade in ['ANGRA DOS REIS', 'CAMPOS DOS GOYTACAZES'] else 1
    if uf in ['GO', 'DF', 'SC', 'RS']: return 2
    return 3 

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
        worksheet = writer.sheets['Relatorio']
        worksheet.hide_gridlines(2)
        max_row, max_col = df.shape
        if max_row > 0:
            col_settings = [{'header': str(col)} for col in df.columns]
            worksheet.add_table(0, 0, max_row, max_col - 1, {'columns': col_settings, 'style': 'Table Style Medium 2'})
            for i, col in enumerate(df.columns):
                tamanho = max(df[col].astype(str).map(len).max(), len(str(col))) + 2
                worksheet.set_column(i, i, min(tamanho, 40))
    return output.getvalue()

def obter_proximo_id(df):
    if df is None or df.empty or 'PEDIDO' not in df.columns: return 100000
    try:
        nums = df['PEDIDO'].astype(str).str.extract(r'^(\d+)')[0].dropna().astype(int)
        return int(nums.max()) + 1 if not nums.empty else 100000
    except:
        return 100000

# CSS Ajustado: Linhas Alternadas Suaves em Tons de Cinza/Azul Claro e Brancas
def obter_css_grid():
    return {
        ".ag-root-wrapper": {"border": "1px solid #E2E8F0 !important", "border-radius": "6px", "overflow": "hidden"},
        ".ag-header": {"background-color": "#F8FAFC !important", "border-bottom": "1px solid #CBD5E1 !important"},
        ".ag-header-cell-text": {"color": "#334155 !important", "font-weight": "700 !important", "font-size": "11px !important"},
        ".ag-header-icon": {"color": "#0284C7 !important"}, 
        ".ag-cell": {"font-size": "11px !important", "color": "#0F172A !important", "border-bottom": "1px solid #F1F5F9 !important", "display": "flex", "align-items": "center"},
        ".ag-row-even": {"background-color": "#FFFFFF !important"},
        ".ag-row-odd": {"background-color": "#F8FAFC !important"}, 
        ".ag-row-hover": {"background-color": "#E2E8F0 !important"}, 
        ".ag-row-selected": {"background-color": "#E0F2FE !important", "color": "#0369A1 !important"},
        ".ag-row-selected .ag-cell": {"color": "#0369A1 !important", "font-weight": "600"}
    }

# 🔥 A PRIORIDADE AGORA É O STATUS REAL
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
            if datetime.strptime(previsao, "%d/%m/%Y").date() < hoje_br: 
                res = f"{res} ⚠️ ATRASADO"
        except: pass
    return res

if 'filtro_kpi_admin' not in st.session_state: st.session_state.filtro_kpi_admin = "TODOS"

# =============================================================================
# 🎨 3. CABEÇALHO LIMPO
# =============================================================================

col_logo, col_title, col_logout = st.columns([1, 4, 1], vertical_alignment="center")

with col_logo:
    st.image("https://i.postimg.cc/x84nnjjq/IGO-LOGO.png", width=140)
    
with col_title:
    st.markdown("<h2 style='color: #0F172A; font-weight: 800; margin: 0; text-align: center;'>PAINEL GERENCIAL</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #64748B; margin: 0; text-align: center; font-weight: 600;'>Centro de Controle Operacional - IGO Logística</p>", unsafe_allow_html=True)

with col_logout:
    if st.button("🚪 Sair", use_container_width=True):
        st.session_state.autenticado = False
        st.cache_data.clear(); st.cache_resource.clear(); st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# =============================================================================
# 🖥️ BARRA DE TAREFAS FIXA NO RODAPÉ (TASKBAR)
# =============================================================================
menu = st.radio("Navegação:", [
    "📊 Dashboard", 
    "📝 Manual", 
    "📥 Lotes", 
    "🔬 Triagem", 
    "📱 Zap", 
    "📁 Relatórios", 
    "⚙️ Rotas"
], horizontal=True, label_visibility="collapsed")


# =============================================================================
# 🚀 MÓDULO 1: DASHBOARD
# =============================================================================
if menu == "📊 Dashboard":
    df_raw = carregar_dados_completos(planilha_db)
    
    if not df_raw.empty:
        # 🔥 ESCUDO ANTI-QUEBRA DE COLUNAS VITAIS PARA O DASHBOARD
        # Se o sistema não encontrar a coluna na planilha, ele cria ela vazia em memória.
        colunas_vitais = ['DATA', 'PEDIDO', 'TOMADOR', 'LABORATORIO', 'BAIRRO', 'CIDADE', 'UF', 'STATUS', 'DATA_LIMITE', 'FOTO', 'AGENTE_RAW', 'ENDERECO', 'NUMERO', 'CEP', 'DATA_ENTREGA']
        for col in colunas_vitais:
            if col not in df_raw.columns:
                df_raw[col] = ""
                
        df_raw['FOTO_URL'] = df_raw['FOTO'].apply(lambda x: f"https://www.appsheet.com/template/gettablefileurl?appName=APPIGOLOGISTICA-153047553&tableName=App_Tarefas&fileName={str(x).strip()}" if str(x).strip() and str(x).upper() not in ['NAN', 'NONE', ''] else "")
        df_raw['STATUS_DISPLAY'] = df_raw.apply(calc_status_display, axis=1)
        
        if 'DATA_LIMITE' in df_raw.columns: df_raw['DATA_LIMITE'] = df_raw['DATA_LIMITE'].fillna("").astype(str)
        if 'DATA_ENTREGA' in df_raw.columns: df_raw['DATA_ENTREGA'] = df_raw['DATA_ENTREGA'].fillna("").astype(str)

        col_f1, col_f2 = st.columns(2)
        f_cli = col_f1.selectbox("🏢 Filtrar por Tomador:", ["Todos"] + CLIENTES_AUTORIZADOS)
        
        data_inicial_padrao = hoje_br - timedelta(days=2)
        f_data = col_f2.date_input("📅 Período de Análise:", value=(data_inicial_padrao, hoje_br), format="DD/MM/YYYY")
        
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
        busca = st.text_input("🔎 Busca Rápida de Rastreio (Código, Lab, Cidade...):", placeholder="Digite para filtrar a tabela abaixo...")

        df_grid = df_f.copy()
        if st.session_state.filtro_kpi_admin == "ENTREGUE": df_grid = df_grid[df_grid['STATUS_DISPLAY'].str.contains('Entregue')]
        elif st.session_state.filtro_kpi_admin == "PENDENTE": df_grid = df_grid[df_grid['STATUS_DISPLAY'].str.contains('Pendente')]
        elif st.session_state.filtro_kpi_admin == "FRUSTRADA": df_grid = df_grid[df_grid['STATUS_DISPLAY'].str.contains('Frustrada')]
        elif st.session_state.filtro_kpi_admin == "ATRASADO": df_grid = df_grid[df_grid['STATUS_DISPLAY'].str.contains('ATRASADO')]
        elif st.session_state.filtro_kpi_admin == "HOJE": df_grid = df_grid[df_grid['DATA_OBJ'] == hoje_br]
        
        colunas_mostrar = ['DATA', 'PEDIDO', 'TOMADOR', 'LABORATORIO', 'BAIRRO', 'CIDADE', 'UF', 'STATUS_DISPLAY', 'DATA_LIMITE', 'FOTO_URL', 'AGENTE_RAW', 'ENDERECO', 'NUMERO', 'CEP', 'DATA_ENTREGA']
        
        # 🔥 ESCUDO FINAL DA GRID: Garante que as colunas existam na hora de filtrar
        for col in colunas_mostrar:
            if col not in df_grid.columns:
                df_grid[col] = ""
                
        df_grid = df_grid[colunas_mostrar]
        
        if busca:
            mask = df_grid.astype(str).apply(lambda x: busca.upper() in x.str.upper().values, axis=1)
            df_grid = df_grid[mask]

        st.markdown(f"<p style='color:#059669; font-weight:600; font-size:12px; margin-bottom: 5px;'>🟢 Sincronizado: {datetime.now(FUSO_BR).strftime('%H:%M:%S')}</p>", unsafe_allow_html=True)
        
        container_botoes = st.container()
        container_grid = st.container()

        with container_grid:
            gb = GridOptionsBuilder.from_dataframe(df_grid)
            gb.configure_default_column(resizable=True, sortable=True, filter=False, suppressMenu=True, minWidth=150, flex=1)
            gb.configure_selection(selection_mode='multiple', use_checkbox=True, header_checkbox=True)
            gb.configure_grid_options(rowHeight=32, headerHeight=35)
            
            gb.configure_column("DATA", headerName="Data")
            gb.configure_column("PEDIDO", headerName="Pedido", maxWidth=90)
            gb.configure_column("TOMADOR", headerName="Tomador", maxWidth=120)
            gb.configure_column("LABORATORIO", headerName="Laboratório")
            gb.configure_column("BAIRRO", headerName="Bairro")
            gb.configure_column("CIDADE", headerName="Cidade")
            gb.configure_column("UF", headerName="UF", maxWidth=60)
            gb.configure_column("DATA_LIMITE", headerName="Previsão Entrega")
            gb.configure_column("AGENTE_RAW", headerName="Agente") 
            gb.configure_column("DATA_ENTREGA", headerName="Data Real Entrega", maxWidth=110)
            
            gb.configure_column("ENDERECO", hide=True)
            gb.configure_column("NUMERO", hide=True)
            gb.configure_column("CEP", hide=True)
            
            st_js = JsCode("""
            function(p){
                let v = p.value || ''; 
                if(v.includes('Entregue')){ return {'backgroundColor':'rgba(16,185,129,0.1)','color':'#059669','fontWeight':'700'}; } 
                if(v.includes('Frustrada') || v.includes('Problema') || v.includes('Cancelado')){ return {'backgroundColor':'rgba(239,68,68,0.1)','color':'#DC2626','fontWeight':'700'}; } 
                if(v.includes('Em Rota')){ return {'backgroundColor':'rgba(245,158,11,0.1)','color':'#D97706','fontWeight':'700'}; } 
                if(v.includes('Coletado') || v.includes('Conferido')){ return {'backgroundColor':'rgba(59,130,246,0.1)','color':'#2563EB','fontWeight':'700'}; } 
                if(v.includes('ATRASADO')){ return {'backgroundColor':'rgba(239,68,68,0.1)','color':'#DC2626','fontWeight':'700'}; } 
                return {'fontWeight':'600', 'color': '#64748B'};
            }
            """)
            gb.configure_column("STATUS_DISPLAY", headerName="Status", cellStyle=st_js, minWidth=170)
            
            img_js = JsCode("""
            class FotoRenderer {
                init(params) {
                    this.eGui = document.createElement('div');
                    this.eGui.style.textAlign = 'center';
                    let val = params.value;
                    if (val && val !== '' && val !== 'nan' && val !== 'None' && val.includes('http')) {
                        this.eGui.innerHTML = '<span style="cursor: pointer; font-size: 16px;" title="Ver Comprovante">📸</span>';
                        this.eGui.onclick = () => {
                            let modal = document.createElement('div');
                            modal.style.position = 'fixed'; modal.style.zIndex = '999999';
                            modal.style.left = '0'; modal.style.top = '0'; modal.style.width = '100vw'; modal.style.height = '100vh';
                            modal.style.backgroundColor = 'rgba(15,23,42,0.9)';
                            modal.style.display = 'flex'; modal.style.flexDirection = 'column'; modal.style.justifyContent = 'center'; modal.style.alignItems = 'center'; modal.style.cursor = 'zoom-out';
                            let img = document.createElement('img');
                            img.src = val; 
                            img.style.maxWidth = '90%'; img.style.maxHeight = '85%'; img.style.borderRadius = '8px'; img.style.boxShadow = '0 25px 50px -12px rgba(0, 0, 0, 0.5)';
                            let txt = document.createElement('div');
                            txt.innerText = '✖ Fechar Visualização'; 
                            txt.style.color = '#ffffff'; txt.style.marginTop = '20px'; txt.style.fontFamily = 'sans-serif'; txt.style.fontWeight = 'bold'; txt.style.padding = '8px 16px'; txt.style.background = 'rgba(255,255,255,0.1)'; txt.style.borderRadius = '20px';
                            modal.appendChild(img); modal.appendChild(txt);
                            modal.onclick = () => { document.body.removeChild(modal); };
                            document.body.appendChild(modal);
                        };
                    }
                }
                getGui() { return this.eGui; }
            }
            """)
            gb.configure_column("FOTO_URL", headerName="Foto", cellRenderer=img_js, width=80, minWidth=80)
            
            grid_response = AgGrid(df_grid, gridOptions=gb.build(), allow_unsafe_jscode=True, theme='alpine', custom_css=obter_css_grid(), height=550, fit_columns_on_grid_load=False, update_mode=GridUpdateMode.MODEL_CHANGED | GridUpdateMode.SELECTION_CHANGED)
            
            selecionados = grid_response['selected_rows']
            tem_sel = False
            if selecionados is not None:
                if isinstance(selecionados, pd.DataFrame): tem_sel = not selecionados.empty
                else: tem_sel = len(selecionados) > 0
                
            if tem_sel:
                if isinstance(selecionados, pd.DataFrame): p_ids = selecionados['PEDIDO'].astype(str).tolist()
                else: p_ids = [str(r['PEDIDO']) for r in selecionados]
            else: p_ids = []

        with container_botoes:
            st.markdown("""
                <style>
                div[data-testid="stPopover"] > button, button[kind="secondary"] {
                    white-space: nowrap !important; overflow: hidden !important; font-weight: 600 !important; font-size: 12px !important; border-radius: 6px !important; height: 32px !important; min-height: 32px !important; padding: 0px 12px !important; border: 1px solid #CBD5E1 !important; background-color: #FFFFFF !important; color: #475569 !important; transition: all 0.2s ease !important; box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
                }
                div[data-testid="stPopover"] > button:hover, button[kind="secondary"]:hover {
                    border-color: #0284C7 !important; color: #0369A1 !important; background-color: #F0F9FF !important; box-shadow: 0 2px 4px rgba(2, 132, 199, 0.1) !important;
                }
                </style>
            """, unsafe_allow_html=True)
            
            col_b2, col_b3, col_b4, col_b5 = st.columns([1.5, 1.5, 1.5, 1.5])
            
            with col_b2.popover("📲 Dar Baixa Manual", use_container_width=True):
                if not tem_sel: st.warning("Selecione na Grid primeiro!")
                else:
                    status_baixa = st.selectbox("Novo Status:", ["ENTREGUE ✅", "PROBLEMA 🚨", "CANCELADO ❌", "PENDENTE ⏳"])
                    data_baixa = st.date_input("Data da Ocorrência:", format="DD/MM/YYYY", value=hoje_br)
                    
                    tem_entregue = df_grid[df_grid['PEDIDO'].isin(p_ids)]['STATUS_DISPLAY'].str.contains('Entregue').any()
                    senha_reversao = ""
                    if tem_entregue:
                        st.warning("⚠️ Você selecionou pedidos já **ENTREGUES**.")
                        senha_reversao = st.text_input("🔑 Senha (Obrigatória para desfazer entrega):", type="password")

                    if st.button("Confirmar Baixa", type="primary", use_container_width=True):
                        status_limpo = status_baixa.split(" ")[0].upper()
                        if tem_entregue and status_limpo != 'ENTREGUE' and senha_reversao != '123':
                            st.error("❌ Senha incorreta ou vazia! Reversão bloqueada.")
                        else:
                            with st.spinner("Atualizando Banco e AppSheet..."):
                                try:
                                    aba = planilha_db.worksheet("Memoria_Sistema")
                                    dados_aba = aba.get_all_values()
                                    df_nuvem = pd.DataFrame(dados_aba[1:], columns=dados_aba[0])
                                    df_nuvem = df_nuvem.loc[:, ~df_nuvem.columns.duplicated()].copy()
                                    for pid in p_ids:
                                        mask = df_nuvem['PEDIDO'] == pid
                                        if 'STATUS' not in df_nuvem.columns: df_nuvem['STATUS'] = ""
                                        if 'DATA_ENTREGA' not in df_nuvem.columns: df_nuvem['DATA_ENTREGA'] = ""
                                        df_nuvem.loc[mask, 'STATUS'] = status_limpo
                                        if status_limpo == "ENTREGUE": df_nuvem.loc[mask, 'DATA_ENTREGA'] = data_baixa.strftime("%d/%m/%Y")
                                        elif status_limpo == "PENDENTE": df_nuvem.loc[mask, 'DATA_ENTREGA'] = ""
                                    atualizar_planilha_memoria(df_nuvem, aba)
                                    try:
                                        aba_app = planilha_db.worksheet("App_Tarefas")
                                        dados_app = aba_app.get_all_values()
                                        if len(dados_app) > 1:
                                            df_app = pd.DataFrame(dados_app[1:], columns=dados_app[0])
                                            df_app = df_app.loc[:, ~df_app.columns.duplicated()].copy()
                                            if 'PEDIDO' in df_app.columns and 'STATUS' in df_app.columns:
                                                mascara_app = df_app['PEDIDO'].isin(p_ids)
                                                df_app.loc[mascara_app, 'STATUS'] = status_limpo
                                                if 'DATA_ENTREGA' not in df_app.columns: df_app['DATA_ENTREGA'] = ""
                                                if status_limpo == "ENTREGUE": df_app.loc[mascara_app, 'DATA_ENTREGA'] = data_baixa.strftime("%d/%m/%Y")
                                                elif status_limpo == "PENDENTE": df_app.loc[mascara_app, 'DATA_ENTREGA'] = ""
                                                aba_app.update("A1", [df_app.columns.tolist()] + df_app.fillna("").astype(str).values.tolist())
                                    except: pass 
                                    st.success("Atualizado!")
                                    carregar_dados_completos.clear()
                                    st.rerun()
                                except Exception as e: st.error(f"Erro: {e}")

            with col_b3.popover("👯 Clonar Pedidos", use_container_width=True):
                if not tem_sel: st.warning("Selecione na Grid primeiro!")
                else:
                    st.markdown(f"**Duplicar {len(p_ids)} pedidos selecionados**")
                    clone_data = st.date_input("Nova Data do Pedido:", format="DD/MM/YYYY", value=hoje_br)
                    logins_disp = sorted(DF_AGENTES['LOGIN DO AGENTE'].unique().tolist()) if not DF_AGENTES.empty else []
                    clone_mot = st.selectbox("Agente (Digite para buscar):", ["Manter Original"] + logins_disp)
                    
                    if st.button("Confirmar Clone", type="primary", use_container_width=True):
                        with st.spinner("Clonando na base segura..."):
                            try:
                                aba = planilha_db.worksheet("Memoria_Sistema")
                                dados_aba = aba.get_all_values()
                                df_nuvem = pd.DataFrame(dados_aba[1:], columns=dados_aba[0])
                                df_nuvem = df_nuvem.loc[:, ~df_nuvem.columns.duplicated()].copy()
                                prox_id = obter_proximo_id(df_nuvem)
                                clones_para_app = []
                                for pid in p_ids:
                                    if pid in df_nuvem['PEDIDO'].values:
                                        l_orig = df_nuvem[df_nuvem['PEDIDO'] == pid].iloc[0].copy()
                                        novo_id = str(prox_id)
                                        prox_id += 1
                                        l_orig['PEDIDO'] = novo_id
                                        l_orig['DATA'] = clone_data.strftime("%d/%m/%Y")
                                        l_orig['STATUS'] = "PENDENTE"
                                        l_orig['DATA_ENTREGA'] = ""; l_orig['FOTO'] = ""; l_orig['ROMANEIO'] = ""
                                        if clone_mot != "Manter Original": l_orig['AGENTE_RAW'] = clone_mot
                                        prazo = calcular_sla_dias(l_orig.get('UF', 'SP'), l_orig.get('CIDADE', ''))
                                        l_orig['PRAZO_DIAS'] = prazo
                                        l_orig['DATA_LIMITE'] = calcular_data_limite(l_orig['DATA'], prazo)
                                        df_nuvem = pd.concat([df_nuvem, pd.DataFrame([l_orig])], ignore_index=True)
                                        if str(l_orig.get('AGENTE_RAW','')).strip():
                                            clones_para_app.append({
                                                'PEDIDO': novo_id, 'MOTORISTA': l_orig['AGENTE_RAW'], 'ENDERECO': l_orig.get('ENDERECO',''), 'NUMERO': l_orig.get('NUMERO',''),
                                                'BAIRRO': l_orig.get('BAIRRO',''), 'CIDADE': l_orig.get('CIDADE',''), 'CEP': l_orig.get('CEP',''), 'LABORATORIO': l_orig.get('LABORATORIO',''), 'TOMADOR': l_orig.get('TOMADOR','')
                                            })
                                atualizar_planilha_memoria(df_nuvem, aba)
                                if clones_para_app: despachar_para_appsheet(clones_para_app)
                                st.success("Clonado com SUCESSO!")
                                carregar_dados_completos.clear()
                                st.rerun()
                            except Exception as e: st.error(f"Erro ao clonar: {e}")

            with col_b4.popover("🔄 Trocar Motorista", use_container_width=True):
                if not tem_sel: st.warning("Selecione na Grid primeiro!")
                else:
                    tem_entregue = df_grid[df_grid['PEDIDO'].isin(p_ids)]['STATUS_DISPLAY'].str.contains('Entregue').any()
                    if tem_entregue: st.error("⚠️ Não é possível trocar motorista de pedidos já ENTREGUES.")
                    else:
                        logins_disp = sorted(DF_AGENTES['LOGIN DO AGENTE'].unique().tolist()) if not DF_AGENTES.empty else []
                        novo_mot = st.selectbox("Novo Agente (Digite para buscar):", logins_disp)
                        
                        if st.button("Confirmar Troca", type="primary", use_container_width=True):
                            with st.spinner("Trocando motorista..."):
                                try:
                                    aba = planilha_db.worksheet("Memoria_Sistema")
                                    dados_aba = aba.get_all_values()
                                    df_nuvem = pd.DataFrame(dados_aba[1:], columns=dados_aba[0])
                                    df_nuvem = df_nuvem.loc[:, ~df_nuvem.columns.duplicated()].copy()
                                    lista_app_troca = []
                                    for pid in p_ids:
                                        mask = df_nuvem['PEDIDO'] == pid
                                        if mask.any():
                                            df_nuvem.loc[mask, 'AGENTE_RAW'] = novo_mot
                                            df_nuvem.loc[mask, 'STATUS'] = "PENDENTE"
                                            l_app = df_nuvem[mask].iloc[0]
                                            lista_app_troca.append({'PEDIDO': pid, 'MOTORISTA': novo_mot, 'ENDERECO': l_app.get('ENDERECO',''), 'NUMERO': l_app.get('NUMERO',''), 'BAIRRO': l_app.get('BAIRRO',''), 'CIDADE': l_app.get('CIDADE',''), 'CEP': l_app.get('CEP',''), 'LABORATORIO': l_app.get('LABORATORIO',''), 'TOMADOR': l_app.get('TOMADOR','')})
                                    atualizar_planilha_memoria(df_nuvem, aba)
                                    despachar_para_appsheet(lista_app_troca)
                                    st.success("Trocado!")
                                    carregar_dados_completos.clear()
                                    st.rerun()
                                except Exception as e: st.error(f"Erro: {e}")

            if col_b5.button("🔄 Atualizar Painel", use_container_width=True):
                carregar_dados_completos.clear()
                st.rerun()

# =============================================================================
# 📝 MÓDULO EXTRA: NOVO PEDIDO MANUAL (COM VIA CEP INTEGRADO)
# =============================================================================
elif menu == "📝 Manual":
    st.markdown("<div class='dinamic-border'><h3 class='dinamic-text' style='margin:0;'>📝 Inserir Novo Pedido Manual</h3></div>", unsafe_allow_html=True)
    st.markdown("Use esta tela para registrar amostras fora do padrão. **Os textos inseridos perderão os acentos e ficarão maiúsculos automaticamente para proteger a cadeia de dados.**")
    
    if 'm_rua' not in st.session_state: st.session_state['m_rua'] = ""
    if 'm_bai' not in st.session_state: st.session_state['m_bai'] = ""
    if 'm_cid' not in st.session_state: st.session_state['m_cid'] = ""
    if 'm_uf' not in st.session_state: st.session_state['m_uf'] = ""

    with st.container(border=True):
        st.markdown("#### 📍 Busca Inteligente de Endereço")
        cc1, cc2, cc3 = st.columns([2, 1, 3], vertical_alignment="bottom")
        cep_input = cc1.text_input("Digite o CEP (Apenas números)", max_chars=9)
        
        if cc2.button("🔍 Buscar CEP", use_container_width=True):
            cep_limpo = re.sub(r'\D', '', cep_input)
            if len(cep_limpo) == 8:
                try:
                    resp = requests.get(f"https://viacep.com.br/ws/{cep_limpo}/json/").json()
                    if "erro" not in resp:
                        st.session_state['m_rua'] = padronizar_texto(resp.get("logradouro", ""))
                        st.session_state['m_bai'] = padronizar_texto(resp.get("bairro", ""))
                        st.session_state['m_cid'] = padronizar_texto(resp.get("localidade", ""))
                        st.session_state['m_uf'] = padronizar_texto(resp.get("uf", ""))
                        st.rerun()
                    else:
                        st.error("❌ CEP não encontrado na base dos Correios.")
                except Exception as e:
                    st.error(f"Erro na API de CEP: {e}")
            else:
                st.warning("⚠️ Digite um CEP válido com 8 dígitos.")
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        m_tomador = col1.selectbox("Laboratório Solicitante (Tomador) *", ["Selecione..."] + CLIENTES_AUTORIZADOS)
        m_data = col2.date_input("Data do Pedido *", format="DD/MM/YYYY", value=hoje_br)
        
        m_lab = st.text_input("Ponto de Coleta (Clínica/Posto) *")
        m_rua = st.text_input("Logradouro *", value=st.session_state['m_rua'])
        
        col3, col4, col5 = st.columns([2, 2, 1])
        m_bai = col3.text_input("Bairro *", value=st.session_state['m_bai'])
        m_cid = col4.text_input("Cidade *", value=st.session_state['m_cid'])
        m_uf = col5.text_input("UF *", value=st.session_state['m_uf'])
        
        logins_disp = sorted(DF_AGENTES['LOGIN DO AGENTE'].unique().tolist()) if not DF_AGENTES.empty else []
        m_agente_escolha = st.selectbox("Agente Designado (Busque ou deixe Automático):", ["Automático (Por Rota)"] + logins_disp)
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚀 Injetar na Base e Roteirizar", type="primary", use_container_width=True):
            if m_tomador == "Selecione..." or not m_cid or not m_lab or not m_rua or not m_bai: 
                st.error("⚠️ Preencha todos os campos obrigatórios (marcados com *)!")
            else:
                with st.spinner("Padronizando textos e salvando na nuvem..."):
                    lab_limpo = padronizar_texto(m_lab)
                    rua_limpa = padronizar_texto(m_rua)
                    bai_limpo = padronizar_texto(m_bai)
                    cid_limpa = padronizar_texto(m_cid)
                    uf_limpa = padronizar_texto(m_uf)
                    
                    m_agente = obter_login_agente(cid_limpa, bai_limpo, lab_limpo, rua_limpa, DF_AGENTES) if m_agente_escolha == "Automático (Por Rota)" else m_agente_escolha
                    m_prazo = calcular_sla_dias(uf_limpa, cid_limpa)
                    m_limite = calcular_data_limite(m_data.strftime("%d/%m/%Y"), m_prazo)
                    
                    try:
                        aba_memoria = planilha_db.worksheet("Memoria_Sistema")
                        dados_atuais = aba_memoria.get_all_values()
                        df_nuvem = pd.DataFrame(dados_atuais[1:], columns=dados_atuais[0]) if len(dados_atuais) > 1 else pd.DataFrame()
                        df_nuvem = df_nuvem.loc[:, ~df_nuvem.columns.duplicated()].copy()
                        
                        m_pedido = str(obter_proximo_id(df_nuvem))
                        
                        novo_ped = pd.DataFrame([{
                            'DATA': m_data.strftime("%d/%m/%Y"), 'PEDIDO': m_pedido, 'TOMADOR': m_tomador, 
                            'LABORATORIO': lab_limpo, 'ENDERECO': rua_limpa, 'NUMERO': "", 'BAIRRO': bai_limpo, 
                            'CIDADE': cid_limpa, 'UF': uf_limpa, 'CEP': cep_input, 'STATUS': 'PENDENTE', 
                            'AGENTE_RAW': m_agente, 'PRAZO_DIAS': m_prazo, 'DATA_LIMITE': m_limite, 
                            'DATA_ENTREGA': "", 'FOTO': "", 'ROMANEIO': ""
                        }])
                        
                        df_atual = pd.concat([df_nuvem, novo_ped], ignore_index=True) if not df_nuvem.empty else novo_ped
                        atualizar_planilha_memoria(df_atual, aba_memoria)
                        
                        if m_agente: despachar_para_appsheet([novo_ped.iloc[0].to_dict()])
                        
                        st.success(f"🎉 Pedido {m_pedido} criado e padronizado com sucesso! Acesse o Dashboard para visualizar.")
                        
                        st.session_state['m_rua'] = ""
                        st.session_state['m_bai'] = ""
                        st.session_state['m_cid'] = ""
                        st.session_state['m_uf'] = ""
                        carregar_dados_completos.clear()
                    except Exception as e: st.error(f"Erro ao salvar: {e}")

# =============================================================================
# ➕ MÓDULO 2: IMPORTAÇÃO DE LOTES
# =============================================================================
elif menu == "📥 Lotes":
    st.markdown("<div class='dinamic-border'><h3 class='dinamic-text' style='margin:0;'>➕ Central de Importação de Lotes</h3></div>", unsafe_allow_html=True)
    st.success("🛡️ **AUDITORIA DE DADOS ATIVA:** O sistema avalia padronizações de vários clientes (Airlab, FFW, etc) e adiciona os pacotes à base sem destruir seu histórico do dia.")
    
    if "df_preview" not in st.session_state: st.session_state.df_preview = pd.DataFrame()
    if "import_success" in st.session_state and st.session_state.import_success:
        st.success(st.session_state.import_success)

    with st.container(border=True):
        st.markdown("#### 1. Mapeamento de Planilha e Colagem")
        c1, c2, c3 = st.columns([1, 1, 2])
        with c1: tom = st.selectbox("🏢 Tomador Central:", ["Selecione..."] + CLIENTES_AUTORIZADOS)
        with c2: dt_c = st.date_input("📅 Data da Rota:", format="DD/MM/YYYY", value=hoje_br)

        txt = st.text_area("📋 Cole os dados da planilha do cliente (Ctrl+V):", height=150, help="Apenas copie as células do Excel e cole direto aqui. O Cérebro IA formata sozinho.")

        col_btn1, _ = st.columns([1, 2])
        if col_btn1.button("🔍 1. Processar Matriz e Roteirizar", type="primary", use_container_width=True):
            if not txt or tom == "Selecione...": st.warning("Preencha o Tomador e cole os dados!")
            else:
                if "import_success" in st.session_state:
                    st.session_state.import_success = ""
                try:
                    delim = '\t' if '\t' in txt else (';' if ';' in txt else ',')
                    df_raw_import = pd.read_csv(io.StringIO(txt), sep=delim, header=None, dtype=str).fillna("")
                    
                    idx_h = 0
                    max_matches = 0
                    for i in range(min(15, len(df_raw_import))):
                        row_str = " ".join(df_raw_import.iloc[i].astype(str).values).upper()
                        row_str = unicodedata.normalize('NFKD', row_str).encode('ASCII', 'ignore').decode('utf-8')
                        matches = sum(1 for kw in ['PEDIDO', 'CODIGO', 'ID', 'CIDADE', 'MUNIC', 'LABORAT', 'POSTO', 'NOME', 'CLIENTE', 'ENDERE', 'RUA', 'BAIRRO', 'CEP'] if kw in row_str)
                        if matches > max_matches:
                            max_matches = matches
                            idx_h = i
                    
                    df_limpo = df_raw_import.iloc[idx_h+1:].copy()
                    df_limpo.columns = [str(c).strip() for c in df_raw_import.iloc[idx_h].values]
                    df_limpo = df_limpo.loc[:, ~df_limpo.columns.duplicated()] 
                    
                    for col in df_limpo.columns: 
                        df_limpo[col] = df_limpo[col].apply(tratar_texto_global)
                    
                    mapa = {}
                    for c in df_limpo.columns:
                        cl = str(c).upper().strip()
                        cl = unicodedata.normalize('NFKD', cl).encode('ASCII', 'ignore').decode('utf-8')
                        cl = ''.join(e for e in cl if e.isalnum()) 
                        
                        if not cl: continue
                        
                        if any(x in cl for x in ['PEDIDO', 'SOLICITA', 'CODIGO', 'CDIGO']) or cl == 'ID': 
                            if 'PEDIDO' not in mapa.values(): mapa[c] = 'PEDIDO'
                        elif any(x in cl for x in ['LABORAT', 'CLINIC', 'POSTO', 'NOME', 'CLIENTE']): 
                            if 'LABORATORIO' not in mapa.values(): mapa[c] = 'LABORATORIO'
                        elif any(x in cl for x in ['ENDERE', 'RUA', 'LOGRADOURO', 'AVENIDA']): 
                            if 'ENDERECO' not in mapa.values(): mapa[c] = 'ENDERECO'
                        elif any(x in cl for x in ['NUM', 'NRO']) or cl in ['N', 'NO']: 
                            if 'NUMERO' not in mapa.values(): mapa[c] = 'NUMERO'
                        elif 'BAIRRO' in cl: 
                            if 'BAIRRO' not in mapa.values(): mapa[c] = 'BAIRRO'
                        elif any(x in cl for x in ['CIDADE', 'MUNIC']): 
                            if 'CIDADE' not in mapa.values(): mapa[c] = 'CIDADE'
                        elif any(x in cl for x in ['ESTADO', 'UF']): 
                            if 'UF' not in mapa.values(): mapa[c] = 'UF'
                        elif 'CEP' in cl: 
                            if 'CEP' not in mapa.values(): mapa[c] = 'CEP'
                    
                    df_limpo.rename(columns=mapa, inplace=True)
                    
                    for c in ['PEDIDO', 'LABORATORIO', 'CEP', 'ENDERECO', 'NUMERO', 'BAIRRO', 'CIDADE', 'UF']:
                        if c not in df_limpo.columns: df_limpo[c] = ""
                    
                    for idx, row in df_limpo.iterrows():
                        e, n, b = str(row['ENDERECO']), str(row['NUMERO']), str(row['BAIRRO'])
                        if e and (not n or not b):
                            cep_m = re.search(r'(\d{5}-?\d{3})', e)
                            if cep_m: 
                                df_limpo.at[idx, 'CEP'] = cep_m.group(1)
                                e = e.replace(cep_m.group(1), '').strip(' ,-')
                            if ',' in e and not n: 
                                pts = e.split(',')
                                df_limpo.at[idx, 'ENDERECO'] = pts[0].strip()
                                df_limpo.at[idx, 'NUMERO'] = pts[1].strip()

                    df_limpo['UF'] = df_limpo['UF'].astype(str).str.upper().str.strip()
                    df_limpo['CIDADE'] = df_limpo['CIDADE'].astype(str).str.upper().str.strip()
                    df_limpo['TOMADOR'] = tom
                    df_limpo['DATA'] = dt_c.strftime("%d/%m/%Y")
                    df_limpo['AGENTE_RAW'] = df_limpo.apply(lambda r: obter_login_agente(r['CIDADE'], r['BAIRRO'], r['LABORATORIO'], r['ENDERECO'], DF_AGENTES), axis=1)
                    
                    df_limpo = df_limpo[df_limpo['LABORATORIO'].str.strip() != ""]
                    
                    st.session_state.df_preview = df_limpo[['DATA', 'TOMADOR', 'PEDIDO', 'LABORATORIO', 'ENDERECO', 'NUMERO', 'BAIRRO', 'CIDADE', 'UF', 'CEP', 'AGENTE_RAW']]
                    st.rerun()
                except Exception as e: st.error(f"Erro no processamento: {e}")

    if not st.session_state.df_preview.empty:
        st.markdown("---")
        
        col_tit, col_canc = st.columns([4, 1], vertical_alignment="center")
        col_tit.markdown("### 👀 2. Preview de Carga (Porta de Segurança)")
        if col_canc.button("❌ Cancelar / Limpar Matriz", type="secondary", use_container_width=True):
            st.session_state.df_preview = pd.DataFrame()
            if 'import_success' in st.session_state: st.session_state.import_success = ""
            st.rerun()

        df_preview = st.session_state.df_preview
        mask_err = (df_preview['AGENTE_RAW'].astype(str).str.strip() == "") | (df_preview['AGENTE_RAW'].astype(str).str.upper() == "NAN")
        df_err = df_preview[mask_err]
        df_ok = df_preview[~mask_err]

        if not df_err.empty:
            st.error(f"🚨 **Atenção:** Encontramos {len(df_err)} pedido(s) sem motorista designado. Corrija-os na gaveta abaixo para liberar o botão de Injetar Base.")
            
            if not df_ok.empty:
                with st.expander(f"✅ Gaveta Verde: {len(df_ok)} Pedido(s) Auditados e Prontos", expanded=False):
                    st.dataframe(df_ok, hide_index=True, use_container_width=True)
            
            st.markdown("### 🛠️ Gaveta Vermelha: Auditoria Pendente")
            st.info("💡 A inteligência artificial não encontrou roteiro de Cidade/Bairro. Digite para buscar o motorista de emergência.")
            with st.form("form_correcao_agentes"):
                correcoes = {}
                logins_disp = sorted(DF_AGENTES['LOGIN DO AGENTE'].unique().tolist()) if not DF_AGENTES.empty else []
                
                for idx, row in df_err.iterrows():
                    st.markdown(f"**Cód:** {row['PEDIDO']} | **Local:** {row['LABORATORIO']} | **Logradouro:** {row['ENDERECO']} - {row['BAIRRO']}, {row['CIDADE']}")
                    correcoes[idx] = st.selectbox(f"Responsável pelo ID {row['PEDIDO']}:", ["Selecione..."] + logins_disp, key=f"fix_mot_{idx}")
                    st.divider()
                
                if st.form_submit_button("💾 Validar Correções de Rota", type="primary"):
                    todas_corrigidas = True
                    for idx, novo_mot in correcoes.items():
                        if novo_mot != "Selecione...":
                            st.session_state.df_preview.at[idx, 'AGENTE_RAW'] = novo_mot
                        else:
                            todas_corrigidas = False
                    
                    if not todas_corrigidas:
                        st.warning("⚠️ O lote está bloqueado. Preencha todos os motoristas de emergência para liberar o botão verde.")
                    st.rerun()

        else:
            st.success(f"✅ Protocolo validado! {len(df_ok)} pedidos blindados e roteirizados para injeção.")
            
            # 🔥 ESCUDO ANTI-QUEBRA DE COLUNAS VITAIS NO PREVIEW DE LOTES
            colunas_prev = ['DATA', 'TOMADOR', 'PEDIDO', 'LABORATORIO', 'ENDERECO', 'NUMERO', 'BAIRRO', 'CIDADE', 'UF', 'CEP', 'AGENTE_RAW']
            for col in colunas_prev:
                if col not in df_ok.columns:
                    df_ok[col] = ""
            df_ok = df_ok[colunas_prev]
            
            gb_prev = GridOptionsBuilder.from_dataframe(df_ok)
            gb_prev.configure_default_column(resizable=True, sortable=True, filter=False, suppressMenu=True, minWidth=150, flex=1)
            gb_prev.configure_grid_options(rowHeight=32, headerHeight=35)
            AgGrid(df_ok, gridOptions=gb_prev.build(), allow_unsafe_jscode=True, theme='alpine', custom_css=obter_css_grid(), height=400, fit_columns_on_grid_load=False)
            
            st.markdown("<br>", unsafe_allow_html=True)
            col_btn2, _ = st.columns([1, 2])
            
            if col_btn2.button("🚀 3. INJETAR LOTE NO DB E APLICATIVOS", type="primary", use_container_width=True):
                with st.spinner("Processando injeção em nuvem..."):
                    df_final = df_ok.copy()
                    
                    try:
                        aba = planilha_db.worksheet("Memoria_Sistema")
                        atuais = aba.get_all_values()
                        df_up = pd.DataFrame(atuais[1:], columns=atuais[0]) if len(atuais) > 1 else pd.DataFrame()
                        df_up = df_up.loc[:, ~df_up.columns.duplicated()].copy()
                        
                        prox_id = obter_proximo_id(df_up)
                        
                        for idx, row in df_final.iterrows():
                            if not str(row['PEDIDO']).strip() or str(row['PEDIDO']).upper() == 'NAN': 
                                df_final.at[idx, 'PEDIDO'] = str(prox_id)
                                prox_id += 1
                        
                        df_final['PRAZO_DIAS'] = df_final.apply(lambda r: calcular_sla_dias(r['UF'], r['CIDADE']), axis=1)
                        df_final['DATA_LIMITE'] = df_final.apply(lambda r: calcular_data_limite(r['DATA'], int(r['PRAZO_DIAS'])), axis=1)
                        df_final['STATUS'], df_final['DATA_ENTREGA'], df_final['FOTO'], df_final['ROMANEIO'] = 'PENDENTE', '', '', ''
                        
                        df_up = pd.concat([df_up, df_final], ignore_index=True) if not df_up.empty else df_final
                        atualizar_planilha_memoria(df_up, aba)
                        
                        lista_app = []
                        for _, r in df_final.iterrows():
                            if str(r.get('AGENTE_RAW','')).strip():
                                lista_app.append({
                                    'PEDIDO': r['PEDIDO'], 'MOTORISTA': r['AGENTE_RAW'], 'ENDERECO': r['ENDERECO'],
                                    'NUMERO': r['NUMERO'], 'BAIRRO': r['BAIRRO'], 'CIDADE': r['CIDADE'],
                                    'CEP': r['CEP'], 'LABORATORIO': r['LABORATORIO'], 'TOMADOR': r['TOMADOR']
                                })
                        if lista_app: despachar_para_appsheet(lista_app)
                        
                        st.session_state.import_success = f"🎉 INTEGRAÇÃO CONCLUÍDA! Lote de {len(df_final)} pedidos auditados injetado no sistema com sucesso."
                        st.session_state.df_preview = pd.DataFrame()
                        carregar_dados_completos.clear()
                        st.rerun()
                    except Exception as e: st.error(f"Falha de Injeção Crítica: {e}")

# =============================================================================
# 📋 MÓDULO 3: TRIAGEM E ROMANEIO 
# =============================================================================
elif menu == "🔬 Triagem":
    st.markdown("<div class='dinamic-border'><h3 class='dinamic-text' style='margin:0;'>🔬 Terminal de Triagem e Expedição</h3></div>", unsafe_allow_html=True)
    df_raw = carregar_dados_completos(planilha_db)
    
    if not df_raw.empty:
        t1, t2, t3 = st.tabs(["📦 1. Bipar Lacre / QR Code", "🚚 2. Gerar Documento de Romaneio", "🕒 3. Histórico de Varredura"])
        
        with t1:
            st.info("💡 A auditoria de triagem aceita apenas materiais **COLETADOS** pelo aplicativo.")
            with st.form("form_bip", clear_on_submit=True):
                col_bip, col_btn = st.columns([4, 1])
                bip_input = col_bip.text_input("🔍 Bipar QR Code de Validação:")
                bip_submit = col_btn.form_submit_button("Auditar", use_container_width=True)
                
                if bip_submit and bip_input:
                    termo = re.sub(r'[^A-Z0-9]', '', bip_input.upper())
                    
                    if not termo:
                        st.error("❌ QR Code inválido ou em branco.")
                    else:
                        df_raw['PED_LIMPO'] = df_raw['PEDIDO'].astype(str).str.upper().apply(lambda x: re.sub(r'[^A-Z0-9]', '', x))
                        
                        if 'QR_CODE' in df_raw.columns:
                            df_raw['QR_LIMPO'] = df_raw['QR_CODE'].astype(str).str.upper().apply(lambda x: re.sub(r'[^A-Z0-9]', '', x))
                            mask = (df_raw['PED_LIMPO'] == termo) | (df_raw['QR_LIMPO'] == termo)
                        else:
                            mask = (df_raw['PED_LIMPO'] == termo)
                        
                        if mask.any():
                            idx = df_raw[mask].index[-1]
                            status_atual = str(df_raw.at[idx, 'STATUS']).strip().upper()
                            if status_atual == 'COLETADO':
                                try:
                                    aba = planilha_db.worksheet("Memoria_Sistema")
                                    dados_aba = aba.get_all_values()
                                    df_nuvem = pd.DataFrame(dados_aba[1:], columns=dados_aba[0])
                                    df_nuvem = df_nuvem.loc[:, ~df_nuvem.columns.duplicated()].copy()
                                    
                                    pedido_alvo = str(df_raw.at[idx, 'PEDIDO'])
                                    mask_nuvem = df_nuvem['PEDIDO'] == pedido_alvo
                                    
                                    if mask_nuvem.any():
                                        df_nuvem.loc[mask_nuvem, 'STATUS'] = 'CONFERIDO'
                                        atualizar_planilha_memoria(df_nuvem, aba)
                                        st.success(f"✅ Pedido {pedido_alvo} VALIDADO COM SUCESSO e liberado para expedição!")
                                        carregar_dados_completos.clear()
                                    else:
                                        st.error("❌ Falha de sincronia: Pedido não localizado na nuvem.")
                                        
                                except Exception as e: st.error(f"Falha ao registrar auditoria: {e}")
                            elif status_atual == 'PENDENTE': st.error(f"❌ VIOLAÇÃO DE CADEIA: O código {df_raw.at[idx, 'PEDIDO']} consta como PENDENTE de coleta no aplicativo do agente.")
                            elif status_atual == 'CONFERIDO': st.warning(f"⚠️ O volume {df_raw.at[idx, 'PEDIDO']} já estava conferido na base.")
                            else: st.error(f"❌ O volume {df_raw.at[idx, 'PEDIDO']} consta com status impeditivo: {status_atual}.")
                        else: st.error(f"❌ Assinatura não reconhecida na base de dados: {bip_input}")
            
            st.markdown("---")
            st.markdown("#### Terminal de Validação em Lote (Recurso Manual)")
            df_fila = df_raw[df_raw['STATUS'].astype(str).str.upper() == 'COLETADO'].copy()
            if not df_fila.empty:
                colunas_fila = ['DATA', 'PEDIDO', 'TOMADOR', 'LABORATORIO', 'CIDADE', 'STATUS']
                # 🔥 ESCUDO ANTI-QUEBRA DE COLUNAS VITAIS NA TRIAGEM
                for col in colunas_fila:
                    if col not in df_fila.columns:
                        df_fila[col] = ""
                df_fila = df_fila[colunas_fila]
                
                gb_fila = GridOptionsBuilder.from_dataframe(df_fila)
                gb_fila.configure_default_column(resizable=True, sortable=True, filter=False, suppressMenu=True, minWidth=150, flex=1)
                gb_fila.configure_grid_options(rowHeight=32, headerHeight=35)
                gb_fila.configure_selection('multiple', use_checkbox=True, header_checkbox=True)
                
                grid_fila_resp = AgGrid(df_fila, gridOptions=gb_fila.build(), theme='alpine', custom_css=obter_css_grid(), height=350, key='grid_fila_manual', fit_columns_on_grid_load=False, update_mode=GridUpdateMode.MODEL_CHANGED | GridUpdateMode.SELECTION_CHANGED)
                
                selecionados_manuais = grid_fila_resp['selected_rows']
                tem_selecao = False
                if selecionados_manuais is not None:
                    if isinstance(selecionados_manuais, pd.DataFrame): tem_selecao = not selecionados_manuais.empty
                    else: tem_selecao = len(selecionados_manuais) > 0

                if st.button("✅ Enviar Selecionados para Despacho", type="primary"):
                    if not tem_selecao: st.warning("⚠️ Selecione os pedidos na tabela acima primeiro!")
                    else:
                        with st.spinner("Atualizando pedidos selecionados em lote (Anti-Bloqueio)..."):
                            if isinstance(selecionados_manuais, pd.DataFrame): p_ids = selecionados_manuais['PEDIDO'].astype(str).tolist()
                            else: p_ids = [str(r['PEDIDO']) for r in selecionados_manuais]
                            try:
                                aba = planilha_db.worksheet("Memoria_Sistema")
                                dados_aba = aba.get_all_values()
                                df_nuvem = pd.DataFrame(dados_aba[1:], columns=dados_aba[0])
                                df_nuvem = df_nuvem.loc[:, ~df_nuvem.columns.duplicated()].copy()
                                mascara_pedidos = df_nuvem['PEDIDO'].isin(p_ids)
                                df_nuvem.loc[mascara_pedidos, 'STATUS'] = 'CONFERIDO'
                                atualizar_planilha_memoria(df_nuvem, aba)
                                st.success(f"🎉 {len(p_ids)} pedidos enviados para o Despacho!")
                                carregar_dados_completos.clear()
                                st.rerun()
                            except Exception as e: st.error(f"Erro: {e}")
            else: st.info("O salão está vazio. Apenas materiais marcados como 'Coletados' chegam à triagem.")

        with t2:
            st.markdown("#### Matriz de Expedição (Romaneio)")
            df_conf = df_raw[df_raw['STATUS'].astype(str).str.upper() == 'CONFERIDO'].copy()
            if not df_conf.empty:
                
                lista_tomadores_conf = sorted(df_conf['TOMADOR'].astype(str).unique().tolist())
                c_filtro, _ = st.columns([1, 2])
                tomador_filtro = c_filtro.selectbox("🏢 Blindagem de Carga (Filtro por Tomador):", ["Todos"] + [t for t in lista_tomadores_conf if t.strip()])
                
                if tomador_filtro != "Todos":
                    df_conf = df_conf[df_conf['TOMADOR'] == tomador_filtro]
                
                colunas_romaneio = ['DATA', 'PEDIDO', 'TOMADOR', 'LABORATORIO', 'CIDADE', 'UF']
                if 'QR_CODE' in df_conf.columns: colunas_romaneio.append('QR_CODE')
                
                # 🔥 ESCUDO ANTI-QUEBRA DE COLUNAS VITAIS NO ROMANEIO
                for col in colunas_romaneio:
                    if col not in df_conf.columns:
                        df_conf[col] = ""
                df_conf = df_conf[colunas_romaneio]
                
                gb = GridOptionsBuilder.from_dataframe(df_conf)
                gb.configure_default_column(resizable=True, sortable=True, filter=False, suppressMenu=True, minWidth=150, flex=1)
                gb.configure_grid_options(rowHeight=32, headerHeight=35)
                gb.configure_selection('multiple', use_checkbox=True, header_checkbox=True)
                
                grid_resp = AgGrid(df_conf, gridOptions=gb.build(), theme='alpine', custom_css=obter_css_grid(), height=300, fit_columns_on_grid_load=False, update_mode=GridUpdateMode.MODEL_CHANGED | GridUpdateMode.SELECTION_CHANGED)
                
                selecionados = grid_resp['selected_rows']
                tem_sel_pdf = False
                if selecionados is not None:
                    if isinstance(selecionados, pd.DataFrame): tem_sel_pdf = not selecionados.empty
                    else: tem_sel_pdf = len(selecionados) > 0
                
                st.markdown("---")
                c_mot, c_data, c_btn = st.columns([2, 1, 2])
                logins_disp = sorted(DF_AGENTES['LOGIN DO AGENTE'].unique().tolist()) if not DF_AGENTES.empty else []
                motorista_escolhido = c_mot.selectbox("👤 Responsável pelo Transporte:", ["Selecione..."] + logins_disp)
                data_despacho = c_data.date_input("📅 Data de Embarque:", format="DD/MM/YYYY", value=hoje_br)
                
                if c_btn.button("🚚 Gerar Doc. Oficial e Despachar", type="primary", use_container_width=True):
                    if not tem_sel_pdf or motorista_escolhido == "Selecione...": st.warning("⚠️ Exigência de Rota: Marque os pacotes e informe o responsável.")
                    else:
                        with st.spinner("Gerando Romaneio PDF (Selo IGO) e injetando no roteiro do motorista..."):
                            if isinstance(selecionados, pd.DataFrame): sel_lista = selecionados.to_dict('records')
                            else: sel_lista = selecionados
                            id_romaneio = f"ROM-{datetime.now().strftime('%d%m')}-{random.randint(100,999)}"
                            pedidos_ids = [str(r['PEDIDO']) for r in sel_lista]
                            
                            try:
                                aba = planilha_db.worksheet("Memoria_Sistema")
                                dados_aba = aba.get_all_values()
                                df_nuvem = pd.DataFrame(dados_aba[1:], columns=dados_aba[0])
                                df_nuvem = df_nuvem.loc[:, ~df_nuvem.columns.duplicated()].copy()
                                mascara_pedidos = df_nuvem['PEDIDO'].isin(pedidos_ids)
                                
                                df_nuvem.loc[mascara_pedidos, 'STATUS'] = 'EM ROTA DE ENTREGA'
                                df_nuvem.loc[mascara_pedidos, 'ROMANEIO'] = id_romaneio
                                df_nuvem.loc[mascara_pedidos, 'DATA'] = data_despacho.strftime("%d/%m/%Y")
                                
                                if 'AGENTE_RAW' in df_nuvem.columns:
                                    df_nuvem.loc[mascara_pedidos, 'AGENTE_RAW'] = motorista_escolhido
                                
                                atualizar_planilha_memoria(df_nuvem, aba)
                                
                                base_tomador = sel_lista[0].get('TOMADOR', 'CLIENTE')
                                base_cidade = sel_lista[0].get('CIDADE', '')
                                lote_app = [{
                                    'PEDIDO': id_romaneio, 'MOTORISTA': motorista_escolhido,
                                    'ENDERECO': "ENTREGA DE LOTE NO TOMADOR", 'NUMERO': f"{len(sel_lista)} VOLUMES",
                                    'BAIRRO': base_tomador, 'CIDADE': base_cidade, 'CEP': "---",
                                    'LABORATORIO': f"CONJUNTO DE {len(sel_lista)} PEDIDOS", 'TOMADOR': base_tomador, 'ROMANEIO': id_romaneio
                                }]
                                despachar_para_appsheet(lote_app)
                                carregar_dados_completos.clear()
                                
                                pdf = FPDF()
                                pdf.add_page()
                                pdf.set_draw_color(15, 23, 42)  
                                pdf.set_line_width(0.3)
                                pdf.rect(5, 5, 200, 287)
                                
                                try:
                                    logo_path = os.path.join(tempfile.gettempdir(), "igo_logo_temp.png")
                                    if not os.path.exists(logo_path):
                                        req = urllib.request.Request("https://i.postimg.cc/x84nnjjq/IGO-LOGO.png", headers={'User-Agent': 'Mozilla/5.0'})
                                        with urllib.request.urlopen(req) as response, open(logo_path, 'wb') as out_file:
                                            out_file.write(response.read())
                                    pdf.image(logo_path, x=10, y=8, w=30) 
                                except Exception:
                                    pass
                                
                                pdf.set_y(15)
                                pdf.set_font("Arial", "B", 14)
                                pdf.set_text_color(15, 23, 42)
                                pdf.cell(0, 6, f"PROTOCOLO DE ENTREGA - IGO LOGISTICA", ln=True, align="C") 
                                
                                pdf.set_font("Arial", "B", 10)
                                pdf.set_text_color(2, 132, 199) 
                                pdf.cell(0, 5, f"LOTE DE EXPEDIÇÃO: {id_romaneio}", ln=True, align="C")
                                
                                pdf.set_font("Arial", "", 8)
                                pdf.set_text_color(100, 116, 139) 
                                pdf.cell(0, 4, f"Data do Embarque: {data_despacho.strftime('%d/%m/%Y')}", ln=True, align="C")
                                
                                pdf.ln(3)
                                pdf.line(10, pdf.get_y(), 200, pdf.get_y())
                                pdf.ln(3)
                                
                                pdf.set_fill_color(15, 23, 42) 
                                pdf.set_text_color(255, 255, 255)
                                pdf.set_font("Arial", "B", 7)
                                pdf.cell(10, 5, "ITEM", 1, 0, "C", True)
                                pdf.cell(25, 5, "PEDIDO", 1, 0, "C", True)
                                pdf.cell(30, 5, "ID CLIENTE", 1, 0, "C", True) 
                                pdf.cell(80, 5, "PONTO DE COLETA / LABORATÓRIO", 1, 0, "C", True)
                                pdf.cell(35, 5, "CIDADE", 1, 0, "C", True)
                                pdf.cell(10, 5, "UF", 1, 1, "C", True)
                                
                                pdf.set_text_color(51, 65, 85) 
                                pdf.set_font("Arial", "", 7)
                                
                                for idx, item in enumerate(sel_lista, 1):
                                    fill = (idx % 2 == 0)
                                    if fill: pdf.set_fill_color(241, 245, 249) 
                                    else: pdf.set_fill_color(255, 255, 255)
                                    
                                    qr_val = str(item.get('QR_CODE', ''))
                                    if qr_val.upper() == 'NAN' or not qr_val: qr_val = "-"
                                    
                                    pdf.cell(10, 5, str(idx), 1, 0, "C", True)
                                    pdf.cell(25, 5, str(item.get('PEDIDO','')), 1, 0, "C", True)
                                    pdf.cell(30, 5, qr_val, 1, 0, "C", True)
                                    pdf.cell(80, 5, str(item.get('LABORATORIO',''))[:48], 1, 0, "L", True)
                                    pdf.cell(35, 5, str(item.get('CIDADE',''))[:22], 1, 0, "L", True)
                                    pdf.cell(10, 5, str(item.get('UF','')), 1, 1, "C", True)
                                    
                                pdf.ln(4)
                                pdf.set_font("Arial", "B", 8)
                                pdf.set_text_color(15, 23, 42)
                                pdf.cell(0, 5, f"TOTAL DE VOLUMES CONFERIDOS E EMBARCADOS: {len(sel_lista)}", ln=True, align="R")
                                
                                pdf.set_y(-25)
                                pdf.line(20, pdf.get_y(), 90, pdf.get_y())
                                pdf.line(120, pdf.get_y(), 190, pdf.get_y())
                                pdf.set_font("Arial", "B", 7)
                                pdf.cell(95, 4, "ASSINATURA CADEIA (MOTORISTA)", 0, 0, "C")
                                pdf.cell(95, 4, "ASSINATURA EXPEDIÇÃO (BASE IGO)", 0, 1, "C")
                                
                                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
                                    pdf.output(tmp_pdf.name)
                                    with open(tmp_pdf.name, "rb") as f: pdf_bytes = f.read()
                                
                                st.success(f"🎉 O Lote de Código {id_romaneio} contendo {len(sel_lista)} amostras foi lacrado!")
                                st.download_button(label="📥 BAIXAR PROTOCOLO TÉCNICO (PDF)", data=pdf_bytes, file_name=f"Romaneio_Tecnico_{id_romaneio}.pdf", mime="application/pdf", type="primary")
                            except Exception as e: st.error(f"Interrupção na Criptografia de Carga: {e}")
            else: st.info("O salão está vazio. Somente lotes validados na Triagem aparecem para despacho.")

        with t3:
            st.markdown("#### Histórico Analítico de Triagem e Despacho")
            st.info("Visão macro de todas as amostras que já ultrapassaram a etapa de Logística de Rua (Coleta).")
            
            status_mostrar = ['CONFERIDO', 'EM ROTA DE ENTREGA', 'ENTREGUE', 'FRUSTRADA', 'PROBLEMA', 'CANCELADO']
            df_hist = df_raw[df_raw['STATUS'].astype(str).str.upper().isin(status_mostrar)].copy()
            
            if not df_hist.empty:
                df_hist = df_hist.sort_values(by=['DATA_OBJ', 'PEDIDO'], ascending=[False, False])
                
                colunas_hist = ['DATA', 'PEDIDO', 'TOMADOR', 'LABORATORIO', 'CIDADE', 'STATUS', 'AGENTE_RAW', 'ROMANEIO']
                
                # 🔥 ESCUDO ANTI-QUEBRA DE COLUNAS VITAIS NO HISTORICO
                for col in colunas_hist:
                    if col not in df_hist.columns:
                        df_hist[col] = ""
                df_hist_show = df_hist[colunas_hist]
                
                gb_hist = GridOptionsBuilder.from_dataframe(df_hist_show)
                gb_hist.configure_default_column(resizable=True, sortable=True, filter=False, suppressMenu=True, minWidth=150, flex=1)
                gb_hist.configure_grid_options(rowHeight=32, headerHeight=35)
                
                st_js = JsCode("""
                function(p){
                    let v = p.value || ''; 
                    if(v.includes('Entregue')){ return {'backgroundColor':'rgba(16,185,129,0.1)','color':'#059669','fontWeight':'700'}; } 
                    if(v.includes('Frustrada') || v.includes('Problema') || v.includes('Cancelado')){ return {'backgroundColor':'rgba(239,68,68,0.1)','color':'#DC2626','fontWeight':'700'}; } 
                    if(v.includes('Em Rota')){ return {'backgroundColor':'rgba(245,158,11,0.1)','color':'#D97706','fontWeight':'700'}; } 
                    if(v.includes('Coletado') || v.includes('Conferido')){ return {'backgroundColor':'rgba(59,130,246,0.1)','color':'#2563EB','fontWeight':'700'}; } 
                    if(v.includes('ATRASADO')){ return {'backgroundColor':'rgba(239,68,68,0.1)','color':'#DC2626','fontWeight':'700'}; } 
                    return {'fontWeight':'600', 'color': '#64748B'};
                }
                """)
                gb_hist.configure_column("STATUS", headerName="STATUS", cellStyle=st_js, minWidth=170)
                
                AgGrid(df_hist_show, gridOptions=gb_hist.build(), allow_unsafe_jscode=True, theme='alpine', custom_css=obter_css_grid(), height=400, fit_columns_on_grid_load=False)
            else:
                st.warning("O arquivo histórico de varreduras está temporariamente em branco.")
                
    else: st.info("O banco de dados está vazio no momento.")

# =============================================================================
# 📱 MÓDULO EXTRA: DISPARO WHATSAPP (BOTÃO ZAP)
# =============================================================================
elif menu == "📱 Zap":
    st.markdown("<div class='dinamic-border'><h3 class='dinamic-text' style='margin:0;'>📱 Central Tática de Comunicação</h3></div>", unsafe_allow_html=True)
    st.markdown("Acione o terminal de comando para injetar o cronograma oficial de rotas no WhatsApp corporativo da equipe.")
    
    df_raw = carregar_dados_completos(planilha_db)
    
    if not df_raw.empty:
        data_filtro = st.date_input("📅 Cronograma da Data:", value=hoje_br, format="DD/MM/YYYY")
        
        df_pendentes = df_raw[(df_raw['DATA_OBJ'] == data_filtro) & (df_raw['STATUS'].astype(str).str.upper() == 'PENDENTE')].copy()
        
        if df_pendentes.empty:
            st.success(f"Nenhum volume PENDENTE detectado no raio logístico de {data_filtro.strftime('%d/%m/%Y')}.")
        else:
            agentes_com_rota = df_pendentes['AGENTE_RAW'].dropna().unique()
            agentes_com_rota = [ag for ag in agentes_com_rota if str(ag).strip()]
            
            if not agentes_com_rota:
                st.warning("Falha de Roteirização Crítica: Os volumes foram captados pela nuvem, mas as diretrizes de rota estão cegas (Sem Motorista).")
            else:
                st.info(f"Radar ativado. Rastreando **{len(df_pendentes)}** pontos de parada distribuídos nos vetores de **{len(agentes_com_rota)}** agentes de campo.")
                
                dict_telefones = {}
                if not DF_AGENTES.empty:
                    for _, row in DF_AGENTES.iterrows():
                        login = str(row.get('LOGIN DO AGENTE', '')).strip().lower()
                        tel = str(row.get('TELEFONE', '')).strip()
                        tel_limpo = re.sub(r'\D', '', tel)
                        if login and tel_limpo:
                            dict_telefones[login] = tel_limpo

                for agente in sorted(agentes_com_rota):
                    df_agente = df_pendentes[df_pendentes['AGENTE_RAW'] == agente].copy()
                    
                    # 🔥 ESCUDO ANTI-QUEBRA DE COLUNAS VITAIS NO ZAP
                    colunas_zap = ['PEDIDO', 'TOMADOR', 'LABORATORIO', 'CIDADE', 'ENDERECO', 'NUMERO', 'BAIRRO', 'OBSERVACOES']
                    for col in colunas_zap:
                        if col not in df_agente.columns:
                            df_agente[col] = ""

                    qtd_pedidos = len(df_agente)
                    telefone = dict_telefones.get(str(agente).strip().lower(), "")
                    
                    with st.expander(f"👤 Agente Tático: {str(agente).upper()} | Volumes na Rota: {qtd_pedidos}", expanded=False):
                        st.dataframe(df_agente[['PEDIDO', 'TOMADOR', 'LABORATORIO', 'CIDADE']], hide_index=True, use_container_width=True)
                        
                        if telefone:
                            msg = f"🚚 *ROTA OFICIAL IGO LOGÍSTICA*\n"
                            msg += f"Data: {data_filtro.strftime('%d/%m/%Y')}\n"
                            msg += f"Agente Tático: {str(agente).upper()}\n\n"
                            msg += f"🧪 *VOLUMES BIOLÓGICOS/TOXICOLÓGICOS ({qtd_pedidos}):*\n\n"
                            
                            for i, (_, row) in enumerate(df_agente.iterrows(), 1):
                                msg += f"*{i}️⃣ Identificador:* {row['PEDIDO']}\n"
                                msg += f"🏥 *Clínica Solicitante:* {row.get('TOMADOR', '')}\n"
                                msg += f"🏢 *Base de Captação:* {row.get('LABORATORIO', '')}\n"
                                msg += f"📍 *Coordenadas:* {row.get('ENDERECO', '')}, {row.get('NUMERO', '')} - {row.get('BAIRRO', '')}, {row.get('CIDADE', '')}\n"
                                if str(row.get('OBSERVACOES', '')).strip() and str(row.get('OBSERVACOES', '')).upper() != 'NAN':
                                    msg += f"📝 *Aviso de Rota:* {row['OBSERVACOES']}\n"
                                msg += "------------------------\n"
                            
                            msg += "\nZele pela integridade do material. Dirija com extrema segurança."
                            
                            msg_codificada = urllib.parse.quote(msg)
                            link_whatsapp = f"https://api.whatsapp.com/send?phone={telefone}&text={msg_codificada}"
                            
                            st.link_button("📲 Emitir Ordem de Deslocamento Automática", link_whatsapp, type="primary")
                        else:
                            st.error(f"⚠️ Barreira de Comunicação: A diretriz de contato numérico do agente '{agente}' está corrompida ou vazia no DB.")
    else:
        st.warning("📭 O banco de dados está vazio no momento.")

# =============================================================================
# 📥 MÓDULO 4: EXPORTAR RELATÓRIOS
# =============================================================================
elif menu == "📁 Relatórios":
    st.markdown("<div class='dinamic-border'><h3 class='dinamic-text' style='margin:0;'>📥 Central de Datamining e Exportação</h3></div>", unsafe_allow_html=True)
    df_raw = carregar_dados_completos(planilha_db)
    
    if not df_raw.empty:
        colunas_export = ['DATA', 'PEDIDO', 'TOMADOR', 'LABORATORIO', 'ENDERECO', 'NUMERO', 'BAIRRO', 'CIDADE', 'UF', 'CEP', 'STATUS', 'DATA_ENTREGA', 'AGENTE_RAW', 'DATA_LIMITE']
        
        # 🔥 ESCUDO ANTI-QUEBRA DE COLUNAS VITAIS NO RELATORIO
        for col in colunas_export:
            if col not in df_raw.columns:
                df_raw[col] = ""
                
        df_export_base = df_raw[colunas_export].copy()
        if 'AGENTE_RAW' in df_export_base.columns: df_export_base.rename(columns={'AGENTE_RAW': 'MOTORISTA'}, inplace=True)
        
        st.markdown("### ⚡ Auditoria Rápida de Lotes Pré-Configurados")
        col_rel1, col_rel2, col_rel3 = st.columns(3)
        
        df_rj = df_export_base[df_export_base['UF'].str.upper() == 'RJ'] if 'UF' in df_export_base.columns else pd.DataFrame()
        if 'CIDADE' in df_export_base.columns:
            df_jf = df_export_base[df_export_base['CIDADE'].str.upper().str.contains('JUIZ DE FORA', na=False)]
            df_rjjf = pd.concat([df_rj, df_jf]).drop_duplicates(subset=['PEDIDO'])
        else: df_rjjf = df_rj
            
        if not df_rjjf.empty:
            col_rel1.download_button("📥 Minerar Bloco RJ / JF", data=gerar_excel_memoria(df_rjjf), file_name=f"Datamining_RJ_JF_{datetime.now(FUSO_BR).strftime('%d%m%Y')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
        else: col_rel1.button("📥 Minerar Bloco RJ / JF (Zero Ocorrências)", disabled=True, use_container_width=True)

        if 'MOTORISTA' in df_export_base.columns:
            df_lud = df_export_base[df_export_base['MOTORISTA'].str.lower().str.contains('ludmila|veloz', na=False)]
            if not df_lud.empty:
                col_rel2.download_button("📥 Minerar Base Ludmila / Veloz", data=gerar_excel_memoria(df_lud), file_name=f"Datamining_Ludmila_{datetime.now(FUSO_BR).strftime('%d%m%Y')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
            else: col_rel2.button("📥 Minerar Base Ludmila / Veloz (Sem Dados)", disabled=True, use_container_width=True)
        
        col_rel3.download_button("📥 Extração Completa (Nuvem Integral)", data=gerar_excel_memoria(df_export_base), file_name=f"BKP_Integral_{datetime.now(FUSO_BR).strftime('%d%m%Y')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary", use_container_width=True)
        
        st.markdown("---")
        st.markdown("### 🔍 Motor Analítico Customizável (Pesquisa Cruzada)")
        with st.form("form_rel_custom"):
            cf1, cf2 = st.columns(2)
            c_ag = cf1.text_input("👤 Codinome do Agente:")
            c_cid = cf2.text_input("🏙️ Raio de Busca (Cidade):")
            c_uf = cf1.text_input("🗺️ Vetor Estadual (UF):")
            c_base = cf2.text_input("🏢 Hub Logístico (Tomador/Clínica):")
            
            if st.form_submit_button("Executar Pesquisa e Compilar Tabela"):
                df_custom = df_export_base.copy()
                if c_ag and 'MOTORISTA' in df_custom.columns: df_custom = df_custom[df_custom['MOTORISTA'].str.upper().str.contains(c_ag.upper(), na=False)]
                if c_cid and 'CIDADE' in df_custom.columns: df_custom = df_custom[df_custom['CIDADE'].str.upper().str.contains(c_cid.upper(), na=False)]
                if c_uf and 'UF' in df_custom.columns: df_custom = df_custom[df_custom['UF'].str.upper() == c_uf.upper()]
                if c_base:
                    mt = df_custom['TOMADOR'].str.upper().str.contains(c_base.upper(), na=False) if 'TOMADOR' in df_custom.columns else False
                    ml = df_custom['LABORATORIO'].str.upper().str.contains(c_base.upper(), na=False) if 'LABORATORIO' in df_custom.columns else False
                    df_custom = df_custom[mt | ml]
                
                if not df_custom.empty:
                    st.success(f"Pesquisa concluída! Encontramos uma massa de {len(df_custom)} volumes cruzados com as suas restrições.")
                    st.download_button("📥 Fazer Download do Relatório Cru (Excel)", data=gerar_excel_memoria(df_custom), file_name=f"Pesquisa_Customizada_IGO.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                else: st.warning("Nenhum dado cruzado sob essas métricas foi identificado na nuvem.")
    else: st.warning("O banco de dados está vazio.")

# =============================================================================
# ⚙️ MÓDULO 5: CONFIGURAR ROTAS E AGENTES
# =============================================================================
elif menu == "⚙️ Rotas":
    st.markdown("<div class='dinamic-border'><h3 class='dinamic-text' style='margin:0;'>⚙️ Matriz Inteligente de Rotas e Equipe</h3></div>", unsafe_allow_html=True)
    
    tab_agente, tab_rota, tab_tabela = st.tabs(["👤 Cadastrar Novo Agente", "📍 Adicionar Rota (Vincular)", "📋 Gerenciar Motorista Específico"])
    
    with tab_agente:
        st.markdown("#### Formulário de Novo Motorista")
        with st.form("form_novo_agente", clear_on_submit=True):
            c1, c2 = st.columns(2)
            login_ag = c1.text_input("ID de Login", placeholder="Ex: carlos.rj")
            nome_ag = c2.text_input("Nome Amigável", placeholder="Ex: CARLOS SILVA")
            tel_ag = st.text_input("WhatsApp com DDD", placeholder="Ex: 5521999999999")
            
            if st.form_submit_button("💾 Salvar Novo Agente", type="primary"):
                if not login_ag or not nome_ag or not tel_ag: st.error("⚠️ Preencha todos os campos!")
                else:
                    tel_limpo = re.sub(r'\D', '', tel_ag)
                    nova_linha = pd.DataFrame([{"ROTA MAPEADA": "SEM ROTA DEFINIDA", "LOGIN DO AGENTE": login_ag.lower().strip(), "NOME DO AGENTE": nome_ag.upper().strip(), "TELEFONE": tel_limpo}])
                    df_novo = pd.concat([DF_AGENTES, nova_linha], ignore_index=True)
                    try:
                        aba = planilha_db.worksheet("Agentes")
                        aba.update("A1", [df_novo.columns.tolist()] + df_novo.fillna("").astype(str).values.tolist())
                        st.success(f"✅ Agente salvo!")
                        carregar_dados_agentes.clear()
                    except Exception as e: st.error(f"Erro: {e}")

    with tab_rota:
        st.markdown("#### Atrelar Cidade/Bairro a um Motorista")
        with st.form("form_nova_rota", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            cid_rota = c1.text_input("Cidade *", placeholder="Ex: SAO PAULO")
            bai_rota = c2.text_input("Bairro (Opcional)", placeholder="Ex: PINHEIROS")
            rua_rota = c3.text_input("Endereço (Opcional)", placeholder="Ex: AVENIDA PAULISTA")
            logins_disp = sorted(DF_AGENTES['LOGIN DO AGENTE'].unique().tolist()) if not DF_AGENTES.empty else []
            ag_selecionado = st.selectbox("Selecione o Agente:", logins_disp)
            
            if st.form_submit_button("📍 Salvar Nova Rota", type="primary"):
                if not cid_rota or not ag_selecionado: st.error("⚠️ Cidade e Agente são obrigatórios!")
                else:
                    partes = [p for p in [limpar_nome_local_rota(cid_rota), limpar_nome_local_rota(bai_rota), tratar_texto_global(rua_rota)] if p]
                    rota_str = " ➔ ".join(partes)
                    dados_ag = DF_AGENTES[DF_AGENTES['LOGIN DO AGENTE'] == ag_selecionado].iloc[0]
                    nova_linha = pd.DataFrame([{"ROTA MAPEADA": rota_str, "LOGIN DO AGENTE": ag_selecionado, "NOME DO AGENTE": dados_ag['NOME DO AGENTE'], "TELEFONE": dados_ag['TELEFONE']}])
                    df_novo = pd.concat([DF_AGENTES, nova_linha], ignore_index=True)
                    try:
                        aba = planilha_db.worksheet("Agentes")
                        aba.update("A1", [df_novo.columns.tolist()] + df_novo.fillna("").astype(str).values.tolist())
                        st.success(f"✅ Rota '{rota_str}' atrelada!")
                        carregar_dados_agentes.clear()
                    except Exception as e: st.error(f"Erro: {e}")

    with tab_tabela:
        if not DF_AGENTES.empty:
            logins_para_filtro = sorted(DF_AGENTES['LOGIN DO AGENTE'].unique().tolist())
            st.markdown("<br>", unsafe_allow_html=True)
            col_f, _ = st.columns([1, 1])
            agente_filtro = col_f.selectbox("👤 Selecione o Motorista para gerenciar apenas suas rotas:", logins_para_filtro)
            
            st.markdown(f"#### ➕ Adicionar rota rápida para {agente_filtro}")
            with st.form(f"form_rapido_{agente_filtro}", clear_on_submit=True):
                ca1, ca2, ca3, ca4 = st.columns([2, 2, 2, 1])
                r_cid = ca1.text_input("Cidade", key="r_cid")
                r_bai = ca2.text_input("Bairro (Opç)", key="r_bai")
                r_rua = ca3.text_input("Endereço (Opç)", key="r_rua")
                st.markdown("<style>.st-key-btn_add_rapido {margin-top: 28px;}</style>", unsafe_allow_html=True)
                add_rapido = ca4.form_submit_button("➕ Salvar", use_container_width=True)
                
                if add_rapido:
                    if not r_cid: st.error("A Cidade é obrigatória!")
                    else:
                        partes = [p for p in [limpar_nome_local_rota(r_cid), limpar_nome_local_rota(r_bai), tratar_texto_global(r_rua)] if p]
                        rota_str = " ➔ ".join(partes)
                        dados_ag = DF_AGENTES[DF_AGENTES['LOGIN DO AGENTE'] == agente_filtro].iloc[0]
                        nova_linha = pd.DataFrame([{"ROTA MAPEADA": rota_str, "LOGIN DO AGENTE": agente_filtro, "NOME DO AGENTE": dados_ag['NOME DO AGENTE'], "TELEFONE": dados_ag['TELEFONE']}])
                        df_novo = pd.concat([DF_AGENTES, nova_linha], ignore_index=True)
                        try:
                            planilha_db.worksheet("Agentes").update("A1", [df_novo.columns.tolist()] + df_novo.fillna("").astype(str).values.tolist())
                            st.success("Rota adicionada!")
                            carregar_dados_agentes.clear()
                            st.rerun()
                        except Exception as e: st.error(f"Erro ao salvar: {e}")

            st.markdown(f"#### 📍 Rotas Atuais")
            df_ag_filtrado = DF_AGENTES[DF_AGENTES['LOGIN DO AGENTE'] == agente_filtro].copy()
            if df_ag_filtrado.empty: st.warning("Nenhuma rota atrelada a este motorista.")
            else:
                for idx, row in df_ag_filtrado.iterrows():
                    rota_disp = row['ROTA MAPEADA'].replace("---", " ➔ ")
                    with st.container():
                        col_rota, col_del = st.columns([5, 1])
                        col_rota.markdown(f"<div style='padding:10px; background-color:#FFFFFF; border-radius:5px; border: 1px solid #E2E8F0;'><b>📍 {rota_disp}</b></div>", unsafe_allow_html=True)
                        if col_del.button("🗑️ Remover", key=f"del_{idx}", use_container_width=True):
                            df_novo = DF_AGENTES.drop(idx)
                            try:
                                aba = planilha_db.worksheet("Agentes")
                                aba.update("A1", [df_novo.columns.tolist()] + df_novo.fillna("").astype(str).values.tolist())
                                carregar_dados_agentes.clear()
                                st.rerun()
                            except Exception as e: st.error(f"Erro ao remover: {e}")
        else: st.warning("Nenhum dado encontrado.")
