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
import time
from datetime import datetime, timedelta, timezone
import random
import gspread
import uuid
import base64
from streamlit_autorefresh import st_autorefresh
from fpdf import FPDF

FUSO_BR = timezone(timedelta(hours=-3))

# =============================================================================
# 🔗 1. CONFIGURAÇÃO DA PÁGINA E ESTILOS NATIVOS
# =============================================================================
st.set_page_config(page_title="C.C.O - IGO Logística", layout="wide", page_icon="🚚", initial_sidebar_state="expanded")
st_autorefresh(interval=120000, limit=None, key="refresh_timer")

st.markdown("""
    <style>
    #MainMenu { visibility: hidden !important; }
    footer { visibility: hidden !important; }
    .stAppDeployButton { display: none !important; }
    
    [data-testid="stSidebar"] { background-color: #FFFFFF !important; border-right: 1px solid #E2E8F0; }
    
    .block-container { padding-top: 2rem !important; padding-bottom: 2rem !important; max-width: 98% !important; }
    
    [data-testid="stAppViewContainer"] { background-color: #FFFFFF !important; }
    
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
    
    div[data-testid="stPopover"] > button, button[kind="secondary"] {
        white-space: nowrap !important; overflow: hidden !important; font-weight: 600 !important; font-size: 13px !important; border-radius: 6px !important; height: 36px !important; min-height: 36px !important; padding: 0px 12px !important; border: 1px solid #CBD5E1 !important; background-color: #FFFFFF !important; color: #475569 !important; transition: all 0.2s ease !important; box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important; margin-bottom: 10px;
    }
    div[data-testid="stPopover"] > button:hover, button[kind="secondary"]:hover {
        border-color: #0284C7 !important; color: #0369A1 !important; background-color: #F0F9FF !important; box-shadow: 0 2px 4px rgba(2, 132, 199, 0.1) !important;
    }
    
    .header-container { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 15px; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px; }
    .sync-status { font-size: 12px; color: #10B981; font-weight: 700; }
    
    div[data-testid="stSidebar"] button[kind="primary"] {
        background: linear-gradient(135deg, #EF4444 0%, #991B1B 100%) !important;
        color: white !important;
        border: none !important;
        font-weight: bold !important;
        box-shadow: 0 4px 6px rgba(239, 68, 68, 0.3) !important;
    }
    </style>
""", unsafe_allow_html=True)

if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

if 'log_triagem' not in st.session_state:
    st.session_state.log_triagem = []

if not st.session_state.autenticado:
    col_vazia1, col_login, col_vazia2 = st.columns([1, 1.5, 1])
    with col_login:
        st.markdown("<br><br><br>", unsafe_allow_html=True) 
        st.markdown("<div style='text-align: center;'><img src='https://i.postimg.cc/x84nnjjq/IGO-LOGO.png' width='250'></div>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; color: #0F172A; margin-top: 15px; margin-bottom: 25px; font-weight: 800;'>PORTAL CORPORATIVO</h2>", unsafe_allow_html=True)
        
        with st.form("form_login"):
            usuario = st.text_input("👤 Usuário")
            senha = st.text_input("🔑 Senha", type="password")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.form_submit_button("ACESSAR SISTEMA", use_container_width=True, type="primary"):
                logins_autorizados = {"robson.melo": "123", "william.bertoldo": "123"}
                if usuario in logins_autorizados and logins_autorizados[usuario] == senha:
                    st.session_state.autenticado = True
                    st.rerun()
                else:
                    st.error("❌ Credenciais inválidas.")
    st.stop()

# =============================================================================
# 🔗 2. CONEXÕES OFICIAL E SANDBOX
# =============================================================================
@st.cache_resource
def conectar_banco():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        import json
        from google.oauth2.credentials import Credentials
        token_str = os.environ.get("google_token_json")
        if not token_str:
            try: token_str = st.secrets.get("google_token_json")
            except: pass
        if not token_str:
            st.error("⚠️ Senha do Google não detectada.")
            return None
        token_info = json.loads(token_str)
        creds = Credentials.from_authorized_user_info(token_info, scopes=scopes)
        gc = gspread.authorize(creds)
        return gc.open("DB_IGO_Logistica")
    except Exception as e:
        st.error(f"Erro na leitura da chave: {e}")
    return None

@st.cache_resource
def conectar_sandbox():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        import json
        from google.oauth2.credentials import Credentials
        token_str = os.environ.get("google_token_json")
        if not token_str:
            try: token_str = st.secrets.get("google_token_json")
            except: pass
        if not token_str: return None
        token_info = json.loads(token_str)
        creds = Credentials.from_authorized_user_info(token_info, scopes=scopes)
        gc = gspread.authorize(creds)
        return gc.open("Import_Umove")
    except Exception as e:
        st.error(f"⚠️ Planilha Sandbox 'Import_Umove' não encontrada no Drive. Erro: {e}")
        return None

planilha_db = conectar_banco()
planilha_sandbox = conectar_sandbox()

CLIENTES_AUTORIZADOS = ["CAEP", "SAPIENS", "GRALAB", "SYNVIA", "INNOVATOX", "LABEST", "AIRLAB", "UNILABOR", "SODRE", "BRASILIENSE", "SOUZA CRUZ", "HEXALIFE", "ECOLYZER"]

@st.cache_data(ttl=20)
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
            df = df.loc[:, ~df.columns.duplicated()].dropna(how='all') 
            
            if 'ZAP_ENVIADO' not in df.columns: df['ZAP_ENVIADO'] = ""
            if 'CNPJ' not in df.columns: df['CNPJ'] = "" 

            try:
                aba_app = _planilha.worksheet("App_Tarefas")
                dados_app = aba_app.get_all_values()
                if len(dados_app) > 1:
                    df_app = pd.DataFrame(dados_app[1:], columns=dados_app[0])
                    cols_limpas = [str(c).upper().strip().replace('?', '').replace(' ', '') for c in df_app.columns]
                    df_app.columns = cols_limpas
                    
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
                        if s_db in ['EM ROTA DE ENTREGA', 'CONFERIDO', 'COLETADO']: return s_db
                        if s_app == 'COLETADO': return s_app
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
                        
                    if 'DATA_ENTREGA' in df.columns or 'APP_DATA_ENTREGA' in df.columns:
                        df['DATA_ENTREGA'] = df.apply(get_true_data_entrega, axis=1)

                    def get_true_foto(row):
                        f_db = str(row.get('FOTO', '')).strip()
                        f_app = str(row.get('APP_FOTO', '')).strip()
                        rom_id = str(row.get('ROMANEIO', '')).strip()
                        if rom_id in rom_dict:
                            f_rom = str(rom_dict[rom_id].get('APP_FOTO', '')).strip()
                            if f_rom and f_rom.upper() != 'NAN': return f_rom
                        if f_app and f_app.upper() != 'NAN': return f_app
                        return f_db
                        
                    if 'APP_FOTO' in df.columns or len(rom_dict) > 0:
                        df['FOTO'] = df.apply(get_true_foto, axis=1)
            except Exception: pass
            
            if 'DATA' in df.columns: 
                df['DATA_OBJ'] = pd.to_datetime(df['DATA'], format='%d/%m/%Y', errors='coerce').dt.date
            return df
    except Exception as e: 
        st.error(f"Erro Crítico ao carregar a Memoria_Sistema: {e}")
    return pd.DataFrame()

DF_AGENTES = carregar_dados_agentes(planilha_db)
FERIADOS_BR = holidays.Brazil()
hoje_br = datetime.now(FUSO_BR).date() 

def padronizar_texto(texto):
    if pd.isna(texto) or not texto: return ""
    return unicodedata.normalize('NFKD', str(texto).strip()).encode('ASCII', 'ignore').decode('utf-8').upper()

def despachar_para_appsheet(lista_pedidos_dicts):
    if planilha_db is None or not lista_pedidos_dicts: return False
    try:
        aba = planilha_db.worksheet("App_Tarefas")
        linhas = []
        for p in lista_pedidos_dicts:
            mot = str(p.get('MOTORISTA', p.get('AGENTE_RAW', '')))
            linhas.append([
                str(uuid.uuid4())[:8].upper(),    
                str(p.get('PEDIDO','')),          
                mot,                              
                "PENDENTE",                        
                str(p.get('ENDERECO','')),        
                str(p.get('NUMERO','')),          
                str(p.get('BAIRRO','')),          
                str(p.get('CIDADE','')),          
                str(p.get('CEP','')),             
                "",                               
                str(p.get('OBSERVACOES','')),     
                str(p.get('LABORATORIO','')),     
                str(p.get('TOMADOR','')),         
                str(p.get('QR_CODE','')),         
                "",                               
                str(p.get('ROMANEIO','')),        
                "",                               
                ""                                
            ])
        aba.append_rows(linhas, value_input_option='USER_ENTERED')
        return True
    except Exception as e: 
        st.error(f"🚨 ERRO APPSHEET: {e}")
        return False

def enviar_whatsapp_zapi(telefone_destino, texto_mensagem):
    INSTANCIA = "3F14E62A63D2B28DC385B20DE66F3711" 
    TOKEN = "2321563615C4242CB6031504"         
    CLIENT_TOKEN = "Ffaa43dcff1e14f0e985c91e92b24ed89S" 
    tel_limpo = re.sub(r'\D', '', str(telefone_destino))
    if not tel_limpo.startswith('55') and len(tel_limpo) in [10, 11]: tel_limpo = '55' + tel_limpo
    url = f"https://api.z-api.io/instances/{INSTANCIA}/token/{TOKEN}/send-text"
    payload = {"phone": tel_limpo, "message": texto_mensagem}
    headers = {"Accept": "application/json", "Content-Type": "application/json", "Client-Token": CLIENT_TOKEN}
    try:
        response = requests.post(url, json=payload, headers=headers)
        return response.status_code in [200, 201]
    except Exception: return False

def enviar_pdf_zapi(telefone_destino, pdf_bytes, nome_arquivo):
    INSTANCIA = "3F14E62A63D2B28DC385B20DE66F3711" 
    TOKEN = "2321563615C4242CB6031504"         
    CLIENT_TOKEN = "Ffaa43dcff1e14f0e985c91e92b24ed89S" 
    tel_limpo = re.sub(r'\D', '', str(telefone_destino))
    if not tel_limpo.startswith('55') and len(tel_limpo) in [10, 11]: tel_limpo = '55' + tel_limpo
    url = f"https://api.z-api.io/instances/{INSTANCIA}/token/{TOKEN}/send-document/pdf"
    b64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
    payload = {"phone": tel_limpo, "document": f"data:application/pdf;base64,{b64_pdf}", "fileName": nome_arquivo}
    headers = {"Accept": "application/json", "Content-Type": "application/json", "Client-Token": CLIENT_TOKEN}
    try:
        response = requests.post(url, json=payload, headers=headers)
        return response.status_code in [200, 201]
    except Exception: return False

def enviar_excel_zapi(telefone_destino, xls_bytes, nome_arquivo):
    INSTANCIA = "3F14E62A63D2B28DC385B20DE66F3711" 
    TOKEN = "2321563615C4242CB6031504"         
    CLIENT_TOKEN = "Ffaa43dcff1e14f0e985c91e92b24ed89S" 
    tel_limpo = re.sub(r'\D', '', str(telefone_destino))
    if not tel_limpo.startswith('55') and len(tel_limpo) in [10, 11]: tel_limpo = '55' + tel_limpo
    url = f"https://api.z-api.io/instances/{INSTANCIA}/token/{TOKEN}/send-document/xlsx"
    b64_xls = base64.b64encode(xls_bytes).decode('utf-8')
    payload = {"phone": tel_limpo, "document": f"data:application/octet-stream;base64,{b64_xls}", "fileName": nome_arquivo}
    headers = {"Accept": "application/json", "Content-Type": "application/json", "Client-Token": CLIENT_TOKEN}
    try:
        response = requests.post(url, json=payload, headers=headers)
        return response.status_code in [200, 201]
    except Exception: return False

def obter_proximo_id(df):
    if df is None or df.empty or 'PEDIDO' not in df.columns: return 1
    try:
        nums = df['PEDIDO'].astype(str).str.extract(r'^(\d+)')[0].dropna().astype(int)
        return int(nums.max() + 1) if not nums.empty else 1
    except: return 1

def calcular_sla_dias(uf, cidade):
    uf, cidade = str(uf).upper().strip(), padronizar_texto(cidade)
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

def calc_status_display(row):
    status_final = str(row.get('STATUS', '')).strip().upper()
    previsao = str(row.get('DATA_LIMITE', '')).strip()
    res = '⏳ Pendente'
    
    if 'ENTREGUE' in status_final: res = '✅ Entregue'
    elif 'COLETADO' in status_final: res = '📦 Coletado'
    elif 'ROTA DE COLETA' in status_final: res = '🚐 Rota de Coleta'
    elif 'ROTA' in status_final: res = '🚚 Em Rota de Entrega'
    elif 'CONFERIDO' in status_final: res = '☑️ Conferido'
    elif 'FRUSTRADA' in status_final: res = '❌ Frustrada'
    elif 'CANCELADO' in status_final: res = '🚫 Cancelado'
    elif 'PROBLEMA' in status_final: res = '🚨 Problema'
    
    if '✅' not in res and '🚫' not in res and '❌' not in res and previsao:
        try:
            if datetime.strptime(previsao, "%d/%m/%Y").date() < hoje_br: res = f"{res} ⚠️ ATRASADO"
        except: pass
    return res

def tratar_texto_global(texto):
    if pd.isna(texto): return ""
    t = padronizar_texto(texto)
    return t[:-2] if t.endswith('.0') else t

def limpar_nome_local_rota(texto):
    return tratar_texto_global(texto).split('/')[0].split('-')[0].strip()

def obter_login_agente(cidade, bairro, laboratorio, endereco="", base_rotas_df=pd.DataFrame()):
    if base_rotas_df.empty: return ""
    rotas_dict = {padronizar_texto(str(row['ROTA MAPEADA']).upper().replace(" ➔ ", "---").replace(" -> ", "---")): str(row['LOGIN DO AGENTE']).lower().strip() for _, row in base_rotas_df.iterrows()}
    cid = limpar_nome_local_rota(cidade)
    bai = limpar_nome_local_rota(bairro)
    lab = tratar_texto_global(laboratorio)
    end = tratar_texto_global(endereco)
    
    for c in [f"{cid}---{bai}---{end}", f"{cid}---{bai}---{lab}", f"{cid}---{lab}", f"{cid}---{bai}", cid]:
        if c in rotas_dict: return rotas_dict[c]
    return ""

