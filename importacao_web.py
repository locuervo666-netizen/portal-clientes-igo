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
st.set_page_config(page_title="C.C.O - IGO Logística", layout="wide", page_icon="🚚", initial_sidebar_state="collapsed")
st_autorefresh(interval=120000, limit=None, key="refresh_timer")

st.markdown("""
    <style>
    [data-testid="stToolbar"], .stAppDeployButton, .stDeployButton, #MainMenu, footer { display: none !important; }
    .block-container { padding-top: 2rem !important; padding-bottom: 120px !important; max-width: 98% !important; }
    [data-testid="stAppViewContainer"] { background-color: #FFFFFF !important; }
    
    div[data-testid="stRadio"] {
        position: fixed !important; bottom: 0 !important; left: 0 !important; width: 100vw !important;
        background-color: #0F172A !important; padding: 12px 0px !important; z-index: 999999 !important;
        box-shadow: 0px -10px 25px -5px rgba(0, 0, 0, 0.3) !important; border-top: 1px solid #1E293B !important; margin: 0 !important;
    }
    div[data-testid="stRadio"] > div { display: flex; flex-direction: row; flex-wrap: wrap; justify-content: center; gap: 10px; }
    div[data-testid="stRadio"] label { background-color: transparent !important; border: 1px solid transparent !important; padding: 8px 20px !important; border-radius: 8px !important; cursor: pointer !important; transition: all 0.2s ease !important; margin: 0 !important; }
    div[data-testid="stRadio"] label:hover { background-color: #1E293B !important; }
    div[data-testid="stRadio"] label p { color: #94A3B8 !important; font-weight: 600 !important; font-size: 14px !important; margin: 0 !important; }
    div[data-testid="stRadio"] label[data-checked="true"] { background-color: #38BDF8 !important; box-shadow: 0 0 10px rgba(56, 189, 248, 0.4) !important; }
    div[data-testid="stRadio"] label[data-checked="true"] p { color: #0F172A !important; font-weight: 800 !important; }
    div[role="radiogroup"] label div[data-testid="stRadio-radio"] { display: none !important; }

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
    </style>
""", unsafe_allow_html=True)

st.markdown("""<style>[data-testid="stSidebar"] { display: none !important; }</style>""", unsafe_allow_html=True)

if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

# 🔥 TELA DE LOGIN CENTRALIZADA COM LOGO 🔥
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
# 🔗 2. CONEXÃO E FUNÇÕES ISOLADAS
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
    except Exception as e:
        st.error(f"Erro na conexão com o Banco: {e}")
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
            df = df.loc[:, ~df.columns.duplicated()] 
            df = df.dropna(how='all') 
            
            if 'ZAP_ENVIADO' not in df.columns:
                df['ZAP_ENVIADO'] = ""

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
            
            if 'DATA' in df.columns: df['DATA_OBJ'] = pd.to_datetime(df['DATA'], format='%d/%m/%Y', errors='coerce').dt.date
            return df
    except Exception as e: st.error(f"Erro Crítico ao carregar a Memoria_Sistema: {e}")
    return pd.DataFrame()

planilha_db = conectar_banco()
DF_AGENTES = carregar_dados_agentes(planilha_db)
FERIADOS_BR = holidays.Brazil()
CLIENTES_AUTORIZADOS = ["CUNHA", "CAEP", "SAPIENS", "GRALAB", "SYNVIA", "INNOVATOX", "LABEST", "AIRLAB", "UNILABOR", "SODRE", "BRASILIENSE", "MB_CAEP"]
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

# 🔥 MOTOR DE DISPARO DA Z-API (TEXTOS) 🔥
def enviar_whatsapp_zapi(telefone_destino, texto_mensagem):
    INSTANCIA = "3F14E62A63D2B28DC385B20DE66F3711" 
    TOKEN = "2321563615C4242CB6031504"         
    CLIENT_TOKEN = "Ffaa43dcff1e14f0e985c91e92b24ed89S" 
    
    tel_limpo = re.sub(r'\D', '', str(telefone_destino))
    if not tel_limpo.startswith('55') and len(tel_limpo) in [10, 11]:
        tel_limpo = '55' + tel_limpo
        
    url = f"https://api.z-api.io/instances/{INSTANCIA}/token/{TOKEN}/send-text"
    payload = {"phone": tel_limpo, "message": texto_mensagem}
    headers = {"Accept": "application/json", "Content-Type": "application/json", "Client-Token": CLIENT_TOKEN}
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code in [200, 201]: return True
        else: return False
    except Exception: return False

# 🔥 MOTOR DE DISPARO DA Z-API (ARQUIVOS / PDF) 🔥
def enviar_pdf_zapi(telefone_destino, pdf_bytes, nome_arquivo):
    INSTANCIA = "3F14E62A63D2B28DC385B20DE66F3711" 
    TOKEN = "2321563615C4242CB6031504"         
    CLIENT_TOKEN = "Ffaa43dcff1e14f0e985c91e92b24ed89S" 
    
    tel_limpo = re.sub(r'\D', '', str(telefone_destino))
    if not tel_limpo.startswith('55') and len(tel_limpo) in [10, 11]:
        tel_limpo = '55' + tel_limpo
        
    url = f"https://api.z-api.io/instances/{INSTANCIA}/token/{TOKEN}/send-document/pdf"
    
    b64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
    document_payload = f"data:application/pdf;base64,{b64_pdf}"
    
    payload = {
        "phone": tel_limpo, 
        "document": document_payload,
        "fileName": nome_arquivo
    }
    headers = {"Accept": "application/json", "Content-Type": "application/json", "Client-Token": CLIENT_TOKEN}
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code in [200, 201]: 
            return True
        else: 
            st.error(f"🚨 Z-API recusou o PDF do agente {tel_limpo}: {response.text}")
            time.sleep(6) # Congela a tela para você ler
            return False
    except Exception as e: 
        st.error(f"🚨 Erro interno ao enviar PDF: {e}")
        time.sleep(6)
        return False

# 🔥 MOTOR DE DISPARO DA Z-API (EXCEL / XLSX) 🔥
def enviar_excel_zapi(telefone_destino, xls_bytes, nome_arquivo):
    INSTANCIA = "3F14E62A63D2B28DC385B20DE66F3711" 
    TOKEN = "2321563615C4242CB6031504"         
    CLIENT_TOKEN = "Ffaa43dcff1e14f0e985c91e92b24ed89S" 
    
    tel_limpo = re.sub(r'\D', '', str(telefone_destino))
    if not tel_limpo.startswith('55') and len(tel_limpo) in [10, 11]:
        tel_limpo = '55' + tel_limpo
        
    url = f"https://api.z-api.io/instances/{INSTANCIA}/token/{TOKEN}/send-document/xlsx"
    
    b64_xls = base64.b64encode(xls_bytes).decode('utf-8')
    document_payload = f"data:application/octet-stream;base64,{b64_xls}"
    
    payload = {
        "phone": tel_limpo, 
        "document": document_payload,
        "fileName": nome_arquivo
    }
    headers = {"Accept": "application/json", "Content-Type": "application/json", "Client-Token": CLIENT_TOKEN}
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code in [200, 201]: 
            return True
        else: 
            st.error(f"🚨 Z-API RECUSOU O EXCEL do agente {tel_limpo}: {response.text}")
            time.sleep(6) # Congela a tela para você ler
            return False
    except Exception as e: 
        st.error(f"🚨 Erro interno ao enviar Excel: {e}")
        time.sleep(6)
        return False

# 🔥 CONSTRUTOR DE EXCEL PARA WHATSAPP (MULTIPLAS ABAS BLINDADO) 🔥
def gerar_excel_rota_whatsapp(df_agente):
    output = io.BytesIO()
    df_xls = df_agente.copy()
    
    # AMORTECEDOR DE ERRO: Garante que todas as colunas que o Excel precisa existam!
    cols_desejadas = ['PEDIDO', 'LABORATORIO', 'ENDERECO', 'NUMERO', 'BAIRRO', 'CEP', 'TOMADOR', 'OBSERVACOES']
    for c in cols_desejadas:
        if c not in df_xls.columns:
            df_xls[c] = ""
            
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        
        # 1. Criar aba de Resumo Geral
        resumo = df_xls.groupby('CIDADE').size().reset_index(name='QTD_VOLUMES')
        resumo.loc[len(resumo)] = ['TOTAL GERAL', resumo['QTD_VOLUMES'].sum()]
        resumo.to_excel(writer, sheet_name='RESUMO_GERAL', index=False)
        
        worksheet_res = writer.sheets['RESUMO_GERAL']
        worksheet_res.hide_gridlines(2)
        worksheet_res.add_table(0, 0, len(resumo), 1, {
            'columns': [{'header': 'CIDADE'}, {'header': 'QTD_VOLUMES'}],
            'style': 'Table Style Medium 2'
        })
        worksheet_res.set_column('A:A', 30)
        worksheet_res.set_column('B:B', 15)
        
        # 2. Criar abas individuais por Cidade
        for cidade, group in df_xls.groupby('CIDADE'):
            cid_limpa = re.sub(r'[^A-Za-z0-9 ]', '', str(cidade).strip())[:30] 
            if not cid_limpa: cid_limpa = "Sem_Cidade"
            
            df_cid = group[cols_desejadas].copy()
            df_cid.to_excel(writer, sheet_name=cid_limpa, index=False)
            
            worksheet = writer.sheets[cid_limpa]
            worksheet.hide_gridlines(2)
            
            if len(df_cid) > 0:
                worksheet.add_table(0, 0, len(df_cid), len(df_cid.columns) - 1, {
                    'columns': [{'header': str(col)} for col in df_cid.columns],
                    'style': 'Table Style Light 9'
                })
                
            worksheet.set_column('A:A', 15) 
            worksheet.set_column('B:B', 40) 
            worksheet.set_column('C:C', 40) 
            worksheet.set_column('D:H', 20) 
            
    return output.getvalue()

