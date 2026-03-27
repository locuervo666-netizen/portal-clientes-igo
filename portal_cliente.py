import streamlit as st
import pandas as pd
import gspread
import os
import json
from datetime import datetime, date
from streamlit_autorefresh import st_autorefresh

# =======================================================
# 🎨 1. CONFIGURAÇÃO DA PÁGINA
# =======================================================
st.set_page_config(page_title="Portal IGO Logística", layout="wide", page_icon="🚚", initial_sidebar_state="expanded")

# ⏱️ Atualização Automática (60 segundos)
st_autorefresh(interval=60000, limit=None, key="refresh_timer")

# 🖌️ CSS Ajustado: Métricas mais discretas e layout mais "Clean"
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #f4f6f9; font-family: 'Inter', sans-serif; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {background-color: transparent !important;}
    .stTextInput>div>div>input, .stSelectbox>div>div>div, .stDateInput>div>div>input, .stMultiSelect>div>div>div { border-radius: 6px; border: 1px solid #ced4da; }
    
    /* 📉 PAINÉIS MAIS DISCRETOS E COMPACTOS */
    [data-testid="stMetric"] { 
        background-color: #ffffff; 
        padding: 10px 15px; 
        border-radius: 6px; 
        box-shadow: 0 1px 3px rgba(0,0,0,0.05); 
        border-left: 4px solid #002e5d; 
    }
    [data-testid="stMetricLabel"] { font-size: 12px; font-weight: 600; text-transform: uppercase; color: #6c757d; }
    [data-testid="stMetricValue"] { font-size: 20px; font-weight: 800; color: #002e5d; }
    
    /* TABELA E TÍTULOS */
    .stDataFrame { border-radius: 8px; overflow: hidden; border: 1px solid #e2e8f0; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }
    h1 { color: #002e5d; font-weight: 800; font-size: 26px; letter-spacing: -0.5px; margin-bottom: 0px; }
    .subtitle { color: #6c757d; font-size: 14px; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

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
        st.error(f"Falha de sincronização com o servidor: {e}")
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
            st.image("https://cdn-icons-png.flaticon.com/512/1532/1532692.png", width=60)
            st.markdown("<h2 style='font-size: 22px;'>Acesso ao Portal</h2>", unsafe_allow_html=True)
            st.markdown("<p style='color: #6c757d; font-size: 14px;'>IGO Logística - Área do Cliente</p>", unsafe_allow_html=True)
            
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
# 🚀 4. DASHBOARD ENTERPRISE V8
# =======================================================
else:
    df_sistema = carregar_dados_nuvem()

    if not df_sistema.empty and 'TOMADOR' in df_sistema.columns:
        df_cliente = df_sistema[df_sistema['TOMADOR'] == st.session_state.cliente].copy()
        
        if not df_cliente.empty:
            
            ordem_padrao = ['PEDIDO', 'DATA', 'STATUS', 'LABORATORIO', 'CIDADE', 'UF', 'BAIRRO', 'ENDERECO', 'Nº', 'CEP', 'DATA_LIMITE', 'DATA_ENTREGA', 'FOTO_URL']
            colunas_disponiveis = [col for col in ordem_padrao if col in df_cliente.columns]

            # --- BARRA LATERAL (FILTROS) ---
            with st.sidebar:
                st.image("https://cdn-icons-png.flaticon.com/512/1532/1532692.png", width=50)
                st.markdown(f"#### Olá, **{st.session_state.cliente}**")
                st.markdown("---")
                
                st.markdown("##### 🔍 Filtros de Busca")
                min_date = df_cliente['DATA_OBJ'].dropna().min() if 'DATA_OBJ' in df_cliente.columns else date.today()
                max_date = df_cliente['DATA_OBJ'].dropna().max() if 'DATA_OBJ' in df_cliente.columns else date.today()
                
                datas_selecionadas = st.date_input("Período:", value=(min_date, max_date), min_value=min_date, max_value=max_date, format="DD/MM/YYYY")
                
                lista_cidades = sorted(df_cliente['CIDADE'].dropna().unique().tolist()) if 'CIDADE' in df_cliente.columns else []
                cidades_selecionadas = st.multiselect("Cidades:", options=lista_cidades, default=lista_cidades)
                
                busca_pedido = st.text_input("Buscar Pedido ou Nº:")
                st.markdown("---")
                
                st.markdown("##### ⚙️ Personalizar Tabela")
                colunas_selecionadas = st.multiselect("Colunas visíveis:", options=colunas_disponiveis, default=colunas_disponiveis)
                st.markdown("---")
                
                if st.button("🚪 Sair do Sistema", use_container_width=True):
                    st.session_state.logado = False
                    st.rerun()

            # --- APLICANDO FILTROS ---
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

            # --- ÁREA PRINCIPAL ---
            c_titulo, c_botao = st.columns([3, 1])
            with c_titulo:
                st.markdown(f"<h1>Espelho de Cargas | {st.session_state.cliente}</h1>", unsafe_allow_html=True)
                st.markdown(f"<p class='subtitle'>Acompanhamento atualizado automaticamente a cada 60s.</p>", unsafe_allow_html=True)
            with c_botao:
                st.markdown("<br>", unsafe_allow_html=True)
                csv_data = df_filtrado[colunas_selecionadas].to_csv(index=False, sep=";").encode('utf-8-sig')
                st.download_button(label="📥 Baixar Excel", data=csv_data, file_name=f"Relatorio_{st.session_state.cliente}.csv", mime="text/csv", use_container_width=True)

            # Painéis Menores e Discretos (Pegando menos largura da tela)
            kpi1, kpi2, kpi3, kpi4 = st.columns([1, 1, 1, 2])
            kpi1.metric("📦 Volume", f"{len(df_filtrado)}")
            kpi2.metric("📍 Cidades", f"{df_filtrado['CIDADE'].nunique() if 'CIDADE' in df_filtrado.columns else 0}")
            
            # --- 🛠️ LÓGICA DE STATUS COM ALERTA DE ATRASO (FAROL) ---
            hoje = date.today()
            def tratar_status_e_atrasos(row):
                status = str(row.get('STATUS', '')).strip().upper()
                previsao_str = str(row.get('DATA_LIMITE', '')).strip()
                
                if status == 'ENTREGUE': status = '✅ Entregue'
                elif status in ['EM ROTA', 'EM ROTA DE ENTREGA']: status = '🚚 Em Rota'
                elif status == 'COLETADO': status = '📦 Coletado'
                elif status == 'CANCELADO': status = '❌ Cancelado'
                else: status = f'⏳ {status}'
                
                if status not in ['✅ Entregue', '❌ Cancelado'] and previsao_str:
                    try:
                        data_previsao = datetime.strptime(previsao_str, "%d/%m/%Y").date()
                        if data_previsao < hoje:
                            status = f"🚨 ATRASADO ({status})"
                    except:
                        pass
                return status
                
            if 'STATUS' in df_filtrado.columns:
                df_filtrado['STATUS'] = df_filtrado.apply(tratar_status_e_atrasos, axis=1)

            # --- EXIBIÇÃO DA TABELA DINÂMICA ---
            if 'CIDADE' in df_filtrado.columns:
                df_filtrado = df_filtrado.sort_values(by=['CIDADE', 'DATA'], ascending=[True, False])

            if not colunas_selecionadas:
                st.warning("Selecione pelo menos uma coluna no menu lateral para visualizar os dados.")
            else:
                df_final = df_filtrado[colunas_selecionadas].copy()
                
                if not df_final.empty:
                    config_colunas = {}
                    if 'FOTO_URL' in df_final.columns:
                        config_colunas['FOTO_URL'] = st.column_config.LinkColumn("Comprovante", display_text="🔗 Ver Foto")
                    if 'DATA_LIMITE' in df_final.columns:
                        config_colunas['DATA_LIMITE'] = "Previsão"
                    if 'DATA_ENTREGA' in df_final.columns:
                        config_colunas['DATA_ENTREGA'] = "Entregue Em"

                    # 🎯 A MÁGICA DA SELEÇÃO FUNCIONANDO! 
                    # Removemos o "estilo zebra" manual para o Streamlit poder aplicar o fundo azul/cinza na linha quando clicada.
                    st.dataframe(
                        df_final, 
                        use_container_width=True, 
                        hide_index=True, 
                        height=550, 
                        column_config=config_colunas,
                        on_select="ignore",           # Ignora o recarregamento da página para não travar
                        selection_mode="single_row"   # Permite clicar e selecionar a LINHA INTEIRA!
                    )
                else:
                    st.warning("Nenhum pedido encontrado para os filtros selecionados.")
                
        else:
            st.info(f"Base de dados limpa. Nenhuma carga alocada para {st.session_state.cliente}.")
    else:
        st.warning("Aguardando carregamento da estrutura. Verifique a conexão com a nuvem.")
