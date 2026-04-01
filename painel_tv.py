import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import json
import gspread
from streamlit_autorefresh import st_autorefresh
from google.oauth2.credentials import Credentials

FUSO_BR = timezone(timedelta(hours=-3))

# =============================================================================
# 1. CONFIGURAÇÃO DA PÁGINA E AUTO-REFRESH (CARROSSEL)
# =============================================================================
st.set_page_config(page_title="C.C.O TV - Autopilot", layout="wide", page_icon="📺")

# O contador avança 1 a cada 60 segundos
count = st_autorefresh(interval=60000, limit=None, key="tv_refresh_autopilot")

# Lógica matemática simples para alternar entre Tela 1 e Tela 2
slide_atual = (count % 2) + 1 

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
# 🎨 3. CSS TÁTICO & PREMIUM (UNIFICADO)
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
    
    /* Cartões Base */
    .metric-card { 
        border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.03); 
        padding: 15px; height: 135px; display: flex; flex-direction: column; 
        justify-content: space-between; border: 1px solid rgba(0,0,0,0.05);
        margin-bottom: 10px;
    }
    /* Cartões de Alerta (Página 2) */
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
    
    /* Fontes e Textos */
    .metric-title { font-size: 11px; font-weight: 900; text-transform: uppercase; letter-spacing: 0.5px; opacity: 0.8;}
    .metric-title-lg { font-size: 13px; font-weight: 900; text-transform: uppercase; letter-spacing: 0.5px; opacity: 0.8;}
    .metric-value { font-size: 44px; font-weight: 900; font-family: 'Segoe UI', sans-serif; line-height: 1; margin: 3px 0;}
    .metric-value-lg { font-size: 48px; font-weight: 900; font-family: 'Segoe UI', sans-serif; line-height: 1; margin: 3px 0;}
    .metric-delta { font-size: 11px; font-weight: 800; padding: 3px 6px; border-radius: 6px; display: inline-block; background-color: rgba(255,255,255,0.6);}
    .metric-sub { font-size: 14px; font-weight: 700; color: #475569;}
    
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
    
    /* Tabela */
    [data-testid="stDataFrame"] { background-color: #FFFFFF; border-radius: 10px; border: 1px solid #E2E8F0; box-shadow: 0 4px 15px rgba(0,0,0,0.04);}
    th { color: #0F172A !important; font-size: 15px !important; font-weight: 900 !important; background-color: #F1F5F9 !important;}
    td { font-size: 16px !important; font-weight: 600; color: #334155 !important;}
</style>
""", unsafe_allow_html=True)

# =============================================================================
# 🚀 4. LÓGICA DE PROCESSAMENTO DE DADOS (USADO NAS DUAS TELAS)
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
    
    # Cálculos Globais
    total_hoje = len(df_hoje)
    total_ontem = len(df_ontem)
    coletados_hoje = df_hoje['STATUS_DISPLAY'].eq('Coletado').sum()
    frustradas_hoje = df_hoje['STATUS_DISPLAY'].eq('Frustrada').sum()
    pendentes_hoje = total_hoje - coletados_hoje - frustradas_hoje
    if pendentes_hoje < 0: pendentes_hoje = 0

    # Lógica de Atrasados
    if 'DATA_LIMITE_OBJ' in df_raw.columns:
        df_atrasados = df_raw[(df_raw['STATUS_DISPLAY'] == 'Pendente') & (df_raw['DATA_LIMITE_OBJ'] < hoje_br)].copy()
    elif 'DATA_OBJ' in df_raw.columns:
        df_atrasados = df_raw[(df_raw['STATUS_DISPLAY'] == 'Pendente') & (df_raw['DATA_OBJ'] < hoje_br)].copy()
    else:
        df_atrasados = pd.DataFrame()
        
    atrasados_total = len(df_atrasados)

    # =========================================================================
    # 📺 SLIDE 1: VISÃO GERAL DE URGÊNCIAS (OS 5 BLOCOS)
    # =========================================================================
    if slide_atual == 1:
        if total_ontem > 0:
            pct_delta = ((total_hoje - total_ontem) / total_ontem) * 100
            html_delta = f'<span class="metric-delta" style="color: #059669;">▲ +{pct_delta:.1f}% vs Ontem</span>' if pct_delta > 0 else f'<span class="metric-delta" style="color: #DC2626;">▼ {pct_delta:.1f}% vs Ontem</span>'
        else:
            html_delta = f'<span class="metric-delta" style="color: #059669;">▲ Novo Ciclo</span>'

        c1, c2, c3, c4, c5 = st.columns(5)
        
        with c1: st.markdown(f'<div class="metric-card" style="background-color: #F1F5F9;"><div class="metric-title" style="color: #475569;">📦 TOTAL DO DIA</div><div class="metric-value" style="color: #0F172A;">{total_hoje}</div><div>{html_delta}</div></div>', unsafe_allow_html=True)
        with c2: st.markdown(f'<div class="metric-card" style="background-color: #E0F2FE;"><div class="metric-title" style="color: #0369A1;">✓ COLETADOS</div><div class="metric-value" style="color: #075985;">{coletados_hoje}</div><div><span class="metric-delta" style="color: #0369A1;">Garantidos</span></div></div>', unsafe_allow_html=True)
        with c3: st.markdown(f'<div class="metric-card" style="background-color: #FFFBEB;"><div class="metric-title" style="color: #B45309;">⏳ RESTANTES</div><div class="metric-value" style="color: #92400E;">{pendentes_hoje}</div><div><span class="metric-delta" style="color: #B45309;">Aguardando</span></div></div>', unsafe_allow_html=True)
        with c4: st.markdown(f'<div class="metric-card" style="background-color: #FEF2F2; border: 1px solid #FECACA;"><div class="metric-title" style="color: #B91C1C;">🚨 ATRASADOS</div><div class="metric-value" style="color: #7F1D1D;">{atrasados_total}</div><div><span class="metric-delta" style="color: #B91C1C; background-color: #FEE2E2;">SLA Rompido</span></div></div>', unsafe_allow_html=True)
        with c5: st.markdown(f'<div class="metric-card" style="background-color: #FDF2F8;"><div class="metric-title" style="color: #BE185D;">❌ FRUSTRADOS</div><div class="metric-value" style="color: #831843;">{frustradas_hoje}</div><div><span class="metric-delta" style="color: #BE185D;">Atenção</span></div></div>', unsafe_allow_html=True)

        # BARRA DE PROGRESSO
        total_base = coletados_hoje + pendentes_hoje
        pct_coletado = (coletados_hoje / total_base) * 100 if total_base > 0 else 0
        st.markdown(f"""
        <div style="display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 5px; margin-top: 15px;">
            <span style="color: #0F172A; font-family: sans-serif; font-weight: 800; font-size: 15px;">PROGRESSO DA OPERAÇÃO</span><span style="color: #0284C7; font-weight: 900; font-size: 16px;">{pct_coletado:.1f}%</span>
        </div>
        <div style="width: 100%; height: 10px; background-color: #E2E8F0; border-radius: 10px; overflow: hidden; box-shadow: inset 0 1px 3px rgba(0,0,0,0.1);"><div style="width: {pct_coletado}%; height: 100%; background-color: #0284C7;"></div></div>
        """, unsafe_allow_html=True)

        # TICKER
        ticker_items = []
        if atrasados_total > 0: ticker_items.append(f"<span class='ticker-item'><span style='color:#EF4444; font-weight:900;'>🚨 ALERTA:</span> {atrasados_total} volumes com SLA rompido!</span>")
        col_tomador = next((col for col in ['TOMADOR', 'CLIENTE', 'EMPRESA'] if col in df_raw.columns), None)
        if col_tomador and not df_hoje.empty:
            vol_hoje = df_hoje[col_tomador].value_counts()
            for t_nome, v_h in vol_hoje.items(): ticker_items.append(f"<span class='ticker-item'>CLIENTE <b>{t_nome}</b>: {v_h} vols hoje</span>")
        if not ticker_items: ticker_items = ["<span class='ticker-item'>Operação em andamento...</span>"]
        st.markdown(f'<div class="ticker-wrap"><div class="ticker">{" &nbsp;&nbsp;•&nbsp;&nbsp; ".join(ticker_items)}</div></div>', unsafe_allow_html=True)


    # =========================================================================
    # 📺 SLIDE 2: RADAR TÁTICO DE ATRASOS (LISTA E ALERTAS)
    # =========================================================================
    elif slide_atual == 2:
        st.markdown("<h3 style='color: #0F172A; font-weight: 900; margin-bottom: 5px; font-family: sans-serif;'>🚨 C.C.O TÁTICO: PAINEL DE AÇÃO E ATRASOS (SLA)</h3>", unsafe_allow_html=True)

        if atrasados_total == 0:
            st.success("✅ **EXCELENTE:** Operação impecável! Nenhum volume em atraso crítico identificado.")
        else:
            cols_disp = df_atrasados.columns.tolist()
            col_nome = next((c for c in ['MOTORISTA', 'NOME_MOTORISTA', 'NOME_AGENTE', 'NOME', 'AGENTE', 'AGENTE_RAW'] if c in cols_disp), None)
            
            if col_nome and not df_atrasados[col_nome].isna().all():
                mot_critico = df_atrasados[col_nome].value_counts().idxmax()
                vols_mot = df_atrasados[col_nome].value_counts().max()
                if str(mot_critico).strip() == "" or str(mot_critico).upper() == "NAN": mot_critico = "Base (Não Roteirizado)"
            else:
                mot_critico = "Não Atribuído"
                vols_mot = atrasados_total
                
            def calc_dias_atraso(row):
                d_ref = row.get('DATA_LIMITE_OBJ', row.get('DATA_OBJ'))
                return (hoje_br - d_ref).days if pd.notnull(d_ref) else 1
            df_atrasados['DIAS_ATRASO'] = df_atrasados.apply(calc_dias_atraso, axis=1)
            atraso_max = df_atrasados['DIAS_ATRASO'].max()

            # 3 BLOCOS SUPERIORES
            c1, c2, c3 = st.columns(3)
            with c1: st.markdown(f'<div class="metric-card-alert"><div class="metric-title-lg" style="color: #B91C1C;">🚨 VOLUMES EM ATRASO CRÍTICO</div><div class="metric-value-lg" style="color: #7F1D1D;">{atrasados_total}</div><div class="metric-sub" style="color: #B91C1C;">SLA Rompido aguardando ação</div></div>', unsafe_allow_html=True)
            with c2: st.markdown(f'<div class="metric-card-info"><div class="metric-title-lg" style="color: #475569;">👤 MOTORISTA MAIS IMPACTADO</div><div class="metric-value-lg" style="color: #0F172A; font-size: 32px; margin-top: 15px;">{mot_critico}</div><div class="metric-sub">Concentra <b style="color:#EF4444;">{vols_mot}</b> pendências vencidas</div></div>', unsafe_allow_html=True)
            with c3: st.markdown(f'<div class="metric-card-info" style="border-left: 5px solid #F59E0B;"><div class="metric-title-lg" style="color: #475569;">⏳ PEDIDO MAIS ANTIGO</div><div class="metric-value-lg" style="color: #B45309;">{atraso_max} <span style="font-size: 20px;">Dias</span></div><div class="metric-sub">Dias de estouro no limite</div></div>', unsafe_allow_html=True)

            # TABELA
            col_tomador = next((c for c in ['TOMADOR', 'CLIENTE', 'EMPRESA'] if c in cols_disp), None)
            col_bairro = next((c for c in ['BAIRRO', 'DESTINO_BAIRRO', 'BAIRRO_COLETA'] if c in cols_disp), None)
            col_cidade = next((c for c in ['CIDADE', 'DESTINO_CIDADE', 'MUNICIPIO'] if c in cols_disp), None)
            
            cols_exibicao = ['PEDIDO']
            if col_tomador: cols_exibicao.append(col_tomador)
            if col_nome: cols_exibicao.append(col_nome)
            if col_bairro: cols_exibicao.append(col_bairro)
            if col_cidade: cols_exibicao.append(col_cidade)
            cols_exibicao.append('DIAS_ATRASO')
            
            df_view = df_atrasados[cols_exibicao].sort_values(by='DIAS_ATRASO', ascending=False)
            
            config_cols = {"PEDIDO": st.column_config.TextColumn("📦 PEDIDO"), "DIAS_ATRASO": st.column_config.ProgressColumn("🔴 DIAS VENCIDOS", format="%d dias", min_value=0, max_value=int(atraso_max) + 2)}
            if col_tomador: config_cols[col_tomador] = st.column_config.TextColumn("🏢 CLIENTE")
            if col_nome: config_cols[col_nome] = st.column_config.TextColumn("👤 MOTORISTA")
            if col_bairro: config_cols[col_bairro] = st.column_config.TextColumn("📍 BAIRRO")
            if col_cidade: config_cols[col_cidade] = st.column_config.TextColumn("🏙️ CIDADE")

            st.dataframe(df_view, column_config=config_cols, hide_index=True, use_container_width=True, height=350)

# --- RODAPÉ DISCRETO ---
st.markdown("<hr style='border: 1px solid #E2E8F0; margin-top: 10px; margin-bottom: 10px;'>", unsafe_allow_html=True)
st.markdown(f"""
<div style="text-align: center; color: #94A3B8; font-size: 11px; font-family: sans-serif; opacity: 0.8; font-weight: 600;">
    🔄 TELA {slide_atual} de 2 | Autopilot Ativo | Última sync: {hora_atual}
</div>
""", unsafe_allow_html=True)
