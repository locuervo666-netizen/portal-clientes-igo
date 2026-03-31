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
from datetime import datetime, timedelta, timezone
import random
import gspread
import uuid
from streamlit_autorefresh import st_autorefresh
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, GridUpdateMode
from fpdf import FPDF

FUSO_BR = timezone(timedelta(hours=-3))

# =============================================================================
# 🔗 1. CONFIGURAÇÃO DA PÁGINA E AUTENTICAÇÃO (NOVO COFRE)
# =============================================================================
st.set_page_config(page_title="Sistema - IGO Logística", layout="wide", page_icon="🚚", initial_sidebar_state="expanded")
st_autorefresh(interval=60000, limit=None, key="refresh_timer")

# Cria a variável de segurança se ela não existir
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

# Se não estiver logado, mostra a tela de login e PARALISA o resto do sistema
if not st.session_state.autenticado:
    st.markdown("<br><br><br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    
    with col2:
        with st.container(border=True):
            st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
            
            # 🟢 DICA: Para usar a sua logomarca real, coloque a imagem na pasta do sistema 
            # com o nome "logo.png" e apague o caractere '#' da linha abaixo:
            # st.image("logo.png", use_container_width=True) 
            
            st.markdown("<h1 style='color: #38BDF8;'>🚚 IGO Logística</h1>", unsafe_allow_html=True)
            st.markdown("<p style='color: gray;'>Acesso Restrito ao Painel Operacional</p>", unsafe_allow_html=True)
            st.markdown("</div><br>", unsafe_allow_html=True)
            
            with st.form("form_login"):
                usuario = st.text_input("👤 Usuário")
                senha = st.text_input("🔑 Senha", type="password")
                submit = st.form_submit_button("Entrar no Sistema", use_container_width=True, type="primary")
                
                if submit:
                    # 🟢 VOCÊ PODE ALTERAR O USUÁRIO E SENHA AQUI:
                    if usuario == "admin" and senha == "igo2026":
                        st.session_state.autenticado = True
                        st.rerun()
                    else:
                        st.error("Usuário ou senha incorretos.")
    
    # O comando st.stop() é o que impede que o resto da página carregue se não houver login
    st.stop()


# =============================================================================
# 🔗 2. CONEXÃO COM A NUVEM E CÉREBRO DE DADOS (ÁREA PROTEGIDA)
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
            try:
                aba_app = _planilha.worksheet("App_Tarefas")
                dados_app = aba_app.get_all_values()
                if len(dados_app) > 1:
                    df_app = pd.DataFrame(dados_app[1:], columns=dados_app[0])
                    cols_limpas = [str(c).upper().strip().replace('?', '').replace(' ', '') for c in df_app.columns]
                    df_app.columns = cols_limpas
                    
                    cols_to_extract = ['PEDIDO', 'STATUS', 'OBSERVACOES']
                    if 'FOTO' in df_app.columns: cols_to_extract.append('FOTO')
                    
                    col_qr_app = None
                    for c in ['QR_CODE', 'QRCODE', 'QR', 'CODIGO']:
                        if c in df_app.columns:
                            col_qr_app = c
                            break
                    if col_qr_app: cols_to_extract.append(col_qr_app)
                    
                    df_app_clean = df_app[[c for c in cols_to_extract if c in df_app.columns]].copy()
                    rename_map = {'STATUS': 'APP_STATUS', 'OBSERVACOES': 'APP_OBS', 'FOTO': 'APP_FOTO'}
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

def carregar_dicionario_rotas(df_agentes):
    base_agentes = {}
    if not df_agentes.empty:
        for _, row in df_agentes.iterrows():
            rota = str(row["ROTA MAPEADA"]).strip().replace(" ➔ ", "---")
            login = str(row["LOGIN DO AGENTE"]).strip().lower()
            if rota and rota != "SEM ROTA DEFINIDA": base_agentes[rota] = login
    return base_agentes
BASE_AGENTES = carregar_dicionario_rotas(DF_AGENTES)

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

# =============================================================================
# 🎨 3. INTERFACE E NAVEGAÇÃO PREMIUM (ÁREA LOGADA)
# =============================================================================

if 'modo_escuro' not in st.session_state: st.session_state.modo_escuro = False

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
    [data-testid="stSidebarNav"] {display: none;}
    
    div.stRadio > div[role="radiogroup"] { display: flex; flex-direction: column; gap: 8px; width: 100% !important; }
    div[role="radiogroup"] > label {
        width: 100% !important; padding: 12px 16px !important; border-radius: 8px !important;
        margin: 0 !important; border: none !important; background-color: transparent !important;
        cursor: pointer !important; transition: all 0.2s ease-in-out !important; box-sizing: border-box !important;
    }
    div[role="radiogroup"] > label:hover { background-color: rgba(56, 189, 248, 0.08) !important; }
    div[role="radiogroup"] label div[data-testid="stRadio-radio"] { display: none !important; }
    div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p { 
        font-size: 15px !important; font-weight: 600 !important; margin: 0 !important;
        color: #64748b !important; transition: color 0.2s ease !important;
    }
    div[role="radiogroup"] > label[data-checked="true"] { 
        background-color: rgba(56, 189, 248, 0.12) !important; border-left: 4px solid #38BDF8 !important; border-radius: 0 8px 8px 0 !important;
    }
    div[role="radiogroup"] > label[data-checked="true"] div[data-testid="stMarkdownContainer"] p { color: #0284c7 !important; font-weight: 700 !important; }

    div.st-key-kpi_total button { background: linear-gradient(135deg, #1E3A8A 0%, #3B82F6 100%) !important; height: 75px !important; border-radius: 8px !important; border: none !important; color: white !important;}
    div.st-key-kpi_entregue button { background: linear-gradient(135deg, #064E3B 0%, #10B981 100%) !important; height: 75px !important; border-radius: 8px !important; border: none !important; color: white !important;}
    div.st-key-kpi_frus button { background: linear-gradient(135deg, #9A3412 0%, #F59E0B 100%) !important; height: 75px !important; border-radius: 8px !important; border: none !important; color: white !important;}
    div.st-key-kpi_atra button { background: linear-gradient(135deg, #7F1D1D 0%, #EF4444 100%) !important; height: 75px !important; border-radius: 8px !important; border: none !important; color: white !important;}
    div.st-key-kpi_hoje button { background: linear-gradient(135deg, #4C1D95 0%, #8B5CF6 100%) !important; height: 75px !important; border-radius: 8px !important; border: none !important; color: white !important;}
    div.st-key-kpi_total button p, div.st-key-kpi_entregue button p, div.st-key-kpi_frus button p, div.st-key-kpi_atra button p, div.st-key-kpi_hoje button p { font-weight: 800 !important; font-size: 15px !important; margin: 0 !important; color: white !important;}
    </style>
""", unsafe_allow_html=True)

if 'filtro_kpi_admin' not in st.session_state: st.session_state.filtro_kpi_admin = "TODOS"

with st.sidebar:
    col_logo, col_tema = st.columns([3, 1], vertical_alignment="center")
    
    # 🔥 AQUI ESTÁ A LOGO NA BARRA LATERAL (Removido o IGO ADMIN)
    with col_logo: 
        # st.image("https://i.postimg.cc/x84nnjjq/IGO-LOGO.png", use_container_width=True) # Descomente para usar a imagem
        st.markdown("<h3 style='color:#38BDF8; margin: 0; padding-bottom: 5px; font-weight: 800;'>SISTEMA IGO</h3>", unsafe_allow_html=True)
    
    with col_tema: st.session_state.modo_escuro = st.toggle("🌙", value=st.session_state.modo_escuro, label_visibility="collapsed", help="Alternar Modo Claro/Escuro")
    
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    menu = st.radio("Navegação:", ["📊 Dashboard de Controle", "📝 Novo Pedido Manual", "➕ Importação de Lotes", "📋 Triagem e Romaneio", "📱 Disparo WhatsApp", "📥 Exportar Relatórios", "⚙️ Configurar Rotas"], label_visibility="collapsed")
    st.markdown("<div style='margin-top: 100%;'></div>", unsafe_allow_html=True)
    st.divider()
    
    # 🔥 BOTÃO DE SAIR AGORA DESTROI A SESSÃO (LOGOUT)
    if st.button("🚪 Sair do Sistema", use_container_width=True, type="secondary"):
        st.session_state.autenticado = False
        st.cache_data.clear(); st.cache_resource.clear(); st.rerun()
        
    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
    with st.expander("🛡️ Backup de Segurança"):
        st.markdown("<p style='font-size: 12px; color: gray;'>Gere uma cópia física completa de todo o histórico do banco de dados.</p>", unsafe_allow_html=True)
        df_bkp = carregar_dados_completos(planilha_db)
        if not df_bkp.empty:
            st.download_button(
                label="📥 Baixar Backup (.xlsx)", 
                data=gerar_excel_memoria(df_bkp), 
                file_name=f"BKP_IGO_Logistica_{datetime.now(FUSO_BR).strftime('%d%m%Y_%H%M')}.xlsx", 
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
                use_container_width=True,
                type="primary"
            )

bg_app = "#0e1117" if st.session_state.modo_escuro else "#f8fafc"
bg_side = "#161b22" if st.session_state.modo_escuro else "#ffffff"
txt_main = "#f8fafc" if st.session_state.modo_escuro else "#0f172a"
txt_menu = "#cbd5e1" if st.session_state.modo_escuro else "#64748b"
txt_menu_ativo = "#38bdf8" if st.session_state.modo_escuro else "#0284c7"
border_c = "#334155" if st.session_state.modo_escuro else "#e2e8f0"

st.markdown(f"""<style>
[data-testid="stAppViewContainer"] {{ background-color: {bg_app} !important; }}
[data-testid="stSidebar"] {{ background-color: {bg_side} !important; border-right: 1px solid {border_c}; padding-top: 2rem !important; }}
.dinamic-text {{ color: {txt_main} !important; }}
.dinamic-border {{ border-bottom: 2px solid {border_c} !important; }}
div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p {{ color: {txt_menu} !important; }}
div[role="radiogroup"] > label[data-checked="true"] div[data-testid="stMarkdownContainer"] p {{ color: {txt_menu_ativo} !important; }}
</style>""", unsafe_allow_html=True)

def obter_css_grid():
    base_css = {
        ".ag-root-wrapper": {"border": f"1px solid {border_c} !important", "border-radius": "6px"},
        ".ag-header": {"background-color": "#1e293b !important"},
        ".ag-header-cell-text": {"color": "#f8fafc !important", "font-weight": "bold", "font-size": "13px !important"},
        ".ag-cell": {"font-size": "13px !important", "display": "flex", "align-items": "center"},
        ".ag-row-selected": {"background-color": "#3B82F6 !important", "color": "#ffffff !important"},
        ".ag-row-selected .ag-cell": {"color": "#ffffff !important"}
    }
    if st.session_state.modo_escuro:
        base_css.update({
            ".ag-root-wrapper": {"background-color": "#0e1117 !important", "border-color": "#334155 !important"},
            ".ag-cell": {"color": "#e2e8f0 !important", "border-bottom": "1px solid #1e293b !important"},
            ".ag-row-even": {"background-color": "#0f172a !important"}, ".ag-row-odd": {"background-color": "#161b22 !important"}, 
            ".ag-row-hover": {"background-color": "#334155 !important"}
        })
    else:
        base_css.update({
            ".ag-cell": {"color": "#334155 !important", "border-bottom": "1px solid #f1f5f9 !important"},
            ".ag-row-even": {"background-color": "#ffffff !important"}, ".ag-row-odd": {"background-color": "#f8fafc !important"}, 
            ".ag-row-hover": {"background-color": "#e2e8f0 !important"}
        })
    return base_css

# =============================================================================
# 🚀 MÓDULO 1: DASHBOARD DE CONTROLE
# =============================================================================
if menu == "📊 Dashboard de Controle":
    df_raw = carregar_dados_completos(planilha_db)
    
    if not df_raw.empty:
        df_raw['FOTO_URL'] = df_raw['FOTO'].apply(lambda x: f"https://www.appsheet.com/template/gettablefileurl?appName=APPIGOLOGISTICA-153047553&tableName=App_Tarefas&fileName={str(x).strip()}" if str(x).strip() and str(x).upper() not in ['NAN', 'NONE', ''] else "")
        
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
                    if datetime.strptime(previsao, "%d/%m/%Y").date() < hoje_br: res = f"🚨 ATRASADO ({res})"
                except: pass
            return res

        df_raw['STATUS_DISPLAY'] = df_raw.apply(calc_status_display, axis=1)
        
        if 'DATA_LIMITE' in df_raw.columns: df_raw['DATA_LIMITE'] = df_raw['DATA_LIMITE'].fillna("").astype(str)
        if 'DATA_ENTREGA' in df_raw.columns: df_raw['DATA_ENTREGA'] = df_raw['DATA_ENTREGA'].fillna("").astype(str)

        st.markdown("<div class='dinamic-border' style='padding-bottom: 10px; margin-bottom: 20px;'><h4 class='dinamic-text' style='margin:0;'>📊 Painel de Controle Operacional</h4></div>", unsafe_allow_html=True)

        col_f1, col_f2 = st.columns(2)
        f_cli = col_f1.selectbox("🏢 Filtrar por Tomador:", ["Todos"] + CLIENTES_AUTORIZADOS)
        f_data = col_f2.date_input("📅 Período de Análise:", value=(df_raw['DATA_OBJ'].min(), hoje_br))
        
        df_f = df_raw.copy()
        if f_cli != "Todos": df_f = df_f[df_f['TOMADOR'] == f_cli]
        if isinstance(f_data, tuple) and len(f_data) == 2: df_f = df_f[(df_f['DATA_OBJ'] >= f_data[0]) & (df_f['DATA_OBJ'] <= f_data[1])]

        n_tot, n_ent = len(df_f), len(df_f[df_f['STATUS_DISPLAY'].str.contains('Entregue')])
        n_frus, n_atra = len(df_f[df_f['STATUS_DISPLAY'].str.contains('Frustrada')]), len(df_f[df_f['STATUS_DISPLAY'].str.contains('ATRASADO')])
        n_hoje = len(df_f[df_f['DATA_OBJ'] == hoje_br])

        c1, c2, c3, c4, c5 = st.columns(5)
        def set_kpi(v): st.session_state.filtro_kpi_admin = v
        c1.button(f"📦 TOTAL\n\n{n_tot}", key="kpi_total", use_container_width=True, on_click=set_kpi, args=("TODOS",))
        c2.button(f"✅ ENTREGUES\n\n{n_ent}", key="kpi_entregue", use_container_width=True, on_click=set_kpi, args=("ENTREGUE",))
        c3.button(f"❌ FRUSTRADAS\n\n{n_frus}", key="kpi_frus", use_container_width=True, on_click=set_kpi, args=("FRUSTRADA",))
        c4.button(f"🚨 ATRASADOS\n\n{n_atra}", key="kpi_atra", use_container_width=True, on_click=set_kpi, args=("ATRASADO",))
        c5.button(f"📅 HOJE\n\n{n_hoje}", key="kpi_hoje", use_container_width=True, on_click=set_kpi, args=("HOJE",))

        st.markdown("<br>", unsafe_allow_html=True)
        busca = st.text_input("🔎 Busca Rápida na Tabela (Qualquer campo):", placeholder="Ex: Nome do Lab, Cidade, Pedido...")

        df_grid = df_f.copy()
        if st.session_state.filtro_kpi_admin == "ENTREGUE": df_grid = df_grid[df_grid['STATUS_DISPLAY'].str.contains('Entregue')]
        elif st.session_state.filtro_kpi_admin == "FRUSTRADA": df_grid = df_grid[df_grid['STATUS_DISPLAY'].str.contains('Frustrada')]
        elif st.session_state.filtro_kpi_admin == "ATRASADO": df_grid = df_grid[df_grid['STATUS_DISPLAY'].str.contains('ATRASADO')]
        elif st.session_state.filtro_kpi_admin == "HOJE": df_grid = df_grid[df_grid['DATA_OBJ'] == hoje_br]
        
        colunas_mostrar = ['DATA', 'PEDIDO', 'TOMADOR', 'STATUS_DISPLAY', 'AGENTE_RAW', 'LABORATORIO', 'CIDADE', 'UF', 'DATA_LIMITE', 'DATA_ENTREGA', 'FOTO_URL', 'ENDERECO', 'NUMERO', 'BAIRRO', 'CEP']
        df_grid = df_grid[[c for c in colunas_mostrar if c in df_grid.columns]]
        
        if busca:
            mask = df_grid.astype(str).apply(lambda x: busca.upper() in x.str.upper().values, axis=1)
            df_grid = df_grid[mask]

        st.markdown(f"<p class='dinamic-text' style='color:#10B981 !important; font-weight:bold; font-size:12px; margin-bottom: 5px;'>🟢 Sincronizado: {datetime.now(FUSO_BR).strftime('%H:%M')}</p>", unsafe_allow_html=True)
        
        container_botoes = st.container()
        container_grid = st.container()

        with container_grid:
            gb = GridOptionsBuilder.from_dataframe(df_grid)
            gb.configure_default_column(resizable=True, sortable=True, filter=True, minWidth=150, flex=1)
            
            gb.configure_selection(selection_mode='multiple', use_checkbox=True, header_checkbox=True)
            
            st_js = JsCode("function(p){let v=p.value||''; if(v.includes('Entregue')){return {'backgroundColor':'rgba(16,185,129,0.15)','color':'#10B981','fontWeight':'800'};} if(v.includes('ATRASADO') || v.includes('Frustrada')){return {'backgroundColor':'rgba(239,68,68,0.15)','color':'#EF4444','fontWeight':'800'};} if(v.includes('Em Rota')){return {'backgroundColor':'rgba(245,158,11,0.15)','color':'#F59E0B','fontWeight':'800'};} if(v.includes('Coletado') || v.includes('Conferido')){return {'backgroundColor':'rgba(59,130,246,0.15)','color':'#3B82F6','fontWeight':'800'};} return {'fontWeight':'bold'};}")
            gb.configure_column("STATUS_DISPLAY", headerName="STATUS", cellStyle=st_js, minWidth=170)
            
            img_js = JsCode("""
            class FotoRenderer {
                init(params) {
                    this.eGui = document.createElement('div');
                    this.eGui.style.textAlign = 'center';
                    let val = params.value;
                    if (val && val !== '' && val !== 'nan' && val !== 'None' && val.includes('http')) {
                        this.eGui.innerHTML = '<span style="cursor: pointer; font-size: 18px;" title="Ver Comprovante">📸</span>';
                        this.eGui.onclick = () => {
                            let modal = document.createElement('div');
                            modal.style.position = 'fixed'; modal.style.zIndex = '999999';
                            modal.style.left = '0'; modal.style.top = '0'; modal.style.width = '100vw'; modal.style.height = '100vh';
                            modal.style.backgroundColor = 'rgba(0,0,0,0.85)';
                            modal.style.display = 'flex'; modal.style.flexDirection = 'column'; modal.style.justifyContent = 'center'; modal.style.alignItems = 'center'; modal.style.cursor = 'zoom-out';
                            let img = document.createElement('img');
                            img.src = val; 
                            img.style.maxWidth = '90%'; img.style.maxHeight = '85%'; img.style.borderRadius = '10px'; img.style.boxShadow = '0 4px 20px rgba(0,0,0,0.5)';
                            let txt = document.createElement('div');
                            txt.innerText = '✖ Clique em qualquer lugar para fechar'; 
                            txt.style.color = '#ffffff'; txt.style.marginTop = '15px'; txt.style.fontFamily = 'sans-serif'; txt.style.fontWeight = 'bold';
                            modal.appendChild(img); modal.appendChild(txt);
                            modal.onclick = () => { document.body.removeChild(modal); };
                            document.body.appendChild(modal);
                        };
                    }
                }
                getGui() { return this.eGui; }
            }
            """)
            gb.configure_column("FOTO_URL", headerName="FOTO", cellRenderer=img_js, width=90, minWidth=90)
            
            grid_response = AgGrid(df_grid, gridOptions=gb.build(), allow_unsafe_jscode=True, theme='alpine', custom_css=obter_css_grid(), height=500, fit_columns_on_grid_load=False, update_mode=GridUpdateMode.MODEL_CHANGED | GridUpdateMode.SELECTION_CHANGED)
            
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
                    white-space: nowrap !important; overflow: hidden !important; font-weight: bold !important; font-size: 14px !important;
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
                                    for pid in p_ids:
                                        mask = df_nuvem['PEDIDO'] == pid
                                        df_nuvem.loc[mask, 'STATUS'] = status_limpo
                                        if status_limpo == "ENTREGUE": df_nuvem.loc[mask, 'DATA_ENTREGA'] = data_baixa.strftime("%d/%m/%Y")
                                        elif status_limpo == "PENDENTE": df_nuvem.loc[mask, 'DATA_ENTREGA'] = ""
                                    
                                    aba.update("A1", [df_nuvem.columns.tolist()] + df_nuvem.fillna("").astype(str).values.tolist())
                                    
                                    try:
                                        aba_app = planilha_db.worksheet("App_Tarefas")
                                        dados_app = aba_app.get_all_values()
                                        if len(dados_app) > 1:
                                            df_app = pd.DataFrame(dados_app[1:], columns=dados_app[0])
                                            if 'PEDIDO' in df_app.columns and 'STATUS' in df_app.columns:
                                                mascara_app = df_app['PEDIDO'].isin(p_ids)
                                                df_app.loc[mascara_app, 'STATUS'] = status_limpo
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
                                        
                                        if clone_mot != "Manter Original":
                                            l_orig['AGENTE_RAW'] = clone_mot
                                            
                                        prazo = calcular_sla_dias(l_orig.get('UF', 'SP'), l_orig.get('CIDADE', ''))
                                        l_orig['PRAZO_DIAS'] = prazo
                                        l_orig['DATA_LIMITE'] = calcular_data_limite(l_orig['DATA'], prazo)
                                            
                                        df_nuvem = pd.concat([df_nuvem, pd.DataFrame([l_orig])], ignore_index=True)
                                        
                                        if str(l_orig.get('AGENTE_RAW','')).strip():
                                            clones_para_app.append({
                                                'PEDIDO': novo_id, 'MOTORISTA': l_orig['AGENTE_RAW'],
                                                'ENDERECO': l_orig.get('ENDERECO',''), 'NUMERO': l_orig.get('NUMERO',''),
                                                'BAIRRO': l_orig.get('BAIRRO',''), 'CIDADE': l_orig.get('CIDADE',''),
                                                'CEP': l_orig.get('CEP',''), 'LABORATORIO': l_orig.get('LABORATORIO',''),
                                                'TOMADOR': l_orig.get('TOMADOR','')
                                            })

                                aba.update("A1", [df_nuvem.columns.tolist()] + df_nuvem.fillna("").astype(str).values.tolist())
                                if clones_para_app: despachar_para_appsheet(clones_para_app)
                                st.success("Clonado com SUCESSO!")
                                carregar_dados_completos.clear()
                                st.rerun()
                            except Exception as e: st.error(f"Erro ao clonar: {e}")

            with col_b4.popover("🔄 Trocar Motorista", use_container_width=True):
                if not tem_sel: st.warning("Selecione na Grid primeiro!")
                else:
                    tem_entregue = df_grid[df_grid['PEDIDO'].isin(p_ids)]['STATUS_DISPLAY'].str.contains('Entregue').any()
                    if tem_entregue:
                        st.error("⚠️ Não é possível trocar motorista de pedidos já ENTREGUES.")
                    else:
                        logins_disp = sorted(DF_AGENTES['LOGIN DO AGENTE'].unique().tolist()) if not DF_AGENTES.empty else []
                        novo_mot = st.selectbox("Novo Agente (Digite para buscar):", logins_disp)
                        nova_data_troca = st.date_input("Nova Data do Pedido (SLA NÃO muda):", format="DD/MM/YYYY", value=hoje_br)
                        
                        if st.button("Confirmar Troca", type="primary", use_container_width=True):
                            with st.spinner("Trocando motorista..."):
                                try:
                                    aba = planilha_db.worksheet("Memoria_Sistema")
                                    dados_aba = aba.get_all_values()
                                    df_nuvem = pd.DataFrame(dados_aba[1:], columns=dados_aba[0])
                                    lista_app_troca = []
                                    
                                    for pid in p_ids:
                                        mask = df_nuvem['PEDIDO'] == pid
                                        if mask.any():
                                            df_nuvem.loc[mask, 'AGENTE_RAW'] = novo_mot
                                            df_nuvem.loc[mask, 'STATUS'] = "PENDENTE"
                                            df_nuvem.loc[mask, 'DATA'] = nova_data_troca.strftime("%d/%m/%Y")
                                            
                                            l_app = df_nuvem[mask].iloc[0]
                                            lista_app_troca.append({'PEDIDO': pid, 'MOTORISTA': novo_mot, 'ENDERECO': l_app.get('ENDERECO',''), 'NUMERO': l_app.get('NUMERO',''), 'BAIRRO': l_app.get('BAIRRO',''), 'CIDADE': l_app.get('CIDADE',''), 'CEP': l_app.get('CEP',''), 'LABORATORIO': l_app.get('LABORATORIO',''), 'TOMADOR': l_app.get('TOMADOR','')})
                                    
                                    aba.update("A1", [df_nuvem.columns.tolist()] + df_nuvem.fillna("").astype(str).values.tolist())
                                    despachar_para_appsheet(lista_app_troca)
                                    st.success("Trocado!")
                                    carregar_dados_completos.clear()
                                    st.rerun()
                                except Exception as e: st.error(f"Erro: {e}")

            if col_b5.button("🔄 Atualizar Painel", use_container_width=True):
                carregar_dados_completos.clear()
                st.rerun()

    else:
        st.warning("📭 O banco de dados está vazio no momento. Acesse a aba '📝 Novo Pedido Manual' no menu lateral para começar.")

# =============================================================================
# 📝 MÓDULO EXTRA: NOVO PEDIDO MANUAL (ABA ISOLADA E PADRONIZADA)
# =============================================================================
elif menu == "📝 Novo Pedido Manual":
    st.markdown("<h4 class='dinamic-text'>📝 Inserir Pedido Manual</h4>", unsafe_allow_html=True)
    st.markdown("Use esta tela para gerar pedidos de emergência. **Os textos inseridos perderão os acentos e ficarão maiúsculos automaticamente.**")
    
    with st.container(border=True):
        with st.form("form_manual_page", clear_on_submit=True):
            col1, col2 = st.columns(2)
            m_tomador = col1.selectbox("Tomador *", ["Selecione..."] + CLIENTES_AUTORIZADOS)
            m_data = col2.date_input("Data do Pedido *", format="DD/MM/YYYY", value=hoje_br)
            
            m_lab = st.text_input("Lab/Clínica *")
            m_rua = st.text_input("Endereço *")
            
            col3, col4 = st.columns(2)
            m_bai = col3.text_input("Bairro *")
            m_cid = col4.text_input("Cidade *")
            
            logins_disp = sorted(DF_AGENTES['LOGIN DO AGENTE'].unique().tolist()) if not DF_AGENTES.empty else []
            m_agente_escolha = st.selectbox("Agente Designado (Busque ou deixe Automático):", ["Automático (Por Rota)"] + logins_disp)
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.form_submit_button("🚀 Gerar e Salvar Pedido", type="primary", use_container_width=True):
                if m_tomador == "Selecione..." or not m_cid or not m_lab or not m_rua or not m_bai: 
                    st.error("⚠️ Preencha todos os campos obrigatórios (marcados com *)!")
                else:
                    with st.spinner("Padronizando textos e salvando na nuvem..."):
                        lab_limpo = padronizar_texto(m_lab)
                        rua_limpa = padronizar_texto(m_rua)
                        bai_limpo = padronizar_texto(m_bai)
                        cid_limpa = padronizar_texto(m_cid)
                        
                        m_agente = obter_login_agente(cid_limpa, bai_limpo, lab_limpo, rua_limpa, DF_AGENTES) if m_agente_escolha == "Automático (Por Rota)" else m_agente_escolha
                        m_prazo = calcular_sla_dias("SP", cid_limpa)
                        m_limite = calcular_data_limite(m_data.strftime("%d/%m/%Y"), m_prazo)
                        
                        try:
                            aba_memoria = planilha_db.worksheet("Memoria_Sistema")
                            dados_atuais = aba_memoria.get_all_values()
                            df_nuvem = pd.DataFrame(dados_atuais[1:], columns=dados_atuais[0]) if len(dados_atuais) > 1 else pd.DataFrame()
                            
                            m_pedido = str(obter_proximo_id(df_nuvem))
                            
                            novo_ped = pd.DataFrame([{
                                'DATA': m_data.strftime("%d/%m/%Y"), 'PEDIDO': m_pedido, 'TOMADOR': m_tomador, 
                                'LABORATORIO': lab_limpo, 'ENDERECO': rua_limpa, 'NUMERO': "", 'BAIRRO': bai_limpo, 
                                'CIDADE': cid_limpa, 'UF': "SP", 'CEP': "", 'STATUS': 'PENDENTE', 
                                'AGENTE_RAW': m_agente, 'PRAZO_DIAS': m_prazo, 'DATA_LIMITE': m_limite, 
                                'DATA_ENTREGA': "", 'FOTO': "", 'ROMANEIO': ""
                            }])
                            
                            df_atual = pd.concat([df_nuvem, novo_ped], ignore_index=True) if not df_nuvem.empty else novo_ped
                            aba_memoria.update("A1", [df_atual.columns.tolist()] + df_atual.fillna("").astype(str).values.tolist())
                            
                            if m_agente: despachar_para_appsheet([novo_ped.iloc[0].to_dict()])
                            
                            st.success(f"🎉 Pedido {m_pedido} criado e padronizado com sucesso! Acesse o Dashboard para visualizar.")
                            carregar_dados_completos.clear()
                        except Exception as e: st.error(f"Erro ao salvar: {e}")

# =============================================================================
# ➕ MÓDULO 2: IMPORTAÇÃO DE LOTES
# =============================================================================
elif menu == "➕ Importação de Lotes":
    st.markdown("<h4 class='dinamic-text'>➕ Central de Importação</h4>", unsafe_allow_html=True)
    st.success("🛡️ **SEGURANÇA DO HISTÓRICO:** O sistema de importação sempre **ADICIONA** os novos pedidos na base. O seu histórico do dia estão seguros.")
    
    if "df_preview" not in st.session_state: st.session_state.df_preview = pd.DataFrame()
    if "import_success" in st.session_state and st.session_state.import_success:
        st.success(st.session_state.import_success)

    with st.container(border=True):
        st.markdown("#### 1. Dados do Lote e Colagem")
        c1, c2, c3 = st.columns([1, 1, 2])
        with c1: tom = st.selectbox("🏢 Tomador:", ["Selecione..."] + CLIENTES_AUTORIZADOS)
        with c2: dt_c = st.date_input("📅 Data da Coleta:", format="DD/MM/YYYY", value=hoje_br)

        txt = st.text_area("📋 Cole os dados do Excel aqui (Ctrl+V):", height=150, help="Apenas copie as células do Excel e cole direto aqui.")

        col_btn1, _ = st.columns([1, 2])
        if col_btn1.button("🔍 1. Tratar e Roteirizar", type="primary", use_container_width=True):
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
        col_tit.markdown("### 👀 2. Preview dos Dados (Barreira de Segurança)")
        if col_canc.button("❌ Cancelar / Limpar", type="secondary", use_container_width=True):
            st.session_state.df_preview = pd.DataFrame()
            if 'import_success' in st.session_state: st.session_state.import_success = ""
            st.rerun()

        df_preview = st.session_state.df_preview
        mask_err = (df_preview['AGENTE_RAW'].astype(str).str.strip() == "") | (df_preview['AGENTE_RAW'].astype(str).str.upper() == "NAN")
        df_err = df_preview[mask_err]
        df_ok = df_preview[~mask_err]

        if not df_err.empty:
            st.error(f"🚨 **Atenção:** Encontramos {len(df_err)} pedido(s) sem motorista designado. Corrija-os na gaveta abaixo para liberar o botão de salvar.")
            
            if not df_ok.empty:
                with st.expander(f"✅ Gaveta Verde: {len(df_ok)} Pedido(s) Prontos para Salvar", expanded=False):
                    st.dataframe(df_ok, hide_index=True, use_container_width=True)
            
            st.markdown("### 🛠️ Gaveta Vermelha: Correção Pendente")
            st.info("💡 Clique na caixa de seleção abaixo para **digitar e buscar** o nome do motorista.")
            with st.form("form_correcao_agentes"):
                correcoes = {}
                logins_disp = sorted(DF_AGENTES['LOGIN DO AGENTE'].unique().tolist()) if not DF_AGENTES.empty else []
                
                for idx, row in df_err.iterrows():
                    st.markdown(f"**Pedido:** {row['PEDIDO']} | **Lab:** {row['LABORATORIO']} | **Endereço:** {row['ENDERECO']} - {row['BAIRRO']}, {row['CIDADE']}")
                    correcoes[idx] = st.selectbox(f"Motorista para o pedido {row['PEDIDO']}:", ["Selecione..."] + logins_disp, key=f"fix_mot_{idx}")
                    st.divider()
                
                if st.form_submit_button("💾 Aplicar Correções", type="primary"):
                    todas_corrigidas = True
                    for idx, novo_mot in correcoes.items():
                        if novo_mot != "Selecione...":
                            st.session_state.df_preview.at[idx, 'AGENTE_RAW'] = novo_mot
                        else:
                            todas_corrigidas = False
                    
                    if not todas_corrigidas:
                        st.warning("⚠️ Ainda há pedidos sem motorista na lista. Preencha todos para liberar o lote.")
                    st.rerun()

        else:
            st.success(f"✅ Maravilha! Todos os {len(df_ok)} pedidos estão roteirizados e prontos para importação.")
            
            gb_prev = GridOptionsBuilder.from_dataframe(df_ok)
            gb_prev.configure_default_column(resizable=True, sortable=True, filter=True, minWidth=150, flex=1)
            AgGrid(df_ok, gridOptions=gb_prev.build(), allow_unsafe_jscode=True, theme='alpine', custom_css=obter_css_grid(), height=400, fit_columns_on_grid_load=False)
            
            st.markdown("<br>", unsafe_allow_html=True)
            col_btn2, _ = st.columns([1, 2])
            
            if col_btn2.button("🚀 3. SALVAR TUDO NO GOOGLE SHEETS", type="primary", use_container_width=True):
                with st.spinner("Adicionando à base geral..."):
                    df_final = df_ok.copy()
                    
                    try:
                        aba = planilha_db.worksheet("Memoria_Sistema")
                        atuais = aba.get_all_values()
                        df_up = pd.DataFrame(atuais[1:], columns=atuais[0]) if len(atuais) > 1 else pd.DataFrame()
                        
                        prox_id = obter_proximo_id(df_up)
                        
                        for idx, row in df_final.iterrows():
                            if not str(row['PEDIDO']).strip() or str(row['PEDIDO']).upper() == 'NAN': 
                                df_final.at[idx, 'PEDIDO'] = str(prox_id)
                                prox_id += 1
                        
                        df_final['PRAZO_DIAS'] = df_final.apply(lambda r: calcular_sla_dias(r['UF'], r['CIDADE']), axis=1)
                        df_final['DATA_LIMITE'] = df_final.apply(lambda r: calcular_data_limite(r['DATA'], int(r['PRAZO_DIAS'])), axis=1)
                        df_final['STATUS'], df_final['DATA_ENTREGA'], df_final['FOTO'], df_final['ROMANEIO'] = 'PENDENTE', '', '', ''
                        
                        df_up = pd.concat([df_up, df_final], ignore_index=True) if not df_up.empty else df_final
                        
                        aba.update("A1", [df_up.columns.tolist()] + df_up.fillna("").astype(str).values.tolist())
                        
                        lista_app = []
                        for _, r in df_final.iterrows():
                            if str(r.get('AGENTE_RAW','')).strip():
                                lista_app.append({
                                    'PEDIDO': r['PEDIDO'], 'MOTORISTA': r['AGENTE_RAW'], 'ENDERECO': r['ENDERECO'],
                                    'NUMERO': r['NUMERO'], 'BAIRRO': r['BAIRRO'], 'CIDADE': r['CIDADE'],
                                    'CEP': r['CEP'], 'LABORATORIO': r['LABORATORIO'], 'TOMADOR': r['TOMADOR']
                                })
                        if lista_app: despachar_para_appsheet(lista_app)
                        
                        st.session_state.import_success = f"🎉 SUCESSO ABSOLUTO! Lote de {len(df_final)} pedidos foi importado e despachado para os motoristas."
                        st.session_state.df_preview = pd.DataFrame()
                        carregar_dados_completos.clear()
                        st.rerun()
                    except Exception as e: st.error(f"Erro ao salvar: {e}")

# =============================================================================
# 📋 MÓDULO 3: TRIAGEM E ROMANEIO (OTIMIZADO)
# =============================================================================
elif menu == "📋 Triagem e Romaneio":
    st.markdown("<h4 class='dinamic-text'>📋 Triagem e Despacho</h4>", unsafe_allow_html=True)
    df_raw = carregar_dados_completos(planilha_db)
    
    if not df_raw.empty:
        t1, t2, t3 = st.tabs(["📦 1. Bipar / Selecionar", "🚚 2. Gerar Romaneio", "🕒 3. Histórico Recente"])
        
        with t1:
            st.info("💡 Apenas pedidos **COLETADOS** aparecerão aqui.")
            with st.form("form_bip", clear_on_submit=True):
                col_bip, col_btn = st.columns([4, 1])
                bip_input = col_bip.text_input("🔍 Bipar QR Code / Pedido:")
                bip_submit = col_btn.form_submit_button("Bipar", use_container_width=True)
                
                if bip_submit and bip_input:
                    termo = re.sub(r'[^A-Z0-9]', '', bip_input.upper())
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
                                aba.update_cell(idx + 2, df_raw.columns.get_loc('STATUS') + 1, 'CONFERIDO')
                                st.success(f"✅ Pedido {df_raw.at[idx, 'PEDIDO']} CONFERIDO com sucesso!")
                                carregar_dados_completos.clear()
                            except Exception as e: st.error(f"Erro ao salvar: {e}")
                        elif status_atual == 'PENDENTE': st.error(f"❌ O pedido {df_raw.at[idx, 'PEDIDO']} ainda está PENDENTE. O agente precisa dar baixa primeiro!")
                        elif status_atual == 'CONFERIDO': st.warning(f"⚠️ O pedido {df_raw.at[idx, 'PEDIDO']} já estava conferido!")
                        else: st.error(f"❌ O pedido {df_raw.at[idx, 'PEDIDO']} está com status: {status_atual}.")
                    else: st.error(f"❌ Pedido não encontrado: {bip_input}")
            
            st.markdown("---")
            st.markdown("#### Seleção Manual de Pedidos (Filtrado: Só Coletados)")
            df_fila = df_raw[df_raw['STATUS'].astype(str).str.upper() == 'COLETADO'].copy()
            if not df_fila.empty:
                df_fila = df_fila[['DATA', 'PEDIDO', 'TOMADOR', 'LABORATORIO', 'CIDADE', 'STATUS']]
                gb_fila = GridOptionsBuilder.from_dataframe(df_fila)
                gb_fila.configure_default_column(resizable=True, sortable=True, filter=True, minWidth=150, flex=1)
                
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
                                mascara_pedidos = df_nuvem['PEDIDO'].isin(p_ids)
                                df_nuvem.loc[mascara_pedidos, 'STATUS'] = 'CONFERIDO'
                                aba.update("A1", [df_nuvem.columns.tolist()] + df_nuvem.fillna("").astype(str).values.tolist())
                                st.success(f"🎉 {len(p_ids)} pedidos enviados para o Despacho!")
                                carregar_dados_completos.clear()
                                st.rerun()
                            except Exception as e: st.error(f"Erro: {e}")
            else: st.info("Nenhum pedido aguardando triagem (Apenas pacotes 'Coletados' chegam aqui).")

        with t2:
            st.markdown("#### Selecione os pedidos Conferidos para gerar o Romaneio")
            df_conf = df_raw[df_raw['STATUS'].astype(str).str.upper() == 'CONFERIDO'].copy()
            if not df_conf.empty:
                
                lista_tomadores_conf = sorted(df_conf['TOMADOR'].astype(str).unique().tolist())
                c_filtro, _ = st.columns([1, 2])
                tomador_filtro = c_filtro.selectbox("🏢 Filtrar Lote por Tomador:", ["Todos"] + [t for t in lista_tomadores_conf if t.strip()])
                
                if tomador_filtro != "Todos":
                    df_conf = df_conf[df_conf['TOMADOR'] == tomador_filtro]
                
                gb = GridOptionsBuilder.from_dataframe(df_conf[['DATA', 'PEDIDO', 'TOMADOR', 'LABORATORIO', 'CIDADE', 'UF']])
                gb.configure_default_column(resizable=True, sortable=True, filter=True, minWidth=150, flex=1)
                
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
                motorista_escolhido = c_mot.selectbox("👤 Motorista (Buscar):", ["Selecione..."] + logins_disp)
                data_despacho = c_data.date_input("📅 Data do Romaneio:", format="DD/MM/YYYY", value=hoje_br)
                
                if c_btn.button("🚚 Gerar Romaneio PDF e Despachar", type="primary", use_container_width=True):
                    if not tem_sel_pdf or motorista_escolhido == "Selecione...": st.warning("⚠️ Selecione os pedidos e um motorista!")
                    else:
                        with st.spinner("Gerando PDF e enviando o Lote ao AppSheet (Anti-Bloqueio)..."):
                            if isinstance(selecionados, pd.DataFrame): sel_lista = selecionados.to_dict('records')
                            else: sel_lista = selecionados
                            id_romaneio = f"ROM-{datetime.now().strftime('%d%m')}-{random.randint(100,999)}"
                            pedidos_ids = [str(r['PEDIDO']) for r in sel_lista]
                            
                            try:
                                aba = planilha_db.worksheet("Memoria_Sistema")
                                dados_aba = aba.get_all_values()
                                df_nuvem = pd.DataFrame(dados_aba[1:], columns=dados_aba[0])
                                mascara_pedidos = df_nuvem['PEDIDO'].isin(pedidos_ids)
                                
                                df_nuvem.loc[mascara_pedidos, 'STATUS'] = 'EM ROTA DE ENTREGA'
                                df_nuvem.loc[mascara_pedidos, 'ROMANEIO'] = id_romaneio
                                df_nuvem.loc[mascara_pedidos, 'DATA'] = data_despacho.strftime("%d/%m/%Y")
                                
                                if 'AGENTE_RAW' in df_nuvem.columns:
                                    df_nuvem.loc[mascara_pedidos, 'AGENTE_RAW'] = motorista_escolhido
                                
                                aba.update("A1", [df_nuvem.columns.tolist()] + df_nuvem.fillna("").astype(str).values.tolist())
                                
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
                                pdf.set_draw_color(44, 62, 80); pdf.set_line_width(1); pdf.rect(5, 5, 200, 287)
                                pdf.set_y(15); pdf.set_font("Arial", "B", 18); pdf.set_text_color(44, 62, 80); pdf.cell(0, 8, f"PROTOCOLO DE ROMANEIO", ln=True, align="C")
                                pdf.set_font("Arial", "B", 13); pdf.set_text_color(52, 152, 219); pdf.cell(0, 8, f"LOTE: {id_romaneio} | DESPACHO IGO", ln=True, align="C")
                                pdf.set_font("Arial", "I", 10); pdf.set_text_color(127, 140, 141); pdf.cell(0, 6, f"Motorista: {motorista_escolhido} | Data do Romaneio: {data_despacho.strftime('%d/%m/%Y')}", ln=True, align="C")
                                pdf.ln(10); pdf.line(15, pdf.get_y(), 195, pdf.get_y()); pdf.ln(8)
                                pdf.set_fill_color(52, 152, 219); pdf.set_text_color(255, 255, 255); pdf.set_font("Arial", "B", 10)
                                pdf.cell(15, 8, "ITEM", 1, 0, "C", True); pdf.cell(35, 8, "PEDIDO", 1, 0, "C", True)
                                pdf.cell(90, 8, "LABORATORIO", 1, 0, "C", True); pdf.cell(40, 8, "CIDADE", 1, 0, "C", True)
                                pdf.cell(10, 8, "UF", 1, 1, "C", True)
                                pdf.set_text_color(44, 62, 80); pdf.set_font("Arial", "", 9)
                                for idx, item in enumerate(sel_lista, 1):
                                    fill = (idx % 2 == 0)
                                    if fill: pdf.set_fill_color(248, 249, 249)
                                    pdf.cell(15, 6, str(idx), 1, 0, "C", fill); pdf.cell(35, 6, str(item.get('PEDIDO','')), 1, 0, "C", fill)
                                    pdf.cell(90, 6, str(item.get('LABORATORIO',''))[:45], 1, 0, "L", fill); pdf.cell(40, 6, str(item.get('CIDADE',''))[:20], 1, 0, "L", fill)
                                    pdf.cell(10, 6, str(item.get('UF','')), 1, 1, "C", fill)
                                pdf.ln(10); pdf.set_font("Arial", "B", 11); pdf.cell(0, 10, f"TOTAL DE VOLUMES: {len(sel_lista)}", ln=True, align="R")
                                pdf.set_y(-50); pdf.line(20, pdf.get_y(), 90, pdf.get_y()); pdf.line(120, pdf.get_y(), 190, pdf.get_y())
                                pdf.set_font("Arial", "B", 9); pdf.cell(95, 5, "MOTORISTA (IGO)", 0, 0, "C"); pdf.cell(95, 5, "ASSINATURA DA BASE", 0, 1, "C")
                                
                                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
                                    pdf.output(tmp_pdf.name)
                                    with open(tmp_pdf.name, "rb") as f: pdf_bytes = f.read()
                                
                                st.success(f"🎉 Lote {id_romaneio} com {len(sel_lista)} pedidos despachado com sucesso!")
                                st.download_button(label="📥 BAIXAR ROMANEIO EM PDF", data=pdf_bytes, file_name=f"Romaneio_{id_romaneio}.pdf", mime="application/pdf", type="primary")
                            except Exception as e: st.error(f"Erro ao processar despacho: {e}")
            else: st.info("Nenhum pedido com status 'CONFERIDO' no momento.")

        with t3:
            st.markdown("#### Histórico de Triagem e Despacho")
            st.info("Visualização rápida de todos os pedidos já conferidos ou despachados.")
            
            status_mostrar = ['CONFERIDO', 'EM ROTA DE ENTREGA', 'ENTREGUE', 'FRUSTRADA', 'PROBLEMA', 'CANCELADO']
            df_hist = df_raw[df_raw['STATUS'].astype(str).str.upper().isin(status_mostrar)].copy()
            
            if not df_hist.empty:
                df_hist = df_hist.sort_values(by=['DATA_OBJ', 'PEDIDO'], ascending=[False, False])
                
                colunas_hist = ['DATA', 'PEDIDO', 'TOMADOR', 'LABORATORIO', 'CIDADE', 'STATUS', 'AGENTE_RAW', 'ROMANEIO']
                df_hist_show = df_hist[[c for c in colunas_hist if c in df_hist.columns]]
                
                gb_hist = GridOptionsBuilder.from_dataframe(df_hist_show)
                gb_hist.configure_default_column(resizable=True, sortable=True, filter=True, minWidth=150, flex=1)
                
                st_js = JsCode("function(p){let v=p.value||''; if(v.includes('ENTREGUE')){return {'backgroundColor':'rgba(16,185,129,0.15)','color':'#10B981','fontWeight':'800'};} if(v.includes('FRUSTRADA') || v.includes('PROBLEMA')){return {'backgroundColor':'rgba(239,68,68,0.15)','color':'#EF4444','fontWeight':'800'};} if(v.includes('EM ROTA')){return {'backgroundColor':'rgba(245,158,11,0.15)','color':'#F59E0B','fontWeight':'800'};} if(v.includes('CONFERIDO')){return {'backgroundColor':'rgba(59,130,246,0.15)','color':'#3B82F6','fontWeight':'800'};} return {'fontWeight':'bold'};}")
                gb_hist.configure_column("STATUS", headerName="STATUS", cellStyle=st_js, minWidth=170)
                
                AgGrid(df_hist_show, gridOptions=gb_hist.build(), allow_unsafe_jscode=True, theme='alpine', custom_css=obter_css_grid(), height=400, fit_columns_on_grid_load=False)
            else:
                st.warning("Nenhum histórico de triagem ou despacho encontrado.")
                
    else: st.info("O banco de dados está vazio no momento.")

# =============================================================================
# 📱 MÓDULO EXTRA: DISPARO WHATSAPP (BOTÃO ZAP)
# =============================================================================
elif menu == "📱 Disparo WhatsApp":
    st.markdown("<h4 class='dinamic-text'>📱 Central de Disparo via WhatsApp</h4>", unsafe_allow_html=True)
    st.markdown("Selecione a data para visualizar e enviar as rotas pendentes para os motoristas.")
    
    df_raw = carregar_dados_completos(planilha_db)
    
    if not df_raw.empty:
        data_filtro = st.date_input("📅 Filtrar pedidos da data:", value=hoje_br)
        
        df_pendentes = df_raw[(df_raw['DATA_OBJ'] == data_filtro) & (df_raw['STATUS'].astype(str).str.upper() == 'PENDENTE')].copy()
        
        if df_pendentes.empty:
            st.success(f"Nenhuma coleta/entrega PENDENTE para o dia {data_filtro.strftime('%d/%m/%Y')}.")
        else:
            agentes_com_rota = df_pendentes['AGENTE_RAW'].dropna().unique()
            agentes_com_rota = [ag for ag in agentes_com_rota if str(ag).strip()]
            
            if not agentes_com_rota:
                st.warning("Existem pedidos pendentes, mas nenhum deles tem um motorista atribuído.")
            else:
                st.info(f"Encontrados **{len(df_pendentes)}** pedidos distribuídos entre **{len(agentes_com_rota)}** motoristas.")
                
                dict_telefones = {}
                if not DF_AGENTES.empty:
                    for _, row in DF_AGENTES.iterrows():
                        login = str(row.get('LOGIN DO AGENTE', '')).strip().lower()
                        tel = str(row.get('TELEFONE', '')).strip()
                        tel_limpo = re.sub(r'\D', '', tel)
                        if login and tel_limpo:
                            dict_telefones[login] = tel_limpo

                for agente in sorted(agentes_com_rota):
                    df_agente = df_pendentes[df_pendentes['AGENTE_RAW'] == agente]
                    qtd_pedidos = len(df_agente)
                    telefone = dict_telefones.get(str(agente).strip().lower(), "")
                    
                    with st.expander(f"👤 Motorista: {str(agente).upper()} ({qtd_pedidos} pacotes)", expanded=False):
                        st.dataframe(df_agente[['PEDIDO', 'TOMADOR', 'LABORATORIO', 'CIDADE']], hide_index=True, use_container_width=True)
                        
                        if telefone:
                            msg = f"🚚 *ROTA IGO LOGÍSTICA*\n"
                            msg += f"Data: {data_filtro.strftime('%d/%m/%Y')}\n"
                            msg += f"Motorista: {str(agente).upper()}\n\n"
                            msg += f"📦 *COLETAS / ENTREGAS ({qtd_pedidos}):*\n\n"
                            
                            for i, (_, row) in enumerate(df_agente.iterrows(), 1):
                                msg += f"*{i}️⃣ Pedido:* {row['PEDIDO']}\n"
                                msg += f"🏥 *Tomador:* {row.get('TOMADOR', '')}\n"
                                msg += f"🏢 *Local:* {row.get('LABORATORIO', '')}\n"
                                msg += f"📍 *Endereço:* {row.get('ENDERECO', '')}, {row.get('NUMERO', '')} - {row.get('BAIRRO', '')}, {row.get('CIDADE', '')}\n"
                                if str(row.get('OBSERVACOES', '')).strip() and str(row.get('OBSERVACOES', '')).upper() != 'NAN':
                                    msg += f"📝 *Obs:* {row['OBSERVACOES']}\n"
                                msg += "------------------------\n"
                            
                            msg += "\nBom trabalho e dirija com segurança!"
                            
                            msg_codificada = urllib.parse.quote(msg)
                            link_whatsapp = f"https://api.whatsapp.com/send?phone={telefone}&text={msg_codificada}"
                            
                            st.link_button("📲 Enviar Rota pelo WhatsApp", link_whatsapp, type="primary")
                        else:
                            st.error(f"⚠️ Telefone não encontrado para o login '{agente}'. Cadastre o telefone na aba 'Configurar Rotas'.")
    else:
        st.warning("📭 O banco de dados está vazio no momento.")

# =============================================================================
# 📥 MÓDULO 4: EXPORTAR RELATÓRIOS
# =============================================================================
elif menu == "📥 Exportar Relatórios":
    st.markdown("<h4 class='dinamic-text'>📥 Central de Exportações</h4>", unsafe_allow_html=True)
    df_raw = carregar_dados_completos(planilha_db)
    
    if not df_raw.empty:
        colunas_export = ['DATA', 'PEDIDO', 'TOMADOR', 'LABORATORIO', 'ENDERECO', 'NUMERO', 'BAIRRO', 'CIDADE', 'UF', 'CEP', 'STATUS', 'AGENTE_RAW', 'DATA_LIMITE']
        df_export_base = df_raw[[c for c in colunas_export if c in df_raw.columns]].copy()
        if 'AGENTE_RAW' in df_export_base.columns: df_export_base.rename(columns={'AGENTE_RAW': 'MOTORISTA'}, inplace=True)
        
        st.markdown("### ⚡ Relatórios de Fechamento Padrão")
        col_rel1, col_rel2, col_rel3 = st.columns(3)
        
        df_rj = df_export_base[df_export_base['UF'].str.upper() == 'RJ'] if 'UF' in df_export_base.columns else pd.DataFrame()
        if 'CIDADE' in df_export_base.columns:
            df_jf = df_export_base[df_export_base['CIDADE'].str.upper().str.contains('JUIZ DE FORA', na=False)]
            df_rjjf = pd.concat([df_rj, df_jf]).drop_duplicates(subset=['PEDIDO'])
        else: df_rjjf = df_rj
            
        if not df_rjjf.empty:
            col_rel1.download_button("📥 Extrair RJ / JF", data=gerar_excel_memoria(df_rjjf), file_name=f"Relatorio_RJ_JF_{datetime.now(FUSO_BR).strftime('%d%m%Y')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
        else: col_rel1.button("📥 Extrair RJ / JF (Sem Dados)", disabled=True, use_container_width=True)

        if 'MOTORISTA' in df_export_base.columns:
            df_lud = df_export_base[df_export_base['MOTORISTA'].str.lower().str.contains('ludmila|veloz', na=False)]
            if not df_lud.empty:
                col_rel2.download_button("📥 Extrair Ludmila / Veloz", data=gerar_excel_memoria(df_lud), file_name=f"Relatorio_Ludmila_{datetime.now(FUSO_BR).strftime('%d%m%Y')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
            else: col_rel2.button("📥 Extrair Ludmila / Veloz (Sem Dados)", disabled=True, use_container_width=True)
        
        col_rel3.download_button("📥 Relatório Geral (Todos)", data=gerar_excel_memoria(df_export_base), file_name=f"Relatorio_Geral_{datetime.now(FUSO_BR).strftime('%d%m%Y')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary", use_container_width=True)
        
        st.markdown("---")
        st.markdown("### 🔍 Gerador de Relatório Personalizado")
        with st.form("form_rel_custom"):
            cf1, cf2 = st.columns(2)
            c_ag = cf1.text_input("👤 Agente (Nome/Login):")
            c_cid = cf2.text_input("🏙️ Cidade:")
            c_uf = cf1.text_input("🗺️ UF:")
            c_base = cf2.text_input("🏢 Base Oper. (Tomador/Lab):")
            
            if st.form_submit_button("Gerar Relatório Customizado"):
                df_custom = df_export_base.copy()
                if c_ag and 'MOTORISTA' in df_custom.columns: df_custom = df_custom[df_custom['MOTORISTA'].str.upper().str.contains(c_ag.upper(), na=False)]
                if c_cid and 'CIDADE' in df_custom.columns: df_custom = df_custom[df_custom['CIDADE'].str.upper().str.contains(c_cid.upper(), na=False)]
                if c_uf and 'UF' in df_custom.columns: df_custom = df_custom[df_custom['UF'].str.upper() == c_uf.upper()]
                if c_base:
                    mt = df_custom['TOMADOR'].str.upper().str.contains(c_base.upper(), na=False) if 'TOMADOR' in df_custom.columns else False
                    ml = df_custom['LABORATORIO'].str.upper().str.contains(c_base.upper(), na=False) if 'LABORATORIO' in df_custom.columns else False
                    df_custom = df_custom[mt | ml]
                
                if not df_custom.empty:
                    st.success(f"Relatório gerado com {len(df_custom)} linhas!")
                    st.download_button("📥 Baixar Customizado", data=gerar_excel_memoria(df_custom), file_name=f"Relatorio_Custom.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                else: st.warning("Nenhum dado encontrado.")
    else: st.warning("O banco de dados está vazio.")

# =============================================================================
# ⚙️ MÓDULO 5: CONFIGURAR ROTAS E AGENTES
# =============================================================================
elif menu == "⚙️ Configurar Rotas":
    st.markdown("<h4 class='dinamic-text'>⚙️ Gestão de Agentes e Rotas</h4>", unsafe_allow_html=True)
    
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
                        col_rota.markdown(f"<div style='padding:10px; background-color:{bg_app}; border-radius:5px; border: 1px solid {border_c};'><b>📍 {rota_disp}</b></div>", unsafe_allow_html=True)
                        if col_del.button("🗑️ Remover", key=f"del_{idx}", use_container_width=True):
                            df_novo = DF_AGENTES.drop(idx)
                            try:
                                aba = planilha_db.worksheet("Agentes")
                                aba.update("A1", [df_novo.columns.tolist()] + df_novo.fillna("").astype(str).values.tolist())
                                carregar_dados_agentes.clear()
                                st.rerun()
                            except Exception as e: st.error(f"Erro ao remover: {e}")
        else: st.warning("Nenhum dado encontrado.")
