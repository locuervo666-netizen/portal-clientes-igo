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
    
    /* FORÇANDO FUNDO BRANCO NA SIDEBAR E PROTEGENDO A COR DO TEXTO */
    [data-testid="stSidebar"], [data-testid="stSidebar"] > div:first-child { 
        background-color: #ffffff !important; 
    }
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] label, [data-testid="stSidebar"] h3 {
        color: #1e293b !important;
    }

    /* 🔥 MELHORIA DE CONTRASTE NO FORMULÁRIO DE CHAMADO 🔥 */
    [data-testid="stSidebar"] [data-testid="stForm"] {
        background-color: #f8fafc !important; /* Fundo cinza clarinho */
        border: 1px solid #cbd5e1 !important; /* Borda mais visível */
        border-radius: 8px !important;
    }
    [data-testid="stSidebar"] input, [data-testid="stSidebar"] textarea {
        background-color: #ffffff !important;
        border: 1px solid #94a3b8 !important; /* Bordas das caixas mais escuras */
        color: #1e293b !important;
    }
    [data-testid="stSidebar"] input:focus, [data-testid="stSidebar"] textarea:focus {
        border-color: #3b82f6 !important;
        box-shadow: 0 0 0 1px #3b82f6 !important;
    }

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
    "LOGISTICA.LABEST": {"senha": "123", "logo": "logo_labest.png", "filtro": "LABEST"},
    "SYNVIA": {"senha": "123", "logo": LOGO_IGO, "filtro": "SYNVIA"},
    "LOGISTICA.BAT": {"senha": "123", "logo": "souza cruz.png", "filtro": "SOUZA CRUZ"}
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
        if not token_str:
            st.error("⚠️ Senha do Google não detectada no Render.")
            return None
        token_info = json.loads(token_str)
        creds = Credentials.from_authorized_user_info(token_info, scopes=scopes)
        gc = gspread.authorize(creds)
        return gc
    except Exception as e:
        st.error(f"Erro Crítico de Conexão: {e}")
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
            df = df.loc[:, ~df.columns.duplicated()] 
            
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
                    
                    df_app_clean = df_app[cols_to_extract].copy()
                    rename_map = {'STATUS': 'A_ST', 'OBSERVACOES': 'A_OB', 'FOTO': 'A_FO', 'DATA': 'A_DT'}
                    df_app_clean.rename(columns=rename_map, inplace=True)
                    df_app_clean['PEDIDO'] = df_app_clean['PEDIDO'].astype(str).str.strip()
                    df_app_clean.drop_duplicates(subset=['PEDIDO'], keep='last', inplace=True)
                    
                    df['PEDIDO'] = df['PEDIDO'].astype(str).str.strip()
                    df = pd.merge(df, df_app_clean, on='PEDIDO', how='left')
                    
                    if 'A_FO' in df.columns:
                        df['FOTO'] = df.apply(lambda r: r['A_FO'] if str(r.get('A_FO','')).strip() and str(r.get('A_FO','')).upper() != 'NAN' else r.get('FOTO',''), axis=1)
            except Exception: pass
                
            if 'DATA' in df.columns: 
                df['DATA_OBJ'] = pd.to_datetime(df['DATA'], format='%d/%m/%Y', errors='coerce').dt.date
            return df
    except Exception: return pd.DataFrame()

