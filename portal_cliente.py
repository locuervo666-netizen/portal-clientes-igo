import streamlit as st
import pandas as pd
import gspread
import os
import json

# =======================================================
# 🎨 CONFIGURAÇÃO DA PÁGINA (ESTILO PREMIUM IGO)
# =======================================================
st.set_page_config(page_title="Portal do Cliente - IGO Logística", layout="wide", page_icon="🚚")

st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; background-color: #002e5d; color: white; border-radius: 8px; }
    .stTextInput>div>div>input { border-radius: 8px; }
    .card { background-color: #ffffff; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    h1 { color: #002e5d; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    </style>
    """, unsafe_allow_html=True)

# =======================================================
# 🔗 CONEXÃO COM O BANCO DE DADOS (BLINDADA)
# =======================================================
@st.cache_data(ttl=60) 
def carregar_dados_nuvem():
    try:
        # ☁️ Tenta ler do cofre do Streamlit (NUVEM)
        if "google_credentials" in st.secrets:
            cred_dict = json.loads(st.secrets["google_credentials"])
            token_dict = json.loads(st.secrets["google_token"])
            
            # Cria arquivos temporários para o gspread ler
            with open("cred_temp.json", "w") as f: json.dump(cred_dict, f)
            with open("token_temp.json", "w") as f: json.dump(token_dict, f)
            
            gc = gspread.oauth(credentials_filename="cred_temp.json", authorized_user_filename="token_temp.json")
        
        # 💻 Se não achar segredos, tenta ler da sua pasta (LOCAL)
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
            
            # 🧹 LIMPEZA DE CABEÇALHO (O segredo para não dar KeyError)
            # Remove espaços no início/fim e deixa tudo em MAIÚSCULO
            df.columns = df.columns.str.strip().str.upper()
            
            return df
    except Exception as e:
        st.error(f"Erro crítico de conexão: {e}")
    return pd.DataFrame()

# =======================================================
# 🔐 SISTEMA DE LOGIN
# =======================================================
if 'logado' not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.image("https://cdn-icons-png.flaticon.com/512/1532/1532692.png", width=100)
        st.title("Portal IGO Logística")
        st.subheader("Acesse suas informações de carga")
        
        usuario = st.text_input("Usuário (Cliente)")
        senha = st.text_input("Senha", type="password")
        
        if st.button("Entrar no Sistema"):
            # Login simples conforme planejado
            if usuario.lower() == "gralab" and senha == "123":
                st.session_state.logado = True
                st.session_state.cliente = "GRALAB"
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")
else:
    # =======================================================
    # 🚀 DASHBOARD DO CLIENTE (PÓS-LOGIN)
    # =======================================================
    df_sistema = carregar_dados_nuvem()

    # Barra Lateral
    st.sidebar.image("https://cdn-icons-png.flaticon.com/512/1532/1532692.png", width=80)
    st.sidebar.title(f"Olá, {st.session_state.cliente}")
    if st.sidebar.button("Sair"):
        st.session_state.logado = False
        st.rerun()

    st.title(f"Painel de Cargas - {st.session_state.cliente}")
    st.write("Acompanhe abaixo o status das suas coletas e entregas em tempo real.")

    if not df_sistema.empty:
        # 🔍 FILTRO INTELIGENTE
        # Ele procura na coluna 'TOMADOR' o nome do cliente logado
        try:
            df_filtrado = df_sistema[df_sistema['TOMADOR'].str.upper() == st.session_state.cliente].copy()
            
            if not df_filtrado.empty:
                # Mostra os principais indicadores
                c1, c2, c3 = st.columns(3)
                c1.metric("Total de Pedidos", len(df_filtrado))
                c2.metric("Cidades Atendidas", len(df_filtrado['CIDADE'].unique()))
                c3.metric("Status", "Operação Ativa")

                st.divider()
                
                # Exibe a tabela com os dados
                st.dataframe(df_filtrado, use_container_width=True, hide_index=True)
            else:
                st.warning(f"Nenhum dado encontrado para o tomador {st.session_state.cliente} na planilha.")
        except KeyError:
            st.error("ERRO: A coluna 'TOMADOR' não foi encontrada na planilha. Verifique se o nome na primeira linha está correto.")
    else:
        st.info("Aguardando carregamento dos dados da planilha...")

st.markdown("<br><hr><center>IGO Logística - Inteligência em Movimento</center>", unsafe_allow_html=True)
