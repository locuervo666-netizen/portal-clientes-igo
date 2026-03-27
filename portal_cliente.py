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

# 🖼️ DICIONÁRIO DE LOGOS
LOGOS_CLIENTES = {
    "GRALAB": "https://cdn.awsli.com.br/2702/2702264/logo/gralab-rbuogsxve7.png", 
    "DEFAULT": "https://cdn-icons-png.flaticon.com/512/1532/1532692.png" 
}

# =======================================================
# 🔗 2. MOTOR DE DADOS
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
            DIRETORIO_USUARIO = os.path.expanduser("~")
            PASTA_SISTEMA = os.path.join(DIRETORIO_USUARIO, "IGO_Logistica_Sistema")
            gc = gspread.oauth(credentials_filename=os.path.join(PASTA_SISTEMA, "credentials.json"), authorized_user_filename=os.path.join(PASTA_SISTEMA, "token.json"))
            
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
        st.error(f"Falha de sincronização: {e}")
    return pd.DataFrame()

# =======================================================
# 🔐 3. TELA DE LOGIN 
# =======================================================
if 'logado' not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<br><br><br><br>", unsafe_allow_html=True)
        with st.container(border=True):
            st.image(LOGOS_CLIENTES["GRALAB"], width=160)
            
            st.markdown("<h2 style='font-size: 24px; color: #0f172a; margin-top: 10px;'>Acesso ao Portal</h2>", unsafe_allow_html=True)
            st.markdown("<p style='color: #64748b; font-size: 15px;'>Área exclusiva de rastreamento</p>", unsafe_allow_html=True)
            
            usuario = st.text_input("Usuário (Ex: GRALAB)")
            senha = st.text_input("Senha", type="password")
            
            if st.button("Entrar", type="primary", use_container_width=True):
                if usuario.upper() == "GRALAB" and senha == "123":
                    st.session_state.logado = True
                    st.session_state.cliente = "GRALAB"
                    st.rerun()
                else:
                    st.error("Credenciais inválidas.")