# FUNÇÃO Z-API PARA O PORTAL DO CLIENTE
def enviar_whatsapp_zapi_cliente(telefone_destino, texto_mensagem):
    INSTANCIA = "3F14E62A63D2B28DC385B20DE66F3711" 
    TOKEN = "2321563615C4242CB6031504"          
    CLIENT_TOKEN = "Ffaa43dcff1e14f0e985c91e92b24ed89S" 
    tel_limpo = re.sub(r'\D', '', str(telefone_destino))
    if not tel_limpo.startswith('55') and len(tel_limpo) in [10, 11]: tel_limpo = '55' + tel_limpo
    url = f"https://api.z-api.io/instances/{INSTANCIA}/token/{TOKEN}/send-text"
    payload = {"phone": tel_limpo, "message": texto_mensagem}
    headers = {"Accept": "application/json", "Content-Type": "application/json", "Client-Token": CLIENT_TOKEN}
    try:
        response = requests.post(url, json=payload, headers=headers)
        return response.status_code in [200, 201]
    except Exception: return False


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
            with col_logo2:
                st.image("https://i.postimg.cc/x84nnjjq/IGO-LOGO.png", use_container_width=True)
            
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
    
    with st.sidebar:
        try: st.image(conf["logo"], width=160)
        except: st.markdown(f"### {st.session_state.cliente}")
        st.divider()
        datas_sel = st.date_input("🗓️ Período:", value=(hoje_br - timedelta(days=7), hoje_br), format="DD/MM/YYYY")
        holder_cidades = st.empty()
        
        # --- 🚀 SUPORTE DIRETO VIA API WHATSAPP ---
        st.divider()
        st.markdown("### 🎧 Chamado C.C.O.")
        
        with st.form("form_chamado_zap"):
            pedido_chamado = st.text_input("Número do Pedido (Opcional):")
            msg_chamado = st.text_area("Sua Mensagem:", placeholder="Ex: Preciso de urgência neste pedido...")
            btn_enviar_chamado = st.form_submit_button("Enviar Solicitação", use_container_width=True)
            
            if btn_enviar_chamado:
                if msg_chamado.strip() == "":
                    st.error("Digite uma mensagem!")
                else:
                    with st.spinner("Enviando para a base..."):
                        numero_cco = "5511947996371" # <- TELEFONE CCO OFICIAL ATUALIZADO
                        
                        # Pegando o nome amigável do tomador configurado na linha 83
                        nome_tomador = conf["filtro"] if conf["filtro"] != "TODOS" else "MATRIZ IGO LOGÍSTICA"
                        
                        texto_final = f"🚨 *CHAMADO PRIORITÁRIO - PORTAL* 🚨\n\n"
                        texto_final += f"🏢 *Cliente:* {nome_tomador}\n"
                        if pedido_chamado:
                            texto_final += f"📦 *Pedido:* {pedido_chamado}\n"
                        texto_final += f"💬 *Mensagem:* {msg_chamado}\n\n"
                        texto_final += f"⏳ _Enviado via Portal Corporativo_"
                        
                        if enviar_whatsapp_zapi_cliente(numero_cco, texto_final):
                            st.success("✅ Chamado enviado com sucesso!")
                        else:
                            st.error("❌ Erro de comunicação com o C.C.O.")
        
        st.divider()
        holder_exportar = st.empty()
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        if st.button("🚪 Sair do Sistema", use_container_width=True): 
            st.session_state.logado = False
            st.rerun()
            
    st.markdown(f"""<div class="header-container"><h2 style="margin:0; font-weight:900; font-size:22px;">Monitoramento Logístico | {st.session_state.cliente}</h2><div class='sync-status'>🟢 Online: {datetime.now(FUSO_BR).strftime('%H:%M')}</div></div>""", unsafe_allow_html=True)

    df_raw = carregar_dados_nuvem()
    
    if df_raw.empty:
        st.info("Aguardando novas informações do C.C.O na base de dados...")
    else:
        if conf["filtro"] == "TODOS": df_cliente = df_raw.copy()
        else:
            if 'TOMADOR' in df_raw.columns:
                df_cliente = df_raw[df_raw['TOMADOR'].str.upper().str.strip() == conf["filtro"]].copy()
            else: df_cliente = pd.DataFrame()
                
        if df_cliente.empty:
            st.warning(f"Nenhum pedido ou lote foi registrado no sistema sob a titularidade '{conf['filtro']}' até o momento.")
        else:
            with holder_cidades:
                cidades_sel = st.multiselect("📍 Cidades:", sorted(df_cliente['CIDADE'].dropna().unique().tolist()))

            def get_st(row):
                st_master = str(row.get('STATUS', '')).strip().upper()
                st_app = str(row.get('A_ST', '')).strip().upper()
                if st_master in ['', 'NAN', 'NONE', 'PENDENTE'] and st_app not in ['', 'NAN', 'NONE']: s = st_app
                else: s = st_master
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
                if obs_master and obs_master.upper() != 'NAN': return obs_master
                if obs_app and obs_app.upper() != 'NAN': return obs_app
                return "-"

            def tratar_link_foto(x):
                x_str = str(x).strip()
                if not x_str or x_str.upper() in ['NAN', 'NONE']: return ""
                if x_str.startswith("http"): return x_str 
                return f"https://www.appsheet.com/template/gettablefileurl?appName=APPIGOLOGISTICA-153047553&tableName=App_Tarefas&fileName={x_str}"

            df_cliente['STATUS_DISPLAY'] = df_cliente.apply(get_st, axis=1)
            df_cliente['DETALHES'] = df_cliente.apply(get_detalhes, axis=1)
            df_cliente['FOTO_URL'] = df_cliente['FOTO'].apply(tratar_link_foto)

            df_f = df_cliente.copy()
            if isinstance(datas_sel, (tuple, list)) and len(datas_sel) == 2:
                df_f = df_f[(df_f['DATA_OBJ'] >= datas_sel[0]) & (df_f['DATA_OBJ'] <= datas_sel[1])]
            
            if cidades_sel: df_f = df_f[df_f['CIDADE'].isin(cidades_sel)]

            df_f['DT_LIMITE_OBJ'] = pd.to_datetime(df_f['DATA_LIMITE'], format='%d/%m/%Y', errors='coerce').dt.date
            
            mask_atrasado = (
                (~df_f['STATUS_DISPLAY'].str.contains('Entregue|Frustrada|Cancelado', case=False, na=False)) &
                (df_f['DT_LIMITE_OBJ'] < hoje_br) &
                (df_f['DT_LIMITE_OBJ'].notnull())
            )
            df_atrasados_only = df_f[mask_atrasado]
            n_atr_k = len(df_atrasados_only)

            ck = st.columns(5)
            def set_kpi(v): st.session_state.filtro_kpi = v
            n_tot_k, n_ent_k, n_fru_k = len(df_f), len(df_f[df_f['STATUS_DISPLAY'].str.contains('Entregue')]), len(df_f[df_f['STATUS_DISPLAY'].str.contains('Frustrada')])
            
            with ck[0]: st.button(f"📦 TOTAL\n\n{n_tot_k}", key="kpi_total", use_container_width=True, on_click=set_kpi, args=("TODOS",))
            with ck[1]: st.button(f"✅ ENTREGUES\n\n{n_ent_k}", key="kpi_entregue", use_container_width=True, on_click=set_kpi, args=("ENTREGUE",))
            with ck[2]: st.button(f"❌ FRUSTRADAS\n\n{n_fru_k}", key="kpi_frus", use_container_width=True, on_click=set_kpi, args=("FRUSTRADA",))
            with ck[3]: st.button(f"🚨 ATRASADOS\n\n{n_atr_k}", key="kpi_atra", use_container_width=True, on_click=set_kpi, args=("ATRASADO",))
            with ck[4]: st.button(f"📅 HOJE\n\n{len(df_f[df_f['DATA_OBJ'] == hoje_br])}", key="kpi_hoje", use_container_width=True, on_click=set_kpi, args=("HOJE",))

            st.markdown("<br>🎯 **Progresso de Hoje**", unsafe_allow_html=True)
            df_h = df_f[df_f['DATA_OBJ'] == hoje_br]
            if not df_h.empty:
                tx = len(df_h[df_h['STATUS_DISPLAY'].str.contains('Entregue|Frustrada|Cancelado')]) / len(df_h)
                st.progress(tx)
            else: st.info("Nenhum pedido despachado para hoje.")

            st.markdown("<br>", unsafe_allow_html=True)
            busca = st.text_input("🔎 Busca Rápida:", placeholder="Buscar por pedido, laboratório, cidade...")
            
            df_grid = df_f.copy()
            if st.session_state.filtro_kpi != "TODOS":
                if st.session_state.filtro_kpi == "HOJE": 
                    df_grid = df_grid[df_grid['DATA_OBJ'] == hoje_br]
                elif st.session_state.filtro_kpi == "ATRASADO":
                    df_grid = df_atrasados_only.copy()
                else: 
                    df_grid = df_grid[df_grid['STATUS_DISPLAY'].str.contains(st.session_state.filtro_kpi, case=False)]
            
            if busca: df_grid = df_grid[df_grid.astype(str).apply(lambda x: x.str.lower().str.contains(busca.lower())).any(axis=1)]

            if not df_grid.empty:
                cols = ['DATA', 'PEDIDO', 'STATUS_DISPLAY', 'A_DT', 'LABORATORIO', 'CIDADE', 'DATA_LIMITE', 'DETALHES', 'FOTO_URL']
                df_final = df_grid[[c for c in cols if c in df_grid.columns]].copy()
                
                def formatar_data_entrega(row):
                    st_atual = str(row.get('STATUS_DISPLAY', '')).upper()
                    dt_entrega = str(row.get('A_DT', '')).strip()
                    if 'ENTREGUE' in st_atual or 'FRUSTRADA' in st_atual:
                        return dt_entrega if dt_entrega not in ['nan', 'None', ''] else "-"
                    return "-"

                df_final['DATA_EFETIVA'] = df_final.apply(formatar_data_entrega, axis=1)
                df_final['COMPROVANTE'] = df_final['FOTO_URL'].apply(lambda x: x if str(x).startswith("http") else "")

                colunas_ordenadas = ['DATA', 'PEDIDO', 'STATUS_DISPLAY', 'LABORATORIO', 'CIDADE', 'DATA_LIMITE', 'DATA_EFETIVA', 'COMPROVANTE', 'DETALHES']
                
                for col in df_final.columns: 
                    df_final[col] = df_final[col].astype(str).replace(["nan", "NaN", "None", "none", "<NA>", "NaT"], "")

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
                    column_order=colunas_ordenadas,
                    disabled=True, hide_index=True, use_container_width=True, height=500
                )

                with holder_exportar:
                    csv = df_grid.to_csv(index=False, sep=';').encode('utf-8-sig')
                    st.download_button("📥 Exportar Planilha (CSV)", data=csv, file_name=f"Relatorio_{st.session_state.cliente}.csv", use_container_width=True)
            else: st.info("Nenhum pacote encontrado para os filtros de busca informados.")
