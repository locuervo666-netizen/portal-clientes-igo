import streamlit as st
import pandas as pd
import gspread
import os
import urllib.parse
from datetime import datetime, timedelta, timezone
from streamlit_autorefresh import st_autorefresh
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

FUSO_BR = timezone(timedelta(hours=-3))

# 🎯 ATENÇÃO ROBSON: Cole o "Link direto" do Postimages dentro das aspas abaixo!
LOGO_IGO = "https://i.postimg.cc/d71mqWDx/IGO-LOGO.png"

# =======================================================
# 🎨 1. CONFIGURAÇÃO DA PÁGINA E CSS BASE
# =======================================================
st.set_page_config(page_title="Monitoramento IGO Logística", layout="wide", page_icon="🚚", initial_sidebar_state="expanded" )
st_autorefresh(interval=60000, limit=None, key="refresh_timer")

st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { transition: background-color 0.3s ease; font-family: 'Inter', sans-serif; }
    [data-testid="stSidebar"] { transition: background-color 0.3s ease; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {background-color: transparent !important;}
    .block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; padding-left: 2rem !important; padding-right: 2rem !important; }
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
    }
    .header-container { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 15px; }
    .sync-status { font-size: 12px; color: #10B981; font-weight: 700; }
    button[data-baseweb="tab"] { font-size: 16px !important; font-weight: 700 !important; }
    </style>
    """, unsafe_allow_html=True)

CLIENTES_CONFIG = {
    "GRALAB": {"senha": "123", "logo": "https://cdn.awsli.com.br/2702/2702264/logo/gralab-rbuogsxve7.png"},
    "IGO_LOGISTICA": {"senha": "admin", "logo": LOGO_IGO}
}

# =======================================================
# 🔗 MOTOR DE DADOS PRINCIPAL
# =======================================================
@st.cache_resource
def conectar_banco_seguro( ):
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
        else:
            st.error("❌ Cofre do Streamlit vazio. Cole as variáveis google_cred_json e google_token_json no Secrets.")
            return None
    except Exception as e:
        st.error(f"Erro de Conexão com o Google: {e}")
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
                    if col_status and col_status not in cols_ext: cols_ext.append(col_status)
                    if col_obs and col_obs not in cols_ext: cols_ext.append(col_obs)
                    if col_detalhes and col_detalhes not in cols_ext: cols_ext.append(col_detalhes)
                    if col_receb and col_receb not in cols_ext: cols_ext.append(col_receb)
                    if col_foto and col_foto not in cols_ext: cols_ext.append(col_foto)
                    df_app_clean = df_app[cols_ext].copy()
                    def extrair_dados_app(r):
                        s = str(r.get(col_status, '')) if col_status else ''
                        o = str(r.get(col_obs, '')) if col_obs else ''
                        d = str(r.get(col_detalhes, '')) if col_detalhes else ''
                        rec = str(r.get(col_receb, '')) if col_receb else ''
                        f = str(r.get(col_foto, '')) if col_foto else ''
                        s, o, d, rec, f = [str(x).strip() if str(x).upper() != 'NAN' else '' for x in [s, o, d, rec, f]]
                        q = d if d else rec
                        return pd.Series([s, o, q, f])
                    df_app_clean[['APP_STATUS', 'APP_OBS', 'APP_QUEM', 'APP_FOTO']] = df_app_clean.apply(extrair_dados_app, axis=1)
                    df_app_clean = df_app_clean[['PEDIDO', 'APP_STATUS', 'APP_OBS', 'APP_QUEM', 'APP_FOTO']]
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
                        for c in ['APP_STATUS', 'APP_QUEM', 'APP_OBS', 'APP_FOTO']:
                            if c in df.columns and f"{c}_R" in df.columns:
                                df[c] = df[f"{c}_R"].replace("", pd.NA).combine_first(df[c].replace("", pd.NA)).fillna("")
                    if 'APP_FOTO' in df.columns:
                        if 'FOTO' not in df.columns: df['FOTO'] = df['APP_FOTO']
                        else: df['FOTO'] = df['APP_FOTO'].replace("", pd.NA).combine_first(df['FOTO'].replace("", pd.NA)).fillna("")
            except Exception as e:
                st.warning(f"Aba App_Tarefas não integrada: {e}")
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame()

# =======================================================
# 🚀 LÓGICA DE LOGIN E INTERFACE
# =======================================================
if 'logado' not in st.session_state: st.session_state.logado = False
if 'cliente' not in st.session_state: st.session_state.cliente = None
if 'filtro_kpi' not in st.session_state: st.session_state.filtro_kpi = "TODOS"

hoje_br = datetime.now(FUSO_BR).date()

if not st.session_state.logado:
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        st.markdown("  
  
", unsafe_allow_html=True)
        st.image(LOGO_IGO, width=220)
        st.markdown("<h2 style='text-align: center;'>Painel do Cliente</h2>", unsafe_allow_html=True)
        cliente_input = st.selectbox("Selecione seu acesso:", ["", "GRALAB", "IGO_LOGISTICA"])
        senha_input = st.text_input("Senha de acesso:", type="password")
        if st.button("Entrar no Sistema", use_container_width=True):
            if cliente_input in CLIENTES_CONFIG and senha_input == CLIENTES_CONFIG[cliente_input]["senha"]:
                st.session_state.logado = True
                st.session_state.cliente = cliente_input
                st.rerun()
            else:
                st.error("❌ Acesso negado. Verifique as credenciais.")
else:
    df_raw = carregar_dados_nuvem()
    if df_raw.empty:
        st.warning("⚠️ Aguardando dados da planilha...")
    else:
        df_cliente = df_raw[df_raw['LABORATORIO'].str.contains(st.session_state.cliente, na=False, case=False)].copy() if st.session_state.cliente != "IGO_LOGISTICA" else df_raw.copy()
        if df_cliente.empty:
            st.info(f"Nenhum dado encontrado para {st.session_state.cliente}.")
        else:
            if 'DATA' in df_cliente.columns:
                df_cliente['DATA_OBJ'] = pd.to_datetime(df_cliente['DATA'], format='%d/%m/%Y', errors='coerce').dt.date
            
            def tratar_status(row):
                s, previsao = str(row.get('STATUS_REAL', '')).strip().upper(), str(row.get('DATA_LIMITE', '')).strip()
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
            ordem_padrao = ['DATA', 'PEDIDO', 'STATUS', 'LABORATORIO', 'CIDADE', 'UF', 'BAIRRO', 'DATA_LIMITE', 'DATA_ENTREGA', 'FOTO_URL', 'DETALHES']
            col_vis = [c for c in ordem_padrao if c in df_cliente.columns]
            
            with st.sidebar:
                st.image(CLIENTES_CONFIG[st.session_state.cliente]["logo"], width=160)
                st.divider()
                modo_escuro = st.toggle("🌙 Modo Noturno", value=False)
                st.divider()
                min_d = df_cliente['DATA_OBJ'].min() if not df_cliente['DATA_OBJ'].dropna().empty else hoje_br
                max_d = df_cliente['DATA_OBJ'].max() if not df_cliente['DATA_OBJ'].dropna().empty else hoje_br
                datas_sel = st.date_input("🗓️ Período:", value=(min_d, max_d), format="DD/MM/YYYY")
                cidades_sel = st.multiselect("📍 Cidades:", options=sorted(df_cliente['CIDADE'].dropna().unique().tolist()))
                st.divider()
                if st.button("🚪 Sair do Sistema", use_container_width=True): st.session_state.logado = False; st.rerun()

            # Filtros
            df_f = df_cliente.copy()
            if isinstance(datas_sel, tuple) and len(datas_sel) == 2:
                df_f = df_f[(df_f['DATA_OBJ'] >= datas_sel[0]) & (df_f['DATA_OBJ'] <= datas_sel[1])]
            if cidades_sel: df_f = df_f[df_f['CIDADE'].isin(cidades_sel)]

            # KPIs
            n_tot = len(df_f)
            n_ent = len(df_f[df_f['STATUS_DISPLAY'].str.contains('Entregue', na=False)])
            n_frus = len(df_f[df_f['STATUS_DISPLAY'].str.contains('Frustrada', na=False)])
            n_atra = len(df_f[df_f['STATUS_DISPLAY'].str.contains('ATRASADO', na=False)])
            n_hoje = len(df_f[df_f['DATA_OBJ'] == hoje_br])

            st.markdown(f"<h2 style='margin-top: -20px;'>Monitoramento {st.session_state.cliente}</h2>", unsafe_allow_html=True)
            c1, c2, c3, c4, c5 = st.columns(5)
            def click_kpi(valor): st.session_state.filtro_kpi = valor
            with c1: st.button(f"📦 TOTAL\n{n_tot}", key="kpi_total", use_container_width=True, on_click=click_kpi, args=("TODOS",))
            with c2: st.button(f"✅ ENTREGUES\n{n_ent}", key="kpi_entregue", use_container_width=True, on_click=click_kpi, args=("ENTREGUE",))
            with c3: st.button(f"❌ FRUSTRADAS\n{n_frus}", key="kpi_frus", use_container_width=True, on_click=click_kpi, args=("FRUSTRADA",))
            with c4: st.button(f"🚨 ATRASADOS\n{n_atra}", key="kpi_atra", use_container_width=True, on_click=click_kpi, args=("ATRASADO",))
            with c5: st.button(f"📅 HOJE\n{n_hoje}", key="kpi_hoje", use_container_width=True, on_click=click_kpi, args=("HOJE",))

            # Grid
            df_grid = df_f.copy()
            if st.session_state.filtro_kpi == "ENTREGUE": df_grid = df_grid[df_grid['STATUS_DISPLAY'].str.contains('Entregue', na=False)]
            elif st.session_state.filtro_kpi == "FRUSTRADA": df_grid = df_grid[df_grid['STATUS_DISPLAY'].str.contains('Frustrada', na=False)]
            elif st.session_state.filtro_kpi == "ATRASADO": df_grid = df_grid[df_grid['STATUS_DISPLAY'].str.contains('ATRASADO', na=False)]
            elif st.session_state.filtro_kpi == "HOJE": df_grid = df_grid[df_grid['DATA_OBJ'] == hoje_br]

            if not df_grid.empty:
                gb = GridOptionsBuilder.from_dataframe(df_grid[col_vis])
                gb.configure_default_column(resizable=True, sortable=True)
                gb.configure_selection('single')
                
                # Renderizador de Foto
                link_jscode = JsCode("""
                class FotoModalRenderer {
                    init(params) {
                        this.eGui = document.createElement('div');
                        let val = params.value;
                        if (val && val.includes('http' )) {
                            this.eGui.innerHTML = '<span style="cursor:pointer;font-size:18px;">📸</span>';
                            this.eGui.onclick = () => {
                                let m = document.createElement('div');
                                m.style = 'position:fixed;z-index:9999;left:0;top:0;width:100%;height:100%;background:rgba(0,0,0,0.8);display:flex;justify-content:center;align-items:center;cursor:pointer;';
                                m.innerHTML = `<img src="${val}" style="max-width:90%;max-height:90%;border-radius:8px;"><div style="position:absolute;bottom:20px;color:white;font-weight:bold;">✖ Clique para fechar</div>`;
                                m.onclick = () => document.body.removeChild(m);
                                document.body.appendChild(m);
                            };
                        } else { this.eGui.innerHTML = '➖'; }
                    }
                    getGui() { return this.eGui; }
                }
                """)
                if 'FOTO_URL' in df_grid.columns:
                    gb.configure_column('FOTO_URL', headerName="FOTO", cellRenderer=link_jscode, width=70)
                
                AgGrid(df_grid[col_vis], gridOptions=gb.build(), allow_unsafe_jscode=True, theme='alpine', height=500)
            else:
                st.info("Nenhum pedido encontrado para os filtros selecionados.")
