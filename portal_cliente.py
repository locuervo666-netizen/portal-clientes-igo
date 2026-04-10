import streamlit as st
import pandas as pd
import gspread
import os
import urllib.parse
from datetime import datetime, timedelta, timezone
from streamlit_autorefresh import st_autorefresh

FUSO_BR = timezone(timedelta(hours=-3))
LOGO_IGO = "https://i.postimg.cc/d71mqWDx/IGO-LOGO.png"

# =======================================================
# 🎨 1. CONFIGURAÇÃO DA PÁGINA E CSS BASE
# =======================================================
st.set_page_config(page_title="Monitoramento IGO Logística", layout="wide", page_icon="🚚", initial_sidebar_state="expanded")
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
    div.st-key-kpi_total button { background: linear-gradient(135deg, #1E3A8A 0%, #3B82F6 100%) !important; }
    div.st-key-kpi_entregue button { background: linear-gradient(135deg, #064E3B 0%, #10B981 100%) !important; }
    div.st-key-kpi_frus button { background: linear-gradient(135deg, #9A3412 0%, #F59E0B 100%) !important; }
    div.st-key-kpi_atra button { background: linear-gradient(135deg, #7F1D1D 0%, #EF4444 100%) !important; }
    div.st-key-kpi_hoje button { background: linear-gradient(135deg, #4C1D95 0%, #8B5CF6 100%) !important; }
    
    div.st-key-kpi_total button p, div.st-key-kpi_entregue button p, div.st-key-kpi_frus button p, div.st-key-kpi_atra button p, div.st-key-kpi_hoje button p { 
        font-weight: 800 !important; font-size: 15px !important; color: #ffffff !important; margin: 0 !important;
    }
    .header-container { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 15px; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px; }
    .sync-status { font-size: 12px; color: #10B981; font-weight: 700; }
    </style>
    """, unsafe_allow_html=True)

CLIENTES_CONFIG = {
    "GRALAB": {"senha": "123", "logo": "https://cdn.awsli.com.br/2702/2702264/logo/gralab-rbuogsxve7.png", "filtro": "GRALAB"},
    "IGO_LOGISTICA": {"senha": "admin", "logo": LOGO_IGO, "filtro": "TODOS"},
    "LOGISTICA.LABEST": {"senha": "123", "logo": "https://i.postimg.cc/mD8P8pGZ/LABEST-LOGO.png", "filtro": "LABEST"}
}

# =======================================================
# 🔗 2. MOTOR DE DADOS (Conexão Blindada Render)
# =======================================================
@st.cache_resource
def conectar_banco():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        import json
        import os
        from google.oauth2.credentials import Credentials
        
        # Lê a senha do painel do Render
        token_str = os.environ.get("google_token_json")
        
        if not token_str:
            try: token_str = st.secrets.get("google_token_json")
            except: pass
                
        if not token_str:
            st.error("⚠️ Senha do Google não detectada no Render.")
            return None
            
        token_info = json.loads(token_str)
        creds = Credentials.from_authorized_user_info(token_info, scopes=scopes)
        gc = gspread.authorize(creds)
        return gc.open("DB_IGO_Logistica")
        
    except Exception as e:
        st.error(f"Erro na leitura da chave: {e}")
    return None

@st.cache_data(ttl=30)
def carregar_dados_nuvem():
    try:
        gc = conectar_banco()
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
                    df_app.columns = [str(c).upper().strip().replace(' ', '') for c in df_app.columns]
                    df_app_clean = df_app[['PEDIDO', 'STATUS', 'OBSERVACOES', 'FOTO']].copy()
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
# 🔐 3. LOGIN / PAINEL
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
    df_raw = carregar_dados_nuvem()
    if not df_raw.empty:
        conf = CLIENTES_CONFIG[st.session_state.cliente]
        df_cliente = df_raw if conf["filtro"] == "TODOS" else df_raw[df_raw['TOMADOR'].str.upper().str.strip() == conf["filtro"]].copy()
        hoje_br = datetime.now(FUSO_BR).date()
        
        if not df_cliente.empty:
            # Funções de Status e Fotos
            def get_st(row):
                s = str(row.get('A_ST', row.get('STATUS', ''))).upper()
                if 'ENTREGUE' in s: return '✅ Entregue'
                if 'FRUSTRADA' in s: return '❌ Frustrada'
                return '⏳ Pendente'
            
            df_cliente['STATUS_DISPLAY'] = df_cliente.apply(get_st, axis=1)
            df_cliente['FOTO_URL'] = df_cliente['FOTO'].apply(lambda x: f"https://www.appsheet.com/template/gettablefileurl?appName=APPIGOLOGISTICA-153047553&tableName=App_Tarefas&fileName={str(x).strip()}" if x else "")

            # --- SIDEBAR (CONFIGURAÇÃO) ---
            with st.sidebar:
                st.image(conf["logo"], width=160)
                st.divider()
                st.toggle("🌙 Modo Noturno")
                
                # AJUSTE BRASILEIRO AQUI
                datas_sel = st.date_input(
                    "🗓️ Período:", 
                    value=(hoje_br - timedelta(days=7), hoje_br),
                    format="DD/MM/YYYY"
                )
                
                cidades_sel = st.multiselect("📍 Cidades:", sorted(df_cliente['CIDADE'].dropna().unique().tolist()))
                st.divider()

            # --- LÓGICA DE FILTROS ---
            df_f = df_cliente.copy()
            
            # FILTRO DE DATA SEGURO
            if isinstance(datas_sel, (tuple, list)) and len(datas_sel) == 2:
                df_f = df_f[(df_f['DATA_OBJ'] >= datas_sel[0]) & (df_f['DATA_OBJ'] <= datas_sel[1])]
            
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

            # BUSCA E GRID
            st.markdown("<br>", unsafe_allow_html=True)
            busca = st.text_input("🔎 Busca Rápida:", placeholder="Pedido, laboratório, cidade...")
            
            df_grid = df_f.copy()
            if st.session_state.filtro_kpi != "TODOS":
                if st.session_state.filtro_kpi == "HOJE":
                    df_grid = df_grid[df_grid['DATA_OBJ'] == hoje_br]
                else:
                    df_grid = df_grid[df_grid['STATUS_DISPLAY'].str.contains(st.session_state.filtro_kpi, case=False)]
            
            if busca: df_grid = df_grid[df_grid.astype(str).apply(lambda x: x.str.lower().str.contains(busca.lower())).any(axis=1)]

            if not df_grid.empty:
                df_grid['STATUS'] = df_grid['STATUS_DISPLAY']
                cols = ['DATA', 'PEDIDO', 'STATUS', 'LABORATORIO', 'CIDADE', 'UF', 'BAIRRO', 'DATA_LIMITE', 'FOTO_URL']
                df_final = df_grid[[c for c in cols if c in df_grid.columns]].copy()
                
                # Prepara os dados e adiciona a coluna de seleção
                for col in df_final.columns: 
                    df_final[col] = df_final[col].astype(str).replace(["nan", "NaN", "None", "none", "<NA>", "NaT"], "")
                df_final['COMPROVANTE'] = df_final['FOTO_URL'].apply(lambda x: x if str(x).startswith("http") else "")
                df_final.drop(columns=['FOTO_URL'], inplace=True)
                df_final.insert(0, "SELECIONAR", False)

                st.markdown("<p style='font-size:13px; color:#64748B;'>Selecione a caixinha do pedido para visualizar a foto do comprovante de entrega.</p>", unsafe_allow_html=True)

                # 🔥 TABELA NATIVA (O Retorno da Estabilidade) 🔥
                tabela_renderizada = st.data_editor(
                    df_final,
                    column_config={
                        "SELECIONAR": st.column_config.CheckboxColumn("✔ VER FOTO", default=False),
                        "STATUS": st.column_config.TextColumn("STATUS DA ENTREGA"),
                        "COMPROVANTE": st.column_config.LinkColumn("FOTO", display_text="🔎 Abrir Link"),
                        "DATA_LIMITE": st.column_config.TextColumn("PREVISÃO"),
                        "DATA": st.column_config.TextColumn("EMBARQUE"),
                        "PEDIDO": st.column_config.TextColumn("PEDIDO"),
                        "LABORATORIO": st.column_config.TextColumn("PONTO DE COLETA"),
                        "CIDADE": st.column_config.TextColumn("CIDADE")
                    },
                    disabled=[c for c in df_final.columns if c != "SELECIONAR"],
                    hide_index=True,
                    use_container_width=True,
                    height=500
                )

                # 🔥 VISUALIZADOR DE FOTOS EMBUTIDO PARA O CLIENTE 🔥
                linhas_selecionadas = tabela_renderizada[tabela_renderizada["SELECIONAR"]]
                if not linhas_selecionadas.empty:
                    selecionados_com_foto = linhas_selecionadas[linhas_selecionadas["COMPROVANTE"].astype(str).str.startswith("http")]
                    if not selecionados_com_foto.empty:
                        st.markdown("<h4 style='color:#0F172A; margin-top: 15px;'>📸 Comprovantes de Entrega Selecionados</h4>", unsafe_allow_html=True)
                        cols_fotos = st.columns(min(len(selecionados_com_foto), 4)) 
                        for i, (_, row) in enumerate(selecionados_com_foto.iterrows()):
                            with cols_fotos[i % 4]:
                                with st.container(border=True):
                                    st.markdown(f"**Pedido:** {row['PEDIDO']}")
                                    st.image(row["COMPROVANTE"], use_container_width=True)
                                    st.markdown(f"<div style='text-align:center;'><a href='{row['COMPROVANTE']}' target='_blank' style='text-decoration:none; color:#0284C7; font-weight:bold;'>🔗 Ampliar Original</a></div>", unsafe_allow_html=True)
                        st.markdown("<br>", unsafe_allow_html=True)

            # SIDEBAR FINAL
            with st.sidebar:
                csv = df_grid.to_csv(index=False, sep=';').encode('utf-8-sig')
                st.download_button("📥 Exportar Relatório (CSV)", data=csv, file_name=f"Relatorio_{st.session_state.cliente}.csv", use_container_width=True)
                if st.button("🚪 Sair do Sistema", use_container_width=True): 
                    st.session_state.logado = False
                    st.rerun()
