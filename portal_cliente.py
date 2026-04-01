import streamlit as st
import pandas as pd
import gspread
import os
import urllib.parse
from datetime import datetime, timedelta, timezone
from streamlit_autorefresh import st_autorefresh
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

# =======================================================
# ⚙️ CONFIGURAÇÕES TÉCNICAS E FUSO
# =======================================================
FUSO_BR = timezone(timedelta(hours=-3))
LOGO_IGO = "https://i.postimg.cc/d71mqWDx/IGO-LOGO.png"

# =======================================================
# 🎨 1. CONFIGURAÇÃO DA PÁGINA E CSS (RESTALRADO INTEGRAL)
# =======================================================
st.set_page_config(page_title="Monitoramento IGO Logística", layout="wide", page_icon="🚚", initial_sidebar_state="expanded")
st_autorefresh(interval=60000, limit=None, key="refresh_timer")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');
    
    [data-testid="stAppViewContainer"] { transition: background-color 0.3s ease; font-family: 'Inter', sans-serif; }
    [data-testid="stSidebar"] { transition: background-color 0.3s ease; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {background-color: transparent !important;}
    
    .block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; padding-left: 2rem !important; padding-right: 2rem !important; }
    
    /* ESTILIZAÇÃO DOS KPIs - GRADIENTES ORIGINAIS */
    div.st-key-kpi_total button, div.st-key-kpi_entregue button, div.st-key-kpi_frus button, div.st-key-kpi_atra button, div.st-key-kpi_hoje button {
        height: 75px !important; border-radius: 10px !important; border: none !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important; transition: all 0.2s ease !important;
        display: flex !important; justify-content: center !important; align-items: center !important;
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
        white-space: pre-wrap !important; text-align: center !important;
    }
    
    .header-container { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 15px; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px; }
    .sync-status { font-size: 12px; color: #10B981; font-weight: 700; }
    
    /* Ajustes para Inputs */
    .stTextInput > div > div > input { font-size: 16px !important; padding: 10px !important; border-radius: 8px !important; }
    </style>
    """, unsafe_allow_html=True)

# 🔐 DICIONÁRIO DE ACESSOS (VINCULADO AO TOMADOR DA PLANILHA)
CLIENTES_CONFIG = {
    "GRALAB": {
        "senha": "123", 
        "logo": "https://cdn.awsli.com.br/2702/2702264/logo/gralab-rbuogsxve7.png", 
        "tomador_planilha": "GRALAB"
    },
    "IGO_LOGISTICA": {
        "senha": "admin", 
        "logo": LOGO_IGO, 
        "tomador_planilha": "TODOS"
    },
    "LOGISTICA.LABEST": {
        "senha": "123", 
        "logo": "https://i.postimg.cc/mD8P8pGZ/LABEST-LOGO.png", 
        "tomador_planilha": "LABEST"
    }
}

# =======================================================
# 🔗 3. MOTOR DE DADOS (LOGICA DE MERGE COMPLETA)
# =======================================================
@st.cache_resource
def conectar_banco_seguro():
    try:
        caminho_windows = os.path.join(os.path.expanduser("~"), "IGO_Logistica_Sistema")
        cred_win = os.path.join(caminho_windows, "credentials.json")
        token_win = os.path.join(caminho_windows, "token.json")
        
        if os.path.exists(cred_win) and os.path.exists(token_win):
            return gspread.oauth(credentials_filename=cred_win, authorized_user_filename=token_win)
        elif "google_cred_json" in st.secrets and "google_token_json" in st.secrets:
            with open("cred_temp.json", "w", encoding="utf-8") as f:
                f.write(st.secrets["google_cred_json"])
            with open("token_temp.json", "w", encoding="utf-8") as f:
                f.write(st.secrets["google_token_json"])
            return gspread.oauth(credentials_filename="cred_temp.json", authorized_user_filename="token_temp.json")
        return None
    except Exception as e:
        st.error(f"Erro de Conexão: {e}")
        return None

@st.cache_data(ttl=30)
def carregar_dados_nuvem():
    try:
        gc = conectar_banco_seguro()
        if not gc: return pd.DataFrame()
            
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
                    
                    col_status = 'STATUS' if 'STATUS' in cols_limpas else None
                    col_obs = 'OBSERVACOES' if 'OBSERVACOES' in cols_limpas else (cols_limpas[10] if len(cols_limpas) > 10 else None)
                    col_detalhes = 'DETALHES' if 'DETALHES' in cols_limpas else (cols_limpas[14] if len(cols_limpas) > 14 else None)
                    col_receb = 'RECEBEDOR' if 'RECEBEDOR' in cols_limpas else (cols_limpas[16] if len(cols_limpas) > 16 else None)
                    col_foto = 'FOTO' if 'FOTO' in cols_limpas else ('IMAGEM' if 'IMAGEM' in cols_limpas else None)
                    
                    cols_ext = ['PEDIDO']
                    if col_status: cols_ext.append(col_status)
                    if col_obs: cols_ext.append(col_obs)
                    if col_detalhes: cols_ext.append(col_detalhes)
                    if col_receb: cols_ext.append(col_receb)
                    if col_foto: cols_ext.append(col_foto)
                    
                    df_app_clean = df_app[cols_ext].copy()
                    
                    def extrair_dados_app(r):
                        s = str(r.get(col_status, '')).strip() if col_status else ''
                        o = str(r.get(col_obs, '')).strip() if col_obs else ''
                        d = str(r.get(col_detalhes, '')).strip() if col_detalhes else ''
                        rec = str(r.get(col_receb, '')).strip() if col_receb else ''
                        f = str(r.get(col_foto, '')).strip() if col_foto else ''
                        
                        s = s if s.upper() != 'NAN' else ''
                        o = o if o.upper() != 'NAN' else ''
                        f = f if f.upper() != 'NAN' else ''
                        quem = d if (d and d.upper() != 'NAN') else rec
                        return pd.Series([s, o, quem, f])
                        
                    df_app_clean[['APP_STATUS', 'APP_OBS', 'APP_QUEM', 'APP_FOTO']] = df_app_clean.apply(extrair_dados_app, axis=1)
                    df_app_clean = df_app_clean[['PEDIDO', 'APP_STATUS', 'APP_OBS', 'APP_QUEM', 'APP_FOTO']]
                    df_app_clean['PEDIDO'] = df_app_clean['PEDIDO'].astype(str).str.strip()
                    df_app_clean.drop_duplicates(subset=['PEDIDO'], keep='last', inplace=True)
                    
                    # Merge Inteligente (Individual e Romaneio)
                    df['PEDIDO'] = df['PEDIDO'].astype(str).str.strip()
                    if 'ROMANEIO' not in df.columns: df['ROMANEIO'] = ""
                    df['ROMANEIO'] = df['ROMANEIO'].astype(str).str.strip()
                    
                    df = pd.merge(df, df_app_clean, on='PEDIDO', how='left')
                    
                    # Merge por Romaneio
                    df_rom = df_app_clean[df_app_clean['PEDIDO'].str.startswith('ROM-', na=False)].copy()
                    if not df_rom.empty:
                        df_rom.rename(columns={'PEDIDO': 'ROMANEIO'}, inplace=True)
                        df = pd.merge(df, df_rom, on='ROMANEIO', how='left', suffixes=('', '_R'))
                        for c in ['APP_STATUS', 'APP_QUEM', 'APP_OBS', 'APP_FOTO']:
                            if f"{c}_R" in df.columns:
                                df[c] = df[f"{c}_R"].replace("", pd.NA).combine_first(df[c].replace("", pd.NA)).fillna("")
                    
                    if 'APP_FOTO' in df.columns:
                        if 'FOTO' not in df.columns: df['FOTO'] = df['APP_FOTO']
                        else: df['FOTO'] = df['APP_FOTO'].replace("", pd.NA).combine_first(df['FOTO'].replace("", pd.NA)).fillna("")
            except: pass
            
            if 'DATA' in df.columns: 
                df['DATA_OBJ'] = pd.to_datetime(df['DATA'], format='%d/%m/%Y', errors='coerce').dt.date
            return df
    except Exception as e:
        st.error(f"Sincronização offline: {e}")
    return pd.DataFrame()

# =======================================================
# 🔐 4. LOGIN E GESTÃO DE ESTADO
# =======================================================
if 'logado' not in st.session_state: st.session_state.logado = False
if 'cliente' not in st.session_state: st.session_state.cliente = None
if 'filtro_kpi' not in st.session_state: st.session_state.filtro_kpi = "TODOS"

if not st.session_state.logado:
    st.markdown("""<style> [data-testid="stAppViewContainer"] { background-color: #f8fafc !important; } </style>""", unsafe_allow_html=True)
    _, col_login, _ = st.columns([1, 1.2, 1])
    with col_login:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown(f"<div style='text-align:center'><img src='{LOGO_IGO}' width='110'><h3>Central de Comando</h3></div>", unsafe_allow_html=True)
            u = st.text_input("👤 Usuário").upper().strip()
            s = st.text_input("🔒 Senha", type="password")
            if st.button("🚀 Acessar Sistema", use_container_width=True, type="primary"):
                if u in CLIENTES_CONFIG and s == CLIENTES_CONFIG[u]["senha"]:
                    st.session_state.logado = True
                    st.session_state.cliente = u
                    st.rerun()
                else: st.error("Acesso Negado")
else:
    # =======================================================
    # 🚀 5. DASHBOARD FINAL (VINCULADO AO TOMADOR)
    # =======================================================
    df_raw = carregar_dados_nuvem()
    cliente_info = CLIENTES_CONFIG[st.session_state.cliente]
    
    if not df_raw.empty:
        # LÓGICA DE FILTRO POR TOMADOR (VIRADA DE CHAVE)
        if cliente_info["tomador_planilha"] == "TODOS":
            df_cliente = df_raw.copy()
        else:
            # Filtra na planilha o TOMADOR que corresponde à configuração do login
            df_cliente = df_raw[df_raw['TOMADOR'].str.upper().str.strip() == cliente_info["tomador_planilha"]].copy()

        hoje_br = datetime.now(FUSO_BR).date()
        
        if not df_cliente.empty:
            # Processamento de Status Display e Fotos
            def definir_status_display(row):
                s = str(row.get('APP_STATUS', row.get('STATUS', ''))).strip().upper()
                previsao = str(row.get('DATA_LIMITE', '')).strip()
                if 'ENTREGUE' in s: res = '✅ Entregue'
                elif any(x in s for x in ['ROTA', 'ENTREGA']): res = '🚚 Em Rota'
                elif 'CONFERIDO' in s: res = '☑️ Conferido'
                elif 'TRIAGEM' in s: res = '⚙️ Triagem'
                elif 'COLETADO' in s: res = '📦 Coletado'
                elif 'FRUSTRADA' in s: res = '❌ Frustrada'
                elif 'CANCELADO' in s: res = '🚫 Cancelado'
                else: res = '⏳ Pendente'
                
                if res not in ['✅ Entregue', '❌ Frustrada', '🚫 Cancelado'] and previsao:
                    try:
                        if datetime.strptime(previsao, "%d/%m/%Y").date() < hoje_br:
                            res = f"🚨 ATRASADO ({res})"
                    except: pass
                return res

            df_cliente['STATUS_DISPLAY'] = df_cliente.apply(definir_status_display, axis=1)
            
            if 'FOTO' in df_cliente.columns:
                df_cliente['FOTO_URL'] = df_cliente['FOTO'].apply(lambda x: f"https://www.appsheet.com/template/gettablefileurl?appName=APPIGOLOGISTICA-153047553&tableName=App_Tarefas&fileName={str(x).strip()}" if x and str(x).upper() != 'NAN' else "")

            # --- SIDEBAR ---
            with st.sidebar:
                st.image(cliente_info["logo"], width=160)
                st.divider()
                modo_escuro = st.toggle("🌙 Modo Noturno", value=False)
                st.divider()
                datas = st.date_input("🗓️ Período:", value=(hoje_br - timedelta(days=7), hoje_br), format="DD/MM/YYYY")
                cidades = st.multiselect("📍 Cidades:", options=sorted(df_cliente['CIDADE'].dropna().unique().tolist()))
                st.divider()
                if st.button("🚪 Sair do Sistema", use_container_width=True):
                    st.session_state.logado = False
                    st.rerun()

            # Aplicação dos Filtros de Sidebar
            df_f = df_cliente.copy()
            if isinstance(datas, tuple) and len(datas) == 2:
                df_f = df_f[(df_f['DATA_OBJ'] >= datas[0]) & (df_f['DATA_OBJ'] <= datas[1])]
            if cidades:
                df_f = df_f[df_f['CIDADE'].isin(cidades)]

            # --- KPIs ---
            n_tot = len(df_f)
            n_ent = len(df_f[df_f['STATUS_DISPLAY'].str.contains('Entregue', na=False)])
            n_fru = len(df_f[df_f['STATUS_DISPLAY'].str.contains('Frustrada', na=False)])
            n_atr = len(df_f[df_f['STATUS_DISPLAY'].str.contains('ATRASADO', na=False)])
            n_hoj = len(df_f[df_f['DATA_OBJ'] == hoje_br])

            # --- HEADER DINÂMICO ---
            bg_v = "#0e1117" if modo_escuro else "#f0f2f6"
            txt_v = "#f8fafc" if modo_escuro else "#0f172a"
            st.markdown(f"""
            <style> [data-testid="stAppViewContainer"] {{ background-color: {bg_v} !important; }} .header-text {{ color: {txt_v} !important; }} </style>
            <div class="header-container">
                <div style="display: flex; align-items: center; gap: 15px;">
                    <img src="{cliente_info['logo']}" height="50" style="border-radius: 8px;">
                    <h2 class="header-text" style="margin: 0; font-weight: 900;">Monitoramento {st.session_state.cliente}</h2>
                </div>
                <div class='sync-status'>🟢 Online {datetime.now(FUSO_BR).strftime('%H:%M')}</div>
            </div>
            """, unsafe_allow_html=True)

            c_kpi = st.columns(5)
            def set_kpi(v): st.session_state.filtro_kpi = v
            with c_kpi[0]: st.button(f"📦 TOTAL\n\n{n_tot}", key="kpi_total", use_container_width=True, on_click=set_kpi, args=("TODOS",))
            with c_kpi[1]: st.button(f"✅ ENTREGUES\n\n{n_ent}", key="kpi_entregue", use_container_width=True, on_click=set_kpi, args=("ENTREGUE",))
            with c_kpi[2]: st.button(f"❌ FRUSTRADAS\n\n{n_fru}", key="kpi_frus", use_container_width=True, on_click=set_kpi, args=("FRUSTRADA",))
            with c_kpi[3]: st.button(f"🚨 ATRASADOS\n\n{n_atr}", key="kpi_atra", use_container_width=True, on_click=set_kpi, args=("ATRASADO",))
            with c_kpi[4]: st.button(f"📅 HOJE\n\n{n_hoj}", key="kpi_hoje", use_container_width=True, on_click=set_kpi, args=("HOJE",))

            # --- BUSCA E GRID ---
            busca = st.text_input("🔎 Busca Rápida:", placeholder="Pedido, laboratório, cidade...")
            df_grid = df_f.copy()
            
            f_kpi = st.session_state.filtro_kpi
            if f_kpi == "ENTREGUE": df_grid = df_grid[df_grid['STATUS_DISPLAY'].str.contains('Entregue', na=False)]
            elif f_kpi == "FRUSTRADA": df_grid = df_grid[df_grid['STATUS_DISPLAY'].str.contains('Frustrada', na=False)]
            elif f_kpi == "ATRASADO": df_grid = df_grid[df_grid['STATUS_DISPLAY'].str.contains('ATRASADO', na=False)]
            elif f_kpi == "HOJE": df_grid = df_grid[df_grid['DATA_OBJ'] == hoje_br]
            
            if busca:
                mask = df_grid.astype(str).apply(lambda x: x.str.lower().str.contains(busca.lower())).any(axis=1)
                df_grid = df_grid[mask]

            if not df_grid.empty:
                df_grid['STATUS'] = df_grid['STATUS_DISPLAY']
                cols_v = ['DATA', 'PEDIDO', 'STATUS', 'LABORATORIO', 'CIDADE', 'UF', 'FOTO_URL']
                df_final = df_grid[[c for c in cols_v if c in df_grid.columns]]
                
                gb = GridOptionsBuilder.from_dataframe(df_final)
                gb.configure_default_column(resizable=True, sortable=True)
                
                # JS Renderer para Modal de Foto
                foto_js = JsCode("""
                class FotoRenderer {
                    init(params) {
                        this.eGui = document.createElement('div');
                        this.eGui.style.textAlign = 'center';
                        if (params.value && params.value.includes('http')) {
                            let btn = document.createElement('span');
                            btn.innerHTML = '📸'; btn.style.cursor = 'pointer';
                            btn.onclick = () => {
                                let m = document.createElement('div');
                                Object.assign(m.style, {position:'fixed', zIndex:'99999', left:0, top:0, width:'100vw', height:'100vh', backgroundColor:'rgba(0,0,0,0.9)', display:'flex', justifyContent:'center', alignItems:'center', cursor:'zoom-out'});
                                let i = document.createElement('img'); i.src = params.value; i.style.maxHeight='90%'; i.style.borderRadius='8px';
                                m.appendChild(i); m.onclick = () => document.body.removeChild(m);
                                document.body.appendChild(m);
                            };
                            this.eGui.appendChild(btn);
                        } else { this.eGui.innerHTML = '➖'; }
                    }
                    getGui() { return this.eGui; }
                }
                """)
                
                gb.configure_column("FOTO_URL", headerName="FOTO", cellRenderer=foto_js, width=80)
                AgGrid(df_final, gridOptions=gb.build(), allow_unsafe_jscode=True, theme='alpine', height=550)
            else:
                st.info("Nenhum pedido encontrado.")
