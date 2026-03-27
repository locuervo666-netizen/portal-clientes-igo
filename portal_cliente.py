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
# 🎨 1. CONFIGURAÇÃO DA PÁGINA E CSS ELITE
# =======================================================
st.set_page_config(page_title="Portal IGO Logística", layout="wide", page_icon="🚚", initial_sidebar_state="expanded")
st_autorefresh(interval=60000, limit=None, key="refresh_timer")

st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #f0f2f6; font-family: 'Inter', sans-serif; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {background-color: transparent !important;}
    .block-container { padding-top: 1.5rem !important; padding-bottom: 1rem !important; padding-left: 2rem !important; padding-right: 2rem !important; }
    
    /* Estilização dos botões para parecerem Cards */
    div.stButton > button {
        width: 100%;
        height: 100px;
        border-radius: 12px;
        border: none;
        color: white;
        text-align: left;
        padding: 20px;
        transition: transform 0.2s, box-shadow 0.2s;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    div.stButton > button:hover { transform: translateY(-3px); box-shadow: 0 6px 15px rgba(0,0,0,0.15); border: none; }
    
    /* Cores específicas dos Cards-Botões */
    .st-key-btn_total > button { background: linear-gradient(135deg, #1E3A8A 0%, #3B82F6 100%); }
    .st-key-btn_frustrada > button { background: linear-gradient(135deg, #9A3412 0%, #F59E0B 100%); }
    .st-key-btn_atrasado > button { background: linear-gradient(135deg, #7F1D1D 0%, #EF4444 100%); }
    .st-key-btn_hoje > button { background: linear-gradient(135deg, #064E3B 0%, #10B981 100%); }

    h1 { color: #0f172a; font-weight: 900; font-size: 24px; letter-spacing: -0.5px; }
    .sync-status { text-align: right; font-size: 12px; color: #10B981; font-weight: 600; margin-top: 10px; }
    .card-label { font-size: 12px; font-weight: 700; text-transform: uppercase; opacity: 0.9; margin-bottom: 5px; }
    .card-value { font-size: 32px; font-weight: 900; }
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
            cred_dict = json.loads(st.secrets["google_credentials"])
            token_dict = json.loads(st.secrets["google_token"])
            with open("cred_temp.json", "w") as f: json.dump(cred_dict, f)
            with open("token_temp.json", "w") as f: json.dump(token_dict, f)
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
    except Exception as e:
        st.error(f"Sincronização offline: {e}")
    return pd.DataFrame()

# Inicialização de estados
if 'logado' not in st.session_state: st.session_state.logado = False
if 'filtro_kpi' not in st.session_state: st.session_state.filtro_kpi = "TODOS"

# =======================================================
# 🔐 3. LOGIN E LOGOUT
# =======================================================
if not st.session_state.logado:
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<br><br><br><br>", unsafe_allow_html=True)
        with st.container(border=True):
            st.image("https://cdn-icons-png.flaticon.com/512/1532/1532692.png", width=60)
            st.markdown("<h2 style='font-size: 24px; color: #0f172a;'>Portal IGO Logística</h2>", unsafe_allow_html=True)
            usuario = st.text_input("Usuário").upper().strip()
            senha = st.text_input("Senha", type="password")
            if st.button("Entrar", type="primary", use_container_width=True):
                if usuario in CLIENTES_CONFIG and senha == CLIENTES_CONFIG[usuario]["senha"]:
                    st.session_state.logado = True
                    st.session_state.cliente = usuario
                    st.rerun()
                else: st.error("Credenciais inválidas.")

# =======================================================
# 🚀 4. DASHBOARD V25 (CLICK-TO-FILTER)
# =======================================================
else:
    df_sistema = carregar_dados_nuvem()
    if not df_sistema.empty and 'TOMADOR' in df_sistema.columns:
        df_cliente = df_sistema if st.session_state.cliente == "IGO_LOGISTICA" else df_sistema[df_sistema['TOMADOR'] == st.session_state.cliente].copy()
        
        if not df_cliente.empty:
            # Funções de suporte
            hoje_br = datetime.now(FUSO_BR).date()
            if 'FOTO' in df_cliente.columns:
                df_cliente['FOTO_URL'] = df_cliente['FOTO'].apply(lambda x: f"https://www.appsheet.com/template/gettablefileurl?appName=APPIGOLOGISTICA-153047553&tableName=App_Tarefas&fileName={str(x).strip()}" if str(x).strip() and str(x).upper() not in ['NAN', 'NONE', ''] else "")
            
            # Formatação de detalhes e Status
            col_resp = 'QUEM ATENDEU?' if 'QUEM ATENDEU?' in df_cliente.columns else 'QUEM ATENDEU'
            col_obs = 'OBSERVACOES' if 'OBSERVACOES' in df_cliente.columns else 'OBS'
            
            def tratar_status(row):
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

            df_cliente['STATUS_FINAL'] = df_cliente.apply(tratar_status, axis=1)
            df_cliente['DETALHES'] = df_cliente.apply(lambda r: f"🗣️ {str(r.get(col_resp,''))} / 📝 {str(r.get(col_obs,''))}" if 'FRUSTRADA' in str(r.get('STATUS','')).upper() else "", axis=1)

            # --- SIDEBAR ---
            with st.sidebar:
                st.image(CLIENTES_CONFIG[st.session_state.cliente]["logo"], width=160)
                st.divider()
                min_d = df_cliente['DATA_OBJ'].dropna().min() if 'DATA_OBJ' in df_cliente.columns else hoje_br
                max_d = df_cliente['DATA_OBJ'].dropna().max() if 'DATA_OBJ' in df_cliente.columns else hoje_br
                datas_sel = st.date_input("🗓️ Período:", value=(min_d, max_d), format="DD/MM/YYYY")
                cidades_sel = st.multiselect("📍 Cidades:", options=sorted(df_cliente['CIDADE'].dropna().unique().tolist()))
                busca_ped = st.text_input("🔍 Pedido / Nº:")
                
                with st.popover("⚙️ Personalizar Colunas", use_container_width=True):
                    cols_all = ['PEDIDO', 'DATA', 'STATUS', 'DETALHES', 'LABORATORIO', 'CIDADE', 'UF', 'BAIRRO', 'ENDERECO', 'Nº', 'CEP', 'DATA_LIMITE', 'DATA_ENTREGA', 'FOTO_URL']
                    colunas_selecionadas = st.multiselect("Ver:", options=cols_all, default=['PEDIDO', 'DATA', 'STATUS', 'DETALHES', 'LABORATORIO', 'CIDADE', 'UF', 'BAIRRO', 'FOTO_URL'])
                
                if st.button("🚪 Sair", use_container_width=True):
                    st.session_state.logado = False
                    st.rerun()

            # --- APLICAÇÃO DE FILTROS BASE ---
            df_f = df_cliente.copy()
            if len(datas_sel) == 2: df_f = df_f[(df_f['DATA_OBJ'] >= datas_sel[0]) & (df_f['DATA_OBJ'] <= datas_sel[1])]
            if cidades_sel: df_f = df_f[df_f['CIDADE'].isin(cidades_sel)]
            if busca_ped:
                b = str(busca_ped).upper()
                df_f = df_f[df_f['PEDIDO'].astype(str).str.contains(b) | df_f['NUMERO'].astype(str).str.contains(b)]

            # --- 📊 CARDS INTERATIVOS (BOTÕES) ---
            v_total = len(df_f)
            v_frus = len(df_f[df_f['STATUS_FINAL'].str.contains('Frustrada', na=False)])
            v_atra = len(df_f[df_f['STATUS_FINAL'].str.contains('ATRASADO', na=False)])
            v_hoje = len(df_f[df_f['DATA_OBJ'] == hoje_br])

            st.markdown(f"<h1>Painel de Cargas | {st.session_state.cliente}</h1>", unsafe_allow_html=True)
            
            c1, c2, c3, c4 = st.columns(4)
            # Função para atualizar o estado do filtro
            def set_filter(val): st.session_state.filtro_kpi = val

            with c1:
                if st.button(f"TOTAL FILTRADO\n{v_total}", key="btn_total", on_click=set_filter, args=("TODOS",)): pass
            with c2:
                if st.button(f"COLETAS FRUSTRADAS\n{v_frus}", key="btn_frustrada", on_click=set_filter, args=("FRUSTRADA",)): pass
            with c3:
                if st.button(f"PEDIDOS ATRASADOS\n{v_atra}", key="btn_atrasado", on_click=set_filter, args=("ATRASADO",)): pass
            with c4:
                if st.button(f"ENTREGAS PARA HOJE\n{v_hoje}", key="btn_hoje", on_click=set_filter, args=("HOJE",)): pass

            # --- APLICAÇÃO DO FILTRO DOS CARDS ---
            if st.session_state.filtro_kpi == "FRUSTRADA":
                df_f = df_f[df_f['STATUS_FINAL'].str.contains('Frustrada', na=False)]
                st.info("🎯 Filtrando apenas **Coletas Frustradas**")
            elif st.session_state.filtro_kpi == "ATRASADO":
                df_f = df_f[df_f['STATUS_FINAL'].str.contains('ATRASADO', na=False)]
                st.warning("🚨 Filtrando apenas **Pedidos Atrasados**")
            elif st.session_state.filtro_kpi == "HOJE":
                df_f = df_f[df_f['DATA_OBJ'] == hoje_br]
                st.success("📅 Filtrando apenas **Pedidos de Hoje**")
            
            if st.session_state.filtro_kpi != "TODOS":
                if st.button("✖ Limpar Filtro de Card"): 
                    st.session_state.filtro_kpi = "TODOS"
                    st.rerun()

            # --- EXIBIÇÃO AG-GRID ---
            df_grid = df_f.copy()
            df_grid['STATUS'] = df_grid['STATUS_FINAL']
            df_final = df_grid[[c for c in colunas_selecionadas if c in df_grid.columns]]

            gb = GridOptionsBuilder.from_dataframe(df_final)
            gb.configure_default_column(resizable=True, sortable=True, minWidth=110)
            gb.configure_selection('single', use_checkbox=False)
            
            if 'FOTO_URL' in colunas_selecionadas:
                link_jscode = JsCode("""class LinkCellRenderer { init(params) { this.eGui = document.createElement('div'); this.eGui.style.textAlign = 'center'; if (params.value) { this.eGui.innerHTML = '<a href="' + params.value + '" target="_blank" style="text-decoration: none; font-size: 18px; display: block; margin-top: 4px;" title="Ver Foto">📸</a>'; } } getGui() { return this.eGui; } }""")
                gb.configure_column("FOTO_URL", headerName="Foto", cellRenderer=link_jscode, width=80)
            
            grid_css = {".ag-header-cell-text": {"font-size": "12px !important", "font-weight": "bold"}, ".ag-cell": {"font-size": "12px !important"}}
            
            AgGrid(df_final, gridOptions=gb.build(), allow_unsafe_jscode=True, theme='alpine', custom_css=grid_css, fit_columns_on_grid_load=True, height=500)
            
            st.markdown(f"<div class='sync-status'>🟢 Sincronizado {datetime.now(FUSO_BR).strftime('%H:%M')}</div>", unsafe_allow_html=True)