# 🔥 CONSTRUTOR DE PDF PARA WHATSAPP 🔥
def gerar_pdf_rota_whatsapp(nome_motorista, data_str, df_agente):
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
    except Exception: pass
    
    pdf.set_y(15)
    pdf.set_font("Arial", "B", 14)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 6, f"ROTA OFICIAL DE OPERACAO - IGO LOGISTICA", ln=True, align="C") 
    pdf.set_font("Arial", "B", 10)
    pdf.set_text_color(2, 132, 199) 
    pdf.cell(0, 5, f"AGENTE: {padronizar_texto(nome_motorista)}", ln=True, align="C")
    pdf.set_font("Arial", "", 8)
    pdf.set_text_color(100, 116, 139) 
    pdf.cell(0, 4, f"Data da Rota: {data_str} | Total de Volumes: {len(df_agente)}", ln=True, align="C")
    
    pdf.ln(3); pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(3)
    
    grouped_cidade = df_agente.groupby('CIDADE')
    for cidade, group_cid in grouped_cidade:
        cidade_nome = padronizar_texto(str(cidade))
        
        pdf.set_fill_color(15, 23, 42)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", "B", 9)
        pdf.cell(0, 6, f"CIDADE: {cidade_nome}", 1, 1, "L", True)
        
        grouped_bairro = group_cid.groupby('BAIRRO')
        for bairro, group_bai in grouped_bairro:
            bairro_nome = padronizar_texto(str(bairro))
            
            pdf.set_fill_color(226, 232, 240)
            pdf.set_text_color(15, 23, 42)
            pdf.set_font("Arial", "B", 8)
            pdf.cell(0, 5, f"   BAIRRO: {bairro_nome}", 1, 1, "L", True)
            
            pdf.set_fill_color(241, 245, 249)
            pdf.set_text_color(71, 85, 105)
            pdf.set_font("Arial", "B", 7)
            pdf.cell(8, 5, "OK", 1, 0, "C", True)
            pdf.cell(20, 5, "PEDIDO", 1, 0, "C", True)
            pdf.cell(60, 5, "LABORATORIO", 1, 0, "L", True)
            pdf.cell(77, 5, "ENDERECO", 1, 0, "L", True)
            pdf.cell(25, 5, "TOMADOR", 1, 1, "C", True)
            
            pdf.set_text_color(51, 65, 85)
            pdf.set_font("Arial", "", 7)
            for _, row in group_bai.iterrows():
                ped = padronizar_texto(str(row.get('PEDIDO','')))
                lab = padronizar_texto(str(row.get('LABORATORIO','')))[:35]
                end = padronizar_texto(f"{str(row.get('ENDERECO',''))}, {str(row.get('NUMERO',''))}")[:48]
                tom = padronizar_texto(str(row.get('TOMADOR','')))[:15]
                
                pdf.cell(8, 5, "[  ]", 1, 0, "C")
                pdf.cell(20, 5, ped, 1, 0, "C")
                pdf.cell(60, 5, lab, 1, 0, "L")
                pdf.cell(77, 5, end, 1, 0, "L")
                pdf.cell(25, 5, tom, 1, 1, "C")
                
        pdf.ln(2)
        
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
        pdf.output(tmp_pdf.name)
        with open(tmp_pdf.name, "rb") as f: pdf_bytes = f.read()
    return pdf_bytes

def gerar_pdf_romaneio(id_romaneio, data_despacho, motorista_escolhido, sel_lista):
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
    except Exception: pass
        
    pdf.set_y(15)
    pdf.set_font("Arial", "B", 14)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 6, f"PROTOCOLO DE ENTREGA - IGO LOGISTICA", ln=True, align="C") 
    pdf.set_font("Arial", "B", 10)
    pdf.set_text_color(2, 132, 199) 
    pdf.cell(0, 5, f"LOTE DE EXPEDIÇÃO: {id_romaneio}", ln=True, align="C")
    pdf.set_font("Arial", "", 8)
    pdf.set_text_color(100, 116, 139) 
    dt_str = data_despacho if isinstance(data_despacho, str) else data_despacho.strftime('%d/%m/%Y')
    pdf.cell(0, 4, f"Data do Embarque: {dt_str} | Motorista: {str(motorista_escolhido).upper()}", ln=True, align="C")
    
    pdf.ln(3); pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(3)
    
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
        pdf.set_fill_color(241, 245, 249) if fill else pdf.set_fill_color(255, 255, 255)
        qr_val = str(item.get('QR_CODE', ''))
        if qr_val.upper() == 'NAN' or not qr_val: qr_val = "-"
            
        pdf.cell(10, 5, str(idx), 1, 0, "C", True)
        pdf.cell(25, 5, str(item.get('PEDIDO','')), 1, 0, "C", True)
        pdf.cell(30, 5, qr_val, 1, 0, "C", True)
        pdf.cell(80, 5, padronizar_texto(str(item.get('LABORATORIO','')))[:48], 1, 0, "L", True)
        pdf.cell(35, 5, padronizar_texto(str(item.get('CIDADE','')))[:22], 1, 0, "L", True)
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
    return pdf_bytes

def tratar_texto_global(texto):
    if pd.isna(texto): return ""
    t = padronizar_texto(texto)
    return t[:-2] if t.endswith('.0') else t

def limpar_nome_local_rota(texto):
    return tratar_texto_global(texto).split('/')[0].split('-')[0].strip()

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
    except Exception: return data_ini

