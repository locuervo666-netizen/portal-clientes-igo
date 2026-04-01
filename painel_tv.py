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
    [data-testid="stDataFrame"] { background-color: #FFFFFF; border-radius: 10px; border: 1px solid #E2E8F0; box-shadow: 0 4px 6px rgba(0,0,0,0.02);}
</style>
""", unsafe_allow_html=True)

# =============================================================================
# 🚀 4. LÓGICA DE PROCESSAMENTO (FILTRO DE ATRASOS)
# =============================================================================
planilha_db = conectar_banco()
df_raw = carregar_dados_completos(planilha_db)
hoje_br = datetime.now(FUSO_BR).date()
hora_atual = datetime.now(FUSO_BR).strftime('%H:%M:%S')

st.markdown("<h3 style='color: #0F172A; font-weight: 900; margin-bottom: 5px;'>🚨 C.C.O TÁTICO: PAINEL DE AÇÃO E ATRASOS (SLA)</h3>", unsafe_allow_html=True)

if df_raw.empty:
    st.info("Aguardando dados da base central...")
else:
    df_raw['STATUS_DISPLAY'] = df_raw.apply(calc_status_display, axis=1)
    
    # 1. Filtro rigoroso: O que está Pendente E a data limite já passou (ontem ou antes)
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
        # 2. Cálculos Táticos
        # Motorista mais crítico
        agente_col = 'AGENTE_RAW' if 'AGENTE_RAW' in df_atrasados.columns else 'MOTORISTA'
        if agente_col in df_atrasados.columns:
            motorista_critico = df_atrasados[agente_col].value_counts().idxmax()
            vols_motorista = df_atrasados[agente_col].value_counts().max()
        else:
            motorista_critico = "Não Atribuído"
            vols_motorista = 0
            
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
                <div class="metric-title" style="color: #475569;">👤 MOTORISTA MAIS IMPACTADO</div>
                <div class="metric-value" style="color: #0F172A; font-size: 32px; margin-top: 15px;">{motorista_critico}</div>
                <div class="metric-sub">Possui <b style="color:#EF4444;">{vols_motorista}</b> pendências antigas</div>
            </div>
            """, unsafe_allow_html=True)

        with c3:
            st.markdown(f"""
            <div class="metric-card-info" style="border-left: 5px solid #F59E0B;">
                <div class="metric-title" style="color: #475569;">⏳ PEDIDO MAIS ANTIGO</div>
                <div class="metric-value" style="color: #B45309;">{atraso_maximo} <span style="font-size: 20px;">Dias</span></div>
                <div class="metric-sub">Dias de estouro no limite</div>
            </div>
            """, unsafe_allow_html=True)

        # ================== ÁREA INFERIOR: MAPA E LISTA ==================
        st.markdown("<hr style='border: 1px solid #E2E8F0; margin-top: 5px; margin-bottom: 15px;'>", unsafe_allow_html=True)
        
        col_lista, col_mapa = st.columns([1.5, 1])

        # ---- LISTA DE DETALHES (TABELA) ----
        with col_lista:
            st.markdown("<h4 style='color: #0F172A; font-weight: 800; font-size: 16px;'>📋 DETALHAMENTO DE PENDÊNCIAS</h4>", unsafe_allow_html=True)
            
            # Selecionar colunas úteis para a tela
            cols_disponiveis = df_atrasados.columns.tolist()
            col_tomador = next((col for col in ['TOMADOR', 'CLIENTE', 'EMPRESA'] if col in cols_disponiveis), 'N/A')
            
            cols_exibicao = ['PEDIDO']
            if col_tomador != 'N/A': cols_exibicao.append(col_tomador)
            if agente_col in cols_disponiveis: cols_exibicao.append(agente_col)
            cols_exibicao.append('DIAS_ATRASO')
            
            df_view = df_atrasados[cols_exibicao].sort_values(by='DIAS_ATRASO', ascending=False)
            
            st.dataframe(
                df_view,
                column_config={
                    "PEDIDO": st.column_config.TextColumn("📦 Pedido/AWB"),
                    col_tomador: st.column_config.TextColumn("🏢 Cliente"),
                    agente_col: st.column_config.TextColumn("👤 Motorista"),
                    "DIAS_ATRASO": st.column_config.ProgressColumn("🔴 Dias Vencidos", format="%d dias", min_value=0, max_value=int(atraso_maximo) + 2)
                },
                hide_index=True, use_container_width=True, height=400
            )

        # ---- MAPA DE CALOR/PONTOS ----
        with col_mapa:
            st.markdown("<h4 style='color: #0F172A; font-weight: 800; font-size: 16px;'>📍 RADAR DE DISPERSÃO</h4>", unsafe_allow_html=True)
            
            # Buscar colunas de latitude e longitude
            col_lat = next((c for c in cols_disponiveis if c in ['LAT', 'LATITUDE', 'LATITUDE_DESTINO', 'LATITUDE_COLETA']), None)
            col_lon = next((c for c in cols_disponiveis if c in ['LON', 'LONG', 'LONGITUDE', 'LONGITUDE_DESTINO', 'LONGITUDE_COLETA']), None)
            
            if col_lat and col_lon:
                df_mapa = df_atrasados[[col_lat, col_lon]].copy()
                df_mapa.rename(columns={col_lat: 'lat', col_lon: 'lon'}, inplace=True)
                df_mapa['lat'] = pd.to_numeric(df_mapa['lat'], errors='coerce')
                df_mapa['lon'] = pd.to_numeric(df_mapa['lon'], errors='coerce')
                df_mapa = df_mapa.dropna()
                
                if not df_mapa.empty:
                    st.map(df_mapa, color="#EF4444", size=100) # Pontos vermelhos maiores para destacar atrasos
                else:
                    st.warning("⚠️ Coordenadas inválidas detectadas na base.")
            else:
                st.info("🗺️ **Módulo Tático de Mapa Inativo**\n\nPara visualizar os atrasos no radar, é necessário que o banco de dados `DB_IGO_Logistica` possua as colunas `LATITUDE` e `LONGITUDE` preenchidas para cada pedido.")

# --- RODAPÉ DISCRETO ---
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(f"""
<div style="text-align: center; color: #94A3B8; font-size: 10px; font-family: sans-serif; opacity: 0.6;">
    Sincronização Alerta SLA: {hora_atual}
</div>
""", unsafe_allow_html=True)
