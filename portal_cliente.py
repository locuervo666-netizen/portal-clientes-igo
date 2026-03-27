import streamlit as st
import pandas as pd
import gspread
import os
import json
from datetime import datetime, date, timezone, timedelta
from streamlit_autorefresh import st_autorefresh
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

FUSO_BR = timezone(timedelta(hours=-3))

# =======================================================
# 🎨 1. CONFIGURAÇÃO E CSS (TRANSFORMAÇÃO DE BOTÕES EM CARDS)
# =======================================================
st.set_page_config(page_title="Portal IGO Logística", layout="wide", page_icon="🚚", initial_sidebar_state="expanded")
st_autorefresh(interval=60000, limit=None, key="refresh_timer")

# CSS Mestre: Transforma botões comuns em Cards Clicáveis
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #f0f2f6; }
    .block-container { padding-top: 1.5rem !important; }
    
    /* Configuração Geral dos Botões-Cards */
    div.stButton > button {
        height: 120px !important;
        border-radius: 15px !important;
        border: none !important;
        color: white !important;
        padding: 20px !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1) !important;
        transition: all 0.3s ease !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
    }
    
    div.stButton > button:hover {
        transform: translateY(-5px) !important;
        box-shadow: 0 8px 25px rgba(0,0,0,0.2) !important;
        opacity: 0.95;
    }

    /* Cores Individuais por Key */
    .st-key-kpi_total > button { background: linear-gradient(135deg, #1E3A8A 0%, #3B82F6 100%) !important; }
    .st-key-kpi_frus > button { background: linear-gradient(135deg, #9A3412 0%, #F59E0B 100%) !important; }
    .st-key-kpi_atra > button { background: linear-gradient(135deg, #7F1D1D 0%, #EF4444 100%) !important; }
    .st-key-kpi_hoje > button { background: linear-gradient(135deg, #064E3B 0%, #10B981 100%) !important; }

    /* Estilo do Texto dentro do Botão-Card */
    .stButton p { 
        font-weight: 900 !important; 
        font-family: 'Inter', sans-serif !important;
        margin: 0 !important;
        line-height: 1.2 !important;
    }
    
    h1 { color: #0f172a; font-weight: 900; font-size: 26px; }
    .sync-status { text-align: right; font-size: 12px; color: #10B981; font-weight: 600; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

CLIENTES_CONFIG = {
    "GRALAB": {"senha": "123", "logo": "https://cdn.awsli.com.br/2702/2702264/logo/gralab-rbuogsxve7.png"},
    "IGO_LOGISTICA": {"senha": "admin", "logo": "https://cdn-icons-png.flaticon.com/512/1532/1532692.png"}
}

# =======================================================
# 🔗 2. MOTOR DE DADOS
# =======================================================
@st.cache_data(ttl=60)
def carregar_dados_nuvem():
    try:
        if "google_credentials" in st.secrets:
            gc = gspread.oauth(credentials_filename="cred_temp.json", authorized_user_filename="token_temp.json")
        else:
            gc = gspread.oauth(credentials_filename="credentials.json", authorized_user_filename="token.json")
        planilha = gc.open("DB_IGO_Logistica")
        aba = planilha.worksheet("Memoria_Sistema")
        dados = aba.get_all_values()
        if len(dados) > 1:
            df = pd.DataFrame(dados[1:], columns=dados[0])
            df.columns = df.columns.str.strip().str.upper() 
            if 'DATA' in df.columns:
                df['DATA_OBJ'] = pd.to_datetime(df['DATA'], format='%d/%m/%Y', errors='coerce').dt.date
            return df
    except: pass
    return pd.DataFrame()

if 'logado' not in st.session_state: st.session_state.logado = False
if 'filtro_kpi' not in st.session_state: st.session_state.filtro_kpi = "TODOS"

# =======================================================
# 🔐 3. TELA DE LOGIN
# =======================================================
if not st.session_state.logado:
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        with st.container(border=True):
            st.image("https://cdn-icons-png.flaticon.com/512/1532/1532692.png", width=60)
            st.markdown("### Acesso ao Portal")
            u = st.text_input("Usuário").upper().strip()
            s = st.text_input("Senha", type="password")
            if st.button("Entrar", type="primary", use_container_width=True):
                if u in CLIENTES_CONFIG and s == CLIENTES_CONFIG[u]["senha"]:
                    st.session_state.logado, st.session_state.cliente = True, u
                    st.rerun()
                else: st.error("Incorreto.")
else:
    # =======================================================
    # 🚀 4. PAINEL PRINCIPAL (SaaS STYLE)
    # =======================================================
    df_raw = carregar_dados_nuvem()
    if not df_raw.empty:
        df_cliente = df_raw if st.session_state.cliente == "IGO_LOGISTICA" else df_raw[df_raw['TOMADOR'] == st.session_state.cliente].copy()
        hoje_br = datetime.now(FUSO_BR).date()
        
        # 📸 Tradutor de Fotos & Detalhes
        if 'FOTO' in df_cliente.columns:
            df_cliente['FOTO_URL'] = df_cliente['FOTO'].apply(lambda x: f"https://www.appsheet.com/template/gettablefileurl?appName=APPIGOLOGISTICA-153047553&tableName=App_Tarefas&fileName={str(x).strip()}" if str(x).strip() and str(x).upper() not in ['NAN', 'NONE', ''] else "")

        col_resp = 'QUEM ATENDEU?' if 'QUEM ATENDEU?' in df_cliente.columns else 'QUEM ATENDEU'
        col_obs = 'OBSERVACOES' if 'OBSERVACOES' in df_cliente.columns else 'OBS'

        def processar_linha(row):
            s, previsao = str(row.get('STATUS', '')).upper(), str(row.get('DATA_LIMITE', '')).strip()
            if 'ENTREGUE' in s: res = '✅ Entregue'
            elif any(x in s for x in ['ROTA', 'ENTREGA']): res = '🚚 Em Rota'
            elif 'COLETADO' in s: res = '📦 Coletado'
            elif 'FRUSTRADA' in s: res = '❌ Frustrada'
            elif 'CANCELADO' in s: res = '🚫 Cancelado'
            else: res = '⏳ Pendente'
            if res not in ['✅ Entregue', '🚫 Cancelado', '❌ Frustrada'] and previsao:
                try:
                    if datetime.strptime(previsao, "%d/%m/%Y").date() < hoje_br: res = f"🚨 ATRASADO ({res})"
                except: pass
            return res

        df_cliente['STATUS_F'] = df_cliente.apply(processar_linha, axis=1)
        df_cliente['DETALHES'] = df_cliente.apply(lambda r: f"🗣️ {str(r.get(col_resp,''))} / 📝 {str(r.get(col_obs,''))}" if 'FRUSTRADA' in str(r.get('STATUS','')).upper() else "", axis=1)

        # Sidebar
        with st.sidebar:
            st.image(CLIENTES_CONFIG[st.session_state.cliente]["logo"], width=160)
            st.divider()
            min_d = df_cliente['DATA_OBJ'].dropna().min() if 'DATA_OBJ' in df_cliente.columns else hoje_br
            max_d = df_cliente['DATA_OBJ'].dropna().max() if 'DATA_OBJ' in df_cliente.columns else hoje_br
            datas_sel = st.date_input("🗓️ Período:", value=(min_d, max_d), format="DD/MM/YYYY")
            cidades_sel = st.multiselect("📍 Cidades:", options=sorted(df_cliente['CIDADE'].dropna().unique().tolist()))
            busca_ped = st.text_input("🔍 Pedido / Nº:")
            with st.popover("⚙️ Colunas", use_container_width=True):
                col_vis = st.multiselect("Ver:", options=['PEDIDO', 'DATA', 'STATUS', 'DETALHES', 'LABORATORIO', 'CIDADE', 'UF', 'BAIRRO', 'FOTO_URL'], default=['PEDIDO', 'DATA', 'STATUS', 'LABORATORIO', 'CIDADE', 'FOTO_URL'])
            if st.button("🚪 Sair", use_container_width=True):
                st.session_state.logado = False
                st.rerun()

        # Filtros de busca
        df_f = df_cliente.copy()
        if len(datas_sel) == 2: df_f = df_f[(df_f['DATA_OBJ'] >= datas_sel[0]) & (df_f['DATA_OBJ'] <= datas_sel[1])]
        if cidades_sel: df_f = df_f[df_f['CIDADE'].isin(cidades_sel)]
        if busca_ped:
            b = str(busca_ped).upper()
            df_f = df_f[df_f['PEDIDO'].astype(str).str.contains(b) | df_f['NUMERO'].astype(str).str.contains(b)]

        # Contagem para os Cards
        n_total = len(df_f)
        n_frus = len(df_f[df_f['STATUS_F'].str.contains('Frustrada', na=False)])
        n_atra = len(df_f[df_f['STATUS_F'].str.contains('ATRASADO', na=False)])
        n_hoje = len(df_f[df_f['DATA_OBJ'] == hoje_br])

        st.markdown(f"<h1>Painel de Cargas | {st.session_state.cliente}</h1>", unsafe_allow_html=True)

        # --- 📈 CARDS CLICÁVEIS (O BOTÃO É O CARD) ---
        c1, c2, c3, c4 = st.columns(4)
        
        # Função para mudar o filtro e dar refresh
        def click_kpi(valor): st.session_state.filtro_kpi = valor

        with c1:
            st.button(f"TOTAL FILTRADO\n\n{n_total}", key="kpi_total", on_click=click_kpi, args=("TODOS",))
        with c2:
            st.button(f"COLETAS FRUSTRADAS\n\n{n_frus}", key="kpi_frus", on_click=click_kpi, args=("FRUSTRADA",))
        with c3:
            st.button(f"PEDIDOS ATRASADOS\n\n{n_atra}", key="kpi_atra", on_click=click_kpi, args=("ATRASADO",))
        with c4:
            st.button(f"PARA HOJE\n\n{n_hoje}", key="kpi_hoje", on_click=click_kpi, args=("HOJE",))

        # Lógica de Filtro Ativo
        df_grid = df_f.copy()
        if st.session_state.filtro_kpi == "FRUSTRADA":
            df_grid = df_grid[df_grid['STATUS_F'].str.contains('Frustrada', na=False)]
            st.info("🎯 Exibindo apenas **Coletas Frustradas**. Clique no card 'Total' para limpar.")
        elif st.session_state.filtro_kpi == "ATRASADO":
            df_grid = df_grid[df_grid['STATUS_F'].str.contains('ATRASADO', na=False)]
            st.warning("🚨 Exibindo apenas **Pedidos Atrasados**. Clique no card 'Total' para limpar.")
        elif st.session_state.filtro_kpi == "HOJE":
            df_grid = df_grid[df_grid['DATA_OBJ'] == hoje_br]
            st.success("📅 Exibindo apenas **Pedidos de Hoje**. Clique no card 'Total' para limpar.")

        # Preparação Grid
        df_grid['STATUS'] = df_grid['STATUS_F']
        df_final = df_grid[[c for c in col_vis if c in df_grid.columns]]

        gb = GridOptionsBuilder.from_dataframe(df_final)
        gb.configure_default_column(resizable=True, sortable=True, minWidth=100)
        gb.configure_selection('single', use_checkbox=False)
        
        if 'FOTO_URL' in df_final.columns:
            link_jscode = JsCode("""class LinkCellRenderer { init(params) { this.eGui = document.createElement('div'); this.eGui.style.textAlign = 'center'; if (params.value) { this.eGui.innerHTML = '<a href="' + params.value + '" target="_blank" style="text-decoration: none; font-size: 18px;">📸</a>'; } } getGui() { return this.eGui; } }""")
            gb.configure_column("FOTO_URL", headerName="Foto", cellRenderer=link_jscode, width=70)
        
        grid_css = {".ag-header-cell-text": {"font-size": "12px !important", "font-weight": "bold"}, ".ag-cell": {"font-size": "12px !important"}}
        
        AgGrid(df_final, gridOptions=gb.build(), allow_unsafe_jscode=True, theme='alpine', custom_css=grid_css, fit_columns_on_grid_load=True, height=550)
        
        st.markdown(f"<div class='sync-status'>🟢 Sincronizado {datetime.now(FUSO_BR).strftime('%H:%M')}</div>", unsafe_allow_html=True)
