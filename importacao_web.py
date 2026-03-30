import streamlit as st
import pandas as pd
import io
import csv
import re
import unicodedata
import holidays
import os
import tempfile
from datetime import datetime, timedelta, timezone
import random
import gspread
import uuid
from streamlit_autorefresh import st_autorefresh
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
from fpdf import FPDF

FUSO_BR = timezone(timedelta(hours=-3))

# =============================================================================
# 🔗 1. CONEXÃO COM A NUVEM E CÉREBRO DE DADOS
# =============================================================================
st.set_page_config(page_title="Admin - IGO Logística", layout="wide", page_icon="🚚", initial_sidebar_state="expanded")
st_autorefresh(interval=60000, limit=None, key="refresh_timer")

@st.cache_resource
def conectar_banco():
    """Conecta ao Google Sheets (Local ou Nuvem)"""
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    
    try:
        # 1. TENTA MODO LOCAL (Seu computador)
        caminho_windows = r"C:\Users\elcic\IGO_Logistica_Sistema"
        cred_win = os.path.join(caminho_windows, "credentials.json")
        token_win = os.path.join(caminho_windows, "token.json")
        
        if os.path.exists(cred_win):
            gc = gspread.oauth(credentials_filename=cred_win, authorized_user_filename=token_win)
            return gc.open("DB_IGO_Logistica")

        # 2. TENTA MODO NUVEM (Streamlit Secrets)
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
                    df_app_clean = df_app[['PEDIDO', 'STATUS', 'OBSERVACOES']].copy()
                    df_app_clean.rename(columns={'STATUS': 'APP_STATUS', 'OBSERVACOES': 'APP_OBS'}, inplace=True)
                    df_app_clean['PEDIDO'] = df_app_clean['PEDIDO'].astype(str).str.strip()
                    df_app_clean.drop_duplicates(subset=['PEDIDO'], keep='last', inplace=True)
                    df['PEDIDO'] = df['PEDIDO'].astype(str).str.strip()
                    df = pd.merge(df, df_app_clean, on='PEDIDO', how='left')
            except Exception: pass
            if 'DATA' in df.columns: df['DATA_OBJ'] = pd.to_datetime(df['DATA'], format='%d/%m/%Y', errors='coerce').dt.date
            return df
    except Exception: pass
    return pd.DataFrame()

planilha_db = conectar_banco()
DF_AGENTES = carregar_dados_agentes(planilha_db)
FERIADOS_BR = holidays.Brazil()
CLIENTES_AUTORIZADOS = ["CUNHA", "CAEP", "SAPIENS", "GRALAB", "SYNVIA", "INNOVATOX", "LABEST", "AIRLAB", "UNILABOR", "SODRE", "BRASILIENSE", "MB_CAEP"]

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

# =============================================================================
# 🧠 2. CÉREBRO LOGÍSTICO E EXPORTAÇÃO
# =============================================================================
def tratar_texto_global(texto):
    if pd.isna(texto): return ""
    t = unicodedata.normalize('NFKD', str(texto).replace('"', '').replace("'", "").replace('\n', ' ')).encode('ASCII', 'ignore').decode('utf-8').upper().strip()
    if t in ['0', '0.0', 'NAN', 'NONE', 'NAT']: return ""
    return t[:-2] if t.endswith('.0') else t

def limpar_nome_local_rota(texto):
    t = tratar_texto_global(texto)
    return t.split('/')[0].split('-')[0].strip()

def obter_login_agente(cidade, bairro, laboratorio, endereco="", base_rotas_df=pd.DataFrame()):
    if base_rotas_df.empty: return ""
    rotas_dict = dict(zip(base_rotas_df['ROTA MAPEADA'].str.upper(), base_rotas_df['LOGIN DO AGENTE'].str.lower()))
    cid, bai, lab, end = limpar_nome_local_rota(cidade), limpar_nome_local_rota(bairro), tratar_texto_global(laboratorio), tratar_texto_global(endereco)
    chaves = [f"{cid}---{bai}---{end}", f"{cid}---{lab}", f"{cid}---{bai}", cid]
    for c in chaves:
        if c in rotas_dict: return rotas_dict[c]
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

# =============================================================================
# 🎨 3. INTERFACE E NAVEGAÇÃO PREMIUM (SAAS LEVEL)
# =============================================================================

# Define a cor de fundo com base no toggle (que leremos via session_state para injetar antes)
if 'modo_escuro' not in st.session_state: st.session_state.modo_escuro = False