def gerar_excel_memoria(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Relatorio', index=False)
        worksheet = writer.sheets['Relatorio']
        worksheet.hide_gridlines(2)
        if df.shape[0] > 0:
            worksheet.add_table(0, 0, df.shape[0], df.shape[1] - 1, {'columns': [{'header': str(col)} for col in df.columns], 'style': 'Table Style Medium 2'})
            for i, col in enumerate(df.columns): 
                worksheet.set_column(i, i, min(max(df[col].astype(str).map(len).max(), len(str(col))) + 2, 40))
    return output.getvalue()

def gerar_excel_rota_whatsapp(df_agente):
    output = io.BytesIO()
    df_xls = df_agente.copy()
    cols_desejadas = ['PEDIDO', 'LABORATORIO', 'ENDERECO', 'NUMERO', 'BAIRRO', 'CEP', 'TOMADOR', 'OBSERVACOES']
    for c in cols_desejadas:
        if c not in df_xls.columns: df_xls[c] = ""
            
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        resumo = df_xls.groupby('CIDADE').size().reset_index(name='QTD_VOLUMES')
        resumo.loc[len(resumo)] = ['TOTAL GERAL', resumo['QTD_VOLUMES'].sum()]
        resumo.to_excel(writer, sheet_name='RESUMO_GERAL', index=False)
        worksheet_res = writer.sheets['RESUMO_GERAL']
        worksheet_res.hide_gridlines(2)
        worksheet_res.add_table(0, 0, len(resumo), 1, {'columns': [{'header': 'CIDADE'}, {'header': 'QTD_VOLUMES'}], 'style': 'Table Style Medium 2'})
        worksheet_res.set_column('A:A', 30); worksheet_res.set_column('B:B', 15)
        
        for cidade, group in df_xls.groupby('CIDADE'):
            cid_limpa = re.sub(r'[^A-Za-z0-9 ]', '', str(cidade).strip())[:30] 
            if not cid_limpa: cid_limpa = "Sem_Cidade"
            df_cid = group[cols_desejadas].copy()
            df_cid.to_excel(writer, sheet_name=cid_limpa, index=False)
            worksheet = writer.sheets[cid_limpa]
            worksheet.hide_gridlines(2)
            if len(df_cid) > 0:
                worksheet.add_table(0, 0, len(df_cid), len(df_cid.columns) - 1, {'columns': [{'header': str(col)} for col in df_cid.columns], 'style': 'Table Style Light 9'})
            worksheet.set_column('A:A', 15); worksheet.set_column('B:B', 40); worksheet.set_column('C:C', 40); worksheet.set_column('D:H', 20) 
    return output.getvalue()

def gerar_pdf_rota_whatsapp(nome_motorista, data_str, df_agente):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_draw_color(15, 23, 42); pdf.set_line_width(0.3); pdf.rect(5, 5, 200, 287)
    try:
        logo_path = os.path.join(tempfile.gettempdir(), "igo_logo_temp.png")
        if not os.path.exists(logo_path):
            req = urllib.request.Request("https://i.postimg.cc/x84nnjjq/IGO-LOGO.png", headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response, open(logo_path, 'wb') as out_file: out_file.write(response.read())
        pdf.image(logo_path, x=10, y=8, w=30) 
    except Exception: pass
    
    pdf.set_y(15); pdf.set_font("Arial", "B", 14); pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 6, f"ROTA OFICIAL DE OPERACAO - IGO LOGISTICA", ln=True, align="C") 
    pdf.set_font("Arial", "B", 10); pdf.set_text_color(2, 132, 199) 
    pdf.cell(0, 5, f"AGENTE: {padronizar_texto(nome_motorista)}", ln=True, align="C")
    pdf.set_font("Arial", "", 8); pdf.set_text_color(100, 116, 139) 
    pdf.cell(0, 4, f"Data da Rota: {data_str} | Total de Volumes: {len(df_agente)}", ln=True, align="C")
    pdf.ln(3); pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(3)
    
    grouped_cidade = df_agente.groupby('CIDADE')
    for cidade, group_cid in grouped_cidade:
        cidade_nome = padronizar_texto(str(cidade))
        pdf.set_fill_color(15, 23, 42); pdf.set_text_color(255, 255, 255); pdf.set_font("Arial", "B", 9)
        pdf.cell(0, 6, f"CIDADE: {cidade_nome}", 1, 1, "L", True)
        
        grouped_bairro = group_bai = group_cid.groupby('BAIRRO')
        for bairro, group_bai in grouped_bairro:
            bairro_nome = padronizar_texto(str(bairro))
            pdf.set_fill_color(226, 232, 240); pdf.set_text_color(15, 23, 42); pdf.set_font("Arial", "B", 8)
            pdf.cell(0, 5, f"   BAIRRO: {bairro_nome}", 1, 1, "L", True)
            pdf.set_fill_color(241, 245, 249); pdf.set_text_color(71, 85, 105); pdf.set_font("Arial", "B", 7)
            pdf.cell(8, 5, "OK", 1, 0, "C", True); pdf.cell(20, 5, "PEDIDO", 1, 0, "C", True); pdf.cell(60, 5, "LABORATORIO", 1, 0, "L", True); pdf.cell(77, 5, "ENDERECO", 1, 0, "L", True); pdf.cell(25, 5, "TOMADOR", 1, 1, "C", True)
            pdf.set_text_color(51, 65, 85); pdf.set_font("Arial", "", 7)
            for _, row in group_bai.iterrows():
                ped = padronizar_texto(str(row.get('PEDIDO',''))); lab = padronizar_texto(str(row.get('LABORATORIO','')))[:35]
                end = padronizar_texto(f"{str(row.get('ENDERECO',''))}, {str(row.get('NUMERO',''))}")[:48]; tom = padronizar_texto(str(row.get('TOMADOR','')))[:15]
                pdf.cell(8, 5, "[  ]", 1, 0, "C"); pdf.cell(20, 5, ped, 1, 0, "C"); pdf.cell(60, 5, lab, 1, 0, "L"); pdf.cell(77, 5, end, 1, 0, "L"); pdf.cell(25, 5, tom, 1, 1, "C")
        pdf.ln(2)
        
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
        pdf.output(tmp_pdf.name)
        with open(tmp_pdf.name, "rb") as f: pdf_bytes = f.read()
    return pdf_bytes

def gerar_pdf_romaneio(id_romaneio, data_despacho, motorista_escolhido, sel_lista):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_draw_color(15, 23, 42); pdf.set_line_width(0.3); pdf.rect(5, 5, 200, 287)
    try:
        logo_path = os.path.join(tempfile.gettempdir(), "igo_logo_temp.png")
        if not os.path.exists(logo_path):
            req = urllib.request.Request("https://i.postimg.cc/x84nnjjq/IGO-LOGO.png", headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response, open(logo_path, 'wb') as out_file: out_file.write(response.read())
        pdf.image(logo_path, x=10, y=8, w=30) 
    except Exception: pass
        
    pdf.set_y(15); pdf.set_font("Arial", "B", 14); pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 6, f"PROTOCOLO DE ENTREGA - IGO LOGISTICA", ln=True, align="C") 
    pdf.set_font("Arial", "B", 10); pdf.set_text_color(2, 132, 199) 
    pdf.cell(0, 5, f"LOTE DE EXPEDIÇÃO: {id_romaneio}", ln=True, align="C")
    pdf.set_font("Arial", "", 8); pdf.set_text_color(100, 116, 139) 
    dt_str = data_despacho if isinstance(data_despacho, str) else data_despacho.strftime('%d/%m/%Y')
    pdf.cell(0, 4, f"Data do Embarque: {dt_str} | Motorista: {str(motorista_escolhido).upper()}", ln=True, align="C")
    pdf.ln(3); pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(3)
    
    pdf.set_fill_color(15, 23, 42); pdf.set_text_color(255, 255, 255); pdf.set_font("Arial", "B", 7)
    pdf.cell(10, 5, "ITEM", 1, 0, "C", True); pdf.cell(25, 5, "PEDIDO", 1, 0, "C", True); pdf.cell(30, 5, "ID CLIENTE", 1, 0, "C", True); pdf.cell(80, 5, "PONTO DE COLETA / LABORATÓRIO", 1, 0, "C", True); pdf.cell(35, 5, "CIDADE", 1, 0, "C", True); pdf.cell(10, 5, "UF", 1, 1, "C", True)
    pdf.set_text_color(51, 65, 85); pdf.set_font("Arial", "", 7)
    
    for idx, item in enumerate(sel_lista, 1):
        fill = (idx % 2 == 0)
        pdf.set_fill_color(241, 245, 249) if fill else pdf.set_fill_color(255, 255, 255)
        qr_val = str(item.get('QR_CODE', ''))
        if qr_val.upper() == 'NAN' or not qr_val: qr_val = "-"
        pdf.cell(10, 5, str(idx), 1, 0, "C", True); pdf.cell(25, 5, str(item.get('PEDIDO','')), 1, 0, "C", True); pdf.cell(30, 5, qr_val, 1, 0, "C", True); pdf.cell(80, 5, padronizar_texto(str(item.get('LABORATORIO','')))[:48], 1, 0, "L", True); pdf.cell(35, 5, padronizar_texto(str(item.get('CIDADE','')))[:22], 1, 0, "L", True); pdf.cell(10, 5, str(item.get('UF','')), 1, 1, "C", True)
        
    pdf.ln(4); pdf.set_font("Arial", "B", 8); pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 5, f"TOTAL DE VOLUMES CONFERIDOS E EMBARCADOS: {len(sel_lista)}", ln=True, align="R")
    pdf.set_y(-25); pdf.line(20, pdf.get_y(), 90, pdf.get_y()); pdf.line(120, pdf.get_y(), 190, pdf.get_y())
    pdf.set_font("Arial", "B", 7); pdf.cell(95, 4, "ASSINATURA CADEIA (MOTORISTA)", 0, 0, "C"); pdf.cell(95, 4, "ASSINATURA EXPEDIÇÃO (BASE IGO)", 0, 1, "C")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
        pdf.output(tmp_pdf.name)
        with open(tmp_pdf.name, "rb") as f: pdf_bytes = f.read()
    return pdf_bytes

# =============================================================================
# 📊 MÓDULO GRID PRINCIPAL E SIDEBAR
# =============================================================================
if 'filtro_kpi_admin' not in st.session_state: st.session_state.filtro_kpi_admin = "TODOS"

with st.sidebar:
    st.image("https://i.postimg.cc/x84nnjjq/IGO-LOGO.png", width=160)
    st.divider()
    menu = st.radio("Navegação Operacional:", ["📊 GRID", "📝 Pedido Manual", "📥 Importações", "📥 Importação Umove", "🔬 Triagem", "📱 WhatsApp", "📁 Relatórios", "⚙️ Rotas"])
    st.markdown("<br><br><br><br><br><br>", unsafe_allow_html=True)
    st.divider()
    if st.button("🚪 Sair do Sistema", type="primary", use_container_width=True): 
        st.session_state.autenticado = False; st.rerun()

st.markdown(f"""<div class="header-container"><h2 style="margin:0; font-weight:900; font-size:24px; color:#0F172A;">Central de Controle Operacional</h2><div class='sync-status'>🟢 Online: {datetime.now(FUSO_BR).strftime('%H:%M')}</div></div>""", unsafe_allow_html=True)

