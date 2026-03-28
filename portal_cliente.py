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
# 🎨 1. CONFIGURAÇÃO DA PÁGINA E CSS (COMPACTO)
# =======================================================
st.set_page_config(page_title="Monitoramento IGO Logística", layout="wide", page_icon="🚚", initial_sidebar_state="expanded")
st_autorefresh(interval=60000, limit=None, key="refresh_timer")

st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #f0f2f6; font-family: 'Inter', sans-serif; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {background-color: transparent !important;}
    
    /* ✂️ Redução agressiva de espaços vazios no topo */
    .block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; padding-left: 2rem !important; padding-right: 2rem !important; }
    
    /* 🗜️ Diminuição dos Cards Coloridos */
    div.stButton > button {
        height: 85px !important;
        border-radius: 12px !important;
        border: none !important;
        color: white !important;
        padding: 10px !important;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1) !important;
        transition: all 0.2s ease !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
    }
    div.stButton > button:hover { transform: translateY(-3px) !important; box-shadow: 0 6px 15px rgba(0,0,0,0.15) !important; opacity: 0.95; }

    .st-key-kpi_total > button { background: linear-gradient(135deg, #1E3A8A 0%, #3B82F6 100%) !important; }
    .st-key-kpi_frus > button { background: linear-gradient(135deg, #9A3412 0%, #F59E0B 100%) !important; }
    .st-key-kpi_atra > button { background: linear-gradient(135deg, #7F1D1D 0%, #EF4444 100%) !important; }
    .st-key-kpi_hoje > button { background: linear-gradient(135deg, #064E3B 0%, #10B981 100%) !important; }

    .stButton p { font-weight: 900 !important; font-size: 13px !important; font-family: 'Inter', sans-serif !important; margin: 0 !important; line-height: 1.2 !important; }
    
    /* 🔤 Título menor e limpo */
    h2 { color: #0f172a; font-weight: 900; font-size: 24px !important; margin-bottom: -15px !important; padding-bottom: 0px !important; }
    
    /* 🟢 Status de sincronização flutuando à direita do título */
    .header-container { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 15px; }
    .sync-status { font-size: 12px; color: #10B981; font-weight: 700; }
    </style>
    """, unsafe_allow_html=True)

CLIENTES_CONFIG = {
    "GRALAB": {"senha": "123", "logo": "https://cdn.awsli.com.br/2702/2702264/logo/gralab-rbuogsxve7.png"},
    "IGO_LOGISTICA": {"senha": "admin", "logo": "https://cdn-icons-png.flaticon.com/512/1532/1532692.png"}
}
LOGO_PADRAO = "https://cdn-icons-png.flaticon.com/512/1532/1532692.png"

# =======================================================
# 🔗 2. MOTOR DE DADOS
# =======================================================
@st.cache_data(ttl=30)
def carregar_dados_nuvem():
    try:
        if "google_credentials" in st.secrets:
            gc = gspread.oauth(credentials_filename="cred_temp.json", authorized_user_filename="token_temp.json")
        else:
            gc = gspread.oauth(credentials_filename="credentials.json", authorized_user_filename="token.json")
            
        planilha = gc.open("DB_IGO_Logistica")
        aba_m = planilha.worksheet("Memoria_Sistema")
        dados_m = aba_m.get_all_values()
        
        if len(dados_m) > 1:
            df = pd.DataFrame(dados_m[1:], columns=dados_m[0])
            df.columns = df.columns.str.strip().str.upper() 
            
            try:
                aba_app = planilha.worksheet("App_Tarefas")
                dados_app = aba_app.get_all_values()
                if len(dados_app) > 1:
                    df_app = pd.DataFrame(dados_app[1:], columns=dados_app[0])
                    cols_limpas = [str(c).upper().strip().replace('?', '').replace(' ', '') for c in df_app.columns]
                    df_app.columns = cols_limpas
                    
                    col_quem, col_obs = None, None
                    for c in cols_limpas:
                        if 'QUEM' in c or 'ATEND' in c or 'RESP' in c: col_quem = c
                        if 'OBS' in c or 'MOTIV' in c: col_obs = c
                    if not col_quem and len(cols_limpas) > 14: col_quem = cols_limpas[14]
                    if not col_obs and len(cols_limpas) > 10: col_obs = cols_limpas[10]
                    
                    if col_quem or col_obs:
                        cols_merge = ['PEDIDO']
                        renames = {'PEDIDO': 'PEDIDO'}
                        if col_quem: 
                            cols_merge.append(col_quem)
                            renames[col_quem] = 'APP_QUEM'
                        if col_obs: 
                            cols_merge.append(col_obs)
                            renames[col_obs] = 'APP_OBS'
                            
                        cols_merge = list(dict.fromkeys(cols_merge))
                        df_app_clean = df_app[cols_merge].copy()
                        df_app_clean.rename(columns=renames, inplace=True)
                        
                        df['PEDIDO'] = df['PEDIDO'].astype(str).str.strip()
                        df_app_clean['PEDIDO'] = df_app_clean['PEDIDO'].astype(str).str.strip()
                        
                        df_app_clean.drop_duplicates(subset=['PEDIDO'], keep='last', inplace=True)
                        df = pd.merge(df, df_app_clean, on='PEDIDO', how='left')
            except: pass
            
            if 'DATA' in df.columns:
                df['DATA_OBJ'] = pd.to_datetime(df['DATA'], format='%d/%m/%Y', errors='coerce').dt.date
            return df
    except Exception as e:
        st.error(f"Sincronização offline: {e}")
    return pd.DataFrame()

if 'logado' not in st.session_state: st.session_state.logado = False
if 'filtro_kpi' not in st.session_state: st.session_state.filtro_kpi = "TODOS"

# =======================================================
# 🔐 3. LOGIN
# =======================================================
if not st.session_state.logado:
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        st.markdown("<br><br><br><br>", unsafe_allow_html=True)
        with st.container(border=True):
            st.image(LOGO_PADRAO, width=60)
            st.markdown("<h2 style='font-size: 24px; color: #0f172a;'>Portal IGO Logística</h2>", unsafe_allow_html=True)
            u = st.text_input("Usuário").upper().strip()
            s = st.text_input("Senha", type="password")
            if st.button("Entrar", type="primary", use_container_width=True):
                if u in CLIENTES_CONFIG and s == CLIENTES_CONFIG[u]["senha"]:
                    st.session_state.logado, st.session_state.cliente = True, u
                    st.rerun()
                else: st.error("Usuário ou senha incorretos.")
else:
    # =======================================================
    # 🚀 4. PAINEL PRINCIPAL (DESIGN COMPACTO)
    # =======================================================
    df_raw = carregar_dados_nuvem()
    if not df_raw.empty:
        df_cliente = df_raw if st.session_state.cliente == "IGO_LOGISTICA" else df_raw[df_raw['TOMADOR'] == st.session_state.cliente].copy()
        hoje_br = datetime.now(FUSO_BR).date()
        
        if 'FOTO' in df_cliente.columns:
            df_cliente['FOTO_URL'] = df_cliente['FOTO'].apply(lambda x: f"https://www.appsheet.com/template/gettablefileurl?appName=APPIGOLOGISTICA-153047553&tableName=App_Tarefas&fileName={str(x).strip()}" if str(x).strip() and str(x).upper() not in ['NAN', 'NONE', ''] else "")

        def processar_detalhes(row):
            s = str(row.get('STATUS', '')).upper()
            if 'FRUSTRADA' in s:
                resp = str(row.get('APP_QUEM', '')).strip()
                obs = str(row.get('APP_OBS', '')).strip()
                if resp.upper() in ['NAN', 'NONE']: resp = ""
                if obs.upper() in ['NAN', 'NONE']: obs = ""
                
                emoji = "📝"
                obs_up = obs.upper()
                if "FECHADO" in obs_up: emoji = "🔒"
                elif "SEM MATERIAL" in obs_up: emoji = "📭"
                elif "AUSENTE" in obs_up: emoji = "🚷"
                elif "ENDERE" in obs_up or "INCORRETO" in obs_up: emoji = "🗺️"
                elif "RECUS" in obs_up: emoji = "🛑"

                t_resp = f"🗣️ {resp}" if resp else ""
                t_obs = f"{emoji} {obs}" if obs else ""
                if t_resp and t_obs: return f"{t_resp} / {t_obs}"
                if t_resp: return t_resp
                if t_obs: return t_obs
            return ""

        df_cliente['DETALHES'] = df_cliente.apply(processar_detalhes, axis=1)

        ordem_padrao = ['PEDIDO', 'DATA', 'STATUS', 'LABORATORIO', 'CIDADE', 'UF', 'BAIRRO', 'DATA_LIMITE', 'DATA_ENTREGA', 'FOTO_URL', 'DETALHES']
        colunas_disponiveis = [c for c in ordem_padrao if c in df_cliente.columns]
        
        # --- SIDEBAR LIMPA COM BOTÃO DE EXPORTAÇÃO ---
        with st.sidebar:
            st.image(CLIENTES_CONFIG[st.session_state.cliente]["logo"], width=160)
            st.divider()
            min_d = df_cliente['DATA_OBJ'].dropna().min() if 'DATA_OBJ' in df_cliente.columns else hoje_br
            max_d = df_cliente['DATA_OBJ'].dropna().max() if 'DATA_OBJ' in df_cliente.columns else hoje_br
            datas_sel = st.date_input("🗓️ Período:", value=(min_d, max_d), format="DD/MM/YYYY")
            cidades_sel = st.multiselect("📍 Cidades:", options=sorted(df_cliente['CIDADE'].dropna().unique().tolist()))
            busca_ped = st.text_input("🔍 Pedido / Nº:")
            
            with st.popover("⚙️ Personalizar Colunas", use_container_width=True):
                col_vis = st.multiselect("Ver:", options=colunas_disponiveis, default=colunas_disponiveis)
            
            st.divider()
            # 📥 MUDANÇA AQUI: Botão de exportar foi para a barra lateral!
            df_f_export = df_cliente.copy()
            csv_data = df_f_export[col_vis].to_csv(index=False, sep=";").encode('utf-8-sig')
            st.download_button(label="📥 Exportar Excel", data=csv_data, file_name=f"Monitoramento_{st.session_state.cliente}.csv", mime="text/csv", use_container_width=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🚪 Sair", use_container_width=True):
                st.session_state.logado = False
                st.rerun()

        # Filtros
        df_f = df_cliente.copy()
        if len(datas_sel) == 2: df_f = df_f[(df_f['DATA_OBJ'] >= datas_sel[0]) & (df_f['DATA_OBJ'] <= datas_sel[1])]
        if cidades_sel: df_f = df_f[df_f['CIDADE'].isin(cidades_sel)]
        if busca_ped:
            b = str(busca_ped).upper()
            df_f = df_f[df_f['PEDIDO'].astype(str).str.contains(b) | df_f['NUMERO'].astype(str).str.contains(b)]

        def tratar_status(row):
            s, previsao = str(row.get('STATUS', '')).strip().upper(), str(row.get('DATA_LIMITE', '')).strip()
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
        
        df_f['STATUS_DISPLAY'] = df_f.apply(tratar_status, axis=1)

        # 🔤 MUDANÇA AQUI: Título menor e sincronização lado a lado
        st.markdown(f"""
        <div class="header-container">
            <h2>Monitoramento {st.session_state.cliente}</h2>
            <div class='sync-status'>🟢 Sincronizado {datetime.now(FUSO_BR).strftime('%H:%M')}</div>
        </div>
        """, unsafe_allow_html=True)

        n_tot = len(df_f)
        n_frus = len(df_f[df_f['STATUS_DISPLAY'].str.contains('Frustrada', na=False)])
        n_atra = len(df_f[df_f['STATUS_DISPLAY'].str.contains('ATRASADO', na=False)])
        n_hoje = len(df_f[df_f['DATA_OBJ'] == hoje_br])

        c1, c2, c3, c4 = st.columns(4)
        def click_kpi(valor): st.session_state.filtro_kpi = valor

        with c1: st.button(f"TOTAL FILTRADO\n\n{n_tot}", key="kpi_total", on_click=click_kpi, args=("TODOS",))
        with c2: st.button(f"COLETAS FRUSTRADAS\n\n{n_frus}", key="kpi_frus", on_click=click_kpi, args=("FRUSTRADA",))
        with c3: st.button(f"PEDIDOS ATRASADOS\n\n{n_atra}", key="kpi_atra", on_click=click_kpi, args=("ATRASADO",))
        with c4: st.button(f"PARA HOJE\n\n{n_hoje}", key="kpi_hoje", on_click=click_kpi, args=("HOJE",))

        df_grid = df_f.copy()
        if st.session_state.filtro_kpi == "FRUSTRADA":
            df_grid = df_grid[df_grid['STATUS_DISPLAY'].str.contains('Frustrada', na=False)]
            st.info("🎯 Exibindo apenas **Coletas Frustradas**. Clique no card azul para limpar.")
        elif st.session_state.filtro_kpi == "ATRASADO":
            df_grid = df_grid[df_grid['STATUS_DISPLAY'].str.contains('ATRASADO', na=False)]
            st.warning("🚨 Exibindo apenas **Pedidos Atrasados**. Clique no card azul para limpar.")
        elif st.session_state.filtro_kpi == "HOJE":
            df_grid = df_grid[df_grid['DATA_OBJ'] == hoje_br]
            st.success("📅 Exibindo apenas **Pedidos de Hoje**. Clique no card azul para limpar.")

        df_grid['STATUS'] = df_grid['STATUS_DISPLAY'] 
        df_final = df_grid[[c for c in col_vis if c in df_grid.columns]]

        # --- AG-GRID OTIMIZADO COM CABEÇALHOS EM MAIÚSCULO ---
        gb = GridOptionsBuilder.from_dataframe(df_final)
        gb.configure_default_column(resizable=True, sortable=True, minWidth=100)
        gb.configure_selection('single', use_checkbox=False)
        
        # 🔤 Força TODAS as colunas para MAIÚSCULAS e Renomeia as específicas
        for col in df_final.columns:
            header_name = col.upper()
            if col == 'DATA_LIMITE': header_name = "PREVISÃO ENTREGA"
            elif col == 'DATA_ENTREGA': header_name = "DATA ENTREGA"
            elif col == 'FOTO_URL': header_name = "FOTO"
            
            # Se for foto, aplica o renderizador do botão, senão, apenas formata o nome
            if col == 'FOTO_URL':
                link_jscode = JsCode("""class LinkCellRenderer { init(params) { this.eGui = document.createElement('div'); this.eGui.style.textAlign = 'center'; if (params.value && params.value !== '' && params.value !== 'nan') { this.eGui.innerHTML = '<a href="' + params.value + '" target="_blank" style="text-decoration: none; font-size: 18px; display: block; margin-top: 2px;">📸</a>'; } } getGui() { return this.eGui; } }""")
                gb.configure_column(col, headerName=header_name, cellRenderer=link_jscode, width=70)
            elif col == 'DETALHES':
                gb.configure_column(col, headerName=header_name, width=250, tooltipField="DETALHES")
            elif col == 'UF':
                gb.configure_column(col, headerName=header_name, width=60)
            elif col == 'DATA':
                gb.configure_column(col, headerName=header_name, width=90)
            elif col == 'PEDIDO':
                gb.configure_column(col, headerName=header_name, width=95)
            else:
                gb.configure_column(col, headerName=header_name)

        grid_css = {
            ".ag-header-cell-text": {"font-size": "11px !important", "font-weight": "bold"},
            ".ag-cell": {"font-size": "11px !important"}
        }

        AgGrid(df_final, gridOptions=gb.build(), allow_unsafe_jscode=True, theme='alpine', custom_css=grid_css, fit_columns_on_grid_load=False, height=520)