st.markdown("""
    <style>
    /* Esconde elementos nativos do Streamlit que poluem a tela */
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
    [data-testid="stSidebarNav"] {display: none;}
    
    /* Estilo Ultra Premium para o Menu Lateral (Radio Buttons) */
    div.stRadio > div[role="radiogroup"] {
        display: flex; flex-direction: column; gap: 8px; width: 100% !important;
    }
    div[role="radiogroup"] > label {
        width: 100% !important;
        padding: 12px 16px !important;
        border-radius: 8px !important;
        margin: 0 !important;
        border: none !important;
        background-color: transparent !important;
        cursor: pointer !important;
        transition: all 0.2s ease-in-out !important;
        box-sizing: border-box !important;
    }
    div[role="radiogroup"] > label:hover {
        background-color: rgba(56, 189, 248, 0.08) !important;
    }
    /* Esconde a "bolinha" do radio */
    div[role="radiogroup"] label div[data-testid="stRadio-radio"] { 
        display: none !important; 
    }
    /* Estilo do Texto Padrão do Menu */
    div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p { 
        font-size: 15px !important; 
        font-weight: 500 !important; 
        margin: 0 !important;
        color: #64748b !important; /* Cor suave (ajustada depois no modo escuro) */
        transition: color 0.2s ease !important;
    }
    /* Estilo do Menu ATIVO */
    div[role="radiogroup"] > label[data-checked="true"] { 
        background-color: rgba(56, 189, 248, 0.12) !important; 
        border-left: 4px solid #38BDF8 !important; 
        border-radius: 0 8px 8px 0 !important;
    }
    div[role="radiogroup"] > label[data-checked="true"] div[data-testid="stMarkdownContainer"] p { 
        color: #0284c7 !important; 
        font-weight: 700 !important; 
    }

    /* Estilo dos Botões de KPI Superiores */
    div.st-key-kpi_total button { background: linear-gradient(135deg, #1E3A8A 0%, #3B82F6 100%) !important; height: 75px !important; border-radius: 10px !important; border: none !important; color: white !important;}
    div.st-key-kpi_entregue button { background: linear-gradient(135deg, #064E3B 0%, #10B981 100%) !important; height: 75px !important; border-radius: 10px !important; border: none !important; color: white !important;}
    div.st-key-kpi_frus button { background: linear-gradient(135deg, #9A3412 0%, #F59E0B 100%) !important; height: 75px !important; border-radius: 10px !important; border: none !important; color: white !important;}
    div.st-key-kpi_atra button { background: linear-gradient(135deg, #7F1D1D 0%, #EF4444 100%) !important; height: 75px !important; border-radius: 10px !important; border: none !important; color: white !important;}
    div.st-key-kpi_hoje button { background: linear-gradient(135deg, #4C1D95 0%, #8B5CF6 100%) !important; height: 75px !important; border-radius: 10px !important; border: none !important; color: white !important;}
    div.st-key-kpi_total button p, div.st-key-kpi_entregue button p, div.st-key-kpi_frus button p, div.st-key-kpi_atra button p, div.st-key-kpi_hoje button p { font-weight: 800 !important; font-size: 15px !important; margin: 0 !important; color: white !important;}
    
    /* Toggle de Modo Escuro disfarçado */
    label[data-testid="stWidgetLabel"] {display: none;}
    </style>
""", unsafe_allow_html=True)

if 'filtro_kpi_admin' not in st.session_state: st.session_state.filtro_kpi_admin = "TODOS"

with st.sidebar:
    # Header Premium Simétrico (Logo e Toggle na mesma linha)
    col_logo, col_tema = st.columns([3, 1], vertical_alignment="center")
    with col_logo:
        st.markdown("<h2 style='color:#38BDF8; margin: 0; padding-bottom: 5px; font-weight: 800;'>IGO ADMIN</h2>", unsafe_allow_html=True)
    with col_tema:
        st.session_state.modo_escuro = st.toggle("🌙", value=st.session_state.modo_escuro, label_visibility="collapsed", help="Alternar Modo Claro/Escuro")
    
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True) # Espaçamento elegante
    
    # Menu Ultra Premium
    menu = st.radio("Navegação:", ["📊 Dashboard de Controle", "➕ Importação de Lotes", "📋 Triagem e Romaneio", "📥 Exportar Relatórios", "⚙️ Configurar Rotas"], label_visibility="collapsed")
    
    # Espaçador Flexível para jogar o botão de Sair pro final (Truque de UI)
    st.markdown("<div style='margin-top: 100%;'></div>", unsafe_allow_html=True)
    
    st.divider()
    # Botão de Sair Minimalista e Funcional
    if st.button("🚪 Sair do Sistema", use_container_width=True, type="secondary"):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.rerun()