# =======================================================
# 🚀 4. DASHBOARD ENTERPRISE V20
# =======================================================
else:
    df_sistema = carregar_dados_nuvem()

    if not df_sistema.empty and 'TOMADOR' in df_sistema.columns:
        df_cliente = df_sistema[df_sistema['TOMADOR'] == st.session_state.cliente].copy()
        
        if not df_cliente.empty:
            # 📸 TRADUTOR DE FOTOS APPSHEET
            if 'FOTO' in df_cliente.columns:
                def construir_link_foto(foto_path):
                    f_str = str(foto_path).strip()
                    if f_str and f_str.upper() not in ['NAN', 'NONE', '']:
                        return f"https://www.appsheet.com/template/gettablefileurl?appName=APPIGOLOGISTICA-153047553&tableName=App_Tarefas&fileName={f_str}"
                    return ""
                
                df_cliente['FOTO_URL'] = df_cliente['FOTO'].apply(construir_link_foto)
            else:
                df_cliente['FOTO_URL'] = ""

            ordem_padrao = ['PEDIDO', 'DATA', 'STATUS', 'LABORATORIO', 'CIDADE', 'UF', 'BAIRRO', 'ENDERECO', 'Nº', 'NUMERO', 'CEP', 'DATA_LIMITE', 'DATA_ENTREGA', 'FOTO_URL']
            colunas_disponiveis = [col for col in ordem_padrao if col in df_cliente.columns]
            
            colunas_ocultas_padrao = ['ENDERECO', 'Nº', 'NUMERO', 'CEP']
            colunas_visiveis_iniciais = [col for col in colunas_disponiveis if col not in colunas_ocultas_padrao]

            hoje_br = datetime.now(FUSO_BR).date()

            with st.sidebar:
                logo_atual = LOGOS_CLIENTES.get(st.session_state.cliente, LOGOS_CLIENTES["DEFAULT"])
                st.image(logo_atual, width=160)
                
                st.markdown("<br>", unsafe_allow_html=True)
                st.divider()
                
                min_date = df_cliente['DATA_OBJ'].dropna().min() if 'DATA_OBJ' in df_cliente.columns else hoje_br
                max_date = df_cliente['DATA_OBJ'].dropna().max() if 'DATA_OBJ' in df_cliente.columns else hoje_br
                
                datas_selecionadas = st.date_input("🗓️ Período:", value=(min_date, max_date), min_value=min_date, max_value=max_date, format="DD/MM/YYYY")
                
                lista_cidades = sorted(df_cliente['CIDADE'].dropna().unique().tolist()) if 'CIDADE' in df_cliente.columns else []
                cidades_selecionadas = st.multiselect("📍 Cidades:", options=lista_cidades, default=lista_cidades)
                
                busca_pedido = st.text_input("🔍 Pedido / Nº:")
                st.divider()
                
                with st.popover("⚙️ Personalizar Colunas", use_container_width=True):
                    colunas_selecionadas = st.multiselect("Selecione o que deseja ver:", options=colunas_disponiveis, default=colunas_visiveis_iniciais)
                
                st.markdown("<br><br>", unsafe_allow_html=True)
                if st.button("🚪 Sair", use_container_width=True):
                    st.session_state.logado = False
                    st.rerun()

            df_filtrado = df_cliente.copy()
            if len(datas_selecionadas) == 2 and 'DATA_OBJ' in df_filtrado.columns:
                df_filtrado = df_filtrado[(df_filtrado['DATA_OBJ'] >= datas_selecionadas[0]) & (df_filtrado['DATA_OBJ'] <= datas_selecionadas[1])]
            if cidades_selecionadas and 'CIDADE' in df_filtrado.columns:
                df_filtrado = df_filtrado[df_filtrado['CIDADE'].isin(cidades_selecionadas)]
            if busca_pedido:
                busca = str(busca_pedido).upper()
                cond_pedido = df_filtrado['PEDIDO'].astype(str).str.upper().str.contains(busca) if 'PEDIDO' in df_filtrado.columns else False
                cond_numero = df_filtrado['NUMERO'].astype(str).str.upper().str.contains(busca) if 'NUMERO' in df_filtrado.columns else False
                df_filtrado = df_filtrado[cond_pedido | cond_numero]

            def tratar_status_e_atrasos(row):
                status = str(row.get('STATUS', '')).strip().upper()
                previsao_str = str(row.get('DATA_LIMITE', '')).strip()
                
                if status == 'ENTREGUE': status = '✅ Entregue'
                elif status in ['EM ROTA', 'EM ROTA DE ENTREGA']: status = '🚚 Em Rota'
                elif status == 'COLETADO': status = '📦 Coletado'
                elif status == 'CANCELADO': status = '❌ Cancelado'
                else: status = f'⏳ Pendente'
                
                if status not in ['✅ Entregue', '❌ Cancelado'] and previsao_str:
                    try:
                        data_previsao = datetime.strptime(previsao_str, "%d/%m/%Y").date()
                        if data_previsao < hoje_br: 
                            status = f"🚨 ATRASADO ({status})"
                    except: pass
                return status
                
            if 'STATUS' in df_filtrado.columns:
                df_filtrado['STATUS'] = df_filtrado.apply(tratar_status_e_atrasos, axis=1)

            vol_total = len(df_filtrado)
            vol_atrasados = len(df_filtrado[df_filtrado['STATUS'].str.contains('ATRASADO', na=False)]) if 'STATUS' in df_filtrado.columns else 0
            vol_pendentes = len(df_filtrado[df_filtrado['STATUS'].str.contains('Pendente|Coletado|Em Rota', case=False, na=False)]) if 'STATUS' in df_filtrado.columns else 0
            vol_hoje = len(df_filtrado[df_filtrado['DATA_OBJ'] == hoje_br]) if 'DATA_OBJ' in df_filtrado.columns else 0 

            c_titulo, c_botao = st.columns([4, 1])
            with c_titulo:
                st.markdown(f"<h1>Painel de Cargas | {st.session_state.cliente}</h1>", unsafe_allow_html=True)
            with c_botao:
                csv_data = df_filtrado[colunas_selecionadas].to_csv(index=False, sep=";").encode('utf-8-sig')
                st.download_button(label="📥 Exportar Excel", data=csv_data, file_name=f"Cargas_{st.session_state.cliente}.csv", mime="text/csv", use_container_width=True)
                hora_brasilia = datetime.now(FUSO_BR).strftime('%H:%M')
                st.markdown(f"<div class='sync-status'>🟢 Sincronizado {hora_brasilia}</div>", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            c1, c2, c3, c4 = st.columns(4)
            c1.markdown(f"""<div class="kpi-card bg-blue"><div class="kpi-title">📦 Total Filtrado</div><div class="kpi-value">{vol_total}</div></div>""", unsafe_allow_html=True)
            c2.markdown(f"""<div class="kpi-card bg-orange"><div class="kpi-title">⏳ Em Operação</div><div class="kpi-value">{vol_pendentes}</div></div>""", unsafe_allow_html=True)
            c3.markdown(f"""<div class="kpi-card bg-red"><div class="kpi-title">🚨 Atrasados</div><div class="kpi-value">{vol_atrasados}</div></div>""", unsafe_allow_html=True)
            c4.markdown(f"""<div class="kpi-card bg-green"><div class="kpi-title">📅 Para Hoje</div><div class="kpi-value">{vol_hoje}</div></div>""", unsafe_allow_html=True)

            if 'CIDADE' in df_filtrado.columns:
                df_filtrado = df_filtrado.sort_values(by=['CIDADE', 'DATA'], ascending=[True, False])

            if not colunas_selecionadas:
                st.warning("Selecione pelo menos uma coluna no menu lateral para visualizar os dados.")
            else:
                df_final = df_filtrado[colunas_selecionadas].copy()
                
                if not df_final.empty:
                    gb = GridOptionsBuilder.from_dataframe(df_final)
                    
                    gb.configure_default_column(resizable=True, sortable=True, minWidth=110)
                    gb.configure_selection('single', use_checkbox=False)
                    
                    # 🎯 A MÁGICA DA CLASSE AG-GRID (Evita o erro do React!)
                    if 'FOTO_URL' in df_final.columns:
                        link_jscode = JsCode("""
                        class LinkCellRenderer {
                            init(params) {
                                this.eGui = document.createElement('div');
                                if (params.value && params.value !== '' && params.value !== 'nan') {
                                    this.eGui.innerHTML = '<a href="' + params.value + '" target="_blank" style="color: #2980B9; text-decoration: none; font-weight: bold; padding: 4px 10px; background-color: #EBF5FB; border-radius: 4px; display: inline-block; margin-top: 4px;">🔗 Ver Foto</a>';
                                }
                            }
                            getGui() {
                                return this.eGui;
                            }
                        }
                        """)
                        gb.configure_column("FOTO_URL", headerName="Comprovante", cellRenderer=link_jscode, width=130)
                    
                    if 'DATA_LIMITE' in df_final.columns: gb.configure_column("DATA_LIMITE", headerName="Previsão")
                    if 'DATA_ENTREGA' in df_final.columns: gb.configure_column("DATA_ENTREGA", headerName="Entregue Em")
                    if 'STATUS' in df_final.columns: gb.configure_column("STATUS", width=160)
                    if 'LABORATORIO' in df_final.columns: gb.configure_column("LABORATORIO", width=180)

                    gridOptions = gb.build()

                    grid_css = {
                        ".ag-header-cell-text": {"font-size": "12px !important", "color": "#475569 !important", "font-family": "Inter, sans-serif !important"},
                        ".ag-cell": {"font-size": "12px !important", "font-family": "Inter, sans-serif !important"}
                    }

                    AgGrid(
                        df_final,
                        gridOptions=gridOptions,
                        enable_enterprise_modules=False,
                        allow_unsafe_jscode=True,
                        theme='alpine',
                        custom_css=grid_css,
                        fit_columns_on_grid_load=True, 
                        height=550
                    )
                else:
                    st.info("Nenhum pedido encontrado para os filtros selecionados.")
                
        else:
            st.info(f"Base de dados limpa. Nenhuma carga alocada para {st.session_state.cliente}.")
    else:
        st.warning("Aguardando carregamento da estrutura. Verifique a conexão com a nuvem.")
