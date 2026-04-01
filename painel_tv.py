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
# 1. CONFIGURAÇÃO DA PÁGINA E AUTO-REFRESH (CARROSSEL)
# =============================================================================
st.set_page_config(page_title="C.C.O TV - IGO Logística", layout="wide", page_icon="📺")

# Atualiza a página a cada 60.000 milissegundos (60 segundos)
count = st_autorefresh(interval=60000, limit=None, key="tv_refresh")

# Memória do Slide Atual
if 'slide_atual' not in st.session_state:
    st.session_state.slide_atual = 1

# Avança o slide a cada refresh (Loop de 1 a 3)
if count > 0:
    st.session_state.slide_atual += 1
    if st.session_state.slide_atual > 3:
        st.session_state.slide_atual = 1

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
    previsao = str(row.get('DATA_LIMITE', '')).strip()
    res = '⏳ Pendente'
    
    if 'ENTREGUE' in status_final: res = '✅ Entregue'
    elif 'COLETADO' in status_final: res = '📦 Coletado'
    elif 'ROTA' in status_final: res = '🚚 Em Rota'
    elif 'CONFERIDO' in status_final: res = '☑️ Conferido'
    elif 'FRUSTRADA' in status_final: res = '❌ Frustrada'
    elif 'CANCELADO' in status_final: res = '🚫 Cancelado'
    elif 'PROBLEMA' in status_final: res = '🚨 Problema'
    
    if '✅' not in res and '🚫' not in res and '❌' not in res and previsao:
        try:
            if datetime.strptime(previsao, "%d/%m/%Y").date() < datetime.now(FUSO_BR).date(): res = f"🚨 ATRASADO ({res})"
        except: pass
    return res

# =============================================================================
# 🎨 3. CSS PREMIUM LIGHT & FUNÇÕES DE TELA
# =============================================================================
st.markdown("""
<style>
    /* Fundo Geral Premium Claro */
    [data-testid="stAppViewContainer"] { background-color: #F8FAFC !important; }
    [data-testid="stHeader"] { background-color: transparent !important; }
    
    /* Cabeçalho */
    .tv-header { display: flex; justify-content: space-between; align-items: center; padding: 10px 30px; margin-bottom: 10px; }
    .tv-clock { color: #0F172A; font-family: 'Segoe UI', sans-serif; font-size: 36px; font-weight: 900; letter-spacing: -1px; }
    h3 { color: #0F172A !important; font-weight: 800 !important; font-family: 'Segoe UI', sans-serif; margin-bottom: 20px;}
    
    /* Barra de Progresso */
    .stProgress > div > div > div > div { background-color: #0284C7 !important; }
    
    /* Barra Rolante Ticker */
    .ticker-wrap {
        width: 100%;
        overflow: hidden;
        background-color: #FFFFFF;
        border-top: 2px solid #E2E8F0;
        border-bottom: 2px solid #E2E8F0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        padding: 12px 0;
        margin-bottom: 30px;
        white-space: nowrap;
    }
    .ticker {
        display: inline-block;
        white-space: nowrap;
        animation: marquee 35s linear infinite;
    }
    .ticker-item {
        font-size: 20px;
        color: #334155;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        margin-right: 50px;
    }
    @keyframes marquee {
        0% { transform: translateX(100vw); }
        100% { transform: translateX(-100%); }
    }
</style>
""", unsafe_allow_html=True)

def criar_card(titulo, valor, subtitulo, cor_acento):
    return f"""
    <div style="background-color: #FFFFFF; border-left: 6px solid {cor_acento}; padding: 25px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.06); height: 160px; display: flex; flex-direction: column; justify-content: center; margin-bottom: 20px; border: 1px solid #F1F5F9;">
        <p style="margin:0; font-size: 14px; font-weight: 800; color: #64748B; text-transform: uppercase; letter-spacing: 1px;">{titulo}</p>
        <h1 style="margin:0; font-size: 56px; font-weight: 900; color: #0F172A; font-family: 'Segoe UI', sans-serif; letter-spacing: -2px;">{valor}</h1>
        <p style="margin:0; font-size: 15px; font-weight: 700; color: {cor_acento}; margin-top: 5px;">{subtitulo}</p>
    </div>
    """

# =============================================================================
# 🚀 4. LÓGICA DE PROCESSAMENTO E CARROSSEL
# =============================================================================
planilha_db = conectar_banco()
df_raw = carregar_dados_completos(planilha_db)
hoje_br = datetime.now(FUSO_BR).date()
hora_atual = datetime.now(FUSO_BR).strftime('%H:%M:%S')

# --- CABEÇALHO FIXO DA TV ---
st.markdown(f"""
<div class="tv-header">
    <img src="https://i.postimg.cc/x84nnjjq/IGO-LOGO.png" width="220" style="filter: drop-shadow(0px 4px 4px rgba(0,0,0,0.1));">
    <div class="tv-clock">{hora_atual}</div>
</div>
""", unsafe_allow_html=True)