# Cores Dinâmicas Baseadas no Toggle
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
/* Injeta cores escuras no menu caso o toggle esteja ativado */
div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p {{ color: {txt_menu} !important; }}
div[role="radiogroup"] > label[data-checked="true"] div[data-testid="stMarkdownContainer"] p {{ color: {txt_menu_ativo} !important; }}
</style>""", unsafe_allow_html=True)

def obter_css_grid():
    base_css = {
        ".ag-root-wrapper": {"border": f"1px solid {border_c} !important", "border-radius": "8px"},
        ".ag-header": {"background-color": "#1e293b !important"},
        ".ag-header-cell-text": {"color": "#f8fafc !important", "font-weight": "bold"},
        ".ag-cell": {"font-size": "13px !important", "font-family": "Inter, sans-serif !important"},
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
            ".ag-row-hover": {"background-color": "#f1f5f9 !important"}
        })
    return base_css

# =============================================================================
# 🚀 MÓDULO 1: DASHBOARD DE CONTROLE
# =============================================================================
if menu == "📊 Dashboard de Controle":
    df_raw = carregar_dados_completos(planilha_db)
    hoje_br = datetime.now(FUSO_BR).date()
    
    if not df_raw.empty:
        df_raw['FOTO_URL'] = df_raw['FOTO'].apply(lambda x: f"https://www.appsheet.com/template/gettablefileurl?appName=APPIGOLOGISTICA-153047553&tableName=App_Tarefas&fileName={str(x).strip()}" if str(x).strip() and str(x).upper() not in ['NAN', 'NONE', ''] else "")
        
        def calc_status(row):
            s_db, s_app = str(row.get('STATUS', '')).strip().upper(), str(row.get('APP_STATUS', '')).strip().upper()
            status_final = s_app if s_app and s_app != 'NAN' else s_db
            previsao = str(row.get('DATA_LIMITE', '')).strip()
            res = '⏳ Pendente'
            if 'ENTREGUE' in status_final: res = '✅ Entregue'
            elif 'COLETADO' in status_final: res = '📦 Coletado'
            elif 'ROTA' in status_final: res = '🚚 Em Rota'
            elif 'CONFERIDO' in status_final: res = '☑️ Conferido'
            elif 'FRUSTRADA' in status_final: res = '❌ Frustrada'
            elif 'CANCELADO' in status_final: res = '🚫 Cancelado'
            if '✅' not in res and '🚫' not in res and '❌' not in res and previsao:
                try:
                    if datetime.strptime(previsao, "%d/%m/%Y").date() < hoje_br: res = f"🚨 ATRASADO ({res})"
                except: pass
            return res

        df_raw['STATUS_DISPLAY'] = df_raw.apply(calc_status, axis=1)
        
        if 'DATA_LIMITE' in df_raw.columns: df_raw['DATA_LIMITE'] = df_raw['DATA_LIMITE'].fillna("").astype(str)
        if 'DATA_ENTREGA' in df_raw.columns: df_raw['DATA_ENTREGA'] = df_raw['DATA_ENTREGA'].fillna("").astype(str)

        st.markdown("<div class='dinamic-border' style='padding-bottom: 10px; margin-bottom: 20px;'><h2 class='dinamic-text' style='margin:0;'>📊 Painel de Controle Operacional</h2></div>", unsafe_allow_html=True)

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
        
        colunas_mostrar = ['DATA', 'PEDIDO', 'TOMADOR', 'STATUS_DISPLAY', 'AGENTE_RAW', 'LABORATORIO', 'CIDADE', 'UF', 'DATA_LIMITE', 'DATA_ENTREGA', 'FOTO_URL']
        df_grid = df_grid[[c for c in colunas_mostrar if c in df_grid.columns]]
        
        if busca:
            mask = df_grid.astype(str).apply(lambda x: busca.upper() in x.str.upper().values, axis=1)
            df_grid = df_grid[mask]

        st.markdown(f"<p class='dinamic-text' style='color:#10B981 !important; font-weight:bold; font-size:12px; margin-bottom: 5px;'>🟢 Sincronizado: {datetime.now(FUSO_BR).strftime('%H:%M')}</p>", unsafe_allow_html=True)
        
        container_botoes = st.container()
        container_grid = st.container()

        with container_grid:
            gb = GridOptionsBuilder.from_dataframe(df_grid)
            gb.configure_default_column(resizable=True, sortable=True, minWidth=120)
            gb.configure_selection('multiple', use_checkbox=True, header_checkbox=True)
            
            st_js = JsCode("function(p){let v=p.value||''; if(v.includes('Entregue')){return {'backgroundColor':'rgba(16,185,129,0.15)','color':'#10B981','fontWeight':'900'};} if(v.includes('ATRASADO') || v.includes('Frustrada')){return {'backgroundColor':'rgba(239,68,68,0.15)','color':'#EF4444','fontWeight':'900'};} if(v.includes('Em Rota')){return {'backgroundColor':'rgba(245,158,11,0.15)','color':'#F59E0B','fontWeight':'900'};} if(v.includes('Coletado') || v.includes('Conferido')){return {'backgroundColor':'rgba(59,130,246,0.15)','color':'#3B82F6','fontWeight':'900'};} return {'fontWeight':'bold'};}")
            gb.configure_column("STATUS_DISPLAY", headerName="STATUS", cellStyle=st_js, width=160)
            
            img_js = JsCode("""
            class FotoRenderer {
                init(params) {
                    this.eGui = document.createElement('div');
                    this.eGui.style.textAlign = 'center';
                    let val = params.value;
                    if (val && val !== '' && val !== 'nan' && val !== 'None' && val.includes('http')) {
                        this.eGui.innerHTML = '<span style="cursor: pointer; font-size: 20px;" title="Ver Comprovante">📸</span>';
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
            
            grid_response = AgGrid(df_grid, gridOptions=gb.build(), allow_unsafe_jscode=True, theme='alpine', custom_css=obter_css_grid(), height=450)
            
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
                    white-space: nowrap !important; overflow: hidden !important; font-weight: bold !important;
                }
                </style>
            """, unsafe_allow_html=True)
            
            col_b1, col_b2, col_b3, col_b4, col_b5, col_b6 = st.columns([1.3, 1, 1, 1.4, 1.2, 0.9])
            
            with col_b1.popover("➕ Novo Pedido", use_container_width=True):
                st.markdown("Inserir Pedido Manual (Urgências e Testes)")
                with st.form("form_manual", clear_on_submit=True):
                    m_tomador = st.selectbox("Tomador:", ["Selecione..."] + CLIENTES_AUTORIZADOS)
                    m_data = st.date_input("Data:", format="DD/MM/YYYY")
                    m_lab = st.text_input("Lab/Clínica:")
                    m_rua = st.text_input("Endereço:")
                    m_bai = st.text_input("Bairro:")
                    m_cid = st.text_input("Cidade:")
                    logins_disp = sorted(DF_AGENTES['LOGIN DO AGENTE'].unique().tolist()) if not DF_AGENTES.empty else []
                    m_agente_escolha = st.selectbox("Motorista:", ["Automático (Por Rota)"] + logins_disp)
                    
                    if st.form_submit_button("💾 Salvar Pedido", type="primary"):
                        if m_tomador == "Selecione..." or not m_cid: st.error("Tomador e Cidade são obrigatórios!")
                        else:
                            with st.spinner("Salvando..."):
                                m_agente = obter_login_agente(m_cid, m_bai, m_lab, m_rua, DF_AGENTES) if m_agente_escolha == "Automático (Por Rota)" else m_agente_escolha
                                m_prazo = calcular_sla_dias("SP", m_cid)
                                m_limite = calcular_data_limite(m_data.strftime("%d/%m/%Y"), m_prazo)
                                m_pedido = str(random.randint(100000, 999999))
                                novo_ped = pd.DataFrame([{'DATA': m_data.strftime("%d/%m/%Y"), 'PEDIDO': m_pedido, 'TOMADOR': m_tomador, 'LABORATORIO': m_lab.upper(), 'ENDERECO': m_rua.upper(), 'NUMERO': "", 'BAIRRO': m_bai.upper(), 'CIDADE': m_cid.upper(), 'UF': "SP", 'CEP': "", 'STATUS': 'PENDENTE', 'AGENTE_RAW': m_agente, 'PRAZO_DIAS': m_prazo, 'DATA_LIMITE': m_limite, 'DATA_ENTREGA': "", 'FOTO': "", 'ROMANEIO': ""}])
                                try:
                                    aba_memoria = planilha_db.worksheet("Memoria_Sistema")
                                    dados_atuais = aba_memoria.get_all_values()
                                    df_nuvem = pd.DataFrame(dados_atuais[1:], columns=dados_atuais[0]) if len(dados_atuais) > 1 else pd.DataFrame()
                                    df_atual = pd.concat([df_nuvem, novo_ped], ignore_index=True) if not df_nuvem.empty else novo_ped
                                    aba_memoria.clear()
                                    aba_memoria.update("A1", [df_atual.columns.tolist()] + df_atual.fillna("").astype(str).values.tolist())
                                    if m_agente: despachar_para_appsheet([novo_ped.iloc[0].to_dict()])
                                    st.success(f"Pedido {m_pedido} criado!")
                                    st.cache_data.clear()
                                    st.rerun()
                                except Exception as e: st.error(f"Erro: {e}")

            with col_b2.popover("📲 Dar Baixa", use_container_width=True):
                if not tem_sel: st.warning("Selecione na Grid primeiro!")
                else:
                    status_baixa = st.selectbox("Novo Status:", ["ENTREGUE ✅", "COLETADO 📦", "PROBLEMA 🚨", "CANCELADO ❌"])
                    if st.button("Confirmar Baixa", type="primary", use_container_width=True):
                        with st.spinner("Atualizando Banco..."):
                            status_limpo = status_baixa.split(" ")[0].upper()
                            try:
                                aba = planilha_db.worksheet("Memoria_Sistema")
                                dados_aba = aba.get_all_values()
                                df_nuvem = pd.DataFrame(dados_aba[1:], columns=dados_aba[0])
                                for pid in p_ids:
                                    mask = df_nuvem['PEDIDO'] == pid
                                    df_nuvem.loc[mask, 'STATUS'] = status_limpo
                                    if status_limpo == "ENTREGUE": df_nuvem.loc[mask, 'DATA_ENTREGA'] = hoje_br.strftime("%d/%m/%Y")
                                aba.clear()
                                aba.update("A1", [df_nuvem.columns.tolist()] + df_nuvem.fillna("").astype(str).values.tolist())
                                st.success("Atualizado!")
                                st.cache_data.clear()
                                st.rerun()
                            except Exception as e: st.error(f"Erro: {e}")

            with col_b3.popover("👯 Clonar", use_container_width=True):
                if not tem_sel: st.warning("Selecione na Grid primeiro!")
                else:
                    st.markdown(f"Deseja duplicar **{len(p_ids)}** pedidos?")
                    if st.button("Confirmar Clone", type="primary", use_container_width=True):
                        with st.spinner("Clonando..."):
                            try:
                                aba = planilha_db.worksheet("Memoria_Sistema")
                                dados_aba = aba.get_all_values()
                                df_nuvem = pd.DataFrame(dados_aba[1:], columns=dados_aba[0])
                                novas_linhas = []
                                for pid in p_ids:
                                    if pid in df_nuvem['PEDIDO'].values:
                                        l_orig = df_nuvem[df_nuvem['PEDIDO'] == pid].iloc[0].copy()
                                        l_orig['PEDIDO'] = f"{random.randint(100000, 999999)}-C"
                                        l_orig['DATA'] = hoje_br.strftime("%d/%m/%Y")
                                        l_orig['STATUS'] = "PENDENTE"
                                        l_orig['DATA_ENTREGA'] = ""; l_orig['FOTO'] = ""; l_orig['ROMANEIO'] = ""
                                        df_nuvem = pd.concat([df_nuvem, pd.DataFrame([l_orig])], ignore_index=True)
                                aba.clear()
                                aba.update("A1", [df_nuvem.columns.tolist()] + df_nuvem.fillna("").astype(str).values.tolist())
                                st.success("Clonado!")
                                st.cache_data.clear()
                                st.rerun()
                            except Exception as e: st.error(f"Erro: {e}")

            with col_b4.popover("🔄 Trocar Motorista", use_container_width=True):
                if not tem_sel: st.warning("Selecione na Grid primeiro!")
                else:
                    logins_disp = sorted(DF_AGENTES['LOGIN DO AGENTE'].unique().tolist()) if not DF_AGENTES.empty else []
                    novo_mot = st.selectbox("Novo Agente:", logins_disp)
                    if st.button("Confirmar Troca", type="primary", use_container_width=True):
                        with st.spinner("Trocando..."):
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
                                        l_app = df_nuvem[mask].iloc[0]
                                        lista_app_troca.append({'PEDIDO': pid, 'MOTORISTA': novo_mot, 'ENDERECO': l_app.get('ENDERECO',''), 'NUMERO': l_app.get('NUMERO',''), 'BAIRRO': l_app.get('BAIRRO',''), 'CIDADE': l_app.get('CIDADE',''), 'CEP': l_app.get('CEP',''), 'LABORATORIO': l_app.get('LABORATORIO',''), 'TOMADOR': l_app.get('TOMADOR','')})
                                aba.clear()
                                aba.update("A1", [df_nuvem.columns.tolist()] + df_nuvem.fillna("").astype(str).values.tolist())
                                despachar_para_appsheet(lista_app_troca)
                                st.success("Trocado!")
                                st.cache_data.clear()
                                st.rerun()
                            except Exception as e: st.error(f"Erro: {e}")

            if col_b5.button("🔄 Atualizar", use_container_width=True):
                st.cache_data.clear()
                st.rerun()
                
            col_b6.button("⚙️ Colunas", disabled=True, use_container_width=True, help="Use o menu no canto direito da tabela.")

    else:
        st.warning("📭 O banco de dados está totalmente vazio no momento.")
        st.markdown("### 🚀 Dê a partida no sistema:")
        col_vazia, _ = st.columns([1, 3])
        
        with col_vazia.popover("➕ Criar Primeiro Pedido Manual", use_container_width=True):
            st.markdown("Inserir Pedido Inicial (Urgências e Testes)")
            with st.form("form_manual_vazio", clear_on_submit=True):
                m_tomador = st.selectbox("Tomador:", ["Selecione..."] + CLIENTES_AUTORIZADOS)
                m_data = st.date_input("Data:", format="DD/MM/YYYY")
                m_lab = st.text_input("Lab/Clínica:")
                m_rua = st.text_input("Endereço:")
                m_bai = st.text_input("Bairro:")
                m_cid = st.text_input("Cidade:")
                logins_disp = sorted(DF_AGENTES['LOGIN DO AGENTE'].unique().tolist()) if not DF_AGENTES.empty else []
                m_agente_escolha = st.selectbox("Motorista:", ["Automático (Por Rota)"] + logins_disp)
                
                if st.form_submit_button("💾 Salvar Pedido", type="primary"):
                    if m_tomador == "Selecione..." or not m_cid: st.error("Tomador e Cidade são obrigatórios!")
                    else:
                        with st.spinner("Salvando..."):
                            m_agente = obter_login_agente(m_cid, m_bai, m_lab, m_rua, DF_AGENTES) if m_agente_escolha == "Automático (Por Rota)" else m_agente_escolha
                            m_prazo = calcular_sla_dias("SP", m_cid)
                            m_limite = calcular_data_limite(m_data.strftime("%d/%m/%Y"), m_prazo)
                            m_pedido = str(random.randint(100000, 999999))
                            novo_ped = pd.DataFrame([{'DATA': m_data.strftime("%d/%m/%Y"), 'PEDIDO': m_pedido, 'TOMADOR': m_tomador, 'LABORATORIO': m_lab.upper(), 'ENDERECO': m_rua.upper(), 'NUMERO': "", 'BAIRRO': m_bai.upper(), 'CIDADE': m_cid.upper(), 'UF': "SP", 'CEP': "", 'STATUS': 'PENDENTE', 'AGENTE_RAW': m_agente, 'PRAZO_DIAS': m_prazo, 'DATA_LIMITE': m_limite, 'DATA_ENTREGA': "", 'FOTO': "", 'ROMANEIO': ""}])
                            try:
                                aba_memoria = planilha_db.worksheet("Memoria_Sistema")
                                dados_atuais = aba_memoria.get_all_values()
                                df_nuvem = pd.DataFrame(dados_atuais[1:], columns=dados_atuais[0]) if len(dados_atuais) > 1 else pd.DataFrame()
                                df_atual = pd.concat([df_nuvem, novo_ped], ignore_index=True) if not df_nuvem.empty else novo_ped
                                aba_memoria.clear()
                                aba_memoria.update("A1", [df_atual.columns.tolist()] + df_atual.fillna("").astype(str).values.tolist())
                                if m_agente: despachar_para_appsheet([novo_ped.iloc[0].to_dict()])
                                st.success(f"Pedido {m_pedido} criado!")
                                st.cache_data.clear()
                                st.rerun()
                            except Exception as e: st.error(f"Erro: {e}")

# =============================================================================
# ➕ MÓDULO 2: IMPORTAÇÃO DE LOTES
# =============================================================================
elif menu == "➕ Importação de Lotes":
    st.markdown("<h2 class='dinamic-text'>➕ Central de Importação</h2>", unsafe_allow_html=True)
    
    st.success("🛡️ **SEGURANÇA DO HISTÓRICO:** O sistema de importação sempre **ADICIONA** os novos pedidos na base. O seu histórico do dia (como os lotes de RJ e Juiz de Fora) estão seguros e não serão apagados ao importar uma nova planilha.")
    
    if "df_preview" not in st.session_state: st.session_state.df_preview = pd.DataFrame()
    if "texto_importacao" not in st.session_state: st.session_state.texto_importacao = ""

    with st.container(border=True):
        st.markdown("#### 1. Dados do Lote e Colagem")
        c1, c2, c3 = st.columns([1, 1, 2])
        with c1:
            tom = st.selectbox("🏢 Tomador:", ["Selecione..."] + CLIENTES_AUTORIZADOS)
        with c2:
            dt_c = st.date_input("📅 Data da Coleta:", format="DD/MM/YYYY")

        txt = st.text_area("📋 Cole os dados do Excel aqui (Ctrl+V):", height=150, key="texto_importacao", help="Apenas copie as células do Excel e cole direto aqui.")

        col_btn1, _ = st.columns([1, 2])
        if col_btn1.button("🔍 1. Tratar e Roteirizar", type="primary", use_container_width=True):
            if not txt or tom == "Selecione...": st.warning("Preencha o Tomador e cole os dados!")
            else:
                try:
                    leitor = csv.reader(io.StringIO(txt), delimiter='\t' if '\t' in txt else ';')
                    dados = [l for l in leitor if any(x.strip() for x in l)]
                    idx_h = 0
                    for i, l in enumerate(dados[:10]):
                        if any(p in " ".join(l).upper() for p in ['PEDIDO', 'CIDADE', 'LABORAT']): idx_h = i; break
                    
                    df_limpo = pd.DataFrame(dados[idx_h+1:], columns=[c.upper().strip() for c in dados[idx_h]]).fillna("").astype(str)
                    for col in df_limpo.columns: df_limpo[col] = df_limpo[col].apply(tratar_texto_global)
                    
                    mapa = {}
                    for c in df_limpo.columns:
                        cl = tratar_texto_global(c)
                        if any(x in cl for x in ['PEDIDO', 'SOLICITA']): mapa[c] = 'PEDIDO'
                        elif any(x in cl for x in ['LABORAT', 'CLINIC']): mapa[c] = 'LABORATORIO'
                        elif any(x in cl for x in ['ENDERE', 'RUA']): mapa[c] = 'ENDERECO'
                        elif any(x in cl for x in ['NUM', 'Nº']): mapa[c] = 'NUMERO'
                        elif 'BAIRRO' in cl: mapa[c] = 'BAIRRO'
                        elif any(x in cl for x in ['CIDADE', 'MUNIC']): mapa[c] = 'CIDADE'
                        elif any(x in cl for x in ['UF', 'ESTADO']): mapa[c] = 'UF'
                        elif 'CEP' in cl: mapa[c] = 'CEP'
                    
                    df_limpo.rename(columns=mapa, inplace=True)
                    for c in ['PEDIDO', 'LABORATORIO', 'CEP', 'ENDERECO', 'NUMERO', 'BAIRRO', 'CIDADE', 'UF']:
                        if c not in df_limpo.columns: df_limpo[c] = ""
                    
                    for idx, row in df_limpo.iterrows():
                        e, n, b = str(row['ENDERECO']), str(row['NUMERO']), str(row['BAIRRO'])
                        if e and (not n or not b):
                            cep_m = re.search(r'(\d{5}-?\d{3})', e)
                            if cep_m: df_limpo.at[idx, 'CEP'] = cep_m.group(1); e = e.replace(cep_m.group(1), '').strip(' ,-')
                            if ',' in e and not n: 
                                pts = e.split(',')
                                df_limpo.at[idx, 'ENDERECO'], df_limpo.at[idx, 'NUMERO'] = pts[0].strip(), pts[1].strip()

                    df_limpo['UF'] = df_limpo['UF'].astype(str).str.upper().str.strip()
                    df_limpo['CIDADE'] = df_limpo['CIDADE'].astype(str).str.upper().str.strip()

                    df_limpo['TOMADOR'], df_limpo['DATA'] = tom, dt_c.strftime("%d/%m/%Y")
                    df_limpo['AGENTE_RAW'] = df_limpo.apply(lambda r: obter_login_agente(r['CIDADE'], r['BAIRRO'], r['LABORATORIO'], r['ENDERECO'], DF_AGENTES), axis=1)
                    st.session_state.df_preview = df_limpo[['DATA', 'TOMADOR', 'PEDIDO', 'LABORATORIO', 'ENDERECO', 'NUMERO', 'BAIRRO', 'CIDADE', 'UF', 'CEP', 'AGENTE_RAW']]
                    st.success("Faxina concluída! Verifique a tabela abaixo.")
                except Exception as e: st.error(f"Erro no processamento: {e}")

    if not st.session_state.df_preview.empty:
        st.markdown("---")
        st.markdown("### 👀 2. Preview dos Dados (Verifique antes de salvar)")
        
        if (st.session_state.df_preview['AGENTE_RAW'] == "").any(): 
            st.error("⚠️ Atenção: Há pedidos SEM MOTORISTA atribuído! Eles estão marcados com fundo vermelho na tabela.")
        
        gb_prev = GridOptionsBuilder.from_dataframe(st.session_state.df_preview)
        gb_prev.configure_default_column(resizable=True, sortable=True, minWidth=130)
        js_err = JsCode("function(p){if(p.data.AGENTE_RAW == ''){return {'backgroundColor': '#FDEDEC', 'color': '#B03A2E', 'fontWeight': 'bold'};} return {};}")
        gb_prev.configure_grid_options(getRowStyle=js_err)
        
        AgGrid(st.session_state.df_preview, gridOptions=gb_prev.build(), allow_unsafe_jscode=True, theme='alpine', custom_css=obter_css_grid(), height=400)
        
        st.markdown("<br>", unsafe_allow_html=True)
        col_btn2, _ = st.columns([1, 2])
        if col_btn2.button("🚀 3. SALVAR TUDO NO GOOGLE SHEETS", type="primary", use_container_width=True):
            with st.spinner("Adicionando à base geral..."):
                df_final = st.session_state.df_preview.copy()
                for idx, row in df_final.iterrows():
                    if not str(row['PEDIDO']).strip() or row['PEDIDO'] == 'NAN': df_final.at[idx, 'PEDIDO'] = str(random.randint(100000, 999999))
                
                df_final['PRAZO_DIAS'] = df_final.apply(lambda r: calcular_sla_dias(r['UF'], r['CIDADE']), axis=1)
                df_final['DATA_LIMITE'] = df_final.apply(lambda r: calcular_data_limite(r['DATA'], int(r['PRAZO_DIAS'])), axis=1)
                df_final['STATUS'], df_final['DATA_ENTREGA'], df_final['FOTO'], df_final['ROMANEIO'] = 'PENDENTE', '', '', ''
                
                try:
                    aba = planilha_db.worksheet("Memoria_Sistema")
                    atuais = aba.get_all_values()
                    
                    df_up = pd.concat([pd.DataFrame(atuais[1:], columns=atuais[0]), df_final], ignore_index=True) if len(atuais) > 1 else df_final
                    
                    aba.clear()
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
                    
                    st.success("🎉 Lote adicionado com sucesso à base principal e despachado aos motoristas!")
                    st.session_state.texto_importacao = ""
                    st.session_state.df_preview = pd.DataFrame()
                    st.cache_data.clear()
                except Exception as e: st.error(f"Erro ao salvar: {e}")

# =============================================================================
# 📋 MÓDULO 3: TRIAGEM E ROMANEIO (OTIMIZADO ANTI-LIMITE DO GOOGLE)
# =============================================================================
elif menu == "📋 Triagem e Romaneio":
    st.markdown("<h2 class='dinamic-text'>📋 Triagem e Despacho</h2>", unsafe_allow_html=True)
    df_raw = carregar_dados_completos(planilha_db)
    
    if not df_raw.empty:
        t1, t2 = st.tabs(["📦 1. Bipar / Selecionar Pedidos Coletados", "🚚 2. Gerar Romaneio e Despachar"])
        
        with t1:
            st.info("💡 Apenas pedidos **COLETADOS** aparecerão aqui.")
            with st.form("form_bip", clear_on_submit=True):
                col_bip, col_btn = st.columns([4, 1])
                bip_input = col_bip.text_input("🔍 Bipar QR Code / Pedido:")
                bip_submit = col_btn.form_submit_button("Bipar", use_container_width=True)
                
                if bip_submit and bip_input:
                    termo = re.sub(r'[^A-Z0-9]', '', bip_input.upper())
                    df_raw['PED_LIMPO'] = df_raw['PEDIDO'].astype(str).str.upper().apply(lambda x: re.sub(r'[^A-Z0-9]', '', x))
                    mask = (df_raw['PED_LIMPO'] == termo)
                    
                    if mask.any():
                        idx = df_raw[mask].index[-1]
                        status_atual = str(df_raw.at[idx, 'STATUS']).strip().upper()
                        if status_atual == 'COLETADO':
                            try:
                                aba = planilha_db.worksheet("Memoria_Sistema")
                                aba.update_cell(idx + 2, df_raw.columns.get_loc('STATUS') + 1, 'CONFERIDO')
                                st.success(f"✅ Pedido {df_raw.at[idx, 'PEDIDO']} CONFERIDO com sucesso!")
                                st.cache_data.clear()
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
                gb_fila.configure_selection('multiple', use_checkbox=True, header_checkbox=True)
                grid_fila_resp = AgGrid(df_fila, gridOptions=gb_fila.build(), theme='alpine', custom_css=obter_css_grid(), height=350, key='grid_fila_manual')
                
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
                                # OTIMIZAÇÃO: Atualização em Lote com 1 requisição
                                aba = planilha_db.worksheet("Memoria_Sistema")
                                dados_aba = aba.get_all_values()
                                df_nuvem = pd.DataFrame(dados_aba[1:], columns=dados_aba[0])
                                
                                mascara_pedidos = df_nuvem['PEDIDO'].isin(p_ids)
                                df_nuvem.loc[mascara_pedidos, 'STATUS'] = 'CONFERIDO'
                                
                                aba.clear()
                                aba.update("A1", [df_nuvem.columns.tolist()] + df_nuvem.fillna("").astype(str).values.tolist())
                                
                                st.success(f"🎉 {len(p_ids)} pedidos enviados para o Despacho!")
                                st.cache_data.clear()
                                st.rerun()
                            except Exception as e: st.error(f"Erro: {e}")
            else: st.info("Nenhum pedido aguardando triagem (Apenas pacotes 'Coletados' chegam aqui).")

        with t2:
            st.markdown("#### Selecione os pedidos Conferidos para gerar o Romaneio")
            df_conf = df_raw[df_raw['STATUS'].astype(str).str.upper() == 'CONFERIDO'].copy()
            if not df_conf.empty:
                gb = GridOptionsBuilder.from_dataframe(df_conf[['DATA', 'PEDIDO', 'TOMADOR', 'LABORATORIO', 'CIDADE', 'UF']])
                gb.configure_selection('multiple', use_checkbox=True, header_checkbox=True)
                grid_resp = AgGrid(df_conf, gridOptions=gb.build(), theme='alpine', custom_css=obter_css_grid(), height=300)
                
                selecionados = grid_resp['selected_rows']
                tem_sel_pdf = False
                if selecionados is not None:
                    if isinstance(selecionados, pd.DataFrame): tem_sel_pdf = not selecionados.empty
                    else: tem_sel_pdf = len(selecionados) > 0
                
                st.markdown("---")
                c_mot, c_btn = st.columns([3, 2])
                lista_mots = sorted(df_raw['AGENTE_RAW'].dropna().unique().tolist())
                motorista_escolhido = c_mot.selectbox("👤 Quem fará a entrega deste lote?", ["Selecione..."] + lista_mots)
                
                if c_btn.button("🚚 Gerar Romaneio PDF e Despachar", type="primary", use_container_width=True):
                    if not tem_sel_pdf or motorista_escolhido == "Selecione...": st.warning("⚠️ Selecione os pedidos e um motorista!")
                    else:
                        with st.spinner("Gerando PDF e atualizando em lote (Anti-Bloqueio)..."):
                            if isinstance(selecionados, pd.DataFrame): sel_lista = selecionados.to_dict('records')
                            else: sel_lista = selecionados
                            id_romaneio = f"ROM-{datetime.now().strftime('%d%m')}-{random.randint(100,999)}"
                            pedidos_ids = [str(r['PEDIDO']) for r in sel_lista]
                            
                            try:
                                # OTIMIZAÇÃO: Atualização em Lote com 1 requisição
                                aba = planilha_db.worksheet("Memoria_Sistema")
                                dados_aba = aba.get_all_values()
                                df_nuvem = pd.DataFrame(dados_aba[1:], columns=dados_aba[0])
                                
                                mascara_pedidos = df_nuvem['PEDIDO'].isin(pedidos_ids)
                                df_nuvem.loc[mascara_pedidos, 'STATUS'] = 'EM ROTA DE ENTREGA'
                                df_nuvem.loc[mascara_pedidos, 'ROMANEIO'] = id_romaneio
                                if 'AGENTE_RAW' in df_nuvem.columns:
                                    df_nuvem.loc[mascara_pedidos, 'AGENTE_RAW'] = motorista_escolhido
                                
                                aba.clear()
                                aba.update("A1", [df_nuvem.columns.tolist()] + df_nuvem.fillna("").astype(str).values.tolist())
                                
                                # Envio para o AppSheet (Já é feito em lote nativamente)
                                base_tomador = sel_lista[0].get('TOMADOR', 'CLIENTE')
                                base_cidade = sel_lista[0].get('CIDADE', '')
                                lote_app = [{
                                    'PEDIDO': id_romaneio, 'MOTORISTA': motorista_escolhido,
                                    'ENDERECO': "ENTREGA DE LOTE NO TOMADOR", 'NUMERO': f"{len(sel_lista)} VOLUMES",
                                    'BAIRRO': base_tomador, 'CIDADE': base_cidade, 'CEP': "---",
                                    'LABORATORIO': f"CONJUNTO DE {len(sel_lista)} PEDIDOS", 'TOMADOR': base_tomador, 'ROMANEIO': id_romaneio
                                }]
                                despachar_para_appsheet(lote_app)
                                st.cache_data.clear()
                                
                                # Geração do PDF
                                pdf = FPDF()
                                pdf.add_page()
                                pdf.set_draw_color(44, 62, 80); pdf.set_line_width(1); pdf.rect(5, 5, 200, 287)
                                pdf.set_y(15); pdf.set_font("Arial", "B", 18); pdf.set_text_color(44, 62, 80); pdf.cell(0, 8, f"PROTOCOLO DE ROMANEIO", ln=True, align="C")
                                pdf.set_font("Arial", "B", 13); pdf.set_text_color(52, 152, 219); pdf.cell(0, 8, f"LOTE: {id_romaneio} | DESPACHO IGO", ln=True, align="C")
                                pdf.set_font("Arial", "I", 10); pdf.set_text_color(127, 140, 141); pdf.cell(0, 6, f"Motorista: {motorista_escolhido} | Data: {datetime.now(FUSO_BR).strftime('%d/%m/%Y %H:%M')}", ln=True, align="C")
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
    else: st.info("O banco de dados está vazio no momento.")
# =============================================================================
# 📥 MÓDULO 4: EXPORTAR RELATÓRIOS
# =============================================================================
elif menu == "📥 Exportar Relatórios":
    st.markdown("<h2 class='dinamic-text'>📥 Central de Exportações</h2>", unsafe_allow_html=True)
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
    st.markdown("<h2 class='dinamic-text'>⚙️ Gestão de Agentes e Rotas</h2>", unsafe_allow_html=True)
    
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
                        aba.clear()
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
                        aba.clear()
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
                            planilha_db.worksheet("Agentes").clear()
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
                                aba.clear()
                                aba.update("A1", [df_novo.columns.tolist()] + df_novo.fillna("").astype(str).values.tolist())
                                carregar_dados_agentes.clear()
                                st.rerun()
                            except Exception as e: st.error(f"Erro ao remover: {e}")
        else: st.warning("Nenhum dado encontrado.")
