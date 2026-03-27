import streamlit as st
import pandas as pd
import gspread
import os
import time

# =======================================================
# ⚙️ CONFIGURAÇÃO PREMIUM & VISUAL (INDUSTRIAL NAVY)
# =======================================================
st.set_page_config(page_title="Portal GRALAB | IGO Logística", page_icon="📦", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
        .block-container { padding-top: 1rem; padding-bottom: 1rem; padding-left: 2rem; padding-right: 2rem; }
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .stApp { background-color: #EDF2F7; }
        div[data-testid="metric-container"] {
            background-color: #ffffff; border: 1px solid #e2e8f0; padding: 20px;
            border-radius: 10px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
        }
        .header-navy {
            background-color: #001C46; color: #ffffff; padding: 20px;
            border-radius: 12px; margin-bottom: 25px; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.2);
        }
        .header-navy h2 { color: #ffffff !important; margin: 0; font-size: 28px; }
        .header-navy p { color: #E2E8F0 !important; margin: 5px 0 0 0; font-size: 14px; }
        [data-testid="stForm"] {
            background-color: #ffffff; border-radius: 15px; padding: 40px;
            border: 1px solid #e2e8f0; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1);
        }
        .stButton > button {
            background-color: #001C46 !important; color: white !important;
            border-radius: 8px !important; border: none !important; height: 45px !important; font-weight: bold !important;
        }
        .stButton > button:hover { background-color: #002D72 !important; }
        [data-testid="stDataFrame"] {
            background-color: #ffffff; padding: 10px; border-radius: 12px; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1);
        }
    </style>
""", unsafe_allow_html=True)

# =======================================================
# 🔗 CONEXÃO COM O BANCO DE DADOS
# =======================================================
@st.cache_data(ttl=30) 
def carregar_dados_nuvem():
    DIRETORIO_USUARIO = os.path.expanduser("~")
    PASTA_SISTEMA = os.path.join(DIRETORIO_USUARIO, "IGO_Logistica_Sistema")
    ARQUIVO_CREDENCIAIS = os.path.join(PASTA_SISTEMA, "credentials.json")
    ARQUIVO_TOKEN = os.path.join(PASTA_SISTEMA, "token.json")
    try:
        cliente_gspread = gspread.oauth(credentials_filename=ARQUIVO_CREDENCIAIS, authorized_user_filename=ARQUIVO_TOKEN)
        planilha = cliente_gspread.open("DB_IGO_Logistica")
        dados = planilha.worksheet("Memoria_Sistema").get_all_values()
        if len(dados) > 1: return pd.DataFrame(dados[1:], columns=dados[0])
    except: pass
    return pd.DataFrame()

# =======================================================
# 🔒 LOGIN
# =======================================================
if 'logado' not in st.session_state:
    st.session_state['logado'] = False

if not st.session_state['logado']:
    _, col_login, _ = st.columns([1, 1.5, 1])
    with col_login:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        with st.form("login_form"):
            st.markdown("<h1 style='text-align: center; color: #001C46; margin-top:0;'>Portal do Cliente</h1>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: #64748b;'>Rastreamento Exclusivo IGO Logística</p>", unsafe_allow_html=True)
            
            usuario = st.text_input("Usuário (Nome da Empresa):", placeholder="Digite: gralab")
            senha = st.text_input("Senha:", type="password", placeholder="Digite: 123")
            st.markdown("<br>", unsafe_allow_html=True)
            submit = st.form_submit_button("Entrar no Painel", use_container_width=True)
            
            if submit:
                if usuario.lower() == 'gralab' and senha == '123':
                    st.success("Login aprovado! Carregando dados...")
                    time.sleep(1)
                    st.session_state['logado'] = True
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")

# =======================================================
# 🌐 DASHBOARD INDUSTRIAL NAVY
# =======================================================
else:
    df_sistema = carregar_dados_nuvem()
    df_cliente = df_sistema[df_sistema['TOMADOR'].astype(str).str.upper() == 'GRALAB'].copy()

    st.markdown(f"""
        <div class="header-navy">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div><h2>🔬 GRALAB - Visão de Operações</h2><p>Atualizado em Tempo Real | Operado por IGO Logística</p></div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    if df_cliente.empty:
        st.info("Nenhuma carga encontrada para este cliente no momento.")
        if st.button("Sair do Sistema"):
            st.session_state['logado'] = False
            st.rerun()
    else:
        total = len(df_cliente)
        entregues = len(df_cliente[df_cliente['STATUS'].isin(['ENTREGUE', 'SUCESSO'])])
        em_rota = len(df_cliente[df_cliente['STATUS'].isin(['EM ROTA', 'EM ROTA DE ENTREGA'])])
        problemas = len(df_cliente[df_cliente['STATUS'].isin(['FRUSTRADA', 'PROBLEMA NA ENTREGA', 'CANCELADO'])])
        pendentes = total - entregues - em_rota - problemas
        taxa_sucesso = f"{(entregues/total)*100:.1f}%" if total > 0 else "0%"

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("📦 Volume Total", total)
        c2.metric("✅ Entregues", entregues, taxa_sucesso)
        c3.metric("🚚 Em Rota", em_rota)
        c4.metric("⏳ Pendentes", pendentes)
        c5.metric("⚠️ Ocorrências", problemas, "- Atenção", delta_color="inverse")

        st.markdown("<br>", unsafe_allow_html=True)
        
        # =======================================================
        # 📸 MÁGICA DA FOTO: CONSTRUINDO O LINK DO APPSHEET
        # =======================================================
        APP_NAME = "APPIGOLOGISTICA-153047553"
        
        def gerar_url_foto(foto_nome):
            if pd.isna(foto_nome) or str(foto_nome).strip() in ["", "NAN", "NONE", "📎", "📸"]:
                return None # Sem foto
            return f"https://www.appsheet.com/template/gettablefileurl?appName={APP_NAME}&tableName=App_Tarefas&fileName={str(foto_nome).strip()}"

        # Se existir a coluna FOTO no Google Sheets, criamos a coluna COMPROVANTE com os links!
        if 'FOTO' in df_cliente.columns:
            df_cliente['COMPROVANTE'] = df_cliente['FOTO'].apply(gerar_url_foto)
        else:
            df_cliente['COMPROVANTE'] = None
        
        # Selecionamos as colunas finais
        colunas_cliente = ['DATA', 'PEDIDO', 'LABORATORIO', 'ENDERECO', 'NUMERO', 'BAIRRO', 'CIDADE', 'UF', 'DATA_LIMITE', 'DATA_ENTREGA', 'STATUS', 'COMPROVANTE']
        df_mostrar = df_cliente[[c for c in colunas_cliente if c in df_cliente.columns]].copy()
        renomeios = {'ENDERECO': 'RUA', 'NUMERO': 'NUM', 'DATA_LIMITE': 'PREVISÃO', 'DATA_ENTREGA': 'ENTREGA REAL'}
        df_mostrar.rename(columns=renomeios, inplace=True)

        st.markdown("<h5 style='color: #001C46;'>🔍 Filtros de Rastreio</h5>", unsafe_allow_html=True)
        col_f1, col_f2, col_f3 = st.columns([2, 1.5, 1.5])
        with col_f1: busca_texto = st.text_input("Busca Rápida:", placeholder="Digite um Pedido, Rua, Lab...")
        with col_f2: cidade_filtro = st.multiselect("Filtrar por Cidade:", options=sorted([str(c) for c in df_mostrar['CIDADE'].unique() if str(c).strip() != ""]))
        with col_f3: status_filtro = st.multiselect("Filtrar por Status:", options=sorted([str(s) for s in df_mostrar['STATUS'].unique() if str(s).strip() != ""]))
            
        df_filtrado = df_mostrar.copy()
        if busca_texto: df_filtrado = df_filtrado[df_filtrado.astype(str).apply(lambda x: x.str.contains(busca_texto, case=False, na=False)).any(axis=1)]
        if cidade_filtro: df_filtrado = df_filtrado[df_filtrado['CIDADE'].isin(cidade_filtro)]
        if status_filtro: df_filtrado = df_filtrado[df_filtrado['STATUS'].isin(status_filtro)]

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: #64748b; font-size: 13px; margin-bottom: 5px;'>Exibindo {len(df_filtrado)} resultado(s)</p>", unsafe_allow_html=True)
        
        # =======================================================
        # ✨ CONFIGURANDO A GRID COM O LINK CLICÁVEL
        # =======================================================
        st.dataframe(
            df_filtrado, 
            use_container_width=True, 
            hide_index=True, 
            height=450,
            column_config={
                "COMPROVANTE": st.column_config.LinkColumn(
                    "Comprovante",
                    help="Clique para abrir a foto da entrega em uma nova aba",
                    display_text="📸 Ver Foto"  # Isso disfarça a URL gigante e deixa o botão bonitinho!
                )
            }
        )
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Sair do Sistema"):
            st.session_state['logado'] = False
            st.rerun()