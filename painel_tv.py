import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import json
import gspread
from streamlit_autorefresh import st_autorefresh
from google.oauth2.credentials import Credentials

FUSO_BR = timezone(timedelta(hours=-3))

# =============================================================================
# 1. CONFIGURAÇÃO DA PÁGINA E AUTO-REFRESH
# =============================================================================
st.set_page_config(page_title="C.C.O TV - Alerta SLA", layout="wide", page_icon="🚨")
st_autorefresh(interval=60000, limit=None, key="tv_refresh_atrasos")

# =============================================================================
# 2. CONEXÃO COM O BANCO DE DADOS
# =============================================================================
@st.cache_resource
def conectar_banco():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        if "google_token_json" in st.secrets:
            token_info = json.loads(st.secrets["google_token_json"])
            creds = Credentials.from_authorized_user_info(token_info, scopes)
            gc = gspread.authorize(creds)
            return gc.open("DB_IGO_Logistica")
        else:
            return None
    except Exception:
        return None

@st.cache_data(ttl=20)
def carregar_dados_completos(_planilha):
    if not _planilha: return pd.DataFrame()
    try:
        aba_m = _planilha.worksheet("Memoria_Sistema")
        dados_m = aba_m.get_all_values()
        if len(dados_m) > 1:
            df = pd.DataFrame(dados_m[1:], columns=dados_m[0])
            df.columns = df.columns.str.strip().str.upper() 
            try:
                aba_app = _planilha.worksheet("App_Tarefas")
                dados_app = aba_app.get_all_values()
                if len(dados_app) > 1:
                    df_app = pd.DataFrame(dados_app[1:], columns=dados_app[0])
                    cols_limpas = [str(c).upper().strip().replace('?', '').replace(' ', '') for c in df_app.columns]
                    df_app.columns = cols_limpas
                    
                    cols_to_extract = ['PEDIDO', 'STATUS']
                    df_app_clean = df_app[[c for c in cols_to_extract if c in df_app.columns]].copy()
                    df_app_clean.rename(columns={'STATUS': 'APP_STATUS'}, inplace=True)
                    df_app_clean['PEDIDO'] = df_app_clean['PEDIDO'].astype(str).str.strip()
                    df_app_clean.drop_duplicates(subset=['PEDIDO'], keep='last', inplace=True)
                    
                    rom_mask = df_app_clean['PEDIDO'].str.startswith('ROM-', na=False)
                    rom_dict = df_app_clean[rom_mask].set_index('PEDIDO').to_dict('index')
                    
                    df['PEDIDO'] = df['PEDIDO'].astype(str).str.strip()
                    df = pd.merge(df, df_app_clean, on='PEDIDO', how='left')
                    
                    def get_true_status(row):
                        s_db = str(row.get('STATUS', '')).strip().upper()
                        s_app = str(row.get('APP_STATUS', '')).strip().upper()
                        rom_id = str(row.get('ROMANEIO', '')).strip()
                        if rom_id in rom_dict:
                            s_rom = str(rom_dict[rom_id].get('APP_STATUS', '')).strip().upper()
                            if s_rom in ['ENTREGUE', 'FRUSTRADA', 'PROBLEMA', 'CANCELADO']: return s_rom
                        if s_db in ['ENTREGUE', 'CANCELADO', 'FRUSTRADA', 'PROBLEMA']: return s_db
                        if s_app in ['ENTREGUE', 'CANCELADO', 'FRUSTRADA', 'PROBLEMA']: return s_app
                        if s_db in ['EM ROTA DE ENTREGA', 'CONFERIDO']: return s_db
                        if s_app and s_app != 'NAN': return s_app
                        return s_db
                    
                    df['STATUS'] = df.apply(get_true_status, axis=1)
            except Exception: pass
            
            if 'DATA' in df.columns: df['DATA_OBJ'] = pd.to_datetime(df['DATA'], format='%d/%m/%Y', errors='coerce').dt.date
            if 'DATA_LIMITE' in df.columns: df['DATA_LIMITE_OBJ'] = pd.to_datetime(df['DATA_LIMITE'], format='%d/%m/%Y', errors='coerce').dt.date
            return df
    except Exception: pass
    return pd.DataFrame()

def calc_status_display(row):
    status_final = str(row.get('STATUS', '')).strip().upper()
    if 'COLETADO' in status_final: return 'Coletado'
    elif 'FRUSTRADA' in status_final or 'PROBLEMA' in status_final or 'CANCELADO' in status_final: return 'Frustrada'
    return 'Pendente'

