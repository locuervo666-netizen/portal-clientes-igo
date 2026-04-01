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
# 🔗 MOTOR DE DADOS PRINCIPAL (CORRIGIDO PARA PUXAR FOTO DO APP )
# =======================================================
@st.cache_resource
def conectar_banco_seguro():
    """Conecta ao Google Sheets buscando as chaves no PC ou no Cofre da Nuvem"""
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
                        
                        s = s.strip() if s.upper() != 'NAN' else ''
                        o = o.strip() if o.upper() != 'NAN' else ''
                        d = d.strip() if d.upper() != 'NAN' else ''
                        rec = rec.strip() if rec.upper() != 'NAN' else ''
                        f = f.strip() if f.upper() != 'NAN' else ''
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
                        if 'FOTO' not in df.columns:
                            df['FOTO'] = df['APP_FOTO']
                        else:
                            df['FOTO'] = df['APP_FOTO'].replace("", pd.NA).combine_first(df['FOTO'].replace("", pd.NA)).fillna("")
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
        st.warning("⚠️ Aguardando dados da planilha DB_IGO_Logistica...")
    else:
        df_cliente = df_raw[df_raw['LABORATORIO'].str.contains(st.session_state.cliente, na=False, case=False)].copy() if st.session_state.cliente != "IGO_LOGISTICA" else df_raw.copy()
        
        if df_cliente.empty:
            st.info(f"Nenhum dado encontrado para {st.session_state.cliente}.")
        else:
            # Tratamento de datas e status
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
            colunas_disponiveis = [c for c in ordem_padrao if c in df_cliente.columns]
            
            min_data = df_cliente['DATA_OBJ'].dropna().min() if ('DATA_OBJ' in df_cliente.columns and not df_cliente['DATA_OBJ'].dropna().empty) else hoje_br
            max_data = df_cliente['DATA_OBJ'].dropna().max() if ('DATA_OBJ' in df_cliente.columns and not df_cliente['DATA_OBJ'].dropna().empty) else hoje_br
            if isinstance(min_data, pd.Timestamp): min_data = min_data.date()
            if isinstance(max_data, pd.Timestamp): max_data = max_data.date()
            
            # --- ⚙️ SIDEBAR (INPUTS PRINCIPAIS) ---
            with st.sidebar:
                st.image(CLIENTES_CONFIG[st.session_state.cliente]["logo"], width=160)
                st.divider()
                modo_escuro = st.toggle("🌙 Modo Noturno", value=False)
                st.divider()
                datas_sel = st.date_input("🗓️ Período:", value=(min_data, max_data), min_value=min_data, max_value=max_data, format="DD/MM/YYYY", key="reset_calendario_v61")
                cidades_sel = st.multiselect("📍 Cidades:", options=sorted(df_cliente['CIDADE'].dropna().unique().tolist()))
                with st.popover("⚙️ Personalizar Colunas", use_container_width=True): col_vis = st.multiselect("Ver:", options=colunas_disponiveis, default=colunas_disponiveis)
                st.divider()

            # --- FILTROS BASE ---
            df_f = df_cliente.copy()
            if isinstance(datas_sel, tuple):
                if len(datas_sel) == 2: df_f = df_f[(df_f['DATA_OBJ'] >= datas_sel[0]) & (df_f['DATA_OBJ'] <= datas_sel[1])]
                elif len(datas_sel) == 1: df_f = df_f[df_f['DATA_OBJ'] == datas_sel[0]]
            else: df_f = df_f[df_f['DATA_OBJ'] == datas_sel]
            
            if cidades_sel: df_f = df_f[df_f['CIDADE'].isin(cidades_sel)]

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

            # --- CÁLCULO DOS KPIs ---
            n_tot = len(df_f)
            n_ent = len(df_f[df_f['STATUS_DISPLAY'].str.contains('Entregue', na=False)]) if not df_f.empty else 0
            n_frus = len(df_f[df_f['STATUS_DISPLAY'].str.contains('Frustrada', na=False)]) if not df_f.empty else 0
            n_atra = len(df_f[df_f['STATUS_DISPLAY'].str.contains('ATRASADO', na=False)]) if not df_f.empty else 0
            n_hoje = len(df_f[df_f['DATA_OBJ'] == hoje_br]) if not df_f.empty else 0

            # --- ⚙️ SIDEBAR ---
            with st.sidebar:
                taxa_conclusao = int(((n_ent + n_frus) / n_tot) * 100) if n_tot > 0 else 0
                texto_whatsapp = f"""*Resumo da Operação - {st.session_state.cliente}* 🚚\n🗓️ Data: {hoje_br.strftime('%d/%m/%Y')}\n\n📦 *Total de Cargas:* {n_tot}\n✅ *Entregues:* {n_ent}\n❌ *Frustradas:* {n_frus}\n🚨 *Atrasos/Pendências:* {n_atra}\n\n📊 *Status do Dia:* {taxa_conclusao}% Concluído.\n\nAcesse o painel para ver detalhes.\nAtendimento IGO Logística."""
                texto_codificado = urllib.parse.quote(texto_whatsapp)
                link_whatsapp = f"https://api.whatsapp.com/send?text={texto_codificado}"
                st.markdown(f"""
                <a href="{link_whatsapp}" target="_blank" style="text-decoration: none;">
                    <div style="background-color: #25D366; color: white; padding: 10px; border-radius: 8px; font-weight: bold; font-size: 14px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1 ); transition: all 0.2s; margin-bottom: 15px;">
                        📲 Enviar Resumo (WhatsApp)
                    </div>
                </a>
                """, unsafe_allow_html=True)
                
                df_f_export = df_cliente.copy()
                csv_data = df_f_export[col_vis].to_csv(index=False, sep=";").encode('utf-8-sig')
                st.download_button(label="📥 Exportar Excel", data=csv_data, file_name=f"Monitoramento_{st.session_state.cliente}.csv", mime="text/csv", use_container_width=True)
                
                st.divider()
                if st.button("🚪 Sair do Sistema", use_container_width=True): st.session_state.logado = False; st.rerun()

            # --- CSS DINÂMICO ---
            bg_app = "#0e1117" if modo_escuro else "#f0f2f6"
            bg_side = "#161b22" if modo_escuro else "#ffffff"
            txt_main = "#f8fafc" if modo_escuro else "#0f172a"
            txt_side = "#cbd5e1" if modo_escuro else "#334155"
            border_c = "#334155" if modo_escuro else "#e2e8f0"
            input_txt = "#ffffff" if modo_escuro else "#0f172a" 
            
            st.markdown(f"""
            <style>
            [data-testid="stAppViewContainer"] {{ background-color: {bg_app} !important; }}
            [data-testid="stSidebar"] {{ background-color: {bg_side} !important; border-right: 1px solid {border_c}; }}
            [data-testid="stSidebar"] .stMarkdown p, [data-testid="stSidebar"] label {{ color: {txt_side} !important; }}
            .dinamic-text {{ color: {txt_main} !important; }}
            .dinamic-border {{ border-bottom: 2px solid {border_c} !important; }}
            [data-testid="stSidebar"] div[data-baseweb="select"] > div {{ background-color: {bg_app} !important; border-color: {border_c} !important; }}
            [data-testid="stSidebar"] input {{ background-color: {bg_app} !important; color: {input_txt} !important; }}
            .stTextInput > div > div > input {{ font-size: 16px !important; padding: 10px !important; border-radius: 8px !important; }}
            </style>
            """, unsafe_allow_html=True)

            # --- HEADER E KPIs ---
            st.markdown(f"""
            <div class="header-container dinamic-border" style="padding-bottom: 10px; margin-top: -15px;">
                <h2 class="dinamic-text" style="margin: 0; font-weight: 900; font-size: 22px; letter-spacing: -0.5px;">Monitoramento {st.session_state.cliente}</h2>
                <div class='sync-status'>🟢 Sincronizado {datetime.now(FUSO_BR).strftime('%H:%M')}</div>
            </div>
            """, unsafe_allow_html=True)

            c1, c2, c3, c4, c5 = st.columns(5)
            def click_kpi(valor): st.session_state.filtro_kpi = valor

            with c1: st.button(f"📦 TOTAL\n\n{n_tot}", key="kpi_total", use_container_width=True, on_click=click_kpi, args=("TODOS",))
            with c2: st.button(f"✅ ENTREGUES\n\n{n_ent}", key="kpi_entregue", use_container_width=True, on_click=click_kpi, args=("ENTREGUE",))
            with c3: st.button(f"❌ FRUSTRADAS\n\n{n_frus}", key="kpi_frus", use_container_width=True, on_click=click_kpi, args=("FRUSTRADA",))
            with c4: st.button(f"🚨 ATRASADOS\n\n{n_atra}", key="kpi_atra", use_container_width=True, on_click=click_kpi, args=("ATRASADO",))
            with c5: st.button(f"📅 HOJE\n\n{n_hoje}", key="kpi_hoje", use_container_width=True, on_click=click_kpi, args=("HOJE",))

            # 📊 BARRA DE PROGRESSO
            st.markdown("  
", unsafe_allow_html=True)
            st.markdown(f"<div class='dinamic-text' style='font-size:14px; font-weight:800; margin-bottom:10px;'>🎯 Progresso de Hoje</div>", unsafe_allow_html=True)
            df_hoje_bi = df_cliente[df_cliente['DATA_OBJ'] == hoje_br]
            if not df_hoje_bi.empty:
                t_hoje = len(df_hoje_bi)
                c_hoje = len(df_hoje_bi[df_hoje_bi['STATUS_DISPLAY'].str.contains('Entregue|Frustrada', na=False)])
                taxa = c_hoje / t_hoje if t_hoje > 0 else 0
                st.progress(taxa)
                st.markdown(f"<div class='dinamic-text' style='font-size:12px; margin-top:-10px; text-align:right;'>{c_hoje} de {t_hoje} finalizados ({int(taxa*100)}%)</div>", unsafe_allow_html=True)
            
            st.markdown(f"<div class='dinamic-border' style='margin-bottom: 15px; margin-top: 15px;'></div>", unsafe_allow_html=True)

            # =======================================================
            # 📋 GRID PRINCIPAL LIMPÍSSIMA
            # =======================================================
            col_busca, _ = st.columns([2, 1])
            with col_busca:
                busca_inteligente = st.text_input("🔎 Busca Rápida:", placeholder="Ex: Melo Labs, Centro, Maria, Frustrada, 102938...", key="busca_inteligente")
            
            df_grid = df_f.copy()
            if not df_grid.empty:
                if st.session_state.filtro_kpi == "ENTREGUE": df_grid = df_grid[df_grid['STATUS_DISPLAY'].str.contains('Entregue', na=False)]
                elif st.session_state.filtro_kpi == "FRUSTRADA": df_grid = df_grid[df_grid['STATUS_DISPLAY'].str.contains('Frustrada', na=False)]
                elif st.session_state.filtro_kpi == "ATRASADO": df_grid = df_grid[df_grid['STATUS_DISPLAY'].str.contains('ATRASADO', na=False)]
                elif st.session_state.filtro_kpi == "HOJE": df_grid = df_grid[df_grid['DATA_OBJ'] == hoje_br]

                df_grid['STATUS'] = df_grid['STATUS_DISPLAY'] 
                df_final = df_grid[[c for c in col_vis if c in df_grid.columns]]
                
                if busca_inteligente:
                    busca_lower = str(busca_inteligente).lower()
                    mask = df_final.astype(str).apply(lambda x: x.str.lower().str.contains(busca_lower)).any(axis=1)
                    df_final = df_final[mask]

                if not df_final.empty:
                    gb = GridOptionsBuilder.from_dataframe(df_final)
                    gb.configure_default_column(resizable=True, sortable=True, minWidth=100)
                    gb.configure_selection('single', use_checkbox=False)
                    
                    status_jscode = JsCode("""
                    function(params) {
                        let val = params.value || '';
                        if (val.includes('Entregue')) { return {'backgroundColor': 'rgba(16, 185, 129, 0.15)', 'color': '#10B981', 'fontWeight': '900'}; } 
                        else if (val.includes('Frustrada') || val.includes('ATRASADO')) { return {'backgroundColor': 'rgba(239, 68, 68, 0.15)', 'color': '#EF4444', 'fontWeight': '900'}; } 
                        else if (val.includes('Em Rota')) { return {'backgroundColor': 'rgba(245, 158, 11, 0.15)', 'color': '#F59E0B', 'fontWeight': '900'}; } 
                        else if (val.includes('Coletado') || val.includes('Conferido') || val.includes('Triagem')) { return {'backgroundColor': 'rgba(59, 130, 246, 0.15)', 'color': '#3B82F6', 'fontWeight': '900'}; }
                        return {'fontWeight': 'bold'};
                    }
                    """)
                    
                    for col in df_final.columns:
                        header_name = col.upper()
                        if col == 'DATA_LIMITE': header_name = "PREVISÃO ENTREGA"
                        elif col == 'DATA_ENTREGA': header_name = "DATA ENTREGA"
                        elif col == 'FOTO_URL': header_name = "FOTO"
                        
                        if col == 'STATUS': gb.configure_column(col, headerName=header_name, cellStyle=status_jscode, width=130, minWidth=120)
                        elif col == 'FOTO_URL':
                            link_jscode = JsCode("""
                            class FotoModalRenderer {
                                init(params) {
                                    this.eGui = document.createElement('div');
                                    this.eGui.style.textAlign = 'center';
                                    let val = params.value;
                                    if (val && typeof val === 'string' && val.trim() !== '' && val.toLowerCase() !== 'nan' && val.includes('http' )) {
                                        let icon = document.createElement('span');
                                        icon.innerHTML = '📸';
                                        icon.style.cursor = 'pointer';
                                        icon.style.fontSize = '18px';
                                        icon.title = 'Clique para ver a foto';
                                        icon.onclick = function(e) {
                                            e.preventDefault();
                                            let modal = document.createElement('div');
                                            modal.style.position = 'fixed';
                                            modal.style.zIndex = '9999999';
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
                                            img.src = val;
                                            img.style.maxWidth = '90%';
                                            img.style.maxHeight = '85%';
                                            img.style.borderRadius = '8px';
                                            img.style.boxShadow = '0 4px 20px rgba(0,0,0,0.5)';
                                            img.style.objectFit = 'contain';
                                            let txt = document.createElement('div');
                                            txt.innerText = '✖ Clique em qualquer lugar para fechar';
                                            txt.style.color = '#ffffff';
                                            txt.style.marginTop = '15px';
                                            txt.style.fontFamily = 'sans-serif';
                                            txt.style.fontSize = '16px';
                                            txt.style.fontWeight = 'bold';
                                            modal.appendChild(img);
                                            modal.appendChild(txt);
                                            modal.onclick = function() {
                                                if(document.body.contains(modal)) {
                                                    document.body.removeChild(modal);
                                                }
                                            };
                                            document.body.appendChild(modal);
                                        };
                                        this.eGui.appendChild(icon);
                                    } else {
                                        this.eGui.innerHTML = '<span style="color: #cbd5e1; font-size: 14px;" title="Nenhuma foto registrada">➖</span>';
                                    }
                                }
                                getGui() { return this.eGui; }
                            }
                            """)
                            gb.configure_column(col, headerName=header_name, cellRenderer=link_jscode, width=70, minWidth=70)
                        elif col == 'DETALHES': gb.configure_column(col, headerName=header_name, width=300, minWidth=250, tooltipField="DETALHES")
                        elif col == 'UF': gb.configure_column(col, headerName=header_name, width=60, minWidth=60)
                        elif col == 'DATA': gb.configure_column(col, headerName=header_name, width=90, minWidth=90)
                        elif col == 'PEDIDO': gb.configure_column(col, headerName=header_name, width=95, minWidth=95)
                        elif col == 'LABORATORIO': gb.configure_column(col, headerName=header_name, width=400, minWidth=350, tooltipField="LABORATORIO")
                        elif col == 'BAIRRO': gb.configure_column(col, headerName=header_name, width=250, minWidth=200, tooltipField="BAIRRO")
                        elif col == 'CIDADE': gb.configure_column(col, headerName=header_name, width=180, minWidth=150)
                        else: gb.configure_column(col, headerName=header_name)

                    if modo_escuro:
                        grid_css = {
                            ".ag-root-wrapper": {"background-color": "#0e1117 !important", "border": "none !important"},
                            ".ag-header": {"background-color": "#1e293b !important", "border-bottom": "1px solid #334155 !important"},
                            ".ag-header-cell-text": {"font-size": "11px !important", "font-weight": "bold", "color": "#f8fafc !important"},
                            ".ag-cell": {"font-size": "11px !important", "color": "#cbd5e1 !important", "border-bottom": "1px solid #1e293b !important"},
                            ".ag-row-even": {"background-color": "#0f172a !important"}, ".ag-row-odd": {"background-color": "#1e293b !important"}, ".ag-row-hover": {"background-color": "#334155 !important"} 
                        }
                    else:
                        grid_css = {
                            ".ag-header-cell-text": {"font-size": "11px !important", "font-weight": "bold", "color": "#334155"},
                            ".ag-cell": {"font-size": "11px !important", "color": "#475569"},
                            ".ag-row-even": {"background-color": "#f8fafc !important"}, ".ag-row-odd": {"background-color": "#ffffff !important"}, ".ag-row-hover": {"background-color": "#e2e8f0 !important"} 
                        }
                    AgGrid(df_final, gridOptions=gb.build(), allow_unsafe_jscode=True, theme='alpine', custom_css=grid_css, fit_columns_on_grid_load=False, height=520)
                else:
                    st.info("Nenhum resultado encontrado na busca inteligente.")
            else: st.warning("Nenhum pedido encontrado nos filtros principais.")
