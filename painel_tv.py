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
st.set_page_config(page_title="C.C.O TV - Urgências", layout="wide", page_icon="📺")
st_autorefresh(interval=60000, limit=None, key="tv_refresh")

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
            return df
    except Exception: pass
    return pd.DataFrame()

def calc_status_display(row):
    status_final = str(row.get('STATUS', '')).strip().upper()
    if 'COLETADO' in status_final: return 'Coletado'
    elif 'FRUSTRADA' in status_final or 'PROBLEMA' in status_final or 'CANCELADO' in status_final: return 'Frustrada'
    return 'Pendente'

# =============================================================================
# 🎨 3. CSS E ESTILOS
# =============================================================================
st.markdown("""
<style>
    /* OCULTAR ELEMENTOS NATIVOS DO STREAMLIT */
    #MainMenu {visibility: hidden !important;}
    header {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    .stDeployButton {display: none !important;}
    iframe[src*="manage"] {display: none !important;}
    [data-testid="manage-app-button"] {display: none !important;}
    
    /* Remove espaços e define fundo */
    .block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; margin-top: 0 !important; }
    [data-testid="stAppViewContainer"] { background-color: #F8FAFC !important; }
    
    /* Cartões de Métrica - Ajustados para 5 colunas */
    .metric-card { 
        border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.03); 
        padding: 15px; height: 135px; display: flex; flex-direction: column; 
        justify-content: space-between; border: 1px solid rgba(0,0,0,0.05);
        margin-bottom: 10px;
    }
    .metric-title { font-size: 11px; font-weight: 900; text-transform: uppercase; letter-spacing: 0.5px; opacity: 0.8;}
    .metric-value { font-size: 44px; font-weight: 900; font-family: 'Segoe UI', sans-serif; line-height: 1; margin: 3px 0;}
    .metric-delta { font-size: 11px; font-weight: 800; padding: 3px 6px; border-radius: 6px; display: inline-block; background-color: rgba(255,255,255,0.6);}
    
    /* Ticker (Barra Rolante) */
    .ticker-wrap { 
        width: 100%; overflow: hidden; background-color: #1E293B; border-radius: 8px; 
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); padding: 10px 0; 
        margin-top: 15px; margin-bottom: 20px; white-space: nowrap; 
    }
    .ticker { display: inline-block; white-space: nowrap; animation: marquee 35s linear infinite; }
    .ticker-item { font-size: 18px; color: #F8FAFC; font-family: 'Segoe UI', sans-serif; margin-right: 60px; font-weight: 500; }
    .ticker-highlight { color: #38BDF8; font-weight: 800; }
    @keyframes marquee { 0% { transform: translateX(100vw); } 100% { transform: translateX(-100%); } }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# 🚀 4. LÓGICA DE PROCESSAMENTO E EXIBIÇÃO
# =============================================================================
planilha_db = conectar_banco()
df_raw = carregar_dados_completos(planilha_db)
hoje_br = datetime.now(FUSO_BR).date()
hora_atual = datetime.now(FUSO_BR).strftime('%H:%M:%S')

if df_raw.empty:
    st.info("Aguardando dados da base central...")
else:
    df_raw['STATUS_DISPLAY'] = df_raw.apply(calc_status_display, axis=1)
    
    df_hoje = df_raw[df_raw['DATA_OBJ'] == hoje_br].copy()
    df_ontem = df_raw[df_raw['DATA_OBJ'] == (hoje_br - timedelta(days=1))].copy()
    
    # Métricas do Dia
    total_hoje = len(df_hoje)
    total_ontem = len(df_ontem)
    coletados_hoje = df_hoje['STATUS_DISPLAY'].eq('Coletado').sum()
    frustradas_hoje = df_hoje['STATUS_DISPLAY'].eq('Frustrada').sum()
    pendentes_hoje = total_hoje - coletados_hoje - frustradas_hoje
    if pendentes_hoje < 0: pendentes_hoje = 0

    # Lógica de Atrasados (Olhando para TODA a base, não só hoje)
    if 'DATA_LIMITE' in df_raw.columns:
        df_raw['DATA_LIMITE_OBJ'] = pd.to_datetime(df_raw['DATA_LIMITE'], format='%d/%m/%Y', errors='coerce').dt.date
        atrasados_total = len(df_raw[(df_raw['STATUS_DISPLAY'] == 'Pendente') & (df_raw['DATA_LIMITE_OBJ'] < hoje_br)])
    elif 'DATA' in df_raw.columns:
        # Se não houver DATA_LIMITE, usa a DATA de criação do pedido como base de atraso
        atrasados_total = len(df_raw[(df_raw['STATUS_DISPLAY'] == 'Pendente') & (df_raw['DATA_OBJ'] < hoje_br)])
    else:
        atrasados_total = 0

    if total_ontem > 0:
        pct_delta_total = ((total_hoje - total_ontem) / total_ontem) * 100
        if pct_delta_total > 0: html_delta_total = f'<span class="metric-delta" style="color: #059669;">▲ +{pct_delta_total:.1f}% vs Ontem</span>'
        elif pct_delta_total < 0: html_delta_total = f'<span class="metric-delta" style="color: #DC2626;">▼ {pct_delta_total:.1f}% vs Ontem</span>'
        else: html_delta_total = f'<span class="metric-delta" style="color: #475569;">▬ Estável</span>'
    else:
        html_delta_total = f'<span class="metric-delta" style="color: #059669;">▲ Novo Ciclo</span>'

    # ================== 1. OS 5 BLOCOS DE MÉTRICAS ==================
    c1, c2, c3, c4, c5 = st.columns(5)
    
    with c1:
        st.markdown(f"""
        <div class="metric-card" style="background-color: #F1F5F9;">
            <div class="metric-title" style="color: #475569;">📦 TOTAL DO DIA</div>
            <div class="metric-value" style="color: #0F172A;">{total_hoje}</div>
            <div>{html_delta_total}</div>
        </div>
        """, unsafe_allow_html=True)
        
    with c2:
        st.markdown(f"""
        <div class="metric-card" style="background-color: #E0F2FE;">
            <div class="metric-title" style="color: #0369A1;">✓ COLETADOS</div>
            <div class="metric-value" style="color: #075985;">{coletados_hoje}</div>
            <div><span class="metric-delta" style="color: #0369A1;">Garantidos</span></div>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        st.markdown(f"""
        <div class="metric-card" style="background-color: #FFFBEB;">
            <div class="metric-title" style="color: #B45309;">⏳ RESTANTES</div>
            <div class="metric-value" style="color: #92400E;">{pendentes_hoje}</div>
            <div><span class="metric-delta" style="color: #B45309;">Aguardando ação</span></div>
        </div>
        """, unsafe_allow_html=True)
        
    with c4:
        st.markdown(f"""
        <div class="metric-card" style="background-color: #FEF2F2; border: 1px solid #FECACA;">
            <div class="metric-title" style="color: #B91C1C;">🚨 ATRASADOS</div>
            <div class="metric-value" style="color: #7F1D1D;">{atrasados_total}</div>
            <div><span class="metric-delta" style="color: #B91C1C; background-color: #FEE2E2;">SLA Rompido</span></div>
        </div>
        """, unsafe_allow_html=True)

    with c5:
        st.markdown(f"""
        <div class="metric-card" style="background-color: #FDF2F8;">
            <div class="metric-title" style="color: #BE185D;">❌ FRUSTRADOS</div>
            <div class="metric-value" style="color: #831843;">{frustradas_hoje}</div>
            <div><span class="metric-delta" style="color: #BE185D;">Requerem atenção</span></div>
        </div>
        """, unsafe_allow_html=True)

    # ================== 2. BARRA DE PROGRESSO ==================
    total_base_progresso = coletados_hoje + pendentes_hoje
    pct_coletado = (coletados_hoje / total_base_progresso) * 100 if total_base_progresso > 0 else 0

    st.markdown(f"""
    <div style="display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 5px; margin-top: 15px;">
        <span style="color: #0F172A; font-family: sans-serif; font-weight: 800; font-size: 15px;">PROGRESSO DA OPERAÇÃO</span>
        <span style="color: #0284C7; font-weight: 900; font-size: 16px;">{pct_coletado:.1f}%</span>
    </div>
    <div style="width: 100%; height: 10px; background-color: #E2E8F0; border-radius: 10px; overflow: hidden; box-shadow: inset 0 1px 3px rgba(0,0,0,0.1);">
        <div style="width: {pct_coletado}%; height: 100%; background-color: #0284C7; transition: width 1s ease-in-out;"></div>
    </div>
    """, unsafe_allow_html=True)

    # ================== 3. TICKER (BARRA ROLANTE) ==================
    ticker_items = []
    
    # Alerta Crítico no Ticker se houver atrasados
    if atrasados_total > 0:
        ticker_items.append(f"<span class='ticker-item'><span style='color:#EF4444; font-weight:900;'>🚨 ALERTA C.C.O:</span> Temos {atrasados_total} volumes com SLA rompido (Atrasados). Ação imediata necessária!</span>")

    col_tomador = next((col for col in ['TOMADOR', 'CLIENTE', 'EMPRESA'] if col in df_raw.columns), None)
    if col_tomador and not df_hoje.empty:
        vol_hoje = df_hoje[col_tomador].value_counts()
        vol_ontem = df_ontem[col_tomador].value_counts()
        for t_nome, v_h in vol_hoje.items():
            v_o = vol_ontem.get(t_nome, 0)
            if v_o > 0:
                pct = ((v_h - v_o) / v_o) * 100
                sinal = "▲" if pct >= 0 else "▼"
                cor_sinal = "#10B981" if pct >= 0 else "#EF4444"
                ticker_items.append(f"<span class='ticker-item'>CLIENTE <b>{t_nome}</b>: {v_h} vols (<span style='color:{cor_sinal};'>{sinal} {abs(pct):.0f}%</span>)</span>")
            else:
                ticker_items.append(f"<span class='ticker-item'>NOVO VOLUME: <b>{t_nome}</b> com {v_h} pedidos.</span>")

    if not df_hoje.empty and 'AGENTE_RAW' in df_hoje.columns:
        agentes_coletas = df_hoje[df_hoje['STATUS_DISPLAY'] == 'Coletado']['AGENTE_RAW'].value_counts()
        if not agentes_coletas.empty:
            melhor_agente = agentes_coletas.index[0]
            vols_melhor = agentes_coletas.iloc[0]
            ticker_items.append(f"<span class='ticker-item'><span class='ticker-highlight'>⚡ DESTAQUE:</span> Motorista {melhor_agente} lidera com {vols_melhor} coletas.</span>")
    
    if frustradas_hoje > 0:
         ticker_items.append(f"<span class='ticker-item'><span style='color:#EF4444; font-weight:bold;'>⚠️ OCORRÊNCIAS:</span> {frustradas_hoje} pedidos frustrados.</span>")

    if not ticker_items: ticker_items = ["<span class='ticker-item'>AGUARDANDO ATUALIZAÇÕES: Operação em andamento...</span>"]

    ticker_content = " &nbsp;&nbsp;•&nbsp;&nbsp; ".join(ticker_items)
    
    st.markdown(f"""
    <div class="ticker-wrap"><div class="ticker">{ticker_content}</div></div>
    """, unsafe_allow_html=True)

    st.markdown("<hr style='border: 1px solid #E2E8F0; margin-top: 10px; margin-bottom: 15px;'>", unsafe_allow_html=True)

# --- RODAPÉ DISCRETO ---
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(f"""
<div style="text-align: center; color: #94A3B8; font-size: 10px; font-family: sans-serif; opacity: 0.6;">
    Última sincronização com C.C.O: {hora_atual}
</div>
""", unsafe_allow_html=True)