if df_raw.empty:
    st.error("Falha de Comunicação: Banco de dados inacessível ou vazio.")
else:
    df_raw['STATUS_DISPLAY'] = df_raw.apply(calc_status_display, axis=1)
    
    df_hoje = df_raw[df_raw['DATA_OBJ'] == hoje_br].copy()
    dia_anterior = hoje_br - timedelta(days=1)
    df_ontem = df_raw[df_raw['DATA_OBJ'] == dia_anterior]
    
    total_hoje = len(df_hoje)
    total_ontem = len(df_ontem)
    delta_pedidos = total_hoje - total_ontem
    sinal = "▲" if delta_pedidos >= 0 else "▼"
    cor_delta = "#10B981" if delta_pedidos >= 0 else "#EF4444"
    
    entregues = df_hoje['STATUS_DISPLAY'].str.contains('Entregue', case=False, na=False).sum()
    frustrados = df_hoje['STATUS_DISPLAY'].str.contains('Frustrada|Problema|Cancelado', case=False, na=False).sum()
    atrasados = df_hoje['STATUS_DISPLAY'].str.contains('ATRASADO', case=False, na=False).sum()
    coletados = df_hoje['STATUS_DISPLAY'].str.contains('Coletado|Conferido', case=False, na=False).sum()
    em_rota = df_hoje['STATUS_DISPLAY'].str.contains('Em Rota', case=False, na=False).sum()
    pendentes = df_hoje['STATUS_DISPLAY'].str.contains('Pendente', case=False, na=False).sum()
    
    # Cálculo de Taxa de Sucesso (SLA)
    taxa_sucesso = round((entregues / (entregues + frustrados)) * 100, 1) if (entregues + frustrados) > 0 else 0

    # ================== TICKER: BARRA ROLANTE ==================
    # Procura a coluna que identifica o cliente/tomador
    col_tomador = next((col for col in ['TOMADOR', 'CLIENTE', 'EMPRESA'] if col in df_raw.columns), None)
    
    ticker_html = ""
    if col_tomador and not df_hoje.empty:
        vol_hoje = df_hoje[col_tomador].value_counts().reset_index()
        vol_hoje.columns = [col_tomador, 'Vol_Hoje']
        vol_ontem = df_ontem[col_tomador].value_counts().reset_index()
        vol_ontem.columns = [col_tomador, 'Vol_Ontem']
        
        df_ticker = pd.merge(vol_hoje, vol_ontem, on=col_tomador, how='left').fillna(0)
        
        ticker_items = []
        for _, row in df_ticker.iterrows():
            t_nome = row[col_tomador]
            v_h = int(row['Vol_Hoje'])
            v_o = int(row['Vol_Ontem'])
            
            if v_o > 0:
                pct = ((v_h - v_o) / v_o) * 100
                t_sinal = "▲" if pct >= 0 else "▼"
                t_cor = "#10B981" if pct >= 0 else "#EF4444"
                ticker_items.append(f"<span class='ticker-item'><b>{t_nome}</b>: {v_h} vols (<span style='color:{t_cor}; font-weight:bold;'>{t_sinal} {abs(pct):.1f}%</span>)</span>")
            else:
                ticker_items.append(f"<span class='ticker-item'><b>{t_nome}</b>: {v_h} vols (<span style='color:#10B981; font-weight:bold;'>▲ Novo</span>)</span>")
        
        ticker_content = "".join(ticker_items)
    else:
        ticker_content = f"<span class='ticker-item'><b>VOLUMES HOJE:</b> {total_hoje} | <b>ENTREGUES:</b> {entregues} | <b>EM ROTA:</b> {em_rota} | <b>OCORRÊNCIAS:</b> {frustrados}</span>"
        
    st.markdown(f"""
    <div class="ticker-wrap">
        <div class="ticker">
            {ticker_content}
        </div>
    </div>
    """, unsafe_allow_html=True)


    # ================== SLIDE 1: VISÃO GERAL (EXECUTIVE) ==================
    if st.session_state.slide_atual == 1:
        st.markdown("<h3 style='padding-left: 10px;'>📊 PAINEL EXECUTIVO - TRACKING DO DIA</h3>", unsafe_allow_html=True)
        
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(criar_card("VOLUMES TOTAIS", total_hoje, f"{sinal} {abs(delta_pedidos)} vs Ontem", cor_delta), unsafe_allow_html=True)
        c2.markdown(criar_card("EM ROTA DE ENTREGA", em_rota, "Expedição em Trânsito", "#F59E0B"), unsafe_allow_html=True)
        c3.markdown(criar_card("ENTREGAS CONCLUÍDAS", entregues, "Sucesso Absoluto", "#10B981"), unsafe_allow_html=True)
        c4.markdown(criar_card("TAXA DE SUCESSO (SLA)", f"{taxa_sucesso}%", "Eficiência de Entrega", "#0284C7"), unsafe_allow_html=True)
        
        c5, c6, c7, c8 = st.columns(4)
        c5.markdown(criar_card("PENDENTES RUA", pendentes, "Aguardando Interceptação", "#64748B"), unsafe_allow_html=True)
        c6.markdown(criar_card("TRIAGEM INTERNA", coletados, "Blindados e Roteirizados", "#38BDF8"), unsafe_allow_html=True)
        c7.markdown(criar_card("OCORRÊNCIAS TÉC.", frustrados, "Reversões ou Falhas", "#F43F5E"), unsafe_allow_html=True)
        
        with c8:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("<h4 style='color: #0F172A; font-weight: 800;'>🎯 Progresso da Operação</h4>", unsafe_allow_html=True)
            concluidos_globais = total_hoje - pendentes
            progresso_pct = int((concluidos_globais / total_hoje) * 100) if total_hoje > 0 else 0
            st.progress(progresso_pct / 100.0, text=f"Índice Radar: {progresso_pct}%")
            st.markdown(f"<p style='font-size:15px; color:#475569; margin-top:-5px; font-weight:600;'>Ação registrada em <b>{concluidos_globais}</b> de <b>{total_hoje}</b> alvos.</p>", unsafe_allow_html=True)

    # ================== SLIDE 2: DESEMPENHO DOS MOTORISTAS ==================
    elif st.session_state.slide_atual == 2:
        st.markdown("<h3 style='padding-left: 10px;'>🏆 PERFORMANCE INDIVIDUAL EM SOLO</h3>", unsafe_allow_html=True)
        
        if not df_hoje.empty:
            df_mot = df_hoje.copy()
            df_mot['CONCLUIDO_COLETA'] = (~df_mot['STATUS_DISPLAY'].str.contains('Pendente', case=False, na=False)).astype(int)
            resumo_mot = df_mot.groupby('AGENTE_RAW').agg(Total=('PEDIDO', 'count'), Concluidos=('CONCLUIDO_COLETA', 'sum')).reset_index()
            resumo_mot['Faltam_Na_Rua'] = resumo_mot['Total'] - resumo_mot['Concluidos']
            resumo_mot['% Concluído'] = (resumo_mot['Concluidos'] / resumo_mot['Total'] * 100).round(1)
            resumo_mot = resumo_mot.sort_values(by='Total', ascending=False)
            resumo_mot.rename(columns={'AGENTE_RAW': 'Motorista'}, inplace=True)
            
            # CSS Tabela Premium Light
            st.markdown("""
            <style>
            [data-testid="stDataFrame"] { background-color: #FFFFFF; padding: 20px; border-radius: 12px; border: 1px solid #E2E8F0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }
            th { color: #0284C7 !important; font-size: 16px !important; font-weight: 800 !important;}
            td { color: #0F172A !important; font-size: 18px !important; font-weight: 600; }
            </style>
            """, unsafe_allow_html=True)
            
            st.dataframe(
                resumo_mot,
                column_config={
                    "Motorista": st.column_config.TextColumn("👤 Identificação do Agente"),
                    "Total": st.column_config.NumberColumn("📦 Volume Atribuído"),
                    "Concluidos": st.column_config.NumberColumn("✅ Ação Realizada"),
                    "Faltam_Na_Rua": st.column_config.NumberColumn("⏳ Alvo Pendente"),
                    "% Concluído": st.column_config.ProgressColumn("📊 Progresso", format="%f%%", min_value=0, max_value=100),
                },
                hide_index=True, use_container_width=True, height=450
            )
        else:
            st.info("O radar logístico indica 0 atividades em solo para este dia.")

    # ================== SLIDE 3: DISTRIBUIÇÃO E GARGALOS ==================
    elif st.session_state.slide_atual == 3:
        st.markdown("<h3 style='padding-left: 10px;'>📊 RAIO-X DE DISTRIBUIÇÃO E GARGALOS</h3>", unsafe_allow_html=True)
        
        col1, col2 = st.columns([2, 1])
        with col1:
            if not df_hoje.empty:
                df_hoje['STATUS_CHART'] = df_hoje['STATUS'].str.upper()
                status_counts = df_hoje['STATUS_CHART'].value_counts().reset_index()
                status_counts.columns = ['Status', 'Quantidade']
                st.bar_chart(data=status_counts, x='Status', y='Quantidade', color='#0284C7', height=450)
        
        with col2:
            st.markdown(criar_card("VOLUME RESTANTE", pendentes, "Aguardando Coleta", "#64748B"), unsafe_allow_html=True)
            st.markdown(criar_card("TAXA DE FALHA", f"{int((frustrados/total_hoje)*100) if total_hoje > 0 else 0}%", "Proporção de problemas no dia", "#F43F5E"), unsafe_allow_html=True)
            st.markdown(criar_card("CRITICIDADE SLA", atrasados, "Volumes em Atraso Crítico", "#EF4444"), unsafe_allow_html=True)

# Rodapé de paginação
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align:center; color:#64748B; font-weight:700;'>Exibição {st.session_state.slide_atual} de 3 | IGO Logística Autopilot</p>", unsafe_allow_html=True)
