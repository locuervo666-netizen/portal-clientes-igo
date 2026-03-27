import streamlit as st
import pandas as pd
import gspread
import os
import json
from datetime import datetime, date

# =======================================================
# 🎨 1. CONFIGURAÇÃO DA PÁGINA E CSS AVANÇADO
# =======================================================
st.set_page_config(page_title="Portal IGO Logística", layout="wide", page_icon="🚚")

st.markdown("""
    <style>
    /* Reset visual e cores corporativas */
    [data-testid="stAppViewContainer"] { background-color: #f8f9fa; font-family: 'Inter', sans-serif; }
    #MainMenu, footer, header {visibility: hidden;}
    
    /* Customização dos Filtros e Inputs */
    .stTextInput>div>div>input, .stSelectbox>div>div>div, .stDateInput>div>div>input {
        border-radius: 8px; border: 1px solid #ced4da;
    }
    
    /* Cartões de Métricas Dinâmicas */
    [data-testid="stMetric"] {
        background-color: #ffffff; padding: 20px; border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.03); border-top: 4px solid #002e5d;
    }
    [data-testid="stMetricLabel"] { font-size: 14px; font-weight: 600; text-transform: uppercase; color: #6c757d; }
    [data-testid="stMetricValue"] { font-size: 32px; font-weight: 800; color: #111827; }
    
    /* Estilização da Grid (Tabela) */
    .stDataFrame { border-radius: 12px; overflow: hidden; border: 1px solid #e5e7eb; box-shadow: 0 4px 6px rgba(0,0,0,0.02); }
    
    /* Títulos */
    h1 { color: #002e5d; font-weight: 900; letter-spacing: -1px; }
    h3 { color: #374151; font-weight: 600; border-bottom: 2px solid #e5e7eb; padding-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# =======================================================
# 🔗 2. MOTOR DE DADOS E FORMATAÇÃO BRASILEIRA
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
            gc = gspread.oauth(
                credentials_filename=os.path.join(PASTA_SISTEMA, "credentials.json"),
                authorized_user_filename=os.path.join(PASTA_SISTEMA, "token.json")
            )
            
        planilha = gc.open("DB_IGO_Logistica")
        aba = planilha.worksheet("Memoria_Sistema")
        dados = aba.get_all_values()
        
        if len(dados) > 1:
            df = pd.DataFrame(dados[1:], columns=dados[0])
            df.columns = df.columns.str.strip().str.upper() 
            
            # Padronização de datas para leitura do calendário
            if 'DATA' in df.columns:
                # Converte para datetime para podermos filtrar com o calendário
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
            st.image("https://cdn-icons-png.flaticon.com/512/1532/1532692.png", width=70)
            st.markdown("<h2>Acesso ao Portal</h2>", unsafe_allow_html=True)
            st.markdown("<p style='color: #6c757d;'>IGO Logística - Área do Cliente</p>", unsafe_allow_html=True)
            
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
# 🚀 4. DASHBOARD ENTERPRISE (PÓS-LOGIN)
# =======================================================
else:
    df_sistema = carregar_dados_nuvem()

    # --- BARRA SUPERIOR E BOTÃO DE SAÍDA ---
    c_header1, c_header2 = st.columns([4, 1])
    with c_header1:
        st.markdown(f"<h1>Painel Operacional | {st.session_state.cliente}</h1>", unsafe_allow_html=True)
    with c_header2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚪 Sair com Segurança", use_container_width=True):
            st.session_state.logado = False
            st.rerun()

    if not df_sistema.empty and 'TOMADOR' in df_sistema.columns:
        # Isola os dados do cliente logado
        df_cliente = df_sistema[df_sistema['TOMADOR'] == st.session_state.cliente].copy()
        
        if not df_cliente.empty:
            
            # --- SEÇÃO DE FILTROS AVANÇADOS ---
            st.markdown("### 🔍 Central de Filtros")
            
            f1, f2, f3 = st.columns([1, 1.5, 1])
            
            # 1. Filtro de Calendário (Período)
            with f1:
                # Pega a menor e maior data disponíveis na planilha para o limite do calendário
                min_date = df_cliente['DATA_OBJ'].dropna().min() if 'DATA_OBJ' in df_cliente.columns else date.today()
                max_date = df_cliente['DATA_OBJ'].dropna().max() if 'DATA_OBJ' in df_cliente.columns else date.today()
                
                datas_selecionadas = st.date_input(
                    "Período da Coleta/Entrega:",
                    value=(min_date, max_date),
                    min_value=min_date,
                    max_value=max_date,
                    format="DD/MM/YYYY"
                )
            
            # 2. Filtro de Cidades (Múltipla Escolha)
            with f2:
                lista_cidades = sorted(df_cliente['CIDADE'].dropna().unique().tolist()) if 'CIDADE' in df_cliente.columns else []
                cidades_selecionadas = st.multiselect("Filtrar por Cidades:", options=lista_cidades, default=lista_cidades)
                
            # 3. Busca Direta por Pedido
            with f3:
                busca_pedido = st.text_input("Buscar Número do Pedido:", placeholder="Digite o Pedido ou PCL...")

            # --- APLICANDO A LÓGICA DE FILTRAGEM ---
            df_filtrado = df_cliente.copy()
            
            # Filtra Calendário
            if len(datas_selecionadas) == 2 and 'DATA_OBJ' in df_filtrado.columns:
                data_inicio, data_fim = datas_selecionadas
                df_filtrado = df_filtrado[(df_filtrado['DATA_OBJ'] >= data_inicio) & (df_filtrado['DATA_OBJ'] <= data_fim)]
                
            # Filtra Cidades
            if cidades_selecionadas and 'CIDADE' in df_filtrado.columns:
                df_filtrado = df_filtrado[df_filtrado['CIDADE'].isin(cidades_selecionadas)]
                
            # Filtra Busca (Busca tanto no Pedido quanto no PCL)
            if busca_pedido:
                busca = str(busca_pedido).upper()
                cond_pedido = df_filtrado['PEDIDO'].astype(str).str.upper().str.contains(busca) if 'PEDIDO' in df_filtrado.columns else False
                cond_pcl = df_filtrado['PCL'].astype(str).str.upper().str.contains(busca) if 'PCL' in df_filtrado.columns else False
                df_filtrado = df_filtrado[cond_pedido | cond_pcl]

            # --- CARDS DE KPIs (Atualizam junto com os filtros) ---
            st.markdown("<br>", unsafe_allow_html=True)
            kpi1, kpi2, kpi3 = st.columns(3)
            
            total_filtrado = len(df_filtrado)
            cidades_filtradas = df_filtrado['CIDADE'].nunique() if 'CIDADE' in df_filtrado.columns else 0
            
            kpi1.metric("📦 Volume de Pedidos", f"{total_filtrado}")
            kpi2.metric("📍 Cobertura Filtrada", f"{cidades_filtradas} Cidades")
            kpi3.metric("🔄 Sincronização", datetime.now().strftime("%H:%M:%S"))

            # --- GOVERNANÇA DE DADOS (A GRID DO CLIENTE) ---
            st.markdown("<br>### 📋 Espelho de Cargas", unsafe_allow_html=True)
            
            # Ordenação oficial: Ordem Alfabética de Cidade
            if 'CIDADE' in df_filtrado.columns:
                df_filtrado = df_filtrado.sort_values(by='CIDADE', ascending=True)

            # Define EXATAMENTE o que o cliente pode ver (esconde QR Code, Telefones, etc.)
            colunas_permitidas = ['DATA', 'PEDIDO', 'PCL', 'CIDADE', 'UF', 'BAIRRO', 'RUA', 'NUMERO', 'CEP']
            colunas_exibicao = [col for col in colunas_permitidas if col in df_filtrado.columns]
            
            df_final = df_filtrado[colunas_exibicao].copy()
            
            if not df_final.empty:
                st.dataframe(
                    df_final,
                    use_container_width=True,
                    hide_index=True,
                    height=500
                )
            else:
                st.warning("Nenhum pedido encontrado para os filtros selecionados.")
                
        else:
            st.info(f"Base de dados limpa. Nenhuma carga alocada para {st.session_state.cliente}.")
    else:
        st.warning("Aguardando carregamento da estrutura. Verifique a conexão com o Google Sheets.")
