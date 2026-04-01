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
# 🎨 1. CONFIGURAÇÃO DA PÁGINA E CSS INTEGRAL (RESTAURADO)
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
        font-weight: 800 !important; font-size: 15px !important; color: #ffffff !important; text-align: center !important;
    }
    .header-container { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 15px; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px; }
    .sync-status { font-size: 12px; color: #10B981; font-weight: 700; }
    </style>
    """, unsafe_allow_html=True)

# =======================================================
# 🔗 2. MOTOR DE DADOS (MERGE APP_TAREFAS + MEMORIA)
# =======================================================
@st.cache_resource
def conectar_banco_seguro():
    try:
        if "google_cred_json" in st.secrets:
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
        df = pd.DataFrame(dados_m[1:], columns=dados_m[0])
        df.columns = df.columns.str.strip().str.upper()

        try:
            aba_app = planilha.worksheet("App_Tarefas")
            dados_app = aba_app.get_all_values()
            df_app = pd.DataFrame(dados_app[1:], columns=dados_app[0])
            df_app.columns = [str(c).upper().strip().replace(' ', '') for c in df_app.columns]
            
            c_s, c_o, c_q, c_f = 'STATUS', 'OBSERVACOES', 'DETALHES', 'FOTO'
            def extrair(r):
                return pd.Series([str(r.get(c_s,'')), str(r.get(c_o,'')), str(r.get(c_q,'')), str(r.get(c_f,''))])

            df_app[['A_ST', 'A_OB', 'A_QU', 'A_FO']] = df_app.apply(extrair, axis=1)
            df_app_clean = df_app[['PEDIDO', 'A_ST', 'A_OB', 'A_QU', 'A_FO']].copy()
            df_app_clean['PEDIDO'] = df_app_clean['PEDIDO'].astype(str).str.strip()
            df_app_clean.drop_duplicates(subset=['PEDIDO'], keep='last', inplace=True)
            
            df['PEDIDO'] = df['PEDIDO'].astype(str).str.strip()
            df = pd.merge(df, df_app_clean, on='PEDIDO', how='left')
            
            # Merge por Romaneio
            if 'ROMANEIO' in df.columns:
                df['ROMANEIO'] = df['ROMANEIO'].astype(str).str.strip()
                df_rom = df_app_clean[df_app_clean['PEDIDO'].str.startswith('ROM-', na=False)].rename(columns={'PEDIDO':'ROMANEIO'})
                df = pd.merge(df, df_rom, on='ROMANEIO', how='left', suffixes=('', '_R'))
                for c in ['A_ST', 'A_OB', 'A_QU', 'A_FO']:
                    if f"{c}_R" in df.columns:
                        df[c] = df[f"{c}_R"].replace("", pd.NA).combine_first(df[c].replace("", pd.NA)).fillna("")
            
            df['FOTO'] = df['A_FO'].fillna('')
        except: pass
        
        if 'DATA' in df.columns: df['DATA_OBJ'] = pd.to_datetime(df['DATA'], format='%d/%m/%Y', errors='coerce').dt.date
        return df
    except: return pd.DataFrame()

# =======================================================
# 🔐 3. LOGIN E CONTROLE
# =======================================================
if 'logado' not in st.session_state: st.session_state.logado = False
if 'filtro_kpi' not in st.session_state: st.session_state.filtro_kpi = "TODOS"

if not st.session_state.logado:
    _, c2, _ = st.columns([1, 1.2, 1])
    with c2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        with st.container(border=True):
            st.image(LOGO_IGO, width=110)
            u = st.text_input("Usuário").upper().strip()
            s = st.text_input("Senha", type="password")
            if st.button("🚀 Acessar", use_container_width=True, type="primary"):
                if u in CLIENTES_CONFIG and s == CLIENTES_CONFIG[u]["senha"]:
                    st.session_state.logado, st.session_state.cliente = True, u; st.rerun()
                else: st.error("Acesso negado")
else:
    # =======================================================
    # 🚀 4. DASHBOARD (RESTAURAÇÃO DOS BOTÕES DE EXPORTAÇÃO E WHATSAPP)
    # =======================================================
    df_raw = carregar_dados_nuvem()
    conf = CLIENTES_CONFIG[st.session_state.cliente]
    
    if not df_raw.empty:
        # Virada de Chave (Tomador)
        df_cliente = df_raw if conf["tomador_planilha"] == "TODOS" else df_raw[df_raw['TOMADOR'].str.upper().str.strip() == conf["tomador_planilha"]].copy()
        hoje_br = datetime.now(FUSO_BR).date()
        
        if not df_cliente.empty:
            # Processamento de Status e Detalhes (RESTAURADO)
            def processar_detalhes(row):
                s = str(row.get('A_ST', '')).upper()
                if 'FRUSTRADA' in s:
                    obs = str(row.get('A_OB', '')).upper()
                    emoji = "📝"
                    if "FECHADO" in obs: emoji = "🔒"
                    elif "SEM MATERIAL" in obs: emoji = "📭"
                    elif "RECUS" in obs: emoji = "🛑"
                    return f"{emoji} {row.get('A_QU', '')} - {row.get('A_OB', '')}"
                return ""
            df_cliente['DETALHES'] = df_cliente.apply(processar_detalhes, axis=1)

            def get_status(row):
                s = str(row.get('A_ST', row.get('STATUS', ''))).upper()
                if 'ENTREGUE' in s: return '✅ Entregue'
                if 'FRUSTRADA' in s: return '❌ Frustrada'
                if any(x in s for x in ['ROTA', 'ENTREGA']): return '🚚 Em Rota'
                return '⏳ Pendente'
            df_cliente['STATUS_DISPLAY'] = df_cliente.apply(get_status, axis=1)
            df_cliente['FOTO_URL'] = df_cliente['FOTO'].apply(lambda x: f"https://www.appsheet.com/template/gettablefileurl?appName=APPIGOLOGISTICA-153047553&tableName=App_Tarefas&fileName={str(x).strip()}" if x else "")

            # --- 🛠️ SIDEBAR (RESTAURADO WHATSAPP E EXPORTAR) ---
            with st.sidebar:
                st.image(conf["logo"], width=160)
                st.divider()
                
                # --- DISPARO WHATSAPP ---
                n_tot = len(df_cliente)
                n_ent = len(df_cliente[df_cliente['STATUS_DISPLAY'] == '✅ Entregue'])
                texto_w = f"*Resumo IGO - {st.session_state.cliente}*\n📦 Total: {n_tot}\n✅ OK: {n_ent}"
                link_w = f"https://api.whatsapp.com/send?text={urllib.parse.quote(texto_w)}"
                st.markdown(f'<a href="{link_w}" target="_blank"><button style="width:100%; background:#25D366; color:white; border:none; padding:10px; border-radius:5px; font-weight:bold; cursor:pointer;">📲 Disparar WhatsApp</button></a>', unsafe_allow_html=True)
                
                st.divider()
                # --- EXPORTAR RELATÓRIO ---
                csv = df_cliente.to_csv(index=False, sep=';').encode('utf-8-sig')
                st.download_button("📥 Exportar Relatório (CSV)", data=csv, file_name=f"Relatorio_{st.session_state.cliente}.csv", use_container_width=True)
                
                st.divider()
                if st.button("🚪 Sair"): st.session_state.logado = False; st.rerun()

            # --- CORPO PRINCIPAL ---
            st.markdown(f"""<div class="header-container">
                <div style="display:flex; align-items:center; gap:15px;">
                    <img src="{conf['logo']}" height="50" style="border-radius:8px;">
                    <h2 style="margin:0;">Monitoramento {st.session_state.cliente}</h2>
                </div>
                <div class='sync-status'>🟢 Online {datetime.now(FUSO_BR).strftime('%H:%M')}</div>
            </div>""", unsafe_allow_html=True)

            # KPIs
            ck = st.columns(5)
            ck[0].button(f"📦 TOTAL\n\n{len(df_cliente)}", key="k1", use_container_width=True)
            ck[1].button(f"✅ ENTREGUES\n\n{n_ent}", key="k2", use_container_width=True)

            # GRID
            df_final = df_cliente[['DATA', 'PEDIDO', 'STATUS_DISPLAY', 'LABORATORIO', 'CIDADE', 'DETALHES', 'FOTO_URL']].copy()
            gb = GridOptionsBuilder.from_dataframe(df_final)
            gb.configure_column("FOTO_URL", headerName="FOTO", cellRenderer=JsCode("""
                class FotoRenderer {
                    init(params) {
                        this.eGui = document.createElement('div');
                        if (params.value && params.value.includes('http')) {
                            this.eGui.innerHTML = '📸'; this.eGui.style.cursor='pointer';
                            this.eGui.onclick = () => {
                                let m = document.createElement('div');
                                Object.assign(m.style, {position:'fixed', zIndex:'9999', left:0, top:0, width:'100%', height:'100%', background:'rgba(0,0,0,0.85)', display:'flex', justifyContent:'center', alignItems:'center'});
                                let i = document.createElement('img'); i.src = params.value; i.style.maxHeight='90%';
                                m.appendChild(i); m.onclick = () => document.body.removeChild(m);
                                document.body.appendChild(m);
                            };
                            this.eGui.appendChild(btn);
                        } else { this.eGui.innerHTML = '➖'; }
                    }
                    getGui() { return this.eGui; }
                }
            """))
            AgGrid(df_final, gridOptions=gb.build(), allow_unsafe_jscode=True, theme='alpine', height=500)
