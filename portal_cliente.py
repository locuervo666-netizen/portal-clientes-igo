import streamlit as st
import pandas as pd
import gspread
import os
import json
from datetime import datetime, date, timezone, timedelta
from streamlit_autorefresh import st_autorefresh
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

FUSO_BR = timezone(timedelta(hours=-3))

st.set_page_config(page_title="Portal IGO Logística", layout="wide", page_icon="🚚", initial_sidebar_state="expanded")
st_autorefresh(interval=60000, limit=None, key="refresh_timer")

# =======================================================
# 🎨 CSS ELITE
# =======================================================
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #f0f2f6; font-family: 'Inter', sans-serif; }
    .kpi-card { padding: 15px 20px; border-radius: 10px; color: white; box-shadow: 0 4px 10px rgba(0,0,0,0.1); margin-bottom: 15px; display: flex; flex-direction: column; justify-content: center; }
    .kpi-value { font-size: 28px; font-weight: 900; line-height: 1; margin: 0; }
    .bg-blue { background: linear-gradient(135deg, #1E3A8A 0%, #3B82F6 100%); }
    .bg-orange { background: linear-gradient(135deg, #9A3412 0%, #F59E0B 100%); }
    .bg-red { background: linear-gradient(135deg, #7F1D1D 0%, #EF4444 100%); }
    .bg-green { background: linear-gradient(135deg, #064E3B 0%, #10B981 100%); }
    h1 { color: #0f172a; font-weight: 900; font-size: 24px; letter-spacing: -0.5px; }
    .sync-status { text-align: right; font-size: 12px; color: #10B981; font-weight: 600; }
    </style>
    """, unsafe_allow_html=True)

CLIENTES_CONFIG = {
    "GRALAB": {"senha": "123", "logo": "https://cdn.awsli.com.br/2702/2702264/logo/gralab-rbuogsxve7.png"},
    "IGO_LOGISTICA": {"senha": "admin", "logo": "https://cdn-icons-png.flaticon.com/512/1532/1532692.png"}
}

# =======================================================
# 🔗 MOTOR DE DADOS (COM REFRESCO AUTOMÁTICO)
# =======================================================
@st.cache_data(ttl=30) # Reduzi para 30 segundos para ser mais rápido
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

if not st.session_state.logado:
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<br><br><br><br>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("### Acesso ao Portal")
            usuario = st.text_input("Usuário").upper().strip()
            senha = st.text_input("Senha", type="password")
            if st.button("Entrar", type="primary", use_container_width=True):
                if usuario in CLIENTES_CONFIG and senha == CLIENTES_CONFIG[usuario]["senha"]:
                    st.session_state.logado, st.session_state.cliente = True, usuario
                    st.rerun()
                else: st.error("Incorreto.")
else:
    df_sistema = carregar_dados_nuvem()
    if not df_sistema.empty:
        df_cliente = df_sistema if st.session_state.cliente == "IGO_LOGISTICA" else df_sistema[df_sistema['TOMADOR'] == st.session_state.cliente].copy()
        
        if not df_cliente.empty:
            # 📸 Tradutor de Fotos
            if 'FOTO' in df_cliente.columns:
                df_cliente['FOTO_URL'] = df_cliente['FOTO'].apply(lambda x: f"https://www.appsheet.com/template/gettablefileurl?appName=APPIGOLOGISTICA-153047553&tableName=App_Tarefas&fileName={str(x).strip()}" if str(x).strip() and str(x).upper() not in ['NAN', 'NONE', ''] else "")

            # 🛠️ GERAÇÃO DA COLUNA "DETALHES" (MELHORADA)
            # Buscamos as colunas independente se tem '?' ou não
            def achar_coluna(lista_cols, termos):
                for c in lista_cols:
                    if any(t in c for t in termos): return c
                return None

            col_resp = achar_coluna(df_cliente.columns, ['QUEM ATENDEU', 'RESPONSAVEL'])
            col_obs = achar_coluna(df_cliente.columns, ['OBSERVACOES', 'OBS'])

            def formatar_detalhes(row):
                resp = str(row.get(col_resp, '')).strip() if col_resp else ""
                obs = str(row.get(col_obs, '')).strip() if col_obs else ""
                
                # Limpa valores fantasmas
                resp = "" if resp.upper() in ['NAN', 'NONE', ''] else resp
                obs = "" if obs.upper() in ['NAN', 'NONE', ''] else obs

                if resp and obs: return f"🗣️ {resp} / 📝 {obs}"
                if resp: return f"🗣️ Resp: {resp}"
                if obs: return f"📝 Motivo: {obs}"
                return ""

            df_cliente['DETALHES'] = df_cliente.apply(formatar_detalhes, axis=1)

            # --- CONFIGURAÇÃO ---
            hoje_br = datetime.now(FUSO_BR).date()
            with st.sidebar:
                st.image(CLIENTES_CONFIG[st.session_state.cliente]["logo"], width=160)
                st.divider()
                datas_sel = st.date_input("🗓️ Período:", value=(hoje_br, hoje_br), format="DD/MM/YYYY")
                cidades_sel = st.multiselect("📍 Cidades:", options=sorted(df_cliente['CIDADE'].dropna().unique().tolist()))
                busca_ped = st.text_input("🔍 Pedido / Nº:")
                if st.button("🚪 Sair", use_container_width=True):
                    st.session_state.logado = False
                    st.rerun()

            # --- FILTROS ---
            df_f = df_cliente.copy()
            if len(datas_sel) == 2: df_f = df_f[(df_f['DATA_OBJ'] >= datas_sel[0]) & (df_f['DATA_OBJ'] <= datas_sel[1])]
            if cidades_sel: df_f = df_f[df_f['CIDADE'].isin(cidades_sel)]
            if busca_ped:
                b = str(busca_ped).upper()
                df_f = df_f[df_f['PEDIDO'].astype(str).str.contains(b) | df_f['NUMERO'].astype(str).str.contains(b)]

            # --- STATUS ---
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
            
            df_f['STATUS_DISPLAY'] = df_f.apply(tratar_status, axis=1)

            # --- DASHBOARD ---
            st.markdown(f"<h1>Painel de Cargas | {st.session_state.cliente}</h1>", unsafe_allow_html=True)
            c1, c2, c3, c4 = st.columns(4)
            c1.markdown(f'<div class="kpi-card bg-blue"><div class="kpi-value">{len(df_f)}</div><div>📦 Total</div></div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="kpi-card bg-orange"><div class="kpi-value">{len(df_f[df_f["STATUS_DISPLAY"].str.contains("Frustrada")])}</div><div>❌ Frustradas</div></div>', unsafe_allow_html=True)
            c3.markdown(f'<div class="kpi-card bg-red"><div class="kpi-value">{len(df_f[df_f["STATUS_DISPLAY"].str.contains("ATRASADO")])}</div><div>🚨 Atrasados</div></div>', unsafe_allow_html=True)
            c4.markdown(f'<div class="kpi-card bg-green"><div class="kpi-value">{len(df_f[df_f["DATA_OBJ"] == hoje_br])}</div><div>📅 Hoje</div></div>', unsafe_allow_html=True)

            # --- GRID ---
            df_grid = df_f.copy()
            df_grid['STATUS'] = df_grid['STATUS_DISPLAY']
            # Garante que DETALHES está na lista
            cols_grid = ['PEDIDO', 'DATA', 'STATUS', 'DETALHES', 'LABORATORIO', 'CIDADE', 'FOTO_URL']
            df_final = df_grid[[c for c in cols_grid if c in df_grid.columns]]

            gb = GridOptionsBuilder.from_dataframe(df_final)
            gb.configure_default_column(resizable=True, sortable=True, minWidth=110)
            if 'FOTO_URL' in df_final.columns:
                link_jscode = JsCode("""class LinkCellRenderer { init(params) { this.eGui = document.createElement('div'); this.eGui.style.textAlign = 'center'; if (params.value) { this.eGui.innerHTML = '<a href="' + params.value + '" target="_blank" style="text-decoration: none; font-size: 18px;">📸</a>'; } } getGui() { return this.eGui; } }""")
                gb.configure_column("FOTO_URL", headerName="Foto", cellRenderer=link_jscode, width=80)
            
            AgGrid(df_final, gridOptions=gb.build(), allow_unsafe_jscode=True, theme='alpine', fit_columns_on_grid_load=True, height=500)
            st.markdown(f"<div class='sync-status'>🟢 Sincronizado {datetime.now(FUSO_BR).strftime('%H:%M')}</div>", unsafe_allow_html=True)
