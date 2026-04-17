import streamlit as st
import pandas as pd
import gspread
import os
import urllib.parse
import json
import requests
import re
from datetime import datetime, timedelta, timezone
from streamlit_autorefresh import st_autorefresh
from google.oauth2.credentials import Credentials

FUSO_BR = timezone(timedelta(hours=-3))
LOGO_IGO = "https://i.postimg.cc/x84nnjjq/IGO-LOGO.png"

# =======================================================
# 🎨 1. CONFIGURAÇÃO DA PÁGINA E CSS BASE
# =======================================================
st.set_page_config(page_title="Monitoramento IGO Logística", layout="wide", page_icon="🚚", initial_sidebar_state="expanded")
st_autorefresh(interval=60000, limit=None, key="refresh_timer")

st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { transition: background-color 0.3s ease; font-family: 'Inter', sans-serif; }
    
    [data-testid="stSidebar"], [data-testid="stSidebar"] > div:first-child { 
        background-color: #ffffff !important; 
    }
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] label, [data-testid="stSidebar"] h3 {
        color: #1e293b !important;
    }

    [data-testid="stSidebar"] [data-testid="stForm"] {
        background-color: #f8fafc !important; 
        border: 1px solid #e2e8f0 !important; 
        border-radius: 12px !important; 
        padding: 15px !important; 
    }
    [data-testid="stSidebar"] input, [data-testid="stSidebar"] textarea {
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important; 
        border-radius: 6px !important;
        color: #1e293b !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important; 
    }
    [data-testid="stSidebar"] input:focus, [data-testid="stSidebar"] textarea:focus {
        border-color: #3b82f6 !important;
        box-shadow: 0 0 0 1px #3b82f6 !important;
    }

    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {background-color: transparent !important;}
    .block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; padding-left: 2rem !important; padding-right: 2rem !important; }
    
    div.st-key-kpi_total button, div.st-key-kpi_entregue button, div.st-key-kpi_frus button, div.st-key-kpi_atra button, div.st-key-kpi_hoje button, div.st-key-kpi_aguardando button {
        height: 75px !important; border-radius: 10px !important; border: none !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important; transition: all 0.2s ease !important;
        display: flex !important; justify-content: center !important; align-items: center !important;
    }
    div.st-key-kpi_total button { background: linear-gradient(135deg, #1E3A8A 0%, #3B82F6 100%) !important; }
    div.st-key-kpi_entregue button { background: linear-gradient(135deg, #064E3B 0%, #10B981 100%) !important; }
    div.st-key-kpi_frus button { background: linear-gradient(135deg, #9A3412 0%, #F59E0B 100%) !important; }
    div.st-key-kpi_atra button { background: linear-gradient(135deg, #7F1D1D 0%, #EF4444 100%) !important; }
    div.st-key-kpi_hoje button { background: linear-gradient(135deg, #4C1D95 0%, #8B5CF6 100%) !important; }
    div.st-key-kpi_aguardando button { background: linear-gradient(135deg, #F59E0B 0%, #D97706 100%) !important; }
    
    div.st-key-kpi_total button p, div.st-key-kpi_entregue button p, div.st-key-kpi_frus button p, div.st-key-kpi_atra button p, div.st-key-kpi_hoje button p, div.st-key-kpi_aguardando button p { 
        font-weight: 800 !important; font-size: 14px !important; color: #ffffff !important; margin: 0 !important; text-align: center !important;
    }
    .header-container { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 15px; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px; }
    .sync-status { font-size: 12px; color: #10B981; font-weight: 700; }
    </style>
    """, unsafe_allow_html=True)

CLIENTES_CONFIG = {
    "GRALAB": {"senha": "123", "logo": "https://cdn.awsli.com.br/2702/2702264/logo/gralab-rbuogsxve7.png", "filtro": "GRALAB"},
    "IGO_LOGISTICA": {"senha": "admin", "logo": LOGO_IGO, "filtro": "TODOS"},
    "LOGISTICA.LABEST": {"senha": "123", "logo": "https://i.postimg.cc/k4yvNpH0/labest.png", "filtro": "LABEST"},
    "SYNVIA": {"senha": "123", "logo": LOGO_IGO, "filtro": "SYNVIA"},
    "LOGISTICA.BAT": {"senha": "123", "logo": "https://i.postimg.cc/5NBvXyv7/souza-cruz.png", "filtro": "SOUZA CRUZ"}
}

# =======================================================
# 🔗 2. MOTOR DE DADOS
# =======================================================
@st.cache_resource
def conectar_banco_seguro():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        token_str = os.environ.get("google_token_json")
        if not token_str:
            try: token_str = st.secrets.get("google_token_json")
            except: pass
        if not token_str: return None
        token_info = json.loads(token_str)
        creds = Credentials.from_authorized_user_info(token_info, scopes=scopes)
        return gspread.authorize(creds)
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
            df = df.loc[:, ~df.columns.duplicated()] 
            
            # 🔥 CORREÇÃO: ADICIONAMOS A LÓGICA INTELIGENTE DO CCO AQUI 🔥
            try:
                aba_app = planilha.worksheet("App_Tarefas")
                dados_app = aba_app.get_all_values()
                if len(dados_app) > 1:
                    df_app = pd.DataFrame(dados_app[1:], columns=dados_app[0])
                    df_app.columns = [str(c).upper().strip().replace(' ', '').replace('?', '') for c in df_app.columns]
                    
                    cols_to_extract = ['PEDIDO']
                    if 'STATUS' in df_app.columns: cols_to_extract.append('STATUS')
                    if 'OBSERVACOES' in df_app.columns: cols_to_extract.append('OBSERVACOES')
                    if 'FOTO' in df_app.columns: cols_to_extract.append('FOTO')
                    if 'DATA' in df_app.columns: cols_to_extract.append('DATA')
                    if 'DATA_ENTREGA' in df_app.columns: cols_to_extract.append('DATA_ENTREGA')
                    
                    col_nome = None
                    for c in ['DETALHES', 'RECEBEDOR', 'CONTATO', 'NOME', 'PESSOA', 'INFORMANTE']:
                        if c in df_app.columns:
                            cols_to_extract.append(c)
                            col_nome = c
                            break
                            
                    df_app_clean = df_app[cols_to_extract].copy()
                    
                    rename_dict = {'STATUS': 'A_ST', 'OBSERVACOES': 'A_OB', 'FOTO': 'A_FO', 'DATA': 'A_DT', 'DATA_ENTREGA': 'A_DT_ENTREGA'}
                    if col_nome: rename_dict[col_nome] = 'A_CONTATO'
                    
                    df_app_clean.rename(columns=rename_dict, inplace=True)
                    
                    # 🔥 INTELIGÊNCIA DE ROMANEIOS NO PORTAL 🔥
                    rom_mask = df_app_clean['PEDIDO'].str.startswith('ROM-', na=False)
                    rom_dict = df_app_clean[rom_mask].set_index('PEDIDO').to_dict('index')
                    
                    df_app_clean.drop_duplicates(subset=['PEDIDO'], keep='last', inplace=True)
                    
                    df['PEDIDO'] = df['PEDIDO'].astype(str).str.strip()
                    df = pd.merge(df, df_app_clean, on='PEDIDO', how='left')
                    
                    if 'A_FO' in df.columns:
                        df['FOTO'] = df.apply(lambda r: r['A_FO'] if str(r.get('A_FO','')).strip() and str(r.get('A_FO','')).upper() != 'NAN' else r.get('FOTO',''), axis=1)

                    # Simula a inteligência do get_true_status do C.C.O.
                    def get_true_status_portal(row):
                        s_db = str(row.get('STATUS', '')).strip().upper()
                        s_app = str(row.get('A_ST', '')).strip().upper()
                        rom_id = str(row.get('ROMANEIO', '')).strip()
                        
                        if rom_id in rom_dict:
                            s_rom = str(rom_dict[rom_id].get('A_ST', '')).strip().upper()
                            if s_rom in ['ENTREGUE', 'FRUSTRADA', 'PROBLEMA', 'CANCELADO']: return s_rom
                            
                        if s_db in ['ENTREGUE', 'CANCELADO', 'FRUSTRADA', 'PROBLEMA']: return s_db
                        if s_app in ['ENTREGUE', 'CANCELADO', 'FRUSTRADA', 'PROBLEMA']: return s_app
                        if s_db in ['EM ROTA DE ENTREGA', 'CONFERIDO', 'COLETADO']: return s_db
                        if s_app == 'COLETADO': return s_app
                        if s_app and s_app != 'NAN': return s_app
                        return s_db
                    
                    df['STATUS_RESOLVIDO'] = df.apply(get_true_status_portal, axis=1)
                    
                    # Resolve data de entrega para exibir no Portal
                    def get_true_data_entrega_portal(row):
                        s_final = str(row.get('STATUS_RESOLVIDO', '')).upper()
                        if s_final not in ['ENTREGUE', 'FRUSTRADA']: return "-"
                        
                        d_db = str(row.get('DATA_ENTREGA', '')).strip()
                        rom_id = str(row.get('ROMANEIO', '')).strip()
                        
                        if rom_id in rom_dict:
                            d_rom = str(rom_dict[rom_id].get('A_DT_ENTREGA', '')).strip()
                            if d_rom and d_rom.upper() != 'NAN': return d_rom
                        
                        if 'A_DT_ENTREGA' in row:
                            d_app = str(row.get('A_DT_ENTREGA', '')).strip()
                            if d_app and d_app.upper() != 'NAN': return d_app
                            
                        return d_db if d_db.upper() != 'NAN' else "-"
                        
                    df['DATA_EFETIVA'] = df.apply(get_true_data_entrega_portal, axis=1)
            except Exception as e:
                print(f"Erro AppSheet: {e}")
                df['STATUS_RESOLVIDO'] = df['STATUS'] # Fallback
                df['DATA_EFETIVA'] = "-"
                
            if 'DATA' in df.columns: 
                df['DATA_OBJ'] = pd.to_datetime(df['DATA'], format='%d/%m/%Y', errors='coerce').dt.date
            return df
    except: return pd.DataFrame()

@st.cache_data(ttl=60)
def carregar_base_locais():
    try:
        gc = conectar_banco_seguro()
        if not gc: return pd.DataFrame()
        planilha = gc.open("DB_IGO_Logistica")
        aba = planilha.worksheet("Base_Clientes_Locais")
        dados = aba.get_all_values()
        if len(dados) > 1:
            df = pd.DataFrame(dados[1:], columns=dados[0])
            return df[df['STATUS'].str.upper() == 'ATIVO']
        return pd.DataFrame()
    except: return pd.DataFrame()

def obter_proximo_id(df):
    if df is None or df.empty or 'PEDIDO' not in df.columns: return 1
    try:
        nums = df['PEDIDO'].astype(str).str.extract(r'^(\d+)')[0].dropna().astype(int)
        return int(nums.max() + 1) if not nums.empty else 1
    except: return 1

def enviar_whatsapp_zapi_cliente(telefone_destino, texto_mensagem):
    INSTANCIA = "3F14E62A63D2B28DC385B20DE66F3711" 
    TOKEN = "2321563615C4242CB6031504"          
    CLIENT_TOKEN = "Ffaa43dcff1e14f0e985c91e92b24ed89S" 
    tel_limpo = re.sub(r'\D', '', str(telefone_destino))
    if not tel_limpo.startswith('55') and len(tel_limpo) in [10, 11]: tel_limpo = '55' + tel_limpo
    url = f"https://api.z-api.io/instances/{INSTANCIA}/token/{TOKEN}/send-text"
    payload = {"phone": tel_limpo, "message": texto_mensagem}
    headers = {"Accept": "application/json", "Content-Type": "application/json", "Client-Token": CLIENT_TOKEN}
    try: requests.post(url, json=payload, headers=headers); return True
    except: return False

if 'logado' not in st.session_state: st.session_state.logado = False
if 'filtro_kpi' not in st.session_state: st.session_state.filtro_kpi = "TODOS"

# =======================================================
# 🔐 3. LOGIN / PAINEL
# =======================================================
if not st.session_state.logado:
    st.markdown("""<style> [data-testid="stAppViewContainer"] { background-color: #ffffff !important; } </style>""", unsafe_allow_html=True)
    _, c2, _ = st.columns([1, 1.2, 1])
    with c2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        with st.container(border=True):
            col_logo1, col_logo2, col_logo3 = st.columns([1, 2, 1])
            with col_logo2: st.image("https://i.postimg.cc/x84nnjjq/IGO-LOGO.png", use_container_width=True)
            st.markdown("<h3 style='text-align: center; color: #1e293b; margin-top: -10px; margin-bottom: 20px;'>Portal do Cliente</h3>", unsafe_allow_html=True)
            u = st.text_input("👤 Usuário").upper().strip()
            s = st.text_input("🔒 Senha", type="password")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🚀 Acessar Sistema", type="primary", use_container_width=True):
                if u in CLIENTES_CONFIG and s == CLIENTES_CONFIG[u]["senha"]:
                    st.session_state.logado = True
                    st.session_state.cliente = u
                    st.rerun()
                else: st.error("❌ Credenciais Incorretas")
else:
    conf = CLIENTES_CONFIG[st.session_state.cliente]
    hoje_br = datetime.now(FUSO_BR).date()
    nome_tomador_oficial = conf["filtro"] if conf["filtro"] != "TODOS" else "MATRIZ IGO"
    
    with st.sidebar:
        col_img1, col_img2, col_img3 = st.columns([1, 3, 1])
        with col_img2:
            try: st.image(conf["logo"], use_container_width=True)
            except: st.markdown(f"<h3 style='text-align: center;'>{st.session_state.cliente}</h3>", unsafe_allow_html=True)
            
        st.divider()
        datas_sel = st.date_input("🗓️ Período:", value=(hoje_br - timedelta(days=7), hoje_br), format="DD/MM/YYYY")
        holder_cidades = st.empty()
        
        st.divider()
        st.markdown("### 🎧 Chamado C.C.O.")
        with st.form("form_chamado_zap"):
            pedido_chamado = st.text_input("Número do Pedido (Opcional):")
            msg_chamado = st.text_area("Sua Mensagem:", placeholder="Ex: Preciso de urgência neste pedido...")
            if st.form_submit_button("Enviar Solicitação", use_container_width=True):
                if msg_chamado.strip() == "": st.error("Digite uma mensagem!")
                else:
                    with st.spinner("Enviando para a base..."):
                        texto_final = f"🚨 *CHAMADO PRIORITÁRIO - PORTAL* 🚨\n\n🏢 *Cliente:* {nome_tomador_oficial}\n"
                        if pedido_chamado: texto_final += f"📦 *Pedido:* {pedido_chamado}\n"
                        texto_final += f"💬 *Mensagem:* {msg_chamado}\n\n⏳ _Enviado via Portal Corporativo_"
                        if enviar_whatsapp_zapi_cliente("5511947996371", texto_final): st.success("✅ Chamado enviado!")
                        else: st.error("❌ Erro de comunicação.")
        
        st.divider()
        holder_exportar = st.empty()
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        if st.button("🚪 Sair do Sistema", use_container_width=True): 
            st.session_state.logado = False; st.rerun()
            
    st.markdown(f"""<div class="header-container"><h2 style="margin:0; font-weight:900; font-size:22px;">Monitoramento Logístico | {st.session_state.cliente}</h2><div class='sync-status'>🟢 Online: {datetime.now(FUSO_BR).strftime('%H:%M')}</div></div>""", unsafe_allow_html=True)

    df_raw = carregar_dados_nuvem()
    
    if df_raw.empty:
        st.info("Aguardando novas informações do C.C.O na base de dados...")
    else:
        if conf["filtro"] == "TODOS": df_cliente = df_raw.copy()
        else: df_cliente = df_raw[df_raw['TOMADOR'].str.upper().str.strip() == conf["filtro"]].copy()

        tab_grid, tab_solicitar = st.tabs(["📊 Meus Pedidos e Monitoramento", "➕ Solicitar Nova Coleta"])

        with tab_grid:
            if df_cliente.empty:
                st.warning(f"Nenhum pedido registrado no sistema sob a titularidade '{conf['filtro']}'.")
            else:
                with holder_cidades:
                    cidades_sel = st.multiselect("📍 Cidades:", sorted(df_cliente['CIDADE'].dropna().unique().tolist()))

                # 🔥 CORREÇÃO: AGORA O PORTAL LÊ O STATUS RESOLVIDO COM INTELIGÊNCIA 🔥
                def get_st(row):
                    s = str(row.get('STATUS_RESOLVIDO', row.get('STATUS', ''))).strip().upper()
                    
                    if 'AGUARDANDO' in s: return '🔒 Aguardando Aprovação' 
                    if 'RECUSA' in s: return '🚫 Solicitação Recusada'   
                    if 'ENTREGUE' in s: return '✅ Entregue'
                    if 'COLETADO' in s: return '📦 Coletado'
                    if 'ROTA DE COLETA' in s: return '🚐 Rota de Coleta'
                    if 'ROTA' in s: return '🚚 Em Rota de Entrega'
                    if 'CONFERIDO' in s: return '☑️ Conferido'
                    if 'FRUSTRADA' in s: return '❌ Frustrada'
                    if 'CANCELADO' in s: return '🚫 Cancelado'
                    if 'PROBLEMA' in s: return '🚨 Problema'
                    return '⏳ Pendente'
                
                def get_detalhes(row):
                    obs_master = str(row.get('OBSERVACOES', '')).strip()
                    obs_app = str(row.get('A_OB', '')).strip()
                    contato = str(row.get('A_CONTATO', '')).strip()
                    
                    obs_final = obs_app if (obs_app and obs_app.upper() != 'NAN') else obs_master
                    
                    if obs_final.upper() == 'NAN': obs_final = ""
                    if contato.upper() == 'NAN': contato = ""
                    
                    if not obs_final and not contato: return "-"
                    
                    if obs_final and contato and obs_final.upper() != contato.upper():
                        return f"{obs_final} (Informante: {contato})"
                    
                    return obs_final if obs_final else f"Informante: {contato}"

                df_cliente['STATUS_DISPLAY'] = df_cliente.apply(get_st, axis=1)
                df_cliente['DETALHES'] = df_cliente.apply(get_detalhes, axis=1)

                df_f = df_cliente.copy()
                if isinstance(datas_sel, (tuple, list)) and len(datas_sel) == 2:
                    df_f = df_f[(df_f['DATA_OBJ'] >= datas_sel[0]) & (df_f['DATA_OBJ'] <= datas_sel[1])]
                if cidades_sel: df_f = df_f[df_f['CIDADE'].isin(cidades_sel)]

                df_f['DT_LIMITE_OBJ'] = pd.to_datetime(df_f['DATA_LIMITE'], format='%d/%m/%Y', errors='coerce').dt.date
                
                mask_atrasado = (
                    (~df_f['STATUS_DISPLAY'].str.contains('Entregue|Frustrada|Cancelado|Aguardando|Recusada', case=False, na=False)) &
                    (df_f['DT_LIMITE_OBJ'] < hoje_br) &
                    (df_f['DT_LIMITE_OBJ'].notnull())
                )
                df_atrasados_only = df_f[mask_atrasado]

                ck = st.columns(6)
                def set_kpi(v): st.session_state.filtro_kpi = v
                n_tot_k = len(df_f)
                n_ent_k = len(df_f[df_f['STATUS_DISPLAY'].str.contains('Entregue')])
                n_fru_k = len(df_f[df_f['STATUS_DISPLAY'].str.contains('Frustrada')])
                n_atr_k = len(df_atrasados_only)
                n_agu_k = len(df_f[df_f['STATUS_DISPLAY'].str.contains('Aguardando')])
                n_hoje_k = len(df_f[df_f['DATA_OBJ'] == hoje_br])
                
                with ck[0]: st.button(f"📦 TOTAL\n\n{n_tot_k}", key="kpi_total", use_container_width=True, on_click=set_kpi, args=("TODOS",))
                with ck[1]: st.button(f"✅ ENTREGUES\n\n{n_ent_k}", key="kpi_entregue", use_container_width=True, on_click=set_kpi, args=("ENTREGUE",))
                with ck[2]: st.button(f"❌ FRUSTRADAS\n\n{n_fru_k}", key="kpi_frus", use_container_width=True, on_click=set_kpi, args=("FRUSTRADA",))
                with ck[3]: st.button(f"🚨 ATRASADOS\n\n{n_atr_k}", key="kpi_atra", use_container_width=True, on_click=set_kpi, args=("ATRASADO",))
                with ck[4]: st.button(f"🔒 AGUARDANDO\n\n{n_agu_k}", key="kpi_aguardando", use_container_width=True, on_click=set_kpi, args=("Aguardando",))
                with ck[5]: st.button(f"📅 HOJE\n\n{n_hoje_k}", key="kpi_hoje", use_container_width=True, on_click=set_kpi, args=("HOJE",))

                st.markdown("<br>🎯 **Progresso de Hoje**", unsafe_allow_html=True)
                df_h = df_f[df_f['DATA_OBJ'] == hoje_br]
                if not df_h.empty:
                    tx = len(df_h[df_h['STATUS_DISPLAY'].str.contains('Entregue|Frustrada|Cancelado|Recusada')]) / len(df_h)
                    st.progress(tx)
                else: st.info("Nenhum pedido despachado para hoje.")

                st.markdown("<br>", unsafe_allow_html=True)
                busca = st.text_input("🔎 Busca Rápida:", placeholder="Buscar por pedido, laboratório, cidade...")
                
                df_grid = df_f.copy()
                if st.session_state.filtro_kpi != "TODOS":
                    if st.session_state.filtro_kpi == "HOJE": df_grid = df_grid[df_grid['DATA_OBJ'] == hoje_br]
                    elif st.session_state.filtro_kpi == "ATRASADO": df_grid = df_atrasados_only.copy()
                    else: df_grid = df_grid[df_grid['STATUS_DISPLAY'].str.contains(st.session_state.filtro_kpi, case=False)]
                
                if busca: df_grid = df_grid[df_grid.astype(str).apply(lambda x: x.str.lower().str.contains(busca.lower())).any(axis=1)]

                if not df_grid.empty:
                    cols = ['DATA', 'PEDIDO', 'STATUS_DISPLAY', 'DATA_EFETIVA', 'LABORATORIO', 'CIDADE', 'DATA_LIMITE', 'DETALHES', 'FOTO']
                    df_final = df_grid[[c for c in cols if c in df_grid.columns]].copy()
                    
                    def tratar_foto(x):
                        xs = str(x).strip()
                        if not xs or xs.upper() in ['NAN', 'NONE']: return ""
                        if xs.startswith("http"): return xs
                        return f"https://www.appsheet.com/template/gettablefileurl?appName=APPIGOLOGISTICA-153047553&tableName=App_Tarefas&fileName={xs}"
                    
                    df_final['COMPROVANTE'] = df_final['FOTO'].apply(tratar_foto)

                    colunas_ordenadas = ['DATA', 'PEDIDO', 'STATUS_DISPLAY', 'LABORATORIO', 'CIDADE', 'DATA_LIMITE', 'DATA_EFETIVA', 'COMPROVANTE', 'DETALHES']
                    
                    for col in df_final.columns: df_final[col] = df_final[col].astype(str).replace(["nan", "NaN", "None", "none", "<NA>", "NaT"], "")

                    st.data_editor(
                        df_final,
                        column_config={
                            "DATA": st.column_config.TextColumn("DATA PEDIDO"),
                            "PEDIDO": st.column_config.TextColumn("PEDIDO"),
                            "STATUS_DISPLAY": st.column_config.TextColumn("STATUS"),
                            "DATA_EFETIVA": st.column_config.TextColumn("DATA ENTREGA"),
                            "LABORATORIO": st.column_config.TextColumn("PCL"),
                            "CIDADE": st.column_config.TextColumn("CIDADE"),
                            "DATA_LIMITE": st.column_config.TextColumn("PREVISÃO"),
                            "COMPROVANTE": st.column_config.LinkColumn("COMPROVANTE", display_text="🔎 Abrir Foto"),
                            "DETALHES": st.column_config.TextColumn("DETALHES / MOTIVO", width="large")
                        },
                        column_order=colunas_ordenadas, disabled=True, hide_index=True, use_container_width=True, height=500
                    )

                    with holder_exportar:
                        csv = df_grid.to_csv(index=False, sep=';').encode('utf-8-sig')
                        st.download_button("📥 Exportar Planilha (CSV)", data=csv, file_name=f"Relatorio_{st.session_state.cliente}.csv", use_container_width=True)

        # 🔥 NOVO MÓDULO: AUTOATENDIMENTO DE COLETA 🔥
        with tab_solicitar:
            st.markdown("### ➕ Nova Solicitação de Coleta")
            st.markdown("<p style='color: #64748B;'>Escolha o ponto de coleta desejado abaixo. A data mínima para agendamento é o próximo dia útil.</p>", unsafe_allow_html=True)
            
            df_locais = carregar_base_locais()
            if df_locais.empty:
                st.warning("O banco de dados de locais de coleta ainda não foi sincronizado ou está vazio.")
            else:
                df_cli_locais = df_locais[df_locais['TOMADOR'].str.upper().str.strip() == nome_tomador_oficial.upper().strip()]
                if df_cli_locais.empty:
                    st.warning(f"Nenhum Ponto de Coleta cadastrado no momento para a empresa {nome_tomador_oficial}.")
                else:
                    with st.container(border=True):
                        with st.form("form_nova_coleta", clear_on_submit=True):
                            lista_labs = sorted(df_cli_locais['LABORATORIO'].unique().tolist())
                            lab_sel = st.selectbox("📍 Selecione o Ponto de Coleta (Laboratório):", ["Selecione..."] + lista_labs)
                            
                            c1, c2 = st.columns(2)
                            amanha = hoje_br + timedelta(days=1)
                            data_coleta = c1.date_input("📅 Data Desejada para Coleta:", min_value=amanha, value=amanha, format="DD/MM/YYYY")
                            obs = st.text_area("📝 Observações / Instruções (Opcional):", placeholder="Ex: Procurar por Fulano, coletar na recepção...", height=100)

                            if st.form_submit_button("🚀 Enviar Solicitação ao C.C.O.", type="primary", use_container_width=True):
                                if lab_sel == "Selecione...":
                                    st.error("⚠️ Por favor, selecione um Ponto de Coleta válido na lista.")
                                else:
                                    with st.spinner("Registrando pedido seguro e notificando o C.C.O..."):
                                        try:
                                            local_data = df_cli_locais[df_cli_locais['LABORATORIO'] == lab_sel].iloc[0]
                                            
                                            gc = conectar_banco_seguro()
                                            planilha = gc.open("DB_IGO_Logistica")
                                            aba_m = planilha.worksheet("Memoria_Sistema")
                                            
                                            dados_m = aba_m.get_all_values()
                                            df_m_temp = pd.DataFrame(dados_m[1:], columns=dados_m[0])
                                            prox_id = obter_proximo_id(df_m_temp)
                                            
                                            nova_linha_dict = {
                                                'DATA': data_coleta.strftime("%d/%m/%Y"),
                                                'PEDIDO': str(prox_id),
                                                'TOMADOR': nome_tomador_oficial,
                                                'LABORATORIO': local_data['LABORATORIO'],
                                                'CNPJ': local_data.get('CNPJ', ''),
                                                'ENDERECO': local_data.get('ENDERECO', ''),
                                                'NUMERO': local_data.get('NUMERO', ''),
                                                'BAIRRO': local_data.get('BAIRRO', ''),
                                                'CIDADE': local_data.get('CIDADE', ''),
                                                'UF': local_data.get('UF', ''),
                                                'CEP': local_data.get('CEP', ''),
                                                'STATUS': 'AGUARDANDO APROVAÇÃO',
                                                'OBSERVACOES': obs
                                            }
                                            
                                            cabecalhos = dados_m[0]
                                            linha_append = [nova_linha_dict.get(c, "") for c in cabecalhos]
                                            aba_m.append_row(linha_append, value_input_option='USER_ENTERED')
                                            
                                            texto_zap = f"🔔 *NOVA SOLICITAÇÃO DE COLETA* 🔔\n\n"
                                            texto_zap += f"🏢 *Cliente:* {nome_tomador_oficial}\n"
                                            texto_zap += f"🔬 *Local:* {local_data['LABORATORIO']}\n"
                                            texto_zap += f"📍 *Cidade:* {local_data.get('CIDADE', '')} - {local_data.get('UF', '')}\n"
                                            texto_zap += f"📅 *Data Desejada:* {data_coleta.strftime('%d/%m/%Y')}\n"
                                            texto_zap += f"📦 *ID do Pedido:* {prox_id}\n\n"
                                            texto_zap += f"Acesse o painel do C.C.O para aprovar ou recusar a rota."
                                            
                                            enviar_whatsapp_zapi_cliente("5511947996371", texto_zap)
                                            
                                            st.success(f"🎉 Sucesso! Pedido #{prox_id} criado e aguardando aprovação do C.C.O.")
                                            carregar_dados_nuvem.clear()
                                        except Exception as e:
                                            st.error(f"Erro ao processar solicitação: {e}")