# =============================================================================
# 🎨 3. CSS TÁTICO (FOCO EM ALERTAS / VERMELHO)
# =============================================================================
st.markdown("""
<style>
    /* Ocultar elementos nativos Streamlit */
    #MainMenu {visibility: hidden !important;}
    header {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    .stDeployButton {display: none !important;}
    iframe[src*="manage"] {display: none !important;}
    [data-testid="manage-app-button"] {display: none !important;}
    
    .block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; margin-top: 0 !important; }
    [data-testid="stAppViewContainer"] { background-color: #F8FAFC !important; }
    
    /* Cartões Táticos */
    .metric-card-alert { 
        border-radius: 12px; padding: 20px; height: 140px; display: flex; flex-direction: column; 
        justify-content: space-between; margin-bottom: 10px; border: 1px solid #FECACA;
        background: linear-gradient(135deg, #FEF2F2 0%, #FEE2E2 100%);
        box-shadow: 0 4px 10px rgba(220, 38, 38, 0.1);
    }
    .metric-card-info { 
        border-radius: 12px; padding: 20px; height: 140px; display: flex; flex-direction: column; 
        justify-content: space-between; margin-bottom: 10px; border: 1px solid #E2E8F0;
        background-color: #FFFFFF; box-shadow: 0 4px 10px rgba(0,0,0,0.03);
    }
    .metric-title { font-size: 13px; font-weight: 900; text-transform: uppercase; letter-spacing: 0.5px; opacity: 0.8;}
    .metric-value { font-size: 48px; font-weight: 900; font-family: 'Segoe UI', sans-serif; line-height: 1; margin: 3px 0;}
    .metric-sub { font-size: 14px; font-weight: 700; color: #475569;}
    
    /* Tabela Premium Customizada */
    [data-testid="stDataFrame"] { background-color: #FFFFFF; border-radius: 10px; border: 1px solid #E2E8F0; box-shadow: 0 4px 15px rgba(0,0,0,0.04);}
    th { color: #0F172A !important; font-size: 15px !important; font-weight: 900 !important; background-color: #F1F5F9 !important;}
    td { font-size: 16px !important; font-weight: 600; color: #334155 !important;}
</style>
""", unsafe_allow_html=True)

# =============================================================================
# 🚀 4. LÓGICA DE PROCESSAMENTO (FILTRO DE ATRASOS)
# =============================================================================
planilha_db = conectar_banco()
df_raw = carregar_dados_completos(planilha_db)
hoje_br = datetime.now(FUSO_BR).date()
hora_atual = datetime.now(FUSO_BR).strftime('%H:%M:%S')

st.markdown("<h3 style='color: #0F172A; font-weight: 900; margin-bottom: 5px; font-family: sans-serif;'>🚨 C.C.O TÁTICO: PAINEL DE AÇÃO E ATRASOS (SLA)</h3>", unsafe_allow_html=True)

if df_raw.empty:
    st.info("Aguardando dados da base central...")
