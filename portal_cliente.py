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
# 🎨 1. CONFIGURAÇÃO DA PÁGINA E CSS BASE
# =======================================================
st.set_page_config(page_title="Monitoramento IGO Logística", layout="wide", page_icon="🚚", initial_sidebar_state="expanded")
st_autorefresh(interval=60000, limit=None, key="refresh_timer")

st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { transition: background-color 0.3s ease; font-family: 'Inter', sans-serif; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {background-color: transparent !important;}
    
    .block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; padding-left: 2rem !important; padding-right: 2rem !important; }
    
    /* 🎯 BOTÕES COLORIDOS DOS KPIs */
    div.st-key-kpi_total button, div.st-key-kpi_entregue button, div.st-key-kpi_frus button, div.st-key-kpi_atra button, div.st-key-kpi_hoje button {
        height: 75px !important;
        border-radius: 10px !important;
        border: none !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
        transition: all 0.2s ease !important;
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
    }
    
    div.st-key-kpi_total button:hover, div.st-key-kpi_entregue button:hover, div.st-key-kpi_frus button:hover, div.st-key-kpi_atra button:hover, div.st-key-kpi_hoje button:hover { 
        transform: translateY(-2px) !important; box-shadow: 0 6px 12px rgba(0,0,0,0.15) !important; opacity: 0.95 !important; 
    }

    div.st-key-kpi_total button { background: linear-gradient(135deg, #1E3A8A 0%, #3B82F6 100%) !important; }
    div.st-key-kpi_entregue button { background: linear-gradient(135deg, #064E3B 0%, #10B981 100%) !important; }
    div.st-key-kpi_frus button { background: linear-gradient(135deg, #9A3412 0%, #F59E0B 100%) !important; }
    div.st-key-kpi_atra button { background: linear-gradient(135deg, #7F1D1D 0%, #EF4444 100%) !important; }
    div.st-key-kpi_hoje button { background: linear-gradient(135deg, #4C1D95 0%, #8B5CF6 100%) !important; }
    
    div.st-key-kpi_total button p, div.st-key-kpi_entregue button p, div.st-key-kpi_frus button p, div.st-key-kpi_atra button p, div.st-key-kpi_hoje button p { 
        font-weight: 800 !important; font-size: 15px !important; font-family: 'Inter', sans-serif !important; margin: 0 !important; color: #ffffff !important;
    }
    
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
                    
                    col_quem, col_obs, col_status_app = None, None, None
                    for c in cols_limpas:
                        if 'QUEM' in c or 'ATEND' in c or 'RESP' in c or 'RECEB' in c: col_quem = c
                        if 'OBS' in c or 'MOTIV' in c: col_obs = c
                        if 'STATUS' == c: col_status_app = c
                        
                    if col_quem or col_obs or col_status_app:
                        cols_extract = ['PEDIDO']
                        renames = {'PEDIDO': 'PEDIDO'}
                        if col_status_app: cols_extract.append(col_status_app); renames[col_status_app] = 'APP_STATUS'
                        if col_quem: cols_extract.append(col_quem); renames[col_quem] = 'APP_QUEM'
                        if col_obs: cols_extract.append(col_obs); renames[col_obs] = 'APP_OBS'
                        
                        cols_extract = list(dict.fromkeys(cols_extract))
                        df_app_clean = df_app[cols_extract].copy()
                        df_app_clean.rename(columns=renames, inplace=True)
                        df_app_clean['PEDIDO'] = df_app_clean['PEDIDO'].astype(str).str.strip()
                        df_app_clean.drop_duplicates(subset=['PEDIDO'], keep='last', inplace=True)
                        
                        df_app_ind = df_app_clean[~df_app_clean['PEDIDO'].str.startswith('ROM-', na=False)]
                        df_app_rom = df_app_clean[df_app_clean['PEDIDO'].str.startswith('ROM-', na=False)].copy()
                        df_app_rom.rename(columns={'PEDIDO': 'ROMANEIO'}, inplace=True)
                        
                        df['PEDIDO'] = df['PEDIDO'].astype(str).str.strip()
                        if 'ROMANEIO' not in df.columns: df['ROMANEIO'] = ""
                        df['ROMANEIO'] = df['ROMANEIO'].astype(str).str.strip()
                        
                        df = pd.merge(df, df_app_ind, on='PEDIDO', how='left')
                        
                        if not df_app_rom.empty:
                            df = pd.merge(df, df_app_rom, on='ROMANEIO', how='left', suffixes=('', '_R'))
                            for c in ['APP_STATUS', 'APP_QUEM', 'APP_OBS']:
                                if c in df.columns and f"{c}_R" in df.columns:
                                    df[c] = df[f"{c}_R"].replace("", pd.NA).combine_first(df[c].replace("", pd.NA)).fillna("")
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
    # 🚀 4. PAINEL PRINCIPAL
    # =======================================================
    df_raw = carregar_dados_nuvem()
    if not df_raw.empty:
        df_cliente = df_raw if st.session_state.cliente == "IGO_LOGISTICA" else df_raw[df_raw['TOMADOR'] == st.session_state.cliente].copy()
        hoje_br = datetime.now(FUSO_BR).date()
        
        if not df_cliente.empty:
            if 'FOTO' in df_cliente.columns:
                df_cliente['FOTO_URL'] = df_cliente['FOTO'].apply(lambda x: f"https://www.appsheet.com/template/gettablefileurl?appName=APPIGOLOGISTICA-153047553&tableName=App_Tarefas&fileName={str(x).strip()}" if str(x).strip() and str(x).upper() not in ['NAN', 'NONE', ''] else "")

            def definir_status_real(row):
                s_db = str(row.get('STATUS', '')).strip().upper()
                s_app = str(row.get('APP_STATUS', '')).strip().upper()
                def peso(st):
                    if any(x in st for x in ['ENTREGUE', 'FRUSTRAD', 'CANCELAD']): return 5
                    if any(x in st for x in ['ROTA', 'ENTREGA']): return 4
                    if any(x in st for x in ['CONFERIDO', 'TRIAGEM']): return 3
                    if 'COLETADO' in st: return 2
                    if 'PENDENTE' in st: return 1
                    return 0
                return s_app if peso(s_app) >= peso(s_db) else s_db
                
            df_cliente['STATUS_REAL'] = df_cliente.apply(definir_status_real, axis=1)

            def processar_detalhes(row):
                s = str(row.get('STATUS_REAL', '')).upper()
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

            def tratar_status(row):
                s = str(row.get('STATUS_REAL', '')).strip().upper()
                previsao = str(row.get('DATA_LIMITE', '')).strip()
                
                if 'ENTREGUE' in s: res = '✅ Entregue'
                elif any(x in s for x in ['ROTA', 'ENTREGA']): res = '🚚 Em Rota'
                elif 'CONFERIDO' in s: res = '☑️ Conferido'
                elif 'TRIAGEM' in s: res = '⚙️ Triagem'
                elif 'COLETADO' in s: res = '📦 Coletado'
                elif 'FRUSTRADA' in s: res = '❌ Frustrada'
                elif 'CANCELADO' in s: res = '🚫 Cancelado'
                else: res = '⏳ Pendente'
                
                if res not in ['✅ Entregue', '🚫 Cancelado', '❌ Frustrada'] and previsao:
                    try:
                        if datetime.strptime(previsao, "%d/%m/%Y").date() < hoje_br: res = f"🚨 ATRASADO ({res})"
                    except: pass
                return res
            
            df_cliente['STATUS_DISPLAY'] = df_cliente.apply(tratar_status, axis=1)

            ordem_padrao = ['PEDIDO', 'DATA', 'STATUS', 'LABORATORIO', 'CIDADE', 'UF', 'BAIRRO', 'DATA_LIMITE', 'DATA_ENTREGA', 'FOTO_URL', 'DETALHES']
            colunas_disponiveis = [c for c in ordem_padrao if c in df_cliente.columns]
            
            min_data = df_cliente['DATA_OBJ'].dropna().min() if ('DATA_OBJ' in df_cliente.columns and not df_cliente['DATA_OBJ'].dropna().empty) else hoje_br
            max_data = df_cliente['DATA_OBJ'].dropna().max() if ('DATA_OBJ' in df_cliente.columns and not df_cliente['DATA_OBJ'].dropna().empty) else hoje_br
            
            # --- ⚙️ SIDEBAR COM TOGGLE DE DARK MODE ---
            with st.sidebar:
                st.image(CLIENTES_CONFIG[st.session_state.cliente]["logo"], width=160)
                st.divider()
                
                modo_escuro = st.toggle("🌙 Modo Escuro", value=False)
                st.divider()
                
                datas_sel = st.date_input("🗓️ Período:", value=(min_data, max_data), min_value=min_data, max_value=max_data, format="DD/MM/YYYY")
                cidades_sel = st.multiselect("📍 Cidades:", options=sorted(df_cliente['CIDADE'].dropna().unique().tolist()))
                busca_ped = st.text_input("🔍 Pedido / Nº:")
                
                with st.popover("⚙️ Personalizar Colunas", use_container_width=True):
                    col_vis = st.multiselect("Ver:", options=colunas_disponiveis, default=colunas_disponiveis)
                
                st.divider()
                df_f_export = df_cliente.copy()
                csv_data = df_f_export[col_vis].to_csv(index=False, sep=";").encode('utf-8-sig')
                st.download_button(label="📥 Exportar Excel", data=csv_data, file_name=f"Monitoramento_{st.session_state.cliente}.csv", mime="text/csv", use_container_width=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🚪 Sair", use_container_width=True):
                    st.session_state.logado = False
                    st.rerun()

            # --- INJEÇÃO DE CSS DINÂMICO (DARK MODE) ---
            bg_app = "#0e1117" if modo_escuro else "#f0f2f6"
            txt_main = "#f8fafc" if modo_escuro else "#0f172a"
            border_c = "#334155" if modo_escuro else "#e2e8f0"
            
            st.markdown(f"""
            <style>
            [data-testid="stAppViewContainer"] {{ background-color: {bg_app} !important; }}
            .dinamic-text {{ color: {txt_main} !important; }}
            .dinamic-border {{ border-bottom: 2px solid {border_c} !important; }}
            </style>
            """, unsafe_allow_html=True)

            # --- FILTROS BASE ---
            df_f = df_cliente.copy()
            if isinstance(datas_sel, tuple):
                if len(datas_sel) == 2: df_f = df_f[(df_f['DATA_OBJ'] >= datas_sel[0]) & (df_f['DATA_OBJ'] <= datas_sel[1])]
                elif len(datas_sel) == 1: df_f = df_f[df_f['DATA_OBJ'] == datas_sel[0]]
            else:
                df_f = df_f[df_f['DATA_OBJ'] == datas_sel]

            if cidades_sel: df_f = df_f[df_f['CIDADE'].isin(cidades_sel)]
            if busca_ped:
                b = str(busca_ped).upper()
                df_f = df_f[df_f['PEDIDO'].astype(str).str.contains(b) | df_f['NUMERO'].astype(str).str.contains(b)]

            # --- ORDENAÇÃO DE PRIORIDADE ---
            if not df_f.empty:
                def calcular_prioridade(row):
                    score = 0
                    if row.get('DATA_OBJ') != hoje_br: score += 1000 
                    status_str = str(row.get('STATUS_DISPLAY', ''))
                    if 'Pendente' not in status_str and '⏳' not in status_str: score += 100
                    return score

                df_f['PRIORIDADE_TELA'] = df_f.apply(calcular_prioridade, axis=1)
                df_f['INDEX_ORIGINAL'] = df_f.index
                df_f = df_f.sort_values(by=['PRIORIDADE_TELA', 'INDEX_ORIGINAL'])

            st.markdown(f"""
            <div class="header-container dinamic-border" style="padding-bottom: 10px; margin-top: -15px;">
                <h2 class="dinamic-text" style="margin: 0; font-weight: 900; font-size: 22px; letter-spacing: -0.5px;">Monitoramento {st.session_state.cliente}</h2>
                <div class='sync-status'>🟢 Sincronizado {datetime.now(FUSO_BR).strftime('%H:%M')}</div>
            </div>
            """, unsafe_allow_html=True)

            n_tot = len(df_f)
            n_ent = len(df_f[df_f['STATUS_DISPLAY'].str.contains('Entregue', na=False)]) if not df_f.empty else 0
            n_frus = len(df_f[df_f['STATUS_DISPLAY'].str.contains('Frustrada', na=False)]) if not df_f.empty else 0
            n_atra = len(df_f[df_f['STATUS_DISPLAY'].str.contains('ATRASADO', na=False)]) if not df_f.empty else 0
            n_hoje = len(df_f[df_f['DATA_OBJ'] == hoje_br]) if not df_f.empty else 0

            c1, c2, c3, c4, c5 = st.columns(5)
            def click_kpi(valor): st.session_state.filtro_kpi = valor

            with c1: st.button(f"📦 TOTAL\n\n{n_tot}", key="kpi_total", use_container_width=True, on_click=click_kpi, args=("TODOS",))
            with c2: st.button(f"✅ ENTREGUES\n\n{n_ent}", key="kpi_entregue", use_container_width=True, on_click=click_kpi, args=("ENTREGUE",))
            with c3: st.button(f"❌ FRUSTRADAS\n\n{n_frus}", key="kpi_frus", use_container_width=True, on_click=click_kpi, args=("FRUSTRADA",))
            with c4: st.button(f"🚨 ATRASADOS\n\n{n_atra}", key="kpi_atra", use_container_width=True, on_click=click_kpi, args=("ATRASADO",))
            with c5: st.button(f"📅 HOJE\n\n{n_hoje}", key="kpi_hoje", use_container_width=True, on_click=click_kpi, args=("HOJE",))

            df_grid = df_f.copy()
            if not df_grid.empty:
                if st.session_state.filtro_kpi == "ENTREGUE":
                    df_grid = df_grid[df_grid['STATUS_DISPLAY'].str.contains('Entregue', na=False)]
                    st.info("🎯 Exibindo apenas **Pedidos Entregues**. Clique no botão azul (TOTAL) para limpar.")
                elif st.session_state.filtro_kpi == "FRUSTRADA":
                    df_grid = df_grid[df_grid['STATUS_DISPLAY'].str.contains('Frustrada', na=False)]
                    st.info("🎯 Exibindo apenas **Coletas Frustradas**. Clique no botão azul (TOTAL) para limpar.")
                elif st.session_state.filtro_kpi == "ATRASADO":
                    df_grid = df_grid[df_grid['STATUS_DISPLAY'].str.contains('ATRASADO', na=False)]
                    st.warning("🚨 Exibindo apenas **Pedidos Atrasados**. Clique no botão azul (TOTAL) para limpar.")
                elif st.session_state.filtro_kpi == "HOJE":
                    df_grid = df_grid[df_grid['DATA_OBJ'] == hoje_br]
                    st.success("📅 Exibindo apenas **Pedidos de Hoje**. Clique no botão azul (TOTAL) para limpar.")

                df_grid['STATUS'] = df_grid['STATUS_DISPLAY'] 
                df_final = df_grid[[c for c in col_vis if c in df_grid.columns]]

                gb = GridOptionsBuilder.from_dataframe(df_final)
                gb.configure_default_column(resizable=True, sortable=True, minWidth=100)
                gb.configure_selection('single', use_checkbox=False)
                
                for col in df_final.columns:
                    header_name = col.upper()
                    if col == 'DATA_LIMITE': header_name = "PREVISÃO ENTREGA"
                    elif col == 'DATA_ENTREGA': header_name = "DATA ENTREGA"
                    elif col == 'FOTO_URL': header_name = "FOTO"
                    
                    if col == 'FOTO_URL':
                        link_jscode = JsCode("""
                        class LinkCellRenderer { 
                            init(params) { 
                                this.eGui = document.createElement('div'); 
                                this.eGui.style.textAlign = 'center'; 
                                if (params.value && params.value !== '' && params.value !== 'nan') { 
                                    this.eGui.innerHTML = '<span style="cursor: pointer; font-size: 18px; display: block; margin-top: 2px;" title="Clique para ver a foto">📸</span>'; 
                                    this.eGui.onclick = () => {
                                        let modal = document.createElement('div');
                                        modal.style.position = 'fixed';
                                        modal.style.zIndex = '999999';
                                        modal.style.left = '0';
                                        modal.style.top = '0';
                                        modal.style.width = '100vw';
                                        modal.style.height = '100vh';
                                        modal.style.backgroundColor = 'rgba(0,0,0,0.85)';
                                        modal.style.display = 'flex';
                                        modal.style.flexDirection = 'column';
                                        modal.style.justifyContent = 'center';
                                        modal.style.alignItems = 'center';
                                        modal.style.cursor = 'zoom-out';
                                        
                                        let img = document.createElement('img');
                                        img.src = params.value;
                                        img.style.maxWidth = '90%';
                                        img.style.maxHeight = '85%';
                                        img.style.borderRadius = '8px';
                                        img.style.boxShadow = '0 4px 20px rgba(0,0,0,0.5)';
                                        
                                        let txt = document.createElement('div');
                                        txt.innerText = '✖ Clique em qualquer lugar para fechar';
                                        txt.style.color = '#ffffff';
                                        txt.style.marginTop = '15px';
                                        txt.style.fontFamily = 'sans-serif';
                                        txt.style.fontSize = '14px';
                                        txt.style.fontWeight = 'bold';
                                        
                                        modal.appendChild(img);
                                        modal.appendChild(txt);
                                        
                                        modal.onclick = () => { document.body.removeChild(modal); };
                                        document.body.appendChild(modal);
                                    };
                                } 
                            } 
                            getGui() { return this.eGui; } 
                        }
                        """)
                        gb.configure_column(col, headerName=header_name, cellRenderer=link_jscode, width=70, minWidth=70)
                    elif col == 'DETALHES':
                        gb.configure_column(col, headerName=header_name, width=300, minWidth=250, tooltipField="DETALHES")
                    elif col == 'UF': 
                        gb.configure_column(col, headerName=header_name, width=60, minWidth=60)
                    elif col == 'DATA': 
                        gb.configure_column(col, headerName=header_name, width=90, minWidth=90)
                    elif col == 'PEDIDO': 
                        gb.configure_column(col, headerName=header_name, width=95, minWidth=95)
                    elif col == 'LABORATORIO': 
                        gb.configure_column(col, headerName=header_name, width=400, minWidth=350, tooltipField="LABORATORIO")
                    elif col == 'BAIRRO': 
                        gb.configure_column(col, headerName=header_name, width=250, minWidth=200, tooltipField="BAIRRO")
                    elif col == 'CIDADE': 
                        gb.configure_column(col, headerName=header_name, width=180, minWidth=150)
                    else: 
                        gb.configure_column(col, headerName=header_name)

                # =======================================================
                # 🦇 CSS DINÂMICO PARA A GRID (MODO CLARO vs ESCURO)
                # =======================================================
                if modo_escuro:
                    grid_css = {
                        ".ag-root-wrapper": {"background-color": "#0e1117 !important", "border": "none !important"},
                        ".ag-header": {"background-color": "#1e293b !important", "border-bottom": "1px solid #334155 !important"},
                        ".ag-header-cell-text": {"font-size": "11px !important", "font-weight": "bold", "color": "#f8fafc !important"},
                        ".ag-cell": {"font-size": "11px !important", "color": "#cbd5e1 !important", "border-bottom": "1px solid #1e293b !important"},
                        ".ag-row-even": {"background-color": "#0f172a !important"}, 
                        ".ag-row-odd": {"background-color": "#1e293b !important"},  
                        ".ag-row-hover": {"background-color": "#334155 !important"} 
                    }
                else:
                    grid_css = {
                        ".ag-header-cell-text": {"font-size": "11px !important", "font-weight": "bold", "color": "#334155"},
                        ".ag-cell": {"font-size": "11px !important", "color": "#475569"},
                        ".ag-row-even": {"background-color": "#f8fafc !important"}, 
                        ".ag-row-odd": {"background-color": "#ffffff !important"},  
                        ".ag-row-hover": {"background-color": "#e2e8f0 !important"} 
                    }

                AgGrid(df_final, gridOptions=gb.build(), allow_unsafe_jscode=True, theme='alpine', custom_css=grid_css, fit_columns_on_grid_load=False, height=520)
            else:
                st.warning("Nenhum pedido encontrado com esses filtros.")