def gerar_excel_memoria(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Relatorio', index=False)
        worksheet = writer.sheets['Relatorio']
        worksheet.hide_gridlines(2)
        if df.shape[0] > 0:
            worksheet.add_table(0, 0, df.shape[0], df.shape[1] - 1, {'columns': [{'header': str(col)} for col in df.columns], 'style': 'Table Style Medium 2'})
            for i, col in enumerate(df.columns): worksheet.set_column(i, i, min(max(df[col].astype(str).map(len).max(), len(str(col))) + 2, 40))
    return output.getvalue()

def obter_proximo_id(df):
    if df is None or df.empty or 'PEDIDO' not in df.columns: return 100000
    try: return int(df['PEDIDO'].astype(str).str.extract(r'^(\d+)')[0].dropna().astype(int).max()) + 1 if not df['PEDIDO'].astype(str).str.extract(r'^(\d+)')[0].dropna().empty else 100000
    except Exception: return 100000

def calc_status_display(row):
    status_final, previsao = str(row.get('STATUS', '')).strip().upper(), str(row.get('DATA_LIMITE', '')).strip()
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
        except Exception: pass
    return res

if 'filtro_kpi_admin' not in st.session_state: st.session_state.filtro_kpi_admin = "TODOS"

# =============================================================================
# 🎨 3. CABEÇALHO E NAVEGAÇÃO
# =============================================================================
col_logo, col_title, col_logout = st.columns([1, 4, 1], vertical_alignment="center")

with col_logo:
    st.image("https://i.postimg.cc/x84nnjjq/IGO-LOGO.png", width=140)
with col_title:
    st.markdown("<h2 style='color: #0F172A; font-weight: 800; margin: 0; text-align: center;'>PAINEL GERENCIAL</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #64748B; margin: 0; text-align: center; font-weight: 600;'>Centro de Controle Operacional - IGO Logística</p>", unsafe_allow_html=True)
with col_logout:
    if st.button("🚪 Sair", use_container_width=True):
        st.session_state.autenticado = False; st.cache_data.clear(); st.cache_resource.clear(); st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

menu = st.radio("Navegação:", ["📊 GRID", "📝 Pedido Manual", "📥 Importações", "🔬 Triagem", "📱 WhatsApp", "📁 Relatórios", "⚙️ Rotas"], horizontal=True, label_visibility="collapsed")

if planilha_db is None:
    st.error("🚨 FALHA CRÍTICA: Não foi possível conectar ao Google Sheets.")
    st.stop()


# =============================================================================
# 🚀 MÓDULO 1: DASHBOARD / GRID PRINCIPAL
# =============================================================================
if menu == "📊 GRID":
    df_raw = carregar_dados_completos(planilha_db)
    
    if not df_raw.empty:
        df_raw['FOTO_URL'] = df_raw['FOTO'].apply(lambda x: f"https://www.appsheet.com/template/gettablefileurl?appName=APPIGOLOGISTICA-153047553&tableName=App_Tarefas&fileName={str(x).strip()}" if str(x).strip() and str(x).upper() not in ['NAN', 'NONE', ''] else "")
        df_raw['STATUS_DISPLAY'] = df_raw.apply(calc_status_display, axis=1)
        if 'DATA_LIMITE' in df_raw.columns: df_raw['DATA_LIMITE'] = df_raw['DATA_LIMITE'].fillna("").astype(str)

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
        taxa_progresso = n_ent / n_tot if n_tot > 0 else 0.0
        st.progress(taxa_progresso, text=f"📊 Progresso da Operação: {int(taxa_progresso * 100)}% dos pacotes entregues")
        
        st.markdown("<br>", unsafe_allow_html=True)
        busca = st.text_input("🔎 Busca Rápida (Código, Lab, Cidade...):", placeholder="Filtrar dados na tabela...")

        df_grid = df_f.copy()
        if st.session_state.filtro_kpi_admin == "ENTREGUE": df_grid = df_grid[df_grid['STATUS_DISPLAY'].str.contains('Entregue')]
        elif st.session_state.filtro_kpi_admin == "PENDENTE": df_grid = df_grid[df_grid['STATUS_DISPLAY'].str.contains('Pendente')]
        elif st.session_state.filtro_kpi_admin == "FRUSTRADA": df_grid = df_grid[df_grid['STATUS_DISPLAY'].str.contains('Frustrada')]
        elif st.session_state.filtro_kpi_admin == "ATRASADO": df_grid = df_grid[df_grid['STATUS_DISPLAY'].str.contains('ATRASADO')]
        elif st.session_state.filtro_kpi_admin == "HOJE": df_grid = df_grid[df_grid['DATA_OBJ'] == hoje_br]
        
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

        colunas_mostrar = ['DATA', 'PEDIDO', 'TOMADOR', 'LABORATORIO', 'CIDADE', 'STATUS_DISPLAY', 'DATA_LIMITE', 'AGENTE_RAW', 'DATA_ENTREGA', 'COMPROVANTE']
        df_grid = df_grid[[c for c in colunas_mostrar if c in df_grid.columns]].dropna(subset=['PEDIDO'])
        df_grid = df_grid[df_grid['PEDIDO'].astype(str).str.strip() != ""] 
        
        for col in df_grid.columns: 
            df_grid[col] = df_grid[col].astype(str).replace(["nan", "NaN", "None", "none", "<NA>", "NaT"], "")
            
        if busca: df_grid = df_grid[df_grid.astype(str).apply(lambda x: busca.upper() in x.str.upper().values, axis=1)]
        df_grid = df_grid.reset_index(drop=True)

        df_grid['COMPROVANTE'] = df_grid['COMPROVANTE'].apply(lambda x: x if str(x).startswith("http") else "")

        st.markdown(f"<p style='color:#059669; font-weight:600; font-size:12px; margin-bottom: 5px;'>🟢 Sincronizado: {datetime.now(FUSO_BR).strftime('%H:%M:%S')} | Selecione as caixinhas na tabela para liberar os botões.</p>", unsafe_allow_html=True)

        box_botoes = st.empty()
        
        df_grid.insert(0, "SELECIONAR", False)
        
        tabela_renderizada = st.data_editor(
            df_grid,
            column_config={
                "SELECIONAR": st.column_config.CheckboxColumn("✔ AÇÃO", default=False),
                "STATUS_DISPLAY": st.column_config.TextColumn("STATUS"),
                "COMPROVANTE": st.column_config.LinkColumn("FOTO", display_text="🔎 Ver Foto"),
                "AGENTE_RAW": st.column_config.TextColumn("AGENTE"),
                "DATA_ENTREGA": st.column_config.TextColumn("ENTREGA"),
                "DATA_LIMITE": st.column_config.TextColumn("PREVISÃO"),
                "DATA": st.column_config.TextColumn("DATA"),
                "PEDIDO": st.column_config.TextColumn("PEDIDO"),
                "TOMADOR": st.column_config.TextColumn("TOMADOR"),
                "LABORATORIO": st.column_config.TextColumn("LABORATÓRIO"),
                "CIDADE": st.column_config.TextColumn("CIDADE")
            },
            disabled=[c for c in df_grid.columns if c != "SELECIONAR"],
            hide_index=True,
            use_container_width=True,
            height=500,
            key="tabela_nativa_indestrutivel_final"
        )
        
        linhas_selecionadas = tabela_renderizada[tabela_renderizada["SELECIONAR"]]
        p_ids = linhas_selecionadas["PEDIDO"].astype(str).tolist() if not linhas_selecionadas.empty else []
        tem_sel = len(p_ids) > 0

        with box_botoes.container():
            st.markdown("""
            <style>
            div[data-testid="stPopover"] > button, button[kind="secondary"] {
                white-space: nowrap !important; overflow: hidden !important; font-weight: 600 !important; font-size: 13px !important; border-radius: 6px !important; height: 36px !important; min-height: 36px !important; padding: 0px 12px !important; border: 1px solid #CBD5E1 !important; background-color: #FFFFFF !important; color: #475569 !important; transition: all 0.2s ease !important; box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important; margin-bottom: 10px;
            }
            div[data-testid="stPopover"] > button:hover, button[kind="secondary"]:hover {
                border-color: #0284C7 !important; color: #0369A1 !important; background-color: #F0F9FF !important; box-shadow: 0 2px 4px rgba(2, 132, 199, 0.1) !important;
            }
            </style>
            """, unsafe_allow_html=True)

            col_b1, col_b2, col_b3, col_b4, col_b5 = st.columns(5)
            
            with col_b1.popover("📲 Dar Baixa Manual", use_container_width=True):
                if not tem_sel: 
                    st.warning("Selecione um pedido na tabela abaixo primeiro!")
                else:
                    with st.form("form_baixa_manual"):
                        status_baixa = st.selectbox("Novo Status:", ["ENTREGUE ✅", "PROBLEMA 🚨", "CANCELADO ❌", "PENDENTE ⏳"])
                        data_baixa = st.date_input("Data da Ocorrência:", format="DD/MM/YYYY", value=hoje_br)
                        tem_entregue = df_f[df_f['PEDIDO'].isin(p_ids)]['STATUS_DISPLAY'].str.contains('Entregue').any()
                        senha_reversao = ""
                        if tem_entregue:
                            st.warning("⚠️ Desfazendo pedido já **ENTREGUES**.")
                            senha_reversao = st.text_input("🔑 Senha:", type="password")

                        if st.form_submit_button("Confirmar Nova Baixa", type="primary", use_container_width=True):
                            status_limpo = status_baixa.split(" ")[0].upper()
                            if tem_entregue and status_limpo != 'ENTREGUE' and senha_reversao != '123': 
                                st.error("❌ Senha incorreta!")
                            else:
                                with st.spinner("Atualizando Banco..."):
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
                                        
                                        try:
                                            aba_app = planilha_db.worksheet("App_Tarefas")
                                            df_app = pd.DataFrame(aba_app.get_all_values()[1:], columns=aba_app.get_all_values()[0])
                                            if 'PEDIDO' in df_app.columns and 'STATUS' in df_app.columns:
                                                df_app.loc[df_app['PEDIDO'].isin(p_ids), 'STATUS'] = status_limpo
                                                if 'DATA_ENTREGA' in df_app.columns:
                                                    if status_limpo == "ENTREGUE": df_app.loc[df_app['PEDIDO'].isin(p_ids), 'DATA_ENTREGA'] = data_baixa.strftime("%d/%m/%Y")
                                                    elif status_limpo == "PENDENTE": df_app.loc[df_app['PEDIDO'].isin(p_ids), 'DATA_ENTREGA'] = ""
                                                aba_app.clear(); aba_app.update("A1", [df_app.columns.tolist()] + df_app.fillna("").astype(str).values.tolist())
                                        except Exception: pass
                                            
                                        st.success("🎉 Atualizado com sucesso!")
                                        time.sleep(1.5)
                                        carregar_dados_completos.clear()
                                        st.rerun()
                                    except Exception as e: st.error(f"Erro: {e}")

            with col_b2.popover("🔄 Trocar de Motorista", use_container_width=True):
                if not tem_sel: 
                    st.warning("Selecione um pedido na tabela abaixo primeiro!")
                else:
                    with st.form("form_troca_motorista"):
                        tem_entregue = df_f[df_f['PEDIDO'].isin(p_ids)]['STATUS_DISPLAY'].str.contains('Entregue').any()
                        if tem_entregue: 
                            st.error("⚠️ Não é possível trocar motorista de pedidos já ENTREGUES.")
                        else:
                            logins_disp = sorted(DF_AGENTES['LOGIN DO AGENTE'].unique().tolist()) if not DF_AGENTES.empty else []
                            novo_mot = st.selectbox("Novo Agente:", logins_disp)
                            nova_data_troca = st.date_input("Nova Data do Pedido:", format="DD/MM/YYYY", value=hoje_br)
                            if st.form_submit_button("Confirmar Troca", type="primary", use_container_width=True):
                                with st.spinner("Trocando motorista..."):
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
                                        aba.clear(); aba.update("A1", [df_nuvem.columns.tolist()] + df_nuvem.fillna("").astype(str).values.tolist())
                                        despachar_para_appsheet(lista_app_troca)
                                        
                                        st.success("🎉 Troca realizada com sucesso!")
                                        time.sleep(1.5)
                                        carregar_dados_completos.clear()
                                        st.rerun()
                                    except Exception as e: st.error(f"Erro: {e}")
            
            with col_b3.popover("👯 Clonar Pedidos", use_container_width=True):
                if not tem_sel: 
                    st.warning("Selecione um pedido na tabela abaixo primeiro!")
                else:
                    with st.form("form_clonar_pedido"):
                        clone_data = st.date_input("Nova Data de Embarque:", format="DD/MM/YYYY", value=hoje_br)
                        logins_disp = sorted(DF_AGENTES['LOGIN DO AGENTE'].unique().tolist()) if not DF_AGENTES.empty else []
                        clone_mot = st.selectbox("Agente Designado:", ["Manter Original"] + logins_disp)
                        
                        if st.form_submit_button("Confirmar Clone", type="primary", use_container_width=True):
                            with st.spinner("Clonando na base..."):
                                try:
                                    aba = planilha_db.worksheet("Memoria_Sistema")
                                    df_nuvem = pd.DataFrame(aba.get_all_values()[1:], columns=aba.get_all_values()[0])
                                    if 'ZAP_ENVIADO' not in df_nuvem.columns: df_nuvem['ZAP_ENVIADO'] = ""
                                    
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
                                            l_orig['DATA_ENTREGA'] = ""
                                            l_orig['FOTO'] = ""
                                            l_orig['ROMANEIO'] = ""
                                            l_orig['ZAP_ENVIADO'] = ""
                                            if clone_mot != "Manter Original": 
                                                l_orig['AGENTE_RAW'] = clone_mot
                                            
                                            prazo = calcular_sla_dias(str(l_orig.get('UF', 'SP')), str(l_orig.get('CIDADE', '')))
                                            l_orig['PRAZO_DIAS'] = str(prazo) 
                                            l_orig['DATA_LIMITE'] = str(calcular_data_limite(l_orig['DATA'], prazo))
                                            
                                            l_orig = l_orig.astype(str)
                                            df_nuvem = pd.concat([df_nuvem, pd.DataFrame([l_orig])], ignore_index=True)
                                            
                                            if str(l_orig.get('AGENTE_RAW','')).strip():
                                                clones_para_app.append({'PEDIDO': novo_id, 'MOTORISTA': l_orig['AGENTE_RAW'], 'ENDERECO': l_orig.get('ENDERECO',''), 'NUMERO': l_orig.get('NUMERO',''), 'BAIRRO': l_orig.get('BAIRRO',''), 'CIDADE': l_orig.get('CIDADE',''), 'CEP': l_orig.get('CEP',''), 'LABORATORIO': l_orig.get('LABORATORIO',''), 'TOMADOR': l_orig.get('TOMADOR','')})
                                    
                                    aba.clear()
                                    aba.update("A1", [df_nuvem.columns.tolist()] + df_nuvem.fillna("").astype(str).values.tolist())
                                    if clones_para_app: 
                                        despachar_para_appsheet(clones_para_app)
                                    
                                    st.success(f"🎉 {len(p_ids)} Pedido(s) clonado(s) com sucesso!")
                                    time.sleep(1.5)
                                    carregar_dados_completos.clear()
                                    st.rerun()
                                except Exception as e: 
                                    st.error(f"Erro no Clone: {e}")

            with col_b4.popover("🗑️ Excluir Definitivamente", use_container_width=True):
                if not tem_sel: 
                    st.warning("Selecione um pedido na tabela abaixo primeiro!")
                else:
                    with st.form("form_excluir_pedido"):
                        st.error("⚠️ Atenção: Exclusão permanente.")
                        senha_del = st.text_input("🔑 Senha Master:", type="password")
                        if st.form_submit_button("Confirmar Exclusão", type="primary", use_container_width=True):
                            if senha_del == "123":
                                with st.spinner("Excluindo da base..."):
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
                                        except Exception: 
                                            pass 
                                            
                                        st.success(f"🗑️ Pedido(s) apagado(s) com sucesso!")
                                        time.sleep(1.5)
                                        carregar_dados_completos.clear()
                                        st.rerun()
                                    except Exception as e: 
                                        st.error(f"Erro: {e}")
                            else: 
                                st.error("Senha incorreta.")
            
            col_b5.button("🔄 Atualizar Painel", use_container_width=True, on_click=lambda: [carregar_dados_completos.clear(), st.rerun()])

    else:
        st.warning("O banco de dados está vazio ou a aba Memoria_Sistema não foi encontrada. Vá para a aba Pedido Manual.")

# =============================================================================
# 📝 MÓDULO EXTRA: NOVO PEDIDO MANUAL COM API VIACEP
# =============================================================================
elif menu == "📝 Pedido Manual":
    st.markdown("<div class='dinamic-border'><h3 class='dinamic-text' style='margin:0;'>📝 Inserir Novo Pedido Manual</h3></div>", unsafe_allow_html=True)
    st.markdown("Use esta tela para registrar amostras fora do padrão. **Os textos inseridos perderão os acentos e ficarão maiúsculos automaticamente.**")
    
    if 'm_rua' not in st.session_state: st.session_state['m_rua'] = ""
    if 'm_bai' not in st.session_state: st.session_state['m_bai'] = ""
    if 'm_cid' not in st.session_state: st.session_state['m_cid'] = ""
    if 'm_uf' not in st.session_state: st.session_state['m_uf'] = ""

    with st.container(border=True):
        st.markdown("#### 📍 Busca Inteligente de Endereço (ViaCEP)")
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
        
        with st.form("form_manual_page", clear_on_submit=True):
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
            
            if st.form_submit_button("🚀 Injetar na Base e Roteirizar", type="primary", use_container_width=True):
                if m_tomador == "Selecione..." or not m_cid or not m_lab or not m_rua or not m_bai: 
                    st.error("⚠️ Preencha todos os campos obrigatórios!")
                else:
                    with st.spinner("Padronizando textos e salvando na nuvem..."):
                        lab_limpo = padronizar_texto(m_lab)
                        rua_limpa = padronizar_texto(m_rua)
                        bai_limpo = padronizar_texto(m_bai)
                        cid_limpa = padronizar_texto(m_cid)
                        uf_limpa = padronizar_texto(m_uf)
                        m_agente = obter_login_agente(cid_limpa, bai_limpo, lab_limpo, rua_limpa, DF_AGENTES) if m_agente_escolha == "Automático (Por Rota)" else m_agente_escolha
                        m_prazo = str(calcular_sla_dias(uf_limpa, cid_limpa))
                        m_limite = str(calcular_data_limite(m_data.strftime("%d/%m/%Y"), int(m_prazo)))
                        
                        try:
                            aba_memoria = planilha_db.worksheet("Memoria_Sistema")
                            dados_atuais = aba_memoria.get_all_values()
                            df_nuvem = pd.DataFrame(dados_atuais[1:], columns=dados_atuais[0]) if len(dados_atuais) > 1 else pd.DataFrame()
                            if 'ZAP_ENVIADO' not in df_nuvem.columns: df_nuvem['ZAP_ENVIADO'] = ""
                            m_pedido = str(obter_proximo_id(df_nuvem))
                            
                            novo_ped = pd.DataFrame([{
                                'DATA': m_data.strftime("%d/%m/%Y"), 'PEDIDO': m_pedido, 'TOMADOR': m_tomador, 
                                'LABORATORIO': lab_limpo, 'ENDERECO': rua_limpa, 'NUMERO': "", 'BAIRRO': bai_limpo, 
                                'CIDADE': cid_limpa, 'UF': uf_limpa, 'CEP': cep_limpo if 'cep_limpo' in locals() else "", 
                                'STATUS': 'PENDENTE', 'AGENTE_RAW': m_agente, 'PRAZO_DIAS': m_prazo, 
                                'DATA_LIMITE': m_limite, 'DATA_ENTREGA': "", 'FOTO': "", 'ROMANEIO': "", 'ZAP_ENVIADO': ""
                            }]).astype(str)
                            
                            df_atual = pd.concat([df_nuvem, novo_ped], ignore_index=True) if not df_nuvem.empty else novo_ped
                            aba_memoria.clear()
                            aba_memoria.update("A1", [df_atual.columns.tolist()] + df_atual.fillna("").astype(str).values.tolist())
                            
                            if m_agente: 
                                despachar_para_appsheet([novo_ped.iloc[0].to_dict()])
                                
                            st.success(f"🎉 Pedido {m_pedido} criado com sucesso!")
                            
                            st.session_state['m_rua'] = ""
                            st.session_state['m_bai'] = ""
                            st.session_state['m_cid'] = ""
                            st.session_state['m_uf'] = ""
                            
                            carregar_dados_completos.clear()
                        except Exception as e: 
                            st.error(f"Erro ao salvar: {e}")

# =============================================================================
# ➕ MÓDULO 2: IMPORTAÇÃO DE LOTES
# =============================================================================
elif menu == "📥 Importações":
    st.markdown("<div class='dinamic-border'><h3 class='dinamic-text' style='margin:0;'>➕ Central de Importação de Lotes</h3></div>", unsafe_allow_html=True)
    if "df_preview" not in st.session_state: 
        st.session_state.df_preview = pd.DataFrame()
        
    with st.container(border=True):
        st.markdown("#### 1. Mapeamento de Planilha e Colagem")
        c1, c2, c3 = st.columns([1, 1, 2])
        with c1: 
            tom = st.selectbox("🏢 Tomador Central:", ["Selecione..."] + CLIENTES_AUTORIZADOS)
        with c2: 
            dt_c = st.date_input("📅 Data da Rota:", format="DD/MM/YYYY", value=hoje_br)
        
        txt = st.text_area("📋 Cole os dados da planilha do cliente (Ctrl+V):", height=150)
        col_btn1, _ = st.columns([1, 2])
        
        if col_btn1.button("🔍 1. Processar Matriz e Roteirizar", type="primary", use_container_width=True):
            if not txt or tom == "Selecione...": 
                st.warning("Preencha o Tomador e cole os dados!")
            else:
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
                        cl = ''.join(e for e in unicodedata.normalize('NFKD', str(c).upper().strip()).encode('ASCII', 'ignore').decode('utf-8') if e.isalnum()) 
                        if any(x in cl for x in ['PEDIDO', 'SOLICITA', 'CODIGO', 'CDIGO']) or cl == 'ID': 
                            mapa[c] = 'PEDIDO'
                        elif any(x in cl for x in ['LABORAT', 'CLINIC', 'POSTO', 'NOME', 'CLIENTE']): 
                            mapa[c] = 'LABORATORIO'
                        elif any(x in cl for x in ['ENDERE', 'RUA', 'LOGRADOURO', 'AVENIDA']): 
                            mapa[c] = 'ENDERECO'
                        elif any(x in cl for x in ['NUM', 'NRO']) or cl in ['N', 'NO']: 
                            mapa[c] = 'NUMERO'
                        elif 'BAIRRO' in cl: 
                            mapa[c] = 'BAIRRO'
                        elif any(x in cl for x in ['CIDADE', 'MUNIC']): 
                            mapa[c] = 'CIDADE'
                        elif any(x in cl for x in ['ESTADO', 'UF']): 
                            mapa[c] = 'UF'
                        elif 'CEP' in cl: 
                            mapa[c] = 'CEP'
                            
                    df_limpo.rename(columns=mapa, inplace=True)
                    
                    for c in ['PEDIDO', 'LABORATORIO', 'CEP', 'ENDERECO', 'NUMERO', 'BAIRRO', 'CIDADE', 'UF']:
                        if c not in df_limpo.columns: 
                            df_limpo[c] = ""
                            
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
                except Exception as e: 
                    st.error(f"Erro no processamento: {e}")

    if not st.session_state.df_preview.empty:
        st.markdown("---")
        col_tit, col_canc = st.columns([4, 1], vertical_alignment="center")
        col_tit.markdown("### 👀 2. Preview de Carga")
        if col_canc.button("❌ Cancelar / Limpar", type="secondary", use_container_width=True):
            st.session_state.df_preview = pd.DataFrame()
            st.rerun()

        df_preview = st.session_state.df_preview
        mask_err = (df_preview['AGENTE_RAW'].astype(str).str.strip() == "") | (df_preview['AGENTE_RAW'].astype(str).str.upper() == "NAN")
        df_err = df_preview[mask_err]
        df_ok = df_preview[~mask_err]

        if not df_err.empty:
            st.error(f"🚨 **Atenção:** {len(df_err)} pedido(s) sem motorista. Corrija abaixo.")
            with st.form("form_correcao_agentes"):
                correcoes = {}
                logins_disp = sorted(DF_AGENTES['LOGIN DO AGENTE'].unique().tolist()) if not DF_AGENTES.empty else []
                for idx, row in df_err.iterrows():
                    st.markdown(f"**Cód:** {row['PEDIDO']} | **Local:** {row['LABORATORIO']} | **Cidade:** {row['CIDADE']}")
                    correcoes[idx] = st.selectbox(f"Motorista para ID {row['PEDIDO']}:", ["Selecione..."] + logins_disp, key=f"fix_mot_{idx}")
                    st.divider()
                if st.form_submit_button("💾 Validar", type="primary"):
                    for idx, novo_mot in correcoes.items():
                        if novo_mot != "Selecione...": 
                            st.session_state.df_preview.at[idx, 'AGENTE_RAW'] = novo_mot
                    st.rerun()
        else:
            st.success(f"✅ Lote validado! {len(df_ok)} pedidos prontos.")
            st.dataframe(df_ok, hide_index=True)
            if st.button("🚀 3. INJETAR LOTE", type="primary"):
                with st.spinner("Injetando..."):
                    try:
                        aba = planilha_db.worksheet("Memoria_Sistema")
                        atuais = aba.get_all_values()
                        df_up = pd.DataFrame(atuais[1:], columns=atuais[0]) if len(atuais) > 1 else pd.DataFrame()
                        if 'ZAP_ENVIADO' not in df_up.columns: df_up['ZAP_ENVIADO'] = ""
                        
                        prox_id = obter_proximo_id(df_up)
                        for idx, row in df_ok.iterrows():
                            if not str(row['PEDIDO']).strip(): 
                                df_ok.at[idx, 'PEDIDO'] = str(prox_id)
                                prox_id += 1
                        df_ok['PRAZO_DIAS'] = df_ok.apply(lambda r: str(calcular_sla_dias(r['UF'], r['CIDADE'])), axis=1)
                        df_ok['DATA_LIMITE'] = df_ok.apply(lambda r: str(calcular_data_limite(r['DATA'], int(r['PRAZO_DIAS']))), axis=1)
                        df_ok['STATUS'] = 'PENDENTE'
                        df_ok['DATA_ENTREGA'] = ''
                        df_ok['FOTO'] = ''
                        df_ok['ROMANEIO'] = ''
                        df_ok['ZAP_ENVIADO'] = ''
                        
                        df_ok = df_ok.astype(str)
                        df_up = pd.concat([df_up, df_ok], ignore_index=True) if not df_up.empty else df_ok
                        aba.clear()
                        aba.update("A1", [df_up.columns.tolist()] + df_up.fillna("").astype(str).values.tolist())
                        
                        lista_app = []
                        for _, r in df_ok.iterrows():
                            if str(r.get('AGENTE_RAW','')).strip():
                                lista_app.append({'PEDIDO': r['PEDIDO'], 'MOTORISTA': r['AGENTE_RAW'], 'ENDERECO': r['ENDERECO'], 'NUMERO': r['NUMERO'], 'BAIRRO': r['BAIRRO'], 'CIDADE': r['CIDADE'], 'CEP': r['CEP'], 'LABORATORIO': r['LABORATORIO'], 'TOMADOR': r['TOMADOR']})
                        
                        if lista_app: 
                            despachar_para_appsheet(lista_app)
                            
                        st.success(f"🎉 SUCESSO! Foram importados um total de {len(df_ok)} pedidos com sucesso.")
                        time.sleep(2.5) 
                        
                        st.session_state.df_preview = pd.DataFrame()
                        carregar_dados_completos.clear()
                        st.rerun()
                    except Exception as e: 
                        st.error(f"Erro: {e}")

# =============================================================================
# 📋 MÓDULO 3: TRIAGEM E ROMANEIO
# =============================================================================
elif menu == "🔬 Triagem":
    st.markdown("<div class='dinamic-border'><h3 class='dinamic-text' style='margin:0;'>🔬 Terminal de Triagem e Expedição</h3></div>", unsafe_allow_html=True)
    df_raw = carregar_dados_completos(planilha_db)
    
    if not df_raw.empty:
        t1, t2, t3 = st.tabs(["📦 1. Validação Manual & Bipar", "🚚 2. Gerar Documento de Romaneio", "🕒 3. Histórico de Varredura"])
        
        with t1:
            st.info("💡 A auditoria de triagem aceita apenas materiais **COLETADOS** pelo aplicativo.")
            
            with st.form("form_bip", clear_on_submit=True):
                col_bip, col_btn = st.columns([4, 1])
                bip_input = col_bip.text_input("🔍 Bipar QR Code de Validação:")
                bip_submit = col_btn.form_submit_button("Auditar", use_container_width=True)
                
                if bip_submit and bip_input:
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
                                    st.success(f"✅ Pedido {str(df_raw.at[idx, 'PEDIDO'])} VALIDADO!"); carregar_dados_completos.clear()
                            except Exception as e: st.error(f"Erro: {e}")
                        else: st.error("❌ Volume não está com status COLETADO.")
                    else: st.error("❌ Assinatura não reconhecida.")

            st.markdown("---")
            st.markdown("#### Terminal de Validação em Lote (Recurso Manual)")
            df_fila = df_raw[df_raw['STATUS'].astype(str).str.upper() == 'COLETADO'].copy()
            
            if not df_fila.empty:
                df_fila = df_fila[['DATA', 'PEDIDO', 'TOMADOR', 'LABORATORIO', 'CIDADE', 'STATUS']].fillna("").astype(str)
                
                c_sel1, c_sel2 = st.columns([1, 4])
                sel_todos_val = c_sel1.checkbox("✅ Selecionar Todos", key="sel_all_val")
                df_fila.insert(0, "SELECIONAR", sel_todos_val)
                
                tabela_fila = st.data_editor(
                    df_fila, 
                    hide_index=True, 
                    disabled=[c for c in df_fila.columns if c != "SELECIONAR"], 
                    use_container_width=True,
                    key="tabela_triagem_lote"
                )
                
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
                                
                                st.success(f"🎉 {len(p_ids)} volumes liberados!")
                                time.sleep(1.5)
                                carregar_dados_completos.clear()
                                st.rerun()
                            except Exception as e: st.error(f"Erro: {e}")
            else:
                st.info("O salão está vazio. Materiais 'Coletados' no app chegam aqui.")

        with t2:
            st.markdown("#### Matriz de Expedição (Romaneio)")
            df_conf = df_raw[df_raw['STATUS'].astype(str).str.upper() == 'CONFERIDO'].copy()
            
            if not df_conf.empty:
                lista_tomadores_conf = sorted(df_conf['TOMADOR'].astype(str).unique().tolist())
                c_filtro, _ = st.columns([1, 2])
                tomador_filtro = c_filtro.selectbox("🏢 Hub de Destino (Filtro):", ["Todos"] + [t for t in lista_tomadores_conf if t.strip()])
                
                if tomador_filtro != "Todos": 
                    df_conf = df_conf[df_conf['TOMADOR'] == tomador_filtro]
                
                col_rom = ['DATA', 'PEDIDO', 'TOMADOR', 'LABORATORIO', 'CIDADE', 'UF']
                if 'QR_CODE' in df_conf.columns: col_rom.append('QR_CODE')
                
                df_conf_show = df_conf[col_rom].fillna("").astype(str)
                
                c_sel_exp1, c_sel_exp2 = st.columns([1, 4])
                sel_todos_exp = c_sel_exp1.checkbox("✅ Selecionar Todos", key="sel_all_exp")
                df_conf_show.insert(0, "SELECIONAR", sel_todos_exp)
                
                tabela_conf = st.data_editor(
                    df_conf_show, 
                    hide_index=True, 
                    disabled=[c for c in df_conf_show.columns if c != "SELECIONAR"], 
                    use_container_width=True,
                    key="tabela_triagem_expedicao"
                )
                
                selecionados = tabela_conf[tabela_conf["SELECIONAR"]]
                
                st.markdown("---")
                c_mot, c_data, c_btn = st.columns([2, 1, 2])
                logins_disp = sorted(DF_AGENTES['LOGIN DO AGENTE'].unique().tolist()) if not DF_AGENTES.empty else []
                motorista_escolhido = c_mot.selectbox("👤 Motorista:", ["Selecione..."] + logins_disp)
                data_despacho = c_data.date_input("📅 Data de Embarque:", format="DD/MM/YYYY", value=hoje_br)
                
                if c_btn.button(f"🚚 Despachar Lote ({len(selecionados)} volumes)", type="primary", use_container_width=True):
                    if selecionados.empty or motorista_escolhido == "Selecione...": 
                        st.warning("⚠️ Selecione os pacotes e informe o motorista.")
                    else:
                        sel_lista = selecionados.to_dict('records')
                        tomadores_unicos = list(set([str(r.get('TOMADOR', '')).strip() for r in sel_lista]))
                        
                        if len(tomadores_unicos) > 1:
                            st.error(f"🚨 VIOLAÇÃO DE ROTA: Destinos diferentes selecionados ({', '.join(tomadores_unicos)}). Use o filtro no topo.")
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
            else:
                st.info("O salão está vazio. Somente lotes validados na Triagem aparecem para despacho.")

        with t3:
            st.markdown("#### Histórico Analítico de Triagem e Despacho")
            status_mostrar = ['CONFERIDO', 'EM ROTA DE ENTREGA', 'ENTREGUE', 'FRUSTRADA', 'PROBLEMA', 'CANCELADO']
            df_hist = df_raw[df_raw['STATUS'].astype(str).str.upper().isin(status_mostrar)].copy()
            if not df_hist.empty:
                df_hist = df_hist.sort_values(by=['DATA_OBJ', 'PEDIDO'], ascending=[False, False])
                st.dataframe(df_hist[['DATA', 'PEDIDO', 'TOMADOR', 'LABORATORIO', 'CIDADE', 'STATUS', 'AGENTE_RAW', 'ROMANEIO']], hide_index=True, use_container_width=True)
            else:
                st.warning("O arquivo histórico de varreduras está temporariamente em branco.")
    else: 
        st.info("O banco de dados está vazio no momento.")

# =============================================================================
# 📱 MÓDULO EXTRA: DISPARO WHATSAPP (LOG, DISPARO EM MASSA E PDF OFICIAL)
# =============================================================================
elif menu == "📱 WhatsApp":
    st.markdown("<div class='dinamic-border'><h3 class='dinamic-text' style='margin:0;'>📱 Central Tática de Comunicação</h3></div>", unsafe_allow_html=True)
    df_raw = carregar_dados_completos(planilha_db)
    
    if not df_raw.empty:
        data_filtro = st.date_input("📅 Cronograma da Data (Filtro e Histórico):", value=hoje_br, format="DD/MM/YYYY")
        st.markdown("---")
        
        col_esq, col_dir = st.columns([2.5, 1.2])
        
        df_dia = df_raw[df_raw['DATA_OBJ'] == data_filtro].copy()
        df_pendentes = df_dia[df_dia['STATUS'].astype(str).str.upper() == 'PENDENTE'].copy()
        
        dict_telefones = {str(r.get('LOGIN DO AGENTE', '')).strip().lower(): re.sub(r'\D', '', str(r.get('TELEFONE', ''))) for _, r in DF_AGENTES.iterrows() if str(r.get('LOGIN DO AGENTE', '')).strip() and re.sub(r'\D', '', str(r.get('TELEFONE', '')))}
        dict_nomes = {str(r.get('LOGIN DO AGENTE', '')).strip().lower(): str(r.get('NOME DO AGENTE', '')).strip() for _, r in DF_AGENTES.iterrows() if str(r.get('LOGIN DO AGENTE', '')).strip()}
        
        # AGENTES COM ACESSO VIP AO EXCEL
        agentes_xls = ['veloz.express', 'robson.melo', 'william.bertoldo']

        with col_esq:
            if df_pendentes.empty:
                st.success(f"Nenhum volume PENDENTE aguardando envio na data {data_filtro.strftime('%d/%m/%Y')}.")
            else:
                agentes_com_rota = [ag for ag in df_pendentes['AGENTE_RAW'].dropna().unique() if str(ag).strip()]
                
                agentes_para_enviar = []
                for ag in agentes_com_rota:
                    df_ag = df_pendentes[df_pendentes['AGENTE_RAW'] == ag]
                    if not df_ag['ZAP_ENVIADO'].astype(str).apply(lambda x: str(x).startswith('SIM')).all():
                        agentes_para_enviar.append(ag)
                
                # 🔥 BOTÃO DE DISPARO EM MASSA 🔥
                if agentes_para_enviar:
                    st.info(f"🚀 Existem {len(agentes_para_enviar)} motoristas aguardando o envio da rota oficial.")
                    if st.button("🚀 DISPARAR ROTAS PARA TODOS AGORA", type="primary", use_container_width=True):
                        with st.spinner("Iniciando disparos em massa via Z-API... (isso pode levar alguns segundos)"):
                            pedidos_atualizados = []
                            sucessos = 0
                            
                            for agente in agentes_para_enviar:
                                df_agente = df_pendentes[(df_pendentes['AGENTE_RAW'] == agente) & (~df_pendentes['ZAP_ENVIADO'].astype(str).apply(lambda x: str(x).startswith('SIM')))]
                                telefone = dict_telefones.get(str(agente).strip().lower(), "")
                                nome_amigavel = dict_nomes.get(str(agente).strip().lower(), str(agente).upper())
                                agente_login = str(agente).strip().lower()
                                
                                if telefone:
                                    data_str = data_filtro.strftime('%d/%m/%Y')
                                    msg_parts = []
                                    msg_parts.append(f"Bom dia, {nome_amigavel}")
                                    msg_parts.append(f"🗓️ {data_str}\n")
                                    msg_parts.append("RESUMO DA ROTA:\n")
                                    msg_parts.append("CIDADE                  | QTD")
                                    msg_parts.append("-------------------------------")
                                    
                                    cidades_counts = df_agente['CIDADE'].value_counts()
                                    total_qtd = 0
                                    for cid, count in cidades_counts.items():
                                        cid_str = str(cid).strip().ljust(23)
                                        qtd_str = f"{count:02d}"
                                        msg_parts.append(f"{cid_str} | {qtd_str}")
                                        total_qtd += count
                                        
                                    msg_parts.append("-------------------------------")
                                    msg_parts.append(f"TOTAL                   | {total_qtd:02d}\n\n")
                                    msg_parts.append("⬇️ DETALHES:")
                                    msg_parts.append("========================\n")
                                    
                                    grouped = df_agente.groupby('CIDADE')
                                    for cid, group in grouped:
                                        cid_limpa = str(cid).strip()
                                        msg_parts.append("------------------------------")
                                        msg_parts.append(f"{cid_limpa.center(30)}")
                                        msg_parts.append("------------------------------\n")
                                        
                                        items = []
                                        for _, row in group.iterrows():
                                            item_str = f"> 🔸 PEDIDO: {row.get('PEDIDO', '')}\n"
                                            item_str += f"> 🔬 LABORATÓRIO: {row.get('LABORATORIO', '')}\n"
                                            item_str += f"> 📍 Rua: {row.get('ENDERECO', '')}, {row.get('NUMERO', '')}\n"
                                            item_str += f"> 🏘️ Bairro: {row.get('BAIRRO', '')}\n"
                                            item_str += f"> 📮 CEP: {row.get('CEP', '')}\n"
                                            item_str += f"> 🏢 Tomador: {row.get('TOMADOR', '')}"
                                            
                                            obs = str(row.get('OBSERVACOES', '')).strip()
                                            if obs and obs.upper() != 'NAN': 
                                                item_str += f"\n> 📝 Aviso: {obs}"
                                            items.append(item_str)
                                            
                                        msg_parts.append("\n\n      . . . . .\n\n".join(items))
                                        msg_parts.append("\n")
                                        
                                    msg_final = "\n".join(msg_parts)
                                    
                                    # 1️⃣ Dispara o Texto
                                    if enviar_whatsapp_zapi(telefone, msg_final):
                                        time.sleep(2.0) # 🐢 Tempo de respiro do robô
                                        
                                        # 2️⃣ Gera e Dispara o PDF Oficial
                                        pdf_bytes = gerar_pdf_rota_whatsapp(nome_amigavel, data_str, df_agente)
                                        nome_pdf = f"ROTA_IGO_{nome_amigavel.replace(' ', '_')}_{data_filtro.strftime('%d%m')}.pdf"
                                        enviar_pdf_zapi(telefone, pdf_bytes, nome_pdf)
                                        
                                        # 3️⃣ Gera e Dispara o EXCEL de Luxo se for VIP
                                        if agente_login in agentes_xls:
                                            time.sleep(3.0) # 🐢 Tempo de respiro maior
                                            xls_bytes = gerar_excel_rota_whatsapp(df_agente)
                                            nome_xls = f"ROTA_ESTRUTURADA_{nome_amigavel.replace(' ', '_')}_{data_filtro.strftime('%d%m')}.xlsx"
                                            enviar_excel_zapi(telefone, xls_bytes, nome_xls)
                                        
                                        sucessos += 1
                                        pedidos_atualizados.extend(df_agente['PEDIDO'].tolist())
                                    time.sleep(1.5) 
                            
                            if pedidos_atualizados:
                                try:
                                    aba = planilha_db.worksheet("Memoria_Sistema")
                                    df_nuvem = pd.DataFrame(aba.get_all_values()[1:], columns=aba.get_all_values()[0])
                                    if 'ZAP_ENVIADO' not in df_nuvem.columns: df_nuvem['ZAP_ENVIADO'] = ""
                                    hora_atual = datetime.now(FUSO_BR).strftime('%H:%M')
                                    df_nuvem.loc[df_nuvem['PEDIDO'].isin(pedidos_atualizados), 'ZAP_ENVIADO'] = f"SIM|{hora_atual}"
                                    aba.clear()
                                    aba.update("A1", [df_nuvem.columns.tolist()] + df_nuvem.fillna("").astype(str).values.tolist())
                                    carregar_dados_completos.clear()
                                except Exception as e:
                                    st.error(f"Erro ao carimbar envio no banco: {e}")
                            
                            st.success(f"🎉 Disparo em massa concluído! {sucessos} motoristas receberam os arquivos.")
                            time.sleep(2.5)
                            st.rerun()
                else:
                    st.success("✅ Excelente! Todos os motoristas com rotas pendentes nesta data já receberam as mensagens.")
                
                st.markdown("---")
                
                # 🔥 LISTA DE MOTORISTAS COM O SELO 🔥
                for agente in sorted(agentes_com_rota):
                    df_agente = df_pendentes[df_pendentes['AGENTE_RAW'] == agente]
                    telefone = dict_telefones.get(str(agente).strip().lower(), "")
                    nome_amigavel = dict_nomes.get(str(agente).strip().lower(), str(agente).upper())
                    agente_login = str(agente).strip().lower()
                    
                    todos_enviados = df_agente['ZAP_ENVIADO'].astype(str).apply(lambda x: str(x).startswith('SIM')).all()
                    selo = "✅ ENVIADO" if todos_enviados else "⏳ PENDENTE"
                    tag_vip = " 🌟 [RECEBE EXCEL]" if agente_login in agentes_xls else ""
                    
                    with st.expander(f"{selo} | 👤 {nome_amigavel}{tag_vip} | Volumes: {len(df_agente)}", expanded=not todos_enviados):
                        st.dataframe(df_agente[['PEDIDO', 'TOMADOR', 'LABORATORIO', 'CIDADE']], hide_index=True)
                        
                        if telefone:
                            data_str = data_filtro.strftime('%d/%m/%Y')
                            msg_parts = []
                            msg_parts.append(f"Bom dia, {nome_amigavel}")
                            msg_parts.append(f"🗓️ {data_str}\n")
                            msg_parts.append("RESUMO DA ROTA:\n")
                            msg_parts.append("CIDADE                  | QTD")
                            msg_parts.append("-------------------------------")
                            
                            cidades_counts = df_agente['CIDADE'].value_counts()
                            total_qtd = 0
                            for cid, count in cidades_counts.items():
                                cid_str = str(cid).strip().ljust(23)
                                qtd_str = f"{count:02d}"
                                msg_parts.append(f"{cid_str} | {qtd_str}")
                                total_qtd += count
                                
                            msg_parts.append("-------------------------------")
                            msg_parts.append(f"TOTAL                   | {total_qtd:02d}\n\n")
                            msg_parts.append("⬇️ DETALHES:")
                            msg_parts.append("========================\n")
                            
                            grouped = df_agente.groupby('CIDADE')
                            for cid, group in grouped:
                                cid_limpa = str(cid).strip()
                                msg_parts.append("------------------------------")
                                msg_parts.append(f"{cid_limpa.center(30)}")
                                msg_parts.append("------------------------------\n")
                                
                                items = []
                                for _, row in group.iterrows():
                                    item_str = f"> 🔸 PEDIDO: {row.get('PEDIDO', '')}\n"
                                    item_str += f"> 🔬 LABORATÓRIO: {row.get('LABORATORIO', '')}\n"
                                    item_str += f"> 📍 Rua: {row.get('ENDERECO', '')}, {row.get('NUMERO', '')}\n"
                                    item_str += f"> 🏘️ Bairro: {row.get('BAIRRO', '')}\n"
                                    item_str += f"> 📮 CEP: {row.get('CEP', '')}\n"
                                    item_str += f"> 🏢 Tomador: {row.get('TOMADOR', '')}"
                                    
                                    obs = str(row.get('OBSERVACOES', '')).strip()
                                    if obs and obs.upper() != 'NAN': 
                                        item_str += f"\n> 📝 Aviso: {obs}"
                                    items.append(item_str)
                                    
                                msg_parts.append("\n\n      . . . . .\n\n".join(items))
                                msg_parts.append("\n")
                                
                            msg_final = "\n".join(msg_parts)
                            
                            texto_botao = "🔄 Reenviar Arquivos" if todos_enviados else f"📲 Disparar Rota para {nome_amigavel}"
                            if st.button(texto_botao, key=f"zap_api_ind_{agente}", type="primary" if not todos_enviados else "secondary"):
                                with st.spinner("Enviando pacote completo via satélite..."):
                                    
                                    # 1️⃣ Manda o Texto
                                    sucesso_texto = enviar_whatsapp_zapi(telefone, msg_final)
                                    
                                    if sucesso_texto:
                                        time.sleep(2.0) # 🐢 Tempo de respiro do robô
                                        
                                        # 2️⃣ Gera e Manda o PDF
                                        pdf_bytes = gerar_pdf_rota_whatsapp(nome_amigavel, data_str, df_agente)
                                        nome_pdf = f"ROTA_IGO_{nome_amigavel.replace(' ', '_')}_{data_filtro.strftime('%d%m')}.pdf"
                                        enviar_pdf_zapi(telefone, pdf_bytes, nome_pdf)
                                        
                                        # 3️⃣ Gera e Manda o Excel Se for VIP
                                        if agente_login in agentes_xls:
                                            time.sleep(3.0) # 🐢 Tempo de respiro maior
                                            xls_bytes = gerar_excel_rota_whatsapp(df_agente)
                                            nome_xls = f"ROTA_ESTRUTURADA_{nome_amigavel.replace(' ', '_')}_{data_filtro.strftime('%d%m')}.xlsx"
                                            enviar_excel_zapi(telefone, xls_bytes, nome_xls)
                                        
                                        try:
                                            aba = planilha_db.worksheet("Memoria_Sistema")
                                            df_nuvem = pd.DataFrame(aba.get_all_values()[1:], columns=aba.get_all_values()[0])
                                            if 'ZAP_ENVIADO' not in df_nuvem.columns: df_nuvem['ZAP_ENVIADO'] = ""
                                            hora_atual = datetime.now(FUSO_BR).strftime('%H:%M')
                                            df_nuvem.loc[df_nuvem['PEDIDO'].isin(df_agente['PEDIDO'].tolist()), 'ZAP_ENVIADO'] = f"SIM|{hora_atual}"
                                            aba.clear()
                                            aba.update("A1", [df_nuvem.columns.tolist()] + df_nuvem.fillna("").astype(str).values.tolist())
                                            carregar_dados_completos.clear()
                                        except Exception as e:
                                            st.error(f"Erro ao carimbar envio: {e}")
                                            
                                        st.success(f"✅ Rota e arquivos enviados com sucesso para {nome_amigavel}!")
                                        time.sleep(1.5)
                                        st.rerun()
                                    else:
                                        st.error("🚨 Falha ao enviar o texto principal.")
                        else: 
                            st.error(f"⚠️ Telefone do agente '{agente}' não encontrado.")
        
        with col_dir:
            with st.container(border=True):
                st.markdown("<h4 style='color:#0F172A; margin-top:0px; font-size:16px;'>⏱️ Log de Disparos</h4>", unsafe_allow_html=True)
                st.divider()
                
                log_list = []
                agentes_dia = [ag for ag in df_dia['AGENTE_RAW'].dropna().unique() if str(ag).strip()]
                
                for ag in agentes_dia:
                    df_ag_log = df_dia[df_dia['AGENTE_RAW'] == ag]
                    status_s = df_ag_log['ZAP_ENVIADO'].dropna().astype(str).tolist()
                    sent_statuses = [s for s in status_s if str(s).startswith('SIM')]
                    if sent_statuses:
                        tempos = [s.split('|')[1] for s in sent_statuses if '|' in s]
                        hora = tempos[0] if tempos else "Desconhecida"
                        nome_amigavel = dict_nomes.get(str(ag).strip().lower(), str(ag).upper())
                        log_list.append({"agente": nome_amigavel, "hora": hora})
                        
                log_list.sort(key=lambda x: x["hora"], reverse=True)
                
                if log_list:
                    for item in log_list:
                        st.markdown(f"""
                        <div style='padding:10px; background-color:#F8FAFC; border-left: 4px solid #10B981; margin-bottom:10px; border-radius:4px;'>
                            <b style='color:#334155; font-size:13px;'>👤 {item['agente']}</b><br>
                            <span style='color:#64748B; font-size:12px;'>✅ Enviado às {item['hora']}</span>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("Nenhum disparo registrado para esta data ainda.")
    else:
        st.warning("O banco de dados está vazio.")

# =============================================================================
# 📥 MÓDULO 4: EXPORTAR RELATÓRIOS
# =============================================================================
elif menu == "📁 Relatórios":
    st.markdown("<div class='dinamic-border'><h3 class='dinamic-text' style='margin:0;'>📥 Central de Datamining e Exportação</h3></div>", unsafe_allow_html=True)
    df_raw = carregar_dados_completos(planilha_db)
    if not df_raw.empty:
        df_export_base = df_raw[['DATA', 'PEDIDO', 'TOMADOR', 'LABORATORIO', 'ENDERECO', 'NUMERO', 'BAIRRO', 'CIDADE', 'UF', 'CEP', 'STATUS', 'DATA_ENTREGA', 'AGENTE_RAW', 'DATA_LIMITE']].copy().rename(columns={'AGENTE_RAW': 'MOTORISTA'})
        col_rel1, col_rel2, col_rel3 = st.columns(3)
        df_rj = df_export_base[df_export_base['UF'].str.upper() == 'RJ'] if 'UF' in df_export_base.columns else pd.DataFrame()
        df_jf = df_export_base[df_export_base['CIDADE'].str.upper().str.contains('JUIZ DE FORA', na=False)] if 'CIDADE' in df_export_base.columns else pd.DataFrame()
        df_rjjf = pd.concat([df_rj, df_jf]).drop_duplicates(subset=['PEDIDO'])
        
        if not df_rjjf.empty: 
            col_rel1.download_button("📥 Minerar Bloco RJ / JF", data=gerar_excel_memoria(df_rjjf), file_name=f"RJ_JF_{datetime.now(FUSO_BR).strftime('%d%m%Y')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
        else: 
            col_rel1.button("📥 Minerar Bloco RJ / JF (Zero)", disabled=True, use_container_width=True)
        
        df_lud = df_export_base[df_export_base['MOTORISTA'].str.lower().str.contains('ludmila|veloz', na=False)] if 'MOTORISTA' in df_export_base.columns else pd.DataFrame()
        
        if not df_lud.empty: 
            col_rel2.download_button("📥 Minerar Ludmila / Veloz", data=gerar_excel_memoria(df_lud), file_name=f"Ludmila_{datetime.now(FUSO_BR).strftime('%d%m%Y')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
        else: 
            col_rel2.button("📥 Minerar Ludmila / Veloz (Zero)", disabled=True, use_container_width=True)
        
        col_rel3.download_button("📥 Extração Completa (Nuvem)", data=gerar_excel_memoria(df_export_base), file_name=f"BKP_{datetime.now(FUSO_BR).strftime('%d%m%Y')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary", use_container_width=True)
        
        st.markdown("---")
        with st.form("form_rel_custom"):
            cf1, cf2 = st.columns(2)
            c_ag = cf1.text_input("👤 Codinome do Agente:")
            c_cid = cf2.text_input("🏙️ Raio de Busca (Cidade):")
            c_uf = cf1.text_input("🗺️ Vetor Estadual (UF):")
            c_base = cf2.text_input("🏢 Hub Logístico (Tomador/Clínica):")
            if st.form_submit_button("Executar Pesquisa e Compilar Tabela"):
                df_custom = df_export_base.copy()
                if c_ag and 'MOTORISTA' in df_custom.columns: 
                    df_custom = df_custom[df_custom['MOTORISTA'].str.upper().str.contains(c_ag.upper(), na=False)]
                if c_cid and 'CIDADE' in df_custom.columns: 
                    df_custom = df_custom[df_custom['CIDADE'].str.upper().str.contains(c_cid.upper(), na=False)]
                if c_uf and 'UF' in df_custom.columns: 
                    df_custom = df_custom[df_custom['UF'].str.upper() == c_uf.upper()]
                if c_base: 
                    df_custom = df_custom[df_custom['TOMADOR'].str.upper().str.contains(c_base.upper(), na=False) | df_custom['LABORATORIO'].str.upper().str.contains(c_base.upper(), na=False)]
                
                if not df_custom.empty: 
                    st.download_button("📥 Fazer Download do Relatório Cru (Excel)", data=gerar_excel_memoria(df_custom), file_name=f"Pesquisa_Customizada_IGO.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                else: 
                    st.warning("Nenhum dado encontrado.")
    else: 
        st.warning("O banco de dados está vazio.")

# =============================================================================
# ⚙️ MÓDULO 5: CONFIGURAR ROTAS E AGENTES
# =============================================================================
elif menu == "⚙️ Rotas":
    st.markdown("<div class='dinamic-border'><h3 class='dinamic-text' style='margin:0;'>⚙️ Matriz Inteligente de Rotas e Equipe</h3></div>", unsafe_allow_html=True)
    tab_agente, tab_rota, tab_tabela = st.tabs(["👤 Cadastrar Novo Agente", "📍 Adicionar Rota (Vincular)", "📋 Gerenciar Motorista Específico"])
    
    with tab_agente:
        with st.form("form_novo_agente", clear_on_submit=True):
            c1, c2 = st.columns(2)
            login_ag = c1.text_input("ID de Login", placeholder="Ex: carlos.rj")
            nome_ag = c2.text_input("Nome Amigável", placeholder="Ex: CARLOS SILVA")
            tel_ag = st.text_input("WhatsApp com DDD", placeholder="Ex: 5521999999999")
            if st.form_submit_button("💾 Salvar Novo Agente", type="primary"):
                if not login_ag or not nome_ag or not tel_ag: 
                    st.error("⚠️ Preencha todos os campos!")
                else:
                    df_novo = pd.concat([DF_AGENTES, pd.DataFrame([{"ROTA MAPEADA": "SEM ROTA DEFINIDA", "LOGIN DO AGENTE": login_ag.lower().strip(), "NOME DO AGENTE": nome_ag.upper().strip(), "TELEFONE": re.sub(r'\D', '', tel_ag)}])], ignore_index=True)
                    try:
                        planilha_db.worksheet("Agentes").update("A1", [df_novo.columns.tolist()] + df_novo.fillna("").astype(str).values.tolist())
                        st.success(f"✅ Agente salvo!")
                        carregar_dados_agentes.clear()
                    except Exception as e: 
                        st.error(f"Erro: {e}")
                        
    with tab_rota:
        with st.form("form_nova_rota", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            cid_rota = c1.text_input("Cidade *", placeholder="Ex: SAO PAULO")
            bai_rota = c2.text_input("Bairro (Opcional)")
            rua_rota = c3.text_input("Endereço (Opcional)")
            ag_selecionado = st.selectbox("Selecione o Agente:", sorted(DF_AGENTES['LOGIN DO AGENTE'].unique().tolist()) if not DF_AGENTES.empty else [])
            if st.form_submit_button("📍 Salvar Nova Rota", type="primary"):
                if not cid_rota or not ag_selecionado: 
                    st.error("⚠️ Cidade e Agente são obrigatórios!")
                else:
                    rota_str = " ➔ ".join([p for p in [limpar_nome_local_rota(cid_rota), limpar_nome_local_rota(bai_rota), tratar_texto_global(rua_rota)] if p])
                    dados_ag = DF_AGENTES[DF_AGENTES['LOGIN DO AGENTE'] == ag_selecionado].iloc[0]
                    df_novo = pd.concat([DF_AGENTES, pd.DataFrame([{"ROTA MAPEADA": rota_str, "LOGIN DO AGENTE": ag_selecionado, "NOME DO AGENTE": dados_ag['NOME DO AGENTE'], "TELEFONE": dados_ag['TELEFONE']}])], ignore_index=True)
                    try:
                        planilha_db.worksheet("Agentes").update("A1", [df_novo.columns.tolist()] + df_novo.fillna("").astype(str).values.tolist())
                        st.success(f"✅ Rota atrelada!")
                        carregar_dados_agentes.clear()
                    except Exception as e: 
                        st.error(f"Erro: {e}")
                        
    with tab_tabela:
        if not DF_AGENTES.empty:
            agente_filtro = st.selectbox("👤 Selecione o Motorista para gerenciar apenas suas rotas:", sorted(DF_AGENTES['LOGIN DO AGENTE'].unique().tolist()))
            with st.form(f"form_rapido_{agente_filtro}", clear_on_submit=True):
                ca1, ca2, ca3, ca4 = st.columns([2, 2, 2, 1])
                r_cid = ca1.text_input("Cidade")
                r_bai = ca2.text_input("Bairro (Opç)")
                r_rua = ca3.text_input("Endereço (Opç)")
                if ca4.form_submit_button("➕ Salvar", use_container_width=True):
                    if not r_cid: 
                        st.error("A Cidade é obrigatória!")
                    else:
                        rota_str = " ➔ ".join([p for p in [limpar_nome_local_rota(r_cid), limpar_nome_local_rota(bai_rota), tratar_texto_global(r_rua)] if p])
                        dados_ag = DF_AGENTES[DF_AGENTES['LOGIN DO AGENTE'] == agente_filtro].iloc[0]
                        df_novo = pd.concat([DF_AGENTES, pd.DataFrame([{"ROTA MAPEADA": rota_str, "LOGIN DO AGENTE": agente_filtro, "NOME DO AGENTE": dados_ag['NOME DO AGENTE'], "TELEFONE": dados_ag['TELEFONE']}])], ignore_index=True)
                        try:
                            planilha_db.worksheet("Agentes").update("A1", [df_novo.columns.tolist()] + df_novo.fillna("").astype(str).values.tolist())
                            st.success("Rota adicionada!")
                            time.sleep(0.5)
                            carregar_dados_agentes.clear()
                            st.rerun()
                        except Exception as e: 
                            st.error(f"Erro ao salvar: {e}")
                            
            df_ag_filtrado = DF_AGENTES[DF_AGENTES['LOGIN DO AGENTE'] == agente_filtro].copy()
            if df_ag_filtrado.empty: 
                st.warning("Nenhuma rota atrelada.")
            else:
                for idx, row in df_ag_filtrado.iterrows():
                    col_rota, col_del = st.columns([5, 1])
                    col_rota.markdown(f"<div style='padding:10px; background-color:#FFFFFF; border-radius:5px; border: 1px solid #E2E8F0;'><b>📍 {row['ROTA MAPEADA'].replace('---', ' ➔ ')}</b></div>", unsafe_allow_html=True)
                    if col_del.button("🗑️ Remover", key=f"del_{idx}", use_container_width=True):
                        try:
                            planilha_db.worksheet("Agentes").update("A1", [DF_AGENTES.drop(idx).columns.tolist()] + DF_AGENTES.drop(idx).fillna("").astype(str).values.tolist())
                            time.sleep(0.5)
                            carregar_dados_agentes.clear()
                            st.rerun()
                        except Exception as e: 
                            st.error(f"Erro ao remover: {e}")
        else: 
            st.warning("Nenhum dado encontrado.")