if menu == "📊 GRID":
    df_raw = carregar_dados_completos(planilha_db)
    if not df_raw.empty:
        def get_detalhes(row):
            obs = str(row.get('A_OB', row.get('OBSERVACOES', ''))).strip()
            if obs and obs.upper() != 'NAN': return obs
            return "-"
        df_raw['DETALHES'] = df_raw.apply(get_detalhes, axis=1)
        
        def tratar_link_foto(x):
            x_str = str(x).strip()
            if not x_str or x_str.upper() in ['NAN', 'NONE']: return ""
            if x_str.startswith("http"): return x_str 
            return f"https://www.appsheet.com/template/gettablefileurl?appName=APPIGOLOGISTICA-153047553&tableName=App_Tarefas&fileName={x_str}"
            
        df_raw['FOTO_URL'] = df_raw['FOTO'].apply(tratar_link_foto)
        df_raw['STATUS_DISPLAY'] = df_raw.apply(calc_status_display, axis=1)
        if 'DATA_LIMITE' in df_raw.columns: df_raw['DATA_LIMITE'] = df_raw['DATA_LIMITE'].fillna("").astype(str)
        
        col_f1, col_f2 = st.columns(2)
        f_cli = col_f1.selectbox("🏢 Filtrar por Tomador:", ["Todos"] + CLIENTES_AUTORIZADOS)
        f_data = col_f2.date_input("📅 Período:", value=(hoje_br - timedelta(days=2), hoje_br), format="DD/MM/YYYY")
        
        df_f = df_raw.copy()
        if f_cli != "Todos": df_f = df_f[df_f['TOMADOR'] == f_cli]
        if isinstance(f_data, tuple) and len(f_data) == 2: df_f = df_f[(df_f['DATA_OBJ'] >= f_data[0]) & (df_f['DATA_OBJ'] <= f_data[1])]

        c1, c2, c3, c4, c5, c6 = st.columns(6)
        def set_kpi(v): st.session_state.filtro_kpi_admin = v
        c1.button(f"📦 TOTAL\n{len(df_f)}", key="kpi_total", use_container_width=True, on_click=set_kpi, args=("TODOS",))
        c2.button(f"✅ ENTREGUES\n{len(df_f[df_f['STATUS_DISPLAY'].str.contains('Entregue')])}", key="kpi_entregue", use_container_width=True, on_click=set_kpi, args=("ENTREGUE",))
        c3.button(f"⏳ PENDENTES\n{len(df_f[df_f['STATUS_DISPLAY'].str.contains('Pendente')])}", key="kpi_pend", use_container_width=True, on_click=set_kpi, args=("PENDENTE",))
        c4.button(f"❌ FRUSTRADAS\n{len(df_f[df_f['STATUS_DISPLAY'].str.contains('Frustrada')])}", key="kpi_frus", use_container_width=True, on_click=set_kpi, args=("FRUSTRADA",))
        c5.button(f"🚨 ATRASADOS\n{len(df_f[df_f['STATUS_DISPLAY'].str.contains('ATRASADO')])}", key="kpi_atra", use_container_width=True, on_click=set_kpi, args=("ATRASADO",))
        c6.button(f"📅 HOJE\n{len(df_f[df_f['DATA_OBJ'] == hoje_br])}", key="kpi_hoje", use_container_width=True, on_click=set_kpi, args=("HOJE",))

        st.markdown("<br>", unsafe_allow_html=True)
        busca = st.text_input("🔎 Busca Rápida:", placeholder="Filtrar dados...")
        
        df_grid = df_f.copy()
        if st.session_state.filtro_kpi_admin != "TODOS":
            if st.session_state.filtro_kpi_admin == "HOJE": df_grid = df_grid[df_grid['DATA_OBJ'] == hoje_br]
            else: df_grid = df_grid[df_grid['STATUS_DISPLAY'].str.contains(st.session_state.filtro_kpi_admin, case=False)]
        
        df_grid['COMPROVANTE'] = df_grid['FOTO_URL']

        def definir_prioridade(status_str):
            s = str(status_str).upper()
            if 'PENDENTE' in s: return 1
            if 'COLETADO' in s: return 2
            if 'CONFERIDO' in s: return 3
            if 'ROTA' in s: return 4
            if 'ENTREGUE' in s: return 5
            return 6 
            
        df_grid['PRIORIDADE'] = df_grid['STATUS_DISPLAY'].apply(definir_prioridade)
        df_grid = df_grid.sort_values(by=['PRIORIDADE', 'PEDIDO'], ascending=[True, False]).drop(columns=['PRIORIDADE'])
        if busca: df_grid = df_grid[df_grid.astype(str).apply(lambda x: busca.upper() in x.str.upper().values, axis=1)]

        dict_nomes_grid = {str(r.get('LOGIN DO AGENTE', '')).strip().lower(): str(r.get('NOME DO AGENTE', '')).strip() for _, r in DF_AGENTES.iterrows() if str(r.get('LOGIN DO AGENTE', '')).strip()}
        df_grid['AGENTE_NOME'] = df_grid['AGENTE_RAW'].apply(lambda x: dict_nomes_grid.get(str(x).strip().lower(), str(x).upper()) if str(x).strip() else "")

        colunas_mostrar = ['DATA', 'PEDIDO', 'TOMADOR', 'LABORATORIO', 'CIDADE', 'STATUS_DISPLAY', 'DATA_LIMITE', 'DATA_ENTREGA', 'DETALHES', 'COMPROVANTE', 'AGENTE_NOME', 'AGENTE_RAW']
        
        df_grid_final = df_grid[[c for c in colunas_mostrar if c in df_grid.columns]].dropna(subset=['PEDIDO'])
            
        df_grid_final = df_grid_final[df_grid_final['PEDIDO'].astype(str).str.strip() != ""] 
        for col in df_grid_final.columns: df_grid_final[col] = df_grid_final[col].astype(str).replace(["nan", "NaN", "None", "none", "<NA>", "NaT"], "")
        
        df_grid_final['COMPROVANTE'] = df_grid_final['COMPROVANTE'].apply(lambda x: x if str(x).startswith("http") else "")
        df_grid_final = df_grid_final.reset_index(drop=True)
        df_grid_final.insert(0, "SELECIONAR", False)

        st.markdown(f"<p style='color:#64748B; font-size:13px; margin-bottom: 5px;'>Selecione as caixinhas na tabela para liberar os botões de ação. Clique no link FOTO para abrir a imagem original.</p>", unsafe_allow_html=True)
        box_botoes = st.empty()

        tabela_renderizada = st.data_editor(
            df_grid_final,
            column_config={
                "SELECIONAR": st.column_config.CheckboxColumn("✔ AÇÃO", default=False),
                "STATUS_DISPLAY": st.column_config.TextColumn("STATUS"),
                "DETALHES": st.column_config.TextColumn("DETALHES / MOTIVO", width="large"),
                "COMPROVANTE": st.column_config.LinkColumn("FOTO", display_text="🔎 Abrir Foto"),
                "AGENTE_NOME": st.column_config.TextColumn("MOTORISTA"), 
                "AGENTE_RAW": None, 
                "DATA_ENTREGA": st.column_config.TextColumn("ENTREGA"),
                "DATA_LIMITE": st.column_config.TextColumn("PREVISÃO"),
                "DATA": st.column_config.TextColumn("DATA"),
                "PEDIDO": st.column_config.TextColumn("PEDIDO"),
                "TOMADOR": st.column_config.TextColumn("TOMADOR"),
                "LABORATORIO": st.column_config.TextColumn("LABORATÓRIO"),
                "CIDADE": st.column_config.TextColumn("CIDADE")
            },
            disabled=[c for c in df_grid_final.columns if c != "SELECIONAR"],
            hide_index=True,
            use_container_width=True,
            height=500,
            key="tabela_nativa_indestrutivel_final" 
        )

        linhas_selecionadas = tabela_renderizada[tabela_renderizada["SELECIONAR"]]
        p_ids = linhas_selecionadas["PEDIDO"].astype(str).tolist() if not linhas_selecionadas.empty else []
        tem_sel = len(p_ids) > 0

        with box_botoes.container():
            col_b1, col_b2, col_b3, col_b4, col_b5, col_b6, col_b7 = st.columns(7)
            
            with col_b1.popover("🛎️ Cobrar Agente", use_container_width=True):
                if not tem_sel: st.warning("Selecione um pedido!")
                else:
                    with st.form("form_cobrar_grid"):
                        st.markdown("Enviar lembrete amigável?")
                        if st.form_submit_button("📲 Mandar Cobrança Agora", type="primary", use_container_width=True):
                            agentes_selecionados = list(set(linhas_selecionadas['AGENTE_RAW'].tolist()))
                            for ag in agentes_selecionados:
                                login_ag = str(ag).lower().strip()
                                tel_row = DF_AGENTES[DF_AGENTES['LOGIN DO AGENTE'] == login_ag]
                                if not tel_row.empty:
                                    tel = tel_row.iloc[0]['TELEFONE']
                                    nome = tel_row.iloc[0]['NOME DO AGENTE']
                                    qtd_ag = len(linhas_selecionadas[linhas_selecionadas['AGENTE_RAW'] == ag])
                                    msg_ind = f"Olá {nome}, a IGO Logística informa que você possui {qtd_ag} pedidos pendentes na rota de hoje. Lembre-se de dar baixa. Bom trabalho!"
                                    if enviar_whatsapp_zapi(tel, msg_ind): st.success(f"Enviado para {nome}!")
                                    else: st.error(f"Erro ao enviar para {nome}")
                                else: st.error(f"Telefone do agente {login_ag} não encontrado.")

            with col_b2.popover("📲 Baixa Manual", use_container_width=True):
                if not tem_sel: st.warning("Selecione um pedido!")
                else:
                    with st.form("form_baixa_manual"):
                        status_baixa = st.selectbox("Novo Status:", ["ENTREGUE ✅", "PROBLEMA 🚨", "CANCELADO ❌", "PENDENTE ⏳"])
                        data_baixa = st.date_input("Data:", format="DD/MM/YYYY", value=hoje_br)
                        tem_entregue = df_f[df_f['PEDIDO'].isin(p_ids)]['STATUS_DISPLAY'].str.contains('Entregue').any()
                        senha_reversao = ""
                        if tem_entregue:
                            st.warning("⚠️ Desfazendo pedido já **ENTREGUES**.")
                            senha_reversao = st.text_input("🔑 Senha:", type="password")
                        if st.form_submit_button("Confirmar Nova Baixa", type="primary", use_container_width=True):
                            with st.spinner("Atualizando status no banco de dados..."):
                                status_limpo = status_baixa.split(" ")[0].upper()
                                if tem_entregue and status_limpo != 'ENTREGUE' and senha_reversao != '123': st.error("❌ Senha incorreta!")
                                else:
                                    try:
                                        aba = planilha_db.worksheet("Memoria_Sistema")
                                        df_nuvem = pd.DataFrame(aba.get_all_values()[1:], columns=aba.get_all_values()[0])
                                        for pid in p_ids:
                                            mask = df_nuvem['PEDIDO'] == pid
                                            df_nuvem.loc[mask, 'STATUS'] = status_limpo
                                            if status_limpo == "ENTREGUE": df_nuvem.loc[mask, 'DATA_ENTREGA'] = data_baixa.strftime("%d/%m/%Y")
                                            elif status_limpo == "PENDENTE": df_nuvem.loc[mask, 'DATA_ENTREGA'] = ""
                                        aba.clear()
                                        aba.update("A1", [df_nuvem.columns.tolist()] + df_nuvem.fillna("").astype(str).values.tolist())
                                        st.success("🎉 Atualizado!")
                                        time.sleep(1); carregar_dados_completos.clear(); st.rerun()
                                    except Exception as e: st.error(f"Erro: {e}")

            with col_b3.popover("🔄 Trocar Agente", use_container_width=True):
                if not tem_sel: st.warning("Selecione um pedido!")
                else:
                    with st.form("form_troca_motorista"):
                        tem_entregue = df_f[df_f['PEDIDO'].isin(p_ids)]['STATUS_DISPLAY'].str.contains('Entregue').any()
                        if tem_entregue: st.error("⚠️ Impossível trocar motorista de ENTREGUES.")
                        else:
                            logins_disp = sorted(DF_AGENTES['LOGIN DO AGENTE'].unique().tolist()) if not DF_AGENTES.empty else []
                            novo_mot = st.selectbox("Novo Agente:", logins_disp)
                            nova_data_troca = st.date_input("Nova Data:", format="DD/MM/YYYY", value=hoje_br)
                            if st.form_submit_button("Confirmar Troca", type="primary", use_container_width=True):
                                with st.spinner("Atualizando rotas e motoristas..."):
                                    try:
                                        aba = planilha_db.worksheet("Memoria_Sistema")
                                        df_nuvem = pd.DataFrame(aba.get_all_values()[1:], columns=aba.get_all_values()[0])
                                        if 'ZAP_ENVIADO' not in df_nuvem.columns: df_nuvem['ZAP_ENVIADO'] = ""
                                        lista_app_troca = []
                                        for pid in p_ids:
                                            mask = df_nuvem['PEDIDO'] == pid
                                            if mask.any():
                                                df_nuvem.loc[mask, 'AGENTE_RAW'] = novo_mot
                                                df_nuvem.loc[mask, 'STATUS'] = "PENDENTE"
                                                df_nuvem.loc[mask, 'DATA'] = nova_data_troca.strftime("%d/%m/%Y")
                                                df_nuvem.loc[mask, 'ZAP_ENVIADO'] = "" 
                                                l_app = df_nuvem[mask].iloc[0]
                                                lista_app_troca.append({'PEDIDO': pid, 'MOTORISTA': novo_mot, 'ENDERECO': l_app.get('ENDERECO',''), 'NUMERO': l_app.get('NUMERO',''), 'BAIRRO': l_app.get('BAIRRO',''), 'CIDADE': l_app.get('CIDADE',''), 'CEP': l_app.get('CEP',''), 'LABORATORIO': l_app.get('LABORATORIO',''), 'TOMADOR': l_app.get('TOMADOR','')})
                                        aba.clear()
                                        aba.update("A1", [df_nuvem.columns.tolist()] + df_nuvem.fillna("").astype(str).values.tolist())
                                        if lista_app_troca: despachar_para_appsheet(lista_app_troca)
                                        st.success("🎉 Troca realizada!")
                                        time.sleep(1); carregar_dados_completos.clear(); st.rerun()
                                    except Exception as e: st.error(f"Erro: {e}")

            with col_b4.popover("👯 Clonar Pedidos", use_container_width=True):
                if not tem_sel: st.warning("Selecione um pedido!")
                else:
                    with st.form("form_clonar_pedido"):
                        clone_data = st.date_input("Nova Data de Embarque:", format="DD/MM/YYYY", value=hoje_br)
                        logins_disp = sorted(DF_AGENTES['LOGIN DO AGENTE'].unique().tolist()) if not DF_AGENTES.empty else []
                        clone_mot = st.selectbox("Agente Designado:", ["Manter Original"] + logins_disp)
                        if st.form_submit_button("Confirmar Clone", type="primary"):
                            with st.spinner("👯 Clonando pedidos e roteirizando..."):
                                try:
                                    aba = planilha_db.worksheet("Memoria_Sistema")
                                    df_nuvem = pd.DataFrame(aba.get_all_values()[1:], columns=aba.get_all_values()[0])
                                    if 'ZAP_ENVIADO' not in df_nuvem.columns: df_nuvem['ZAP_ENVIADO'] = ""
                                    prox_id = obter_proximo_id(df_nuvem)
                                    clones_app = []
                                    for pid in p_ids:
                                        if pid in df_nuvem['PEDIDO'].values:
                                            l_orig = df_nuvem[df_nuvem['PEDIDO'] == pid].iloc[0].copy()
                                            novo_id = str(prox_id); prox_id += 1
                                            l_orig['PEDIDO'] = novo_id; l_orig['DATA'] = clone_data.strftime("%d/%m/%Y")
                                            l_orig['STATUS'] = "PENDENTE"; l_orig['DATA_ENTREGA'] = ""; l_orig['FOTO'] = ""; l_orig['ROMANEIO'] = ""; l_orig['ZAP_ENVIADO'] = ""
                                            if clone_mot != "Manter Original": l_orig['AGENTE_RAW'] = clone_mot
                                            prazo = calcular_sla_dias(str(l_orig.get('UF', 'SP')), str(l_orig.get('CIDADE', '')))
                                            l_orig['PRAZO_DIAS'] = str(prazo); l_orig['DATA_LIMITE'] = str(calcular_data_limite(l_orig['DATA'], prazo))
                                            l_orig = l_orig.astype(str)
                                            df_nuvem = pd.concat([df_nuvem, pd.DataFrame([l_orig])], ignore_index=True)
                                            if str(l_orig.get('AGENTE_RAW','')).strip():
                                                clones_app.append({'PEDIDO': novo_id, 'MOTORISTA': l_orig['AGENTE_RAW'], 'ENDERECO': l_orig.get('ENDERECO',''), 'NUMERO': l_orig.get('NUMERO',''), 'BAIRRO': l_orig.get('BAIRRO',''), 'CIDADE': l_orig.get('CIDADE',''), 'CEP': l_orig.get('CEP',''), 'LABORATORIO': l_orig.get('LABORATORIO',''), 'TOMADOR': l_orig.get('TOMADOR','')})
                                    aba.clear()
                                    aba.update("A1", [df_nuvem.columns.tolist()] + df_nuvem.fillna("").astype(str).values.tolist())
                                    if clones_app: despachar_para_appsheet(clones_app)
                                    st.success("🎉 Clonado!"); time.sleep(1); carregar_dados_completos.clear(); st.rerun()
                                except Exception as e: st.error(f"Erro: {e}")

            with col_b5.popover("🗑️ Excluir", use_container_width=True):
                if not tem_sel: st.warning("Selecione um pedido!")
                else:
                    with st.form("form_excluir_grid"):
                        senha_del = st.text_input("🔑 Senha Master:", type="password")
                        if st.form_submit_button("Confirmar Exclusão"):
                            if senha_del == "123":
                                with st.spinner("Apagando registros do banco..."):
                                    try:
                                        aba = planilha_db.worksheet("Memoria_Sistema")
                                        df_nuvem = pd.DataFrame(aba.get_all_values()[1:], columns=aba.get_all_values()[0])
                                        df_nuvem = df_nuvem[~df_nuvem['PEDIDO'].isin(p_ids)]
                                        aba.clear()
                                        aba.update("A1", [df_nuvem.columns.tolist()] + df_nuvem.fillna("").astype(str).values.tolist())
                                        try:
                                            aba_app = planilha_db.worksheet("App_Tarefas")
                                            df_app = pd.DataFrame(aba_app.get_all_values()[1:], columns=aba_app.get_all_values()[0])
                                            df_app = df_app[~df_app['PEDIDO'].isin(p_ids)]
                                            aba_app.clear()
                                            aba_app.update("A1", [df_app.columns.tolist()] + df_app.fillna("").astype(str).values.tolist())
                                        except Exception: pass 
                                        st.success("🗑️ Apagado!"); time.sleep(1); carregar_dados_completos.clear(); st.rerun()
                                    except Exception as e: st.error(f"Erro: {e}")

            with col_b6.popover("📱 Enviar WhatsApp", use_container_width=True):
                if not tem_sel: st.warning("Selecione os pedidos na tabela!")
                else:
                    entregues_mask = linhas_selecionadas['STATUS_DISPLAY'].str.contains('Entregue', case=False, na=False)
                    linhas_pendentes = linhas_selecionadas[~entregues_mask]
                    if linhas_pendentes.empty: st.error("⚠️ Apenas pedidos Não-Entregues podem ser enviados.")
                    else:
                        with st.form("form_zap_grid"):
                            st.markdown(f"**{len(linhas_pendentes)}** volumes válidos selecionados para envio.")
                            if st.form_submit_button("🚀 Disparar para Motorista(s)", type="primary", use_container_width=True):
                                with st.spinner("Enviando rotas via satélite..."):
                                    p_ids_pendentes = linhas_pendentes["PEDIDO"].astype(str).tolist()
                                    df_raw_pendentes = df_raw[df_raw['PEDIDO'].isin(p_ids_pendentes)]
                                    dict_tel = {str(r.get('LOGIN DO AGENTE', '')).strip().lower(): re.sub(r'\D', '', str(r.get('TELEFONE', ''))) for _, r in DF_AGENTES.iterrows()}
                                    dict_nom = {str(r.get('LOGIN DO AGENTE', '')).strip().lower(): str(r.get('NOME DO AGENTE', '')).strip() for _, r in DF_AGENTES.iterrows()}
                                    ag_xls = ['veloz.express', 'robson.melo', 'william.bertoldo']
                                    sucessos = 0
                                    agentes_selecionados = df_raw_pendentes['AGENTE_RAW'].dropna().unique()
                                    
                                    for ag in agentes_selecionados:
                                        if not str(ag).strip(): continue
                                        df_ag = df_raw_pendentes[df_raw_pendentes['AGENTE_RAW'] == ag]
                                        tel = dict_tel.get(str(ag).strip().lower(), "")
                                        nom = dict_nom.get(str(ag).strip().lower(), str(ag).upper())
                                        ag_login = str(ag).strip().lower()
                                        
                                        if tel:
                                            data_str = hoje_br.strftime('%d/%m/%Y')
                                            msg_parts = [f"Bom dia, {nom}", f"🗓️ {data_str}\n", "RESUMO DA ROTA:\n", "CIDADE                  | QTD", "-------------------------------"]
                                            cid_counts = df_ag['CIDADE'].value_counts()
                                            tot_qtd = 0
                                            for cid, count in cid_counts.items():
                                                msg_parts.append(f"{str(cid).strip().ljust(23)} | {count:02d}"); tot_qtd += count
                                            msg_parts.extend(["-------------------------------", f"TOTAL                   | {tot_qtd:02d}\n\n", "⬇️ DETALHES:", "========================\n"])
                                            for cid, group in df_ag.groupby('CIDADE'):
                                                msg_parts.extend(["------------------------------", f"{str(cid).strip().center(30)}", "------------------------------\n"])
                                                items = []
                                                for _, row in group.iterrows():
                                                    item_str = f"> 🔸 PEDIDO: {row.get('PEDIDO', '')}\n> 🔬 LABORATÓRIO: {row.get('LABORATORIO', '')}\n> 📍 Rua: {row.get('ENDERECO', '')}, {row.get('NUMERO', '')}\n> 🏘️ Bairro: {row.get('BAIRRO', '')}\n> 📮 CEP: {row.get('CEP', '')}\n> 🏢 Tomador: {row.get('TOMADOR', '')}"
                                                    obs = str(row.get('OBSERVACOES', '')).strip()
                                                    if obs and obs.upper() != 'NAN': item_str += f"\n> 📝 Aviso: {obs}"
                                                    items.append(item_str)
                                                msg_parts.append("\n\n      . . . . .\n\n".join(items) + "\n")
                                            msg_final = "\n".join(msg_parts)
                                            
                                            if enviar_whatsapp_zapi(tel, msg_final):
                                                time.sleep(2.0)
                                                pdf_bytes = gerar_pdf_rota_whatsapp(nom, data_str, df_ag)
                                                enviar_pdf_zapi(tel, pdf_bytes, f"ROTA_IGO_{nom.replace(' ', '_')}_{hoje_br.strftime('%d%m')}.pdf")
                                                if ag_login in ag_xls:
                                                    time.sleep(3.0)
                                                    xls_bytes = gerar_excel_rota_whatsapp(df_ag)
                                                    enviar_excel_zapi(tel, xls_bytes, f"ROTA_ESTRUTURADA_{nom.replace(' ', '_')}_{hoje_br.strftime('%d%m')}.xlsx")
                                                sucessos += 1
                                                try:
                                                    aba = planilha_db.worksheet("Memoria_Sistema")
                                                    df_nuvem = pd.DataFrame(aba.get_all_values()[1:], columns=aba.get_all_values()[0])
                                                    if 'ZAP_ENVIADO' not in df_nuvem.columns: df_nuvem['ZAP_ENVIADO'] = ""
                                                    hora_atual = datetime.now(FUSO_BR).strftime('%H:%M')
                                                    df_nuvem.loc[df_nuvem['PEDIDO'].isin(df_ag['PEDIDO'].tolist()), 'ZAP_ENVIADO'] = f"SIM|{hora_atual}"
                                                    aba.clear()
                                                    aba.update("A1", [df_nuvem.columns.tolist()] + df_nuvem.fillna("").astype(str).values.tolist())
                                                except Exception as e: st.error(f"Erro ao carimbar envio: {e}")
                                    if sucessos > 0:
                                        st.success(f"✅ Disparo concluído para {sucessos} agente(s)!")
                                        time.sleep(2.0); carregar_dados_completos.clear(); st.rerun()
                                    else: st.error("🚨 Nenhum envio realizado. Verifique os contatos.")

            col_b7.button("🔄 Atualizar", use_container_width=True, on_click=lambda: [carregar_dados_completos.clear(), st.rerun()])

