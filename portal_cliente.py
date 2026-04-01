import streamlit as st
import pandas as pd
import gspread
import os
import urllib.parse
from datetime import datetime, timedelta, timezone
from streamlit_autorefresh import st_autorefresh
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

FUSO_BR = timezone(timedelta(hours=-3))
# 🎯 ATENÇÃO ROBSON: Link direto da Logo IGO
LOGO_IGO = "https://i.postimg.cc/d71mqWDx/IGO-LOGO.png"

# =======================================================
# 🎨 1. CONFIGURAÇÃO DA PÁGINA E CSS BASE (INTEGRAL)
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
                        s, o, d, rec, f = [str(r.get(x, '')).strip() for x in [col_status, col_obs, col_detalhes, col_receb, col_foto]]
                        s = s if s.upper() != 'NAN' else ''
                        o = o if o.upper() != 'NAN' else ''
                        d = d if d.upper() != 'NAN' else ''
                        rec = rec if rec.upper() != 'NAN' else ''
                        f = f if f.upper() != 'NAN' else ''
                        q = d if d else rec
                        return pd.Series([s, o, q, f])
                    df_app_clean[['APP_STATUS', 'APP_OBS', 'APP_QUEM', 'APP_FOTO']] = df_app_clean.apply(extrair_dados_app, axis=1)
                    df_app_clean = df_app_clean[['PEDIDO', 'APP_STATUS', 'APP_OBS', 'APP_QUEM', 'APP_FOTO']]
                    df_app_clean['PEDIDO'] = df_app_clean['PEDIDO'].astype(str).str.strip()
                    df_app_clean.drop_duplicates(subset=['PEDIDO'], keep='last', inplace=True)
                    df['PEDIDO'] = df['PEDIDO'].astype(str).str.strip()
                    if 'ROMANEIO' not in df.columns: df['ROMANEIO'] = ""
                    df['ROMANEIO'] = df['ROMANEIO'].astype(str).str.strip()
                    df = pd.merge(df, df_app_clean, on='PEDIDO', how='left')
                    df_app_rom = df_app_clean[df_app_clean['PEDIDO'].str.startswith('ROM-', na=False)].rename(columns={'PEDIDO': 'ROMANEIO'})
                    if not df_app_rom.empty:
                        df = pd.merge(df, df_app_rom, on='ROMANEIO', how='left', suffixes=('', '_R'))
                        for c in ['APP_STATUS', 'APP_QUEM', 'APP_OBS', 'APP_FOTO']:
                            if f"{c}_R" in df.columns:
                                df[c] = df[f"{c}_R"].replace("", pd.NA).combine_first(df[c].replace("", pd.NA)).fillna("")
                    if 'APP_FOTO' in df.columns:
                        if 'FOTO' not in df.columns: df['FOTO'] = df['APP_FOTO']
                        else: df['FOTO'] = df['APP_FOTO'].replace("", pd.NA).combine_first(df['FOTO'].replace("", pd.NA)).fillna("")
            except: pass
            if 'DATA' in df.columns: df['DATA_OBJ'] = pd.to_datetime(df['DATA'], format='%d/%m/%Y', errors='coerce').dt.date
            return df
    except Exception as e: st.error(f"Sincronização offline: {e}")
    return pd.DataFrame()

if 'logado' not in st.session_state: st.session_state.logado = False
if 'filtro_kpi' not in st.session_state: st.session_state.filtro_kpi = "TODOS"