else:
    df_raw['STATUS_DISPLAY'] = df_raw.apply(calc_status_display, axis=1)
    
    # Filtro rigoroso: Pendente + data limite já passou
    if 'DATA_LIMITE_OBJ' in df_raw.columns:
        df_atrasados = df_raw[(df_raw['STATUS_DISPLAY'] == 'Pendente') & (df_raw['DATA_LIMITE_OBJ'] < hoje_br)].copy()
    elif 'DATA_OBJ' in df_raw.columns:
        df_atrasados = df_raw[(df_raw['STATUS_DISPLAY'] == 'Pendente') & (df_raw['DATA_OBJ'] < hoje_br)].copy()
    else:
        df_atrasados = pd.DataFrame()

    total_atrasados = len(df_atrasados)

    if total_atrasados == 0:
        st.success("✅ **EXCELENTE:** Operação impecável! Nenhum volume em atraso crítico identificado na base de dados.")
    else:
        # Lógica para identificar a coluna correta de Nome do Agente
        cols_disponiveis = df_atrasados.columns.tolist()
        col_nome_agente = next((col for col in ['MOTORISTA', 'NOME_MOTORISTA', 'NOME_AGENTE', 'NOME', 'AGENTE', 'ENTREGADOR'] if col in cols_disponiveis), None)
        if not col_nome_agente and 'AGENTE_RAW' in cols_disponiveis:
            col_nome_agente = 'AGENTE_RAW' # Fallback para o ID se o nome não existir
            
        # Encontrar Motorista Mais Crítico
        if col_nome_agente and not df_atrasados[col_nome_agente].isna().all():
            motorista_critico = df_atrasados[col_nome_agente].value_counts().idxmax()
            vols_motorista = df_atrasados[col_nome_agente].value_counts().max()
            if str(motorista_critico).strip() == "" or str(motorista_critico).upper() == "NAN":
                motorista_critico = "Base (Não Roteirizado)"
        else:
            motorista_critico = "Não Atribuído"
            vols_motorista = total_atrasados
            
        # Calcular dias de atraso
        def calc_dias_atraso(row):
            data_ref = row.get('DATA_LIMITE_OBJ', row.get('DATA_OBJ'))
            if pd.notnull(data_ref):
                return (hoje_br - data_ref).days
            return 1
            
        df_atrasados['DIAS_ATRASO'] = df_atrasados.apply(calc_dias_atraso, axis=1)
        atraso_maximo = df_atrasados['DIAS_ATRASO'].max()

        # ================== BLOCOS DE MÉTRICAS TÁTICAS ==================
        c1, c2, c3 = st.columns(3)
        
        with c1:
            st.markdown(f"""
            <div class="metric-card-alert">
                <div class="metric-title" style="color: #B91C1C;">🚨 VOLUMES EM ATRASO CRÍTICO</div>
                <div class="metric-value" style="color: #7F1D1D;">{total_atrasados}</div>
                <div class="metric-sub" style="color: #B91C1C;">SLA Rompido aguardando ação</div>
            </div>
            """, unsafe_allow_html=True)
            
        with c2:
            st.markdown(f"""
            <div class="metric-card-info">
                <div class="metric-title" style="color: #475569;">👤 MOTORISTA/PONTO MAIS IMPACTADO</div>
                <div class="metric-value" style="color: #0F172A; font-size: 32px; margin-top: 15px;">{motorista_critico}</div>
                <div class="metric-sub">Concentra <b style="color:#EF4444;">{vols_motorista}</b> pendências vencidas</div>
            </div>
            """, unsafe_allow_html=True)

        with c3:
            st.markdown(f"""
            <div class="metric-card-info" style="border-left: 5px solid #F59E0B;">
                <div class="metric-title" style="color: #475569;">⏳ PEDIDO MAIS ANTIGO</div>
                <div class="metric-value" style="color: #B45309;">{atraso_maximo} <span style="font-size: 20px;">Dias</span></div>
                <div class="metric-sub">Dias de estouro no limite máximo</div>
            </div>
            """, unsafe_allow_html=True)

        # ================== LISTA COMPLETA DE DETALHES (TABELA WIDE) ==================
        st.markdown("<hr style='border: 1px solid #E2E8F0; margin-top: 5px; margin-bottom: 20px;'>", unsafe_allow_html=True)
        st.markdown("<h4 style='color: #0F172A; font-weight: 900; font-size: 18px; font-family: sans-serif;'>📋 LISTA DE INTERVENÇÃO (RADAR DE ATRASOS)</h4>", unsafe_allow_html=True)
        
        # Mapeamento Dinâmico de Colunas
        col_tomador = next((col for col in ['TOMADOR', 'CLIENTE', 'EMPRESA'] if col in cols_disponiveis), None)
        col_bairro = next((col for col in ['BAIRRO', 'DESTINO_BAIRRO', 'BAIRRO_COLETA'] if col in cols_disponiveis), None)
        col_cidade = next((col for col in ['CIDADE', 'DESTINO_CIDADE', 'MUNICIPIO'] if col in cols_disponiveis), None)
        col_uf = next((col for col in ['UF', 'ESTADO', 'DESTINO_UF'] if col in cols_disponiveis), None)
        
        # Construir a lista de colunas que vão aparecer na tela
        cols_exibicao = ['PEDIDO']
        if col_tomador: cols_exibicao.append(col_tomador)
        if col_nome_agente: cols_exibicao.append(col_nome_agente)
        if col_bairro: cols_exibicao.append(col_bairro)
        if col_cidade: cols_exibicao.append(col_cidade)
        if col_uf: cols_exibicao.append(col_uf)
        cols_exibicao.append('DIAS_ATRASO')
        
        # Prepara o DataFrame para exibição
        df_view = df_atrasados[cols_exibicao].sort_values(by='DIAS_ATRASO', ascending=False)
        
        # Configuração das Colunas no Streamlit
        configuracao_colunas = {
            "PEDIDO": st.column_config.TextColumn("📦 PEDIDO/AWB"),
            "DIAS_ATRASO": st.column_config.ProgressColumn("🔴 DIAS VENCIDOS", format="%d dias", min_value=0, max_value=int(atraso_maximo) + 2)
        }
        
        if col_tomador: configuracao_colunas[col_tomador] = st.column_config.TextColumn("🏢 CLIENTE")
        if col_nome_agente: configuracao_colunas[col_nome_agente] = st.column_config.TextColumn("👤 MOTORISTA")
        if col_bairro: configuracao_colunas[col_bairro] = st.column_config.TextColumn("📍 BAIRRO")
        if col_cidade: configuracao_colunas[col_cidade] = st.column_config.TextColumn("🏙️ CIDADE")
        if col_uf: configuracao_colunas[col_uf] = st.column_config.TextColumn("🗺️ UF")

        # Exibe a tabela pegando 100% da largura
        st.dataframe(
            df_view,
            column_config=configuracao_colunas,
            hide_index=True, 
            use_container_width=True, 
            height=450
        )

# --- RODAPÉ DISCRETO ---
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(f"""
<div style="text-align: center; color: #94A3B8; font-size: 10px; font-family: sans-serif; opacity: 0.6;">
    Sincronização Alerta SLA: {hora_atual}
</div>
""", unsafe_allow_html=True)