# =============================================================================
# 📝 MÓDULO EXTRA: NOVO PEDIDO MANUAL
# =============================================================================
elif menu == "📝 Pedido Manual":
    st.markdown("<div class='dinamic-border'><h3 class='dinamic-text' style='margin:0;'>📝 Inserir Novo Pedido Manual</h3></div>", unsafe_allow_html=True)
    
    if 'm_rua' not in st.session_state: st.session_state['m_rua'] = ""
    if 'm_bai' not in st.session_state: st.session_state['m_bai'] = ""
    if 'm_cid' not in st.session_state: st.session_state['m_cid'] = ""
    if 'm_uf' not in st.session_state: st.session_state['m_uf'] = ""
    if 'cep_busca_input' not in st.session_state: st.session_state['cep_busca_input'] = ""

    def buscar_cep_callback():
        cep_limpo = re.sub(r'\D', '', st.session_state.cep_busca_input)
        if len(cep_limpo) == 8:
            try:
                resp = requests.get(f"https://viacep.com.br/ws/{cep_limpo}/json/").json()
                if "erro" not in resp:
                    st.session_state['m_rua'] = padronizar_texto(resp.get("logradouro", ""))
                    st.session_state['m_bai'] = padronizar_texto(resp.get("bairro", ""))
                    st.session_state['m_cid'] = padronizar_texto(resp.get("localidade", ""))
                    st.session_state['m_uf'] = padronizar_texto(resp.get("uf", ""))
            except Exception: pass

    with st.container(border=True):
        cc1, cc2, cc3 = st.columns([2, 1, 3], vertical_alignment="bottom")
        cc1.text_input("Digite o CEP e aperte ENTER", max_chars=9, key="cep_busca_input", on_change=buscar_cep_callback)
        
        if cc2.button("🔍 Buscar CEP", use_container_width=True):
            buscar_cep_callback()
        
        st.markdown("---")
        with st.form("form_manual_page", clear_on_submit=True):
            col1, col2 = st.columns(2)
            m_tomador = col1.selectbox("Laboratório Solicitante *", ["Selecione..."] + CLIENTES_AUTORIZADOS)
            m_data = col2.date_input("Data *", format="DD/MM/YYYY", value=hoje_br)
            m_lab = st.text_input("Ponto de Coleta *")
            m_cnpj = st.text_input("CNPJ / Documento (Opcional)")
            m_rua = st.text_input("Logradouro *", value=st.session_state['m_rua'])
            
            col3, col4, col5 = st.columns([2, 2, 1])
            m_bai = col3.text_input("Bairro *", value=st.session_state['m_bai'])
            m_cid = col4.text_input("Cidade *", value=st.session_state['m_cid'])
            m_uf = col5.text_input("UF *", value=st.session_state['m_uf'])
            
            logins_disp = sorted(DF_AGENTES['LOGIN DO AGENTE'].unique().tolist()) if not DF_AGENTES.empty else []
            m_agente_escolha = st.selectbox("Agente Designado:", ["Automático (Por Rota)"] + logins_disp)
            
            if st.form_submit_button("🚀 Injetar na Base", type="primary", use_container_width=True):
                if m_tomador == "Selecione..." or not m_cid or not m_lab or not m_rua or not m_bai: 
                    st.error("⚠️ Preencha todos os campos!")
                else:
                    with st.spinner("Injetando pedido no sistema..."):
                        lab_limpo, rua_limpa, bai_limpo, cid_limpa, uf_limpa = padronizar_texto(m_lab), padronizar_texto(m_rua), padronizar_texto(m_bai), padronizar_texto(m_cid), padronizar_texto(m_uf)
                        if m_agente_escolha == "Automático (Por Rota)": m_agente = obter_login_agente(cid_limpa, bai_limpo, lab_limpo, rua_limpa, DF_AGENTES)
                        else: m_agente = m_agente_escolha
                            
                        m_prazo = str(calcular_sla_dias(uf_limpa, cid_limpa))
                        m_limite = str(calcular_data_limite(m_data.strftime("%d/%m/%Y"), int(m_prazo)))
                        
                        try:
                            aba_memoria = planilha_db.worksheet("Memoria_Sistema")
                            dados_atuais = aba_memoria.get_all_values()
                            df_nuvem = pd.DataFrame(dados_atuais[1:], columns=dados_atuais[0]) if len(dados_atuais) > 1 else pd.DataFrame()
                            
                            if 'ZAP_ENVIADO' not in df_nuvem.columns: df_nuvem['ZAP_ENVIADO'] = ""
                            if 'CNPJ' not in df_nuvem.columns: df_nuvem['CNPJ'] = ""
                                
                            m_pedido = str(obter_proximo_id(df_nuvem))
                            
                            novo_ped_dict = {
                                'DATA': m_data.strftime("%d/%m/%Y"), 'PEDIDO': m_pedido, 'TOMADOR': m_tomador, 
                                'LABORATORIO': lab_limpo, 'CNPJ': padronizar_texto(m_cnpj), 'ENDERECO': rua_limpa, 'NUMERO': "", 
                                'BAIRRO': bai_limpo, 'CIDADE': cid_limpa, 'UF': uf_limpa, 
                                'CEP': re.sub(r'\D', '', st.session_state.cep_busca_input), 'STATUS': 'PENDENTE', 
                                'AGENTE_RAW': m_agente, 'PRAZO_DIAS': m_prazo, 'DATA_LIMITE': m_limite, 
                                'DATA_ENTREGA': "", 'FOTO': "", 'ROMANEIO': "", 'ZAP_ENVIADO': ""
                            }
                            
                            novo_ped = pd.DataFrame([novo_ped_dict]).astype(str)
                            df_atual = pd.concat([df_nuvem, novo_ped], ignore_index=True) if not df_nuvem.empty else novo_ped
                            aba_memoria.clear()
                            aba_memoria.update("A1", [df_atual.columns.tolist()] + df_atual.fillna("").astype(str).values.tolist())
                            
                            if m_agente: despachar_para_appsheet([novo_ped.iloc[0].to_dict()])
                            
                            st.balloons()
                            st.success(f"🎉 Pedido {m_pedido} criado com sucesso!")
                            time.sleep(3.5)
                            
                            carregar_dados_completos.clear()
                            st.session_state['m_rua'] = ""; st.session_state['m_bai'] = ""; st.session_state['m_cid'] = ""; st.session_state['m_uf'] = ""; st.session_state['cep_busca_input'] = ""
                            st.rerun()
                        except Exception as e: st.error(f"Erro: {e}")

# =============================================================================
# ➕ MÓDULO 2: IMPORTAÇÃO DE LOTES (OFICIAL)
# =============================================================================
elif menu == "📥 Importações":
    st.markdown("<div class='dinamic-border'><h3 class='dinamic-text' style='margin:0;'>➕ Central de Importação de Lotes (Oficial)</h3></div>", unsafe_allow_html=True)
    if "df_preview_oficial" not in st.session_state: st.session_state.df_preview_oficial = pd.DataFrame()
        
    with st.container(border=True):
        st.markdown("#### 1. Mapeamento de Planilha e Colagem")
        c1, c2, c3 = st.columns([1, 1, 2])
        with c1: tom = st.selectbox("🏢 Tomador Central:", ["Selecione..."] + CLIENTES_AUTORIZADOS)
        with c2: dt_c = st.date_input("📅 Data da Rota:", format="DD/MM/YYYY", value=hoje_br)
            
        txt = st.text_area("📋 Cole os dados (Ctrl+V):", height=150)
        
        if st.columns([1, 2])[0].button("🔍 1. Processar Matriz", type="primary", use_container_width=True):
            if not txt or tom == "Selecione...": st.warning("Preencha o Tomador e cole os dados!")
            else:
                with st.spinner("⏳ Processando dados da planilha..."):
                    try:
                        delim = '\t' if '\t' in txt else (';' if ';' in txt else ',')
                        df_raw_import = pd.read_csv(io.StringIO(txt), sep=delim, header=None, dtype=str).fillna("")
                        idx_h, max_matches = 0, 0
                        for i in range(min(15, len(df_raw_import))):
                            row_str = unicodedata.normalize('NFKD', " ".join(df_raw_import.iloc[i].astype(str).values).upper()).encode('ASCII', 'ignore').decode('utf-8')
                            matches = sum(1 for kw in ['PEDIDO', 'CODIGO', 'CNPJ', 'CPF', 'DOCUMENTO', 'DOC', 'ID', 'CIDADE', 'MUNIC', 'LABORAT', 'POSTO', 'NOME', 'CLIENTE', 'ENDERE', 'RUA', 'BAIRRO', 'CEP'] if kw in row_str)
                            if matches > max_matches: max_matches, idx_h = matches, i
                                
                        df_limpo = df_raw_import.iloc[idx_h+1:].copy()
                        df_limpo.columns = [str(c).strip() for c in df_raw_import.iloc[idx_h].values]
                        df_limpo = df_limpo.loc[:, ~df_limpo.columns.duplicated()] 
                        
                        for col in df_limpo.columns: df_limpo[col] = df_limpo[col].apply(tratar_texto_global)
                            
                        mapa = {}
                        for c in df_limpo.columns:
                            c_upper = str(c).upper().strip()
                            cl = ''.join(e for e in unicodedata.normalize('NFKD', c_upper).encode('ASCII', 'ignore').decode('utf-8') if e.isalnum()) 
                            
                            if c_upper in ['Nº', 'N°', 'N.', 'N', 'NUM', 'NUMERO', 'NRO'] or cl in ['N', 'NO', 'NR', 'NUM', 'NUMERO']: mapa[c] = 'NUMERO'
                            elif any(x in cl for x in ['PEDIDO', 'SOLICITA', 'CODIGO', 'CDIGO']) or cl == 'ID': mapa[c] = 'PEDIDO'
                            elif any(x in cl for x in ['CNPJ', 'CPF', 'DOCUMENTO', 'DOC']): mapa[c] = 'CNPJ' 
                            elif any(x in cl for x in ['LABORAT', 'CLINIC', 'POSTO', 'NOME', 'CLIENTE']): mapa[c] = 'LABORATORIO'
                            elif any(x in cl for x in ['ENDERE', 'RUA', 'LOGRADOURO', 'AVENIDA']): mapa[c] = 'ENDERECO'
                            elif 'BAIRRO' in cl: mapa[c] = 'BAIRRO'
                            elif any(x in cl for x in ['CIDADE', 'MUNIC']): mapa[c] = 'CIDADE'
                            elif any(x in cl for x in ['ESTADO', 'UF']): mapa[c] = 'UF'
                            elif 'CEP' in cl: mapa[c] = 'CEP'
                                
                        df_limpo.rename(columns=mapa, inplace=True)
                        
                        for c in ['PEDIDO', 'LABORATORIO', 'CNPJ', 'CEP', 'ENDERECO', 'NUMERO', 'BAIRRO', 'CIDADE', 'UF']:
                            if c not in df_limpo.columns: df_limpo[c] = ""
                                
                        df_limpo['PEDIDO'] = ""
                            
                        for idx, row in df_limpo.iterrows():
                            e, n, b = str(row['ENDERECO']), str(row['NUMERO']), str(row['BAIRRO'])
                            if e and (not n or not b):
                                cep_m = re.search(r'(\d{5}-?\d{3})', e)
                                if cep_m: 
                                    df_limpo.at[idx, 'CEP'] = cep_m.group(1)
                                    e = e.replace(cep_m.group(1), '').strip(' ,-')
                                if ',' in e and not n: 
                                    pts = e.split(',')
                                    df_limpo.at[idx, 'ENDERECO'], df_limpo.at[idx, 'NUMERO'] = pts[0].strip(), pts[1].strip()
                                    
                        df_limpo['UF'] = df_limpo['UF'].astype(str).str.upper().str.strip()
                        df_limpo['CIDADE'] = df_limpo['CIDADE'].astype(str).str.upper().str.strip()
                        df_limpo['TOMADOR'] = tom
                        df_limpo['DATA'] = dt_c.strftime("%d/%m/%Y")
                        df_limpo['AGENTE_RAW'] = df_limpo.apply(lambda r: obter_login_agente(r['CIDADE'], r['BAIRRO'], r['LABORATORIO'], r['ENDERECO'], DF_AGENTES), axis=1)
                        
                        st.session_state.df_preview_oficial = df_limpo[df_limpo['LABORATORIO'].str.strip() != ""][['DATA', 'TOMADOR', 'PEDIDO', 'LABORATORIO', 'CNPJ', 'ENDERECO', 'NUMERO', 'BAIRRO', 'CIDADE', 'UF', 'CEP', 'AGENTE_RAW']]
                        st.success("✅ Processamento Concluído!")
                        time.sleep(1); st.rerun()
                    except Exception as e: st.error(f"Erro no processamento: {e}")

    if not st.session_state.df_preview_oficial.empty:
        st.markdown("---")
        col_tit, col_canc = st.columns([4, 1], vertical_alignment="center")
        col_tit.markdown("### 👀 2. Preview de Carga Oficial")
        if col_canc.button("❌ Cancelar / Limpar", type="secondary", use_container_width=True, key="canc_oficial"):
            st.session_state.df_preview_oficial = pd.DataFrame(); st.rerun()

        df_preview = st.session_state.df_preview_oficial
        mask_err = (df_preview['AGENTE_RAW'].astype(str).str.strip() == "") | (df_preview['AGENTE_RAW'].astype(str).str.upper() == "NAN")
        df_err = df_preview[mask_err]; df_ok = df_preview[~mask_err]

        if not df_err.empty:
            st.error(f"🚨 **Atenção:** {len(df_err)} pedido(s) sem motorista. Corrija abaixo.")
            with st.form("form_correcao_agentes_of"):
                correcoes = {}; logins_disp = sorted(DF_AGENTES['LOGIN DO AGENTE'].unique().tolist()) if not DF_AGENTES.empty else []
                for idx, row in df_err.iterrows():
                    st.markdown(f"**Local:** {row['LABORATORIO']} | **Cidade:** {row['CIDADE']}")
                    correcoes[idx] = st.selectbox(f"Motorista:", ["Selecione..."] + logins_disp, key=f"fix_mot_of_{idx}")
                if st.form_submit_button("💾 Validar", type="primary"):
                    for idx, novo_mot in correcoes.items():
                        if novo_mot != "Selecione...": st.session_state.df_preview_oficial.at[idx, 'AGENTE_RAW'] = novo_mot
                    st.rerun()
        else:
            st.success(f"✅ Lote validado! {len(df_ok)} pedidos prontos.")
            st.dataframe(df_ok, hide_index=True)
            if st.button("🚀 3. INJETAR LOTE OFICIAL", type="primary", key="inj_oficial"):
                with st.spinner("🚀 Injetando lotes no banco de dados principal..."):
                    try:
                        aba = planilha_db.worksheet("Memoria_Sistema")
                        atuais = aba.get_all_values()
                        df_up = pd.DataFrame(atuais[1:], columns=atuais[0]) if len(atuais) > 1 else pd.DataFrame()
                        
                        if 'ZAP_ENVIADO' not in df_up.columns: df_up['ZAP_ENVIADO'] = ""
                        if 'CNPJ' not in df_up.columns: df_up['CNPJ'] = ""
                        
                        prox_id = obter_proximo_id(df_up)
                        for idx, row in df_ok.iterrows():
                            if not str(row['PEDIDO']).strip(): 
                                df_ok.at[idx, 'PEDIDO'] = str(prox_id); prox_id += 1
                                
                        df_ok['PRAZO_DIAS'] = df_ok.apply(lambda r: str(calcular_sla_dias(r['UF'], r['CIDADE'])), axis=1)
                        df_ok['DATA_LIMITE'] = df_ok.apply(lambda r: str(calcular_data_limite(r['DATA'], int(r['PRAZO_DIAS']))), axis=1)
                        df_ok['STATUS'] = 'PENDENTE'; df_ok['DATA_ENTREGA'] = ''; df_ok['FOTO'] = ''; df_ok['ROMANEIO'] = ''; df_ok['ZAP_ENVIADO'] = ''
                        
                        df_ok = df_ok.astype(str)
                        df_up = pd.concat([df_up, df_ok], ignore_index=True) if not df_up.empty else df_ok
                        aba.clear()
                        aba.update("A1", [df_up.columns.tolist()] + df_up.fillna("").astype(str).values.tolist())
                        
                        lista_app = []
                        for _, r in df_ok.iterrows():
                            if str(r.get('AGENTE_RAW','')).strip():
                                dict_app = {
                                    'PEDIDO': r['PEDIDO'], 'MOTORISTA': r['AGENTE_RAW'], 
                                    'ENDERECO': r['ENDERECO'], 'NUMERO': r['NUMERO'], 
                                    'BAIRRO': r['BAIRRO'], 'CIDADE': r['CIDADE'], 
                                    'CEP': r['CEP'], 'LABORATORIO': r['LABORATORIO'], 
                                    'TOMADOR': r['TOMADOR']
                                }
                                lista_app.append(dict_app)
                        if lista_app: despachar_para_appsheet(lista_app)
                        
                        st.balloons()
                        st.success(f"🎉 SUCESSO! {len(df_ok)} pedidos importados no C.C.O.")
                        time.sleep(3.5) 
                        
                        st.session_state.df_preview_oficial = pd.DataFrame(); carregar_dados_completos.clear(); st.rerun()
                    except Exception as e: st.error(f"Erro: {e}")

