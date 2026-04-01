import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import os
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
    if 'ENTREGUE' in status_final: return 'Entregue'
    elif 'COLETADO' in status_final: return 'Coletado'
    elif 'ROTA' in status_final: return 'Em Rota'
    elif 'CONFERIDO' in status_final: return 'Conferido'
    elif 'FRUSTRADA' in status_final: return 'Frustrada'
    elif 'CANCELADO' in status_final: return 'Cancelado'
    elif 'PROBLEMA' in status_final: return 'Problema'
    return 'Pendente'

# =============================================================================
# 🎨 3. CSS PREMIUM LIGHT & ESTILO CNN
# =============================================================================
st.markdown("""
<style>
    /* Fundo Claro e Limpo */
    [data-testid="stAppViewContainer"] { background-color: #F8FAFC !important; }
    [data-testid="stHeader"] { background-color: transparent !important; }
    
    /* Cabeçalho Discreto */
    .tv-header { display: flex; justify-content: space-between; align-items: flex-end; padding: 0px 10px 15px 10px; border-bottom: 1px solid #E2E8F0; margin-bottom: 20px; }
    .sync-info { color: #64748B; font-family: 'Segoe UI', sans-serif; font-size: 14px; font-weight: 600; text-align: right;}
    .sync-time { color: #0F172A; font-size: 18px; font-weight: 800; }
    
    /* Ticker Inteligente Estilo CNN */
    .ticker-wrap {
        width: 100%; overflow: hidden; background-color: #1E293B; border-radius: 8px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); padding: 12px 0; margin-bottom: 25px; white-space: nowrap;
    }
    .ticker { display: inline-block; white-space: nowrap; animation: marquee 40s linear infinite; }
    .ticker-item { font-size: 18px; color: #F8FAFC; font-family: 'Segoe UI', sans-serif; margin-right: 60px; font-weight: 500; }
    .ticker-highlight { color: #38BDF8; font-weight: 800; }
    .ticker-alert { color: #FBBF24; font-weight: 800; }
    @keyframes marquee { 0% { transform: translateX(100vw); } 100% { transform: translateX(-100%); } }
    
    /* Cartões Executivos */
    .metric-card {
        background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02); padding: 25px; height: 160px;
        display: flex; flex-direction: column; justify-content: space-between;
    }
    .metric-title { font-size: 14px; font-weight: 800; color: #64748B; text-transform: uppercase; letter-spacing: 0.5px; }
    .metric-value { font-size: 52px; font-weight: 900; color: #0F172A; font-family: 'Segoe UI', sans-serif; line-height: 1; }
    .metric-delta { font-size: 14px; font-weight: 700; padding: 4px 8px; border-radius: 6px; display: inline-block; margin-top: 5px;}
    .delta-up { background-color: #D1FAE5; color: #059669; }
    .delta-down { background-color: #FEE2E2; color: #DC2626; }
    .delta-neutral { background-color: #F1F5F9; color: #475569; }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# 🚀 4. LÓGICA DE PROCESSAMENTO
# =============================================================================
planilha_db = conectar_banco()
df_raw = carregar_dados_completos(planilha_db)
hoje_br = datetime.now(FUSO_BR).date()
hora_atual = datetime.now(FUSO_BR).strftime('%H:%M:%S')

# --- CABEÇALHO ---
st.markdown(f"""
<div class="tv-header">
    <img src="https://i.postimg.cc/x84nnjjq/IGO-LOGO.png" width="120" style="opacity: 0.9;">
    <div class="sync-info">STATUS DO SISTEMA<br><span class="sync-time">🟢 ÚLTIMA ATUALIZAÇÃO: {hora_atual}</span></div>
</div>
""", unsafe_allow_html=True)

if df_raw.empty:
    st.error("Aguardando dados da base central...")
else:
    df_raw['STATUS_DISPLAY'] = df_raw.apply(calc_status_display, axis=1)
    
    df_hoje = df_raw[df_raw['DATA_OBJ'] == hoje_br].copy()
    df_ontem = df_raw[df_raw['DATA_OBJ'] == (hoje_br - timedelta(days=1))].copy()
    
    # Métricas Base
    total_hoje = len(df_hoje)
    total_ontem = len(df_ontem)
    
    coletados_hoje = df_hoje['STATUS_DISPLAY'].eq('Coletado').sum()
    frustradas_hoje = df_hoje['STATUS_DISPLAY'].eq('Frustrada').sum()
    pendentes_hoje = df_hoje['STATUS_DISPLAY'].eq('Pendente').sum()

    # Cálculo de Delta do Total
    if total_ontem > 0:
        pct_delta_total = ((total_hoje - total_ontem) / total_ontem) * 100
        if pct_delta_total > 0:
            html_delta_total = f'<span class="metric-delta delta-up">▲ +{pct_delta_total:.1f}% vs Ontem</span>'
        elif pct_delta_total < 0:
            html_delta_total = f'<span class="metric-delta delta-down">▼ {pct_delta_total:.1f}% vs Ontem</span>'
        else:
            html_delta_total = f'<span class="metric-delta delta-neutral">▬ Estável vs Ontem</span>'
    else:
        html_delta_total = f'<span class="metric-delta delta-up">▲ Novo Ciclo</span>'

    # ================== TICKER INTELIGENTE (ESTILO CNN) ==================
    ticker_items = []
    
    # 1. Informações de Tomadores (Clientes)
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
                ticker_items.append(f"<span class='ticker-item'>MERCADO: <b>{t_nome}</b> registra {v_h} volumes (<span style='color:{cor_sinal};'>{sinal} {abs(pct):.0f}%</span>)</span>")
            else:
                ticker_items.append(f"<span class='ticker-item'>NOVO CLIENTE: <b>{t_nome}</b> iniciou com {v_h} volumes hoje.</span>")

    # 2. Movimentação/Notícias dos Motoristas e Operação
    if not df_hoje.empty and 'AGENTE_RAW' in df_hoje.columns:
        agentes_coletas = df_hoje[df_hoje['STATUS_DISPLAY'] == 'Coletado']['AGENTE_RAW'].value_counts()
        if not agentes_coletas.empty:
            melhor_agente = agentes_coletas.index[0]
            vols_melhor = agentes_coletas.iloc[0]
            ticker_items.append(f"<span class='ticker-item'><span class='ticker-highlight'>⚡ DESTAQUE EM CAMPO:</span> Motorista {melhor_agente} lidera com {vols_melhor} coletas realizadas.</span>")
    
    if pendentes_hoje > 0:
         ticker_items.append(f"<span class='ticker-item'><span class='ticker-alert'>⚠️ ATENÇÃO C.C.O:</span> Faltam {pendentes_hoje} pedidos aguardando ação na rua.</span>")
    if frustradas_hoje > 0:
         ticker_items.append(f"<span class='ticker-item'><span style='color:#EF4444; font-weight:bold;'>🚨 OCORRÊNCIAS:</span> {frustradas_hoje} entregas/coletas frustradas registradas hoje. Acionar contingência.</span>")

    if not ticker_items:
        ticker_items = ["<span class='ticker-item'>OPERAÇÃO PADRÃO: Aguardando atualizações de campo...</span>"]

    ticker_content = " • ".join(ticker_items)
    
    st.markdown(f"""
    <div class="ticker-wrap">
        <div class="ticker">
            {ticker_content}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ================== CARTÕES DE URGÊNCIA ==================
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Volume Total do Dia</div>
            <div class="metric-value">{total_hoje}</div>
            <div>{html_delta_total}</div>
        </div>
        """, unsafe_allow_html=True)
        
    with c2:
        st.markdown(f"""
        <div class="metric-card" style="border-left: 6px solid #0284C7;">
            <div class="metric-title" style="color: #0284C7;">Somente Coletados</div>
            <div class="metric-value">{coletados_hoje}</div>
            <div><span class="metric-delta" style="background: #E0F2FE; color: #0369A1;">✓ Registrados com Sucesso</span></div>
        </div>
        """, unsafe_allow_html=True)
        
    with c3:
        st.markdown(f"""
        <div class="metric-card" style="border-left: 6px solid #EF4444;">
            <div class="metric-title" style="color: #EF4444;">Somente Frustradas</div>
            <div class="metric-value">{frustradas_hoje}</div>
            <div><span class="metric-delta" style="background: #FEE2E2; color: #B91C1C;">⚠ Requerem Atenção</span></div>
        </div>
        """, unsafe_allow_html=True)

    # ================== BARRA DE PROGRESSO (COLETADOS X PENDENTES) ==================
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<h4 style='color: #0F172A; font-family: sans-serif; font-weight: 800; font-size: 18px;'>📍 ACOMPANHAMENTO DE RUA (COLETADOS vs PENDENTES)</h4>", unsafe_allow_html=True)
    
    total_base_progresso = coletados_hoje + pendentes_hoje
    if total_base_progresso > 0:
        pct_coletado = (coletados_hoje / total_base_progresso) * 100
        pct_pendente = 100 - pct_coletado
    else:
        pct_coletado = 0
        pct_pendente = 100

    st.markdown(f"""
    <div style="width: 100%; background-color: #E2E8F0; border-radius: 10px; height: 35px; display: flex; overflow: hidden; box-shadow: inset 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 5px;">
        <div style="width: {pct_coletado}%; background-color: #0284C7; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-family: sans-serif; font-size: 14px; transition: width 1s ease-in-out;">
            {f"{pct_coletado:.1f}%" if pct_coletado > 5 else ""}
        </div>
        <div style="width: {pct_pendente}%; background-color: #CBD5E1; display: flex; align-items: center; justify-content: center; color: #475569; font-weight: bold; font-family: sans-serif; font-size: 14px; transition: width 1s ease-in-out;">
             {f"{pct_pendente:.1f}%" if pct_pendente > 5 else ""}
        </div>
    </div>
    <div style="display: flex; justify-content: space-between; color: #64748B; font-weight: 600; font-size: 14px; font-family: sans-serif;">
        <span>📦 {coletados_hoje} Coletados</span>
        <span>⏳ {pendentes_hoje} Pendentes</span>
    </div>
    """, unsafe_allow_html=True)
