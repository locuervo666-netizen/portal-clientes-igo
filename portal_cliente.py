import streamlit as st
import pandas as pd
import gspread
import os
import urllib.parse
from datetime import datetime, timedelta, timezone
from streamlit_autorefresh import st_autorefresh
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

FUSO_BR = timezone(timedelta(hours=-3))
# 🎯 ATENÇÃO ROBSON: Link oficial da Logo IGO
LOGO_IGO = "https://i.postimg.cc/d71mqWDx/IGO-LOGO.png"

# =======================================================
# 🎨 1. CONFIGURAÇÃO DA PÁGINA E CSS BASE (COMPLETO)
# =======================================================
st.set_page_config(page_title="Monitoramento IGO Logística", layout="wide", page_icon="🚚", initial_sidebar_state="expanded")
st_autorefresh(interval=60000, limit=None, key="refresh_timer")

st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { transition: background-color 0.3s ease; font-family: 'Inter', sans-serif; }
    [data-testid="stSidebar"] { transition: background-color 0.3s ease; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {background-color: transparent !important;}
    
    .block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; padding-left: 2rem !important; padding-right: 2rem !important; }
    
    /* 🎨 BLOCOS COLORIDOS GRADIENTES ORIGINAIS */
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
    .header-container { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 15px; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px; }
    .sync-status { font-size: 12px; color: #10B981; font-weight: 700; }
    button[data-baseweb="tab"] { font-size: 16px !important; font-weight: 700 !important; }
    
    .stTextInput > div > div > input { font-size: 16px !important; padding: 10px !important; border-radius: 8px !important; }
    </style>
    """, unsafe_allow_html=True)

CLIENTES_CONFIG = {
    "GRALAB": {"senha": "123", "logo": "https://cdn.awsli.com.br/2702/2702264/logo/gralab-rbuogsxve7.png", "filtro": "GRALAB"},
    "IGO_LOGISTICA": {"senha": "admin", "logo": LOGO_IGO, "filtro": "TODOS"},
    "LOGISTICA.LABEST": {"senha": "123", "logo": "https://i.postimg.cc/mD8P8pGZ/LABEST-LOGO.png", "filtro": "LABEST"}
}

# =======================================================
# 🔗 2. MOTOR DE DADOS PRINCIPAL
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
            with open("cred_temp.json", "w", encoding="utf-8") as f: f.write(st.secrets["google_cred_json"])
            with open("token_temp.json", "w", encoding="utf-8") as f: f.write(st.secrets["google_token_json"])
            return gspread.oauth(credentials_filename="cred_temp.json", authorized_user_filename="token_temp.json")
        return None
    except: return None

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
                    cols_limpas = [str(c).upper().strip().replace(' ', '') for c in df_app.columns]
                    df_app.columns = cols_limpas
                    c_s, c_o, c_f = 'STATUS', 'OBSERVACOES', 'FOTO'
                    df_app_clean = df_app[['PEDIDO', c_s, c_o, c_f]].copy()
                    df_app_clean.columns = ['PEDIDO', 'A_ST', 'A_OB', 'A_FO']
                    df_app_clean['PEDIDO'] = df_app_clean['PEDIDO'].astype(str).str.strip()
                    df_app_clean.drop_duplicates(subset=['PEDIDO'], keep='last', inplace=True)
                    df['PEDIDO'] = df['PEDIDO'].astype(str).str.strip()
                    df = pd.merge(df, df_app_clean, on='PEDIDO', how='left')
                    df['FOTO'] = df['A_FO'].fillna('')
            except: pass
            if 'DATA' in df.columns: df['DATA_OBJ'] = pd.to_datetime(df['DATA'], format='%d/%m/%Y', errors='coerce').dt.date
            return df
    except: return pd.DataFrame()

if 'logado' not in st.session_state: st.session_state.logado = False
if 'filtro_kpi' not in st.session_state: st.session_state.filtro_kpi = "TODOS"

# =======================================================
# 🔐 3. LOGIN
# =======================================================
if not st.session_state.logado:
    st.markdown("""<style> [data-testid="stAppViewContainer"] { background-color: #f8fafc !important; } </style>""", unsafe_allow_html=True)
    _, c2, _ = st.columns([1, 1.2, 1])
    with c2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        with st.container(border=True):
            st.image(LOGO_IGO, width=110)
            u = st.text_input("👤 Usuário").upper().strip()
            s = st.text_input("🔒 Senha", type="password")
            if st.button("🚀 Acessar Sistema", type="primary", use_container_width=True):
                if u in CLIENTES_CONFIG and s == CLIENTES_CONFIG[u]["senha"]:
                    st.session_state.logado, st.session_state.cliente = True, u; st.rerun()
                else: st.error("Incorreto")
else:
    # 🚀 4. PAINEL PRINCIPAL
    df_raw = carregar_dados_nuvem()
    if not df_raw.empty:
        conf = CLIENTES_CONFIG[st.session_state.cliente]
        df_cliente = df_raw if conf["filtro"] == "TODOS" else df_raw[df_raw['TOMADOR'].str.upper().str.strip() == conf["filtro"]].copy()
        hoje_br = datetime.now(FUSO_BR).date()
        
        if not df_cliente.empty:
            def get_st(row):
                s = str(row.get('A_ST', row.get('STATUS', ''))).upper()
                if 'ENTREGUE' in s: return '✅ Entregue'
                if 'FRUSTRADA' in s: return '❌ Frustrada'
                return '⏳ Pendente'
            df_cliente['STATUS_DISPLAY'] = df_cliente.apply(get_st, axis=1)
            df_cliente['FOTO_URL'] = df_cliente['FOTO'].apply(lambda x: f"https://www.appsheet.com/template/gettablefileurl?appName=APPIGOLOGISTICA-153047553&tableName=App_Tarefas&fileName={str(x).strip()}" if x else "")

            with st.sidebar:
                st.image(conf["logo"], width=160)
                st.divider()
                modo_noturno = st.toggle("🌙 Modo Noturno")
                datas_sel = st.date_input("🗓️ Período:", value=(hoje_br - timedelta(days=7), hoje_br))
                cidades_sel = st.multiselect("📍 Cidades:", sorted(df_cliente['CIDADE'].dropna().unique().tolist()))
                st.divider()

            # FILTROS DE DADOS
            df_f = df_cliente.copy()
            if len(datas_sel) == 2: df_f = df_f[(df_f['DATA_OBJ'] >= datas_sel[0]) & (df_f['DATA_OBJ'] <= datas_sel[1])]
            if cidades_sel: df_f = df_f[df_f['CIDADE'].isin(cidades_sel)]

            # HEADER
            st.markdown(f"""<div class="header-container"><h2 style="margin:0; font-weight:900; font-size:22px;">Monitoramento {st.session_state.cliente}</h2><div class='sync-status'>🟢 Sincronizado {datetime.now(FUSO_BR).strftime('%H:%M')}</div></div>""", unsafe_allow_html=True)

            # KPIs
            ck = st.columns(5)
            def set_kpi(v): st.session_state.filtro_kpi = v
            n_tot_k = len(df_f); n_ent_k = len(df_f[df_f['STATUS_DISPLAY'].str.contains('Entregue')])
            n_fru_k = len(df_f[df_f['STATUS_DISPLAY'].str.contains('Frustrada')])
            with ck[0]: st.button(f"📦 TOTAL\n\n{n_tot_k}", key="kpi_total", use_container_width=True, on_click=set_kpi, args=("TODOS",))
            with ck[1]: st.button(f"✅ ENTREGUES\n\n{n_ent_k}", key="kpi_entregue", use_container_width=True, on_click=set_kpi, args=("ENTREGUE",))
            with ck[2]: st.button(f"❌ FRUSTRADAS\n\n{n_fru_k}", key="kpi_frus", use_container_width=True, on_click=set_kpi, args=("FRUSTRADA",))
            with ck[3]: st.button(f"🚨 ATRASADOS\n\n0", key="kpi_atra", use_container_width=True)
            with ck[4]: st.button(f"📅 HOJE\n\n{len(df_f[df_f['DATA_OBJ'] == hoje_br])}", key="kpi_hoje", use_container_width=True, on_click=set_kpi, args=("HOJE",))

            # PROGRESSO
            st.markdown("<br>🎯 **Progresso de Hoje**", unsafe_allow_html=True)
            df_h = df_f[df_f['DATA_OBJ'] == hoje_br]
            if not df_h.empty:
                tx = len(df_h[df_h['STATUS_DISPLAY'].str.contains('Entregue|Frustrada')]) / len(df_h)
                st.progress(tx)
            else: st.info("Nenhum pedido para hoje.")

            # BUSCA RÁPIDA
            busca = st.text_input("🔎 Busca Rápida:", placeholder="Pedido, laboratório, cidade...")
            df_grid = df_f.copy()
            if st.session_state.filtro_kpi == "ENTREGUE": df_grid = df_grid[df_grid['STATUS_DISPLAY'].str.contains('Entregue')]
            if busca: df_grid = df_grid[df_grid.astype(str).apply(lambda x: x.str.lower().str.contains(busca.lower())).any(axis=1)]

            # SIDEBAR - BOTÕES DE WHATSAPP E EXCEL NO FINAL
            with st.sidebar:
                texto_w = f"*Resumo IGO - {st.session_state.cliente}*\n📦 Total: {len(df_grid)}"
                st.markdown(f'<a href="https://api.whatsapp.com/send?text={urllib.parse.quote(texto_w)}" target="_blank" style="text-decoration:none;"><div style="background:#25D366; color:white; padding:10px; border-radius:8px; font-weight:bold; text-align:center; margin-bottom:15px;">📲 Enviar Resumo WhatsApp</div></a>', unsafe_allow_html=True)
                csv = df_grid.to_csv(index=False, sep=';').encode('utf-8-sig')
                st.download_button("📥 Exportar Relatório (CSV)", data=csv, file_name=f"Relatorio_{st.session_state.cliente}.csv", use_container_width=True)
                st.divider()
                if st.button("🚪 Sair do Sistema", use_container_width=True): 
                    st.session_state.logado = False
                    st.rerun()

            # GRID
            if not df_grid.empty:
                df_grid['STATUS'] = df_grid['STATUS_DISPLAY']
                cols = ['DATA', 'PEDIDO', 'STATUS', 'LABORATORIO', 'CIDADE', 'UF', 'BAIRRO', 'DATA_LIMITE', 'FOTO_URL']
                df_final = df_grid[[c for c in cols if c in df_grid.columns]]
                gb = GridOptionsBuilder.from_dataframe(df_final)
                gb.configure_default_column(resizable=True, sortable=True, minWidth=100)
                status_js = JsCode("""function(params) { let v = params.value || ''; if (v.includes('Entregue')) return {'backgroundColor': 'rgba(16, 185, 129, 0.15)', 'color': '#10B981', 'fontWeight': '900'}; if (v.includes('Frustrada')) return {'backgroundColor': 'rgba(239, 68, 68, 0.15)', 'color': '#EF4444', 'fontWeight': '900'}; return {'fontWeight': 'bold'}; }""")
                foto_js = JsCode("""class FotoRenderer { init(params) { this.eGui = document.createElement('div'); this.eGui.style.textAlign = 'center'; if (params.value && params.value.includes('http')) { let b = document.createElement('span'); b.innerHTML = '📸'; b.style.cursor='pointer'; b.onclick = () => { let m = document.createElement('div'); Object.assign(m.style, {position:'fixed', zIndex:'9999999', left:0, top:0, width:'100vw', height:'100vh', backgroundColor:'rgba(0,0,0,0.85)', display:'flex', flexDirection:'column', justifyContent:'center', alignItems:'center', cursor:'zoom-out'}); let i = document.createElement('img'); i.src = params.value; Object.assign(i.style, {maxWidth:'90%', maxHeight:'85%', borderRadius:'8px', boxShadow:'0 4px 20px rgba(0,0,0,0.5)', objectFit:'contain'}); m.appendChild(i); m.onclick = () => document.body.removeChild(m); document.body.appendChild(m); }; this.eGui.appendChild(b); } else { this.eGui.innerHTML = '➖'; } } getGui() { return this.eGui; } }""")
                gb.configure_column("STATUS", cellStyle=status_js)
                gb.configure_column("FOTO_URL", headerName="FOTO", cellRenderer=foto_js, width=80)
                AgGrid(df_final, gridOptions=gb.build(), allow_unsafe_jscode=True, theme='alpine', height=550)