# =============================================================================
# 🔥 MÓDULO SANDBOX (PARALELO): IMPORTAÇÃO UMOVE 🔥
# =============================================================================
elif menu == "📥 Importação Umove":
    st.markdown("<div class='dinamic-border'><h3 class='dinamic-text' style='margin:0;'>🛠️ Laboratório de Testes (Sandbox Umove)</h3></div>", unsafe_allow_html=True)
    st.info("🔒 **Ambiente Blindado (Carrinho):** Processe vários Tomadores. Eles serão acumulados aqui antes da geração dos arquivos e disparo do WhatsApp.")
    
    if planilha_sandbox is None:
        st.error("❌ Não foi possível conectar com a planilha 'Import_Umove' no Drive. Verifique as permissões.")
        st.stop()
        
    if "df_sandbox_mem" not in st.session_state: 
        st.session_state.df_sandbox_mem = pd.DataFrame()

    with st.container(border=True):
        st.markdown("#### 1. Colagem da Matriz do Cliente")
        c1_sb, c2_sb, c3_sb = st.columns([1, 1, 2])
        with c1_sb: tom_sandbox = st.selectbox("🏢 Tomador Desta Carga:", ["Selecione..."] + CLIENTES_AUTORIZADOS, key="tom_sb")
        with c2_sb: dt_sandbox = st.date_input("📅 Data da Rota:", format="DD/MM/YYYY", value=hoje_br, key="dt_sb")
            
        txt_sb = st.text_area("📋 Cole os dados (Ctrl+V) do sistema legado:", height=150, key="txt_sb")

        if st.columns([1, 2])[0].button("➕ Adicionar ao Carrinho de Importação", type="primary", use_container_width=True):
            if not txt_sb or tom_sandbox == "Selecione...":
                st.warning("⚠️ Preencha o Tomador e cole os dados!")
            else:
                with st.spinner("Processando e empilhando dados..."):
                    try:
                        # 1. Recupera o Contador da Nuvem
                        prox_id_sb = 700000
                        try:
                            aba_contador = planilha_sandbox.worksheet("Contador")
                            val = aba_contador.acell('A1').value
                            if val and str(val).isdigit():
                                prox_id_sb = int(val)
                            else:
                                aba_contador.update("A1", [["700000"]])
                        except Exception:
                            if 'contador_temp' in st.session_state:
                                prox_id_sb = st.session_state.contador_temp
                            else:
                                st.session_state.contador_temp = 700000

                        delim = '\t' if '\t' in txt_sb else (';' if ';' in txt_sb else ',')
                        df_raw_sb = pd.read_csv(io.StringIO(txt_sb), sep=delim, header=None, dtype=str).fillna("")
                        
                        idx_h, max_matches = 0, 0
                        for i in range(min(15, len(df_raw_sb))):
                            row_str = unicodedata.normalize('NFKD', " ".join(df_raw_sb.iloc[i].astype(str).values).upper()).encode('ASCII', 'ignore').decode('utf-8')
                            matches = sum(1 for kw in ['PEDIDO', 'CODIGO', 'CNPJ', 'CPF', 'DOCUMENTO', 'DOC', 'ID', 'CIDADE', 'MUNIC', 'LABORAT', 'POSTO', 'NOME', 'CLIENTE', 'ENDERE', 'RUA', 'BAIRRO', 'CEP'] if kw in row_str)
                            if matches > max_matches: max_matches, idx_h = matches, i
                                
                        df_limpo_sb = df_raw_sb.iloc[idx_h+1:].copy()
                        df_limpo_sb.columns = [str(c).strip() for c in df_raw_sb.iloc[idx_h].values]
                        df_limpo_sb = df_limpo_sb.loc[:, ~df_limpo_sb.columns.duplicated()] 
                        
                        for col in df_limpo_sb.columns: df_limpo_sb[col] = df_limpo_sb[col].apply(tratar_texto_global)
                        
                        mapa_sb = {}
                        for c in df_limpo_sb.columns:
                            c_upper = str(c).upper().strip()
                            cl = ''.join(e for e in unicodedata.normalize('NFKD', c_upper).encode('ASCII', 'ignore').decode('utf-8') if e.isalnum()) 
                            
                            if c_upper in ['Nº', 'N°', 'N.', 'N', 'NUM', 'NUMERO', 'NRO'] or cl in ['N', 'NO', 'NR', 'NUM', 'NUMERO']: mapa_sb[c] = 'NUMERO'
                            elif any(x in cl for x in ['PEDIDO', 'SOLICITA', 'CODIGO', 'CDIGO']) or cl == 'ID': mapa_sb[c] = 'PEDIDO'
                            elif any(x in cl for x in ['CNPJ', 'CPF', 'DOCUMENTO', 'DOC']): mapa_sb[c] = 'CNPJ' 
                            elif any(x in cl for x in ['LABORAT', 'CLINIC', 'POSTO', 'NOME', 'CLIENTE']): mapa_sb[c] = 'LABORATORIO'
                            elif any(x in cl for x in ['ENDERE', 'RUA', 'LOGRADOURO', 'AVENIDA']): mapa_sb[c] = 'ENDERECO'
                            elif 'BAIRRO' in cl: mapa_sb[c] = 'BAIRRO'
                            elif any(x in cl for x in ['CIDADE', 'MUNIC']): mapa_sb[c] = 'CIDADE'
                            elif any(x in cl for x in ['ESTADO', 'UF']): mapa_sb[c] = 'UF'
                            elif 'CEP' in cl: mapa_sb[c] = 'CEP'
                                
                        df_limpo_sb.rename(columns=mapa_sb, inplace=True)
                        
                        for c in ['PEDIDO', 'LABORATORIO', 'CNPJ', 'CEP', 'ENDERECO', 'NUMERO', 'BAIRRO', 'CIDADE', 'UF']:
                            if c not in df_limpo_sb.columns: df_limpo_sb[c] = ""
                                
                        df_limpo_sb['PEDIDO'] = ""
                        for idx, row in df_limpo_sb.iterrows():
                            # Usa e incrementa o ID
                            df_limpo_sb.at[idx, 'PEDIDO'] = str(prox_id_sb)
                            prox_id_sb += 1
                            
                            e, n, b = str(row['ENDERECO']), str(row['NUMERO']), str(row['BAIRRO'])
                            if e and (not n or not b):
                                cep_m = re.search(r'(\d{5}-?\d{3})', e)
                                if cep_m: 
                                    df_limpo_sb.at[idx, 'CEP'] = cep_m.group(1)
                                    e = e.replace(cep_m.group(1), '').strip(' ,-')
                                if ',' in e and not n: 
                                    pts = e.split(',')
                                    df_limpo_sb.at[idx, 'ENDERECO'], df_limpo_sb.at[idx, 'NUMERO'] = pts[0].strip(), pts[1].strip()
                                    
                        df_limpo_sb['UF'] = df_limpo_sb['UF'].astype(str).str.upper().str.strip()
                        df_limpo_sb['CIDADE'] = df_limpo_sb['CIDADE'].astype(str).str.upper().str.strip()
                        df_limpo_sb['TOMADOR'] = tom_sandbox
                        df_limpo_sb['DATA'] = dt_sandbox.strftime("%d/%m/%Y")
                        
                        df_limpo_sb['AGENTE_RAW'] = df_limpo_sb.apply(lambda r: obter_login_agente(r['CIDADE'], r['BAIRRO'], r['LABORATORIO'], r['ENDERECO'], DF_AGENTES), axis=1)
                        df_final_sb = df_limpo_sb[df_limpo_sb['LABORATORIO'].str.strip() != ""][['DATA', 'TOMADOR', 'PEDIDO', 'LABORATORIO', 'CNPJ', 'ENDERECO', 'NUMERO', 'BAIRRO', 'CIDADE', 'UF', 'CEP', 'AGENTE_RAW']]
                        
                        # 2. Devolve o novo limite máximo do Contador para o Sheets
                        try:
                            aba_contador.update("A1", [[str(prox_id_sb)]])
                        except:
                            st.session_state.contador_temp = prox_id_sb

                        # 3. Lógica Cumulativa (O Carrinho)
                        if st.session_state.df_sandbox_mem.empty:
                            st.session_state.df_sandbox_mem = df_final_sb
                        else:
                            st.session_state.df_sandbox_mem = pd.concat([st.session_state.df_sandbox_mem, df_final_sb], ignore_index=True)

                        # Salva o carrinho todo no Drive
                        try:
                            aba_sb = planilha_sandbox.sheet1
                            aba_sb.clear()
                            aba_sb.update("A1", [st.session_state.df_sandbox_mem.columns.tolist()] + st.session_state.df_sandbox_mem.fillna("").astype(str).values.tolist())
                        except: pass
                        
                        st.success(f"✅ {len(df_final_sb)} pedidos do {tom_sandbox} adicionados ao carrinho!")
                        time.sleep(1); st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao processar arquivo Sandbox: {e}")

    # Painel Principal do Sandbox (Aparece se tiver algo no carrinho)
    if not st.session_state.df_sandbox_mem.empty:
        df_sb = st.session_state.df_sandbox_mem
        
        st.markdown("---")
        col_tit, col_canc = st.columns([4, 1], vertical_alignment="center")
        col_tit.markdown("### 🛒 2. Carrinho de Expedição Umove")
        if col_canc.button("🗑️ Esvaziar Carrinho (Reset)", type="secondary", use_container_width=True, key="canc_sb"):
            st.session_state.df_sandbox_mem = pd.DataFrame()
            try: planilha_sandbox.sheet1.clear()
            except: pass
            st.rerun()

        c_kpi1, c_kpi2 = st.columns([1, 4])
        total_sb = len(df_sb)
        c_kpi1.metric("TOTAL NO CARRINHO", total_sb)
        
        resumo_tom = df_sb.groupby('TOMADOR').size().reset_index(name='QTD')
        resumo_str = " | ".join([f"**{row['TOMADOR']}**: {row['QTD']}" for _, row in resumo_tom.iterrows()])
        c_kpi2.info(f"**Detalhamento por Cliente:**\n{resumo_str}")
        
        st.markdown("#### 🕵️‍♂️ Grid Interativa Cumulativa")
        st.markdown("<p style='font-size:12px; color:#64748B;'>Esta tabela exibe todos os lotes que você adicionou até agora. Dê dois cliques para corrigir agentes.</p>", unsafe_allow_html=True)
        
        df_editado_sb = st.data_editor(
            df_sb,
            num_rows="dynamic",
            use_container_width=True,
            key="grid_sandbox"
        )
        
        st.markdown("---")
        st.markdown("### 🎛️ Mesa de Comando de Saída")
        col_cmd1, col_cmd2, col_cmd3 = st.columns([1, 1, 1])
        
        # Gerador dos arquivos
        def criar_arquivos_legados(df):
            loc_lines = ["alternativeIdentifier;description;corporateName;state;city;cityNeighborhood;street;streetNumber;zipCode;CF_loc_responsavel_cliente;CF_loc_whats;CF_CNPJ;active"]
            agd_lines = ["C", "command;serviceLocal;scheduleType;activitiesOrigin;active;date;hour;situation;alternativeIdentifier;agent;CF_tar_valor"]
            
            for idx, row in df.iterrows():
                id_agd = str(row['PEDIDO'])
                tomador = str(row.get('TOMADOR', '')).upper()
                lab = str(row.get('LABORATORIO', '')).upper()
                cep = str(row.get('CEP', ''))
                
                id_loc = f"{tomador}-{lab}-{cep}"
                corp_name = f"{tomador}-{lab}"
                cnpj = str(row.get('CNPJ', ''))
                if cnpj: cnpj = f"'{cnpj}"
                
                linha_loc = f"{id_loc};{id_loc};{corp_name};{row.get('UF','')};{row.get('CIDADE','')};{row.get('BAIRRO','')};{row.get('ENDERECO','')};{row.get('NUMERO','')};{cep};{tomador};;{cnpj};1"
                loc_lines.append(linha_loc)
                
                schedule_type = "visita_tox" if "SODRE" in tomador or "INNOVATOX" in tomador or "CAEP" in tomador else "visita"
                linha_agd = f";{id_loc};{schedule_type};7;1;{row.get('DATA','')};00:10;;{id_agd};{row.get('AGENTE_RAW','')};"
                agd_lines.append(linha_agd)
                
            loc_lines_unique = [loc_lines[0]] + list(dict.fromkeys(loc_lines[1:]))
            return "\n".join(loc_lines_unique).encode('utf-8'), "\n".join(agd_lines).encode('utf-8')
            
        bytes_loc, bytes_agd = criar_arquivos_legados(df_editado_sb)
        
        with col_cmd1:
            st.download_button("💾 1. Baixar Arquivo .LOC", data=bytes_loc, file_name=f"LOC_GERAL_{dt_sandbox.strftime('%d%m%y')}.csv", mime="text/csv", use_container_width=True)
        with col_cmd2:
            st.download_button("💾 2. Baixar Arquivo .AGD", data=bytes_agd, file_name=f"AGD_GERAL_{dt_sandbox.strftime('%d%m%y')}.csv", mime="text/csv", use_container_width=True)

        with col_cmd3.popover("📲 3. Disparar WhatsApp", use_container_width=True):
            st.markdown("Isso disparará as rotas de todos os clientes no carrinho para os motoristas.")
            if st.button("🚀 Confirmar Disparos", use_container_width=True):
                with st.spinner("Enviando rotas unificadas..."):
                    dict_tel = {str(r.get('LOGIN DO AGENTE', '')).strip().lower(): re.sub(r'\D', '', str(r.get('TELEFONE', ''))) for _, r in DF_AGENTES.iterrows()}
                    dict_nom = {str(r.get('LOGIN DO AGENTE', '')).strip().lower(): str(r.get('NOME DO AGENTE', '')).strip() for _, r in DF_AGENTES.iterrows()}
                    
                    agentes_selecionados = df_editado_sb['AGENTE_RAW'].dropna().unique()
                    sucessos_sb = 0
                    
                    for ag in agentes_selecionados:
                        if not str(ag).strip(): continue
                        df_ag_sb = df_editado_sb[df_editado_sb['AGENTE_RAW'] == ag]
                        tel = dict_tel.get(str(ag).strip().lower(), "")
                        nom = dict_nom.get(str(ag).strip().lower(), str(ag).upper())
                        
                        if tel:
                            data_str = dt_sandbox.strftime('%d/%m/%Y')
                            msg_parts = [f"Bom dia, {nom}", f"🗓️ {data_str}\n", "RESUMO DA ROTA:\n", "CIDADE                  | QTD", "-------------------------------"]
                            tot_qtd = 0
                            for cid, count in df_ag_sb['CIDADE'].value_counts().items():
                                msg_parts.append(f"{str(cid).strip().ljust(23)} | {count:02d}"); tot_qtd += count
                            msg_parts.extend(["-------------------------------", f"TOTAL                   | {tot_qtd:02d}\n\n", "⬇️ DETALHES:", "========================\n"])
                            
                            for cid, group in df_ag_sb.groupby('CIDADE'):
                                msg_parts.extend(["------------------------------", f"{str(cid).strip().center(30)}", "------------------------------\n"])
                                items = []
                                for _, row in group.iterrows():
                                    item_str = f"> 🔸 PEDIDO: {row.get('PEDIDO', 'SEM NUM')}\n> 🔬 LABORATÓRIO: {row.get('LABORATORIO', '')}\n> 📍 Rua: {row.get('ENDERECO', '')}, {row.get('NUMERO', '')}\n> 🏘️ Bairro: {row.get('BAIRRO', '')}\n> 🏢 Tomador: {row.get('TOMADOR', '')}"
                                    items.append(item_str)
                                msg_parts.append("\n\n      . . . . .\n\n".join(items) + "\n")
                                
                            if enviar_whatsapp_zapi(tel, "\n".join(msg_parts)):
                                time.sleep(2.0)
                                pdf_bytes_sb = gerar_pdf_rota_whatsapp(nom, data_str, df_ag_sb)
                                enviar_pdf_zapi(tel, pdf_bytes_sb, f"ROTA_IGO_{nom.replace(' ', '_')}_{dt_sandbox.strftime('%d%m')}.pdf")
                                sucessos_sb += 1
                                
                    if sucessos_sb > 0: st.success(f"✅ Disparo Sandbox concluído para {sucessos_sb} motorista(s)!")
                    else: st.error("🚨 Nenhum envio realizado. Verifique os agentes.")

