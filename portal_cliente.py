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
    .stTextInput>div>div>input, .stSelectbox>div>div>div, .stDateInput>div>div>input, .stMultiSelect>div>div>div { border-radius: 6px; border: 1px solid #ced4da; font-size: 13px;}
    .kpi-card { padding: 15px 20px; border-radius: 10px; color: white; box-shadow: 0 4px 10px rgba(0,0,0,0.1); margin-bottom: 15px; display: flex; flex-direction: column; justify-content: center; }
    .kpi-title { font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; opacity: 0.9; margin-bottom: 3px; }
    .kpi-value { font-size: 28px; font-weight: 900; line-height: 1; margin: 0; }
    .bg-blue { background: linear-gradient(135deg, #1E3A8A 0%, #3B82F6 100%); }
    .bg-orange { background: linear-gradient(135deg, #9A3412 0%, #F59E0B 100%); }
    .bg-red { background: linear-gradient(135deg, #7F1D1D 0%, #EF4444 100%); }
    .bg-green { background: linear-gradient(135deg, #064E3B 0%, #10B981 100%); }
    h1 { color: #0f172a; font-weight: 900; font-size: 24px; letter-spacing: -0.5px; margin-bottom: 0px; }
    .sync-status { text-align: right; font-size: 12px; color: #10B981; font-weight: 600; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

# =======================================================
# 🏦 2. CENTRAL DE CLIENTES (CADASTRE NOVOS AQUI)
# =======================================================
CLIENTES_CONFIG = {
    "GRALAB": {
        "senha": "123",
        "logo": "https://cdn.awsli.com.br/2702/2702264/logo/gralab-rbuogsxve7.png"
    },
    "IGO_LOGISTICA": {
        "senha": "admin",
        "logo": "https://cdn-icons-png.flaticon.com/512/1532/1532692.png"
    }
}

LOGO_PADRAO = "https://cdn-icons-png.flaticon.com/512/1532/1532692.png"

# =======================================================
# 🔗 3. MOTOR DE DADOS
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

# =======================================================
# 🔐 4. TELA DE LOGIN
# =======================================================
if 'logado' not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<br><br><br><br>", unsafe_allow_html=True)
        with st.container(border=True):
            st.image(LOGO_PADRAO, width=60)
            st.markdown("<h2 style='font-size: 24px; color: #0f172a;'>Portal IGO Logística</h2>", unsafe_allow_html=True)
            usuario = st.text_input("Usuário").upper().strip()
            senha = st.text_input("Senha", type="password")
            if st.button("Entrar", type="primary", use_container_width=True):
                if usuario in CLIENTES_CONFIG and senha == CLIENTES_CONFIG[usuario]["senha"]:
                    st.session_state.logado = True
                    st.session_state.cliente = usuario
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")

# =======================================================
# 🚀 5. DASHBOARD ELITE V23 (RECONHECENDO FRUSTRADAS)
# =======================================================
else:
    df_sistema = carregar_dados_nuvem()
    if not df_sistema.empty and 'TOMADOR' in df_sistema.columns:
        if st.session_state.cliente == "IGO_LOGISTICA":
            df_cliente = df_sistema.copy()
        else:
            df_cliente = df_sistema[df_sistema['TOMADOR'] == st.session_state.cliente].copy()
        
        if not df_cliente.empty:
            # 📸 Tradutor de Fotos
            if 'FOTO' in df_cliente.columns:
                def construir_link_foto(f_path):
                    f_str = str(f_path).strip()
                    if f_str and f_str.upper() not in ['NAN', 'NONE', '']:
                        return f"https://www.appsheet.com/template/gettablefileurl?appName=APPIGOLOGISTICA-153047553&tableName=App_Tarefas&fileName={f_str}"
                    return ""
                df_cliente['FOTO_URL'] = df_cliente['FOTO'].apply(construir_link_foto)

            ordem_padrao = ['PEDIDO', 'DATA', 'STATUS', 'LABORATORIO', 'CIDADE', 'UF', 'BAIRRO', 'ENDERECO', 'Nº', 'CEP', 'DATA_LIMITE', 'DATA_ENTREGA', 'FOTO_URL']
            colunas_disponiveis = [col for col in ordem_padrao if col in df_cliente.columns]
            colunas_ocultas_padrao = ['ENDERECO', 'Nº', 'CEP']
            colunas_visiveis_iniciais = [col for col in colunas_disponiveis if col not in colunas_ocultas_padrao]
            hoje_br = datetime.now(FUSO_BR).date()

            with st.sidebar:
                info_cli = CLIENTES_CONFIG.get(st.session_state.cliente, CLIENTES_CONFIG["GRALAB"])
                st.image(info_cli["logo"], width=160)
                st.divider()
                min_d = df_cliente['DATA_OBJ'].dropna().min() if 'DATA_OBJ' in df_cliente.columns else hoje_br
                max_d = df_cliente['DATA_OBJ'].dropna().max() if 'DATA_OBJ' in df_cliente.columns else hoje_br
                datas_sel = st.date_input("🗓️ Período:", value=(min_d, max_d), format="DD/MM/YYYY")
                cidades_sel = st.multiselect("📍 Cidades:", options=sorted(df_cliente['CIDADE'].dropna().unique().tolist()))
                busca_ped = st.text_input("🔍 Pedido / Nº:")
                with st.popover("⚙️ Personalizar Colunas", use_container_width=True):
                    colunas_selecionadas = st.multiselect("Ver:", options=colunas_disponiveis, default=colunas_visiveis_iniciais)
                if st.button("🚪 Sair", use_container_width=True):
                    st.session_state.logado = False
                    st.rerun()

            # --- FILTROS ---
            df_f = df_cliente.copy()
            if len(datas_sel) == 2:
                df_f = df_f[(df_f['DATA_OBJ'] >= datas_sel[0]) & (df_f['DATA_OBJ'] <= datas_sel[1])]
            if cidades_sel:
                df_f = df_f[df_f['CIDADE'].isin(cidades_sel)]
            if busca_ped:
                b = str(busca_ped).upper()
                df_f = df_f[df_f['PEDIDO'].astype(str).str.contains(b) | df_f['NUMERO'].astype(str).str.contains(b)]

            # --- 🛠️ LÓGICA DE STATUS REFINADA (FRUSTRADAS INCLUÍDAS) ---
            def tratar_status(row):
                s = str(row.get('STATUS', '')).strip().upper()
                previsao = str(row.get('DATA_LIMITE', '')).strip()
                
                if s == 'ENTREGUE': res = '✅ Entregue'
                elif s in ['EM ROTA', 'EM ROTA DE ENTREGA']: res = '🚚 Em Rota'
                elif s == 'COLETADO': res = '📦 Coletado'
                elif 'FRUSTRADA' in s: res = '❌ Frustrada' # 🎯 RECONHECE AQUI!
                elif s == 'CANCELADO': res = '🚫 Cancelado'
                else: res = '⏳ Pendente'
                
                if res not in ['✅ Entregue', '🚫 Cancelado', '❌ Frustrada'] and previsao:
                    try:
                        if datetime.strptime(previsao, "%d/%m/%Y").date() < hoje_br:
                            res = f"🚨 ATRASADO ({res})"
                    except: pass
                return res
            
            df_f['STATUS_DISPLAY'] = df_f.apply(tratar_status, axis=1)

            # --- KPIs ---
            v_total = len(df_f)
            v_atrasados = len(df_f[df_f['STATUS_DISPLAY'].str.contains('ATRASADO', na=False)])
            v_frustradas = len(df_f[df_f['STATUS_DISPLAY'].str.contains('Frustrada', na=False)]) # 🎯 CONTAGEM NOVA
            v_hoje = len(df_f[df_f['DATA_OBJ'] == hoje_br])

            st.markdown(f"<h1>Painel de Cargas | {st.session_state.cliente}</h1>", unsafe_allow_html=True)
            csv_data = df_f[colunas_selecionadas].to_csv(index=False, sep=";").encode('utf-8-sig')
            st.download_button(label="📥 Exportar Excel", data=csv_data, file_name=f"Cargas_{st.session_state.cliente}.csv", mime="text/csv")
            st.markdown(f"<div class='sync-status'>🟢 Sincronizado {datetime.now(FUSO_BR).strftime('%H:%M')}</div>", unsafe_allow_html=True)

            c1, c2, c3, c4 = st.columns(4)
            c1.markdown(f"""<div class="kpi-card bg-blue"><div class="kpi-title">📦 Total</div><div class="kpi-value">{v_total}</div></div>""", unsafe_allow_html=True)
            c2.markdown(f"""<div class="kpi-card bg-orange"><div class="kpi-title">❌ Frustradas</div><div class="kpi-value">{v_frustradas}</div></div>""", unsafe_allow_html=True)
            c3.markdown(f"""<div class="kpi-card bg-red"><div class="kpi-title">🚨 Atrasados</div><div class="kpi-value">{v_atrasados}</div></div>""", unsafe_allow_html=True)
            c4.markdown(f"""<div class="kpi-card bg-green"><div class="kpi-title">📅 Hoje</div><div class="kpi-value">{v_hoje}</div></div>""", unsafe_allow_html=True)

            # --- AG-GRID ---
            df_grid = df_f.copy()
            df_grid['STATUS'] = df_grid['STATUS_DISPLAY'] # Substitui para a grid mostrar o ícone
            df_final = df_grid[colunas_selecionadas].copy()
            
            gb = GridOptionsBuilder.from_dataframe(df_final)
            gb.configure_default_column(resizable=True, sortable=True, minWidth=110)
            gb.configure_selection('single', use_checkbox=False)
            
            if 'FOTO_URL' in df_final.columns:
                link_jscode = JsCode("""
                class LinkCellRenderer {
                    init(params) {
                        this.eGui = document.createElement('div');
                        this.eGui.style.textAlign = 'center';
                        if (params.value && params.value !== '' && params.value !== 'nan') {
                            this.eGui.innerHTML = '<a href="' + params.value + '" target="_blank" style="text-decoration: none; font-size: 18px; display: block; margin-top: 4px;" title="Ver Foto">📸</a>';
                        }
                    }
                    getGui() { return this.eGui; }
                }
                """)
                gb.configure_column("FOTO_URL", headerName="Foto", cellRenderer=link_jscode, width=80)
            
            grid_css = {
                ".ag-header-cell-text": {"font-size": "12px !important", "font-weight": "bold"},
                ".ag-cell": {"font-size": "12px !important"}
            }

            AgGrid(df_final, gridOptions=gb.build(), allow_unsafe_jscode=True, theme='alpine', custom_css=grid_css, fit_columns_on_grid_load=True, height=550)