# =======================================================
# 🔐 3. LOGIN PREMIUM
# =======================================================
if not st.session_state.logado:
    st.markdown("""<style> [data-testid="stAppViewContainer"] { background-color: #f8fafc !important; background-image: radial-gradient(#cbd5e1 1px, transparent 1px); background-size: 24px 24px; } </style>""", unsafe_allow_html=True)
    _, c2, _ = st.columns([1, 1.2, 1])
    with c2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown(f"""<div style="text-align: center; padding-top: 15px;"><img src="{LOGO_IGO}" width="110" style="margin-bottom: 20px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.1);"><h2 style="margin: 0; color: #0f172a; font-weight: 900; font-size: 28px;">Central de Comando</h2><p style="color: #64748b; font-size: 15px; margin-bottom: 25px;">Portal de Monitoramento IGO Logística</p></div>""", unsafe_allow_html=True)
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
            df_cliente['FOTO_URL'] = df_cliente['FOTO'].apply(lambda x: f"https://www.appsheet.com/template/gettablefileurl?appName=APPIGOLOGISTICA-153047553&tableName=App_Tarefas&fileName={str(x).strip()}" if x and str(x).upper() not in ['NAN', ''] else "")

            def definir_status_real(row):
                s_db, s_app = str(row.get('STATUS', '')).strip().upper(), str(row.get('APP_STATUS', '')).strip().upper()
                def peso(st_txt):
                    if any(x in st_txt for x in ['ENTREGUE', 'FRUSTRAD', 'CANCELAD']): return 5
                    if any(x in st_txt for x in ['ROTA', 'ENTREGA']): return 4
                    if any(x in st_txt for x in ['CONFERIDO', 'TRIAGEM']): return 3
                    if 'COLETADO' in st_txt: return 2
                    return 1
                return s_app if peso(s_app) >= peso(s_db) else s_db
            df_cliente['STATUS_REAL'] = df_cliente.apply(definir_status_real, axis=1)

            def processar_detalhes(row):
                s = str(row.get('STATUS_REAL', '')).upper()
                if 'FRUSTRADA' in s:
                    resp, obs = str(row.get('APP_QUEM', '')).strip(), str(row.get('APP_OBS', '')).strip()
                    emoji = "📝"
                    obs_up = obs.upper()
                    if "FECHADO" in obs_up: emoji = "🔒"
                    elif "SEM MATERIAL" in obs_up: emoji = "📭"
                    elif "AUSENTE" in obs_up: emoji = "🚷"
                    elif "ENDERE" in obs_up or "INCORRETO" in obs_up: emoji = "🗺️"
                    elif "RECUS" in obs_up: emoji = "🛑"
                    t_resp = f"🗣️ {resp}" if resp and resp.upper() != 'NAN' else ""
                    t_obs = f"{emoji} {obs}" if obs and obs.upper() != 'NAN' else ""
                    return f"{t_resp} / {t_obs}" if t_resp and t_obs else (t_resp or t_obs)
                return ""
            df_cliente['DETALHES'] = df_cliente.apply(processar_detalhes, axis=1)

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
            col_disponiveis = [c for c in ordem_padrao if c in df_cliente.columns]

            # --- PROCESSAMENTO DE FILTROS PARA O SIDEBAR E EXPORTAÇÃO ---
            min_d = df_cliente['DATA_OBJ'].dropna().min() if not df_cliente['DATA_OBJ'].dropna().empty else hoje_br
            max_d = df_cliente['DATA_OBJ'].dropna().max() if not df_cliente['DATA_OBJ'].dropna().empty else hoje_br
            
            with st.sidebar:
                st.image(conf["logo"], width=160)
                st.divider()
                modo_escuro = st.toggle("🌙 Modo Noturno", value=False)
                st.divider()
                datas_sel = st.date_input("🗓️ Período:", value=(min_d, max_d), format="DD/MM/YYYY")
                cidades_sel = st.multiselect("📍 Cidades:", sorted(df_cliente['CIDADE'].dropna().unique().tolist()))
                with st.popover("⚙️ Personalizar Colunas", use_container_width=True):
                    col_vis = st.multiselect("Ver:", options=col_disponiveis, default=['DATA', 'PEDIDO', 'STATUS', 'LABORATORIO', 'CIDADE', 'UF', 'BAIRRO', 'DATA_LIMITE', 'FOTO_URL', 'DETALHES'])
                st.divider()

            # --- APLICAÇÃO DOS FILTROS NO DATAFRAME DE TRABALHO ---
            df_f = df_cliente.copy()
            if isinstance(datas_sel, tuple) and len(datas_sel) == 2: df_f = df_f[(df_f['DATA_OBJ'] >= datas_sel[0]) & (df_f['DATA_OBJ'] <= datas_sel[1])]
            if cidades_sel: df_f = df_f[df_f['CIDADE'].isin(cidades_sel)]

            # --- FILTRO POR KPI ---
            if st.session_state.filtro_kpi == "ENTREGUE": df_f = df_f[df_f['STATUS_DISPLAY'].str.contains('Entregue')]
            elif st.session_state.filtro_kpi == "FRUSTRADA": df_f = df_f[df_f['STATUS_DISPLAY'].str.contains('Frustrada')]
            elif st.session_state.filtro_kpi == "ATRASADO": df_f = df_f[df_f['STATUS_DISPLAY'].str.contains('ATRASADO')]
            elif st.session_state.filtro_kpi == "HOJE": df_f = df_f[df_f['DATA_OBJ'] == hoje_br]

            # --- BUSCA INTELIGENTE (APLICADA ANTES DO DOWNLOAD) ---
            busca = st.text_input("🔎 Busca Rápida:", placeholder="Ex: Melo Labs, Centro, Maria...")
            df_grid = df_f.copy()
            if busca:
                mask = df_grid.astype(str).apply(lambda x: x.str.lower().str.contains(busca.lower())).any(axis=1)
                df_grid = df_grid[mask]

            # --- SIDEBAR: BOTÕES DE WHATSAPP E EXPORTAÇÃO (AGORA COM DF_GRID FILTRADO) ---
            with st.sidebar:
                n_tot_f = len(df_grid)
                n_ent_f = len(df_grid[df_grid['STATUS_DISPLAY'].str.contains('Entregue')])
                texto_w = f"*Resumo IGO - {st.session_state.cliente}*\n📦 Total: {n_tot_f}\n✅ OK: {n_ent_f}"
                st.markdown(f'<a href="https://api.whatsapp.com/send?text={urllib.parse.quote(texto_w)}" target="_blank" style="text-decoration:none;"><div style="background:#25D366; color:white; padding:10px; border-radius:8px; font-weight:bold; text-align:center; margin-bottom:15px;">📲 Enviar Resumo WhatsApp</div></a>', unsafe_allow_html=True)
                
                # EXPORTAÇÃO DINÂMICA: Exporta apenas o que está na tela (df_grid)
                csv = df_grid.to_csv(index=False, sep=';').encode('utf-8-sig')
                st.download_button("📥 Exportar Relatório (CSV)", data=csv, file_name=f"Monitoramento_{st.session_state.cliente}.csv", use_container_width=True)
                
                st.divider()
                if st.button("🚪 Sair do Sistema", use_container_width=True): st.session_state.logado = False; st.rerun()

            st.markdown(f"""<style> [data-testid="stAppViewContainer"] {{ background-color: {"#0e1117" if modo_escuro else "#f0f2f6"} !important; }} .dinamic-text {{ color: {"#f8fafc" if modo_escuro else "#0f172a"} !important; }} </style>""", unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class="header-container" style="border-bottom: 2px solid #e2e8f0; padding-bottom: 10px; margin-top: -15px;">
                <h2 class="dinamic-text" style="margin: 0; font-weight: 900; font-size: 22px; letter-spacing: -0.5px;">Monitoramento {st.session_state.cliente}</h2>
                <div class='sync-status'>🟢 Sincronizado {datetime.now(FUSO_BR).strftime('%H:%M')}</div>
            </div>
            """, unsafe_allow_html=True)

            ck = st.columns(5)
            def set_kpi(v): st.session_state.filtro_kpi = v
            n_fru_k = len(df_f[df_f['STATUS_DISPLAY'].str.contains('Frustrada')])
            n_atr_k = len(df_f[df_f['STATUS_DISPLAY'].str.contains('ATRASADO')])
            n_hoj_k = len(df_f[df_f['DATA_OBJ'] == hoje_br])
            ck[0].button(f"📦 TOTAL\n\n{len(df_f)}", key="k_tot", use_container_width=True, on_click=set_kpi, args=("TODOS",))
            ck[1].button(f"✅ ENTREGUES\n\n{len(df_f[df_f['STATUS_DISPLAY'].str.contains('Entregue')])}", key="k_ent", use_container_width=True, on_click=set_kpi, args=("ENTREGUE",))
            ck[2].button(f"❌ FRUSTRADAS\n\n{n_fru_k}", key="k_fru", use_container_width=True, on_click=set_kpi, args=("FRUSTRADA",))
            ck[3].button(f"🚨 ATRASADOS\n\n{n_atr_k}", key="k_atr", use_container_width=True, on_click=set_kpi, args=("ATRASADO",))
            ck[4].button(f"📅 HOJE\n\n{n_hoj_k}", key="k_hoj", use_container_width=True, on_click=set_kpi, args=("HOJE",))

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(f"<div class='dinamic-text' style='font-size:14px; font-weight:800; margin-bottom:10px;'>🎯 Progresso de Hoje</div>", unsafe_allow_html=True)
            df_hoje_bi = df_cliente[df_cliente['DATA_OBJ'] == hoje_br]
            if not df_hoje_bi.empty:
                t_h = len(df_hoje_bi); c_h = len(df_hoje_bi[df_hoje_bi['STATUS_DISPLAY'].str.contains('Entregue|Frustrada')])
                tx = c_h / t_h if t_h > 0 else 0
                st.progress(tx)
                st.markdown(f"<div class='dinamic-text' style='font-size:12px; margin-top:-10px; text-align:right;'>{c_h} de {t_h} finalizados ({int(tx*100)}%)</div>", unsafe_allow_html=True)
            else: st.info("Nenhum pedido para hoje.")
            st.markdown("<div class='dinamic-border' style='margin-bottom: 15px; margin-top: 15px;'></div>", unsafe_allow_html=True)

            if not df_grid.empty:
                df_grid['STATUS'] = df_grid['STATUS_DISPLAY']
                df_final_grid = df_grid[[c for c in col_vis if c in df_grid.columns]]
                gb = GridOptionsBuilder.from_dataframe(df_final_grid)
                gb.configure_default_column(resizable=True, sortable=True, minWidth=100)
                status_js = JsCode("""
                function(params) {
                    let v = params.value || '';
                    if (v.includes('Entregue')) return {'backgroundColor': 'rgba(16, 185, 129, 0.15)', 'color': '#10B981', 'fontWeight': '900'};
                    if (v.includes('Frustrada') || v.includes('ATRASADO')) return {'backgroundColor': 'rgba(239, 68, 68, 0.15)', 'color': '#EF4444', 'fontWeight': '900'};
                    if (v.includes('Em Rota')) return {'backgroundColor': 'rgba(245, 158, 11, 0.15)', 'color': '#F59E0B', 'fontWeight': '900'};
                    if (v.includes('Coletado') || v.includes('Conferido') || v.includes('Triagem')) return {'backgroundColor': 'rgba(59, 130, 246, 0.15)', 'color': '#3B82F6', 'fontWeight': '900'};
                    return {'fontWeight': 'bold'};
                }
                """)
                foto_js = JsCode("""
                class FotoRenderer {
                    init(params) {
                        this.eGui = document.createElement('div');
                        this.eGui.style.textAlign = 'center';
                        if (params.value && params.value.includes('http')) {
                            let b = document.createElement('span'); b.innerHTML = '📸'; b.style.cursor='pointer'; b.style.fontSize='18px';
                            b.onclick = () => {
                                let m = document.createElement('div');
                                Object.assign(m.style, {position:'fixed', zIndex:'9999999', left:0, top:0, width:'100vw', height:'100vh', backgroundColor:'rgba(0,0,0,0.85)', display:'flex', flexDirection:'column', justifyContent:'center', alignItems:'center', cursor:'zoom-out'});
                                let i = document.createElement('img'); i.src = params.value; Object.assign(i.style, {maxWidth:'90%', maxHeight:'85%', borderRadius:'8px', boxShadow:'0 4px 20px rgba(0,0,0,0.5)', objectFit:'contain'});
                                let t = document.createElement('div'); t.innerText = '✖ Clique para fechar'; Object.assign(t.style, {color:'#fff', marginTop:'15px', fontWeight:'bold'});
                                m.appendChild(i); m.appendChild(t); m.onclick = () => document.body.removeChild(m); document.body.appendChild(m);
                            };
                            this.eGui.appendChild(b);
                        } else { this.eGui.innerHTML = '<span style="color:#cbd5e1">➖</span>'; }
                    }
                    getGui() { return this.eGui; }
                }
                """)
                for col in df_final_grid.columns:
                    if col == 'STATUS': gb.configure_column(col, cellStyle=status_js)
                    elif col == 'FOTO_URL': gb.configure_column(col, headerName="FOTO", cellRenderer=foto_js, width=80)
                
                AgGrid(df_final_grid, gridOptions=gb.build(), allow_unsafe_jscode=True, theme='alpine', height=550)