# =============================================================================
# 📋 MÓDULO 3: TRIAGEM E ROMANEIO
# =============================================================================
elif menu == "🔬 Triagem":
    st.markdown("<div class='dinamic-border'><h3 class='dinamic-text' style='margin:0;'>🔬 Terminal de Triagem e Expedição</h3></div>", unsafe_allow_html=True)
    df_raw = carregar_dados_completos(planilha_db)
    
    if not df_raw.empty:
        t1, t2, t3 = tabs(["📦 1. Validação Manual & Bipar", "🚚 2. Gerar Documento de Romaneio", "🕒 3. Histórico de Varredura"])
        
        with t1:
            st.info("💡 A auditoria de triagem aceita apenas materiais **COLETADOS** pelo aplicativo.")
            
            col_bip_esq, col_bip_dir = st.columns([1.5, 1])

            with col_bip_esq:
                with st.form("form_bip", clear_on_submit=True):
                    col_bip, col_btn = st.columns([3, 1])
                    bip_input = col_bip.text_input("🔍 Bipar QR Code de Validação:")
                    if col_btn.form_submit_button("Auditar", use_container_width=True) and bip_input:
                        termo = re.sub(r'[^A-Z0-9]', '', bip_input.upper())
                        df_raw['PED_LIMPO'] = df_raw['PEDIDO'].astype(str).str.upper().apply(lambda x: re.sub(r'[^A-Z0-9]', '', x))
                        mask = (df_raw['PED_LIMPO'] == termo)
                        if 'QR_CODE' in df_raw.columns:
                            df_raw['QR_LIMPO'] = df_raw['QR_CODE'].astype(str).str.upper().apply(lambda x: re.sub(r'[^A-Z0-9]', '', x))
                            mask = mask | (df_raw['QR_LIMPO'] == termo)
                        if mask.any():
                            idx = df_raw[mask].index[-1]
                            if str(df_raw.at[idx, 'STATUS']).strip().upper() == 'COLETADO':
                                try:
                                    aba = planilha_db.worksheet("Memoria_Sistema")
                                    df_nuvem = pd.DataFrame(aba.get_all_values()[1:], columns=aba.get_all_values()[0])
                                    mask_nuvem = df_nuvem['PEDIDO'] == str(df_raw.at[idx, 'PEDIDO'])
                                    if mask_nuvem.any():
                                        df_nuvem.loc[mask_nuvem, 'STATUS'] = 'CONFERIDO'
                                        aba.clear(); aba.update("A1", [df_nuvem.columns.tolist()] + df_nuvem.fillna("").astype(str).values.tolist())
                                        
                                        st.session_state.log_triagem.insert(0, {
                                            'PEDIDO': str(df_raw.at[idx, 'PEDIDO']),
                                            'TOMADOR': str(df_raw.at[idx, 'TOMADOR']),
                                            'CIDADE': str(df_raw.at[idx, 'CIDADE']),
                                            'HORA': datetime.now(FUSO_BR).strftime('%H:%M:%S')
                                        })
                                        
                                        st.success(f"✅ Pedido {str(df_raw.at[idx, 'PEDIDO'])} VALIDADO!")
                                        time.sleep(1.0); carregar_dados_completos.clear(); st.rerun() 
                                except Exception as e: st.error(f"Erro: {e}")
                            else: st.error("❌ Volume não está com status COLETADO.")
                        else: st.error("❌ Assinatura não reconhecida.")

            with col_bip_dir:
                st.markdown("<div style='border: 1px solid #E2E8F0; padding: 10px; border-radius: 8px; background-color: #F8FAFC; height: 130px; overflow-y: auto;'>", unsafe_allow_html=True)
                st.markdown("<p style='margin-bottom: 5px; font-weight: bold; color: #0F172A; font-size: 14px;'>⏱️ Últimos Bips Realizados:</p>", unsafe_allow_html=True)
                if st.session_state.log_triagem:
                    for item in st.session_state.log_triagem[:5]: 
                        st.markdown(f"<div style='font-size: 12px; color: #334155; margin-bottom: 3px;'>🟢 <b>{item['PEDIDO']}</b> - {item['TOMADOR']} - {item['CIDADE']} <span style='color: #94A3B8;'>({item['HORA']})</span></div>", unsafe_allow_html=True)
                else:
                    st.markdown("<p style='font-size: 12px; color: #94A3B8;'>Nenhum volume bipado ainda.</p>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("---")
            df_fila = df_raw[df_raw['STATUS'].astype(str).str.upper() == 'COLETADO'].copy()
            if not df_fila.empty:
                df_fila = df_fila[['DATA', 'PEDIDO', 'TOMADOR', 'LABORATORIO', 'CIDADE', 'STATUS']].fillna("").astype(str)
                c_sel1, c_sel2 = st.columns([1, 4])
                df_fila.insert(0, "SELECIONAR", c_sel1.checkbox("✅ Selecionar Todos", key="sel_all_val"))
                tabela_fila = st.data_editor(df_fila, hide_index=True, disabled=[c for c in df_fila.columns if c != "SELECIONAR"], use_container_width=True)
                selecionados_manuais = tabela_fila[tabela_fila["SELECIONAR"]]
                if st.button("✅ Enviar Selecionados para Despacho", type="primary"):
                    if selecionados_manuais.empty: st.warning("⚠️ Marque os pedidos primeiro!")
                    else:
                        with st.spinner("Conferindo lote..."):
                            p_ids = selecionados_manuais['PEDIDO'].astype(str).tolist()
                            try:
                                aba = planilha_db.worksheet("Memoria_Sistema")
                                df_nuvem = pd.DataFrame(aba.get_all_values()[1:], columns=aba.get_all_values()[0])
                                df_nuvem.loc[df_nuvem['PEDIDO'].isin(p_ids), 'STATUS'] = 'CONFERIDO'
                                aba.clear(); aba.update("A1", [df_nuvem.columns.tolist()] + df_nuvem.fillna("").astype(str).values.tolist())
                                st.success(f"🎉 {len(p_ids)} volumes liberados!"); time.sleep(1.5); carregar_dados_completos.clear(); st.rerun()
                            except Exception as e: st.error(f"Erro: {e}")
            else: st.info("O salão está vazio. Materiais 'Coletados' no app chegam aqui.")

        with t2:
            df_conf = df_raw[df_raw['STATUS'].astype(str).str.upper() == 'CONFERIDO'].copy()
            if not df_conf.empty:
                tomador_filtro = st.columns([1, 2])[0].selectbox("🏢 Hub de Destino (Filtro):", ["Todos"] + sorted(df_conf['TOMADOR'].astype(str).unique().tolist()))
                if tomador_filtro != "Todos": df_conf = df_conf[df_conf['TOMADOR'] == tomador_filtro]
                col_rom = ['DATA', 'PEDIDO', 'TOMADOR', 'LABORATORIO', 'CIDADE', 'UF']
                if 'QR_CODE' in df_conf.columns: col_rom.append('QR_CODE')
                df_conf_show = df_conf[col_rom].fillna("").astype(str)
                df_conf_show.insert(0, "SELECIONAR", st.columns([1, 4])[0].checkbox("✅ Selecionar Todos", key="sel_all_exp"))
                tabela_sel_exp = st.data_editor(df_conf_show, hide_index=True, disabled=[c for c in df_conf_show.columns if c != "SELECIONAR"], use_container_width=True)
                selecionados = tabela_sel_exp[tabela_sel_exp["SELECIONAR"]]
                
                st.markdown("---")
                c_mot, c_data, c_btn = st.columns([2, 1, 2])
                motorista_escolhido = c_mot.selectbox("👤 Motorista:", ["Selecione..."] + (sorted(DF_AGENTES['LOGIN DO AGENTE'].unique().tolist()) if not DF_AGENTES.empty else []))
                data_despacho = c_data.date_input("📅 Data de Embarque:", format="DD/MM/YYYY", value=hoje_br)
                
                if c_btn.button(f"🚚 Despachar Lote ({len(selecionados)} volumes)", type="primary", use_container_width=True):
                    if selecionados.empty or motorista_escolhido == "Selecione...": st.warning("⚠️ Selecione os pacotes e informe o motorista.")
                    else:
                        sel_lista = selecionados.to_dict('records')
                        tomadores_unicos = list(set([str(r.get('TOMADOR', '')).strip() for r in sel_lista]))
                        if len(tomadores_unicos) > 1: st.error(f"🚨 VIOLAÇÃO DE ROTA: Destinos diferentes selecionados ({', '.join(tomadores_unicos)}). Use o filtro no topo.")
                        else:
                            with st.spinner("Selando romaneio..."):
                                id_romaneio = f"ROM-{datetime.now().strftime('%d%m')}-{random.randint(100,999)}"
                                p_ids = [str(r['PEDIDO']) for r in sel_lista]
                                try:
                                    aba = planilha_db.worksheet("Memoria_Sistema")
                                    df_nuvem = pd.DataFrame(aba.get_all_values()[1:], columns=aba.get_all_values()[0])
                                    df_nuvem.loc[df_nuvem['PEDIDO'].isin(p_ids), ['STATUS', 'ROMANEIO', 'DATA', 'AGENTE_RAW']] = ['EM ROTA DE ENTREGA', id_romaneio, data_despacho.strftime("%d/%m/%Y"), motorista_escolhido]
                                    aba.clear(); aba.update("A1", [df_nuvem.columns.tolist()] + df_nuvem.fillna("").astype(str).values.tolist())
                                    base_tomador = tomadores_unicos[0]
                                    base_cidade = sel_lista[0].get('CIDADE', '')
                                    despachar_para_appsheet([{'PEDIDO': id_romaneio, 'MOTORISTA': motorista_escolhido, 'ENDERECO': "ENTREGA LOTE NO TOMADOR", 'NUMERO': f"{len(p_ids)} VOLUMES", 'BAIRRO': base_tomador, 'CIDADE': base_cidade, 'CEP': "---", 'LABORATORIO': f"CONJUNTO DE {len(sel_lista)} PEDIDOS", 'TOMADOR': base_tomador, 'ROMANEIO': id_romaneio}])
                                    pdf_bytes = gerar_pdf_romaneio(id_romaneio, data_despacho, motorista_escolhido, sel_lista)
                                    carregar_dados_completos.clear()
                                    st.success(f"🎉 Lote {id_romaneio} gerado com sucesso!")
                                    st.download_button(label="📥 BAIXAR PROTOCOLO TÉCNICO (PDF)", data=pdf_bytes, file_name=f"Romaneio_IGO_{id_romaneio}.pdf", mime="application/pdf", type="primary")
                                except Exception as e: st.error(f"Erro na Geração: {e}")
            else: st.info("O salão está vazio. Somente lotes validados na Triagem aparecem para despacho.")

        with t3:
            df_hist = df_raw[df_raw['STATUS'].astype(str).str.upper().isin(['CONFERIDO', 'EM ROTA DE ENTREGA', 'ENTREGUE', 'FRUSTRADA', 'PROBLEMA', 'CANCELADO'])].copy()
            if not df_hist.empty: st.dataframe(df_hist.sort_values(by=['DATA_OBJ', 'PEDIDO'], ascending=[False, False])[['DATA', 'PEDIDO', 'TOMADOR', 'LABORATORIO', 'CIDADE', 'STATUS', 'AGENTE_RAW', 'ROMANEIO']], hide_index=True, use_container_width=True)
            else: st.warning("O arquivo histórico de varreduras está temporariamente em branco.")
    else: st.info("O banco de dados está vazio no momento.")

# =============================================================================
# 📱 MÓDULO EXTRA: DISPARO WHATSAPP
# =============================================================================
elif menu == "📱 WhatsApp":
    st.markdown("<div class='dinamic-border'><h3 class='dinamic-text' style='margin:0;'>📱 Central Tática de Comunicação</h3></div>", unsafe_allow_html=True)
    df_raw = carregar_dados_completos(planilha_db)
    if not df_raw.empty:
        data_filtro = st.date_input("📅 Cronograma da Data:", value=hoje_br, format="DD/MM/YYYY")
        st.markdown("---")
        col_esq, col_dir = st.columns([2.5, 1.2])
        
        df_dia = df_raw[df_raw['DATA_OBJ'] == data_filtro].copy()
        df_pendentes = df_dia[df_dia['STATUS'].astype(str).str.upper() == 'PENDENTE'].copy()
        
        dict_telefones = {str(r.get('LOGIN DO AGENTE', '')).strip().lower(): re.sub(r'\D', '', str(r.get('TELEFONE', ''))) for _, r in DF_AGENTES.iterrows() if str(r.get('LOGIN DO AGENTE', '')).strip() and re.sub(r'\D', '', str(r.get('TELEFONE', '')))}
        dict_nomes = {str(r.get('LOGIN DO AGENTE', '')).strip().lower(): str(r.get('NOME DO AGENTE', '')).strip() for _, r in DF_AGENTES.iterrows() if str(r.get('LOGIN DO AGENTE', '')).strip()}
        agentes_xls = ['veloz.express', 'robson.melo', 'william.bertoldo']

        with col_esq:
            if df_pendentes.empty: st.success(f"Nenhum volume PENDENTE aguardando envio na data {data_filtro.strftime('%d/%m/%Y')}.")
            else:
                agentes_com_rota = [ag for ag in df_pendentes['AGENTE_RAW'].dropna().unique() if str(ag).strip()]
                agentes_para_enviar = [ag for ag in agentes_com_rota if not df_pendentes[df_pendentes['AGENTE_RAW'] == ag]['ZAP_ENVIADO'].astype(str).apply(lambda x: str(x).startswith('SIM')).all()]
                
                if agentes_para_enviar:
                    st.info(f"🚀 Existem {len(agentes_para_enviar)} motoristas aguardando o envio da rota oficial.")
                    if st.button("🚀 DISPARAR ROTAS PARA TODOS AGORA", type="primary", use_container_width=True):
                        with st.spinner("Iniciando disparos em massa..."):
                            pedidos_atualizados = []
                            sucessos = 0
                            for agente in agentes_para_enviar:
                                mask_agente = (df_pendentes['AGENTE_RAW'] == agente) & (~df_pendentes['ZAP_ENVIADO'].astype(str).apply(lambda x: str(x).startswith('SIM')))
                                df_agente = df_pendentes[mask_agente]
                                telefone = dict_telefones.get(str(agente).strip().lower(), "")
                                nome_amigavel = dict_nomes.get(str(agente).strip().lower(), str(agente).upper())
                                agente_login = str(agente).strip().lower()
                                
                                if telefone:
                                    data_str = data_filtro.strftime('%d/%m/%Y')
                                    msg_parts = [f"Bom dia, {nome_amigavel}", f"🗓️ {data_str}\n", "RESUMO DA ROTA:\n", "CIDADE                  | QTD", "-------------------------------"]
                                    cid_counts = df_agente['CIDADE'].value_counts()
                                    tot_qtd = 0
                                    for cid, count in cid_counts.items():
                                        msg_parts.append(f"{str(cid).strip().ljust(23)} | {count:02d}"); tot_qtd += count
                                    msg_parts.extend(["-------------------------------", f"TOTAL                   | {tot_qtd:02d}\n\n", "⬇️ DETALHES:", "========================\n"])
                                    for cid, group in df_agente.groupby('CIDADE'):
                                        msg_parts.extend(["------------------------------", f"{str(cid).strip().center(30)}", "------------------------------\n"])
                                        items = []
                                        for _, row in group.iterrows():
                                            item_str = f"> 🔸 PEDIDO: {row.get('PEDIDO', '')}\n> 🔬 LABORATÓRIO: {row.get('LABORATORIO', '')}\n> 📍 Rua: {row.get('ENDERECO', '')}, {row.get('NUMERO', '')}\n> 🏘️ Bairro: {row.get('BAIRRO', '')}\n> 📮 CEP: {row.get('CEP', '')}\n> 🏢 Tomador: {row.get('TOMADOR', '')}"
                                            obs = str(row.get('OBSERVACOES', '')).strip()
                                            if obs and obs.upper() != 'NAN': item_str += f"\n> 📝 Aviso: {obs}"
                                            items.append(item_str)
                                        msg_parts.append("\n\n      . . . . .\n\n".join(items) + "\n")
                                        
                                    if enviar_whatsapp_zapi(telefone, "\n".join(msg_parts)):
                                        time.sleep(2.0)
                                        pdf_bytes = gerar_pdf_rota_whatsapp(nome_amigavel, data_str, df_agente)
                                        enviar_pdf_zapi(telefone, pdf_bytes, f"ROTA_IGO_{nome_amigavel.replace(' ', '_')}_{data_filtro.strftime('%d%m')}.pdf")
                                        if agente_login in agentes_xls:
                                            time.sleep(3.0)
                                            enviar_excel_zapi(telefone, gerar_excel_rota_whatsapp(df_agente), f"ROTA_ESTRUTURADA_{nome_amigavel.replace(' ', '_')}_{data_filtro.strftime('%d%m')}.xlsx")
                                        sucessos += 1
                                        pedidos_atualizados.extend(df_agente['PEDIDO'].tolist())
                                time.sleep(1.5) 
                            
                            if pedidos_atualizados:
                                try:
                                    aba = planilha_db.worksheet("Memoria_Sistema")
                                    df_nuvem = pd.DataFrame(aba.get_all_values()[1:], columns=aba.get_all_values()[0])
                                    if 'ZAP_ENVIADO' not in df_nuvem.columns: df_nuvem['ZAP_ENVIADO'] = ""
                                    df_nuvem.loc[df_nuvem['PEDIDO'].isin(pedidos_atualizados), 'ZAP_ENVIADO'] = f"SIM|{datetime.now(FUSO_BR).strftime('%H:%M')}"
                                    aba.clear(); aba.update("A1", [df_nuvem.columns.tolist()] + df_nuvem.fillna("").astype(str).values.tolist())
                                    carregar_dados_completos.clear()
                                except Exception as e: st.error(f"Erro ao carimbar envio: {e}")
                            st.success(f"🎉 Disparo em massa concluído! {sucessos} motoristas receberam os arquivos.")
                            time.sleep(2.5); st.rerun()
                else: st.success("✅ Todos os motoristas desta data já receberam as mensagens.")
                
                st.markdown("---")
                for agente in sorted(agentes_com_rota):
                    df_agente = df_pendentes[df_pendentes['AGENTE_RAW'] == agente]
                    telefone = dict_telefones.get(str(agente).strip().lower(), "")
                    nome_amigavel = dict_nomes.get(str(agente).strip().lower(), str(agente).upper())
                    agente_login = str(agente).strip().lower()
                    todos_enviados = df_agente['ZAP_ENVIADO'].astype(str).apply(lambda x: str(x).startswith('SIM')).all()
                    
                    selo_status = '✅ ENVIADO' if todos_enviados else '⏳ PENDENTE'
                    selo_vip = ' 🌟 [RECEBE EXCEL]' if agente_login in agentes_xls else ''
                    
                    with st.expander(f"{selo_status} | 👤 {nome_amigavel}{selo_vip} | Volumes: {len(df_agente)}", expanded=not todos_enviados):
                        st.dataframe(df_agente[['PEDIDO', 'TOMADOR', 'LABORATORIO', 'CIDADE']], hide_index=True)
                        if telefone:
                            data_str = data_filtro.strftime('%d/%m/%Y')
                            msg_parts = [f"Bom dia, {nome_amigavel}", f"🗓️ {data_str}\n", "RESUMO DA ROTA:\n", "CIDADE                  | QTD", "-------------------------------"]
                            tot_qtd = 0
                            for cid, count in df_agente['CIDADE'].value_counts().items():
                                msg_parts.append(f"{str(cid).strip().ljust(23)} | {count:02d}"); tot_qtd += count
                            msg_parts.extend(["-------------------------------", f"TOTAL                   | {tot_qtd:02d}\n\n", "⬇️ DETALHES:", "========================\n"])
                            
                            for cid, group in df_agente.groupby('CIDADE'):
                                msg_parts.extend(["------------------------------", f"{str(cid).strip().center(30)}", "------------------------------\n"])
                                items = []
                                for _, row in group.iterrows():
                                    item_str = f"> 🔸 PEDIDO: {row.get('PEDIDO', '')}\n> 🔬 LABORATÓRIO: {row.get('LABORATORIO', '')}\n> 📍 Rua: {row.get('ENDERECO', '')}, {row.get('NUMERO', '')}\n> 🏘️ Bairro: {row.get('BAIRRO', '')}\n> 📮 CEP: {row.get('CEP', '')}\n> 🏢 Tomador: {row.get('TOMADOR', '')}"
                                    obs = str(row.get('OBSERVACOES', '')).strip()
                                    if obs and obs.upper() != 'NAN': item_str += f"\n> 📝 Aviso: {obs}"
                                    items.append(item_str)
                                msg_parts.append("\n\n      . . . . .\n\n".join(items) + "\n")
                                
                            botao_label = "🔄 Reenviar Arquivos" if todos_enviados else f"📲 Disparar Rota para {nome_amigavel}"
                            botao_type = "primary" if not todos_enviados else "secondary"
                            if st.button(botao_label, key=f"zap_api_ind_{agente}", type=botao_type):
                                with st.spinner("Enviando pacote completo via satélite..."):
                                    if enviar_whatsapp_zapi(telefone, "\n".join(msg_parts)):
                                        time.sleep(2.0)
                                        enviar_pdf_zapi(telefone, gerar_pdf_rota_whatsapp(nome_amigavel, data_str, df_agente), f"ROTA_IGO_{nome_amigavel.replace(' ', '_')}_{data_filtro.strftime('%d%m')}.pdf")
                                        if agente_login in agentes_xls:
                                            time.sleep(3.0)
                                            enviar_excel_zapi(telefone, gerar_excel_rota_whatsapp(df_agente), f"ROTA_ESTRUTURADA_{nome_amigavel.replace(' ', '_')}_{data_filtro.strftime('%d%m')}.xlsx")
                                        try:
                                            aba = planilha_db.worksheet("Memoria_Sistema")
                                            df_nuvem = pd.DataFrame(aba.get_all_values()[1:], columns=aba.get_all_values()[0])
                                            if 'ZAP_ENVIADO' not in df_nuvem.columns: df_nuvem['ZAP_ENVIADO'] = ""
                                            df_nuvem.loc[df_nuvem['PEDIDO'].isin(df_agente['PEDIDO'].tolist()), 'ZAP_ENVIADO'] = f"SIM|{datetime.now(FUSO_BR).strftime('%H:%M')}"
                                            aba.clear(); aba.update("A1", [df_nuvem.columns.tolist()] + df_nuvem.fillna("").astype(str).values.tolist())
                                            carregar_dados_completos.clear()
                                        except Exception as e: st.error(f"Erro ao carimbar envio: {e}")
                                        st.success(f"✅ Rota enviada para {nome_amigavel}!")
                                        time.sleep(1.5); st.rerun()
                                    else: st.error("🚨 Falha ao enviar o texto principal.")
                        else: st.error(f"⚠️ Telefone do agente '{agente}' não encontrado.")
                            
        with col_dir:
            with st.container(border=True):
                st.markdown("<h4 style='color:#0F172A; margin-top:0px; font-size:16px;'>⏱️ Log de Disparos</h4>", unsafe_allow_html=True)
                st.divider()
                log_list = []
                agentes_unicos_dia = [ag for ag in df_dia['AGENTE_RAW'].dropna().unique() if str(ag).strip()]
                for ag in agentes_unicos_dia:
                    sent_statuses = [s for s in df_dia[df_dia['AGENTE_RAW'] == ag]['ZAP_ENVIADO'].dropna().astype(str).tolist() if str(s).startswith('SIM')]
                    if sent_statuses: 
                        hora_envio = sent_statuses[0].split('|')[1] if '|' in sent_statuses[0] else "Desconhecida"
                        log_list.append({"agente": dict_nomes.get(str(ag).strip().lower(), str(ag).upper()), "hora": hora_envio})
                        
                log_list.sort(key=lambda x: x["hora"], reverse=True)
                if log_list:
                    for item in log_list:
                        st.markdown(f"<div style='padding:10px; background-color:#F8FAFC; border-left: 4px solid #10B981; margin-bottom:10px; border-radius:4px;'><b style='color:#334155; font-size:13px;'>👤 {item['agente']}</b><br><span style='color:#64748B; font-size:12px;'>✅ Enviado às {item['hora']}</span></div>", unsafe_allow_html=True)
                else: st.info("Nenhum disparo registrado.")
    else: st.warning("O banco de dados está vazio.")

# =============================================================================
# 📥 MÓDULO 4: EXPORTAR RELATÓRIOS (NOVO E INTELIGENTE)
# =============================================================================
elif menu == "📁 Relatórios":
    st.markdown("<div class='dinamic-border'><h3 class='dinamic-text' style='margin:0;'>📥 Central de Datamining e Exportação</h3></div>", unsafe_allow_html=True)
    df_raw = carregar_dados_completos(planilha_db)
    
    if not df_raw.empty:
        def get_detalhes_rel(row):
            obs = str(row.get('A_OB', row.get('OBSERVACOES', ''))).strip()
            if obs and obs.upper() != 'NAN': return obs
            return "-"
        df_raw['DETALHES'] = df_raw.apply(get_detalhes_rel, axis=1)

        # 🔥 1. FILTRO INTELIGENTE DE DATAS 🔥
        st.markdown("#### 📅 1. Selecione o Período Base")
        col_data = st.columns([1, 2])[0]
        periodo_rel = col_data.date_input("Filtro de Datas para os Relatórios:", value=(hoje_br - timedelta(days=7), hoje_br), format="DD/MM/YYYY")

        df_filtered = df_raw.copy()
        if isinstance(periodo_rel, (tuple, list)) and len(periodo_rel) == 2:
            df_filtered = df_filtered[(df_filtered['DATA_OBJ'] >= periodo_rel[0]) & (df_filtered['DATA_OBJ'] <= periodo_rel[1])]

        st.markdown("---")
        st.markdown("#### 📊 2. Extrações Rápidas (Baseado no período selecionado)")
        
        df_export_base = df_filtered[['DATA', 'PEDIDO', 'TOMADOR', 'LABORATORIO', 'ENDERECO', 'NUMERO', 'BAIRRO', 'CIDADE', 'UF', 'CEP', 'STATUS', 'DETALHES', 'DATA_ENTREGA', 'AGENTE_RAW', 'DATA_LIMITE']].copy()
        df_export_base = df_export_base.rename(columns={'AGENTE_RAW': 'MOTORISTA'})
        col_rel1, col_rel2, col_rel3 = st.columns(3)
        
        df_rj = df_export_base[df_export_base['UF'].str.upper() == 'RJ'] if 'UF' in df_export_base.columns else pd.DataFrame()
        df_jf = df_export_base[df_export_base['CIDADE'].str.upper().str.contains('JUIZ DE FORA', na=False)] if 'CIDADE' in df_export_base.columns else pd.DataFrame()
        df_rjjf = pd.concat([df_rj, df_jf]).drop_duplicates(subset=['PEDIDO'])
        if not df_rjjf.empty: col_rel1.download_button(f"📥 Extrair Bloco RJ/JF ({len(df_rjjf)} col.)", data=gerar_excel_memoria(df_rjjf), file_name=f"RJ_JF_{datetime.now(FUSO_BR).strftime('%d%m%Y')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
        else: col_rel1.button("📥 Extrair Bloco RJ/JF (Vazio)", disabled=True, use_container_width=True)
        
        df_lud = df_export_base[df_export_base['MOTORISTA'].str.lower().str.contains('ludmila|veloz', na=False)] if 'MOTORISTA' in df_export_base.columns else pd.DataFrame()
        if not df_lud.empty: col_rel2.download_button(f"📥 Extrair Ludmila/Veloz ({len(df_lud)} col.)", data=gerar_excel_memoria(df_lud), file_name=f"Ludmila_{datetime.now(FUSO_BR).strftime('%d%m%Y')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
        else: col_rel2.button("📥 Extrair Ludmila/Veloz (Vazio)", disabled=True, use_container_width=True)
        
        df_full_bkp = df_raw[['DATA', 'PEDIDO', 'TOMADOR', 'LABORATORIO', 'ENDERECO', 'NUMERO', 'BAIRRO', 'CIDADE', 'UF', 'CEP', 'STATUS', 'DETALHES', 'DATA_ENTREGA', 'AGENTE_RAW', 'DATA_LIMITE']].copy()
        df_full_bkp = df_full_bkp.rename(columns={'AGENTE_RAW': 'MOTORISTA'})
        col_rel3.download_button("☁️ Backup Completo (Toda a Nuvem)", data=gerar_excel_memoria(df_full_bkp), file_name=f"BKP_COMPLETO_{datetime.now(FUSO_BR).strftime('%d%m%Y')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary", use_container_width=True)
        
        st.markdown("---")
        st.markdown("#### 🔎 3. Pesquisa Customizada (No período selecionado)")
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
                if c_base: df_custom = df_custom[df_custom['TOMADOR'].str.upper().str.contains(c_base.upper(), na=False) | df_custom['LABORATORIO'].str.upper().str.contains(c_base.upper(), na=False)]
                
                if not df_custom.empty: 
                    st.success(f"✅ Encontrados {len(df_custom)} registros.")
                    st.download_button("📥 Fazer Download do Relatório Cru (Excel)", data=gerar_excel_memoria(df_custom), file_name=f"Pesquisa_Customizada_IGO.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary")
                else: 
                    st.warning("Nenhum dado encontrado para os filtros e período selecionados.")
    else: st.warning("O banco de dados está vazio.")

# =============================================================================
# ⚙️ MÓDULO 5: CONFIGURAR ROTAS E AGENTES
# =============================================================================
elif menu == "⚙️ Rotas":
    st.markdown("<div class='dinamic-border'><h3 class='dinamic-text' style='margin:0;'>⚙️ Matriz Inteligente de Rotas e Equipe</h3></div>", unsafe_allow_html=True)
    tab_agente, tab_rota, tab_tabela, tab_sistema = st.tabs(["👤 Cadastrar Novo Agente", "📍 Adicionar Rota (Vincular)", "📋 Gerenciar Motorista Específico", "⚠️ Sistema"])
    
    with tab_agente:
        with st.form("form_novo_agente", clear_on_submit=True):
            c1, c2 = st.columns(2)
            login_ag = c1.text_input("ID de Login", placeholder="Ex: carlos.rj")
            nome_ag = c2.text_input("Nome Amigável", placeholder="Ex: CARLOS SILVA")
            tel_ag = st.text_input("WhatsApp com DDD", placeholder="Ex: 5521999999999")
            
            if st.form_submit_button("💾 Salvar Novo Agente", type="primary"):
                if not login_ag or not nome_ag or not tel_ag: st.error("⚠️ Preencha todos os campos!")
                else:
                    df_novo = pd.concat([DF_AGENTES, pd.DataFrame([{"ROTA MAPEADA": "SEM ROTA DEFINIDA", "LOGIN DO AGENTE": login_ag.lower().strip(), "NOME DO AGENTE": nome_ag.upper().strip(), "TELEFONE": re.sub(r'\D', '', tel_ag)}])], ignore_index=True)
                    try:
                        planilha_db.worksheet("Agentes").clear()
                        planilha_db.worksheet("Agentes").update("A1", [df_novo.columns.tolist()] + df_novo.fillna("").astype(str).values.tolist())
                        st.success(f"✅ Agente salvo!"); carregar_dados_agentes.clear()
                    except Exception as e: st.error(f"Erro: {e}")
                        
    with tab_rota:
        with st.form("form_nova_rota", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            cid_rota = c1.text_input("Cidade *", placeholder="Ex: SAO PAULO")
            bai_rota = c2.text_input("Bairro (Opcional)")
            rua_rota = c3.text_input("Endereço (Opcional)")
            agentes_disponiveis = sorted(DF_AGENTES['LOGIN DO AGENTE'].unique().tolist()) if not DF_AGENTES.empty else []
            ag_selecionado = st.selectbox("Selecione o Agente:", agentes_disponiveis)
            
            if st.form_submit_button("📍 Salvar Nova Rota", type="primary"):
                if not cid_rota or not ag_selecionado: st.error("⚠️ Cidade e Agente são obrigatórios!")
                else:
                    rota_str = " ➔ ".join([p for p in [limpar_nome_local_rota(cid_rota), limpar_nome_local_rota(bai_rota), tratar_texto_global(rua_rota)] if p])
                    dados_ag = DF_AGENTES[DF_AGENTES['LOGIN DO AGENTE'] == ag_selecionado].iloc[0]
                    df_novo = pd.concat([DF_AGENTES, pd.DataFrame([{"ROTA MAPEADA": rota_str, "LOGIN DO AGENTE": ag_selecionado, "NOME DO AGENTE": dados_ag['NOME DO AGENTE'], "TELEFONE": dados_ag['TELEFONE']}])], ignore_index=True)
                    try:
                        planilha_db.worksheet("Agentes").clear()
                        planilha_db.worksheet("Agentes").update("A1", [df_novo.columns.tolist()] + df_novo.fillna("").astype(str).values.tolist())
                        st.success(f"✅ Rota atrelada!"); carregar_dados_agentes.clear()
                    except Exception as e: st.error(f"Erro: {e}")
                        
    with tab_tabela:
        if not DF_AGENTES.empty:
            agente_filtro = st.selectbox("👤 Selecione o Motorista para gerenciar:", sorted(DF_AGENTES['LOGIN DO AGENTE'].unique().tolist()))
            dados_atuais_ag = DF_AGENTES[DF_AGENTES['LOGIN DO AGENTE'] == agente_filtro].iloc[0]
            with st.expander("✏️ Editar Cadastro (Nome / Telefone)"):
                with st.form(f"form_edit_{agente_filtro}"):
                    c_edit1, c_edit2 = st.columns(2)
                    edit_nome = c_edit1.text_input("Nome Amigável", value=dados_atuais_ag['NOME DO AGENTE'])
                    edit_tel = c_edit2.text_input("WhatsApp com DDD", value=dados_atuais_ag['TELEFONE'])
                    if st.form_submit_button("💾 Salvar Alterações do Motorista", type="primary"):
                        if not edit_nome or not edit_tel: st.error("Preencha todos os campos!")
                        else:
                            df_ag_edit = DF_AGENTES.copy()
                            mask_edit = df_ag_edit['LOGIN DO AGENTE'] == agente_filtro
                            df_ag_edit.loc[mask_edit, 'NOME DO AGENTE'] = edit_nome.upper().strip()
                            df_ag_edit.loc[mask_edit, 'TELEFONE'] = re.sub(r'\D', '', edit_tel)
                            try:
                                aba_ag = planilha_db.worksheet("Agentes"); aba_ag.clear()
                                aba_ag.update("A1", [df_ag_edit.columns.tolist()] + df_ag_edit.fillna("").astype(str).values.tolist())
                                st.success("✅ Cadastro atualizado com sucesso!"); time.sleep(1); carregar_dados_agentes.clear(); st.rerun()
                            except Exception as e: st.error(f"Erro ao editar: {e}")
            
            st.markdown("---")
            st.markdown("#### 📍 Rotas Atreladas ao Motorista")
            with st.form(f"form_rapido_{agente_filtro}", clear_on_submit=True):
                ca1, ca2, ca3, ca4 = st.columns([2, 2, 2, 1])
                r_cid = ca1.text_input("Cidade")
                r_bai = ca2.text_input("Bairro (Opç)")
                r_rua = ca3.text_input("Endereço (Opç)")
                if ca4.form_submit_button("➕ Salvar", use_container_width=True):
                    if not r_cid: st.error("A Cidade é obrigatória!")
                    else:
                        rota_str = " ➔ ".join([p for p in [limpar_nome_local_rota(r_cid), limpar_nome_local_rota(r_bai), tratar_texto_global(r_rua)] if p])
                        dados_ag = DF_AGENTES[DF_AGENTES['LOGIN DO AGENTE'] == agente_filtro].iloc[0]
                        df_novo = pd.concat([DF_AGENTES, pd.DataFrame([{"ROTA MAPEADA": rota_str, "LOGIN DO AGENTE": agente_filtro, "NOME DO AGENTE": dados_ag['NOME DO AGENTE'], "TELEFONE": dados_ag['TELEFONE']}])], ignore_index=True)
                        try:
                            planilha_db.worksheet("Agentes").clear()
                            planilha_db.worksheet("Agentes").update("A1", [df_novo.columns.tolist()] + df_novo.fillna("").astype(str).values.tolist())
                            st.success("Rota adicionada!"); time.sleep(0.5); carregar_dados_agentes.clear(); st.rerun()
                        except Exception as e: st.error(f"Erro ao salvar: {e}")
                            
            df_ag_filtrado = DF_AGENTES[DF_AGENTES['LOGIN DO AGENTE'] == agente_filtro].copy()
            if df_ag_filtrado.empty: st.warning("Nenhuma rota atrelada.")
            else:
                for idx, row in df_ag_filtrado.iterrows():
                    col_rota, col_del = st.columns([5, 1])
                    col_rota.markdown(f"<div style='padding:10px; background-color:#FFFFFF; border-radius:5px; border: 1px solid #E2E8F0;'><b>📍 {row['ROTA MAPEADA'].replace('---', ' ➔ ')}</b></div>", unsafe_allow_html=True)
                    if col_del.button("🗑️ Remover", key=f"del_{idx}", use_container_width=True):
                        try:
                            planilha_db.worksheet("Agentes").clear()
                            planilha_db.worksheet("Agentes").update("A1", [DF_AGENTES.drop(idx).columns.tolist()] + DF_AGENTES.drop(idx).fillna("").astype(str).values.tolist())
                            time.sleep(0.5); carregar_dados_agentes.clear(); st.rerun()
                        except Exception as e: st.error(f"Erro ao remover: {e}")
        else: st.warning("Nenhum dado encontrado.")

    with tab_sistema:
        st.markdown("#### 🧹 Manutenção: Limpeza Inteligente de 30 Dias")
        st.info("💡 **Recomendado:** Esta ação varre o banco de dados e exclui apenas os pedidos com data superior a 30 dias.")
        with st.form("form_limpeza_30_dias"):
            senha_limpeza = st.text_input("🔑 Senha de Confirmação (Digite: 123):", type="password", key="senha_30d")
            if st.form_submit_button("🧹 REALIZAR LIMPEZA DE 30 DIAS", type="primary", use_container_width=True):
                if senha_limpeza == "123":
                    with st.spinner("Analisando linha do tempo e removendo histórico antigo..."):
                        try:
                            aba_m = planilha_db.worksheet("Memoria_Sistema")
                            dados_m = aba_m.get_all_values()
                            if len(dados_m) > 1:
                                df_m = pd.DataFrame(dados_m[1:], columns=dados_m[0])
                                df_m['DATA_TEMP'] = pd.to_datetime(df_m['DATA'], format='%d/%m/%Y', errors='coerce').dt.date
                                data_corte = hoje_br - timedelta(days=30)
                                mask_manter = (df_m['DATA_TEMP'] >= data_corte) | (df_m['DATA_TEMP'].isna())
                                df_m_novo = df_m[mask_manter].drop(columns=['DATA_TEMP'])
                                pedidos_preservados = df_m_novo['PEDIDO'].astype(str).tolist()
                                qtd_removidos = len(df_m) - len(df_m_novo)
                                if qtd_removidos > 0:
                                    aba_m.clear(); aba_m.update("A1", [df_m_novo.columns.tolist()] + df_m_novo.fillna("").astype(str).values.tolist())
                                    try:
                                        aba_app = planilha_db.worksheet("App_Tarefas")
                                        dados_app = aba_app.get_all_values()
                                        if len(dados_app) > 1:
                                            df_app = pd.DataFrame(dados_app[1:], columns=dados_app[0])
                                            if 'PEDIDO' in df_app.columns:
                                                df_app_novo = df_app[df_app['PEDIDO'].astype(str).isin(pedidos_preservados)]
                                                aba_app.clear(); aba_app.update("A1", [df_app_novo.columns.tolist()] + df_app_novo.fillna("").astype(str).values.tolist())
                                    except Exception: pass
                                    st.success(f"✅ Limpeza concluída! 🗑️ {qtd_removidos} registros antigos foram apagados.")
                                else: st.info("👍 A base já está leve! Não foram encontrados pedidos com mais de 30 dias.")
                            time.sleep(2.5); carregar_dados_completos.clear(); st.rerun()
                        except Exception as e: st.error(f"Erro ao realizar a limpeza: {e}")
                else:
                    if senha_limpeza: st.error("❌ Senha incorreta. Ação bloqueada.")

        st.markdown("---")
        st.markdown("#### 🚨 Zona de Perigo: Reset Total do Banco")
        with st.form("form_reset_banco"):
            senha_reset = st.text_input("🔑 Senha de Autorização (Digite: 123):", type="password")
            if st.form_submit_button("🗑️ ZERAR TUDO (RESET TOTAL)", type="primary", use_container_width=True):
                if senha_reset == "123":
                    with st.spinner("Limpando banco de dados com segurança e preservando cabeçalhos..."):
                        try:
                            aba_m = planilha_db.worksheet("Memoria_Sistema")
                            cabecalho_m = aba_m.row_values(1)
                            aba_m.clear(); aba_m.update("A1", [cabecalho_m])
                            try:
                                aba_app = planilha_db.worksheet("App_Tarefas")
                                cabecalho_app = aba_app.row_values(1)
                                aba_app.clear(); aba_app.update("A1", [cabecalho_app])
                            except Exception: pass
                            st.success("✅ Banco zerado com sucesso! A base está pronta para a produção.")
                            time.sleep(2); carregar_dados_completos.clear(); st.rerun()
                        except Exception as e: st.error(f"Erro Crítico ao limpar o banco: {e}")
                else:
                    if senha_reset: st.error("❌ Senha incorreta.")
