import streamlit as st
import pandas as pd
import io
import csv
import re
import unicodedata
import holidays
import os
import tempfile
import urllib.parse
import urllib.request
import requests
import time
import json
import hashlib
from datetime import datetime, timedelta, timezone
import random
import gspread
import uuid
import base64
import difflib
from streamlit_autorefresh import st_autorefresh
from fpdf import FPDF
# 🚀 NOVAS BIBLIOTECAS PARA A TABELA MODERNA
from st_aggrid import AgGrid, GridOptionsBuilder, ColumnsAutoSizeMode, JsCode
import qrcode
from PIL import Image, ImageDraw, ImageFont
import string

# 🚀 NOVAS BIBLIOTECAS PARA A TABELA MODERNA
from st_aggrid import AgGrid, GridOptionsBuilder, ColumnsAutoSizeMode, JsCode

FUSO_BR = timezone(timedelta(hours=-3))
LOGO_IGO = "https://i.postimg.cc/x84nnjjq/IGO-LOGO.png"
# =============================================================================
# ⚙️ CONFIGURAÇÕES GERAIS DO SISTEMA
# =============================================================================
AGENTES_XLS_AUTORIZADOS = [
    'veloz.express',
    'robson.melo',
    'william.bertoldo',
    'ludmila',
    'helio.frade',
    'domingos.ssa']
AGENTES_PDF_AUTORIZADOS = ['veloz.express', 'francisco.gru', 'adilson.lima','domingos.ssa']
ARQUIVO_USUARIOS_LOGIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "usuarios_login.json")
ARQUIVO_PORTAL_CLIENTE_LOGIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "portal_cliente_login.json")
NOME_PLANILHA_LOGIN_PORTAL = "DB_IGO_Logistica"
NOME_ABA_LOGIN_PORTAL = "Usuarios_Portal_Cliente"
SCOPES_GOOGLE_LOGIN = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]


def normalizar_usuario_login(usuario):
    return str(usuario).strip().upper()


def gerar_hash_senha(senha):
    return hashlib.sha256(str(senha).encode('utf-8')).hexdigest()


def verificar_senha(senha_digitada, senha_hash):
    if not senha_hash:
        return False
    return gerar_hash_senha(senha_digitada) == str(senha_hash)


def normalizar_tomador_portal(tomador):
    tomador_norm = str(tomador).strip().upper() or "TODOS"
    return tomador_norm.replace("CAEP", "SYNVIA").replace("CUNHA", "GRALAB")


def obter_token_google_login():
    token_str = os.environ.get("google_token_json")
    if not token_str:
        try:
            token_str = st.secrets.get("google_token_json")
        except Exception:
            token_str = None
    return token_str


def abrir_planilha_login_portal():
    planilha_existente = globals().get("planilha_db")
    if planilha_existente is not None:
        return planilha_existente

    token_str = obter_token_google_login()
    if not token_str:
        return None
    try:
        from google.oauth2.credentials import Credentials
        token_info = json.loads(token_str)
        creds = Credentials.from_authorized_user_info(token_info, scopes=SCOPES_GOOGLE_LOGIN)
        gc = gspread.authorize(creds)
        return gc.open(NOME_PLANILHA_LOGIN_PORTAL)
    except Exception:
        return None


def montar_config_portal_cliente(senha_hash, tomador):
    tomador_norm = normalizar_tomador_portal(tomador)
    return {
        "senha_hash": str(senha_hash).strip(),
        "logo": LOGO_IGO,
        "filtro": tomador_norm,
        "tomador": tomador_norm,
    }


def registrar_feedback_cadastro_usuario(tipo, mensagem):
    st.session_state.cadastro_usuario_feedback = {
        "tipo": tipo,
        "mensagem": mensagem,
    }


def salvar_portal_clientes_login_nuvem(usuarios):
    planilha = abrir_planilha_login_portal()
    if not planilha:
        return False
    try:
        try:
            aba = planilha.worksheet(NOME_ABA_LOGIN_PORTAL)
        except Exception:
            aba = planilha.add_worksheet(title=NOME_ABA_LOGIN_PORTAL, rows="200", cols="5")

        linhas = [["USUARIO", "SENHA_HASH", "TOMADOR"]]
        for usuario, info in sorted(usuarios.items()):
            linhas.append([
                normalizar_usuario_login(usuario),
                str(info.get("senha_hash", "")).strip(),
                normalizar_tomador_portal(info.get("tomador", info.get("filtro", "TODOS"))),
            ])

        aba.clear()
        aba.update("A1", linhas)
        return True
    except Exception:
        return False


def usuarios_padrao_login():
    return {
        "ROBSON.MELO": {
            "senha_hash": gerar_hash_senha("123"),
            "admin": True,
        },
        "WILLIAM.BERTOLDO": {
            "senha_hash": gerar_hash_senha("123"),
            "admin": True,
        },
    }


def carregar_usuarios_login():
    usuarios = {}

    if os.path.exists(ARQUIVO_USUARIOS_LOGIN):
        try:
            with open(ARQUIVO_USUARIOS_LOGIN, "r", encoding="utf-8") as f:
                dados = json.load(f)

            if isinstance(dados, dict):
                for usuario, info in dados.items():
                    user_norm = normalizar_usuario_login(usuario)
                    if not user_norm:
                        continue

                    if isinstance(info, dict):
                        senha_hash = str(info.get("senha_hash", "")).strip()
                        admin = bool(info.get("admin", False))
                    else:
                        # Compatibilidade com formato antigo: {"USUARIO": "senha_em_texto"}
                        senha_hash = gerar_hash_senha(str(info))
                        admin = False

                    if senha_hash:
                        usuarios[user_norm] = {
                            "senha_hash": senha_hash,
                            "admin": admin,
                        }
        except Exception:
            usuarios = {}

    if not usuarios:
        usuarios = usuarios_padrao_login()
        salvar_usuarios_login(usuarios)

    return usuarios


def salvar_usuarios_login(usuarios):
    with open(ARQUIVO_USUARIOS_LOGIN, "w", encoding="utf-8") as f:
        json.dump(usuarios, f, ensure_ascii=False, indent=2)


def usuarios_padrao_portal_cliente():
    return {
        "GRALAB": {
            "senha_hash": gerar_hash_senha("123"),
            "logo": "https://cdn.awsli.com.br/2702/2702264/logo/gralab-rbuogsxve7.png",
            "filtro": "GRALAB",
            "tomador": "GRALAB",
        },
        "IGO_LOGISTICA": {
            "senha_hash": gerar_hash_senha("admin"),
            "logo": "https://i.postimg.cc/x84nnjjq/IGO-LOGO.png",
            "filtro": "TODOS",
            "tomador": "TODOS",
        },
        "LOGISTICA.LABEST": {
            "senha_hash": gerar_hash_senha("123"),
            "logo": "logo_labest.png",
            "filtro": "LABEST",
            "tomador": "LABEST",
        },
        "DANILO.DUARTE": {
            "senha_hash": gerar_hash_senha("123"),
            "logo": "logo_labest.png",
            "filtro": "LABEST",
            "tomador": "LABEST",
        },
        "SYNVIA": {
            "senha_hash": gerar_hash_senha("123"),
            "logo": "https://i.postimg.cc/x84nnjjq/IGO-LOGO.png",
            "filtro": "SYNVIA",
            "tomador": "SYNVIA",
        },
        "LOGISTICA.BAT": {
            "senha_hash": gerar_hash_senha("123"),
            "logo": "souza cruz.png",
            "filtro": "SOUZA CRUZ",
            "tomador": "SOUZA CRUZ",
        },
    }


def carregar_portal_clientes_login():
    usuarios_nuvem = {}
    usuarios_local = {}

    planilha = abrir_planilha_login_portal()
    if planilha:
        try:
            aba = planilha.worksheet(NOME_ABA_LOGIN_PORTAL)
            dados = aba.get_all_values()
            if len(dados) > 1:
                cabecalhos = [str(c).strip().upper() for c in dados[0]]
                idx_usuario = cabecalhos.index("USUARIO")
                idx_senha = cabecalhos.index("SENHA_HASH")
                idx_tomador = cabecalhos.index("TOMADOR")

                for linha in dados[1:]:
                    usuario = normalizar_usuario_login(linha[idx_usuario] if idx_usuario < len(linha) else "")
                    senha_hash = str(linha[idx_senha] if idx_senha < len(linha) else "").strip()
                    tomador = normalizar_tomador_portal(linha[idx_tomador] if idx_tomador < len(linha) else "TODOS")
                    if usuario and senha_hash:
                        usuarios_nuvem[usuario] = montar_config_portal_cliente(senha_hash, tomador)
        except Exception:
            usuarios_nuvem = {}

    if os.path.exists(ARQUIVO_PORTAL_CLIENTE_LOGIN):
        try:
            with open(ARQUIVO_PORTAL_CLIENTE_LOGIN, "r", encoding="utf-8") as f:
                dados = json.load(f)

            if isinstance(dados, dict):
                for usuario, info in dados.items():
                    user_norm = normalizar_usuario_login(usuario)
                    if not user_norm:
                        continue

                    if isinstance(info, dict):
                        senha_hash = str(info.get("senha_hash", "")).strip()
                        filtro = str(info.get("filtro", "TODOS")).strip().upper() or "TODOS"
                        tomador = str(info.get("tomador", filtro)).strip().upper() or filtro
                    else:
                        senha_hash = gerar_hash_senha(str(info))
                        tomador = "TODOS"

                    if senha_hash:
                        usuarios_local[user_norm] = montar_config_portal_cliente(senha_hash, tomador)
        except Exception:
            usuarios_local = {}

    # Evita perda de cadastros quando uma das fontes (nuvem/local) estiver incompleta.
    usuarios = {}
    usuarios.update(usuarios_local)
    usuarios.update(usuarios_nuvem)

    if not usuarios:
        usuarios = usuarios_padrao_portal_cliente()
        salvar_portal_clientes_login(usuarios)

    return usuarios


def salvar_portal_clientes_login(usuarios):
    salvou_nuvem = salvar_portal_clientes_login_nuvem(usuarios)
    with open(ARQUIVO_PORTAL_CLIENTE_LOGIN, "w", encoding="utf-8") as f:
        json.dump(usuarios, f, ensure_ascii=False, indent=2)
    return salvou_nuvem


def sincronizar_usuarios_portal_para_salvar(usuarios, permitir_remocoes=False):
    # Sincroniza com o estado mais recente para evitar sobrescrita por sessao defasada.
    usuarios_novos = {}
    for usuario, info in (usuarios or {}).items():
        user_norm = normalizar_usuario_login(usuario)
        if not user_norm:
            continue
        if isinstance(info, dict):
            senha_hash = str(info.get("senha_hash", "")).strip()
            tomador = str(info.get("tomador", info.get("filtro", "TODOS"))).strip().upper() or "TODOS"
        else:
            senha_hash = gerar_hash_senha(str(info))
            tomador = "TODOS"

        if senha_hash:
            usuarios_novos[user_norm] = montar_config_portal_cliente(senha_hash, tomador)

    if permitir_remocoes:
        return usuarios_novos

    usuarios_atuais = carregar_portal_clientes_login()
    usuarios_merge = {}
    usuarios_merge.update(usuarios_atuais)
    usuarios_merge.update(usuarios_novos)
    return usuarios_merge


def persistir_e_recarregar_portal_clientes(usuarios, permitir_remocoes=False):
    usuarios_sincronizados = sincronizar_usuarios_portal_para_salvar(
        usuarios,
        permitir_remocoes=permitir_remocoes,
    )
    salvou_nuvem = salvar_portal_clientes_login(usuarios_sincronizados)
    recarregado = carregar_portal_clientes_login()
    st.session_state.portal_clientes_login = recarregado
    return salvou_nuvem, recarregado


def normalizar_modo_disparo_whatsapp(valor):
    texto = unicodedata.normalize('NFKD', str(valor).strip()).encode('ASCII', 'ignore').decode('utf-8').upper()
    if not texto or texto in {'NAN', 'NONE'}:
        return ''
    if 'PDF' in texto and 'XLS' in texto:
        return 'PDF_XLS'
    if 'PDF' in texto:
        return 'PDF'
    if 'XLS' in texto:
        return 'XLS'
    return 'NOTIFICACAO'


def obter_modo_disparo_whatsapp_legacy(login_agente):
    login = str(login_agente).strip().lower()
    login_base = login.split('|')[0].split('/')[0].strip()
    is_pdf = login in AGENTES_PDF_AUTORIZADOS or login_base in AGENTES_PDF_AUTORIZADOS
    is_xls = login in AGENTES_XLS_AUTORIZADOS or login_base in AGENTES_XLS_AUTORIZADOS
    if is_pdf and is_xls:
        return 'PDF_XLS'
    if is_pdf:
        return 'PDF'
    if is_xls:
        return 'XLS'
    return 'NOTIFICACAO'


def obter_modo_disparo_whatsapp(login_agente):
    login = str(login_agente).strip().lower()
    login_base = login.split('|')[0].split('/')[0].strip()

    if not DF_AGENTES.empty and 'TIPO_DISPARO_WHATSAPP' in DF_AGENTES.columns:
        df_match = DF_AGENTES[DF_AGENTES['LOGIN DO AGENTE'].astype(str).str.strip().str.lower() == login]
        if df_match.empty and login_base != login:
            df_match = DF_AGENTES[DF_AGENTES['LOGIN DO AGENTE'].astype(str).str.strip().str.lower() == login_base]
        if not df_match.empty:
            modo = normalizar_modo_disparo_whatsapp(df_match.iloc[0].get('TIPO_DISPARO_WHATSAPP', ''))
            if modo:
                return modo

    return obter_modo_disparo_whatsapp_legacy(login)


def etiqueta_modo_disparo_whatsapp(modo):
    return {
        'NOTIFICACAO': 'Somente notificação',
        'PDF': 'Notificação + PDF',
        'XLS': 'Notificação + XLS',
        'PDF_XLS': 'Notificação + PDF + XLS',
    }.get(modo, 'Somente notificação')


def gerar_saudacao_spintax(nome, uf=""):
    """
    🔥 GERADOR DE SAUDAÇÕES INTELIGENTE COM REGIONALIZAÇÃO POR ESTADO
    Oferece mensagens personalizadas, variadas e motivacionais por região
            
    Args:
        nome: Nome do agente/motorista
        uf: Estado (UF) para mensagens regionalizadas (opcional)
    """
            
    # 🔥 SAUDAÇÕES GENÉRICAS (FUNCIONAM EM QUALQUER REGIÃO - VERSÃO ULTRA)
    saudacoes_genericas = [
        # --- As Clássicas (Originais) ---
        f"Olá {nome}, tudo bem? Segue a ",
        f"Bom dia, {nome}. Aqui está a ",
        f"Fala {nome}! Passando para deixar a ",
        f"Oi {nome}. A sua ",
        f"Tudo certo, {nome}? Acabou de sair a ",
        f"Opa {nome}, beleza? Dá uma olhada na ",
        f"E aí {nome}! Já está liberada a ",
        f"Salve {nome}! Bora pra cima, segue a ",
        f"Tudo tranquilo por aí, {nome}? Passando a ",
        f"Fala grande {nome}! Aqui vai a ",
        f"Alô {nome}! Passando pra enviar a ",
        f"Bora rodar, {nome}! Aqui tá a ",
        f"Oi {nome}, tudo na paz? Confere aí a ",
        f"{nome}, meu parceiro! Já saiu a ",
        f"Fala guerreiro! {nome}, segue a ",
        f"Opa {nome}! Força na labuta, aqui vai a ",
        f"Tamo junto, {nome}! Segue a rota de ",
        f"Força {nome}! Partiu rodar essa ",
        f"Valeu {nome}, agora é com você. Bora nessa ",
        f"{nome}, bomba! Tá saindo agora a ",

        # --- Casuais e Amigáveis ---
        f"E aí {nome}, beleza pura? Confere a ",
        f"Tudo joia, {nome}? Acabei de gerar a ",
        f"Fala {nome}, na escuta? Aqui vai a ",
        f"Salve {nome}! Tudo no jeito por aqui, segue a ",
        f"Oi {nome}! Passando rapidinho pra deixar a ",
        f"Fala meu caro {nome}! Tudo pronto, aqui vai a ",
        f"Tudo em ordem, {nome}? Já mandei a ",
        f"E aí {nome}, como estamos? Dá um confere na ",
        f"Opa {nome}, tranquilo? Já puxei a ",
        f"Fala {nome}! Direto ao ponto, aqui tá a ",
        f"Tudo ótimo por aí, {nome}? Segue o link da ",
        f"{nome}, como vai a lida? Deixando aqui a ",
        f"Boa {nome}! Passando a bola pra você, segue a ",
        f"Ei {nome}, tudo certo? Acabei de atualizar a ",
        f"Tudo sussa, {nome}? Passando pra deixar a ",
        f"Aí sim, {nome}! Já tá separada a ",
        f"Opa {nome}, tudo nos trinks? Já saiu a ",
        f"Fala {nome}, meu consagrado! Dá uma olhada na ",
        f"E aí {nome}, de boa na lagoa? Dá uma checada na ",
        f"Tamo na área, {nome}! Já soltei a ",

        # --- Focadas em Operação / Logística / Trecho ---
        f"Bora acelerar, {nome}! Já está na mão a ",
        f"E aí {nome}, preparado? Aqui está a ",
        f"{nome}, bom dia! Partiu? Segue a ",
        f"Opa {nome}! Rumo a mais um fechamento, confere a ",
        f"Salve {nome}! Boa rota pra você, segue a ",
        f"Fala {nome}! Caminho livre, aqui vai a ",
        f"Motor ligado, {nome}? Já soltei a ",
        f"Bora pra mais uma, {nome}! Segue a ",
        f"Atenção {nome}, na agulha! Aqui tá a ",
        f"Fala mestre {nome}! Bora despachar, segue a ",
        f"Opa {nome}! Tudo mapeado, confere a ",
        f"Vamos nessa, {nome}! Tá liberada a ",
        f"{nome}! Pra cima deles, segue a ",
        f"Fala {nome}, pé na estrada! Aqui vai a ",
        f"Pronto pro trecho, {nome}? Segue a ",
        f"Simbora {nome}! Já deixei no esquema a ",
        f"Tudo engatilhado, {nome}. Dá uma olhada na ",
        f"Boa viagem hoje, {nome}! Passando a ",
        f"Chegou a hora, {nome}! Partiu rodar a ",
        f"Aperta o cinto, {nome}! Já mandei a ",
        f"Chama na rota, {nome}! Tá liberada a ",
        f"Fala {nome}! Pneu no asfalto, aqui tá a ",
        f"Salve {nome}, na marcha! Confere aí a ",

        # --- Alta Energia / Motivacionais ---
        f"Tudo no grau, {nome}? Aqui tá a ",
        f"Dá o start aí, {nome}! Segue a ",
        f"Bora fazer acontecer, {nome}! Segue a ",
        f"Dia de vitória, {nome}! Aqui vai a ",
        f"E aí {nome}, 100%? Aqui tá a ",
        f"Bora que o dia tá rendendo, {nome}! Segue a ",
        f"Missão dada é missão cumprida, {nome}! Segue a ",
        f"E aí {nome}, pronto pro bote? Aqui tá a ",
        f"Fala {nome}, correria pura? Aqui vai a ",
        f"Bora bater meta, {nome}! Segue a ",
        f"Bora pro game, {nome}! Aqui tá a ",
        f"E aí {nome}, bora pra luta? Segue a ",
        f"Fala {nome}! Tá na hora do show, aqui vai a ",
        f"Simbora {nome}, sem perder tempo! Segue a ",
        f"Boa sorte no trecho hoje, {nome}! Segue a ",
        f"Tudo tranquilo, {nome}? Foco na missão, segue a ",
        f"Fala {nome}, bora acelerar os fretes! Aqui vai a ",
        f"Firme e forte, {nome}? Aqui tá a ",
        f"Opa {nome}, que hoje seja top! Aqui vai a ",
        f"Bora fazer grana, {nome}! Segue a ",
        f"Fala {nome}, bora fazer render! Tá liberada a ",
        f"Partiu pro ataque, {nome}! Aqui vai a ",
        f"E aí {nome}, bora dar o nome hoje! Tá na mão a ",

        # --- Mais Diretas, Formais e Status Check ---
        f"Prezado {nome}, segue a ",
        f"{nome}, conforme alinhado, envio a ",
        f"Atenção {nome}, já está disponível a ",
        f"Bom trabalho, {nome}. Aqui está a ",
        f"Olá {nome}. Segue para acompanhamento a ",
        f"{nome}, atualizando: segue a ",
        f"Opa {nome}, tudo nos conformes? Dá um confere na ",
        f"Fala {nome}, tudo em paz? Já puxei a ",
        f"Opa {nome}, na atividade? Confere a ",
        f"Tudo 100%, {nome}? Partiu rodar com a ",
        f"Opa {nome}, firmão? Já deixei engatilhada a ",
        f"E aí {nome}, na pegada? Aqui tá a ",
        f"Opa {nome}, tudo no esquema? Já enviei a ",
        f"E aí {nome}! Deixando tudo no prumo, segue a ",
        f"Salve {nome}, bora produzir! Confere a ",
        f"Fala {nome}! Tudo no radar, segue a ",
        f"E aí {nome}, na boa? Passando pra entregar a ",
        f"Opa {nome}, prontinho por aqui! Segue a ",
        f"Tudo zerado, {nome}? Confere a ",
        f"Salve {nome}, bora triturar essas entregas! Segue a ",
        f"E aí {nome}, tudo nos eixos? Já puxei a ",
        f"Opa {nome}, boa lida! Segue a "
    ]
            
    # 🔥 SAUDAÇÕES REGIONALIZADAS POR ESTADO (VERSÃO ULTRA)
            
    saudacoes_sp = [
        f"Ô {nome}! Tá rolando rota aí em SP, segue a ",
        f"E lá vem mais, {nome}. Aqui tá liberada a ",
        f"Bora lá, {nome}! São Paulo chama, segue a ",
        f"Ó o trem, {nome}! A rota de SP tá pronta. Confere aí a ",
        f"{nome}, toma lá sua rota de SP! Aqui vai a ",
        f"Fala {nome}, beleza meu? Rota de SP na mão, segue a ",
        f"E aí {nome}, suave? São Paulo não para, aqui tá a ",
        f"Salve {nome}, a milhão! Tá liberada a ",
        f"Opa {nome}, trampo chamando! Rota de SP pronta, confere a ",
        f"E aí {nome}, daora? Já soltei a ",
        f"Fala {nome}, meu bom! Aqui em SP o bicho pega, segue a ",
        f"Ô loco {nome}, bora rodar! Aqui tá a ",
        f"Salve {nome}! Rota paulista no esquema, segue a ",
        f"Bora pro corre, {nome}! SP na área, aqui vai a "
    ]
            
    saudacoes_rj = [
        f"Abraço {nome}! A rota do RJ tá saindo agora. Segue a ",
        f"Pô {nome}, beleza? Rio de Janeiro chama, aqui vai a ",
        f"Meu brother {nome}! Tá liberada sua rota carioca. Confere aí a ",
        f"Fala {nome} do Rio! Partiu essa rota, vamo que vamo. Segue a ",
        f"{nome}, meu parceiro carioca! Bora rodar essa. Aqui tá a ",
        f"Qual é {nome}, tranquilidade? Rio de Janeiro chama, aqui vai a ",
        f"Fala tu, {nome}! Tá liberada sua rota. Confere aí a ",
        f"E aí {nome}, suave na nave? Partiu corre, segue a ",
        f"Papo reto, {nome}! Sua rota tá na mão, segue a ",
        f"Coé {nome}, demorou! Partiu rua, segue a ",
        f"Bora pro corre, {nome}! RJ fervendo, confere a ",
        f"Fala mestre {nome}! Rota carioca no jeito, aqui tá a ",
        f"E aí {nome}, tudo na paz mermão? Aqui vai a "
    ]
            
    saudacoes_mg = [
        f"E lá vai, {nome}! Minas Gerais com tudo, segue a ",
        f"Tamo junto, {nome}! Minas tá bombando, aqui vai a ",
        f"Bora lá, {nome}. A rota mineira chegou! Confere aí a ",
        f"Fala {nome}, guerreiro de MG! Essa aqui é sua. Segue a ",
        f"{nome}, mineiro de lei! Partiu essa rota agora. Aqui tá a ",
        f"Uai {nome}, bão demais? Minas na área, aqui vai a ",
        f"Fala {nome}, pega esse trem aí! Segue a ",
        f"Nu, {nome}! Trem tá feio não, partiu essa rota. Aqui tá a ",
        f"Ô sô {nome}, beleza? Bora rodar esse trecho mineiro. Segue a ",
        f"Bom demais da conta, {nome}! Confere a ",
        f"Bora pelejar, {nome}! Trem tá pronto, segue a ",
        f"E aí {nome}, firme? Sua rota mineira no capricho. Aqui vai a "
    ]
            
    saudacoes_ba = [
        f"Salve {nome}! Bahia tá chamando, bora nessa. Segue a ",
        f"Lá no malvado, {nome}! A rota baiana tá pronta. Aqui vai a ",
        f"E aí meu nordestino {nome}? Bora explorar essa rota. Confere aí a ",
        f"{nome}, partiu Bahia! Força nessa labuta. Segue a ",
        f"Ô jóia, {nome}! Mais uma rota baiana pra você mandar bem. Aqui tá a ",
        f"Oxe {nome}! A rota baiana tá no esquema. Aqui vai a ",
        f"E aí {nome}, meu rei? Bora brocar nessa rota. Confere aí a ",
        f"Fala {nome}, arretado! Força nessa labuta, segue a ",
        f"Bora rodar, {nome}! Oxe, tá esperando o quê? Segue a ",
        f"Fala {nome}, partiu malvado? Aqui vai a ",
        f"E aí {nome}, beleza pura? Bahia na área, confere a ",
        f"{nome}, meu parceiro! Bora pra cima dessa rota. Segue a "
    ]
            
    saudacoes_rs = [
        f"Opa {nome}, gaúcho! Bora rodar aí no Rio Grande. Segue a ",
        f"E lá pro Sul, {nome}! A rota tá quente. Aqui vai a ",
        f"Fala guerreiro do RS! {nome}, essa rota é sua. Confere aí a ",
        f"{nome}, tá rolando mais uma no Sul. Bora bombar. Segue a ",
        f"Ó o tremendo, {nome}! Sua rota gaúcha tá saindo. Aqui tá a ",
        f"Opa {nome}, tchê! Bora rodar. Segue a ",
        f"Bah {nome}! A rota tá quente. Aqui vai a ",
        f"Mas que barbaridade, {nome}! Bora meter ficha. Segue a ",
        f"E aí {nome}, tri legal? Partiu trecho. Segue a ",
        f"Bora lá, {nome}! O Rio Grande te chama. Confere a ",
        f"Fala {nome}, cupincha! Rota liberada, aqui vai a ",
        f"Tudo nos trinques, {nome}? Pega essa rota gaúcha. Segue a "
    ]
            
    saudacoes_sc = [
        f"{nome}, parceiro de Santa Catarina! A rota tá liberada. Segue a ",
        f"Salve {nome}! Santa Catarina tá pedindo, bora lá. Aqui vai a ",
        f"E aqui pro Sul, {nome}! Essa rota catarinense é show. Confere aí a ",
        f"Fala {nome} de SC! Partiu mais essa. Segue a ",
        f"Opa {nome}, tamo junto! Sua rota tá saindo. Aqui tá a ",
        f"Fala {nome}, beleza? Essa rota barriga-verde é show. Confere aí a ",
        f"E aí {nome}, tudo certo? Bora rodar pelo litoral e serra. Segue a ",
        f"Bora acelerar, {nome}! SC te chama. Confere a ",
        f"{nome}, firmeza? Rota catarinense engatilhada. Aqui vai a ",
        f"Fala parceiro {nome}! Santa Catarina tá no jeito. Segue a ",
        f"Tudo pronto, {nome}! Acelera em SC. Aqui tá a "
    ]
            
    saudacoes_pr = [
        f"Ô {nome}! Paraná chama, bora nessa rota agora. Segue a ",
        f"Fala paranaense! {nome}, sua rota tá pronta. Aqui vai a ",
        f"E lá vem mais, {nome}! Paraná tá bombando. Confere aí a ",
        f"{nome}, tamo junto! Rota de PR saindo agora. Segue a ",
        f"Bora lá {nome}! Sua labuta em PR tá aqui. Aqui tá a ",
        f"Fala {nome}! Sua rota paranaense tá pronta. Aqui vai a ",
        f"E aí {nome}, firme e forte? Bora rodar o Paraná. Segue a ",
        f"Opa {nome}, beleza? Trecho paranaense liberado. Confere a ",
        f"Fala {nome}! Capricha nessa rota aí no PR. Aqui vai a ",
        f"Simbora {nome}! Paraná não para, segue a ",
        f"{nome}, tudo certo por aí? Puxa essa rota. Aqui tá a "
    ]
            
    saudacoes_go = [
        f"Opa {nome}! Goiás tá ligado em você. Aqui vai a ",
        f"Salve {nome} do Centro-Oeste! A rota saiu. Segue a ",
        f"E lá em Goiás, {nome}! Bora rodar essa. Confere aí a ",
        f"Fala {nome}! Sua rota goiana tá pronta. Aqui vai a ",
        f"{nome}, parceiro! Goiás chama, vamo que vamo. Segue a ",
        f"Opa {nome}, bão? Goiás tá ligado em você. Aqui vai a ",
        f"{nome}, moço! Bora rodar esse trem. Confere aí a ",
        f"E aí {nome}, bão ou não? Rota liberada. Aqui tá a ",
        f"Bora rodar, {nome}! Pega essa rota em GO. Segue a ",
        f"Fala {nome}, firmeza no cerrado? Confere a ",
        f"Tudo nos eixos, {nome}? Goiás te aguarda. Aqui vai a "
    ]
            
    saudacoes_df = [
        f"{nome}, brasiliense! Sua rota no DF tá saindo. Segue a ",
        f"Fala {nome}! Aqui em Brasília pulsando. Aqui vai a ",
        f"E lá tá, {nome}! Sua rota de DF bombando. Confere aí a ",
        f"Opa {nome}, capital do país chamando! Bora nessa. Segue a ",
        f"Salve {nome}! DF com tudo, aqui tá sua rota. Aqui tá a ",
        f"{nome}, beleza? Sua rota no Quadrado tá saindo. Segue a ",
        f"E aí véi, {nome}! Sua rota de BSB bombando. Confere aí a ",
        f"Bora rodar o quadrado, {nome}! Rota no DF liberada. Segue a ",
        f"Fala {nome}, tranquilo? DF na área, confere a ",
        f"{nome}, na pista! Partiu eixão, aqui vai a ",
        f"Bora fechar o dia, {nome}! Rota do DF na mão. Aqui tá a "
    ]
            
    # Mapear UF para saudações regionalizadas (SP removido para cair na lista de +100)
    dict_saudacoes_uf = {
        'RJ': saudacoes_rj,
        'MG': saudacoes_mg,
        'BA': saudacoes_ba,
        'RS': saudacoes_rs,
        'SC': saudacoes_sc,
        'PR': saudacoes_pr,
        'GO': saudacoes_go,
        'DF': saudacoes_df,
    }
            
    # Selecionar saudação: regional se UF disponível, senão genérica
    uf_upper = str(uf).upper().strip() if uf else ""
    if uf_upper in dict_saudacoes_uf:
        saudacoes_escolhidas = dict_saudacoes_uf[uf_upper]
    else:
        saudacoes_escolhidas = saudacoes_genericas
            
    # 🔥 FECHAMENTOS BLINDADOS (PEDINDO PARA SALVAR O CONTATO E RESPONDER 'OK') 🔥
    fechamentos = [
        "⚠️ *Aviso Rápido:* Por favor, salve o nosso número nos seus contatos e responda com um 'OK' para confirmar o recebimento desta rota. Boa viagem!",
        "📌 Para garantir que o sistema não falhe, adicione este número aos seus contatos e me mande um 'OK' confirmando a leitura. Bom trabalho!",
        "🚨 *Importante:* Salve nosso contato na sua agenda para não perder as próximas atualizações. Me dê um 'OK' para eu saber que a rota chegou bem. Sucesso hoje!",
        "✅ Ah, um favor: guarde este número na sua lista de contatos e confirme o recebimento com um 'OK'. Dirija com cuidado e boa coleta!",
        "📱 Para a comunicação ficar perfeita, não esqueça de salvar nosso número nos seus contatos e me confirmar aqui com um 'OK'. Um abraço e boa rota!",
        "💪 Tá tudo pronto! Salva nosso contato aí e manda um 'OK' rapidinho confirmando que recebeu a rota. Confiança em você!",
        "🎯 Última coisa: guarda nosso número e confirma com 'OK' quando receber. Muito obrigado e sucesso na sua rota!",
        "🚀 Só mais um detalhe: salva nosso contato e manda aquele 'OK' pra gente saber que tá tudo certo. Bora rodar!",
        "☑️ Pra tudo rodar perfeitamente, adiciona nosso número aos contatos e confirma com 'OK'. Força aí!",
        "📲 Fechando: salva o contato IGO e responde com um simples 'OK'. Muito obrigado e que a rota seja sucesso!",
    ]

    inicio = random.choice(saudacoes_escolhidas)
    fim = random.choice(fechamentos)
    return inicio, fim


CSS_DASHBOARD = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    /* 🔥 FUNDO PRINCIPAL 100% BRANCO 🔥 */
    [data-testid="stAppViewContainer"] {
        transition: background-color 0.3s ease;
        font-family: 'Inter', sans-serif;
        background-color: #FFFFFF !important; 
    }

    /* ── SIDEBAR PREMIUM ── */
    [data-testid="stSidebar"],
    [data-testid="stSidebar"] > div:first-child {
        background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%) !important;
        border-right: 1px solid #dbe3ef !important;
    }
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] h3 {
        color: #1e293b !important;
    }
    [data-testid="stSidebar"] div.stRadio > div {
        gap: 8px;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] > label {
        background: linear-gradient(135deg, #FFFFFF 0%, #F8FAFC 100%);
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 8px 10px;
        margin: 0;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06);
        transition: all 0.2s ease;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] > label:hover {
        border-color: #93C5FD;
        transform: translateX(2px);
        box-shadow: 0 6px 16px rgba(59, 130, 246, 0.14);
    }
    [data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child {
        display: none;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] input[type="radio"] {
        appearance: none !important;
        -webkit-appearance: none !important;
        accent-color: transparent !important;
        width: 0 !important;
        height: 0 !important;
        margin: 0 !important;
        opacity: 0 !important;
        position: absolute !important;
        pointer-events: none !important;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] > label p {
        font-size: 14px;
        font-weight: 700;
        color: #0F172A;
        margin: 0;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) {
        background: linear-gradient(135deg, #0EA5E9 0%, #2563EB 100%);
        border-color: #1D4ED8;
        box-shadow: 0 10px 20px rgba(37, 99, 235, 0.30);
        transform: translateX(4px);
    }
    [data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) p,
    [data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) span,
    [data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) div,
    [data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) * {
        color: #FFFFFF !important;
        font-weight: 800;
    }
    [data-testid="stSidebar"] .stButton > button,
    [data-testid="stSidebar"] [data-testid="stFormSubmitButton"] > button {
        border-radius: 10px !important;
        border: 1px solid #93c5fd !important;
        background: linear-gradient(180deg, #eff6ff 0%, #dbeafe 100%) !important;
        color: #0f172a !important;
        font-weight: 700 !important;
        box-shadow: 0 4px 10px rgba(37, 99, 235, 0.10) !important;
        transition: all 0.2s ease !important;
        min-height: 42px !important;
    }
    [data-testid="stSidebar"] .stButton > button:hover,
    [data-testid="stSidebar"] [data-testid="stFormSubmitButton"] > button:hover {
        transform: translateY(-1px) !important;
        border-color: #60a5fa !important;
        background: linear-gradient(180deg, #dbeafe 0%, #bfdbfe 100%) !important;
        box-shadow: 0 8px 18px rgba(37, 99, 235, 0.18) !important;
    }
    [data-testid="stSidebar"] .stDateInput input,
    [data-testid="stSidebar"] .stDateInput button,
    [data-testid="stSidebar"] .stDateInput [role="button"],
    [data-testid="stSidebar"] [data-baseweb="select"] > div {
        border-radius: 10px !important;
        border: 1px solid #cbd5e1 !important;
        background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%) !important;
        color: #0f172a !important;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05) !important;
    }
    [data-testid="stSidebar"] .stDateInput input:focus {
        border-color: #93c5fd !important;
        box-shadow: 0 0 0 1px #93c5fd !important;
    }

    /* ── LAYOUT ── */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {background-color: transparent !important;}
    .block-container {
        padding-top: 1.2rem !important;
        padding-bottom: 1rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        max-width: 98% !important;
    }

    /* ── KPI CARDS MODERNOS ── */
    .kpi-card {
        border-radius: 12px;
        padding: 16px;
        text-align: left;
        cursor: pointer;
        transition: all 0.2s ease;
        position: relative;
        overflow: hidden;
        height: 95px;
    }
    .kpi-card:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        transform: translateY(-2px);
    }
    .kpi-card.active {
        box-shadow: 0 0 0 2px #3b82f6;
    }

    /* ── HEADER SUPERIOR ── */
    .header-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 18px;
        padding-bottom: 14px;
        border-bottom: 1.5px solid #e2e8f0;
    }
    .header-title {
        font-size: 22px;
        font-weight: 900;
        color: #0f172a;
        letter-spacing: -0.3px;
    }
    .sync-status {
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .status-chip {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 12px;
        font-weight: 700;
        border-radius: 99px;
        padding: 5px 12px;
        white-space: nowrap;
    }
    .status-chip.online {
        color: #10b981;
        background: #f0fdf4;
        border: 1px solid #bbf7d0;
    }
    .status-chip.user {
        color: #1d4ed8;
        background: #eff6ff;
        border: 1px solid #bfdbfe;
    }
    .sync-dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background: #10b981;
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.4; }
    }

    /* ── BARRA DE PROGRESSO DOS PEDIDOS DO DIA ── */
    /* 🎯 ALTURA DO BLOCO: Altere "padding: 20px" para aumentar/diminuir espaço interno */
    /* 🎯 ESPAÇO ENTRE ELEMENTOS: Altere "gap: 12px" para aumentar/diminuir distância entre linhas */
    .progress-block-main {
        background: linear-gradient(135deg, #ffffff 0%, #f8fafc 52%, #eff6ff 100%);
        border: 1px solid #bfdbfe;
        border-radius: 16px;
        padding: 14px; /* 🔴 ALTURA INTERNA - Aumentar para 25px, 30px, etc */
        margin: 12px 0 18px 0;
        overflow: hidden;
        box-shadow: 0 12px 26px rgba(37, 99, 235, 0.16);
    }
    .progress-block-content {
        position: relative;
        z-index: 1;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 8px; /* 🔴 ESPAÇO ENTRE LINHAS - Aumentar para 14px, 16px, 18px, etc */
    }
    .progress-title {
        font-size: 12px;
        font-weight: 700;
        color: #0f172a;
        align-self: flex-start;
    }
    /* ── PROGRESS WITH COUNTER ── */
    /* 🎯 ALTURA DA BARRA: Altere "height: 8px" para aumentar/diminuir espessura */
    .progress-row {
        display: flex;
        align-items: center;
        gap: 10px; /* 🔴 ESPAÇO entre barra e número - Aumentar para 14px, 16px, etc */
        width: 100%;
    }
    .progress-bar-container {
        width: 100%;
        height: 6px; /* 🔴 ESPESSURA DA BARRA - Aumentar para 10px, 12px, 14px, etc */
        background: #e2e8f0;
        border-radius: 99px;
        overflow: hidden;
        box-shadow: inset 0 1px 2px rgba(0,0,0,0.05);
    }
    .progress-bar-fill {
        height: 100%;
        border-radius: 99px;
        transition: width 0.8s cubic-bezier(0.34, 1.56, 0.64, 1);
        background: linear-gradient(90deg, #ef4444 0%, #f59e0b 50%, #22c55e 100%);
        box-shadow: 0 0 10px rgba(34, 197, 94, 0.6);
    }
    .progress-text {
        font-size: 12px;
        color: #475569;
        font-weight: 500;
        align-self: flex-start;
    }
            
    .progress-counter {
        font-size: 20px;
        font-weight: 800;
        color: #0f172a;
        background: #f1f5f9;
        padding: 6px 12px;
        border-radius: 8px;
        border: 1px solid #e2e8f0;
        white-space: nowrap;
        min-width: 68px;
        text-align: center;
    }
    </style>
"""

if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

if 'usuario_logado' not in st.session_state:
    st.session_state.usuario_logado = None

if 'usuarios_login' not in st.session_state:
    st.session_state.usuarios_login = carregar_usuarios_login()

if 'portal_clientes_login' not in st.session_state:
    st.session_state.portal_clientes_login = carregar_portal_clientes_login()

if 'log_triagem' not in st.session_state:
    st.session_state.log_triagem = []

# TELA DE LOGIN BLINDADA
if not st.session_state.autenticado:
    st.markdown("""
        <style>
        [data-testid="stSidebar"] { display: none; }
        header { display: none !important; }
        [data-testid="stAppViewContainer"] { 
            background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%) !important; 
            font-family: 'Inter', sans-serif; 
        }
                
        /* Empurra o bloco inteiro para baixo na medida certa */
        .block-container { 
            padding-top: 15vh !important; 
            max-width: 100% !important;
        }
                
        /* Deixa o formulário com cara de App */
        [data-testid="stForm"] { 
            background-color: #ffffff !important; 
            padding: 40px !important; 
            border-radius: 20px !important; 
            box-shadow: 0 20px 40px -5px rgba(0,0,0,0.1) !important; 
            border: none !important; 
        }
                
        .login-title { 
            text-align: center; 
            font-size: 22px; 
            font-weight: 900; 
            color: #0f172a; 
            margin-top: 15px; 
            margin-bottom: 25px; 
        }
        </style>
    """, unsafe_allow_html=True)

    # Usa colunas nativas para esmagar o formulário perfeitamente no centro
    _, col_login, _ = st.columns([1, 1.2, 1])

    with col_login:
        with st.form("form_login", clear_on_submit=False):
            # Colunas internas para centralizar o logotipo
            col_espaco1, col_logo, col_espaco2 = st.columns([1, 1.5, 1])
            with col_logo:
                st.image('https://i.postimg.cc/x84nnjjq/IGO-LOGO.png', use_container_width=True)
                        
            st.markdown('<div class="login-title">CONTROLE OPERACIONAL</div>', unsafe_allow_html=True)

            usuario = normalizar_usuario_login(st.text_input("👤 Usuário"))
            senha = st.text_input("🔑 Senha", type="password")
                    
            st.markdown("<br>", unsafe_allow_html=True)

            if st.form_submit_button("🚀 ACESSAR SISTEMA", type="primary", use_container_width=True):
                usuarios_login = st.session_state.usuarios_login
                info_usuario = usuarios_login.get(usuario)

                if info_usuario and verificar_senha(senha, info_usuario.get("senha_hash", "")):
                    st.session_state.autenticado = True
                    st.session_state.usuario_logado = usuario
                    st.rerun()
                else:
                    st.error("❌ Credenciais inválidas.")
    st.stop()

# Aplica o CSS do painel
# Aplica o CSS do painel
st.markdown(CSS_DASHBOARD, unsafe_allow_html=True)

# =============================================================================
# 🔔 SISTEMA GLOBAL DE NOTIFICAÇÕES (TOASTS NA MEMÓRIA)
# =============================================================================
if 'ui_toast' in st.session_state:
    st.toast(st.session_state.ui_toast['msg'], icon=st.session_state.ui_toast['icon'])
    del st.session_state.ui_toast

# =============================================================================
# 🔗 2. CONEXÕES OFICIAL E SANDBOX (MOTOR DE DADOS INTACTO)
# =============================================================================


@st.cache_resource
def conectar_banco():
    scopes = ["https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"]
    try:
        import json
        from google.oauth2.credentials import Credentials
        token_str = os.environ.get("google_token_json")
        if not token_str:
            try:
                token_str = st.secrets.get("google_token_json")
            except BaseException:
                pass
        if not token_str:
            st.error("⚠️ Senha do Google não detectada.")
            return None
        token_info = json.loads(token_str)
        creds = Credentials.from_authorized_user_info(
            token_info, scopes=scopes)
        gc = gspread.authorize(creds)
        return gc.open("DB_IGO_Logistica")
    except Exception as e:
        st.error(f"Erro na leitura da chave: {e}")
    return None


@st.cache_resource
def conectar_sandbox():
    scopes = ["https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"]
    try:
        import json
        from google.oauth2.credentials import Credentials
        token_str = os.environ.get("google_token_json")
        if not token_str:
            try:
                token_str = st.secrets.get("google_token_json")
            except BaseException:
                pass
        if not token_str:
            return None
        token_info = json.loads(token_str)
        creds = Credentials.from_authorized_user_info(
            token_info, scopes=scopes)
        gc = gspread.authorize(creds)
        return gc.open("Import_Umove")
    except Exception as e:
        st.error(
            f"⚠️ Planilha Sandbox 'Import_Umove' não encontrada no Drive. Erro: {e}")
        return None


@st.cache_resource
def conectar_financeiro():
    scopes = ["https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"]
    try:
        import json
        from google.oauth2.credentials import Credentials
        token_str = os.environ.get("google_token_json")
        if not token_str:
            try:
                token_str = st.secrets.get("google_token_json")
            except BaseException:
                pass
        if not token_str:
            return None
        token_info = json.loads(token_str)
        creds = Credentials.from_authorized_user_info(
            token_info, scopes=scopes)
        gc = gspread.authorize(creds)
        return gc.open_by_key("1yaVC8MnF3BiwnNDw1DXRu6cxsG4Hnylu2Uv-WVwt1TQ")
    except Exception as e:
        return None


planilha_db = conectar_banco()
planilha_sandbox = conectar_sandbox()
planilha_financeiro = conectar_financeiro()

CLIENTES_AUTORIZADOS = sorted(["CAEP",
                            "MB_CAEP",
                            "CUNHA",
                            "CONTRAPROVA",
                            "SAPIENS",
                            "GRALAB",
                            "SYNVIA",
                            "INNOVATOX",
                            "LABEST",
                            "AIRLAB",
                            "UNILABOR",
                            "SODRE",
                            "BRASILIENSE",
                            "SOUZA CRUZ",
                            "HEXALIFE",
                            "ECOLYZER"])


def corrigir_nomes_relatorio(texto):
    if pd.isna(texto):
        return ""
    t = str(texto)
    t = re.sub(r'\bCAEP\b', 'SYNVIA', t, flags=re.IGNORECASE)
    t = re.sub(r'\bCUNHA\b', 'GRALAB', t, flags=re.IGNORECASE)
    return t


@st.cache_data(ttl=60)
def checar_chamados_pendentes(_planilha):
    if not _planilha:
        return 0
    try:
        aba = _planilha.worksheet("Base_Chamados")
        dados = aba.get_all_values()
        if len(dados) > 1:
            df = pd.DataFrame(dados[1:], columns=dados[0])
            return len(df[df['STATUS'].str.contains(
                'ANÁLISE', case=False, na=False)])
    except BaseException:
        pass
    return 0


@st.cache_data(ttl=20)
def carregar_dados_agentes(_planilha):
    if not _planilha:
        return pd.DataFrame()
    try:
        aba = _planilha.worksheet("Agentes")
        dados = aba.get_all_values()
        if len(dados) > 1:
            df_ag = pd.DataFrame(dados[1:], columns=dados[0])
            if 'TIPO_DISPARO_WHATSAPP' not in df_ag.columns:
                df_ag['TIPO_DISPARO_WHATSAPP'] = df_ag['LOGIN DO AGENTE'].apply(obter_modo_disparo_whatsapp_legacy)
            else:
                df_ag['TIPO_DISPARO_WHATSAPP'] = df_ag['TIPO_DISPARO_WHATSAPP'].apply(normalizar_modo_disparo_whatsapp)
            return df_ag
    except Exception:
        pass
    return pd.DataFrame(
        columns=[
            "ROTA MAPEADA",
            "LOGIN DO AGENTE",
            "NOME DO AGENTE",
            "TELEFONE",
            "TIPO_DISPARO_WHATSAPP"])


# 🔥 TTL Aumentado de 20s para 10 min (600s). Evita Erro 429! 🔥
@st.cache_data(ttl=600, show_spinner=False)
def carregar_dados_completos(_planilha):
    if not _planilha:
        return pd.DataFrame()
    try:
        aba_m = _planilha.worksheet("Memoria_Sistema")
        dados_m = aba_m.get_all_values()
        if len(dados_m) > 1:
            df = pd.DataFrame(dados_m[1:], columns=dados_m[0])
            df.columns = df.columns.str.strip().str.upper()
            df = df.loc[:, ~df.columns.duplicated()].dropna(how='all')

            if 'ZAP_ENVIADO' not in df.columns:
                df['ZAP_ENVIADO'] = ""
            if 'CNPJ' not in df.columns:
                df['CNPJ'] = ""

            if 'TOMADOR' in df.columns:
                df['TOMADOR'] = df['TOMADOR'].str.replace(
                    'CAEP', 'SYNVIA').str.replace(
                    'CUNHA', 'GRALAB')
            if 'CIDADE' in df.columns:
                df['CIDADE'] = df['CIDADE'].str.replace(
                    'Brodosqui', 'Brodowski', case=False).str.replace(
                    'BRODOSQUI', 'BRODOWSKI')
                # 🔥 CORREÇÃO PARA CIDADES PROBLEMÁTICAS (FUZZY MATCHING FALSO POSITIVO) 🔥
                # "Santo Antonio de Posse" é em MG, mas "São Sebastião do Passe" é em BA
                df['CIDADE'] = df['CIDADE'].str.replace(
                    'Santo Antonio de Posse', 'São Sebastião do Passe', case=False)

            try:
                aba_app = _planilha.worksheet("App_Tarefas")
                dados_app = aba_app.get_all_values()
                if len(dados_app) > 1:
                    df_app = pd.DataFrame(dados_app[1:], columns=dados_app[0])
                    cols_limpas = [
                        str(c).upper().strip().replace(
                            '?', '').replace(
                            ' ', '') for c in df_app.columns]
                    df_app.columns = cols_limpas

                    cols_to_extract = ['PEDIDO', 'STATUS', 'OBSERVACOES']
                    if 'FOTO' in df_app.columns:
                        cols_to_extract.append('FOTO')
                    if 'DATA_ENTREGA' in df_app.columns:
                        cols_to_extract.append('DATA_ENTREGA')

                    col_qr_app = next(
                        (c for c in [
                            'QR_CODE',
                            'QRCODE',
                            'QR',
                            'CODIGO'] if c in df_app.columns),
                        None)
                    if col_qr_app:
                        cols_to_extract.append(col_qr_app)

                    # Captura a coluna de hora do AppSheet
                    col_hora = next((c for c in ['HORA_STATUS', 'HORASTATUS', 'HORA'] if c in df_app.columns), None)
                    if col_hora:
                        cols_to_extract.append(col_hora)

                    col_nome = None
                    for c in [
                        'DETALHES',
                        'RECEBEDOR',
                        'CONTATO',
                        'NOME',
                        'PESSOA',
                            'INFORMANTE']:
                        if c in df_app.columns:
                            cols_to_extract.append(c)
                            col_nome = c
                            break

                    df_app_clean = df_app[[
                        c for c in cols_to_extract if c in df_app.columns]].copy()
                    rename_map = {
                        'STATUS': 'APP_STATUS',
                        'OBSERVACOES': 'APP_OBS',
                        'FOTO': 'APP_FOTO'}
                    if 'DATA_ENTREGA' in df_app.columns:
                        rename_map['DATA_ENTREGA'] = 'APP_DATA_ENTREGA'
                    if col_qr_app:
                        rename_map[col_qr_app] = 'APP_QR'
                    if col_nome:
                        rename_map[col_nome] = 'A_CONTATO'
                    # Mantém o mapeamento da hora para o pop-up
                    if col_hora:
                        rename_map[col_hora] = 'HORA_STATUS'

                    df_app_clean.rename(columns=rename_map, inplace=True)
                    df_app_clean['PEDIDO'] = df_app_clean['PEDIDO'].astype(
                        str).str.strip()
                    df_app_clean.drop_duplicates(
                        subset=['PEDIDO'], keep='last', inplace=True)

                    rom_mask = df_app_clean['PEDIDO'].str.startswith(
                        'ROM-', na=False)
                    rom_dict = df_app_clean[rom_mask].set_index(
                        'PEDIDO').to_dict('index')

                    df['PEDIDO'] = df['PEDIDO'].astype(str).str.strip()
                    df = pd.merge(df, df_app_clean, on='PEDIDO', how='left')

                    if 'APP_QR' in df.columns:
                        if 'QR_CODE' not in df.columns:
                            df['QR_CODE'] = df['APP_QR']
                        else:
                            df['QR_CODE'] = df.apply(
                                lambda r: r['APP_QR'] if str(
                                    r.get(
                                        'APP_QR',
                                        '')).strip() and str(
                                    r.get(
                                        'APP_QR',
                                        '')).upper() != 'NAN' else r.get(
                                    'QR_CODE',
                                    ''),
                                axis=1)

                    def get_true_status(row):
                        s_db = str(row.get('STATUS', '')).strip().upper()
                        s_app = str(row.get('APP_STATUS', '')).strip().upper()
                        rom_id = str(row.get('ROMANEIO', '')).strip()
                        if rom_id in rom_dict:
                            s_rom = str(
                                rom_dict[rom_id].get(
                                    'APP_STATUS',
                                    '')).strip().upper()
                            if s_rom in [
                                'ENTREGUE',
                                'FRUSTRADA',
                                'PROBLEMA',
                                    'CANCELADO']:
                                return s_rom
                        if s_db in [
                            'ENTREGUE',
                            'CANCELADO',
                            'FRUSTRADA',
                                'PROBLEMA']:
                            return s_db
                        if s_app in [
                            'ENTREGUE',
                            'CANCELADO',
                            'FRUSTRADA',
                                'PROBLEMA']:
                            return s_app
                        if s_db in [
                            'EM ROTA DE ENTREGA',
                            'CONFERIDO',
                                'COLETADO']:
                            return s_db
                        if s_app == 'COLETADO':
                            return s_app
                        if s_app and s_app != 'NAN':
                            return s_app
                        return s_db

                    df['STATUS_DB_ORIGINAL'] = df['STATUS'].copy()
                    df['STATUS'] = df.apply(get_true_status, axis=1)

                    def get_true_data_entrega(row):
                        d_db = str(row.get('DATA_ENTREGA', '')).strip()
                        s_final = str(row.get('STATUS', '')).strip().upper()
                        rom_id = str(row.get('ROMANEIO', '')).strip()
                        if rom_id in rom_dict:
                            d_rom = str(
                                rom_dict[rom_id].get(
                                    'APP_DATA_ENTREGA', '')).strip()
                            if d_rom and d_rom.upper() != 'NAN':
                                return d_rom
                        if s_final in [
                            'ENTREGUE',
                            'FRUSTRADA',
                                'PROBLEMA'] and 'APP_DATA_ENTREGA' in row:
                            d_app = str(
                                row.get(
                                    'APP_DATA_ENTREGA',
                                    '')).strip()
                            if d_app and d_app.upper() != 'NAN':
                                return d_app
                        return d_db if d_db.upper() != 'NAN' else ""

                    if 'DATA_ENTREGA' in df.columns or 'APP_DATA_ENTREGA' in df.columns:
                        df['DATA_ENTREGA'] = df.apply(
                            get_true_data_entrega, axis=1)

                    def get_true_foto(row):
                        f_db = str(row.get('FOTO', '')).strip()
                        f_app = str(row.get('APP_FOTO', '')).strip()
                                
                        # 1º PRIORIDADE: Foto da COLETA (atrelada diretamente ao número do PEDIDO no App)
                        if f_app and f_app.upper() != 'NAN':
                            return f_app
                                    
                        # 2º PRIORIDADE: Foto original da base (Memoria_Sistema)
                        if f_db and f_db.upper() != 'NAN':
                            return f_db
                                    
                        # 3º PRIORIDADE (Último Caso): Foto da ENTREGA (atrelada ao ROMANEIO)
                        rom_id = str(row.get('ROMANEIO', '')).strip()
                        if rom_id in rom_dict:
                            f_rom = str(rom_dict[rom_id].get('APP_FOTO', '')).strip()
                            if f_rom and f_rom.upper() != 'NAN':
                                return f_rom
                                        
                        return ""

                    if 'APP_FOTO' in df.columns or len(rom_dict) > 0:
                        df['FOTO'] = df.apply(get_true_foto, axis=1)
            except Exception:
                pass

            if 'DATA' in df.columns:
                df['DATA_OBJ'] = pd.to_datetime(
                    df['DATA'], format='%d/%m/%Y', errors='coerce').dt.date
            return df
    except Exception as e:
        st.error(f"Erro Crítico ao carregar a Memoria_Sistema: {e}")
    return pd.DataFrame()


DF_AGENTES = carregar_dados_agentes(planilha_db)
FERIADOS_BR = holidays.Brazil()
hoje_br = datetime.now(FUSO_BR).date()


def padronizar_texto(texto):
    if pd.isna(texto) or not texto:
        return ""
    return unicodedata.normalize(
        'NFKD', str(texto).strip()).encode(
        'ASCII', 'ignore').decode('utf-8').upper()


SINONIMOS_BAIRRO_GERAL = {
    'JD': 'JARDIM',
    'JADIM': 'JARDIM',
    'JARDIM': 'JARDIM',
    'PQ': 'PARQUE',
    'PARQ': 'PARQUE',
    'PARQUE': 'PARQUE',
    'VL': 'VILA',
    'VILA': 'VILA',
    'STA': 'SANTA',
    'SANTA': 'SANTA',
    'STO': 'SANTO',
    'SANTO': 'SANTO',
    'CH': 'CHACARA',
    'CHA': 'CHACARA',
    'CHACARA': 'CHACARA',
}

# Estrutura pronta para excecoes por cliente/regiao.
# Exemplo de uso futuro:
# SINONIMOS_BAIRRO_POR_TOMADOR['CLIENTE X'] = {'STA': 'SITIO', 'CH': 'CHACARA'}
SINONIMOS_BAIRRO_POR_TOMADOR = {
    '__DEFAULT__': {},
}


def normalizar_bairro_whatsapp(bairro, tomador=""):
    """Unifica abreviacoes comuns de bairro e permite regras extras por tomador."""
    bairro_norm = padronizar_texto(bairro)
    if not bairro_norm:
        return ""

    bairro_norm = re.sub(r'\s+', ' ', bairro_norm).strip()
    tomador_norm = padronizar_texto(tomador)

    mapa_sinonimos = dict(SINONIMOS_BAIRRO_GERAL)
    if tomador_norm and tomador_norm in SINONIMOS_BAIRRO_POR_TOMADOR:
        mapa_sinonimos.update(SINONIMOS_BAIRRO_POR_TOMADOR[tomador_norm])
    if '__DEFAULT__' in SINONIMOS_BAIRRO_POR_TOMADOR:
        mapa_sinonimos.update(SINONIMOS_BAIRRO_POR_TOMADOR['__DEFAULT__'])

    for alias, canonico in mapa_sinonimos.items():
        bairro_norm = re.sub(
            rf'^(?:{re.escape(alias)})\.?\s+',
            f'{canonico} ',
            bairro_norm,
        )
        if bairro_norm == alias:
            bairro_norm = canonico

    return re.sub(r'\s+', ' ', bairro_norm).strip()


def ordenar_grupo_por_bairro(df_grupo):
    """Ordena bairros alfabeticamente com estabilidade, mantendo a ordem dos pedidos dentro do mesmo bairro."""
    if df_grupo is None or df_grupo.empty:
        return df_grupo

    df_ordenado = df_grupo.copy()
    if '_BAIRRO_WHATS' in df_ordenado.columns:
        df_ordenado['_BAIRRO_ORD'] = df_ordenado['_BAIRRO_WHATS'].apply(normalizar_bairro_whatsapp)
    elif 'TOMADOR' in df_ordenado.columns and 'BAIRRO' in df_ordenado.columns:
        df_ordenado['_BAIRRO_ORD'] = df_ordenado.apply(
            lambda row: normalizar_bairro_whatsapp(row.get('BAIRRO', ''), row.get('TOMADOR', '')),
            axis=1,
        )
    elif 'BAIRRO' in df_ordenado.columns:
        df_ordenado['_BAIRRO_ORD'] = df_ordenado['BAIRRO'].apply(normalizar_bairro_whatsapp)
    else:
        df_ordenado['_BAIRRO_ORD'] = ''
    df_ordenado['_BAIRRO_VAZIO'] = (df_ordenado['_BAIRRO_ORD'] == '')
    df_ordenado = df_ordenado.sort_values(
        by=['_BAIRRO_VAZIO', '_BAIRRO_ORD'],
        ascending=[True, True],
        kind='mergesort',
    )
    return df_ordenado.drop(columns=['_BAIRRO_ORD', '_BAIRRO_VAZIO'])


def corrigir_cidade_inteligente(cidade_suja, df_rotas):
    if pd.isna(cidade_suja) or not str(cidade_suja).strip() or df_rotas.empty:
        return padronizar_texto(cidade_suja)
    c_limpa = padronizar_texto(str(cidade_suja))
            
    # 🔥 MAPEAMENTO DE CIDADES PROBLEMÁTICAS (Evita Falsos Positivos) 🔥
    CIDADES_FIXAS = {
        'SAO SEBASTIAO DO PASSE': 'SAO SEBASTIAO DO PASSE',
        'SANTO ANTONIO DE POSSE': 'SANTO ANTONIO DE POSSE',
    }
            
    # Verifica mapeamento fixo primeiro
    if c_limpa in CIDADES_FIXAS:
        return CIDADES_FIXAS[c_limpa]
            
    cidades_conhecidas = []
    for rota in df_rotas['ROTA MAPEADA'].dropna():
        cid = str(rota).split('➔')[0].split('---')[0].strip().upper()
        if cid and cid not in cidades_conhecidas:
            cidades_conhecidas.append(cid)

    # 🔥 AUMENTADO CUTOFF DE 0.8 PARA 0.90 (Mais Rigoroso) 🔥
    correcoes = difflib.get_close_matches(
        c_limpa, cidades_conhecidas, n=1, cutoff=0.90)
    if correcoes:
        return correcoes[0]
    return c_limpa


SINONIMOS_CIDADE_GERAL = {
    'JUQUITIBA': 'JUQUITIBA',
    'JUQUITIBA SP': 'JUQUITIBA',
    'JUQUITIBA/SP': 'JUQUITIBA',
    'JUQUITIBA - SP': 'JUQUITIBA',
}


def normalizar_cidade_operacao(cidade, df_rotas=None):
    cidade_norm = padronizar_texto(cidade)
    if not cidade_norm:
        return ""

    cidade_norm = re.sub(r'\s+', ' ', cidade_norm).strip()
    cidade_norm = re.sub(r'\s*[-/]\s*[A-Z]{2}$', '', cidade_norm).strip()

    if cidade_norm in SINONIMOS_CIDADE_GERAL:
        return SINONIMOS_CIDADE_GERAL[cidade_norm]

    if df_rotas is not None and not df_rotas.empty:
        return corrigir_cidade_inteligente(cidade_norm, df_rotas)

    return cidade_norm


def despachar_para_appsheet(lista_pedidos_dicts):
    if planilha_db is None or not lista_pedidos_dicts:
        return False
    try:
        aba = planilha_db.worksheet("App_Tarefas")
        linhas = []
        for p in lista_pedidos_dicts:
            mot_raw = str(p.get('MOTORISTA', p.get('AGENTE_RAW', '')))
            mot_app = mot_raw.split('|')[0].strip()
            linhas.append(
                [
                    str(
                        uuid.uuid4())[
                        :8].upper(), str(
                        p.get(
                            'PEDIDO', '')), mot_app, "PENDENTE", str(
                            p.get(
                                'ENDERECO', '')), str(
                                    p.get(
                                        'NUMERO', '')), str(
                                            p.get(
                                                'BAIRRO', '')), str(
                                                    p.get(
                                                        'CIDADE', '')), str(
                                                            p.get(
                                                                'CEP', '')), "", str(
                                                                    p.get(
                                                                        'OBSERVACOES', '')), str(
                                                                            p.get(
                                                                                'LABORATORIO', '')), str(
                                                                                    p.get(
                                                                                        'TOMADOR', '')), str(
                                                                                            p.get(
                                                                                                'QR_CODE', '')), "", str(
                                                                                                    p.get(
                                                                                                        'ROMANEIO', '')), "", ""])
        aba.append_rows(linhas, value_input_option='USER_ENTERED')
        return True
    except Exception as e:
        st.error(f"🚨 ERRO APPSHEET: {e}")
        return False


def substituir_pedido_appsheet(lista_pedidos_dicts):
    if planilha_db is None or not lista_pedidos_dicts:
        return False
    try:
        aba = planilha_db.worksheet("App_Tarefas")
        dados = aba.get_all_values()
        if not dados:
            return False

        cabecalho = dados[0]
        linhas_atuais = dados[1:] if len(dados) > 1 else []

        def normalizar(chave):
            return str(chave).strip().upper().replace(" ", "").replace("?", "")

        cab_map = {normalizar(col): idx for idx, col in enumerate(cabecalho)}
        idx_pedido = cab_map.get("PEDIDO")
        if idx_pedido is None:
            return False

        pedidos_alvo = {
            str(p.get('PEDIDO', '')).strip() for p in lista_pedidos_dicts if str(p.get('PEDIDO', '')).strip()
        }
        if not pedidos_alvo:
            return False

        def padronizar_linha(linha):
            return list(linha) + [""] * (len(cabecalho) - len(linha))

        linhas_sem_alvo = []
        for linha in linhas_atuais:
            linha_pad = padronizar_linha(linha)
            if str(linha_pad[idx_pedido]).strip() not in pedidos_alvo:
                linhas_sem_alvo.append(linha_pad)

        novas_linhas = []
        for pedido_dict in lista_pedidos_dicts:
            pedido = str(pedido_dict.get('PEDIDO', '')).strip()
            if not pedido:
                continue

            mot_raw = str(pedido_dict.get('MOTORISTA', pedido_dict.get('AGENTE_RAW', '')))
            mot_app = mot_raw.split('|')[0].strip()

            linha_base = None
            for linha in linhas_atuais:
                linha_pad = padronizar_linha(linha)
                if str(linha_pad[idx_pedido]).strip() == pedido:
                    linha_base = linha_pad
                    break

            linha_final = linha_base[:] if linha_base else [""] * len(cabecalho)
            for chave, valor in pedido_dict.items():
                chave_norm = normalizar(chave)
                if chave_norm in cab_map:
                    linha_final[cab_map[chave_norm]] = str(valor)

            if "MOTORISTA" in cab_map:
                linha_final[cab_map["MOTORISTA"]] = mot_app
            elif "AGENTERAW" in cab_map:
                linha_final[cab_map["AGENTERAW"]] = mot_app

            linha_final[idx_pedido] = pedido
            novas_linhas.append(linha_final)

        aba.clear()
        aba.update("A1", [cabecalho] + linhas_sem_alvo + novas_linhas)
        return True
    except Exception as e:
        st.error(f"🚨 ERRO APPSHEET: {e}")
        return False


def enviar_whatsapp_zapi(telefone_destino, texto_mensagem):
    INSTANCIA = "3F14E62A63D2B28DC385B20DE66F3711"
    TOKEN = "2321563615C4242CB6031504"
    CLIENT_TOKEN = "Ffaa43dcff1e14f0e985c91e92b24ed89S"
    tel_limpo = re.sub(r'\D', '', str(telefone_destino))
    if not tel_limpo.startswith('55') and len(tel_limpo) in [10, 11]:
        tel_limpo = '55' + tel_limpo
    url = f"https://api.z-api.io/instances/{INSTANCIA}/token/{TOKEN}/send-text"
    payload = {"phone": tel_limpo, "message": texto_mensagem}
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Client-Token": CLIENT_TOKEN}
    try:
        response = requests.post(url, json=payload, headers=headers)
        return response.status_code in [200, 201]
    except Exception:
        return False


def enviar_pdf_zapi(telefone_destino, pdf_bytes, nome_arquivo):
    INSTANCIA = "3F14E62A63D2B28DC385B20DE66F3711"
    TOKEN = "2321563615C4242CB6031504"
    CLIENT_TOKEN = "Ffaa43dcff1e14f0e985c91e92b24ed89S"
    tel_limpo = re.sub(r'\D', '', str(telefone_destino))
    if not tel_limpo.startswith('55') and len(tel_limpo) in [10, 11]:
        tel_limpo = '55' + tel_limpo
    url = f"https://api.z-api.io/instances/{INSTANCIA}/token/{TOKEN}/send-document/pdf"
    b64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
    payload = {
        "phone": tel_limpo,
        "document": f"data:application/pdf;base64,{b64_pdf}",
        "fileName": nome_arquivo}
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Client-Token": CLIENT_TOKEN}
    try:
        response = requests.post(url, json=payload, headers=headers)
        return response.status_code in [200, 201]
    except Exception:
        return False


def enviar_excel_zapi(telefone_destino, xls_bytes, nome_arquivo):
    INSTANCIA = "3F14E62A63D2B28DC385B20DE66F3711"
    TOKEN = "2321563615C4242CB6031504"
    CLIENT_TOKEN = "Ffaa43dcff1e14f0e985c91e92b24ed89S"
    tel_limpo = re.sub(r'\D', '', str(telefone_destino))
    if not tel_limpo.startswith('55') and len(tel_limpo) in [10, 11]:
        tel_limpo = '55' + tel_limpo
    url = f"https://api.z-api.io/instances/{INSTANCIA}/token/{TOKEN}/send-document/xlsx"
    b64_xls = base64.b64encode(xls_bytes).decode('utf-8')
    payload = {
        "phone": tel_limpo,
        "document": f"data:application/octet-stream;base64,{b64_xls}",
        "fileName": nome_arquivo}
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Client-Token": CLIENT_TOKEN}
    try:
        response = requests.post(url, json=payload, headers=headers)
        return response.status_code in [200, 201]
    except Exception:
        return False


def enviar_gif_zapi(telefone_destino, gif_url, legenda=""):
    """Tenta enviar GIF por URL na Z-API com fallback entre endpoints de video e imagem."""
    INSTANCIA = "3F14E62A63D2B28DC385B20DE66F3711"
    TOKEN = "2321563615C4242CB6031504"
    CLIENT_TOKEN = "Ffaa43dcff1e14f0e985c91e92b24ed89S"

    tel_limpo = re.sub(r'\D', '', str(telefone_destino))
    if not tel_limpo.startswith('55') and len(tel_limpo) in [10, 11]:
        tel_limpo = '55' + tel_limpo

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Client-Token": CLIENT_TOKEN,
    }

    tentativas = [
        (
            f"https://api.z-api.io/instances/{INSTANCIA}/token/{TOKEN}/send-video",
            {"phone": tel_limpo, "video": gif_url, "caption": legenda},
        ),
        (
            f"https://api.z-api.io/instances/{INSTANCIA}/token/{TOKEN}/send-image",
            {"phone": tel_limpo, "image": gif_url, "caption": legenda},
        ),
    ]

    for url, payload in tentativas:
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            if response.status_code in [200, 201]:
                return True
        except Exception:
            continue

    return False


def obter_proximo_id(df, minimo_inicial=1000):
    minimo_inicial = max(1, int(minimo_inicial))
    if df is None or df.empty or 'PEDIDO' not in df.columns:
        return minimo_inicial
    try:
        nums = df['PEDIDO'].astype(str).str.extract(
            r'^(\d+)')[0].dropna().astype(int)
        if nums.empty:
            return minimo_inicial
        return max(int(nums.max() + 1), minimo_inicial)
    except BaseException:
        return minimo_inicial


@st.cache_data(ttl=300)
def carregar_mapa_sla_tarifas(tomador):
    if planilha_financeiro is None:
        return {}

    tomador_norm = str(tomador).strip().upper()
    if not tomador_norm:
        return {}

    try:
        buscado = tomador_norm.replace('CAEP', 'SYNVIA').replace('CUNHA', 'GRALAB')
        todas_abas = planilha_financeiro.worksheets()
        mapa_abas = {aba.title.strip().upper(): aba for aba in todas_abas}

        if buscado not in mapa_abas:
            return {}

        dados = mapa_abas[buscado].get_all_values()
        if len(dados) <= 1:
            return {}

        df_prazos = pd.DataFrame(dados[1:], columns=dados[0])
        if 'CIDADE' not in df_prazos.columns or 'PRAZO_DIAS_UTEIS' not in df_prazos.columns:
            return {}

        df_prazos['CIDADE'] = df_prazos['CIDADE'].apply(padronizar_texto)
        df_prazos['PRAZO_DIAS_UTEIS'] = pd.to_numeric(df_prazos['PRAZO_DIAS_UTEIS'], errors='coerce')
        df_prazos = df_prazos.dropna(subset=['PRAZO_DIAS_UTEIS'])
        df_prazos = df_prazos[df_prazos['PRAZO_DIAS_UTEIS'] > 0]
        if df_prazos.empty:
            return {}

        # Mantem apenas um prazo por cidade (primeira ocorrencia valida).
        df_prazos = df_prazos.drop_duplicates(subset=['CIDADE'], keep='first')
        return {
            str(r['CIDADE']): int(r['PRAZO_DIAS_UTEIS'])
            for _, r in df_prazos.iterrows()
            if str(r.get('CIDADE', '')).strip()
        }
    except Exception:
        return {}


def obter_prazo_sla_tabela(tomador, cidade):
    tomador_norm = str(tomador).strip().upper()
    cidade_norm = padronizar_texto(cidade)
    if not tomador_norm or not cidade_norm:
        return None

    mapa_sla = carregar_mapa_sla_tarifas(tomador_norm)
    prazo = mapa_sla.get(cidade_norm)
    return int(prazo) if prazo else None


def calcular_sla_dias(uf, cidade, tomador=""):
    uf, cidade = str(uf).upper().strip(), padronizar_texto(cidade)
    tomador = str(tomador).upper().strip()

    prazo_tabela = obter_prazo_sla_tabela(tomador, cidade)
    if prazo_tabela:
        return prazo_tabela

    if "SOUZA CRUZ" in tomador:
        if uf == 'SP' or cidade == 'DUQUE DE CAXIAS':
            return 3
        return 5

    if uf == 'SP':
        return 1
    if uf == 'RJ':
        return 2 if cidade in [
            'ANGRA DOS REIS',
            'CAMPOS DOS GOYTACAZES'] else 1
    return 2 if uf in ['GO', 'DF', 'SC', 'RS'] else 3


def calcular_data_limite(data_ini, prazo):
    try:
        dt = pd.to_datetime(data_ini, format="%d/%m/%Y")
        add = 0
        while add < prazo:
            dt += timedelta(days=1)
            if dt.weekday() < 5 and dt not in FERIADOS_BR:
                add += 1
        return dt.strftime("%d/%m/%Y")
    except BaseException:
        return data_ini


def calc_status_display(row):
    status_final = str(row.get('STATUS', '')).strip().upper()
    previsao = str(row.get('DATA_LIMITE', '')).strip()
    res = '⏳ Pendente'

    if 'ENTREGUE' in status_final:
        res = '✅ Entregue'
    elif 'COLETADO' in status_final:
        res = '📦 Coletado'
    elif 'ROTA DE COLETA' in status_final:
        res = '🚐 Rota de Coleta'
    elif 'ROTA' in status_final:
        res = '🚚 Em Rota de Entrega'
    elif 'CONFERIDO' in status_final:
        res = '☑️ Conferido'
    elif 'FRUSTRADA' in status_final:
        res = '❌ Frustrada'
    elif 'CANCELADO' in status_final:
        res = '🚫 Cancelado'
    elif 'PROBLEMA' in status_final:
        res = '🚨 Problema'

    if '✅' not in res and '🚫' not in res and '❌' not in res and previsao:
        try:
            if datetime.strptime(previsao, "%d/%m/%Y").date() < hoje_br:
                res = f"{res} ⚠️ ATRASADO"
        except BaseException:
            pass
    return res
# =============================================================================
# 🪟 FUNÇÃO DO POP-UP DE DETALHES (MEGAZORD CCO)
# =============================================================================


@st.dialog("📋 Detalhes da Operação", width="large")
def modal_detalhes_pedido(pedido_data):
    status = str(pedido_data.get('STATUS_DISPLAY', '')).upper()
    cor_etiqueta = "#10B981" if "ENTREGUE" in status else "#F59E0B"
    if any(
        x in status for x in [
            "FRUSTRADA",
            "PROBLEMA",
            "CANCELADO",
            "ATRASADO",
            "RECUSA"]):
        cor_etiqueta = "#EF4444"
    if "COLETADO" in status or "ROTA" in status:
        cor_etiqueta = "#3B82F6"

    c_h1, c_h2 = st.columns([3, 1])
    c_h1.subheader(f"Pedido: {pedido_data.get('PEDIDO', 'N/A')}")
    c_h2.markdown(
        f"<div style='text-align:center; background:{cor_etiqueta}; color:white; padding:8px; border-radius:10px; font-weight:bold; font-size:12px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>{status}</div>",
        unsafe_allow_html=True)

    step = 1
    cor_barra = "#3b82f6"
    if any(
        x in status for x in [
            "FRUSTRADA",
            "PROBLEMA",
            "CANCELADO",
            "RECUSA"]):
        cor_barra = "#ef4444"
        if "ROTA DE COLETA" in status or "COLETADO" in status:
            step = 2
    else:
        if "ROTA DE COLETA" in status:
            step = 2
        elif "COLETADO" in status or "ROTA DE ENTREGA" in status or "EM ROTA" in status or "CONFERIDO" in status:
            step = 3
        elif "ENTREGUE" in status:
            step = 4
            cor_barra = "#10b981"

    html_barra = (
        f"<div style='display:flex;justify-content:space-between;position:relative;margin:15px 0 35px 0;'>"
        f"<div style='position:absolute;top:12px;left:0;right:0;height:4px;background:#e2e8f0;z-index:1;'></div>"
        f"<div style='position:absolute;top:12px;left:0;width:{(step - 1) * 33.3}%;height:4px;background:{cor_barra};z-index:2;transition:width 0.5s;'></div>"
        f"<div style='z-index:3;text-align:center;width:60px;'><div style='width:28px;height:28px;background:{cor_barra if step >= 1 else '#e2e8f0'};color:white;border-radius:50%;line-height:28px;margin:0 auto;font-size:14px;box-shadow:0 2px 4px rgba(0,0,0,0.1);'>✓</div><div style='font-size:11px;margin-top:5px;font-weight:600;color:{'#0f172a' if step >= 1 else '#64748b'};'>Pedido</div></div>"
        f"<div style='z-index:3;text-align:center;width:60px;'><div style='width:28px;height:28px;background:{cor_barra if step >= 2 else '#e2e8f0'};color:white;border-radius:50%;line-height:28px;margin:0 auto;font-size:14px;box-shadow:0 2px 4px rgba(0,0,0,0.1);'>{'!' if step == 2 and cor_barra == '#ef4444' else '🚐'}</div><div style='font-size:11px;margin-top:5px;font-weight:600;color:{'#0f172a' if step >= 2 else '#64748b'};'>Em Rota</div></div>"
        f"<div style='z-index:3;text-align:center;width:60px;'><div style='width:28px;height:28px;background:{cor_barra if step >= 3 else '#e2e8f0'};color:white;border-radius:50%;line-height:28px;margin:0 auto;font-size:14px;box-shadow:0 2px 4px rgba(0,0,0,0.1);'>📦</div><div style='font-size:11px;margin-top:5px;font-weight:600;color:{'#0f172a' if step >= 3 else '#64748b'};'>Coletado</div></div>"
        f"<div style='z-index:3;text-align:center;width:60px;'><div style='width:28px;height:28px;background:{cor_barra if step >= 4 else '#e2e8f0'};color:white;border-radius:50%;line-height:28px;margin:0 auto;font-size:14px;box-shadow:0 2px 4px rgba(0,0,0,0.1);'>✅</div><div style='font-size:11px;margin-top:5px;font-weight:600;color:{'#0f172a' if step >= 4 else '#64748b'};'>Entregue</div></div>"
        f"</div>"
    )
    st.markdown(html_barra, unsafe_allow_html=True)

    endereco_completo = f"{
        pedido_data.get(
            'ENDERECO', '')}, nº {
        pedido_data.get(
            'NUMERO', '')}, {
        pedido_data.get(
            'BAIRRO', '')} — {
        pedido_data.get(
            'CIDADE', '')}/{
        pedido_data.get(
            'UF', '')}"
    agente_nome = str(
        pedido_data.get(
            'AGENTE_RAW',
            'Equipe IGO')).split('|')[0].upper()

    c1, c2 = st.columns(2)
    with c1:
        html_c1 = (
            f"<div style='background:#f8fafc;padding:16px;border-radius:12px;border:1px solid #e2e8f0;height:100%;'>"
            f"<p style='margin:0;font-size:11px;font-weight:700;color:#64748b;text-transform:uppercase;'>🏢 Tomador / Ponto de Coleta</p>"
            f"<p style='margin:2px 0 12px 0;font-size:15px;font-weight:700;color:#0f172a;'>{pedido_data.get('TOMADOR', '')} <br><span style='font-size:13px; font-weight:500; color:#475569;'>{pedido_data.get('LABORATORIO', 'N/A')}</span></p>"
            f"<p style='margin:0;font-size:11px;font-weight:700;color:#64748b;text-transform:uppercase;'>📍 Endereço Completo</p>"
            f"<p style='margin:2px 0 12px 0;font-size:13px;color:#334155;'>{endereco_completo}</p>"
            f"<p style='margin:0;font-size:11px;font-weight:700;color:#64748b;text-transform:uppercase;'>👤 Motorista da Operação</p>"
            f"<p style='margin:2px 0 12px 0;font-size:14px;font-weight:700;color:#3b82f6;'>🚐 {agente_nome}</p>"
            f"</div>"
        )
        st.markdown(html_c1, unsafe_allow_html=True)

    with c2:
        data_efetiva = str(pedido_data.get('DATA_ENTREGA', '---')).strip()
        data_limite = str(pedido_data.get('DATA_LIMITE', '---')).strip()

        # Extrai a hora do registro HORA_STATUS, caso ele exista. (Exemplo de retorno bruto: '11/06/2026 12:35:01')
        hora_status_raw = str(pedido_data.get('HORA_STATUS', '')).strip()
        # Quebra na primeira ocorrência de espaço e pega os primeiros 5 dígitos da parte de hora, deixando só o "HH:MM"
        hora_formatada = hora_status_raw.split(' ')[1][:5] if ' ' in hora_status_raw else '---'

        html_c2 = (
            f"<div style='background:#f8fafc;padding:16px;border-radius:12px;border:1px solid #e2e8f0;height:100%;'>"
            f"<p style='margin:0;font-size:11px;font-weight:700;color:#64748b;text-transform:uppercase;'>📅 Solicitação Criada Em</p>"
            f"<p style='margin:2px 0 12px 0;font-size:14px;color:#334155;'>{pedido_data.get('DATA', '---')}</p>"
            f"<p style='margin:0;font-size:11px;font-weight:700;color:#64748b;text-transform:uppercase;'>🕒 Detalhes da Baixa</p>"
            f"<p style='margin:2px 0 4px 0;font-size:14px;color:#334155;'>⏱️ Horário (App): <b>{hora_formatada}</b></p>"
            f"<p style='margin:0 0 12px 0;font-size:14px;color:#334155;'>✅ Data Efetiva: <b>{data_efetiva if data_efetiva else 'Pendente'}</b></p>"
            f"<p style='margin:0;font-size:11px;font-weight:700;color:#64748b;text-transform:uppercase;'>🏁 Prazo Acordado</p>"
            f"<p style='margin:2px 0 0 0;font-size:13px;color:#334155;'>🎯 Previsão Limite: {data_limite}</p>"
            f"</div>"
        )
        st.markdown(html_c2, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.info(
        f"**💬 Atualizações e Observações do Agente:**\n\n{
            pedido_data.get(
                'DETALHES',
                'Nenhuma observação.')}")

    foto = pedido_data.get('FOTO_URL', '')
    if foto and str(foto).startswith("http"):
        st.markdown("#### 📸 Comprovante de Campo")
        f1, f2, f3 = st.columns([1, 2, 1])
        with f2:
            st.image(foto, use_container_width=True)

    if st.button("Fechar Detalhes", use_container_width=True):
        st.session_state.modal_aberto = False
        st.session_state.pedido_modal = None
        st.rerun()


def tratar_texto_global(texto):
    if pd.isna(texto):
        return ""
    t = padronizar_texto(texto)
    return t[:-2] if t.endswith('.0') else t


def limpar_nome_local_rota(texto):
    return tratar_texto_global(texto).split('/')[0].split('-')[0].strip()


def obter_login_agente(
        cidade,
        bairro,
        laboratorio,
        endereco="",
        base_rotas_df=pd.DataFrame()):
    if base_rotas_df.empty:
        return ""
    rotas_dict = {padronizar_texto(str(row['ROTA MAPEADA']).upper().replace(" ➔ ", "---").replace(
        " -> ", "---")): str(row['LOGIN DO AGENTE']).lower().strip() for _, row in base_rotas_df.iterrows()}
    cid = limpar_nome_local_rota(cidade)
    bai = limpar_nome_local_rota(bairro)
    lab = tratar_texto_global(laboratorio)
    end = tratar_texto_global(endereco)

    for c in [
            f"{cid}---{bai}---{end}",
            f"{cid}---{bai}---{lab}",
            f"{cid}---{lab}",
            f"{cid}---{bai}",
            cid]:
        if c in rotas_dict:
            return rotas_dict[c]
    return ""


def gerar_excel_memoria(df):
    output = io.BytesIO()
    df_rep = df.copy()
    for col in df_rep.columns:
        if df_rep[col].dtype == object:
            df_rep[col] = df_rep[col].apply(
                lambda x: corrigir_nomes_relatorio(x) if isinstance(
                    x, str) else x)

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_rep.to_excel(writer, sheet_name='Relatorio', index=False)
        worksheet = writer.sheets['Relatorio']
        worksheet.hide_gridlines(2)
        if df_rep.shape[0] > 0:
            worksheet.add_table(0,
                                0,
                                df_rep.shape[0],
                                df_rep.shape[1] - 1,
                                {'columns': [{'header': str(col)} for col in df_rep.columns],
                                    'style': 'Table Style Medium 2'})
            for i, col in enumerate(df_rep.columns):
                tam_max_coluna = df_rep[col].map(lambda v: len(str(v)) if pd.notna(v) else 0).max()
                worksheet.set_column(i, i, min(
                    max(tam_max_coluna, len(str(col))) + 2, 40))
    return output.getvalue()


def gerar_excel_rota_whatsapp(df_agente):
    output = io.BytesIO()
    df_xls = df_agente.copy()

    for col in df_xls.columns:
        if df_xls[col].dtype == object:
            df_xls[col] = df_xls[col].apply(
                lambda x: corrigir_nomes_relatorio(x) if isinstance(
                    x, str) else x)

    cols_desejadas = [
        'PEDIDO',
        'LABORATORIO',
        'ENDERECO',
        'NUMERO',
        'BAIRRO',
        'CEP',
        'TOMADOR',
        'OBSERVACOES']
    for c in cols_desejadas:
        if c not in df_xls.columns:
            df_xls[c] = ""

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        resumo = df_xls.groupby('CIDADE').size(
        ).reset_index(name='QTD_VOLUMES')
        resumo.loc[len(resumo)] = ['TOTAL GERAL', resumo['QTD_VOLUMES'].sum()]
        resumo.to_excel(writer, sheet_name='RESUMO_GERAL', index=False)
        worksheet_res = writer.sheets['RESUMO_GERAL']
        worksheet_res.hide_gridlines(2)
        worksheet_res.add_table(0, 0, len(resumo), 1, {'columns': [{'header': 'CIDADE'}, {
                                'header': 'QTD_VOLUMES'}], 'style': 'Table Style Medium 2'})
        worksheet_res.set_column('A:A', 30)
        worksheet_res.set_column('B:B', 15)

        for cidade, group in df_xls.groupby('CIDADE'):
            cid_limpa = re.sub(r'[^A-Za-z0-9 ]', '', str(cidade).strip())[:30]
            if not cid_limpa:
                cid_limpa = "Sem_Cidade"
            df_cid = group[cols_desejadas].copy()
            df_cid.to_excel(writer, sheet_name=cid_limpa, index=False)
            worksheet = writer.sheets[cid_limpa]
            worksheet.hide_gridlines(2)
            if len(df_cid) > 0:
                worksheet.add_table(0,
                                    0,
                                    len(df_cid),
                                    len(df_cid.columns) - 1,
                                    {'columns': [{'header': str(col)} for col in df_cid.columns],
                                        'style': 'Table Style Light 9'})
            worksheet.set_column('A:A', 15)
            worksheet.set_column('B:B', 40)
            worksheet.set_column('C:C', 40)
            worksheet.set_column('D:H', 20)
    return output.getvalue()


def gerar_pdf_rota_whatsapp(nome_motorista, data_str, df_agente):
    W_OK = 8
    W_PED = 16
    W_TOM = 22
    W_LAB = 28
    W_END = 54
    W_OBS = 62

    def _txt_pdf(valor, limite=120):
        texto = corrigir_nomes_relatorio(padronizar_texto(valor))
        texto = re.sub(r'\s+', ' ', texto).strip()
        return texto[:limite]

    def _texto_obs(valor):
        obs = str(valor).strip()
        if not obs or obs.upper() in ['NAN', 'NONE']:
            return ''
        obs = corrigir_nomes_relatorio(obs)
        obs = re.sub(r'\s+', ' ', obs).strip()
        obs = re.sub(r'^\[\s*COLETA\s*:\s*', '', obs, flags=re.IGNORECASE)
        obs = re.sub(r'\]\s*-\s*', ' | ', obs)
        obs = re.sub(r'\]$', '', obs).strip()
        return obs

    def _texto_obs_whatsapp(valor):
        obs = str(valor).strip()
        if not obs or obs.upper() in ['NAN', 'NONE']:
            return ''
        return re.sub(r'\s+', ' ', corrigir_nomes_relatorio(obs)).strip()

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()
    pdf.set_draw_color(15, 23, 42)
    pdf.set_line_width(0.3)
    pdf.rect(5, 5, 200, 287)

    try:
        logo_path = os.path.join(tempfile.gettempdir(), "igo_logo_temp.png")
        if not os.path.exists(logo_path):
            req = urllib.request.Request(
                "https://i.postimg.cc/x84nnjjq/IGO-LOGO.png",
                headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response, open(logo_path, 'wb') as out_file:
                out_file.write(response.read())
        pdf.image(logo_path, x=10, y=8, w=28)
    except Exception:
        pass

    df_pdf = df_agente.copy()
    colunas_base = ['PEDIDO', 'LABORATORIO', 'ENDERECO', 'NUMERO', 'BAIRRO', 'CIDADE', 'TOMADOR', 'OBSERVACOES']
    for col in colunas_base:
        if col not in df_pdf.columns:
            df_pdf[col] = ""

    if 'CIDADE' in df_pdf.columns:
        df_pdf['_CIDADE_PDF'] = df_pdf['CIDADE'].apply(lambda c: normalizar_cidade_operacao(c))
    else:
        df_pdf['_CIDADE_PDF'] = 'SEM CIDADE'
    if 'BAIRRO' in df_pdf.columns:
        df_pdf['_BAIRRO_PDF'] = df_pdf.apply(
            lambda row: normalizar_bairro_whatsapp(row.get('BAIRRO', ''), row.get('TOMADOR', '')),
            axis=1,
        )
    else:
        df_pdf['_BAIRRO_PDF'] = 'SEM BAIRRO'

    df_pdf['_CIDADE_PDF'] = df_pdf['_CIDADE_PDF'].replace('', 'SEM CIDADE')
    df_pdf['_BAIRRO_PDF'] = df_pdf['_BAIRRO_PDF'].replace('', 'SEM BAIRRO')
    df_pdf = df_pdf.sort_values(by=['_CIDADE_PDF', '_BAIRRO_PDF', 'PEDIDO'], kind='mergesort')

    total_volumes = len(df_pdf)
    total_cidades = int(df_pdf['_CIDADE_PDF'].nunique()) if not df_pdf.empty else 0
    total_bairros = int(df_pdf.groupby(['_CIDADE_PDF', '_BAIRRO_PDF']).ngroups) if not df_pdf.empty else 0
    total_tomadores = int(df_pdf['TOMADOR'].astype(str).str.strip().replace('', 'SEM TOMADOR').nunique()) if not df_pdf.empty else 0
    cidade_unica_lote = total_cidades == 1

    def _cabecalho_cidade(cidade_nome):
        if cidade_unica_lote:
            return
        pdf.set_fill_color(15, 23, 42)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", "B", 8)
        pdf.cell(0, 6, f"CIDADE: {cidade_nome}", 1, 1, "L", True)

    def _cabecalho_bairro(bairro_nome):

        pdf.set_fill_color(226, 232, 240)
        pdf.set_text_color(15, 23, 42)
        pdf.set_font("Arial", "B", 7)
        pdf.cell(0, 5, f"   BAIRRO: {bairro_nome}", 1, 1, "L", True)

        pdf.set_fill_color(241, 245, 249)
        pdf.set_text_color(71, 85, 105)
        pdf.set_font("Arial", "B", 6)
        pdf.cell(W_OK, 5, "OK", 1, 0, "C", True)
        pdf.cell(W_PED, 5, "PEDIDO", 1, 0, "C", True)
        pdf.cell(W_TOM, 5, "TOMADOR", 1, 0, "L", True)
        pdf.cell(W_LAB, 5, "LABORATORIO", 1, 0, "L", True)
        pdf.cell(W_END, 5, "ENDERECO", 1, 0, "L", True)
        pdf.cell(W_OBS, 5, "OBS", 1, 1, "C", True)

    def _nova_pagina_com_retorno(cidade_nome, bairro_nome):
        pdf.add_page()
        pdf.rect(5, 5, 200, 287)
        _cabecalho_cidade(cidade_nome)
        _cabecalho_bairro(bairro_nome)

    pdf.set_y(15)
    pdf.set_font("Arial", "B", 14)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 6, "ROTA OFICIAL DE OPERACAO - IGO LOGISTICA", ln=True, align="C")
    pdf.set_font("Arial", "B", 10)
    pdf.set_text_color(2, 132, 199)
    pdf.cell(0, 5, f"AGENTE: {_txt_pdf(nome_motorista, 50)}", ln=True, align="C")
    pdf.set_font("Arial", "", 8)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 4, f"Data da Rota: {data_str}", ln=True, align="C")
    pdf.cell(0, 4, f"Volumes: {total_volumes} | Cidades: {total_cidades} | Bairros: {total_bairros} | Tomadores: {total_tomadores}", ln=True, align="C")
    if cidade_unica_lote and not df_pdf.empty:
        pdf.cell(0, 4, f"Cidade da Rota: {_txt_pdf(df_pdf['_CIDADE_PDF'].iloc[0], 50)}", ln=True, align="C")

    y_base = pdf.get_y() + 3
    tile_w = 43
    gap = 2
    tiles = [
        ("PEDIDOS", str(total_volumes), (239, 246, 255), (15, 23, 42)),
        ("CIDADES", str(total_cidades), (240, 253, 244), (5, 150, 105)),
        ("BAIRROS", str(total_bairros), (255, 251, 235), (217, 119, 6)),
        ("TOMADORES", str(total_tomadores), (254, 242, 242), (185, 28, 28)),
    ]
    for idx, (titulo, valor, fill, txt_color) in enumerate(tiles):
        x = 10 + idx * (tile_w + gap)
        pdf.set_xy(x, y_base)
        pdf.set_fill_color(*fill)
        pdf.set_text_color(*txt_color)
        pdf.set_font("Arial", "B", 7)
        pdf.cell(tile_w, 5, titulo, 1, 1, "C", True)
        pdf.set_xy(x, y_base + 5)
        pdf.set_font("Arial", "B", 13)
        pdf.cell(tile_w, 9, valor, 1, 0, "C", True)

    pdf.ln(12)
    pdf.set_text_color(15, 23, 42)
    pdf.set_font("Arial", "B", 8)
    pdf.cell(0, 5, "CHECKLIST OPERACIONAL", ln=True)
    pdf.set_font("Arial", "", 6)
    pdf.set_text_color(71, 85, 105)
    pdf.multi_cell(
        0,
        3.5,
        "Conferir volumes, validar observacoes e assinalar cada item antes da saida. Itens em amarelo merecem revisao rapida.",
    )
    pdf.ln(1)

    grouped_cidade = df_pdf.groupby('_CIDADE_PDF', sort=False)
    for cidade, group_cid in grouped_cidade:
        cidade_nome = _txt_pdf(cidade, 40)
        _cabecalho_cidade(cidade_nome)
        grouped_bairro = group_cid.groupby('_BAIRRO_PDF', sort=False)
        for bairro, group_bai in grouped_bairro:
            bairro_nome = _txt_pdf(bairro, 42)
            _cabecalho_bairro(bairro_nome)
            pdf.set_text_color(51, 65, 85)
            pdf.set_font("Arial", "", 6)
            for idx_item, (_, row) in enumerate(group_bai.iterrows()):
                if pdf.get_y() > 272:
                    _nova_pagina_com_retorno(cidade_nome, bairro_nome)
                    pdf.set_text_color(51, 65, 85)
                    pdf.set_font("Arial", "", 6)

                ped = _txt_pdf(row.get('PEDIDO', ''), 18)
                tom = _txt_pdf(row.get('TOMADOR', ''), 22)
                lab = _txt_pdf(row.get('LABORATORIO', ''), 28)
                end = _txt_pdf(f"{row.get('ENDERECO', '')}, {row.get('NUMERO', '')}", 72)
                obs_bruto = row.get('OBSERVACOES', '')
                if (not str(obs_bruto).strip() or str(obs_bruto).strip().upper() in ['NAN', 'NONE']) and str(row.get('HORARIO', '')).strip():
                    obs_bruto = f"[COLETA: {str(row.get('HORARIO', '')).strip()}]"
                obs = _texto_obs(obs_bruto)

                fill_row = (248, 250, 252) if idx_item % 2 == 0 else (255, 255, 255)
                fill_obs = (254, 249, 195) if obs else fill_row

                pdf.set_fill_color(*fill_row)
                pdf.cell(W_OK, 5, "[ ]", 1, 0, "C", True)
                pdf.cell(W_PED, 5, ped, 1, 0, "C", True)
                pdf.cell(W_TOM, 5, tom, 1, 0, "L", True)
                pdf.cell(W_LAB, 5, lab, 1, 0, "L", True)
                pdf.cell(W_END, 5, end, 1, 0, "L", True)
                pdf.set_fill_color(*fill_obs)
                pdf.cell(W_OBS, 5, obs[:62] if obs else "", 1, 1, "L", True)

            pdf.ln(0.5)

    # ---- LINHA DO TEMPO DA ROTA ----
    paradas_tl = []
    for cidade_tl, g_cid_tl in df_pdf.groupby('_CIDADE_PDF', sort=False):
        for bairro_tl, g_bai_tl in g_cid_tl.groupby('_BAIRRO_PDF', sort=False):
            paradas_tl.append({
                'cidade': _txt_pdf(str(cidade_tl), 22),
                'bairro': _txt_pdf(str(bairro_tl), 22),
                'qtd': len(g_bai_tl),
            })

    # ~4km entre bairros da mesma cidade, ~25km entre cidades + 0.5km por volume (entregas no bairro)
    km_estimado = sum(
        4 if paradas_tl[i]['cidade'] == paradas_tl[i - 1]['cidade'] else 25
        for i in range(1, len(paradas_tl))
    ) + len(df_pdf) * 0.5

    pdf.add_page()
    pdf.rect(5, 5, 200, 287)
    pdf.set_xy(10, 10)
    pdf.set_font("Arial", "B", 11)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 7, "LINHA DO TEMPO DA ROTA", ln=True, align="C")
    pdf.set_font("Arial", "", 7)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 4, "Sequencia de paradas por bairro e cidade", ln=True, align="C")
    pdf.ln(4)

    _palette_tl = [
        (2, 132, 199), (5, 150, 105), (217, 119, 6),
        (185, 28, 28), (109, 40, 217), (3, 105, 161),
    ]
    _cores_tl = {}
    _idx_cor_tl = 0
    for _p in paradas_tl:
        if _p['cidade'] not in _cores_tl:
            _cores_tl[_p['cidade']] = _palette_tl[_idx_cor_tl % len(_palette_tl)]
            _idx_cor_tl += 1

    x_line_tl = 30
    x_text_tl = 36
    y_tl_start = pdf.get_y()
    n_paradas_tl = max(len(paradas_tl), 1)
    step_tl = min(9.0, (255.0 - y_tl_start) / n_paradas_tl)

    pdf.set_draw_color(210, 210, 210)
    pdf.set_line_width(0.4)
    pdf.line(x_line_tl, y_tl_start, x_line_tl, y_tl_start + step_tl * len(paradas_tl))

    for i_tl, parada_tl in enumerate(paradas_tl):
        r_tl, g_tl, b_tl = _cores_tl[parada_tl['cidade']]
        y_dot = y_tl_start + i_tl * step_tl

        pdf.set_fill_color(r_tl, g_tl, b_tl)
        pdf.set_draw_color(r_tl, g_tl, b_tl)
        pdf.ellipse(x_line_tl - 2, y_dot - 2, 4, 4, 'F')

        pdf.set_xy(10, y_dot - 2.5)
        pdf.set_font("Arial", "B", 6)
        pdf.set_text_color(120, 120, 120)
        pdf.cell(18, 5, f"PARADA {i_tl + 1:02d}", align="R")

        pdf.set_xy(x_text_tl, y_dot - 2.5)
        pdf.set_text_color(r_tl, g_tl, b_tl)
        pdf.set_font("Arial", "B", 7)
        if cidade_unica_lote:
            label_tl = parada_tl['bairro']
        else:
            label_tl = f"{parada_tl['cidade']}  >  {parada_tl['bairro']}"
        pdf.cell(120, 5, label_tl[:52])

        pdf.set_fill_color(r_tl, g_tl, b_tl)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", "B", 6)
        pdf.cell(22, 4, f"{parada_tl['qtd']} vol.", 0, 0, "C", True)

        if i_tl > 0:
            km_trecho = 4 if paradas_tl[i_tl]['cidade'] == paradas_tl[i_tl - 1]['cidade'] else 25
            pdf.set_xy(x_line_tl - 14, y_dot - step_tl / 2 - 1.5)
            pdf.set_font("Arial", "I", 5)
            pdf.set_text_color(160, 160, 160)
            pdf.cell(12, 3, f"~{km_trecho}km", align="C")

    y_box = y_tl_start + step_tl * len(paradas_tl) + 8
    pdf.set_xy(10, y_box)
    pdf.set_fill_color(239, 246, 255)
    pdf.set_draw_color(2, 132, 199)
    pdf.set_line_width(0.4)
    pdf.set_text_color(15, 23, 42)
    pdf.set_font("Arial", "B", 9)
    pdf.cell(0, 9, f"   ESTIMATIVA TOTAL DA ROTA:  ~{km_estimado:.0f} km", 1, 1, "L", True)
    pdf.set_xy(10, pdf.get_y())
    pdf.set_font("Arial", "I", 6)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 4, "   * Estimativa baseada em distancias medias por bairro/cidade (~4km entre bairros, ~25km entre cidades).", ln=True)
    pdf.ln(3)

    pdf.set_font("Arial", "I", 7)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 5, f"Relatorio gerado em {datetime.now(FUSO_BR).strftime('%d/%m/%Y %H:%M:%S')}", ln=True, align="R")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
        pdf.output(tmp_pdf.name)
        with open(tmp_pdf.name, "rb") as f:
            pdf_bytes = f.read()
    return pdf_bytes

# 🔥 FUNÇÃO PARA GERAR RELATÓRIO DE DISPARO UMOVE COM RASTREAMENTO 🔥


def gerar_relatorio_umove_xls(df_disparos, resultados_dict):
    """
    Gera relatório XLS com rastreamento de cada disparo WhatsApp no Umove
    resultados_dict: {'agente': {'total': N, 'sucesso': N, 'pedidos': [...]}}
    """
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book

        # Estilos
        header_fmt = workbook.add_format({'bold': True,
                                        'bg_color': '#0F172A',
                                        'font_color': 'white',
                                        'border': 1,
                                        'align': 'center',
                                        'valign': 'vcenter'})
        sucesso_fmt = workbook.add_format(
            {'bg_color': '#DCFCE7', 'font_color': '#166534', 'border': 1, 'align': 'center'})
        falha_fmt = workbook.add_format(
            {'bg_color': '#FEE2E2', 'font_color': '#991B1B', 'border': 1, 'align': 'center'})
        normal_fmt = workbook.add_format(
            {'border': 1, 'align': 'left', 'valign': 'vcenter'})
        total_fmt = workbook.add_format(
            {'bold': True, 'bg_color': '#E0E7FF', 'border': 1, 'align': 'center'})

        # RESUMO GERAL
        resumo_data = []
        total_geral_pedidos = 0
        total_geral_sucesso = 0
        for agente, dados in resultados_dict.items():
            resumo_data.append({
                'AGENTE': agente,
                'TOTAL_DISPAROS': dados['total'],
                'SUCESSOS': dados['sucesso'],
                'FALHAS': dados['total'] - dados['sucesso'],
                'TAXA_SUCESSO': f"{(dados['sucesso'] / dados['total'] * 100):.1f}%" if dados['total'] > 0 else "0%"
            })
            total_geral_pedidos += dados['total']
            total_geral_sucesso += dados['sucesso']

        df_resumo = pd.DataFrame(resumo_data)
        df_resumo.to_excel(
            writer,
            sheet_name='RESUMO_DISPAROS',
            index=False,
            startrow=0)
        ws_resumo = writer.sheets['RESUMO_DISPAROS']
        ws_resumo.set_column('A:A', 25)
        ws_resumo.set_column('B:B', 15)
        ws_resumo.set_column('C:C', 12)
        ws_resumo.set_column('D:D', 12)
        ws_resumo.set_column('E:E', 15)

        # Formatar cabeçalho
        for col_num, col_name in enumerate(df_resumo.columns, 1):
            ws_resumo.write(0, col_num - 1, col_name, header_fmt)

        # Formatar dados
        for row_num, row_data in enumerate(resumo_data, 1):
            ws_resumo.write(row_num, 0, row_data['AGENTE'], normal_fmt)
            ws_resumo.write(row_num, 1, row_data['TOTAL_DISPAROS'], total_fmt)
            ws_resumo.write(row_num, 2, row_data['SUCESSOS'], sucesso_fmt)
            ws_resumo.write(
                row_num,
                3,
                row_data['FALHAS'],
                falha_fmt if row_data['FALHAS'] > 0 else sucesso_fmt)
            ws_resumo.write(row_num, 4, row_data['TAXA_SUCESSO'], total_fmt)

        # Total geral
        taxa_geral = f"{(total_geral_sucesso / total_geral_pedidos * 100):.1f}%" if total_geral_pedidos > 0 else "0%"
        linha_total = len(df_resumo) + 1
        ws_resumo.write(linha_total, 0, 'TOTAL GERAL', total_fmt)
        ws_resumo.write(linha_total, 1, total_geral_pedidos, total_fmt)
        ws_resumo.write(linha_total, 2, total_geral_sucesso, sucesso_fmt)
        ws_resumo.write(
            linha_total,
            3,
            total_geral_pedidos -
            total_geral_sucesso,
            total_fmt)
        ws_resumo.write(linha_total, 4, taxa_geral, total_fmt)

        # DETALHES POR AGENTE
        df_detalhe = df_disparos.copy()
        cols_det = [
            'PEDIDO',
            'AGENTE_RAW',
            'LABORATORIO',
            'ENDERECO',
            'NUMERO',
            'BAIRRO',
            'CIDADE',
            'UF',
            'TOMADOR',
            'STATUS_ENVIO']
        for c in cols_det:
            if c not in df_detalhe.columns:
                df_detalhe[c] = ""

        df_detalhe['STATUS_ENVIO'] = df_detalhe['AGENTE_RAW'].apply(
            lambda x: '✅ ENVIADO' if x in [
                ag for ag, d in resultados_dict.items() if d['sucesso'] > 0] else '❌ FALHA')

        df_detalhe[cols_det].to_excel(
            writer, sheet_name='DETALHES_PEDIDOS', index=False)
        ws_detalhe = writer.sheets['DETALHES_PEDIDOS']
        ws_detalhe.set_column('A:A', 12)
        ws_detalhe.set_column('B:B', 20)
        ws_detalhe.set_column('C:C', 35)
        ws_detalhe.set_column('D:D', 30)
        ws_detalhe.set_column('E:E', 10)
        ws_detalhe.set_column('F:F', 20)
        ws_detalhe.set_column('G:G', 15)
        ws_detalhe.set_column('H:H', 8)
        ws_detalhe.set_column('I:I', 20)
        ws_detalhe.set_column('J:J', 15)

        for col_num, col_name in enumerate(cols_det, 1):
            ws_detalhe.write(0, col_num - 1, col_name, header_fmt)

        # INFORMAÇÕES DO DISPARO
        ws_info = workbook.add_worksheet('INFORMACOES')
        ws_info.set_column('A:B', 25)
        info_fmt = workbook.add_format(
            {'bold': True, 'bg_color': '#F0F9FF', 'border': 1})
        info_val_fmt = workbook.add_format({'border': 1})

        ws_info.write(0, 0, 'DATA DO DISPARO', info_fmt)
        ws_info.write(0, 1, hoje_br.strftime(
            '%d/%m/%Y %H:%M:%S'), info_val_fmt)
        ws_info.write(1, 0, 'TOTAL DE AGENTES', info_fmt)
        ws_info.write(1, 1, len(resultados_dict), info_val_fmt)
        ws_info.write(2, 0, 'TOTAL DE PEDIDOS', info_fmt)
        ws_info.write(2, 1, total_geral_pedidos, info_val_fmt)
        ws_info.write(3, 0, 'SUCESSOS', info_fmt)
        ws_info.write(3, 1, total_geral_sucesso, info_val_fmt)
        ws_info.write(4, 0, 'FALHAS', info_fmt)
        ws_info.write(
            4,
            1,
            total_geral_pedidos -
            total_geral_sucesso,
            info_val_fmt)
        ws_info.write(5, 0, 'TAXA DE SUCESSO', info_fmt)
        ws_info.write(5, 1, taxa_geral, info_val_fmt)

    return output.getvalue()


def salvar_historico_disparo_umove(df_disparos, resultados_dict, periodo, planilha):
    if planilha is None:
        return False
    try:
        try:
            aba = planilha.worksheet("Historico_Disparos_Umove")
        except Exception:
            aba = planilha.add_worksheet(
                title="Historico_Disparos_Umove",
                rows=200,
                cols=20)
            aba.update("A1", [[
                "ID_EVENTO",
                "DATA_DISPARO",
                "PERIODO",
                "MOTORISTA",
                "TOTAL_PEDIDOS",
                "SUCESSOS",
                "FALHAS",
                "PEDIDOS"
            ]])

        id_evento = f"UMOVE-{datetime.now(FUSO_BR).strftime('%Y%m%d%H%M%S')}"
        rows = []
        for motorista, dados in resultados_dict.items():
            pedidos = dados.get('pedidos', [])
            pedidos_text = ", ".join([str(p) for p in pedidos])
            if len(pedidos_text) > 3000:
                pedidos_text = pedidos_text[:3000] + "..."
            total = int(dados.get('total', 0))
            sucesso = int(dados.get('sucesso', 0))
            falha = total - sucesso
            rows.append([
                id_evento,
                datetime.now(FUSO_BR).strftime('%d/%m/%Y %H:%M:%S'),
                periodo,
                motorista,
                total,
                sucesso,
                falha,
                pedidos_text
            ])
        if rows:
            aba.append_rows(rows, value_input_option='USER_ENTERED')
            return True
    except Exception:
        return False
    return False


def gerar_pdf_romaneio(
        id_romaneio,
        data_despacho,
        motorista_escolhido,
        sel_lista):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_draw_color(15, 23, 42)
    pdf.set_line_width(0.3)
    pdf.rect(5, 5, 200, 287)
    try:
        logo_path = os.path.join(tempfile.gettempdir(), "igo_logo_temp.png")
        if not os.path.exists(logo_path):
            req = urllib.request.Request(
                "https://i.postimg.cc/x84nnjjq/IGO-LOGO.png",
                headers={
                    'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response, open(logo_path, 'wb') as out_file:
                out_file.write(response.read())
        pdf.image(logo_path, x=10, y=8, w=30)
    except Exception:
        pass

    pdf.set_y(15)
    pdf.set_font("Arial", "B", 14)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 6, f"PROTOCOLO DE ENTREGA - IGO LOGISTICA", ln=True, align="C")
    pdf.set_font("Arial", "B", 10)
    pdf.set_text_color(2, 132, 199)
    pdf.cell(0, 5, f"LOTE DE EXPEDIÇÃO: {id_romaneio}", ln=True, align="C")
    pdf.set_font("Arial", "", 8)
    pdf.set_text_color(100, 116, 139)
    dt_str = data_despacho if isinstance(
        data_despacho, str) else data_despacho.strftime('%d/%m/%Y')

    nome_amigavel = str(motorista_escolhido).upper()
    try:
        if not DF_AGENTES.empty:
            match_nome = DF_AGENTES[DF_AGENTES['LOGIN DO AGENTE'] == str(
                motorista_escolhido).strip().lower()]
            if not match_nome.empty:
                nome_amigavel = str(
                    match_nome.iloc[0]['NOME DO AGENTE']).upper()
    except Exception:
        pass

    pdf.cell(
        0,
        4,
        f"Data do Embarque: {dt_str} | Motorista: {nome_amigavel}",
        ln=True,
        align="C")
    pdf.ln(3)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)

    pdf.set_fill_color(15, 23, 42)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", "B", 7)
    pdf.cell(10, 5, "ITEM", 1, 0, "C", True)
    pdf.cell(25, 5, "PEDIDO", 1, 0, "C", True)
    pdf.cell(30, 5, "ID CLIENTE", 1, 0, "C", True)
    pdf.cell(80, 5, "PONTO DE COLETA / LABORATÓRIO", 1, 0, "C", True)
    pdf.cell(35, 5, "CIDADE", 1, 0, "C", True)
    pdf.cell(10, 5, "UF", 1, 1, "C", True)
    pdf.set_text_color(51, 65, 85)
    pdf.set_font("Arial", "", 7)

    for idx, item in enumerate(sel_lista, 1):
        fill = (idx % 2 == 0)
                
        # Correção para evitar que o Streamlit imprima "None" na tela
        if fill:
            pdf.set_fill_color(241, 245, 249)
        else:
            pdf.set_fill_color(255, 255, 255)
        qr_val = str(item.get('QR_CODE', ''))
        if qr_val.upper() == 'NAN' or not qr_val:
            qr_val = "-"

        lab = corrigir_nomes_relatorio(padronizar_texto(
            str(item.get('LABORATORIO', ''))))[:48]

        pdf.cell(10, 5, str(idx), 1, 0, "C", True)
        pdf.cell(25, 5, str(item.get('PEDIDO', '')), 1, 0, "C", True)
        pdf.cell(30, 5, qr_val, 1, 0, "C", True)
        pdf.cell(80, 5, lab, 1, 0, "L", True)
        pdf.cell(35, 5, padronizar_texto(
            str(item.get('CIDADE', '')))[:22], 1, 0, "L", True)
        pdf.cell(10, 5, str(item.get('UF', '')), 1, 1, "C", True)

    pdf.ln(4)
    pdf.set_font("Arial", "B", 8)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(
        0,
        5,
        f"TOTAL DE VOLUMES CONFERIDOS E EMBARCADOS: {
            len(sel_lista)}",
        ln=True,
        align="R")
    pdf.set_y(-25)
    pdf.line(20, pdf.get_y(), 90, pdf.get_y())
    pdf.line(120, pdf.get_y(), 190, pdf.get_y())
    pdf.set_font("Arial", "B", 7)
    pdf.cell(95, 4, "ASSINATURA CADEIA (MOTORISTA)", 0, 0, "C")
    pdf.cell(95, 4, "ASSINATURA EXPEDIÇÃO (BASE IGO)", 0, 1, "C")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
        pdf.output(tmp_pdf.name)
        with open(tmp_pdf.name, "rb") as f:
            pdf_bytes = f.read()
    return pdf_bytes
# =============================================================================
# 🏷️ FUNÇÕES DO GERADOR DE ETIQUETAS (PADRÃO LABELJOY: 4.85x2.80cm)
# =============================================================================
from collections import Counter
import unicodedata

def obter_logo_etiqueta_pil():
    """Retorna bytes da logo da IGO com cache local e fallback de download."""
    logo_url = "https://i.postimg.cc/x84nnjjq/IGO-LOGO.png"
    logo_cache_path = os.path.join(tempfile.gettempdir(), "igo_logo_etiqueta_cache.png")

    # 1) Prioriza cache local válido (evita depender da rede em toda renderização).
    try:
        if os.path.exists(logo_cache_path) and os.path.getsize(logo_cache_path) > 0:
            with open(logo_cache_path, "rb") as f_logo:
                return f_logo.read()
    except:
        pass

    # 2) Tenta urllib (mais leve) e salva em cache local.
    try:
        req = urllib.request.Request(logo_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=8) as response:
            logo_bytes = response.read()
            if logo_bytes:
                with open(logo_cache_path, "wb") as f_logo:
                    f_logo.write(logo_bytes)
                return logo_bytes
    except:
        pass

    # 3) Fallback com requests (ambientes podem bloquear urllib).
    try:
        resp = requests.get(logo_url, timeout=8)
        if resp.status_code == 200 and resp.content:
            with open(logo_cache_path, "wb") as f_logo:
                f_logo.write(resp.content)
            return resp.content
    except:
        pass

    return None

def gerar_codigo_unico_etiqueta():
    """Gera um código único aleatório (Ex: IGO-A8X92B)"""
    caracteres = string.ascii_uppercase + string.digits
    codigo = ''.join(random.choices(caracteres, k=6))
    return f"IGO-{codigo}"

def gerar_sigla_regiao(nome_agente, df_agentes):
    """Descobre a cidade principal do motorista e gera uma sigla de 3 letras"""
    if nome_agente == "GERAL/SEM AGENTE" or df_agentes.empty:
        return "IGO"
                
    df_ag = df_agentes[df_agentes['NOME DO AGENTE'] == nome_agente]
    if df_ag.empty:
        return str(nome_agente)[:3].upper()
                
    rotas = df_ag['ROTA MAPEADA'].dropna().tolist()
    cidades = []
    for r in rotas:
        if str(r).strip() and "SEM ROTA" not in str(r).upper():
            cid = str(r).split('➔')[0].split('---')[0].strip().upper()
            if cid:
                cidades.append(cid)
                        
    if not cidades:
        return str(nome_agente)[:3].upper()
                
    cidade_principal = Counter(cidades).most_common(1)[0][0]
    cidade_limpa = ''.join(c for c in unicodedata.normalize('NFD', cidade_principal) if unicodedata.category(c) != 'Mn')
    palavras = [p for p in cidade_limpa.split() if p not in ['DE', 'DA', 'DO', 'DAS', 'DOS']]
            
    if not palavras:
        return "IGO"
                
    if len(palavras) >= 3:
        sigla = palavras[0][0] + palavras[1][0] + palavras[2][0]
    elif len(palavras) == 2:
        sigla = palavras[0][0] + palavras[1][:2]
    else:
        sigla = palavras[0][:3]
                
    return sigla.ljust(3, 'X').upper()

def criar_imagem_etiqueta_pil(codigo, sigla_tarja, tam_qr, tam_fonte, mostrar_logo, 
                            largura_tarja, altura_tarja, tam_logo,
                            off_x_tarja, off_y_tarja, off_x_txt, off_y_txt, 
                            off_x_qr, off_y_qr, off_x_logo, off_y_logo):
    """Desenha a imagem da etiqueta com liberdade total de movimento (Eixos X e Y)"""
    largura, altura = 573, 331
    img = Image.new('RGB', (largura, altura), 'white')
    draw = ImageDraw.Draw(img)
            
    # 1. Desenhar a Tarja Preta (Com controle de posição, largura e altura)
    draw.rectangle([off_x_tarja, off_y_tarja, off_x_tarja + largura_tarja, off_y_tarja + altura_tarja], fill="black")
            
    fontes_possiveis = ["arialbd.ttf", "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf", "FreeSansBold.ttf", "Arial Bold.ttf"]
    font_tarja = None
    for fonte in fontes_possiveis:
        try:
            font_tarja = ImageFont.truetype(fonte, tam_fonte)
            break
        except IOError:
            continue
                    
    if font_tarja is None:
        try: font_tarja = ImageFont.load_default(size=tam_fonte)
        except: font_tarja = ImageFont.load_default()
                    
    # 2. Texto da Tarja (Independente da Tarja)
    img_txt_tarja = Image.new('RGBA', (altura, largura_tarja), (0,0,0,0))
    draw_tarja = ImageDraw.Draw(img_txt_tarja)
            
    try:
        bbox = draw_tarja.textbbox((0, 0), sigla_tarja, font=font_tarja)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
    except:
        tw, th = 100, 40
                
    draw_tarja.text(((altura - tw)/2, (largura_tarja - th)/2 - 15), sigla_tarja, font=font_tarja, fill="white")
            
    # 👇 A CORREÇÃO ESTÁ AQUI: Mudamos de 90 para 270 graus 👇
    img_txt_tarja_rot = img_txt_tarja.rotate(270, expand=True) 
            
    # Posição final do texto com Offset do eixo X e Y
    img.paste(img_txt_tarja_rot, (off_x_tarja + off_x_txt, off_y_txt), img_txt_tarja_rot)
            
    # 3. Colar a Logo Oficial Colorida
    logo_w_real = 0
    if mostrar_logo:
        logo_bytes = obter_logo_etiqueta_pil()
        # Fallback: se o cache tiver salvo vazio por falha temporária de rede,
        # tenta buscar novamente em tempo real para não "sumir" com a logo.
        if not logo_bytes:
            try:
                resp = requests.get("https://i.postimg.cc/x84nnjjq/IGO-LOGO.png", timeout=8)
                if resp.status_code == 200 and resp.content:
                    logo_bytes = resp.content
            except:
                logo_bytes = None
        if logo_bytes:
            try:
                logo_img = Image.open(io.BytesIO(logo_bytes)).convert("RGBA")
                logo_rot = logo_img.rotate(270, expand=True)

                filtro = Image.Resampling.LANCZOS if hasattr(Image, 'Resampling') else Image.ANTIALIAS
                logo_rot.thumbnail((tam_logo, 300), filtro)

                logo_w_real = logo_rot.width + 10
                # Centro matemático + offset do usuário
                pos_x_logo = largura - logo_rot.width - 10 + off_x_logo
                pos_y_logo = int((altura - logo_rot.height) / 2) + off_y_logo

                bg_logo = Image.new("RGB", logo_rot.size, (255,255,255))
                bg_logo.paste(logo_rot, (0,0), logo_rot)
                img.paste(bg_logo, (pos_x_logo, pos_y_logo))
            except:
                logo_w_real = 0

    # 4. Gerar e Posicionar QR Code Dinâmico
    qr = qrcode.QRCode(version=1, box_size=10, border=0)
    qr.add_data(codigo)
    qr.make(fit=True)
    img_qr = qr.make_image(fill_color="black", back_color="white")
            
    resampling_filter = getattr(Image, 'Resampling', Image).LANCZOS
    img_qr = img_qr.resize((tam_qr, tam_qr), resampling_filter)
            
    # Centro matemático livre inteligente + offset do usuário
    espaco_livre_x = largura - largura_tarja - logo_w_real
    pos_x_qr = off_x_tarja + largura_tarja + int((espaco_livre_x - tam_qr) / 2) + off_x_qr
    pos_y_qr = int((altura - tam_qr) / 2) + off_y_qr
            
    img.paste(img_qr, (pos_x_qr, pos_y_qr))
            
    temp_path = os.path.join(tempfile.gettempdir(), f"etiq_{codigo}.png")
    img.save(temp_path, dpi=(300, 300))
    return temp_path


def gerar_pdf_rolo_duplo_premium(lista_codigos, sigla_final, larg_pagina, alt_pagina, larg_etiq, alt_etiq, margem_esq, gap_central, tam_qr, tam_fonte, mostrar_logo, largura_tarja, altura_tarja, tam_logo, off_x_tarja, off_y_tarja, off_x_txt, off_y_txt, off_x_qr, off_y_qr, off_x_logo, off_y_logo):
    # 🔥 CORREÇÃO: orientation='L' e invertemos o formato para a Zebra entender 🔥
    pdf = FPDF(orientation='L', unit='mm', format=(alt_pagina, larg_pagina))
    pdf.set_auto_page_break(auto=False)
    pdf.set_margins(0, 0, 0)
                
    margem_topo = (alt_pagina - alt_etiq) / 2.0
    pos_x2 = margem_esq + larg_etiq + gap_central

    for i in range(0, len(lista_codigos), 2):
        pdf.add_page()
                
        cod1 = lista_codigos[i]
        img1 = criar_imagem_etiqueta_pil(cod1, sigla_final, tam_qr, tam_fonte, mostrar_logo, largura_tarja, altura_tarja, tam_logo, off_x_tarja, off_y_tarja, off_x_txt, off_y_txt, off_x_qr, off_y_qr, off_x_logo, off_y_logo)
        pdf.image(img1, x=margem_esq, y=margem_topo, w=larg_etiq, h=alt_etiq)
                
        if i + 1 < len(lista_codigos):
            cod2 = lista_codigos[i+1]
            img2 = criar_imagem_etiqueta_pil(cod2, sigla_final, tam_qr, tam_fonte, mostrar_logo, largura_tarja, altura_tarja, tam_logo, off_x_tarja, off_y_tarja, off_x_txt, off_y_txt, off_x_qr, off_y_qr, off_x_logo, off_y_logo)
            pdf.image(img2, x=pos_x2, y=margem_topo, w=larg_etiq, h=alt_etiq)
                
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
        pdf.output(tmp_pdf.name)
        with open(tmp_pdf.name, "rb") as f:
            pdf_bytes = f.read()
                    
    return pdf_bytes

# =============================================================================
# 🧭 NAVEGAÇÃO E SIDEBAR (MODERNA)
# =============================================================================
if 'filtro_kpi_admin' not in st.session_state:
    st.session_state.filtro_kpi_admin = "TODOS"

with st.sidebar:
    import streamlit.components.v1 as components

    st.image(
        "https://i.postimg.cc/x84nnjjq/IGO-LOGO.png",
        use_container_width=True)

    st.markdown("""
        <style>
        /* 🔥 SIDEBAR: SCROLL ESTÁVEL EM CAMADA ÚNICA 🔥 */
            section[data-testid="stSidebar"],
            [data-testid="stSidebar"] {
                --sidebar-btn-width: 220px;
                /* AJUSTE MANUAL AQUI: altura total da área de rolagem */
                --sidebar-scroll-height: 100vh;
                /* AJUSTE MANUAL AQUI: folga superior para rolar "para cima" */
                --sidebar-scroll-pad-top: 160px;
                /* AJUSTE MANUAL AQUI: folga inferior para rolar "para baixo" */
                --sidebar-scroll-pad-bottom: 260px;

                height: var(--sidebar-scroll-height) !important;
                max-height: var(--sidebar-scroll-height) !important;
                overflow-y: auto !important;
                overflow-x: hidden !important;
                overscroll-behavior-y: contain !important;
                -webkit-overflow-scrolling: touch !important;
                pointer-events: auto !important;
            }

            /* Perfil notebook (1366x768 e similares) */
            @media (max-height: 820px) {
                section[data-testid="stSidebar"],
                [data-testid="stSidebar"] {
                    --sidebar-scroll-pad-top: 120px;
                    --sidebar-scroll-pad-bottom: 220px;
                }
            }

            /* Perfil telas pequenas */
            @media (max-width: 768px), (max-height: 700px) {
                section[data-testid="stSidebar"],
                [data-testid="stSidebar"] {
                    --sidebar-scroll-pad-top: 96px;
                    --sidebar-scroll-pad-bottom: 180px;
                }
            }

            /* Camadas internas não podem disputar o scroll */
            section[data-testid="stSidebar"] > div:first-child,
            [data-testid="stSidebar"] > div:first-child,
            section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"],
            section[data-testid="stSidebar"] [data-testid="stSidebarContent"],
            [data-testid="stSidebarUserContent"],
            [data-testid="stSidebarContent"] {
                height: auto !important;
                max-height: none !important;
                overflow: visible !important;
            }

            /* Barra visível para garantir percepção do scroll */
            section[data-testid="stSidebar"]::-webkit-scrollbar,
            [data-testid="stSidebar"]::-webkit-scrollbar {
                width: 8px !important;
            }
            section[data-testid="stSidebar"]::-webkit-scrollbar-thumb,
            [data-testid="stSidebar"]::-webkit-scrollbar-thumb {
                background: #cbd5e1 !important;
                border-radius: 10px !important;
            }

            /* Espaço superior/inferior para rolagem longa nos dois sentidos */
            section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"],
            section[data-testid="stSidebar"] [data-testid="stSidebarContent"],
            [data-testid="stSidebarUserContent"],
            [data-testid="stSidebarContent"] {
                padding: var(--sidebar-scroll-pad-top) 10px var(--sidebar-scroll-pad-bottom) !important;
            }
                
        [data-testid="stSidebar"] .stImage {
            margin-bottom: 6px !important;
        }
        [data-testid="stSidebar"] .stImage img {
            display: block;
            margin: 0 auto;
            max-width: 94% !important;
        }
        [data-testid="stSidebar"] .nav-premium-wrap {
            background: linear-gradient(140deg, #0F172A 0%, #1E293B 60%, #334155 100%);
            border: 1px solid rgba(148, 163, 184, 0.28);
            border-radius: 14px;
            padding: 10px 10px;
            margin-bottom: 8px;
            box-shadow: 0 10px 22px rgba(15, 23, 42, 0.25);
        }
        [data-testid="stSidebar"] .nav-premium-title {
            color: #F8FAFC;
            font-size: 12px;
            font-weight: 900;
            letter-spacing: 1.3px;
            text-transform: uppercase;
            margin-bottom: 4px;
        }
        [data-testid="stSidebar"] .nav-premium-subtitle {
            color: #CBD5E1;
            font-size: 11px;
            margin: 0;
        }
        [data-testid="stSidebar"] div.stRadio > div {
            gap: 4px;
            margin-top: 2px;
            align-items: center;
        }
        [data-testid="stSidebar"] div[role="radiogroup"] {
            width: var(--sidebar-btn-width);
            margin: 0 auto;
        }
        [data-testid="stSidebar"] div[role="radiogroup"] > label {
            width: 100%;
            min-height: 38px;
            box-sizing: border-box;
            background: linear-gradient(135deg, #FFFFFF 0%, #F8FAFC 100%);
            border: 1px solid #E2E8F0;
            border-radius: 10px;
            padding: 6px 12px;
            margin: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06);
            transition: all 0.2s ease;
        }
        [data-testid="stSidebar"] div[role="radiogroup"] > label:hover {
            border-color: #93C5FD;
            transform: none;
            box-shadow: 0 6px 16px rgba(59, 130, 246, 0.14);
        }
        [data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child {
            display: none;
        }
        [data-testid="stSidebar"] div[role="radiogroup"] input[type="radio"] {
            appearance: none !important;
            -webkit-appearance: none !important;
            accent-color: transparent !important;
            width: 0 !important;
            height: 0 !important;
            margin: 0 !important;
            opacity: 0 !important;
            position: absolute !important;
            pointer-events: none !important;
        }
        [data-testid="stSidebar"] div[role="radiogroup"] > label p {
            font-size: 12px;
            font-weight: 700;
            color: #0F172A;
            margin: 0;
            line-height: 1.05;
            text-align: center;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            width: 100%;
        }
        [data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) {
            background: linear-gradient(135deg, #0EA5E9 0%, #2563EB 100%);
            border-color: #1D4ED8;
            box-shadow: 0 8px 16px rgba(37, 99, 235, 0.30);
            transform: none;
        }
        [data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) p,
        [data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) span,
        [data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) div,
        [data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) * {
            color: #FFFFFF !important;
            font-weight: 800;
        }
        [data-testid="stSidebar"] div.st-key-btn_sair_sidebar {
            width: var(--sidebar-btn-width);
            margin: 0 auto;
        }
        [data-testid="stSidebar"] div.st-key-btn_sair_sidebar button[kind="primary"] {
            background: #ef4444 !important;
            border: 1px solid #dc2626 !important;
            border-radius: 6px !important;
            box-sizing: border-box !important;
            box-shadow: none !important;
            min-height: 38px !important;
            margin-top: 4px !important;
        }
        [data-testid="stSidebar"] div.st-key-btn_sair_sidebar button[kind="primary"] p,
        [data-testid="stSidebar"] div.st-key-btn_sair_sidebar button[kind="primary"] span,
        [data-testid="stSidebar"] div.st-key-btn_sair_sidebar button[kind="primary"] div {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            color: #ffffff !important;
            font-weight: 700 !important;
            font-size: 14px !important;
        }
        [data-testid="stSidebar"] div.st-key-btn_sair_sidebar button[kind="primary"]:hover {
            background: #dc2626 !important;
            border-color: #b91c1c !important;
            box-shadow: none !important;
            transform: none !important;
        }
        [data-testid="stSidebar"] div.st-key-btn_sair_sidebar button[kind="primary"]:hover p,
        [data-testid="stSidebar"] div.st-key-btn_sair_sidebar button[kind="primary"]:hover span {
            color: #ffffff !important;
        }
        [data-testid="stSidebar"] hr {
            width: var(--sidebar-btn-width);
            margin: 10px auto 10px !important;
        }
        </style>
    """, unsafe_allow_html=True)

    components.html(
        """
        <script>
        (function () {
            function getSidebarScroller(doc) {
                const sidebar = doc.querySelector('section[data-testid="stSidebar"], [data-testid="stSidebar"]');
                if (!sidebar) return null;

                const candidates = [
                    sidebar,
                    sidebar.querySelector('[data-testid="stSidebarUserContent"]'),
                    sidebar.querySelector('[data-testid="stSidebarContent"]'),
                    sidebar.querySelector(':scope > div:first-child')
                ].filter(Boolean);

                let best = null;
                let bestDelta = 0;
                for (const el of candidates) {
                    const delta = el.scrollHeight - el.clientHeight;
                    if (delta > bestDelta) {
                        bestDelta = delta;
                        best = el;
                    }
                }
                return bestDelta > 0 ? best : null;
            }

            function centerSidebarIfNeeded() {
                const doc = window.parent.document;
                const scroller = getSidebarScroller(doc);
                if (!scroller) return false;

                // Só centraliza se estiver no topo (estado inicial)
                if (scroller.scrollTop <= 2) {
                    scroller.scrollTop = Math.round((scroller.scrollHeight - scroller.clientHeight) / 2);
                }
                return true;
            }

            let tries = 0;
            const timer = setInterval(() => {
                tries += 1;
                const ok = centerSidebarIfNeeded();
                if (ok || tries >= 40) clearInterval(timer);
            }, 120);
        })();
        </script>
        """,
        height=0,
        width=0,
    )

    qtd_chamados_abertos = checar_chamados_pendentes(planilha_db)
    if qtd_chamados_abertos > 0:
        st.markdown(f"""
            <div style="background-color: #FEF2F2; border-left: 4px solid #DC2626; padding: 8px; border-radius: 4px; margin-bottom: 8px; box-shadow: 0 2px 4px rgba(220, 38, 38, 0.2);">
                <p style="color: #991B1B; font-weight: 800; font-size: 12px; margin: 0;">🚨 {qtd_chamados_abertos} Chamado(s) Aberto(s)</p>
                <p style="color: #7F1D1D; font-size: 10px; margin: 0;">Acesse o menu Atendimento.</p>
            </div>
        """, unsafe_allow_html=True)

    menu_opcoes = [
        "📈 Dashboard",
        "📊 GRID",
        "💰 Faturamento",
        "📥 Importações",
        "📥 Importações Umove",
        "📝 Pedido Manual",
        "🏷️ Gerador de Etiquetas", # <--- COLE ESTA LINHA AQUI
        "📁 Relatórios",
        "⚙️ Rotas",
        "🔬 Triagem",
        "🎧 Atendimento"
    ]

    usuario_atual = st.session_state.usuarios_login.get(st.session_state.usuario_logado or "", {})
    if usuario_atual.get("admin", False):
        menu_opcoes.append("👥 Cadastro de Usuários")

    menu = st.radio("Navegação Operacional:", menu_opcoes, index=1, label_visibility="collapsed")

    st.divider()

    if st.button("🚪 Sair do Sistema", key="btn_sair_sidebar", use_container_width=True, type="primary"):
        st.session_state.autenticado = False
        st.session_state.usuario_logado = None
        st.rerun()

# ✅ AUTO-REFRESH SÓ NA GRID!
if menu == "📊 GRID":
    st_autorefresh(interval=120000, limit=None, key="refresh_timer")

if menu != "📈 Dashboard":
    usuario_online = (st.session_state.get('usuario_logado') or 'N/A').upper()
    st.markdown(f"""
        <div class="header-container">
            <div>
                <div class="header-title">CONTROLE OPERACIONAL</div>
            </div>
            <div class="sync-status">
                <div class="status-chip online"><span class="sync-dot"></span> Online: {datetime.now(FUSO_BR).strftime('%H:%M')}</div>
                <div class="status-chip user">👤 Usuário logado: {usuario_online}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

# =============================================================================
# 📊 MÓDULO GRID
# =============================================================================
if menu == "📊 GRID":
    df_raw = carregar_dados_completos(planilha_db)

    # 🔥 AUTO-SYNC SILENCIOSO (A MÁGICA INVISÍVEL) 🔥
    if not df_raw.empty and 'STATUS_DB_ORIGINAL' in df_raw.columns:
        mask_sync = (df_raw['STATUS_DB_ORIGINAL'] != df_raw['STATUS']) & (df_raw['STATUS'].isin(
            ['ENTREGUE', 'FRUSTRADA', 'PROBLEMA', 'CANCELADO', 'CONFERIDO', 'COLETADO']))
        df_to_sync = df_raw[mask_sync]

        if not df_to_sync.empty:
            try:
                aba_m = planilha_db.worksheet("Memoria_Sistema")
                df_nuvem = pd.DataFrame(
                    aba_m.get_all_values()[1:], columns=aba_m.get_all_values()[0])

                # Mapeia as atualizações de forma vetorizada (muito mais rápido no Pandas)
                df_nuvem.set_index('PEDIDO', inplace=True)
                df_to_sync.set_index('PEDIDO', inplace=True)
                        
                df_nuvem.update(df_to_sync[['STATUS', 'DATA_ENTREGA']])
                df_nuvem.reset_index(inplace=True)
                df_to_sync.reset_index(inplace=True)

                aba_m.clear()
                aba_m.update("A1", [df_nuvem.columns.tolist()] +
                            df_nuvem.fillna("").astype(str).values.tolist())
                        
                # 🔥 A mágica: só limpa o cache se REALMENTE houver sincronização pesada
                carregar_dados_completos.clear()
                df_raw = carregar_dados_completos(planilha_db)
            except Exception:
                pass

    if not df_raw.empty:
        qtd_chamados_abertos = checar_chamados_pendentes(planilha_db)
        if qtd_chamados_abertos > 0:
            st.error(
                f"🎧 **HELPDESK:** Existem **{qtd_chamados_abertos} chamado(s)** de clientes aguardando sua resposta na aba de Atendimento!")

        # CAIXA DE ENTRADA DO PORTAL DO CLIENTE
        df_aprovacao = df_raw[df_raw['STATUS'].astype(
            str).str.upper() == 'AGUARDANDO APROVAÇÃO'].copy()
        if not df_aprovacao.empty:
            st.error(
                f"🚨 **Atenção:** Existem {
                    len(df_aprovacao)} solicitação(ões) de coleta do Portal do Cliente aguardando aprovação!")
            with st.expander("🔔 INBOX: Analisar e Aprovar Coletas", expanded=True):
                if 'OBSERVACOES' not in df_aprovacao.columns:
                    df_aprovacao['OBSERVACOES'] = ""
                colunas_reais = [
                    c for c in [
                        'DATA',
                        'PEDIDO',
                        'TOMADOR',
                        'LABORATORIO',
                        'CIDADE',
                        'OBSERVACOES'] if c in df_aprovacao.columns]
                df_aprovacao_show = df_aprovacao[colunas_reais].copy()
                df_aprovacao_show.insert(0, "SELECIONAR", False)
                tabela_aprov = st.data_editor(
                    df_aprovacao_show,
                    hide_index=True,
                    disabled=colunas_reais,
                    use_container_width=True,
                    key="grid_aprovacao_inbox")
                sel_aprov = tabela_aprov[tabela_aprov["SELECIONAR"]]

                if not sel_aprov.empty:
                    c_mot, c_btn1, c_btn2 = st.columns([2, 1, 1])
                    logins_disp = sorted(
                        DF_AGENTES['LOGIN DO AGENTE'].unique().tolist()) if not DF_AGENTES.empty else []
                    mot_aprov = c_mot.selectbox(
                        "👤 Atribuir Motorista:",
                        ["Automático (Por Rota)"] + logins_disp,
                        key="sel_mot_aprov")

                    if c_btn1.button(
                        "✅ Aprovar e Roteirizar",
                        type="primary",
                            use_container_width=True):
                        with st.spinner("Processando..."):
                            try:
                                aba_m = planilha_db.worksheet(
                                    "Memoria_Sistema")
                                df_nuvem = pd.DataFrame(
                                    aba_m.get_all_values()[
                                        1:], columns=aba_m.get_all_values()[0])
                                pedidos_aprov = sel_aprov['PEDIDO'].astype(
                                    str).tolist()
                                lista_para_app = []

                                for pid in pedidos_aprov:
                                    mask = df_nuvem['PEDIDO'] == pid
                                    if mask.any():
                                        l_orig = df_nuvem[mask].iloc[0].copy()
                                        if mot_aprov == "Automático (Por Rota)":
                                            mot_final = obter_login_agente(
                                                l_orig.get(
                                                    'CIDADE', ''), l_orig.get(
                                                    'BAIRRO', ''), l_orig.get(
                                                    'LABORATORIO', ''), l_orig.get(
                                                    'ENDERECO', ''), DF_AGENTES)
                                        else:
                                            mot_final = mot_aprov

                                        prazo_calc = calcular_sla_dias(str(l_orig.get('UF', 'SP')), str(
                                            l_orig.get('CIDADE', '')), str(l_orig.get('TOMADOR', '')))
                                        data_limite_calc = calcular_data_limite(
                                            str(l_orig.get('DATA', hoje_br.strftime("%d/%m/%Y"))), prazo_calc)

                                        df_nuvem.loc[mask, 'PRAZO_DIAS'] = str(
                                            prazo_calc)
                                        df_nuvem.loc[mask, 'DATA_LIMITE'] = str(
                                            data_limite_calc)
                                        df_nuvem.loc[mask,
                                                    'STATUS'] = "PENDENTE"
                                        df_nuvem.loc[mask,
                                                    'AGENTE_RAW'] = mot_final

                                        d_app = l_orig.to_dict()
                                        d_app['MOTORISTA'] = mot_final
                                        lista_para_app.append(d_app)

                                        if mot_final:
                                            tel_row = DF_AGENTES[DF_AGENTES['LOGIN DO AGENTE']
                                                                == mot_final]
                                            if not tel_row.empty:
                                                data_coleta = l_orig.get('DATA', hoje_br.strftime("%d/%m/%Y"))
                                                endereco_coleta = l_orig.get('ENDERECO', '')
                                                numero_coleta = l_orig.get('NUMERO', '')
                                                bairro_coleta = l_orig.get('BAIRRO', '')
                                                complemento_coleta = l_orig.get('COMPLEMENTO', '')
                                                telefone_cliente = l_orig.get('TELEFONE', '')
                                                        
                                                endereco_completo = f"{endereco_coleta}"
                                                if numero_coleta:
                                                    endereco_completo += f", nº {numero_coleta}"
                                                if complemento_coleta:
                                                    endereco_completo += f" - {complemento_coleta}"
                                                if bairro_coleta:
                                                    endereco_completo += f", {bairro_coleta}"
                                                        
                                                msg_zap = f"🚨 *NOVA COLETA APROVADA* 🚨\nOlá, {tel_row.iloc[0]['NOME DO AGENTE']}!\n\nUm novo pedido foi aprovado e adicionado à sua rota.\n\n📦 *Pedido:* {pid}\n🏢 *Cliente:* {l_orig.get('TOMADOR', '')}\n📅 *Data da Coleta:* {data_coleta}\n\n📍 *LOCALIZAÇÃO:*\n{endereco_completo}\n🏙️ *Cidade:* {l_orig.get('CIDADE', '')}"
                                                        
                                                if telefone_cliente:
                                                    msg_zap += f"\n📱 *Telefone Cliente:* {telefone_cliente}"
                                                        
                                                msg_zap += f"\n\n✅ Atualize seu GPS e boa sorte na coleta!"
                                                        
                                                enviar_whatsapp_zapi(
                                                    tel_row.iloc[0]['TELEFONE'], msg_zap)

                                aba_m.clear()
                                aba_m.update(
                                    "A1", [
                                        df_nuvem.columns.tolist()] + df_nuvem.fillna("").astype(str).values.tolist())
                                if lista_para_app:
                                    despachar_para_appsheet(lista_para_app)
                                        
                                st.session_state.ui_toast = {'msg': "Solicitações aprovadas!", 'icon': "🎉"}
                                carregar_dados_completos.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro: {e}")

                    if c_btn2.button(
                        "❌ Recusar Solicitação",
                            use_container_width=True):
                        with st.spinner("Recusando..."):
                            try:
                                aba_m = planilha_db.worksheet(
                                    "Memoria_Sistema")
                                df_nuvem = pd.DataFrame(
                                    aba_m.get_all_values()[
                                        1:], columns=aba_m.get_all_values()[0])
                                df_nuvem.loc[df_nuvem['PEDIDO'].isin(
                                    sel_aprov['PEDIDO'].astype(str).tolist()), 'STATUS'] = "RECUSADA"
                                aba_m.clear()
                                aba_m.update(
                                    "A1", [
                                        df_nuvem.columns.tolist()] + df_nuvem.fillna("").astype(str).values.tolist())
                                st.success("Recusadas!")
                                time.sleep(2)
                                carregar_dados_completos.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro: {e}")

        # INTELIGÊNCIA DOS DETALHES
        def get_detalhes(row):
            obs_master = str(row.get('OBSERVACOES', '')).strip()
            obs_app = str(row.get('APP_OBS', '')).strip()
            contato_app = str(row.get('A_CONTATO', '')).strip()
            status_atual = str(row.get('STATUS', '')).upper()

            if obs_master.upper() in ['NAN', 'NONE']:
                obs_master = ""
            if obs_app.upper() in ['NAN', 'NONE']:
                obs_app = ""
            if contato_app.upper() in ['NAN', 'NONE']:
                contato_app = ""

            obs_final_app = obs_app
            if obs_app and contato_app:
                if obs_app.upper() != contato_app.upper():
                    obs_final_app = f"{obs_app} / {contato_app}"
            elif contato_app:
                obs_final_app = contato_app

            obs_final = obs_final_app if obs_final_app else obs_master

            if status_atual in ['FRUSTRADA', 'PROBLEMA', 'CANCELADO']:
                obs_limpa = re.sub(
                    r'\[COLETA:.*?\]\s*-?\s*', '', obs_final).strip()
                if obs_limpa:
                    return f"⚠️ {obs_limpa}"
                else:
                    return "⚠️ Sem justificativa"

            if obs_final:
                return obs_final
            return "-"

        df_raw['DETALHES'] = df_raw.apply(get_detalhes, axis=1)

        def tratar_link_foto(x):
            x_str = str(x).strip()
            if not x_str or x_str.upper() in ['NAN', 'NONE']:
                return ""
            if x_str.startswith("http"):
                return x_str
            return f"https://www.appsheet.com/template/gettablefileurl?appName=APPIGOLOGISTICA-153047553&tableName=App_Tarefas&fileName={x_str}"

        df_raw['FOTO_URL'] = df_raw['FOTO'].apply(tratar_link_foto)
        df_raw['STATUS_DISPLAY'] = df_raw.apply(calc_status_display, axis=1)
        if 'DATA_LIMITE' in df_raw.columns:
            df_raw['DATA_LIMITE'] = df_raw['DATA_LIMITE'].fillna(
                "").astype(str)

        # FILTROS DA GRID
        col_f1, col_f2 = st.columns(2)
        f_cli = col_f1.selectbox(
            "🏢 Filtrar por Tomador:",
            ["Todos"] + CLIENTES_AUTORIZADOS)
        f_data = col_f2.date_input(
            "📅 Período:",
            value=(
                hoje_br -
                timedelta(
                    days=30),
                hoje_br),
            format="DD/MM/YYYY")

        df_f = df_raw.copy()
        if f_cli != "Todos":
            df_f = df_f[df_f['TOMADOR'] == f_cli]
        if isinstance(f_data, tuple) and len(f_data) == 2:
            df_f = df_f[(df_f['DATA_OBJ'] >= f_data[0]) &
                        (df_f['DATA_OBJ'] <= f_data[1])]

        # 🔥 OS NOVOS CARDS DE KPI (ESTILO PORTAL DO CLIENTE) 🔥
        n_vals = {
            "TODOS": len(df_f),
            "ENTREGUE": len(df_f[df_f['STATUS_DISPLAY'].str.contains('Entregue', case=False)]),
            "PENDENTE": len(df_f[df_f['STATUS_DISPLAY'].str.contains('Pendente', case=False)]),
            "FRUSTRADA": len(df_f[df_f['STATUS_DISPLAY'].str.contains('Frustrada', case=False)]),
            "ATRASADO": len(df_f[df_f['STATUS_DISPLAY'].str.contains('ATRASADO', case=False)]),
            "HOJE": len(df_f[df_f['DATA_OBJ'] == hoje_br]),
        }

        KPI_META = [
            ("TODOS", "📦 Total", "kpi_total", n_vals["TODOS"], "#2563eb", "#dbeafe"),
            ("ENTREGUE", "✅ Entregues", "kpi_entregue", n_vals["ENTREGUE"], "#16a34a", "#dcfce7"),
            ("PENDENTE", "⏳ Pendentes", "kpi_pend", n_vals["PENDENTE"], "#d97706", "#fef3c7"),
            ("FRUSTRADA", "❌ Frustradas", "kpi_frus", n_vals["FRUSTRADA"], "#dc2626", "#fee2e2"),
            ("ATRASADO", "🚨 Atrasados", "kpi_atra", n_vals["ATRASADO"], "#be123c", "#ffe4e6"),
            ("HOJE", "📅 Hoje", "kpi_hoje", n_vals["HOJE"], "#7c3aed", "#ede9fe")
        ]

        c_kpis = st.columns(7)

        for col, (filtro, label, key, valor, dot_color,
                bg_color) in zip(c_kpis[:6], KPI_META):
            is_active = st.session_state.filtro_kpi_admin == filtro
            borda = f"1px solid {dot_color}" if is_active else f"1px solid {bg_color}"
            partes = label.split(' ', 1)
            emoji_card = partes[0]
            texto_card = partes[1] if len(partes) > 1 else label

            with col:
                st.markdown(f"""
                    <div class="kpi-card" style="background-color: {bg_color}; border: {borda};">
                        <div style="position: absolute; right: -5px; bottom: -15px; font-size: 65px; opacity: 0.25; z-index: 0; line-height: 1; filter: drop-shadow(0px 2px 2px rgba(0,0,0,0.1));">{emoji_card}</div>
                        <div style="position: relative; z-index: 1;">
                            <div style="font-size: 11px; font-weight: 800; color: {dot_color}; text-transform: uppercase; letter-spacing: 0.5px;">{texto_card}</div>
                            <div style="font-size: 28px; font-weight: 900; color: #0F172A; margin-top: 2px; line-height: 1;">{valor}</div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                if st.button(label, key=key, use_container_width=True):
                    st.session_state.filtro_kpi_admin = filtro
                    st.rerun()

        # O 7º Cartão é o Helpdesk
        with c_kpis[6]:
            cor_tkt = "#991B1B" if qtd_chamados_abertos > 0 else "#475569"
            bg_tkt = "#fee2e2" if qtd_chamados_abertos > 0 else "#f1f5f9"
            borda_tkt = f"1px solid {cor_tkt}" if qtd_chamados_abertos > 0 else f"1px solid {bg_tkt}"
            st.markdown(f"""
                <div class="kpi-card" style="background-color: {bg_tkt}; border: {borda_tkt};">
                    <div style="position: absolute; right: -5px; bottom: -15px; font-size: 65px; opacity: 0.25; z-index: 0; line-height: 1;">🎧</div>
                    <div style="position: relative; z-index: 1;">
                        <div style="font-size: 11px; font-weight: 800; color: {cor_tkt}; text-transform: uppercase; letter-spacing: 0.5px;">Chamados</div>
                        <div style="font-size: 28px; font-weight: 900; color: #0F172A; margin-top: 2px; line-height: 1;">{qtd_chamados_abertos}</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            if st.button(
                "🎧 Chamados",
                key="btn_chamados_fake",
                    use_container_width=True):
                pass

        # Ocultando os botões nativos invisíveis que acionam a lógica acima
        st.markdown("""
            <style>
            div.st-key-kpi_total, div.st-key-kpi_entregue, div.st-key-kpi_pend, div.st-key-kpi_frus, div.st-key-kpi_atra, div.st-key-kpi_hoje, div.st-key-btn_chamados_fake {
                margin-top: -110px !important; position: relative; z-index: 999; opacity: 0 !important;
            }
            div.st-key-kpi_total button, div.st-key-kpi_entregue button, div.st-key-kpi_pend button, div.st-key-kpi_frus button, div.st-key-kpi_atra button, div.st-key-kpi_hoje button, div.st-key-btn_chamados_fake button {
                height: 105px !important; cursor: pointer !important;
            }
            </style>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # 🔥 BARRA DE PROGRESSO DOS PEDIDOS DO DIA 🔥
        df_hoje = df_f[df_f['DATA_OBJ'] == hoje_br]
        if not df_hoje.empty:
            n_concluidos = len(df_hoje[df_hoje['STATUS_DISPLAY'].str.contains('Entregue|Frustrada|Cancelado|Recusada|Coletado|Em Transferência', case=False, na=False)])
            n_total_hoje = len(df_hoje)
            pct_progresso = round((n_concluidos / n_total_hoje) * 100) if n_total_hoje else 0
        else:
            n_concluidos = 0
            n_total_hoje = 0
            pct_progresso = 0

        st.markdown(f"""
            <div class="progress-block-main">
                <div class="progress-block-content">
                    <div class="progress-title">📶 Progresso de Hoje</div>
                    <div class="progress-row">
                        <div style="flex: 1;">
                            <div class="progress-bar-container">
                                <div class="progress-bar-fill" style="width: {pct_progresso}%;"></div>
                            </div>
                        </div>
                        <div class="progress-counter">{pct_progresso}%</div>
                    </div>
                    <div class="progress-text">{n_concluidos}/{n_total_hoje} pedidos movimentados</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        busca = st.text_input(
            "🔎 Busca Rápida:",
            placeholder="Filtrar dados...")

        df_grid = df_f.copy()
        if st.session_state.filtro_kpi_admin != "TODOS":
            if st.session_state.filtro_kpi_admin == "HOJE":
                df_grid = df_grid[df_grid['DATA_OBJ'] == hoje_br]
            else:
                df_grid = df_grid[df_grid['STATUS_DISPLAY'].str.contains(
                    st.session_state.filtro_kpi_admin, case=False)]

        df_grid['COMPROVANTE'] = df_grid['FOTO_URL']

        # 🔥 MOTOR DE ORDENAÇÃO: RANKING DE 1 A 7 🔥
        def definir_prioridade_cco(status_str):
            s = str(status_str).upper()
            if 'PENDENTE' in s or 'AGUARDANDO' in s:
                return 1
            if 'ROTA DE COLETA' in s:
                return 2
            if 'COLETADO' in s:
                return 3
            if 'FRUSTRADA' in s or 'PROBLEMA' in s or 'RECUSA' in s or 'ATRASADO' in s:
                return 4
            if 'CONFERIDO' in s:
                return 5
            if 'ROTA DE ENTREGA' in s or 'EM ROTA' in s:
                return 6
            if 'ENTREGUE' in s:
                return 7
            return 8

        df_grid['PRIORIDADE'] = df_grid['STATUS_DISPLAY'].apply(
            definir_prioridade_cco)
        # Ordena PRIMEIRO por Data (Mais recente no topo) e DEPOIS por
        # Prioridade
        df_grid = df_grid.sort_values(by=['DATA_OBJ', 'PRIORIDADE', 'PEDIDO'], ascending=[
                                    False, True, False]).drop(columns=['PRIORIDADE'])

        if busca:
            mask = df_grid.apply(
                lambda row: row.astype(str).str.contains(
                    busca, case=False).any(), axis=1)
            df_grid = df_grid[mask]

        dict_nomes_grid = {
            str(
                r.get(
                    'LOGIN DO AGENTE',
                    '')).strip().lower(): str(
                r.get(
                    'NOME DO AGENTE',
                    '')).strip() for _,
            r in DF_AGENTES.iterrows() if str(
                        r.get(
                            'LOGIN DO AGENTE',
                            '')).strip()}
        df_grid['AGENTE_NOME'] = df_grid['AGENTE_RAW'].apply(
            lambda x: dict_nomes_grid.get(
                str(x).strip().lower(),
                str(x).upper()) if str(x).strip() else "")

        # ADICIONAMOS A COLUNA 'ACAO' AQUI PARA PADRONIZAR COM O PORTAL DO
        # CLIENTE
        df_grid['ACAO'] = '🔍 Detalhes'
        colunas_mostrar = [
            'DATA',
            'PEDIDO',
            'TOMADOR',
            'LABORATORIO',
            'CIDADE',
            'STATUS_DISPLAY',
            'DATA_LIMITE',
            'DATA_ENTREGA',
            'COMPROVANTE',
            'AGENTE_NOME',
            'AGENTE_RAW',
            'DETALHES']

        df_grid_final = df_grid[[
            c for c in colunas_mostrar if c in df_grid.columns]].dropna(subset=['PEDIDO'])

        df_grid_final = df_grid_final[df_grid_final['PEDIDO'].astype(
            str).str.strip() != ""]
        for col in df_grid_final.columns:
            df_grid_final[col] = df_grid_final[col].astype(str).replace(
                ["nan", "NaN", "None", "none", "<NA>", "NaT"], "")

        df_grid_final['COMPROVANTE'] = df_grid_final['COMPROVANTE'].apply(
            lambda x: x if str(x).startswith("http") else "")

        # 🔥 VISUAL OTIMIZADO: DATAS CURTAS MANTIDAS 🔥
        for col in ['DATA', 'DATA_LIMITE', 'DATA_ENTREGA']:
            if col in df_grid_final.columns:
                df_grid_final[col] = df_grid_final[col].astype(str).apply(
                    lambda x: x.split(' ')[0] if x and str(x).lower() != 'nan' else '')
                df_grid_final[col] = df_grid_final[col].astype(str).apply(
                    lambda x: re.sub(r'/20(\d{2})(?!\d)', r'/\1', x))

        df_grid_final = df_grid_final.reset_index(drop=True)

        if df_grid_final.empty:
            st.warning(
                f"Nenhum pedido encontrado com os filtros atuais. Total carregado: {len(df_raw)} | Após filtros: {len(df_f)}."
            )

        st.markdown(
            f"<p style='color:#64748B; font-size:13px; margin-bottom: 5px;'>Selecione as caixas na tabela para libertar as ações no topo. Marque a caixa e use o botão 'Ver Detalhes' para abrir o pop-up da linha.</p>",
            unsafe_allow_html=True)

        box_botoes = st.empty()
        st.markdown("<br>", unsafe_allow_html=True)

        link_jscode = JsCode("""
        class EmojiLinkRenderer {
        init(params) {
            this.eGui = document.createElement('div');
            this.eGui.style.cssText = 'display: flex; justify-content: center; align-items: center; height: 100%;';
            if (params.value && params.value !== '') {
            let a = document.createElement('a');
            a.href = params.value;
            a.target = '_blank';
            a.innerHTML = '📷';
            a.title = 'Clique para abrir o anexo';
            a.style.cssText = 'text-decoration: none; font-size: 20px; transition: transform 0.2s; cursor: pointer;';

            let previewContainer = document.createElement('div');
            previewContainer.style.cssText = 'position: fixed; display: none; z-index: 99999; pointer-events: none;';

            let preview = document.createElement('img');
            preview.src = params.value;
            preview.style.cssText = 'max-width: 350px; max-height: 350px; border-radius: 12px; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.4); border: 3px solid white; display: block;';

            let timeOverlay = document.createElement('div');
            let statusText = params.data && params.data.STATUS_DISPLAY ? params.data.STATUS_DISPLAY : '';
            timeOverlay.innerHTML = statusText;
            timeOverlay.style.cssText = 'position: absolute; bottom: 10px; left: 50%; transform: translateX(-50%); background: rgba(15, 23, 42, 0.9); color: #fff; padding: 5px 12px; border-radius: 99px; font-family: Inter, sans-serif; font-size: 12px; font-weight: bold; white-space: nowrap; box-shadow: 0 4px 10px rgba(0,0,0,0.3);';

            previewContainer.appendChild(preview);
            if (statusText) { previewContainer.appendChild(timeOverlay); }
            document.body.appendChild(previewContainer);

            a.onmouseover = (e) => {
                a.style.transform = 'scale(1.3)';
                previewContainer.style.display = 'block';
                previewContainer.style.left = (e.clientX + 20) + 'px';
                previewContainer.style.top = (e.clientY + 20) + 'px';
            };
            a.onmousemove = (e) => {
                previewContainer.style.left = (e.clientX + 20) + 'px';
                previewContainer.style.top = (e.clientY + 20) + 'px';
            };
            a.onmouseout = () => {
                a.style.transform = 'scale(1)';
                previewContainer.style.display = 'none';
            };

            this.eGui.appendChild(a);
            this.previewElement = previewContainer;
            }
        }
        getGui() { return this.eGui; }
        destroy() { if (this.previewElement && this.previewElement.parentNode) { this.previewElement.parentNode.removeChild(this.previewElement); } }
        }
        """)

        status_jscode = JsCode("""
        class StatusBadgeRenderer {
        init(params) {
            this.eGui = document.createElement('div');
            this.eGui.style.cssText = 'display: flex; align-items: center; height: 100%;';
            let badge = document.createElement('span');
            badge.style.cssText = 'display: inline-flex; align-items: center; justify-content: center; padding: 4px 10px; border-radius: 99px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; height: 22px;';
            let text = params.value || '';
            let status = text.toUpperCase();

            if (status.includes('ENTREGUE') || status.includes('CONFERIDO')) { badge.style.backgroundColor = '#dcfce7'; badge.style.color = '#166534'; badge.style.border = '1px solid #bbf7d0'; }
            else if (status.includes('FRUSTRADA') || status.includes('PROBLEMA') || status.includes('ATRASADO') || status.includes('RECUSA')) { badge.style.backgroundColor = '#fee2e2'; badge.style.color = '#991b1b'; badge.style.border = '1px solid #fecaca'; }
            else if (status.includes('COLETADO') || status.includes('ROTA')) { badge.style.backgroundColor = '#dbeafe'; badge.style.color = '#1e40af'; badge.style.border = '1px solid #bfdbfe'; }
            else if (status.includes('PENDENTE') || status.includes('AGUARDANDO')) { badge.style.backgroundColor = '#fef3c7'; badge.style.color = '#b45309'; badge.style.border = '1px solid #fde68a'; }
            else { badge.style.backgroundColor = '#f1f5f9'; badge.style.color = '#475569'; badge.style.border = '1px solid #e2e8f0'; }

            badge.innerText = text;
            this.eGui.appendChild(badge);
        }
        getGui() { return this.eGui; }
        }
        """)

        gb = GridOptionsBuilder.from_dataframe(df_grid_final)
        gb.configure_pagination(
            paginationAutoPageSize=False,
            paginationPageSize=15)
        gb.configure_grid_options(
            pagination=True,
            suppressPaginationPanel=False,
            domLayout='normal',
            alwaysShowVerticalScroll=True,
            alwaysShowHorizontalScroll=True
        )
        gb.configure_default_column(
            resizable=True, filterable=True, sortable=True)

        gb.configure_selection(
            'multiple',
            use_checkbox=True,
            header_checkbox=True,
            header_checkbox_filtered_only=True,
            suppressRowClickSelection=False)

        gb.configure_column("DATA", header_name="📅 Data", width=100)
        gb.configure_column("PEDIDO", header_name="📦 Pedido", width=100)
        gb.configure_column("TOMADOR", header_name="🏢 Tomador", width=140)
        gb.configure_column(
            "LABORATORIO",
            header_name="🔬 Ponto de Coleta",
            width=220)
        gb.configure_column("CIDADE", header_name="📍 Cidade", width=140)
        gb.configure_column(
            "STATUS_DISPLAY",
            header_name="🚦 Status",
            cellRenderer=status_jscode,
            width=160)
        gb.configure_column("DATA_LIMITE", header_name="🎯 Previsão", width=100)
        gb.configure_column("DATA_ENTREGA", header_name="🏁 Entrega", width=100)
        gb.configure_column(
            "COMPROVANTE",
            header_name="📎 Anexo",
            cellRenderer=link_jscode,
            width=90)
        gb.configure_column(
            "AGENTE_NOME",
            header_name="👤 Motorista",
            width=130)
        gb.configure_column("AGENTE_RAW", hide=True)

        # 🔥 COLUNA DE ATUALIZAÇÕES RESTAURADA COM TEXTO ORIGINAL 🔥
        gb.configure_column(
            "DETALHES",
            header_name="💬 Atualizações",
            width=250)

        gridOptions = gb.build()

        custom_css = {
            ".ag-theme-alpine": {
                "--ag-font-family": "Inter, sans-serif",
                "--ag-font-size": "13px",
                "--ag-row-height": "40px",
                "--ag-header-height": "44px",
                "background-color": "#ffffff !important",
                "border": "1px solid #dbe3ef",
                "border-radius": "12px",
                "overflow": "hidden",
                "box-shadow": "0 8px 20px rgba(15, 23, 42, 0.07)"
            },
            ".ag-root-wrapper": {"background-color": "#ffffff !important"},
            ".ag-root-wrapper-body": {"background-color": "#ffffff !important"},
            ".ag-body-viewport": {"background-color": "#ffffff !important"},
            ".ag-header": {
                "background": "linear-gradient(180deg, #f8fafc 0%, #e2e8f0 100%) !important",
                "border-bottom": "1px solid #cbd5e1 !important"
            },
            ".ag-header-cell": {
                "border-right": "1px solid #dbe3ef !important",
                "padding-top": "5px !important",
                "padding-bottom": "5px !important"
            },
            ".ag-header-cell-text": {
                "color": "#0f172a !important",
                "font-weight": "800 !important",
                "font-size": "12px !important",
                "letter-spacing": "0.35px !important",
                "text-transform": "uppercase !important"
            },
            ".ag-row": {
                "border-bottom": "1px solid #eef2f7 !important",
                "height": "40px !important",
                "transition": "background-color 0.2s ease"
            },
            ".ag-row:hover": {
                "background-color": "#dbeafe !important",
                "cursor": "pointer",
                "box-shadow": "inset 3px 0 0 #2563eb !important"
            },
            ".ag-row-odd": {"background": "linear-gradient(90deg, #ffffff 0%, #fcfdff 100%) !important"},
            ".ag-row-even": {"background": "linear-gradient(90deg, #f8fafc 0%, #f1f5f9 100%) !important"},
            ".ag-cell": {
                "display": "flex !important",
                "align-items": "center !important",
                "border-right": "1px solid #eef2f7 !important",
                "font-size": "13px !important"
            },
            ".ag-cell-focus": {"border": "none !important", "outline": "none !important"},
            ".ag-paging-panel": {
                "background": "#f8fafc !important",
                "border-top": "1px solid #dbe3ef !important",
                "padding": "8px 10px !important"
            }
        }

        tabela_renderizada = AgGrid(
            df_grid_final,
            gridOptions=gridOptions,
            theme="alpine",
            columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS,
            height=550,
            allow_unsafe_jscode=True,
            custom_css=custom_css,
            update_mode="SELECTION_CHANGED"
        )

        sel_list = tabela_renderizada.get('selected_rows', [])
        if sel_list is not None and len(sel_list) > 0:
            linhas_selecionadas = pd.DataFrame(sel_list)
        else:
            linhas_selecionadas = pd.DataFrame(columns=df_grid_final.columns)

        p_ids = linhas_selecionadas["PEDIDO"].astype(
            str).tolist() if not linhas_selecionadas.empty else []
        tem_sel = len(p_ids) > 0

        # 🔥 PREENCHENDO A BARRA DE AÇÕES NO TOPO DA TELA 🔥
        st.markdown("""
            <style>
                /* 1. Padroniza TODOS os botões nativos e popovers para a paleta azul da sidebar */
                div.stButton:not([class*="st-key-kpi"]):not([class*="st-key-btn_chamados"]):not([class*="st-key-btn_sair_sidebar"]) > button[kind="secondary"],
                div[data-testid="stPopover"] > div > button,
                div[data-testid="stPopover"] > button {
                    background: linear-gradient(180deg, #eff6ff 0%, #dbeafe 100%) !important;
                    color: #0f172a !important;
                    border: 1px solid #93c5fd !important;
                    border-radius: 10px !important;
                    font-weight: 700 !important;
                    font-size: 14px !important;
                    transition: all 0.2s ease !important;
                    box-shadow: 0 4px 10px rgba(37, 99, 235, 0.10) !important;
                    min-height: 42px !important;
                }
                        
                /* Efeito ao passar o mouse */
                div.stButton:not([class*="st-key-kpi"]):not([class*="st-key-btn_chamados"]):not([class*="st-key-btn_sair_sidebar"]) > button[kind="secondary"]:hover,
                div[data-testid="stPopover"] > div > button:hover,
                div[data-testid="stPopover"] > button:hover {
                    background: linear-gradient(180deg, #dbeafe 0%, #bfdbfe 100%) !important;
                    border-color: #60a5fa !important;
                    color: #0f172a !important;
                    box-shadow: 0 8px 18px rgba(37, 99, 235, 0.18) !important;
                    transform: translateY(-1px) !important;
                }
                        
                div.stButton:not([class*="st-key-kpi"]):not([class*="st-key-btn_chamados"]):not([class*="st-key-btn_sair_sidebar"]) > button[kind="secondary"]:active,
                div[data-testid="stPopover"] > div > button:active,
                div[data-testid="stPopover"] > button:active {
                    transform: translateY(0px) !important;
                }
                        
                /* 2. Botões internos de AÇÃO/CONFIRMAÇÃO dentro dos popovers (Verdes para destaque) */
                div[data-testid="stPopoverBody"] button,
                div[data-testid="popover"] button {
                    background-color: #10b981 !important; /* Verde */
                    color: white !important;
                    border: 1px solid #059669 !important;
                    transform: none !important;
                    font-weight: bold !important;
                }
                div[data-testid="stPopoverBody"] button:hover,
                div[data-testid="popover"] button:hover {
                    background-color: #059669 !important;
                    border-color: #059669 !important;
                }
                        
                /* Layout dos Popovers e Forms nativos */
                div[data-testid="stPopoverBody"], div[data-testid="popover"] {
                    border-radius: 12px !important;
                    box-shadow: 0 10px 25px rgba(0,0,0,0.15) !important;
                }
                div.stForm {
                    border: none !important;
                    border-radius: 8px !important;
                }
            </style>
        """, unsafe_allow_html=True)
                
        with box_botoes.container():
            col_b0, col_b1, col_b2, col_b3, col_b4, col_b5, col_b6 = st.columns(7)

            with col_b0:
                # O BOTÃO AGORA ABRE A TELA DIRETAMENTE, SEM USAR A MEMÓRIA DO SISTEMA
                if st.button(
                    "🔍 Ver Detalhes",
                    use_container_width=True,
                        type="secondary"):
                    if not tem_sel or len(p_ids) > 1:
                        st.warning(
                            "Selecione apenas 1 pedido na caixinha para ver os detalhes!")
                    else:
                        linha_dict = df_raw[df_raw['PEDIDO'] == p_ids[0]].iloc[0].to_dict()
                        modal_detalhes_pedido(linha_dict)

            with col_b1.popover("🛎️ Cobrar", use_container_width=True):
                if not tem_sel:
                    st.warning("Selecione um pedido!")
                else:
                    with st.form("form_cobrar_grid"):
                        st.markdown("Enviar lembrete amigável?")
                        if st.form_submit_button("📲 Mandar Cobrança Agora", type="secondary", use_container_width=True):
                            agentes_selecionados = list(set(linhas_selecionadas['AGENTE_RAW'].tolist()))
                            for ag in agentes_selecionados:
                                login_ag = str(ag).lower().strip()
                                tel_row = DF_AGENTES[DF_AGENTES['LOGIN DO AGENTE'] == login_ag]
                                if not tel_row.empty:
                                    tel = tel_row.iloc[0]['TELEFONE']
                                    nome = tel_row.iloc[0]['NOME DO AGENTE']
                                    qtd_ag = len(linhas_selecionadas[linhas_selecionadas['AGENTE_RAW'] == ag])
                                    msg_ind = f"Olá {nome}, a IGO Logística informa que possui {qtd_ag} pedidos pendentes na rota de hoje. Lembre-se de dar baixa. Bom trabalho!"
                                    if enviar_whatsapp_zapi(tel, msg_ind):
                                        st.success(f"Enviado para {nome}!")
                                    else:
                                        st.error(f"Erro ao enviar para {nome}")
                                else:
                                    st.error(f"Telefone do agente {login_ag} não encontrado.")

            with col_b2.popover("📲 Baixa", use_container_width=True):
                if not tem_sel:
                    st.warning("Selecione um pedido!")
                else:
                    with st.form("form_baixa_manual"):
                        status_baixa = st.selectbox(
                            "Novo Status:", [
                                "ENTREGUE ✅", "COLETADO 📦", "FRUSTRADA ❌", "PROBLEMA 🚨", "CANCELADO ❌", "PENDENTE ⏳"])
                        data_baixa = st.date_input("Data:", format="DD/MM/YYYY", value=hoje_br)
                        tem_entregue = df_f[df_f['PEDIDO'].isin(p_ids)]['STATUS_DISPLAY'].str.contains('Entregue').any()
                        senha_reversao = ""
                        if tem_entregue:
                            st.warning("⚠️ Desfazendo pedido já **ENTREGUES**.")
                            senha_reversao = st.text_input("🔑 Senha:", type="password")

                        if st.form_submit_button("Confirmar Nova Baixa", type="secondary", use_container_width=True):
                            with st.spinner("A atualizar C.C.O. e a limpar a App do Motorista..."):
                                status_limpo = status_baixa.split(" ")[0].upper()
                                if tem_entregue and status_limpo != 'ENTREGUE' and senha_reversao != '123':
                                    st.error("❌ Senha incorreta!")
                                else:
                                    try:
                                        aba = planilha_db.worksheet("Memoria_Sistema")
                                        dados_nuvem = aba.get_all_values()
                                        if len(dados_nuvem) > 1:
                                            df_nuvem = pd.DataFrame(dados_nuvem[1:], columns=dados_nuvem[0])
                                            for pid in p_ids:
                                                mask = df_nuvem['PEDIDO'] == pid
                                                df_nuvem.loc[mask, 'STATUS'] = status_limpo
                                                if status_limpo == "ENTREGUE":
                                                    df_nuvem.loc[mask, 'DATA_ENTREGA'] = data_baixa.strftime("%d/%m/%Y")
                                                elif status_limpo in ["PENDENTE", "COLETADO"]:
                                                    df_nuvem.loc[mask, 'DATA_ENTREGA'] = ""
                                            aba.update("A1", [df_nuvem.columns.tolist()] + df_nuvem.fillna("").astype(str).values.tolist())

                                        try:
                                            aba_app = planilha_db.worksheet("App_Tarefas")
                                            dados_app = aba_app.get_all_values()
                                            if len(dados_app) > 1:
                                                df_app = pd.DataFrame(dados_app[1:], columns=dados_app[0])
                                                for pid in p_ids:
                                                    mask_app = df_app['PEDIDO'] == pid
                                                    if mask_app.any():
                                                        df_app.loc[mask_app, 'STATUS'] = status_limpo
                                                        if status_limpo == "ENTREGUE" and 'DATA_ENTREGA' in df_app.columns:
                                                            df_app.loc[mask_app, 'DATA_ENTREGA'] = data_baixa.strftime("%d/%m/%Y %H:%M:%S")

                                                if 'PEDIDO' in df_app.columns:
                                                    df_app = df_app.drop_duplicates(subset=['PEDIDO'], keep='last')

                                                aba_app.clear()
                                                aba_app.update("A1", [df_app.columns.tolist()] + df_app.fillna("").astype(str).values.tolist())
                                        except Exception:
                                            pass

                                        st.session_state.ui_toast = {'msg': "Atualizado no CCO e App sincronizada!", 'icon': "🎉"}
                                        carregar_dados_completos.clear()
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Erro: {e}")

            with col_b3.popover("🔄 Trocar", use_container_width=True):
                if not tem_sel:
                    st.warning("Selecione um pedido!")
                else:
                    with st.form("form_troca_motorista"):
                        tem_entregue = df_f[df_f['PEDIDO'].isin(p_ids)]['STATUS_DISPLAY'].str.contains('Entregue').any()
                        if tem_entregue:
                            st.error("⚠️ Impossível trocar motorista de ENTREGUES.")
                        else:
                            logins_disp = sorted(DF_AGENTES['LOGIN DO AGENTE'].unique().tolist()) if not DF_AGENTES.empty else []
                            novo_mot = st.selectbox("Novo Agente:", logins_disp)
                            nova_data_troca = st.date_input("Nova Data:", format="DD/MM/YYYY", value=hoje_br)
                            if st.form_submit_button("Confirmar Troca", type="secondary", use_container_width=True):
                                with st.spinner("A atualizar rotas e motoristas..."):
                                    try:
                                        aba = planilha_db.worksheet("Memoria_Sistema")
                                        dados_nuvem = aba.get_all_values()
                                        if len(dados_nuvem) > 1:
                                            df_nuvem = pd.DataFrame(dados_nuvem[1:], columns=dados_nuvem[0])
                                            if 'ZAP_ENVIADO' not in df_nuvem.columns:
                                                df_nuvem['ZAP_ENVIADO'] = ""
                                            lista_app_troca = []
                                            for pid in p_ids:
                                                mask = df_nuvem['PEDIDO'] == pid
                                                if mask.any():
                                                    df_nuvem.loc[mask, 'AGENTE_RAW'] = novo_mot
                                                    df_nuvem.loc[mask, 'ZAP_ENVIADO'] = ""
                                                    l_app = df_nuvem[mask].iloc[0]
                                                    lista_app_troca.append({
                                                            'PEDIDO': pid, 'MOTORISTA': novo_mot, 'ENDERECO': l_app.get('ENDERECO', ''), 'NUMERO': l_app.get('NUMERO', ''), 'BAIRRO': l_app.get('BAIRRO', ''), 'CIDADE': l_app.get('CIDADE', ''), 'CEP': l_app.get('CEP', ''), 'LABORATORIO': l_app.get('LABORATORIO', ''), 'TOMADOR': l_app.get('TOMADOR', '')})
                                            aba.update("A1", [df_nuvem.columns.tolist()] + df_nuvem.fillna("").astype(str).values.tolist())
                                            if lista_app_troca:
                                                substituir_pedido_appsheet(lista_app_troca)
                                        st.success("🎉 Troca realizada preservando o estado original!")
                                        time.sleep(1.5)
                                        carregar_dados_completos.clear()
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Erro: {e}")

            with col_b4.popover("👯 Clonar", use_container_width=True):
                if not tem_sel:
                    st.warning("Selecione um pedido!")
                else:
                    with st.form("form_clonar_pedido"):
                        clone_data = st.date_input("Nova Data de Embarque:", format="DD/MM/YYYY", value=hoje_br)
                        logins_disp = sorted(DF_AGENTES['LOGIN DO AGENTE'].unique().tolist()) if not DF_AGENTES.empty else []
                        clone_mot = st.selectbox("Agente Designado:", ["Manter Original"] + logins_disp)
                        if st.form_submit_button("Confirmar Clone", type="secondary"):
                            with st.spinner("👯 A clonar pedidos e organizar rotas..."):
                                try:
                                    aba = planilha_db.worksheet("Memoria_Sistema")
                                    dados_nuvem = aba.get_all_values()
                                    if len(dados_nuvem) > 1:
                                        df_nuvem = pd.DataFrame(dados_nuvem[1:], columns=dados_nuvem[0])
                                        if 'ZAP_ENVIADO' not in df_nuvem.columns:
                                            df_nuvem['ZAP_ENVIADO'] = ""
            
                                        prox_id = obter_proximo_id(df_nuvem)
                                        clones_app = []
                                        for pid in p_ids:
                                            if pid in df_nuvem['PEDIDO'].values:
                                                l_orig = df_nuvem[df_nuvem['PEDIDO'] == pid].iloc[0].copy()
                                            novo_id = str(prox_id)
                                            prox_id += 1
                                            l_orig['PEDIDO'] = novo_id
                                            l_orig['DATA'] = clone_data.strftime("%d/%m/%Y")

                                            l_orig['STATUS'] = "PENDENTE"
                                            l_orig['DATA_ENTREGA'] = ""
                                            l_orig['FOTO'] = ""
                                            l_orig['ROMANEIO'] = ""
                                            l_orig['ZAP_ENVIADO'] = ""
                                            l_orig['FATURA'] = ""

                                            if clone_mot != "Manter Original":
                                                l_orig['AGENTE_RAW'] = clone_mot
                                            prazo = calcular_sla_dias(str(l_orig.get('UF', 'SP')), str(l_orig.get('CIDADE', '')), str(l_orig.get('TOMADOR', '')))
                                            l_orig['PRAZO_DIAS'] = str(prazo)
                                            l_orig['DATA_LIMITE'] = str(calcular_data_limite(l_orig['DATA'], prazo))
                                            l_orig = l_orig.astype(str)
                                            df_nuvem = pd.concat([df_nuvem, pd.DataFrame([l_orig])], ignore_index=True)
                                            if str(l_orig.get('AGENTE_RAW', '')).strip():
                                                clones_app.append({
                                                        'PEDIDO': novo_id, 'MOTORISTA': l_orig['AGENTE_RAW'], 'ENDERECO': l_orig.get('ENDERECO', ''), 'NUMERO': l_orig.get('NUMERO', ''), 'BAIRRO': l_orig.get('BAIRRO', ''), 'CIDADE': l_orig.get('CIDADE', ''), 'CEP': l_orig.get('CEP', ''), 'LABORATORIO': l_orig.get('LABORATORIO', ''), 'TOMADOR': l_orig.get('TOMADOR', '')})
                                    aba.update("A1", [df_nuvem.columns.tolist()] + df_nuvem.fillna("").astype(str).values.tolist())
                                    if clones_app:
                                        despachar_para_appsheet(clones_app)
                                    st.success("🎉 Clonado!")
                                    time.sleep(1)
                                    carregar_dados_completos.clear()
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro: {e}")

            with col_b5.popover("🗑️ Excluir", use_container_width=True):
                if not tem_sel:
                    st.warning("Selecione um pedido!")
                else:
                    with st.form("form_excluir_grid"):
                        senha_del = st.text_input("🔑 Senha Master:", type="password")
                        if st.form_submit_button("Confirmar Exclusão", type="secondary"):
                            if senha_del == "123":
                                with st.spinner("A apagar registos da base de dados..."):
                                    try:
                                        aba = planilha_db.worksheet("Memoria_Sistema")
                                        dados_nuvem = aba.get_all_values()
                                        if len(dados_nuvem) > 1:
                                            df_nuvem = pd.DataFrame(dados_nuvem[1:], columns=dados_nuvem[0])
                                            df_nuvem = df_nuvem[~df_nuvem['PEDIDO'].isin(p_ids)]
                                            aba.clear()
                                            aba.update("A1", [df_nuvem.columns.tolist()] + df_nuvem.fillna("").astype(str).values.tolist())
                                        try:
                                            aba_app = planilha_db.worksheet("App_Tarefas")
                                            dados_app = aba_app.get_all_values()
                                            if len(dados_app) > 1:
                                                df_app = pd.DataFrame(dados_app[1:], columns=dados_app[0])
                                                df_app = df_app[~df_app['PEDIDO'].isin(p_ids)]
                                                aba_app.clear()
                                                aba_app.update("A1", [df_app.columns.tolist()] + df_app.fillna("").astype(str).values.tolist())
                                        except Exception:
                                            pass
                                        st.success("🗑️ Apagado!")
                                        time.sleep(1)
                                        carregar_dados_completos.clear()
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Erro: {e}")

            if col_b6.button("🔄 Atualizar", use_container_width=True, type="secondary"):
                    with st.spinner("Sincronizando..."):
                        carregar_dados_completos.clear()
                        st.toast("Dados atualizados com sucesso!", icon="🔄")
                        time.sleep(0.5)
                        st.rerun()

# =============================================================================
# 💰 MÓDULO 2: FATURAMENTO MASTER (LENTE DE RAIO-X E ANTI-ERROS)
# =============================================================================
elif menu == "💰 Faturamento":
    st.markdown(
        "<div class='dinamic-border'><h3 class='dinamic-text' style='margin:0;'>💰 Gestão Financeira Master</h3></div>",
        unsafe_allow_html=True)

    # =========================================================================
    # ⚙️ RECURSOS VISUAIS GLOBAIS DO AGGRID E FILTROS PREMIUM
    # =========================================================================
    st.markdown("""
        <style>
        div[data-baseweb="tab-list"] {
            gap: 14px;
            margin-bottom: 16px;
            align-items: stretch;
        }
        div[data-baseweb="tab"] {
            background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%) !important;
            border: 1px solid #dbe3ef !important;
            border-radius: 12px !important;
            color: #334155 !important;
            font-weight: 700 !important;
            min-height: 50px !important;
            padding: 0 18px !important;
            line-height: 1.25 !important;
            letter-spacing: 0.15px !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04) !important;
            transition: all 0.2s ease !important;
        }
        button[role="tab"] {
            padding: 0 18px !important;
            min-height: 50px !important;
            line-height: 1.25 !important;
        }
        button[role="tab"] p {
            margin: 0 !important;
            line-height: 1.25 !important;
            white-space: nowrap !important;
        }
        div[data-baseweb="tab"]:hover {
            border-color: #93c5fd !important;
            color: #0f172a !important;
            transform: translateY(-1px);
            box-shadow: 0 6px 16px rgba(37, 99, 235, 0.10) !important;
        }
        button[role="tab"][aria-selected="true"] {
            background: linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%) !important;
            border-color: #1d4ed8 !important;
            border-radius: 12px !important;
            color: #ffffff !important;
            box-shadow: 0 10px 20px rgba(37, 99, 235, 0.22) !important;
            overflow: hidden !important;
            padding: 0 20px !important;
        }
        button[role="tab"][aria-selected="true"] p {
            letter-spacing: 0.2px !important;
            line-height: 1.3 !important;
        }
        div[data-testid="stSelectbox"] > div[data-baseweb="select"] > div,
        div[data-testid="stMultiSelect"] > div[data-baseweb="select"] > div,
        div[data-testid="stTextInput"] input,
        div[data-testid="stDateInput"] input,
        div[data-testid="stDateInput"] button,
        div[data-testid="stTextArea"] textarea {
            background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%) !important;
            border-radius: 10px !important;
            border: 1px solid #cbd5e1 !important;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05) !important;
        }
        div[data-testid="stSelectbox"] > div[data-baseweb="select"] > div:focus,
        div[data-testid="stTextInput"] input:focus,
        div[data-testid="stDateInput"] input:focus,
        div[data-testid="stTextArea"] textarea:focus {
            border-color: #60a5fa !important;
            box-shadow: 0 0 0 1px #93c5fd !important;
        }
        div[data-testid="stForm"],
        div[data-testid="stExpander"],
        div[data-testid="stDataFrame"],
        div[data-testid="stVerticalBlockBorderWrapper"],
        div[data-testid="stAlert"] {
            border-radius: 14px !important;
        }
        div[data-testid="stExpander"] {
            border: 1px solid #dbe3ef !important;
            background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%) !important;
            box-shadow: 0 6px 16px rgba(15, 23, 42, 0.05) !important;
        }
        div[data-testid="stFormSubmitButton"] > button,
        div.stButton > button:not([kind="primary"]),
        div[data-testid="stPopover"] > div > button,
        div[data-testid="stPopover"] > button {
            background: linear-gradient(180deg, #eff6ff 0%, #dbeafe 100%) !important;
            color: #0f172a !important;
            border: 1px solid #93c5fd !important;
            border-radius: 10px !important;
            font-weight: 700 !important;
            box-shadow: 0 4px 10px rgba(37, 99, 235, 0.10) !important;
            min-height: 42px !important;
            transition: all 0.2s ease !important;
        }
        div[data-testid="stFormSubmitButton"] > button:hover,
        div.stButton > button:not([kind="primary"]):hover,
        div[data-testid="stPopover"] > div > button:hover,
        div[data-testid="stPopover"] > button:hover {
            background: linear-gradient(180deg, #dbeafe 0%, #bfdbfe 100%) !important;
            border-color: #60a5fa !important;
            box-shadow: 0 8px 18px rgba(37, 99, 235, 0.18) !important;
            transform: translateY(-1px) !important;
        }
        div.stButton > button[kind="primary"],
        div[data-testid="stFormSubmitButton"] > button[kind="primary"] {
            background: linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%) !important;
            border: 1px solid #1d4ed8 !important;
            color: #ffffff !important;
            box-shadow: 0 10px 20px rgba(37, 99, 235, 0.22) !important;
        }
        div.stButton > button[kind="primary"]:hover,
        div[data-testid="stFormSubmitButton"] > button[kind="primary"]:hover {
            background: linear-gradient(135deg, #0284c7 0%, #1d4ed8 100%) !important;
            border-color: #1e40af !important;
            color: #ffffff !important;
        }
        .ag-theme-alpine {
            --ag-font-family: Inter, sans-serif;
            --ag-font-size: 13px;
            --ag-row-height: 40px;
            --ag-header-height: 44px;
            border: 1px solid #dbe3ef !important;
            border-radius: 12px !important;
            overflow: hidden !important;
            box-shadow: 0 8px 20px rgba(15, 23, 42, 0.07) !important;
            background-color: #ffffff !important;
        }
        .ag-theme-alpine .ag-root-wrapper,
        .ag-theme-alpine .ag-root-wrapper-body,
        .ag-theme-alpine .ag-body-viewport {
            background-color: #ffffff !important;
        }
        .ag-theme-alpine .ag-header {
            background: linear-gradient(180deg, #f8fafc 0%, #e2e8f0 100%) !important;
            border-bottom: 1px solid #cbd5e1 !important;
        }
        .ag-theme-alpine .ag-header-cell {
            border-right: 1px solid #dbe3ef !important;
            padding-top: 5px !important;
            padding-bottom: 5px !important;
        }
        .ag-theme-alpine .ag-header-cell-text {
            color: #0f172a !important;
            font-weight: 800 !important;
            font-size: 12px !important;
            letter-spacing: 0.35px !important;
            text-transform: uppercase !important;
        }
        .ag-theme-alpine .ag-row {
            border-bottom: 1px solid #eef2f7 !important;
            transition: background-color 0.2s ease !important;
        }
        .ag-theme-alpine .ag-row:hover {
            background-color: #dbeafe !important;
            box-shadow: inset 3px 0 0 #2563eb !important;
        }
        .ag-theme-alpine .ag-row-odd {
            background: linear-gradient(90deg, #ffffff 0%, #fcfdff 100%) !important;
        }
        .ag-theme-alpine .ag-row-even {
            background: linear-gradient(90deg, #f8fafc 0%, #f1f5f9 100%) !important;
        }
        .ag-theme-alpine .ag-cell {
            display: flex !important;
            align-items: center !important;
            border-right: 1px solid #eef2f7 !important;
        }
        .ag-theme-alpine .ag-paging-panel {
            background: #f8fafc !important;
            border-top: 1px solid #dbe3ef !important;
            padding: 8px 10px !important;
        }
        </style>
    """, unsafe_allow_html=True)

    status_jscode_fat = JsCode("""
    class StatusBadgeRenderer {
    init(params) {
        this.eGui = document.createElement('div');
        this.eGui.style.cssText = 'display: flex; align-items: center; height: 100%;';
        let badge = document.createElement('span');
        badge.style.cssText = 'display: inline-flex; align-items: center; justify-content: center; padding: 4px 10px; border-radius: 99px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; height: 22px;';
        let text = params.value || '';
        let status = text.toUpperCase();

        if (status.includes('ENTREGUE') || status.includes('CONFERIDO') || status.includes('PAGO')) { badge.style.backgroundColor = '#dcfce7'; badge.style.color = '#166534'; badge.style.border = '1px solid #bbf7d0'; }
        else if (status.includes('FRUSTRADA') || status.includes('PROBLEMA') || status.includes('ATRASADO') || status.includes('RECUSA')) { badge.style.backgroundColor = '#fee2e2'; badge.style.color = '#991b1b'; badge.style.border = '1px solid #fecaca'; }
        else if (status.includes('COLETADO') || status.includes('ROTA')) { badge.style.backgroundColor = '#dbeafe'; badge.style.color = '#1e40af'; badge.style.border = '1px solid #bfdbfe'; }
        else if (status.includes('PENDENTE') || status.includes('AGUARDANDO')) { badge.style.backgroundColor = '#fef3c7'; badge.style.color = '#b45309'; badge.style.border = '1px solid #fde68a'; }
        else { badge.style.backgroundColor = '#f1f5f9'; badge.style.color = '#475569'; badge.style.border = '1px solid #e2e8f0'; }

        badge.innerText = text;
        this.eGui.appendChild(badge);
    }
    getGui() { return this.eGui; }
    }
    """)

    valor_jscode = JsCode("""
    class ValorRenderer {
        init(params) {
            this.eGui = document.createElement('span');
            let val = parseFloat(params.value);
            if (!isNaN(val)) {
                this.eGui.innerHTML = 'R$ ' + val.toFixed(2).replace('.', ',');
                this.eGui.style.fontWeight = '700';
            } else {
                this.eGui.innerHTML = params.value;
            }
        }
        getGui() { return this.eGui; }
    }
    """)

    custom_css_premium = {
        ".ag-theme-alpine": {
            "--ag-font-family": "Inter, sans-serif",
            "--ag-font-size": "13px",
            "background-color": "#ffffff !important",
            "border": "1px solid #dbe3ef",
            "border-radius": "12px",
            "overflow": "hidden",
            "box-shadow": "0 8px 22px rgba(15, 23, 42, 0.08)"
        },
        ".ag-root-wrapper": {"background-color": "#ffffff !important"},
        ".ag-root-wrapper-body": {"background-color": "#ffffff !important"},
        ".ag-body-viewport": {"background-color": "#ffffff !important"},
        ".ag-header": {
            "background": "linear-gradient(180deg, #f8fafc 0%, #e2e8f0 100%) !important",
            "border-bottom": "1px solid #cbd5e1 !important",
            "min-height": "48px !important"
        },
        ".ag-header-cell": {
            "border-right": "1px solid #dbe3ef !important",
            "padding-top": "6px !important",
            "padding-bottom": "6px !important"
        },
        ".ag-header-cell-text": {
            "color": "#0f172a !important",
            "font-weight": "800 !important",
            "font-size": "12px !important",
            "text-transform": "uppercase !important",
            "letter-spacing": "0.4px !important"
        },
        ".ag-row": {
            "border-bottom": "1px solid #eef2f7 !important",
            "height": "40px !important",
            "transition": "background-color 0.22s ease"
        },
        ".ag-row:hover": {
            "background-color": "#dbeafe !important",
            "cursor": "pointer",
            "box-shadow": "inset 3px 0 0 #2563eb"
        },
        ".ag-row-odd": {"background": "linear-gradient(90deg, #ffffff 0%, #fbfdff 100%) !important"},
        ".ag-row-even": {"background": "linear-gradient(90deg, #f8fafc 0%, #f1f5f9 100%) !important"},
        ".ag-cell": {
            "display": "flex !important",
            "align-items": "center !important",
            "border-right": "1px solid #eef2f7 !important",
            "font-size": "13px !important"
        },
        ".ag-cell-focus": {"border": "none !important", "outline": "none !important"}
    }

    # =========================================================================
    # 🧹 LIMPEZA E PADRONIZAÇÃO DE NOMENCLATURAS DOS TOMADORES
    # =========================================================================
    CLIENTES_ATUALIZADOS = sorted(list(set([c.replace('CAEP', 'SYNVIA').replace('CUNHA', 'GRALAB') for c in CLIENTES_AUTORIZADOS])))

    # 🔥 ABAS DE NAVEGAÇÃO 🔥
    tab_faturar, tab_historico, tab_faturados, tab_tarifas = st.tabs(
        ["📈 Novo Lote de Faturamento", "📜 Livro Caixa e Histórico", "✅ Pedidos Faturados", "💲 Tabela de Tarifas"])

    df_raw = carregar_dados_completos(planilha_db)
    if 'fatura_sucesso' not in st.session_state:
        st.session_state.fatura_sucesso = False

    @st.cache_data(ttl=60)
    def carregar_tabela_precos(tomador):
        if planilha_financeiro is None:
            return pd.DataFrame()
        try:
            def _normalizar_coluna(valor):
                txt = unicodedata.normalize('NFKD', str(valor)).encode('ASCII', 'ignore').decode('utf-8').upper()
                txt = re.sub(r'[^A-Z0-9]+', '_', txt)
                return re.sub(r'_+', '_', txt).strip('_')

            def _normalizar_chave_tomador(valor):
                txt = unicodedata.normalize('NFKD', str(valor)).encode('ASCII', 'ignore').decode('utf-8').upper()
                txt = re.sub(r'[^A-Z0-9]+', ' ', txt)
                return re.sub(r'\s+', ' ', txt).strip()

            def _normalizar_df_tarifas(df_p):
                if df_p.empty:
                    return df_p

                # Padroniza nomes de colunas para suportar layouts diferentes da tabela master.
                df_p.columns = [_normalizar_coluna(c) for c in df_p.columns]

                aliases = {
                    'CIDADE': ['CIDADE_DESTINO', 'MUNICIPIO', 'MUNICIPIO_DESTINO'],
                    'BAIRRO': ['BAIRRO_DESTINO'],
                    'ENDERECO': ['ENDERECO_DESTINO', 'LOGRADOURO', 'RUA'],
                    'VALOR_CHEIO': ['VALOR', 'VALOR_R', 'VALOR_BASE', 'VALOR_UNITARIO'],
                    'MULT_FRUSTRADA': ['MULTIPLICADOR_FRUSTRADA', 'MULT_FRUSTRADA', 'PERC_FRUSTRADA', 'PERCENTUAL_FRUSTRADA'],
                    'PRAZO_DIAS_UTEIS': ['PRAZO_DIAS', 'SLA_DIAS', 'PRAZO_SLA', 'SLA']
                }
                for col_padrao, candidatos in aliases.items():
                    if col_padrao not in df_p.columns:
                        for cand in candidatos:
                            if cand in df_p.columns:
                                df_p[col_padrao] = df_p[cand]
                                break

                for col in ['VALOR_CHEIO', 'MULT_FRUSTRADA', 'PRAZO_DIAS_UTEIS']:
                    if col in df_p.columns:
                        df_p[col] = df_p[col].astype(str).str.replace(',', '.').str.replace('R$', '').str.strip()
                        df_p[col] = pd.to_numeric(df_p[col], errors='coerce').fillna(0.0)
                    else:
                        # Garante colunas mínimas para o cálculo não quebrar.
                        df_p[col] = 0.0

                for col in ['CIDADE', 'BAIRRO', 'ENDERECO']:
                    if col in df_p.columns:
                        df_p[col] = df_p[col].apply(padronizar_texto)
                    else:
                        df_p[col] = ""

                # Chave simplificada para casar cidades com pequenas variações de escrita.
                df_p['CIDADE_KEY'] = df_p['CIDADE'].astype(str).apply(lambda x: re.sub(r'[^A-Z0-9]+', '', x))

                return df_p

            buscado = tomador.replace('CAEP', 'SYNVIA').replace('CUNHA', 'GRALAB') if tomador in ['CAEP', 'CUNHA', 'SYNVIA', 'GRALAB'] else tomador
            buscado = buscado.strip().upper()
            buscado_norm = _normalizar_chave_tomador(buscado)
            aliases_tomador = {buscado_norm}
            if buscado_norm == 'SOUZA CRUZ':
                aliases_tomador.update({'SOUZA CRUZ SA', 'SOUZA CRUZ S A', 'SOUZA CRUZ BRASIL'})

            todas_abas = planilha_financeiro.worksheets()
            mapa_abas = {aba.title.strip().upper(): aba for aba in todas_abas}
            mapa_abas_norm = {_normalizar_chave_tomador(aba.title): aba for aba in todas_abas}

            # 1) Modo legado: uma aba por cliente (comportamento atual)
            if buscado in mapa_abas:
                aba_cli = mapa_abas[buscado]
                dados = aba_cli.get_all_values()
                if len(dados) > 1:
                    return _normalizar_df_tarifas(pd.DataFrame(dados[1:], columns=dados[0]))
            elif buscado_norm in mapa_abas_norm:
                aba_cli = mapa_abas_norm[buscado_norm]
                dados = aba_cli.get_all_values()
                if len(dados) > 1:
                    return _normalizar_df_tarifas(pd.DataFrame(dados[1:], columns=dados[0]))

            # 1.1) Candidatos explícitos para estruturas como Faturamento_Log.
            candidatos_por_tomador = {
                'SOUZA CRUZ': ['SOUZA CRUZ', 'SOUZA_CRUZ', 'SOUZACRUZ', 'SOUZA CRUZ SA', 'FATURAMENTO_LOG', 'FATURAMENTO LOG']
            }
            for nome_cand in candidatos_por_tomador.get(buscado_norm, []):
                nome_cand_norm = _normalizar_chave_tomador(nome_cand)
                if nome_cand_norm in mapa_abas_norm:
                    aba_cand = mapa_abas_norm[nome_cand_norm]
                    dados_cand = aba_cand.get_all_values()
                    if len(dados_cand) > 1:
                        return _normalizar_df_tarifas(pd.DataFrame(dados_cand[1:], columns=dados_cand[0]))

            # 2) Modo novo: tabela centralizada (Faturamento Master / Tarifas Master)
            abas_master = [
                'FATURAMENTO MASTER',
                'FATURAMENTO_MASTER',
                'TARIFAS_MASTER',
                'TABELA_TARIFAS_MASTER',
                'TABELA DE TARIFAS'
            ]
            aba_master = None
            for nome_aba in abas_master:
                if nome_aba in mapa_abas:
                    aba_master = mapa_abas[nome_aba]
                    break

            if aba_master is not None:
                dados_master = aba_master.get_all_values()
                if len(dados_master) > 1:
                    df_master = pd.DataFrame(dados_master[1:], columns=dados_master[0])
                    df_master.columns = [_normalizar_coluna(c) for c in df_master.columns]

                    # Mapeia o nome da coluna de cliente/tomador para filtrar corretamente.
                    col_tomador = None
                    for c in ['TOMADOR', 'CLIENTE', 'CONTRATANTE', 'EMPRESA', 'EMPRESA_CLIENTE', 'TOMADOR_CLIENTE']:
                        if c in df_master.columns:
                            col_tomador = c
                            break

                    if col_tomador:
                        col_tomador_vals = df_master[col_tomador].astype(str)
                        col_tomador_norm = col_tomador_vals.apply(_normalizar_chave_tomador)
                        mask_exata = col_tomador_norm.isin(aliases_tomador)
                        mask_contida = pd.Series(False, index=df_master.index)
                        for alias in aliases_tomador:
                            if len(alias) >= 4:
                                mask_contida = mask_contida | col_tomador_norm.str.contains(alias, na=False)
                        df_filtrado = df_master[mask_exata | mask_contida].copy()
                        if not df_filtrado.empty:
                            return _normalizar_df_tarifas(df_filtrado)
                    else:
                        # Alguns layouts master não trazem tomador por linha; usa tabela inteira.
                        return _normalizar_df_tarifas(df_master)

            # 3) Fallback final: procura qualquer aba com estrutura de tarifa (CIDADE + VALOR).
            for aba in todas_abas:
                try:
                    dados_gen = aba.get_all_values()
                    if len(dados_gen) <= 1:
                        continue
                    df_gen = pd.DataFrame(dados_gen[1:], columns=dados_gen[0])
                    cols_norm = {_normalizar_coluna(c) for c in df_gen.columns}
                    if ('CIDADE' in cols_norm or 'MUNICIPIO' in cols_norm or 'CIDADE_DESTINO' in cols_norm) and ('VALOR_CHEIO' in cols_norm or 'VALOR' in cols_norm or 'VALOR_BASE' in cols_norm):
                        return _normalizar_df_tarifas(df_gen)
                except Exception:
                    continue

            return pd.DataFrame()
        except Exception:
            return pd.DataFrame()

    def calcular_valor_fatura(cid, bai, end, status, df_p):
        if df_p.empty:
            return 0.0
        c, b, e = padronizar_texto(cid), padronizar_texto(bai), padronizar_texto(end)
        match = df_p[(df_p['CIDADE'] == c) & (df_p['BAIRRO'] == b) & (df_p['ENDERECO'] == e)]
        if match.empty:
            match = df_p[(df_p['CIDADE'] == c) & (df_p['BAIRRO'] == b) & (df_p['ENDERECO'] == "")]
        if match.empty:
            match = df_p[(df_p['CIDADE'] == c) & (df_p['BAIRRO'] == "") & (df_p['ENDERECO'] == "")]
        if match.empty:
            # Fallback para tabelas mais genéricas: cidade sem bairro/endereço detalhado.
            match = df_p[df_p['CIDADE'] == c]
        if match.empty:
            c_key = re.sub(r'[^A-Z0-9]+', '', c)
            if c_key and 'CIDADE_KEY' in df_p.columns:
                match = df_p[
                    (df_p['CIDADE_KEY'] == c_key) |
                    (df_p['CIDADE_KEY'].str.contains(c_key, na=False)) |
                    (pd.Series([c_key] * len(df_p)).str.contains(df_p['CIDADE_KEY'], regex=False, na=False))
                ]
        if not match.empty:
            v_base = float(match.iloc[0]['VALOR_CHEIO'])
            mult = float(match.iloc[0]['MULT_FRUSTRADA'])
            return v_base if "ENTREGUE" in str(status).upper() else (v_base * mult)
        return 0.0

    def gerar_pdf_fatura(id_fat, tomador, df_cobrados, total, obs_texto=""):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_draw_color(15, 23, 42)
        pdf.set_line_width(0.3)
        pdf.rect(5, 5, 200, 287)
        try:
            logo_path = os.path.join(tempfile.gettempdir(), "igo_logo_temp.png")
            if not os.path.exists(logo_path):
                req = urllib.request.Request("https://i.postimg.cc/x84nnjjq/IGO-LOGO.png", headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response, open(logo_path, 'wb') as out_file:
                    out_file.write(response.read())
            pdf.image(logo_path, x=10, y=8, w=30)
        except BaseException:
            pass
        pdf.set_y(15)
        pdf.set_font("Arial", "B", 14)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(0, 6, "DEMONSTRATIVO DE FATURAMENTO - IGO LOGISTICA", ln=True, align="C")
        pdf.set_font("Arial", "B", 10)
        pdf.set_text_color(2, 132, 199)
        pdf.cell(0, 5, f"FATURA: {id_fat} | CLIENTE: {tomador}", ln=True, align="C")
        pdf.set_font("Arial", "", 8)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(0, 4, f"Emissao: {hoje_br.strftime('%d/%m/%Y')} | Volumes: {len(df_cobrados)}", ln=True, align="C")
        pdf.ln(3)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(3)

        pdf.set_fill_color(15, 23, 42)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", "B", 7)
        pdf.cell(18, 5, "PEDIDO", 1, 0, "C", True)
        pdf.cell(18, 5, "COLETA", 1, 0, "C", True)
        pdf.cell(18, 5, "ENTREGA", 1, 0, "C", True)
        pdf.cell(64, 5, "PONTO DE COLETA", 1, 0, "C", True)
        pdf.cell(37, 5, "CIDADE", 1, 0, "C", True)
        pdf.cell(20, 5, "STATUS", 1, 0, "C", True)
        pdf.cell(15, 5, "VALOR", 1, 1, "C", True)

        pdf.set_text_color(51, 65, 85)
        pdf.set_font("Arial", "", 7)
        # Envolvemos o df_cobrados.iterrows() com um enumerate()
        for contador, (idx, row) in enumerate(df_cobrados.iterrows()):
            fill = (contador % 2 == 0) # Agora usamos o 'contador' que é sempre Int
            pdf.set_fill_color(241, 245, 249) if fill else pdf.set_fill_color(255, 255, 255)
            d_col = str(row.get('DATA', '')).split(' ')[0]
            d_ent = str(row.get('DATA_ENTREGA', '')).split(' ')[0]
            val_str = f"R$ {row.get('VALOR (R$)', 0):.2f}"
            st_pdf = "ENTREGUE" if "ENTREGUE" in str(row.get('STATUS', '')).upper() else "FRUSTRADA"

            pdf.cell(18, 5, str(row.get('PEDIDO', '')), 1, 0, "C", True)
            pdf.cell(18, 5, d_col, 1, 0, "C", True)
            pdf.cell(18, 5, d_ent, 1, 0, "C", True)
            pdf.cell(64, 5, str(row.get('LABORATORIO', ''))[:42], 1, 0, "L", True)
            pdf.cell(37, 5, str(row.get('CIDADE', ''))[:22], 1, 0, "L", True)
            pdf.cell(20, 5, st_pdf, 1, 0, "C", True)
            pdf.cell(15, 5, val_str, 1, 1, "R", True)

        pdf.ln(5)
        pdf.set_font("Arial", "B", 10)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(0, 6, f"TOTAL GERAL DA FATURA: R$ {total:,.2f}", 0, 1, "R")
        if obs_texto:
            pdf.ln(5)
            pdf.set_font("Arial", "B", 8)
            pdf.set_text_color(15, 23, 42)
            pdf.cell(0, 5, "OBSERVACOES:", ln=True)
            pdf.set_font("Arial", "", 8)
            pdf.multi_cell(0, 4, obs_texto)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            pdf.output(tmp.name)
            with open(tmp.name, "rb") as f:
                return f.read()

    # =========================================================================
    # ABA 1: NOVO LOTE DE FATURAMENTO
    # =========================================================================
    with tab_faturar:
        if st.session_state.fatura_sucesso:
            st.markdown("### 🧾 Resumo do Faturamento")
            st.success(f"🎉 Fatura gerada com sucesso e salva no Livro Caixa!")

            with st.container(border=True):
                st.markdown(
                    f"<p style='color:#64748B; font-size:12px; margin-bottom:0px;'>Nº DO DOCUMENTO</p><h4 style='margin-top:0px; color:#0F172A;'>{st.session_state.get('fatura_id', 'FAT-000')}</h4>",
                    unsafe_allow_html=True)
                st.divider()
                col_s1, col_s2, col_s3 = st.columns(3)
                col_s1.metric("🏢 Cliente (Tomador)", st.session_state.get('fatura_tomador', '-'))
                col_s2.metric("📦 Volumes Faturados", st.session_state.get('fatura_qtd', 0))
                col_s3.metric("💰 Total do Lote", f"R$ {st.session_state.get('fatura_total', 0):,.2f}")

            st.markdown("<br>", unsafe_allow_html=True)
            c_b1, c_b2, c_b3 = st.columns(3)
            c_b1.download_button(
                "📥 Baixar Fatura (PDF)",
                data=st.session_state.fatura_pdf,
                file_name=f"{st.session_state.get('fatura_id', 'Fatura')}.pdf",
                use_container_width=True,
                type="primary")
            c_b2.download_button(
                "📥 Baixar Relatório (Excel)",
                data=st.session_state.fatura_xls,
                file_name=f"{st.session_state.get('fatura_id', 'Relatorio')}.xlsx",
                use_container_width=True)
            if c_b3.button("🔄 Voltar / Novo Faturamento", use_container_width=True):
                st.session_state.fatura_sucesso = False
                st.rerun()

        else:
            with st.container(border=True):
                c1, c2 = st.columns([1, 1])
                f_tom = c1.selectbox("🏢 Selecionar Tomador:", CLIENTES_ATUALIZADOS, key="fat_tom_sel")
                f_per = c2.date_input(
                    "📅 Período de Entrega:",
                    value=(hoje_br - timedelta(days=30), hoje_br),
                    format="DD/MM/YYYY",
                    key="fat_per_sel")

                if df_raw.empty:
                    st.warning("O banco de dados está vazio.")
                else:
                    if 'STATUS_DISPLAY' not in df_raw.columns:
                        df_raw['STATUS_DISPLAY'] = df_raw.apply(calc_status_display, axis=1)

                    df_raw['TOMADOR_CLEAN'] = df_raw['TOMADOR'].astype(str).str.strip().str.upper()
                    mask_status = df_raw['STATUS_DISPLAY'].str.contains(
                        'Entregue|Frustrada', case=False, na=False) | df_raw['STATUS'].str.upper().str.contains(
                        'ENTREGUE|FRUSTRADA', na=False)
                    mask_tomador = (df_raw['TOMADOR_CLEAN'] == f_tom.upper()) | (df_raw['TOMADOR_CLEAN'].str.contains(f_tom.upper(), na=False))

                    if 'FATURA' not in df_raw.columns:
                        df_raw['FATURA'] = ""
                    mask_fatura = ~df_raw['FATURA'].astype(str).str.upper().str.contains('FAT-', na=False)

                    df_todas_pendentes = df_raw[mask_tomador & mask_status & mask_fatura].copy()

                    if df_todas_pendentes.empty:
                        st.success(f"✅ O sistema vasculhou todo o banco de dados e não achou NENHUM pedido 'Entregue' para {f_tom} que já não tenha sido faturado.")
                    else:
                        def extrair_data_real(row):
                            d_ent = str(row.get('DATA_ENTREGA', '')).split(' ')[0]
                            try:
                                return pd.to_datetime(d_ent, format='%d/%m/%Y').date()
                            except BaseException:
                                try: return pd.to_datetime(d_ent).date()
                                except BaseException:
                                    return pd.to_datetime(row.get('DATA', hoje_br.strftime('%d/%m/%Y')), format='%d/%m/%Y', errors='coerce').date()

                        df_todas_pendentes['DT_FILTRO'] = df_todas_pendentes.apply(extrair_data_real, axis=1)
                        df_todas_pendentes['DT_FILTRO'] = df_todas_pendentes['DT_FILTRO'].fillna(hoje_br)

                        if isinstance(f_per, (tuple, list)) and len(f_per) == 2:
                            mask_data = (df_todas_pendentes['DT_FILTRO'] >= f_per[0]) & (df_todas_pendentes['DT_FILTRO'] <= f_per[1])
                            df_fin = df_todas_pendentes[mask_data].copy()
                        else:
                            df_fin = df_todas_pendentes.copy()

                        if df_fin.empty:
                            datas_escondidas = sorted([d.strftime('%d/%m/%Y') for d in df_todas_pendentes['DT_FILTRO'].unique()])
                            st.warning(f"⚠️ Achei {len(df_todas_pendentes)} pedido(s) Entregues da {f_tom}! MAS eles não estão aparecendo porque a data de entrega deles foi em: {', '.join(datas_escondidas)}. Ajuste o calendário acima para cobrir essas datas.")
                        else:
                            df_p = carregar_tabela_precos(f_tom)
                            if df_p.empty:
                                st.error(f"⚠️ Aba de preços '{f_tom}' vazia ou não encontrada na planilha do financeiro.")
                            else:
                                df_fin['VALOR (R$)'] = df_fin.apply(
                                    lambda r: calcular_valor_fatura(r['CIDADE'], r.get('BAIRRO', ''), r.get('ENDERECO', ''), r['STATUS_DISPLAY'], df_p), axis=1)

                                total_periodo = float(df_fin['VALOR (R$)'].sum()) if not df_fin.empty else 0.0
                                qtd_periodo = int(len(df_fin))
                                qtd_com_valor = int((pd.to_numeric(df_fin['VALOR (R$)'], errors='coerce') > 0).sum()) if not df_fin.empty else 0

                                kpi_p1, kpi_p2, kpi_p3 = st.columns(3)
                                kpi_p1.metric("💰 Faturado no Período", f"R$ {total_periodo:,.2f}")
                                kpi_p2.metric("📦 Pedidos no Período", f"{qtd_periodo}")
                                kpi_p3.metric("✅ Pedidos com Tarifa", f"{qtd_com_valor}")
                                        
                                df_show = df_fin[['DT_FILTRO', 'DATA', 'DATA_ENTREGA', 'PEDIDO', 'LABORATORIO', 'CIDADE', 'STATUS_DISPLAY', 'VALOR (R$)']].copy()
                                df_show.rename(columns={'STATUS_DISPLAY': 'STATUS'}, inplace=True)
                                df_show['DATA_ENTREGA'] = df_show['DATA_ENTREGA'].apply(lambda x: str(x).split(' ')[0])

                                st.markdown("💡 **Dica:** Utilize a caixa de seleção no próprio cabeçalho da primeira coluna da tabela para marcar ou desmarcar todos os pedidos de uma vez.")
                                        
                                # ==========================================
                                # 🚀 GRID AGGRID STREAMLIT THEME (NOVO LOTE)
                                # ==========================================
                                df_grid_fat = df_show.drop(columns=['DT_FILTRO']).copy()
                                        
                                gb_fat = GridOptionsBuilder.from_dataframe(df_grid_fat)
                                gb_fat.configure_selection('multiple', use_checkbox=True, header_checkbox=True, header_checkbox_filtered_only=True)
                                gb_fat.configure_default_column(resizable=True, filterable=True, sortable=True)
                                        
                                gb_fat.configure_column("DATA", header_name="📅 Coleta", width=110)
                                gb_fat.configure_column("DATA_ENTREGA", header_name="🏁 Entrega", width=110)
                                gb_fat.configure_column("PEDIDO", header_name="📦 Pedido", width=110)
                                gb_fat.configure_column("LABORATORIO", header_name="🔬 Ponto de Coleta", width=250)
                                gb_fat.configure_column("CIDADE", header_name="📍 Cidade", width=150)
                                gb_fat.configure_column("STATUS", header_name="🚦 Status", cellRenderer=status_jscode_fat, width=160)
                                gb_fat.configure_column("VALOR (R$)", header_name="💰 Valor", cellRenderer=valor_jscode, width=120)

                                gridOptions_fat = gb_fat.build()

                                tabela_fat = AgGrid(
                                    df_grid_fat,
                                    gridOptions=gridOptions_fat,
                                    theme="streamlit", # HERDA O VISUAL NATIVO DO STREAMLIT
                                    columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS,
                                    height=400,
                                    allow_unsafe_jscode=True,
                                    update_mode="SELECTION_CHANGED",
                                    key="grid_faturamento"
                                )

                                sel_list_fat = tabela_fat.get('selected_rows', [])
                                if sel_list_fat is not None and len(sel_list_fat) > 0:
                                    sel_f = pd.DataFrame(sel_list_fat)
                                    sel_f['VALOR (R$)'] = pd.to_numeric(sel_f['VALOR (R$)'], errors='coerce')
                                    if '_selectedRowNodeInfo' in sel_f.columns:
                                        sel_f = sel_f.drop(columns=['_selectedRowNodeInfo'])
                                else:
                                    sel_f = pd.DataFrame(columns=df_show.columns)
                                            
                                total_f = sel_f['VALOR (R$)'].sum() if not sel_f.empty else 0.0
                                qtd_f = len(sel_f)

                                st.markdown("---")

                                html_kpis = f"""
                                <div style="display: flex; gap: 15px; margin-bottom: 20px;">
                                    <div style="flex: 1; background: linear-gradient(135deg, #1E293B 0%, #334155 100%); border-radius: 8px; height: 75px; display: flex; flex-direction: column; justify-content: center; align-items: center; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                                        <p style="color: white; font-weight: 800; font-size: 13px; margin: 0; line-height: 1.3;">📦 VOLUMES SELECIONADOS</p>
                                        <p style="color: white; font-weight: 900; font-size: 22px; margin: 0; line-height: 1.3;">{qtd_f}</p>
                                    </div>
                                    <div style="flex: 1; background: linear-gradient(135deg, #059669 0%, #10B981 100%); border-radius: 8px; height: 75px; display: flex; flex-direction: column; justify-content: center; align-items: center; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                                        <p style="color: white; font-weight: 800; font-size: 13px; margin: 0; line-height: 1.3;">💰 TOTAL PROJETADO</p>
                                        <p style="color: white; font-weight: 900; font-size: 22px; margin: 0; line-height: 1.3;">R$ {total_f:,.2f}</p>
                                    </div>
                                </div>
                                """
                                st.markdown(html_kpis, unsafe_allow_html=True)

                                obs_fat = st.text_area(
                                    "📝 Observação Customizada (Opcional - Sai no rodapé do PDF):",
                                    placeholder="Ex: Dados bancários para depósito...")

                                if st.button("⚙️ GERAR FATURA AGORA", type="primary", use_container_width=True):
                                    if sel_f.empty:
                                        st.warning("Selecione os pedidos na tabela para faturar!")
                                    else:
                                        with st.spinner("Registrando fatura no Livro Caixa e consolidando baixas..."):
                                            id_fat = f"FAT-{f_tom[:3]}-{datetime.now(FUSO_BR).strftime('%d%m%H%M')}"
                                            aba_m = planilha_db.worksheet("Memoria_Sistema")
                                            df_nuvem = pd.DataFrame(aba_m.get_all_values()[1:], columns=aba_m.get_all_values()[0])

                                            pedidos_faturados = sel_f['PEDIDO'].astype(str).tolist()
                                            for pid in pedidos_faturados:
                                                mask = df_nuvem['PEDIDO'] == pid
                                                if mask.any():
                                                    df_nuvem.loc[mask, 'FATURA'] = id_fat
                                                    st_grid = sel_f[sel_f['PEDIDO'] == pid].iloc[0]['STATUS']
                                                    df_nuvem.loc[mask, 'STATUS'] = "ENTREGUE" if "ENTREGUE" in st_grid.upper() else "FRUSTRADA"

                                            aba_m.clear()
                                            aba_m.update("A1", [df_nuvem.columns.tolist()] + df_nuvem.fillna("").astype(str).values.tolist())

                                            try: aba_h = planilha_financeiro.worksheet("Historico_Faturas")
                                            except BaseException:
                                                aba_h = planilha_financeiro.add_worksheet("Historico_Faturas", 100, 7)
                                                aba_h.update("A1", [["ID_FATURA", "DATA_EMISSAO", "TOMADOR", "TOTAL_PEDIDOS", "VALOR_TOTAL_R$", "PERIODO", "STATUS_PAGAMENTO"]])
                                            time.sleep(1)

                                            d_sel = pd.to_datetime(sel_f['DATA'], format='%d/%m/%Y', errors='coerce').dropna()
                                            periodo_f = f"{d_sel.min().strftime('%d/%m/%Y')} a {d_sel.max().strftime('%d/%m/%Y')}" if not d_sel.empty else "Data Única"

                                            valor_str = f"{total_f:.2f}".replace('.', ',')
                                            nova_linha = [id_fat, hoje_br.strftime("%d/%m/%Y"), f_tom, str(len(sel_f)), valor_str, periodo_f, "⏳ AGUARDANDO"]

                                            aba_h.append_row(nova_linha)
                                            time.sleep(1)

                                            st.session_state.fatura_pdf = gerar_pdf_fatura(id_fat, f_tom, sel_f, total_f, obs_fat)
                                            st.session_state.fatura_xls = gerar_excel_memoria(sel_f.drop(columns=['DT_FILTRO', 'SELECIONAR'], errors='ignore'))
                                            st.session_state.fatura_id = id_fat
                                            st.session_state.fatura_tomador = f_tom
                                            st.session_state.fatura_qtd = len(sel_f)
                                            st.session_state.fatura_total = total_f

                                            carregar_dados_completos.clear()
                                            st.session_state.fatura_sucesso = True
                                            st.rerun()

    # =========================================================================
    # ABA 2: LIVRO CAIXA E HISTÓRICO
    # =========================================================================
    with tab_historico:
        st.markdown("#### 📖 Livro Caixa Eletrônico")
        try:
            aba_h = planilha_financeiro.worksheet("Historico_Faturas")
            dados_h = aba_h.get_all_values()
            if len(dados_h) <= 1:
                st.info("📭 Nenhuma fatura emitida no Livro Caixa.")
            else:
                df_h = pd.DataFrame(dados_h[1:], columns=dados_h[0])
                df_h_disp = df_h.copy()

                if 'VALOR_TOTAL_R$' in df_h_disp.columns:
                    df_h_disp['VALOR_TOTAL_R$'] = df_h_disp['VALOR_TOTAL_R$'].apply(lambda x: f"R$ {float(str(x).replace(',', '.')):.2f}")

                c_h1, c_h2 = st.columns(2)
                f_h_tom = c_h1.selectbox("Filtrar por Cliente:", ["Todos"] + CLIENTES_ATUALIZADOS, key="h_tom")
                if f_h_tom != "Todos":
                    df_h_disp = df_h_disp[df_h_disp['TOMADOR'] == f_h_tom]

                st.markdown(f"**Total de Faturas:** {len(df_h_disp)}")
                        
                # ==========================================
                # 🚀 GRID AGGRID STREAMLIT THEME (LIVRO CAIXA)
                # ==========================================
                df_h_disp = df_h_disp.sort_values('DATA_EMISSAO', ascending=False)
                        
                gb_h = GridOptionsBuilder.from_dataframe(df_h_disp)
                gb_h.configure_default_column(resizable=True, filterable=True, sortable=True)
                gb_h.configure_column("ID_FATURA", header_name="🗂️ Fatura", width=130)
                gb_h.configure_column("DATA_EMISSAO", header_name="📅 Emissão", width=120)
                gb_h.configure_column("TOMADOR", header_name="🏢 Tomador", width=180)
                gb_h.configure_column("TOTAL_PEDIDOS", header_name="📦 Volumes", width=110)
                gb_h.configure_column("VALOR_TOTAL_R$", header_name="💰 Valor", width=130)
                gb_h.configure_column("PERIODO", header_name="📆 Período", width=180)
                gb_h.configure_column("STATUS_PAGAMENTO", header_name="🚦 Status Pagamento", cellRenderer=status_jscode_fat, width=170)
                        
                gridOptions_h = gb_h.build()
                AgGrid(
                    df_h_disp,
                    gridOptions=gridOptions_h,
                    theme="streamlit",
                    columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS,
                    height=300,
                    allow_unsafe_jscode=True,
                    key="grid_livro_caixa"
                )

                st.markdown("---")
                col_re1, col_re2 = st.columns(2)
                with col_re1:
                    st.markdown("#### 🔄 Gestão de Status e Reemissão")
                    fat_sel = st.selectbox("Escolha uma Fatura:", ["Selecione..."] + df_h['ID_FATURA'].tolist())
                    if fat_sel != "Selecione...":
                        st.divider()
                        if st.button("✅ Marcar como PAGO", use_container_width=True):
                            idx_fat = df_h[df_h['ID_FATURA'] == fat_sel].index[0]
                            aba_h.update_cell(idx_fat + 2, 7, "✅ PAGO")
                            st.success("✅ Fatura marcada como PAGO!")
                            time.sleep(1)
                            st.rerun()

                        st.markdown("---")
                        df_rec = df_raw[df_raw['FATURA'] == fat_sel].copy()
                        if df_rec.empty:
                            st.info("📭 Nenhum pedido encontrado para esta fatura.")
                        else:
                            try:
                                df_p_rec = carregar_tabela_precos(df_rec.iloc[0]['TOMADOR'])
                                if not df_p_rec.empty:
                                    df_rec['VALOR (R$)'] = df_rec.apply(
                                        lambda r: calcular_valor_fatura(r['CIDADE'], r.get('BAIRRO', ''), r.get('ENDERECO', ''), str(r['STATUS']).strip().upper(), df_p_rec), axis=1)
                                    total_rec = df_rec['VALOR (R$)'].sum()
                                    st.markdown(f"**Pedidos Encontrados:** {len(df_rec)} | **Total:** R$ {total_rec:,.2f}")
                                    st.download_button(
                                        "📥 Reemitir PDF",
                                        data=gerar_pdf_fatura(fat_sel, df_rec.iloc[0]['TOMADOR'], df_rec, total_rec),
                                        file_name=f"{fat_sel}_2via.pdf",
                                        use_container_width=True,
                                        type="primary")
                                else:
                                    st.warning(f"⚠️ Tabela de preços para {df_rec.iloc[0]['TOMADOR']} não encontrada.")
                            except Exception as e:
                                st.error(f"❌ Erro ao gerar PDF: {str(e)}")

                with col_re2:
                    st.markdown("#### 🚨 Estorno de Segurança")
                    st.warning("O Estorno apaga a fatura do histórico e libera os pedidos para cobrança novamente.")
                    if fat_sel != "Selecione...":
                        senha_estorno = st.text_input("🔑 Senha Master para Estornar:", type="password", key="sen_est")
                        if st.button("❌ EXECUTAR ESTORNO", type="primary", use_container_width=True):
                            if senha_estorno == "123":
                                with st.spinner("Limpando carimbos e histórico..."):
                                    aba_m = planilha_db.worksheet("Memoria_Sistema")
                                    df_m_est = pd.DataFrame(aba_m.get_all_values()[1:], columns=aba_m.get_all_values()[0])
                                    df_m_est.loc[df_m_est['FATURA'] == fat_sel, 'FATURA'] = ""
                                    aba_m.clear()
                                    aba_m.update("A1", [df_m_est.columns.tolist()] + df_m_est.fillna("").astype(str).values.tolist())
                                    idx_del = df_h[df_h['ID_FATURA'] == fat_sel].index[0]
                                    aba_h.delete_rows(idx_del + 2)
                                    st.success("Estorno concluído!")
                                    time.sleep(2)
                                    carregar_dados_completos.clear()
                                    st.rerun()
                            else:
                                st.error("Senha incorreta!")
        except Exception as e:
            st.error(f"⚠️ Erro ao carregar histórico de faturas: {e}")

    # =========================================================================
    # ABA 3: PEDIDOS FATURADOS (HISTÓRICO COM LOTES)
    # =========================================================================
    with tab_faturados:
        st.markdown("#### 📋 Histórico de Pedidos Faturados")
        st.markdown("Consulte todos os pedidos que foram inclusos em lotes de faturamento.")

        try:
            df_faturados = df_raw[df_raw['FATURA'].astype(str).str.contains('FAT-', na=False)].copy()

            if df_faturados.empty:
                st.info("📭 Nenhum pedido faturado até o momento.")
            else:
                df_faturados['DATA_ENTREGA'] = df_faturados['DATA_ENTREGA'].apply(lambda x: str(x).split(' ')[0] if pd.notna(x) else "")
                df_faturados['DATA'] = df_faturados['DATA'].apply(lambda x: str(x).split(' ')[0] if pd.notna(x) else "")

                col_f1, col_f2, col_f3 = st.columns(3)
                f_lote = col_f1.selectbox("Filtrar por Lote (Fatura):", ["Todos"] + sorted(df_faturados['FATURA'].unique().tolist()), key="f_lote")
                f_tomador = col_f2.selectbox("Filtrar por Tomador:", ["Todos"] + CLIENTES_ATUALIZADOS, key="f_tomador")
                f_status = col_f3.selectbox("Filtrar por Status:", ["Todos", "ENTREGUE", "FRUSTRADA"], key="f_status")

                df_filtered = df_faturados.copy()
                if f_lote != "Todos": df_filtered = df_filtered[df_filtered['FATURA'] == f_lote]
                if f_tomador != "Todos": df_filtered = df_filtered[df_filtered['TOMADOR'] == f_tomador]
                if f_status != "Todos": df_filtered = df_filtered[df_filtered['STATUS'].str.upper().str.contains(f_status, na=False)]

                df_display = df_filtered[['PEDIDO', 'FATURA', 'TOMADOR', 'LABORATORIO', 'CIDADE', 'DATA', 'DATA_ENTREGA', 'STATUS']].copy()

                st.markdown(f"**Total de Pedidos Faturados:** {len(df_display)} | **Lotes Únicos:** {df_filtered['FATURA'].nunique()}")
                        
                # ==========================================
                # 🚀 GRID AGGRID STREAMLIT THEME (PEDIDOS FATURADOS)
                # ==========================================
                df_display = df_display.sort_values('FATURA', ascending=False)
                gb_f = GridOptionsBuilder.from_dataframe(df_display)
                gb_f.configure_default_column(resizable=True, filterable=True, sortable=True)
                gb_f.configure_column("PEDIDO", header_name="📦 Pedido", width=110)
                gb_f.configure_column("FATURA", header_name="🗂️ Lote (Fatura)", width=160)
                gb_f.configure_column("TOMADOR", header_name="🏢 Tomador", width=160)
                gb_f.configure_column("LABORATORIO", header_name="🏭 Laboratório", width=250)
                gb_f.configure_column("CIDADE", header_name="🏙️ Cidade", width=150)
                gb_f.configure_column("DATA", header_name="📅 Coleta", width=100)
                gb_f.configure_column("DATA_ENTREGA", header_name="✅ Entrega", width=100)
                gb_f.configure_column("STATUS", header_name="🔄 Status", cellRenderer=status_jscode_fat, width=150)
                        
                gridOptions_f = gb_f.build()
                AgGrid(
                    df_display,
                    gridOptions=gridOptions_f,
                    theme="streamlit",
                    columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS,
                    height=350,
                    allow_unsafe_jscode=True,
                    key="grid_pedidos_faturados"
                )

                st.markdown("---")
                st.markdown("#### 📊 Resumo por Lote de Faturamento")

                df_resumo = df_filtered.groupby('FATURA').agg({
                    'PEDIDO': 'count',
                    'TOMADOR': 'first',
                    'DATA': 'first'
                }).rename(columns={'PEDIDO': 'Qtd Pedidos', 'TOMADOR': 'Tomador', 'DATA': 'Data Primeiro Pedido'}).reset_index()

                df_resumo.rename(columns={'FATURA': 'Lote (Fatura)'}, inplace=True)
                df_resumo = df_resumo.sort_values('Lote (Fatura)', ascending=False)
                        
                gb_r = GridOptionsBuilder.from_dataframe(df_resumo)
                gb_r.configure_default_column(resizable=True, filterable=True, sortable=True)
                gb_r.configure_column("Lote (Fatura)", header_name="🗂️ Lote", width=200)
                gb_r.configure_column("Tomador", header_name="🏢 Tomador", width=250)
                gb_r.configure_column("Qtd Pedidos", header_name="📦 Qtd", width=120)
                gb_r.configure_column("Data Primeiro Pedido", header_name="📅 Início", width=150)
                        
                gridOptions_r = gb_r.build()
                AgGrid(
                    df_resumo,
                    gridOptions=gridOptions_r,
                    theme="streamlit",
                    columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS,
                    height=250,
                    key="grid_resumo_faturas"
                )

        except Exception as e:
            st.error(f"⚠️ Erro ao carregar pedidos faturados: {e}")

    # =========================================================================
    # FUNÇÃO IBGE (Fica dentro do módulo de Faturamento)
    # =========================================================================
    @st.cache_data(ttl=86400)
    def obter_cidades_por_uf(uf):
        if not uf:
            return []
        try:
            url = f"https://servicodados.ibge.gov.br/api/v1/localidades/estados/{uf}/municipios"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                cidades = [padronizar_texto(c['nome']) for c in resp.json()]
                return sorted(cidades)
        except BaseException:
            pass
        return []

    # 🔥 NOVA ABA 4: GESTÃO DE TARIFAS 🔥
    with tab_tarifas:
        st.markdown("#### 💲 Gestão de Tarifas e Preços")
        st.info("Cadastre ou atualize os valores cobrados por rota para cada cliente. Os dados são salvos e aplicados diretamente no banco financeiro.")

        t_cliente = st.selectbox(
            "Selecione o Cliente (Tomador) para gerenciar:",
            ["Selecione..."] + CLIENTES_ATUALIZADOS,
            key="sel_tomador_tarifa")

        if t_cliente != "Selecione...":
            df_precos_atuais = carregar_tabela_precos(t_cliente)

            with st.container(border=True):
                st.markdown(f"**➕ Cadastrar Nova Tarifa para {t_cliente}**")

                lista_ufs = ["", "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"]
                col_uf, col_espaco = st.columns([1, 3])
                t_uf = col_uf.selectbox("1º Passo: Selecione a UF *", lista_ufs, key="tarifa_uf_dinamica")

                with st.form("form_nova_tarifa", clear_on_submit=True):
                    col_t1, col_t2 = st.columns([2, 2])

                    if t_uf:
                        lista_cidades = obter_cidades_por_uf(t_uf)
                        opcoes_cid = ["Selecione..."] + lista_cidades + ["✍️ OUTRA (DIGITAR MANUALMENTE)"]
                        t_cid_box = col_t1.selectbox("2º Passo: Cidade *", opcoes_cid)
                        t_cid_manual = col_t1.text_input("Se escolheu 'Outra', digite a cidade aqui:") if t_cid_box == "✍️ OUTRA (DIGITAR MANUALMENTE)" else ""
                    else:
                        col_t1.info("👆 Selecione a UF acima para carregar as cidades.")
                        t_cid_box = "Selecione..."
                        t_cid_manual = ""

                    t_bai = col_t2.text_input("Bairro (Opcional)", placeholder="Deixe em branco para tarifa geral da cidade")

                    col_t3, col_t4 = st.columns(2)
                    t_rua = col_t3.text_input("Endereço/Rua (Opcional)", placeholder="Ex: AV PAULISTA")
                    t_cep = col_t4.text_input("CEP (Opcional)", placeholder="Apenas números")

                    col_t5, col_t6 = st.columns(2)
                    t_valor = col_t5.number_input("Valor da Entrega (R$) *", min_value=0.0, step=0.5, format="%.2f")
                    t_multa = col_t6.number_input("Multiplicador p/ Frustrada *", min_value=0.0, max_value=1.0, value=0.5, step=0.1, help="Ex: 0.5 cobra 50% do valor caso seja frustrada.")
                    t_prazo = st.number_input("Prazo SLA (dias uteis) *", min_value=1, max_value=30, value=1, step=1, help="Prazo padrao para esta cidade no calculo de DATA_LIMITE.")

                    submit_tarifa = st.form_submit_button("💾 Cadastrar Nova Tarifa no Banco", type="primary", use_container_width=True)

                    if submit_tarifa:
                        t_cid_final = t_cid_manual if t_cid_box == "✍️ OUTRA (DIGITAR MANUALMENTE)" else t_cid_box

                        if not t_uf or t_cid_final in ["Selecione...", ""]:
                            st.error("⚠️ O preenchimento da UF e da Cidade são obrigatórios!")
                        elif t_valor <= 0:
                            st.error("⚠️ O Valor da entrega deve ser maior que zero!")
                        else:
                            with st.spinner("Registrando tarifa e alinhando colunas no banco financeiro..."):
                                try:
                                    buscado = t_cliente.replace('CAEP', 'SYNVIA').replace('CUNHA', 'GRALAB') if t_cliente in ['CAEP', 'CUNHA', 'SYNVIA', 'GRALAB'] else t_cliente
                                    buscado = buscado.strip().upper()

                                    try: aba_cli = planilha_financeiro.worksheet(buscado)
                                    except BaseException:
                                        aba_cli = planilha_financeiro.add_worksheet(title=buscado, rows="100", cols="10")
                                        aba_cli.update("A1", [["CIDADE", "BAIRRO", "ENDERECO", "CEP", "VALOR_CHEIO", "MULT_FRUSTRADA", "PRAZO_DIAS_UTEIS", "UF"]])

                                    cabecalhos_atuais = aba_cli.row_values(1)
                                    if not cabecalhos_atuais:
                                        cabecalhos_atuais = ["CIDADE", "BAIRRO", "ENDERECO", "CEP", "VALOR_CHEIO", "MULT_FRUSTRADA", "PRAZO_DIAS_UTEIS", "UF"]
                                        aba_cli.update("A1", [cabecalhos_atuais])

                                    dicionario_nova_tarifa = {
                                        "CIDADE": padronizar_texto(t_cid_final), "BAIRRO": padronizar_texto(t_bai),
                                        "ENDERECO": padronizar_texto(t_rua), "CEP": re.sub(r'\D', '', t_cep),
                                        "VALOR_CHEIO": f"{t_valor:.2f}".replace(".", ","),
                                        "MULT_FRUSTRADA": f"{t_multa:.2f}".replace(".", ","),
                                        "PRAZO_DIAS_UTEIS": str(int(t_prazo)),
                                        "UF": t_uf}

                                    precisa_atualizar_cab = False
                                    for chave in dicionario_nova_tarifa.keys():
                                        if chave not in cabecalhos_atuais:
                                            cabecalhos_atuais.append(chave)
                                            precisa_atualizar_cab = True

                                    if precisa_atualizar_cab:
                                        aba_cli.update("A1", [cabecalhos_atuais])

                                    nova_linha_ordenada = [dicionario_nova_tarifa.get(col, "") for col in cabecalhos_atuais]
                                    aba_cli.append_row(nova_linha_ordenada)
                                    carregar_tabela_precos.clear()
                                    carregar_mapa_sla_tarifas.clear()

                                    st.session_state.ui_toast = {
                                        'msg': f"Tarifa de R$ {t_valor:.2f} para {padronizar_texto(t_cid_final)} - {t_uf} cadastrada com prazo de {int(t_prazo)} dia(s) util(eis)!",
                                        'icon': "✅"
                                    }
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro Crítico ao salvar tarifa: {e}")

            # --- TABELA INTERATIVA DE TARIFAS ---
            st.markdown("---")
            st.markdown(f"#### 🔎 Gerenciar Tabela de Preços Atual ({t_cliente})")
            st.info("💡 **DICAS DE USO:** \n\n"
                    "1️⃣ **Para EDITAR um valor:** Clique duas vezes em cima do número que deseja mudar.\n\n"
                    "2️⃣ **Para EXCLUIR tarifas:** Marque a caixa no canto esquerdo da linha e use o botão cinza 'Excluir Selecionadas'.\n\n"
                    "⚠️ *Não se esqueça de clicar em 'Salvar Edições' após digitar novos valores!*")

            if not df_precos_atuais.empty:
                # ==========================================
                # 🚀 GRID AGGRID STREAMLIT THEME (TABELA DE TARIFAS)
                # ==========================================
                gb_tar = GridOptionsBuilder.from_dataframe(df_precos_atuais)
                gb_tar.configure_default_column(editable=True, resizable=True, filterable=True, sortable=True)
                gb_tar.configure_selection('multiple', use_checkbox=True, header_checkbox=True)
                        
                # Formatando as colunas pra não ficarem feias
                gb_tar.configure_column("VALOR_CHEIO", header_name="💰 Valor (R$)", type=["numericColumn", "numberColumnFilter"])
                gb_tar.configure_column("MULT_FRUSTRADA", header_name="✖️ Mult. Frustrada", type=["numericColumn"])
                gb_tar.configure_column("PRAZO_DIAS_UTEIS", header_name="⏱️ SLA (dias uteis)", type=["numericColumn", "numberColumnFilter"])
                gb_tar.configure_column("CIDADE", header_name="📍 Cidade")
                gb_tar.configure_column("BAIRRO", header_name="🏘️ Bairro")
                gb_tar.configure_column("ENDERECO", header_name="🛣️ Endereço")
                gb_tar.configure_column("CEP", header_name="📮 CEP")
                gb_tar.configure_column("UF", header_name="🗺️ UF")
                        
                gridOptions_tar = gb_tar.build()

                tabela_tarifas = AgGrid(
                    df_precos_atuais,
                    gridOptions=gridOptions_tar,
                    theme="streamlit", 
                    columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS,
                    height=400,
                    update_mode="MODEL_CHANGED",
                    key=f"editor_tarifas_{t_cliente}"
                )
                        
                df_precos_edit = pd.DataFrame(tabela_tarifas['data'])
                selecionados_del = tabela_tarifas['selected_rows']

                col_btn_save, col_btn_del = st.columns(2)

                if col_btn_save.button("💾 Salvar Edições de Valores (Células)", type="primary", use_container_width=True):
                    with st.spinner("Atualizando tabela de preços no Google Sheets..."):
                        try:
                            # Limpa artefatos do AgGrid e preserva as colunas normais
                            cols_to_keep = [c for c in df_precos_edit.columns if not c.startswith('_')]
                            df_final_save = df_precos_edit[cols_to_keep]

                            buscado = t_cliente.replace('CAEP', 'SYNVIA').replace('CUNHA', 'GRALAB') if t_cliente in ['CAEP', 'CUNHA', 'SYNVIA', 'GRALAB'] else t_cliente
                            buscado = buscado.strip().upper()
                            aba_cli = planilha_financeiro.worksheet(buscado)

                            aba_cli.clear()
                            if not df_final_save.empty:
                                aba_cli.update("A1", [df_final_save.columns.tolist()] + df_final_save.fillna("").astype(str).values.tolist())
                            else:
                                aba_cli.update("A1", [["CIDADE", "BAIRRO", "ENDERECO", "CEP", "VALOR_CHEIO", "MULT_FRUSTRADA", "PRAZO_DIAS_UTEIS", "UF"]])

                            carregar_tabela_precos.clear()
                            carregar_mapa_sla_tarifas.clear()
                            st.session_state.ui_toast = {'msg': "Edições de tarifas salvas com sucesso!", 'icon': "✅"}
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao atualizar tabela: {e}")

                if col_btn_del.button("🗑️ Excluir Tarifas Selecionadas", use_container_width=True):
                    if not selecionados_del:
                        st.warning("⚠️ Selecione a caixa à esquerda de pelo menos uma tarifa para excluí-la.")
                    else:
                        with st.spinner("Excluindo linhas..."):
                            try:
                                # Captura os indices reais selecionados
                                indices_to_drop = [int(row['_selectedRowNodeInfo']['nodeRowIndex']) for row in selecionados_del if '_selectedRowNodeInfo' in row]
                                df_final_save = df_precos_edit.drop(index=indices_to_drop)
                                        
                                # Limpa colunas ocultas
                                cols_to_keep = [c for c in df_final_save.columns if not c.startswith('_')]
                                df_final_save = df_final_save[cols_to_keep]

                                buscado = t_cliente.replace('CAEP', 'SYNVIA').replace('CUNHA', 'GRALAB') if t_cliente in ['CAEP', 'CUNHA', 'SYNVIA', 'GRALAB'] else t_cliente
                                buscado = buscado.strip().upper()
                                aba_cli = planilha_financeiro.worksheet(buscado)

                                aba_cli.clear()
                                if not df_final_save.empty:
                                    aba_cli.update("A1", [df_final_save.columns.tolist()] + df_final_save.fillna("").astype(str).values.tolist())
                                else:
                                    aba_cli.update("A1", [["CIDADE", "BAIRRO", "ENDERECO", "CEP", "VALOR_CHEIO", "MULT_FRUSTRADA", "PRAZO_DIAS_UTEIS", "UF"]])

                                carregar_tabela_precos.clear()
                                carregar_mapa_sla_tarifas.clear()
                                st.session_state.ui_toast = {'msg': f"{len(indices_to_drop)} tarifa(s) excluída(s) com sucesso!", 'icon': "✅"}
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao excluir as tarifas: {e}")

            else:
                st.warning("Nenhuma tarifa cadastrada no banco de dados para este cliente ainda.")
# =============================================================================
# 📝 MÓDULO EXTRA: NOVO PEDIDO MANUAL
# =============================================================================
elif menu == "📝 Pedido Manual":
    st.markdown(
        "<div class='dinamic-border'><h3 class='dinamic-text' style='margin:0;'>📝 Inserir Novo Pedido Manual</h3></div>",
        unsafe_allow_html=True)

    if 'm_rua' not in st.session_state:
        st.session_state['m_rua'] = ""
    if 'm_bai' not in st.session_state:
        st.session_state['m_bai'] = ""
    if 'm_cid' not in st.session_state:
        st.session_state['m_cid'] = ""
    if 'm_uf' not in st.session_state:
        st.session_state['m_uf'] = ""
    if 'cep_input_final' not in st.session_state:
        st.session_state['cep_input_final'] = ""

    def buscar_cep_callback():
        cep_limpo = re.sub(r'\D', '', st.session_state.cep_input_final)
        if len(cep_limpo) == 8:
            try:
                resp = requests.get(
                    f"https://viacep.com.br/ws/{cep_limpo}/json/").json()
                if "erro" not in resp:
                    st.session_state['m_rua'] = padronizar_texto(
                        resp.get("logradouro", ""))
                    st.session_state['m_bai'] = padronizar_texto(
                        resp.get("bairro", ""))
                    st.session_state['m_cid'] = padronizar_texto(
                        resp.get("localidade", ""))
                    st.session_state['m_uf'] = padronizar_texto(
                        resp.get("uf", ""))
            except Exception:
                pass

    with st.container(border=True):
        cc1, cc2, cc3 = st.columns([2, 1, 3], vertical_alignment="bottom")
        cc1.text_input(
            "Digite o CEP e aperte ENTER",
            max_chars=9,
            key="cep_input_final",
            on_change=buscar_cep_callback)

        if cc2.button("🔍 Buscar CEP", use_container_width=True):
            buscar_cep_callback()

        st.markdown("---")
        with st.form("form_manual_definitivo", clear_on_submit=True):
            col1, col2 = st.columns(2)
            m_tomador = col1.selectbox(
                "Laboratório Solicitante *",
                ["Selecione..."] + CLIENTES_AUTORIZADOS)
            m_data = col2.date_input(
                "Data *", format="DD/MM/YYYY", value=hoje_br)
            m_lab = st.text_input("Ponto de Coleta *")
            m_cnpj = st.text_input("CNPJ / Documento (Opcional)")

            col_rua, col_num = st.columns([3, 1])
            m_rua = col_rua.text_input(
                "Logradouro *", value=st.session_state['m_rua'])
            m_numero = col_num.text_input(
                "Número *", placeholder="Ex: 123 ou S/N")

            col3, col4, col5 = st.columns([2, 2, 1])
            m_bai = col3.text_input(
                "Bairro *", value=st.session_state['m_bai'])
            m_cid = col4.text_input(
                "Cidade *", value=st.session_state['m_cid'])
            m_uf = col5.text_input("UF *", value=st.session_state['m_uf'])

            logins_disp = sorted(
                DF_AGENTES['LOGIN DO AGENTE'].unique().tolist()) if not DF_AGENTES.empty else []
            m_agente_escolha = st.selectbox(
                "Agente Designado:",
                ["Automático (Por Rota)"] + logins_disp)

            if st.form_submit_button(
                "🚀 Injetar na Base",
                type="primary",
                    use_container_width=True):
                if m_tomador == "Selecione..." or not m_cid or not m_lab or not m_rua or not m_bai or not m_numero:
                    st.error(
                        "⚠️ Preencha todos os campos obrigatórios (inclusive o Número)!")
                else:
                    with st.spinner("Injetando pedido no sistema..."):
                        lab_limpo = padronizar_texto(m_lab)
                        rua_limpa = padronizar_texto(m_rua)
                        num_limpo = padronizar_texto(m_numero)
                        bai_limpo = padronizar_texto(m_bai)
                        cid_limpa = padronizar_texto(m_cid)
                        uf_limpa = padronizar_texto(m_uf)

                        if m_agente_escolha == "Automático (Por Rota)":
                            m_agente = obter_login_agente(
                                cid_limpa, bai_limpo, lab_limpo, rua_limpa, DF_AGENTES)
                        else:
                            m_agente = m_agente_escolha

                        m_prazo = str(
                            calcular_sla_dias(
                                uf_limpa, cid_limpa, m_tomador))
                        m_limite = str(
                            calcular_data_limite(
                                m_data.strftime("%d/%m/%Y"),
                                int(m_prazo)))

                        try:
                            aba_m_manual = planilha_db.worksheet(
                                "Memoria_Sistema")
                            dados_nuvem = aba_m_manual.get_all_values()
                            df_nuvem_local = pd.DataFrame(dados_nuvem[1:], columns=dados_nuvem[0]) if len(
                                dados_nuvem) > 1 else pd.DataFrame()

                            m_pedido = str(obter_proximo_id(df_nuvem_local))

                            novo_ped_dict = {
                                'DATA': m_data.strftime("%d/%m/%Y"),
                                'PEDIDO': m_pedido,
                                'TOMADOR': m_tomador,
                                'LABORATORIO': lab_limpo,
                                'CNPJ': padronizar_texto(m_cnpj),
                                'ENDERECO': rua_limpa,
                                'NUMERO': num_limpo,
                                'BAIRRO': bai_limpo,
                                'CIDADE': cid_limpa,
                                'UF': uf_limpa,
                                'CEP': re.sub(
                                    r'\D',
                                    '',
                                    st.session_state.cep_input_final),
                                'STATUS': 'PENDENTE',
                                'AGENTE_RAW': m_agente,
                                'PRAZO_DIAS': m_prazo,
                                'DATA_LIMITE': m_limite,
                                'DATA_ENTREGA': "",
                                'FOTO': "",
                                'ROMANEIO': "",
                                'ZAP_ENVIADO': "",
                                'FATURA': ""}

                            if not df_nuvem_local.empty:
                                nova_linha = []
                                for col in df_nuvem_local.columns:
                                    nova_linha.append(
                                        novo_ped_dict.get(col, ""))
                                aba_m_manual.append_row(
                                    nova_linha, value_input_option='USER_ENTERED')
                            else:
                                aba_m_manual.append_row(
                                    list(novo_ped_dict.keys()))
                                aba_m_manual.append_row(
                                    list(novo_ped_dict.values()))

                            if m_agente:
                                despachar_para_appsheet([novo_ped_dict])

                            st.session_state.ui_toast = {'msg': f"Pedido {m_pedido} criado com sucesso!", 'icon': "🎉"}

                            carregar_dados_completos.clear()
                            st.session_state['m_rua'] = ""
                            st.session_state['m_bai'] = ""
                            st.session_state['m_cid'] = ""
                            st.session_state['m_uf'] = ""
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao injetar pedido: {e}")
# =============================================================================
# ➕ MÓDULO 2: IMPORTAÇÃO DE LOTES (OFICIAL)
# =============================================================================
elif menu == "📥 Importações":
    import streamlit.components.v1 as components

    def obter_proximo_id_oficial_seguro(df_base):
        # Recalcula sempre a partir da base oficial para evitar repetição entre dias/sessões.
        proximo_db = obter_proximo_id(df_base, minimo_inicial=2000)
        proximo_sessao = int(st.session_state.get('contador_oficial_temp', 2000))
        proximo = max(proximo_db, proximo_sessao, 2000)

        df_cart = st.session_state.get('df_carrinho_oficial', pd.DataFrame())
        if not df_cart.empty and 'PEDIDO' in df_cart.columns:
            try:
                nums_cart = df_cart['PEDIDO'].astype(str).str.extract(r'^(\d+)')[0].dropna().astype(int)
                if not nums_cart.empty:
                    proximo = max(proximo, int(nums_cart.max() + 1))
            except BaseException:
                pass

        st.session_state.contador_oficial_temp = proximo
        return proximo

    def gsheets_call(op_name, fn, *args, **kwargs):
        """Executa chamadas do Google Sheets com retry/backoff para reduzir bloqueios por excesso de requests."""
        max_tentativas = int(os.environ.get("IGO_GS_MAX_RETRIES", "5"))
        base_delay = float(os.environ.get("IGO_GS_BACKOFF_BASE", "0.6"))
        retry_tokens = [
            "429", "RATE LIMIT", "RESOURCE_EXHAUSTED", "QUOTA", "TIMED OUT",
            "DEADLINE", "503", "502", "UNAVAILABLE", "TRY AGAIN"
        ]

        for tentativa in range(1, max_tentativas + 1):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                msg = str(e).upper()
                deve_tentar = any(token in msg for token in retry_tokens)
                if tentativa >= max_tentativas or not deve_tentar:
                    raise
                espera = base_delay * (2 ** (tentativa - 1)) + random.uniform(0.05, 0.35)
                time.sleep(espera)

    def worksheet_values_to_df(valores, fallback_cols=None):
        """Converte get_all_values() em DataFrame sem gerar nova leitura da API."""
        if valores and len(valores) > 1:
            return pd.DataFrame(valores[1:], columns=valores[0])
        if valores and len(valores) == 1:
            return pd.DataFrame(columns=valores[0])
        return pd.DataFrame(columns=fallback_cols or [])

    def obter_df_memoria_oficial_cache(refresh=False):
        """Cache curto em sessão para reduzir leituras repetidas da aba Memoria_Sistema."""
        ttl_seg = int(os.environ.get("IGO_GS_CACHE_TTL_OFICIAL", "25"))
        cache_key_df = "of_memoria_cache_df"
        cache_key_ts = "of_memoria_cache_ts"
        agora = time.time()

        if not refresh:
            ts_cache = float(st.session_state.get(cache_key_ts, 0))
            df_cache = st.session_state.get(cache_key_df)
            if df_cache is not None and (agora - ts_cache) <= ttl_seg:
                return df_cache.copy()

        aba_m = planilha_db.worksheet("Memoria_Sistema")
        dados_m = gsheets_call("leitura Memoria_Sistema", aba_m.get_all_values)
        df_m = worksheet_values_to_df(dados_m)
        st.session_state[cache_key_df] = df_m
        st.session_state[cache_key_ts] = agora
        return df_m.copy()

    # 🔥 PING SILENCIOSO (ANTI-TIMEOUT DO RENDER) 🔥
    components.html(
        """
        <script>
        setInterval(function() {
            fetch(window.location.href);
        }, 240000);
        </script>
        """,
        height=0, width=0
    )

    st.markdown(
        """
        <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 24px;">
            <div style="background-color: #EFF6FF; padding: 12px 15px; border-radius: 12px; border: 1px solid #BFDBFE; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                <span style="font-size: 26px;">➕</span>
            </div>
            <div>
                <h3 style="margin: 0; color: #1E293B; font-weight: 800;">Central de Importação de Lotes (Oficial)</h3>
                <p style="margin: 0; color: #64748B; font-size: 13px;">Entrada oficial, carrinho cumulativo, gestão de pedidos fixos e central de envio na mesma linha visual do sandbox.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True)

    if "df_preview_oficial" not in st.session_state:
        st.session_state.df_preview_oficial = pd.DataFrame()
    if "df_carrinho_oficial" not in st.session_state:
        st.session_state.df_carrinho_oficial = pd.DataFrame()
    if "contador_fixos_oficial" not in st.session_state:
        st.session_state.contador_fixos_oficial = None

    # 🔥 INICIALIZAR SESSION STATE PARA PEDIDOS FIXOS 🔥
    if 'f_rua_of' not in st.session_state:
        st.session_state['f_rua_of'] = ""
    if 'f_bai_of' not in st.session_state:
        st.session_state['f_bai_of'] = ""
    if 'f_cid_of' not in st.session_state:
        st.session_state['f_cid_of'] = ""
    if 'f_uf_of' not in st.session_state:
        st.session_state['f_uf_of'] = ""
    if 'cep_version_of' not in st.session_state:
        st.session_state['cep_version_of'] = 0

    st.markdown(
        """
        <style>
        div[data-baseweb="tab-list"] {
            gap: 14px;
            margin-bottom: 16px;
            align-items: stretch;
        }
        div[data-baseweb="tab"] {
            background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%) !important;
            border: 1px solid #dbe3ef !important;
            border-radius: 12px !important;
            color: #334155 !important;
            font-weight: 700 !important;
            min-height: 50px !important;
            padding: 0 18px !important;
            line-height: 1.25 !important;
            letter-spacing: 0.15px !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04) !important;
            transition: all 0.2s ease !important;
        }
        button[role="tab"] {
            padding: 0 18px !important;
            min-height: 50px !important;
            line-height: 1.25 !important;
        }
        button[role="tab"] p {
            margin: 0 !important;
            line-height: 1.25 !important;
            white-space: nowrap !important;
        }
        div[data-baseweb="tab"]:hover {
            border-color: #93c5fd !important;
            color: #0f172a !important;
            transform: translateY(-1px);
            box-shadow: 0 6px 16px rgba(37, 99, 235, 0.10) !important;
        }
        button[role="tab"][aria-selected="true"] {
            background: linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%) !important;
            border-color: #1d4ed8 !important;
            border-radius: 12px !important;
            color: #ffffff !important;
            box-shadow: 0 10px 20px rgba(37, 99, 235, 0.22) !important;
            overflow: hidden !important;
            padding: 0 20px !important;
        }
        button[role="tab"][aria-selected="true"] p {
            letter-spacing: 0.2px !important;
            line-height: 1.3 !important;
        }
        div[data-testid="stTextArea"] textarea,
        div[data-testid="stTextInput"] input,
        div[data-testid="stDateInput"] input,
        div[data-testid="stDateInput"] button,
        div[data-testid="stSelectbox"] > div[data-baseweb="select"] > div,
        div[data-testid="stMultiSelect"] > div[data-baseweb="select"] > div {
            background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%) !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 10px !important;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05) !important;
        }
        div[data-testid="stTextArea"] textarea:focus,
        div[data-testid="stTextInput"] input:focus,
        div[data-testid="stDateInput"] input:focus {
            border-color: #60a5fa !important;
            box-shadow: 0 0 0 1px #93c5fd !important;
        }
        div[data-testid="stForm"],
        div[data-testid="stExpander"],
        div[data-testid="stDataFrame"],
        div[data-testid="stVerticalBlockBorderWrapper"],
        div[data-testid="stAlert"] {
            border-radius: 14px !important;
        }
        div[data-testid="stExpander"] {
            border: 1px solid #dbe3ef !important;
            background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%) !important;
            box-shadow: 0 6px 16px rgba(15, 23, 42, 0.05) !important;
        }
        div[data-testid="stFormSubmitButton"] > button,
        div.stButton > button:not([kind="primary"]),
        div[data-testid="stPopover"] > div > button,
        div[data-testid="stPopover"] > button {
            background: linear-gradient(180deg, #eff6ff 0%, #dbeafe 100%) !important;
            color: #0f172a !important;
            border: 1px solid #93c5fd !important;
            border-radius: 10px !important;
            font-weight: 700 !important;
            box-shadow: 0 4px 10px rgba(37, 99, 235, 0.10) !important;
            min-height: 42px !important;
            transition: all 0.2s ease !important;
        }
        div[data-testid="stFormSubmitButton"] > button:hover,
        div.stButton > button:not([kind="primary"]):hover,
        div[data-testid="stPopover"] > div > button:hover,
        div[data-testid="stPopover"] > button:hover {
            background: linear-gradient(180deg, #dbeafe 0%, #bfdbfe 100%) !important;
            border-color: #60a5fa !important;
            box-shadow: 0 8px 18px rgba(37, 99, 235, 0.18) !important;
            transform: translateY(-1px) !important;
        }
        div.stButton > button[kind="primary"],
        div[data-testid="stFormSubmitButton"] > button[kind="primary"] {
            background: linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%) !important;
            border: 1px solid #1d4ed8 !important;
            color: #ffffff !important;
            box-shadow: 0 10px 20px rgba(37, 99, 235, 0.22) !important;
        }
        div.stButton > button[kind="primary"]:hover,
        div[data-testid="stFormSubmitButton"] > button[kind="primary"]:hover {
            background: linear-gradient(135deg, #0284c7 0%, #1d4ed8 100%) !important;
            border-color: #1e40af !important;
            color: #ffffff !important;
        }
        .of-card {
            background: #F8FAFC;
            border: 1px solid #E2E8F0;
            border-radius: 12px;
            padding: 15px;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
        }
        .of-card-title {
            font-size: 11px;
            font-weight: 800;
            color: #64748B;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .of-card-value {
            font-size: 34px;
            font-weight: 900;
            color: #0F172A;
            line-height: 1.1;
        }
        .of-card-subtitle {
            font-size: 13px;
            color: #475569;
            line-height: 1.4;
            margin-top: 4px;
        }
        .of-terminal {
            background: linear-gradient(135deg, #0F172A 0%, #334155 100%);
            color: white;
            padding: 24px 20px;
            border-radius: 14px;
            border-left: 5px solid #3B82F6;
            box-shadow: 0 10px 15px -3px rgba(0,0,0,0.08);
            margin-bottom: 20px;
        }
        .of-sticky-driver {
            position: sticky;
            top: 84px;
            z-index: 5;
        }
        </style>
        """,
        unsafe_allow_html=True)

    # 🔥 CRIAR TABS: IMPORTAÇÃO AVULSA E GESTÃO DE PEDIDOS FIXOS 🔥
    tab_import, tab_fixos_of, tab_envios_of = st.tabs(
        ["📋 1. Importação Avulsa (Matriz)", "🔁 2. Gestão de Pedidos Fixos", "🚀 3. Central de Envios"])

    with tab_import:
        with st.container(border=True):
            st.markdown("#### 1. Mapeamento de Planilha e Colagem")
            c1, c2, c3 = st.columns([1, 1, 2])
            with c1:
                tom = st.selectbox(
                    "🏢 Tomador Central:",
                    ["Selecione..."] +
                    CLIENTES_AUTORIZADOS)
            with c2:
                dt_c = st.date_input(
                    "📅 Data da Rota:",
                    format="DD/MM/YYYY",
                    value=hoje_br)

            txt = st.text_area("📋 Cole os dados (Ctrl+V):", height=150)

            if st.columns([1, 2])[0].button("🔍 1. Processar Matriz",
                                            type="primary", use_container_width=True):
                if not txt or tom == "Selecione...":
                    st.warning("Preencha o Tomador e cole os dados!")
                else:
                    with st.spinner("⏳ Processando dados da planilha..."):
                        try:
                            delim = '\t' if '\t' in txt else (
                                ';' if ';' in txt else ',')
                            df_raw_import = pd.read_csv(
                                io.StringIO(txt), sep=delim, header=None, dtype=str).fillna("")
                            idx_h, max_matches = 0, 0
                            for i in range(min(15, len(df_raw_import))):
                                row_str = unicodedata.normalize(
                                    'NFKD', " ".join(
                                        df_raw_import.iloc[i].astype(str).values).upper()).encode(
                                    'ASCII', 'ignore').decode('utf-8')
                                matches = sum(
                                    1 for kw in [
                                        'PEDIDO', 'CODIGO', 'CNPJ', 'CPF', 'DOCUMENTO', 'DOC', 'ID',
                                        'CIDADE', 'MUNIC', 'LABORAT', 'POSTO', 'NOME', 'CLIENTE',
                                        'ENDERE', 'RUA', 'BAIRRO', 'CEP', 'HORARIO', 'FUNCIONAMENTO', 'OBSERVA'] if kw in row_str)
                                if matches > max_matches:
                                    max_matches, idx_h = matches, i

                            df_limpo = df_raw_import.iloc[idx_h + 1:].copy()
                            df_limpo.columns = [
                                str(c).strip() for c in df_raw_import.iloc[idx_h].values]
                            df_limpo = df_limpo.loc[:, ~df_limpo.columns.duplicated()]

                            for col in df_limpo.columns:
                                df_limpo[col] = df_limpo[col].apply(tratar_texto_global)

                            mapa = {}
                            for c in df_limpo.columns:
                                c_upper = str(c).upper().strip()
                                cl = ''.join(
                                    e for e in unicodedata.normalize(
                                        'NFKD', c_upper).encode(
                                        'ASCII', 'ignore').decode('utf-8') if e.isalnum())

                                if c_upper in ['Nº', 'N°', 'N.', 'N', 'NUM', 'NUMERO', 'NRO'] or cl in ['N', 'NO', 'NR', 'NUM', 'NUMERO']:
                                    mapa[c] = 'NUMERO'
                                elif any(x in cl for x in ['PEDIDO', 'SOLICITA', 'CODIGO', 'CDIGO']) or cl == 'ID':
                                    mapa[c] = 'PEDIDO'
                                elif any(x in cl for x in ['CNPJ', 'CPF', 'DOCUMENTO', 'DOC']):
                                    mapa[c] = 'CNPJ'
                                elif any(x in cl for x in ['LABORAT', 'CLINIC', 'POSTO', 'NOME', 'CLIENTE']):
                                    mapa[c] = 'LABORATORIO'
                                elif any(x in cl for x in ['ENDERE', 'RUA', 'LOGRADOURO', 'AVENIDA']):
                                    mapa[c] = 'ENDERECO'
                                elif 'BAIRRO' in cl:
                                    mapa[c] = 'BAIRRO'
                                elif any(x in cl for x in ['CIDADE', 'MUNIC']):
                                    mapa[c] = 'CIDADE'
                                elif any(x in cl for x in ['ESTADO', 'UF']):
                                    mapa[c] = 'UF'
                                elif 'CEP' in cl:
                                    mapa[c] = 'CEP'
                                elif any(x in cl for x in ['HORARIO', 'HORA', 'FUNCIONAMENTO', 'PERIODO']):
                                    mapa[c] = 'HORARIO'
                                elif any(x in cl for x in ['OBSERVA', 'OBS', 'NOTA']):
                                    mapa[c] = 'OBSERVACOES'

                            df_limpo.rename(columns=mapa, inplace=True)

                            for c in ['PEDIDO', 'LABORATORIO', 'CNPJ', 'CEP', 'ENDERECO', 'NUMERO', 'BAIRRO', 'CIDADE', 'UF', 'OBSERVACOES']:
                                if c not in df_limpo.columns:
                                    df_limpo[c] = ""

                            if 'HORARIO' in df_limpo.columns:
                                for idx, row in df_limpo.iterrows():
                                    horario_val = str(row['HORARIO']).strip()
                                    obs_val = str(row['OBSERVACOES']).strip()
                                    if horario_val and horario_val.upper() not in ['NAN', 'NONE']:
                                        nova_obs = f"[COLETA: {horario_val}]"
                                        if obs_val and obs_val.upper() not in ['NAN', 'NONE']:
                                            nova_obs += f" - {obs_val}"
                                        df_limpo.at[idx, 'OBSERVACOES'] = nova_obs

                            df_limpo['PEDIDO'] = ""

                            for idx, row in df_limpo.iterrows():
                                e, n, b = str(row['ENDERECO']), str(row['NUMERO']), str(row['BAIRRO'])
                                if e and (not n or not b):
                                    cep_m = re.search(r'(\d{5}-?\d{3})', e)
                                    if cep_m:
                                        df_limpo.at[idx, 'CEP'] = cep_m.group(1)
                                        e = e.replace(cep_m.group(1), '').strip(' ,-')
                                    if ',' in e and not n:
                                        pts = e.split(',')
                                        df_limpo.at[idx, 'ENDERECO'], df_limpo.at[idx, 'NUMERO'] = pts[0].strip(), pts[1].strip()

                            df_limpo['UF'] = df_limpo['UF'].astype(str).str.upper().str.strip()
                            df_limpo['TOMADOR'] = tom
                            df_limpo['DATA'] = dt_c.strftime("%d/%m/%Y")

                            df_limpo['CIDADE'] = df_limpo['CIDADE'].apply(lambda c: normalizar_cidade_operacao(corrigir_cidade_inteligente(c, DF_AGENTES), DF_AGENTES))
                            df_limpo['AGENTE_RAW'] = df_limpo.apply(lambda r: obter_login_agente(r['CIDADE'], r['BAIRRO'], r['LABORATORIO'], r['ENDERECO'], DF_AGENTES), axis=1)

                            st.session_state.df_preview_oficial = df_limpo[df_limpo['LABORATORIO'].str.strip() != ""][['DATA', 'TOMADOR', 'PEDIDO', 'LABORATORIO', 'CNPJ', 'ENDERECO', 'NUMERO', 'BAIRRO', 'CIDADE', 'UF', 'CEP', 'OBSERVACOES', 'AGENTE_RAW']]
                            st.session_state.ui_toast = {'msg': "Processamento Concluído!", 'icon': "✅"}
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro no processamento: {e}")

        if not st.session_state.df_preview_oficial.empty:
            st.markdown("---")
            col_tit, col_canc = st.columns([4, 1], vertical_alignment="center")
            col_tit.markdown("### 👀 2. Preview de Carga Oficial")
            if col_canc.button("❌ Cancelar / Limpar", type="secondary", use_container_width=True, key="canc_oficial"):
                st.session_state.df_preview_oficial = pd.DataFrame()
                st.rerun()

            df_preview = st.session_state.df_preview_oficial
            mask_err = (df_preview['AGENTE_RAW'].astype(str).str.strip() == "") | (df_preview['AGENTE_RAW'].astype(str).str.upper() == "NAN")
            df_err = df_preview[mask_err]
            df_ok = df_preview[~mask_err]

            if not df_err.empty:
                st.error(f"🚨 **Atenção:** {len(df_err)} pedido(s) sem motorista. Corrija abaixo.")
                with st.form("form_correcao_agentes_of"):
                    correcoes = {}
                    logins_disp = sorted(DF_AGENTES['LOGIN DO AGENTE'].unique().tolist()) if not DF_AGENTES.empty else []
                    for idx, row in df_err.iterrows():
                        st.markdown(f"**Local:** {row['LABORATORIO']} | **Cidade:** {row['CIDADE']}")
                        correcoes[idx] = st.selectbox(f"Motorista:", ["Selecione..."] + logins_disp, key=f"fix_mot_of_{idx}")
                            
                    if st.form_submit_button("💾 Validar Motoristas", type="primary"):
                        novas_rotas = []
                        for idx, novo_mot in correcoes.items():
                            if novo_mot != "Selecione...":
                                st.session_state.df_preview_oficial.at[idx, 'AGENTE_RAW'] = novo_mot
                                r_cid = str(st.session_state.df_preview_oficial.at[idx, 'CIDADE'])
                                r_bai = str(st.session_state.df_preview_oficial.at[idx, 'BAIRRO'])
                                rota_str = " ➔ ".join([p for p in [limpar_nome_local_rota(r_cid), limpar_nome_local_rota(r_bai)] if p])
                                if not DF_AGENTES.empty:
                                    dados_ag = DF_AGENTES[DF_AGENTES['LOGIN DO AGENTE'] == novo_mot].iloc[0]
                                    novas_rotas.append({
                                        "ROTA MAPEADA": rota_str,
                                        "LOGIN DO AGENTE": novo_mot,
                                        "NOME DO AGENTE": dados_ag['NOME DO AGENTE'],
                                        "TELEFONE": dados_ag['TELEFONE']})

                        if novas_rotas:
                            try:
                                df_novas_rotas = pd.DataFrame(novas_rotas)
                                aba_agentes = planilha_db.worksheet("Agentes")
                                dados_atuais_ag = aba_agentes.get_all_values()
                                df_ag_atual = pd.DataFrame(dados_atuais_ag[1:], columns=dados_atuais_ag[0]) if len(dados_atuais_ag) > 1 else pd.DataFrame(columns=["ROTA MAPEADA", "LOGIN DO AGENTE", "NOME DO AGENTE", "TELEFONE"])
                                df_novo = pd.concat([df_ag_atual, df_novas_rotas], ignore_index=True).drop_duplicates(subset=["ROTA MAPEADA", "LOGIN DO AGENTE"])
                                aba_agentes.clear()
                                aba_agentes.update("A1", [df_novo.columns.tolist()] + df_novo.fillna("").astype(str).values.tolist())
                                carregar_dados_agentes.clear()
                            except Exception as e:
                                st.warning(f"Erro ao salvar rota inteligente: {e}")
                        st.rerun()
            else:
                st.success(f"✅ Lote validado! {len(df_ok)} pedidos prontos.")
                st.dataframe(df_ok, hide_index=True)

                if st.button("➕ Adicionar ao Carrinho Oficial (Cumulativo)", type="primary", key="add_carrinho_oficial"):
                    with st.spinner("Gerando IDs sequenciais e adicionando ao carrinho..."):
                        try:
                            agora_click = time.time()
                            ultimo_click = float(st.session_state.get('of_add_carrinho_last_click_ts', 0))
                            if (agora_click - ultimo_click) < 1.5:
                                st.warning("Aguarde 2 segundos antes de clicar novamente para evitar excesso de leitura no Google Sheets.")
                                st.stop()

                            st.session_state.of_add_carrinho_last_click_ts = agora_click

                            df_ok_add = df_ok.copy()

                            # Busca na nuvem apenas para semear o contador na primeira carga da sessão.
                            precisa_seed_remoto = int(st.session_state.get('contador_oficial_temp', 2000)) <= 2000
                            if precisa_seed_remoto:
                                df_up = obter_df_memoria_oficial_cache(refresh=False)
                            else:
                                df_up = pd.DataFrame(columns=['PEDIDO'])

                            prox_id_of = obter_proximo_id_oficial_seguro(df_up)

                            for idx, row in df_ok_add.iterrows():
                                df_ok_add.at[idx, 'PEDIDO'] = str(prox_id_of)
                                prox_id_of += 1

                            st.session_state.contador_oficial_temp = prox_id_of

                            df_ok_add['PRAZO_DIAS'] = df_ok_add.apply(lambda r: str(calcular_sla_dias(r['UF'], r['CIDADE'], r['TOMADOR'])), axis=1)
                            df_ok_add['DATA_LIMITE'] = df_ok_add.apply(lambda r: str(calcular_data_limite(r['DATA'], int(r['PRAZO_DIAS']))), axis=1)
                            df_ok_add['STATUS'] = 'PENDENTE'
                            df_ok_add['DATA_ENTREGA'] = ''
                            df_ok_add['FOTO'] = ''
                            df_ok_add['ROMANEIO'] = ''
                            df_ok_add['ZAP_ENVIADO'] = ''
                            df_ok_add['FATURA'] = ''

                            df_ok_add = df_ok_add.astype(str)

                            if st.session_state.df_carrinho_oficial.empty:
                                st.session_state.df_carrinho_oficial = df_ok_add
                            else:
                                st.session_state.df_carrinho_oficial = pd.concat([st.session_state.df_carrinho_oficial, df_ok_add], ignore_index=True)

                            st.session_state.df_preview_oficial = pd.DataFrame()
                            st.session_state.ui_toast = {'msg': "Pedidos adicionados ao carrinho com sucesso!", 'icon': "🛒"}
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro: {e}")

    # -------------------------------------------------------------------------
    # ABA 2: GESTÃO DE PEDIDOS FIXOS (IMPORTAÇÃO OFICIAL)
    # -------------------------------------------------------------------------
    with tab_fixos_of:
        st.markdown("#### 🏭 Criar Novo Agendamento Fixo")

        cols_fixos_of = ['ID_REGRA', 'TOMADOR', 'LABORATORIO', 'ENDERECO', 'NUMERO', 'BAIRRO', 'CIDADE', 'UF', 'CEP', 'OBSERVACOES', 'MOTORISTA', 'SEG', 'TER', 'QUA', 'QUI', 'SEX', 'SAB', 'STATUS']
        df_regras_of = pd.DataFrame(columns=cols_fixos_of)

        try:
            aba_fixos_of = planilha_db.worksheet("Agendamentos_Fixos_Oficial")
            dados_fixos_of = aba_fixos_of.get_all_values()
            if len(dados_fixos_of) > 1:
                df_regras_of = pd.DataFrame(dados_fixos_of[1:], columns=dados_fixos_of[0])
        except Exception:
            try:
                aba_fixos_of = planilha_db.add_worksheet("Agendamentos_Fixos_Oficial", 100, 20)
                aba_fixos_of.update("A1", [cols_fixos_of])
            except Exception: pass

        def buscar_cep_fixo_of_callback():
            chave_atual = f"cep_input_fixo_of_{st.session_state.cep_version_of}"
            cep_digitado = st.session_state.get(chave_atual, "")
            cep_limpo = re.sub(r'\D', '', cep_digitado)
            if len(cep_limpo) == 8:
                try:
                    resp = requests.get(f"https://viacep.com.br/ws/{cep_limpo}/json/").json()
                    if "erro" not in resp:
                        st.session_state['f_rua_of'] = padronizar_texto(resp.get("logradouro", ""))
                        st.session_state['f_bai_of'] = padronizar_texto(resp.get("bairro", ""))
                        st.session_state['f_cid_of'] = padronizar_texto(resp.get("localidade", ""))
                        st.session_state['f_uf_of'] = padronizar_texto(resp.get("uf", ""))
                except Exception: pass

        cc1_f, cc2_f, cc3_f = st.columns([2, 1, 3], vertical_alignment="bottom")

        key_dinamica_of = f"cep_input_fixo_of_{st.session_state.cep_version_of}"
        cc1_f.text_input("Digite o CEP e aperte ENTER", max_chars=9, key=key_dinamica_of, on_change=buscar_cep_fixo_of_callback)

        if cc2_f.button("🔍 Buscar CEP", key="btn_busc_cep_fixo_of", use_container_width=True):
            buscar_cep_fixo_of_callback()

        st.markdown("---")

        with st.form("form_novo_fixo_oficial", clear_on_submit=True):
            col_f1, col_f2 = st.columns(2)
            f_tomador = col_f1.selectbox("Tomador *", ["Selecione..."] + CLIENTES_AUTORIZADOS)
            f_lab = col_f2.text_input("Ponto de Coleta / Laboratório *")

            c_rua, c_num = st.columns([3, 1])
            f_rua = c_rua.text_input("Logradouro *", value=st.session_state['f_rua_of'])
            f_num = c_num.text_input("Número *")

            c_bai, c_cid, c_uf = st.columns([2, 2, 1])
            f_bai = c_bai.text_input("Bairro *", value=st.session_state['f_bai_of'])
            f_cid = c_cid.text_input("Cidade *", value=st.session_state['f_cid_of'])
            f_uf = c_uf.text_input("UF *", value=st.session_state['f_uf_of'])

            f_obs = st.text_input("Observações Padrão (Ex: [COLETA: 08:00 - 12:00])")

            st.markdown("**Dias da Semana com Coleta Fixa:**")
            d1, d2, d3, d4, d5, d6 = st.columns(6)
            b_seg = d1.checkbox("Segunda")
            b_ter = d2.checkbox("Terça")
            b_qua = d3.checkbox("Quarta")
            b_qui = d4.checkbox("Quinta")
            b_sex = d5.checkbox("Sexta")
            b_sab = d6.checkbox("Sábado")

            logins_disp = sorted(DF_AGENTES['LOGIN DO AGENTE'].unique().tolist()) if not DF_AGENTES.empty else []
            f_agente = st.selectbox("Motorista Fixo:", ["Automático (Por Rota)"] + logins_disp)

            if st.form_submit_button("💾 Salvar Agendamento Fixo", type="primary"):
                if f_tomador == "Selecione..." or not f_lab or not f_rua or not f_num or not f_bai or not f_cid:
                    st.error("Preencha todos os campos obrigatórios (*).")
                elif not any([b_seg, b_ter, b_qua, b_qui, b_sex, b_sab]):
                    st.error("Selecione pelo menos um dia da semana.")
                else:
                    with st.spinner("Salvando regra..."):
                        if f_agente == "Automático (Por Rota)":
                            f_agente = obter_login_agente(f_cid, f_bai, f_lab, f_rua, DF_AGENTES)

                        nova_regra = [
                            f"REG-{str(uuid.uuid4())[:6].upper()}", f_tomador, padronizar_texto(f_lab),
                            padronizar_texto(f_rua), padronizar_texto(f_num), padronizar_texto(f_bai),
                            padronizar_texto(f_cid), padronizar_texto(f_uf), st.session_state.get(key_dinamica_of, ""),
                            str(f_obs), f_agente,
                            "SIM" if b_seg else "NAO", "SIM" if b_ter else "NAO", "SIM" if b_qua else "NAO",
                            "SIM" if b_qui else "NAO", "SIM" if b_sex else "NAO", "SIM" if b_sab else "NAO",
                            "ATIVO"
                        ]
                        try:
                            aba_fixos_of.append_row(nova_regra)
                            st.success("✅ Regra Fixa cadastrada com sucesso!")

                            st.session_state['f_rua_of'] = ""
                            st.session_state['f_bai_of'] = ""
                            st.session_state['f_cid_of'] = ""
                            st.session_state['f_uf_of'] = ""
                            st.session_state.cep_version_of += 1

                            time.sleep(1.5)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro: {e}")

        st.markdown("---")
        st.markdown("#### ⚙️ Gerar Pedidos Fixos para a Importação")
        dt_fixos_of = st.date_input("📅 Data da Rota Fixa:", value=hoje_br, key="dt_fixos_of")
        dia_sem_of = {0: 'SEG', 1: 'TER', 2: 'QUA', 3: 'QUI', 4: 'SEX', 5: 'SAB', 6: 'DOM'}
        dia_selecionado_of = dia_sem_of[dt_fixos_of.weekday()]

        df_geracao_of = pd.DataFrame()
        if not df_regras_of.empty and dia_selecionado_of != 'DOM':
            df_geracao_of = df_regras_of[(df_regras_of['STATUS'].astype(str).str.upper() == 'ATIVO') & (df_regras_of[dia_selecionado_of].astype(str).str.upper() == 'SIM')].copy()

        if dia_selecionado_of == 'DOM':
            st.info(f"Hoje é domingo. Pedidos fixos não são gerados para domingo.")
        elif df_geracao_of.empty:
            st.info(f"Nenhum pedido fixo programado para {dt_fixos_of.strftime('%d/%m/%Y')} ({dia_selecionado_of}).")
        else:
            st.info(f"{len(df_geracao_of)} pedido(s) fixo(s) encontrados para {dt_fixos_of.strftime('%d/%m/%Y')} ({dia_selecionado_of}).")
            st.dataframe(df_geracao_of[['TOMADOR', 'LABORATORIO', 'ENDERECO', 'NUMERO', 'BAIRRO', 'CIDADE', 'UF', 'MOTORISTA', 'OBSERVACOES']].fillna(""), use_container_width=True)

            if st.button("➕ Adicionar Regras Fixas ao Preview Oficial", key="btn_add_fixos_preview_of"):
                novos_fixos = []
                for _, regra in df_geracao_of.iterrows():
                    agente = str(regra.get('MOTORISTA', '')).strip()
                    if not agente or agente.upper() in ['AUTOMÁTICO (POR ROTA)', 'AUTOMATICO (POR ROTA)', 'AUTOMATICO (POR ROTA)']:
                        agente = obter_login_agente(str(regra.get('CIDADE', '')), str(regra.get('BAIRRO', '')), str(regra.get('LABORATORIO', '')), str(regra.get('ENDERECO', '')), DF_AGENTES)

                    obs_fix = str(regra.get('OBSERVACOES', '')).strip()
                    if obs_fix and obs_fix.upper() not in ['NAN', 'NONE']: obs_fix = obs_fix + ' [FIXO]'
                    else: obs_fix = '[FIXO]'

                    novos_fixos.append({
                        'DATA': dt_fixos_of.strftime('%d/%m/%Y'),
                        'TOMADOR': regra.get('TOMADOR', ''),
                        'PEDIDO': '',
                        'LABORATORIO': regra.get('LABORATORIO', ''),
                        'CNPJ': '',
                        'ENDERECO': regra.get('ENDERECO', ''),
                        'NUMERO': regra.get('NUMERO', ''),
                        'BAIRRO': regra.get('BAIRRO', ''),
                        'CIDADE': regra.get('CIDADE', ''),
                        'UF': regra.get('UF', ''),
                        'CEP': regra.get('CEP', ''),
                        'OBSERVACOES': obs_fix,
                        'AGENTE_RAW': agente
                    })

                df_novos_fixos_of = pd.DataFrame(novos_fixos)
                if not df_novos_fixos_of.empty:
                    if not st.session_state.df_preview_oficial.empty:
                        st.session_state.df_preview_oficial = pd.concat([st.session_state.df_preview_oficial, df_novos_fixos_of], ignore_index=True)
                    else:
                        st.session_state.df_preview_oficial = df_novos_fixos_of
                        
                st.session_state.ui_toast = {'msg': "Pedidos fixos adicionados ao preview!", 'icon': "✅"}
                st.rerun()

        st.markdown("---")
        st.markdown("#### 📋 Gerenciar Laboratórios Fixos")
        st.info("💡 **Edite diretamente na tabela!** Mude o Status (ATIVO/INATIVO), ajuste os dias da semana ou troque o Motorista. Para deletar, selecione a linha no canto esquerdo e aperte a tecla 'Delete' ou 'Backspace'.")

        if not df_regras_of.empty:
            logins_p_tabela_of = sorted(DF_AGENTES['LOGIN DO AGENTE'].unique().tolist()) if not DF_AGENTES.empty else []

            df_regras_edit_of = st.data_editor(
                df_regras_of,
                num_rows="dynamic",
                use_container_width=True,
                hide_index=True,
                column_config={
                    "STATUS": st.column_config.SelectboxColumn("STATUS", options=["ATIVO", "INATIVO"]),
                    "SEG": st.column_config.SelectboxColumn("SEG", options=["SIM", "NAO"]),
                    "TER": st.column_config.SelectboxColumn("TER", options=["SIM", "NAO"]),
                    "QUA": st.column_config.SelectboxColumn("QUA", options=["SIM", "NAO"]),
                    "QUI": st.column_config.SelectboxColumn("QUI", options=["SIM", "NAO"]),
                    "SEX": st.column_config.SelectboxColumn("SEX", options=["SIM", "NAO"]),
                    "SAB": st.column_config.SelectboxColumn("SAB", options=["SIM", "NAO"]),
                    "MOTORISTA": st.column_config.SelectboxColumn("MOTORISTA", options=logins_p_tabela_of)
                },
                key="editor_regras_fixas_oficial"
            )

            if st.button("💾 Salvar Alterações na Base de Regras", type="primary", use_container_width=True):
                with st.spinner("Atualizando banco de dados..."):
                    try:
                        aba_fixos_of.clear()
                        if df_regras_edit_of.empty:
                            aba_fixos_of.update("A1", [cols_fixos_of])
                        else:
                            aba_fixos_of.update("A1", [df_regras_edit_of.columns.tolist()] + df_regras_edit_of.fillna("").astype(str).values.tolist())
                                
                        st.session_state.ui_toast = {'msg': f"{len(ids_para_remover)} regras excluídas!", 'icon': "🗑️"}
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao salvar regras: {e}")
        else:
            st.info("Nenhuma regra de agendamento cadastrada ainda.")

    # -------------------------------------------------------------------------
    # ABA 3: CENTRAL DE ENVIOS OFICIAL
    # -------------------------------------------------------------------------
    with tab_envios_of:
        st.markdown("#### 🚀 Central de Envios Oficial")
        st.info("O carrinho oficial continua sendo alimentado na aba de importação; aqui você confere, injeta e dispara.")

        # --- BLOCAGEM DE PROCESSAMENTO: AGENDAMENTOS FIXOS ---
        df_fixos_hoje_of = pd.DataFrame()
        try:
            aba_fixos_of = planilha_db.worksheet("Agendamentos_Fixos_Oficial")
            dados_fixos_of = aba_fixos_of.get_all_values()
            if len(dados_fixos_of) > 1:
                df_regras_temp = pd.DataFrame(dados_fixos_of[1:], columns=dados_fixos_of[0])
                mapa_dias = {0: 'SEG', 1: 'TER', 2: 'QUA', 3: 'QUI', 4: 'SEX', 5: 'SAB', 6: 'DOM'}
                dia_atual = mapa_dias[hoje_br.weekday()]

                if dia_atual != 'DOM':
                    df_alvo = df_regras_temp[(df_regras_temp[dia_atual] == "SIM") & (df_regras_temp['STATUS'] == "ATIVO")].copy()

                    if not df_alvo.empty:
                        try:
                            df_up_temp = obter_df_memoria_oficial_cache(refresh=False)

                            prox_id_fixo = obter_proximo_id_oficial_seguro(df_up_temp)

                            novos_pedidos_fixos = []
                            for _, regra in df_alvo.iterrows():
                                agente = str(regra.get('MOTORISTA', '')).strip()
                                if not agente or agente.upper() in ['AUTOMÁTICO (POR ROTA)', 'AUTOMATICO (POR ROTA)']:
                                    agente = obter_login_agente(str(regra.get('CIDADE', '')), str(regra.get('BAIRRO', '')), str(regra.get('LABORATORIO', '')), str(regra.get('ENDERECO', '')), DF_AGENTES)

                                obs_fix = str(regra.get('OBSERVACOES', '')).strip()
                                if obs_fix and obs_fix.upper() not in ['NAN', 'NONE']: obs_fix = obs_fix + ' [FIXO]'
                                else: obs_fix = '[FIXO]'

                                prazo = calcular_sla_dias(regra.get('UF', 'SP'), regra.get('CIDADE', ''), regra.get('TOMADOR', ''))
                                dt_lim = calcular_data_limite(hoje_br.strftime("%d/%m/%Y"), int(prazo))

                                novo_pedido = {
                                    'DATA': hoje_br.strftime("%d/%m/%Y"),
                                    'TOMADOR': regra.get('TOMADOR', ''),
                                    'PEDIDO': str(prox_id_fixo),
                                    'LABORATORIO': regra.get('LABORATORIO', ''),
                                    'CNPJ': "",
                                    'ENDERECO': regra.get('ENDERECO', ''),
                                    'NUMERO': regra.get('NUMERO', ''),
                                    'BAIRRO': regra.get('BAIRRO', ''),
                                    'CIDADE': regra.get('CIDADE', ''),
                                    'UF': regra.get('UF', ''),
                                    'CEP': regra.get('CEP', ''),
                                    'STATUS': 'PENDENTE',
                                    'AGENTE_RAW': agente,
                                    'PRAZO_DIAS': str(prazo),
                                    'DATA_LIMITE': str(dt_lim),
                                    'DATA_ENTREGA': "",
                                    'FOTO': "",
                                    'ROMANEIO': "",
                                    'ZAP_ENVIADO': "",
                                    'FATURA': "",
                                    'OBSERVACOES': obs_fix
                                }
                                novos_pedidos_fixos.append(novo_pedido)
                                prox_id_fixo += 1

                            df_fixos_hoje_of = pd.DataFrame(novos_pedidos_fixos)
                        except Exception:
                            pass
        except Exception:
            pass

        incluir_fixos_of = False
        if not df_fixos_hoje_of.empty:
            st.info(f"💡 O sistema encontrou **{len(df_fixos_hoje_of)} pedidos fixos** programados para hoje ({dia_atual}).")
            incluir_fixos_of = st.toggle("👉 INCLUIR PEDIDOS FIXOS NA CARGA OFICIAL DE HOJE", value=False, key="toggle_fixos_oficial")
        else:
            st.info("Nenhum pedido fixo programado para hoje.")

        df_cart_of = st.session_state.df_carrinho_oficial.copy()

        if incluir_fixos_of and not df_fixos_hoje_of.empty:
            if df_cart_of.empty: df_cart_of = df_fixos_hoje_of
            else: df_cart_of = pd.concat([df_cart_of, df_fixos_hoje_of], ignore_index=True)

        if 'of_step' not in st.session_state:
            st.session_state.of_step = 'IDLE'
        if 'of_df_dispatch' not in st.session_state:
            st.session_state.of_df_dispatch = pd.DataFrame()
        if 'of_resultados_disparo' not in st.session_state:
            st.session_state.of_resultados_disparo = {}
        if 'of_final_metrics' not in st.session_state:
            st.session_state.of_final_metrics = {'total': 0, 'sucesso': 0, 'falhas': 0}

        def render_big_metrics_off(tot, pend, suc, fal):
            return f"""
            <div style="display:flex; gap:12px; text-align:center; margin-bottom: 20px;">
                <div style="flex:1; background:#F8FAFC; border: 2px solid #E2E8F0; padding:15px; border-radius:12px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                    <div style="font-size:13px; font-weight:800; color:#64748B; text-transform:uppercase;">Alvos Totais</div>
                    <div style="font-size:38px; font-weight:900; color:#0F172A; line-height:1.2;">{tot}</div>
                </div>
                <div style="flex:1; background:#FFFBEB; border: 2px solid #FDE68A; padding:15px; border-radius:12px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                    <div style="font-size:13px; font-weight:800; color:#D97706; text-transform:uppercase;">Pendentes</div>
                    <div style="font-size:38px; font-weight:900; color:#B45309; line-height:1.2;">{pend}</div>
                </div>
                <div style="flex:1; background:#F0FDF4; border: 2px solid #A7F3D0; padding:15px; border-radius:12px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                    <div style="font-size:13px; font-weight:800; color:#059669; text-transform:uppercase;">Sucessos (✅)</div>
                    <div style="font-size:38px; font-weight:900; color:#047857; line-height:1.2;">{suc}</div>
                </div>
                <div style="flex:1; background:#FEF2F2; border: 2px solid #FECACA; padding:15px; border-radius:12px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                    <div style="font-size:13px; font-weight:800; color:#DC2626; text-transform:uppercase;">Falhas (❌)</div>
                    <div style="font-size:38px; font-weight:900; color:#B91C1C; line-height:1.2;">{fal}</div>
                </div>
            </div>
            """

        def render_current_driver_off(nom, idx, total):
            return f"""
            <div class="of-sticky-driver" style="background: linear-gradient(135deg, #0F172A 0%, #334155 100%); color: white; padding: 25px 20px; border-radius: 12px; margin-bottom: 25px; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1); border-left: 5px solid #3B82F6;">
                <div style="font-size: 13px; font-weight: 800; color: #94A3B8; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 5px;">🚀 Transmitindo Lote ({idx}/{total})</div>
                <div style="font-size: 36px; font-weight: 900; letter-spacing: -0.5px; color: #FFFFFF;">👤 {nom}</div>
            </div>
            """

        if not df_cart_of.empty:
            c_kpi1_of, c_kpi2_of = st.columns([1, 4])
            c_kpi1_of.metric("TOTAL NO CARRINHO", len(df_cart_of))
            resumo_tom_of = df_cart_of.groupby('TOMADOR').size().reset_index(name='QTD')
            resumo_tom_str = " | ".join([f"{row['TOMADOR']}: {row['QTD']}" for _, row in resumo_tom_of.iterrows()])
            c_kpi2_of.info(f"Detalhamento por Cliente: {resumo_tom_str}")

            st.markdown("#### 🕵️‍♂️ Grid Interativa Cumulativa")
            df_editado_oficial = st.data_editor(
                df_cart_of,
                num_rows="dynamic",
                use_container_width=True,
                key="oficial_grid_master")

            st.markdown("---")
            st.markdown("### 🎛️ Mesa de Comando Oficial")

            # ---------------------------------------------------------------------
            # ESTADOS: IDLE e CONFIRMING (Exibe os botões em 3 colunas)
            # ---------------------------------------------------------------------
            if st.session_state.of_step in ['IDLE', 'CONFIRMING']:
                col_inj, col_disparo, col_limp = st.columns(3)

                with col_inj:
                    if st.button("🚀 1. Injetar Lote no Banco", type="primary", use_container_width=True):
                        with st.spinner("🚀 Injetando lotes no banco de dados principal e AppSheet..."):
                            try:
                                colunas_bd_oficiais = ['DATA', 'PEDIDO', 'TOMADOR', 'LABORATORIO', 'CNPJ', 'ENDERECO', 'NUMERO', 'BAIRRO', 'CIDADE', 'UF', 'CEP', 'STATUS', 'AGENTE_RAW', 'PRAZO_DIAS', 'DATA_LIMITE', 'DATA_ENTREGA', 'FOTO', 'ROMANEIO', 'ZAP_ENVIADO', 'FATURA', 'OBSERVACOES']
                                df_to_insert = df_editado_oficial.copy()
                                for c in colunas_bd_oficiais:
                                    if c not in df_to_insert.columns:
                                        df_to_insert[c] = ""
                                df_to_insert = df_to_insert[colunas_bd_oficiais].astype(str)

                                aba_m = planilha_db.worksheet("Memoria_Sistema")
                                dados_m = gsheets_call("leitura Memoria_Sistema", aba_m.get_all_values)
                                if len(dados_m) > 1:
                                    df_up_final = pd.DataFrame(dados_m[1:], columns=dados_m[0])
                                else:
                                    df_up_final = pd.DataFrame(columns=dados_m[0] if dados_m else colunas_bd_oficiais)
                                pedidos_existentes = df_up_final['PEDIDO'].astype(str).tolist()
                                df_to_insert_clean = df_to_insert[~df_to_insert['PEDIDO'].astype(str).isin(pedidos_existentes)]

                                if not df_to_insert_clean.empty:
                                    df_up_final = pd.concat([df_up_final, df_to_insert_clean], ignore_index=True)
                                    gsheets_call("limpeza Memoria_Sistema", aba_m.clear)
                                    gsheets_call(
                                        "atualizacao Memoria_Sistema",
                                        aba_m.update,
                                        "A1",
                                        [df_up_final.columns.tolist()] + df_up_final.fillna("").astype(str).values.tolist()
                                    )

                                    lista_app_of = []
                                    for _, r in df_to_insert_clean.iterrows():
                                        if str(r.get('AGENTE_RAW', '')).strip():
                                            lista_app_of.append({
                                                'PEDIDO': r['PEDIDO'], 'MOTORISTA': r['AGENTE_RAW'],
                                                'ENDERECO': r['ENDERECO'], 'NUMERO': r['NUMERO'],
                                                'BAIRRO': r['BAIRRO'], 'CIDADE': r['CIDADE'],
                                                'CEP': r['CEP'], 'LABORATORIO': r['LABORATORIO'],
                                                'TOMADOR': r['TOMADOR'], 'OBSERVACOES': r.get('OBSERVACOES', '')
                                            })
                                    if lista_app_of:
                                        despachar_para_appsheet(lista_app_of)

                                st.success("🎉 SUCESSO! O Lote foi injetado no C.C.O. Prossiga para a transmissão.")
                                time.sleep(2.0)
                                carregar_dados_completos.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao injetar: {e}")

                with col_disparo:
                    if st.session_state.of_step == 'IDLE':
                        st.markdown(render_big_metrics_off(len(df_editado_oficial), 0, 0, 0), unsafe_allow_html=True)
                        st.markdown("<div class='of-card'><div class='of-card-title'>Transmissão ao vivo</div><div class='of-card-subtitle'>Clique para abrir o modo monitorado com atualização de status por motorista.</div></div>", unsafe_allow_html=True)
                        if st.button("🚀 INICIAR TRANSMISSÃO EM LOTE AGORA", type="primary", use_container_width=True):
                            st.session_state.of_df_dispatch = df_editado_oficial.copy()
                            st.session_state.of_step = 'CONFIRMING'
                            st.rerun()
                    else: # CONFIRMING
                        st.markdown(render_big_metrics_off(len(df_editado_oficial), 0, 0, 0), unsafe_allow_html=True)
                        st.markdown("<div style='background-color:#FEF2F2; border:2px solid #FCA5A5; border-radius:12px; padding:18px; margin-bottom:14px;'><h4 style='margin:0; color:#991B1B;'>⚠️ Confirmação de Disparo Crítico</h4><p style='margin:6px 0 0 0; color:#7F1D1D;'>Você está prestes a disparar mensagens oficiais via WhatsApp para os motoristas do lote selecionado.</p></div>", unsafe_allow_html=True)
                        c_ok, c_cancel = st.columns(2)
                        if c_ok.button("✔️ CONFIRMAR E DISPARAR", type="primary", use_container_width=True):
                            st.session_state.of_step = 'PROCESSING'
                            st.rerun()
                        if c_cancel.button("❌ Cancelar Operação", use_container_width=True):
                            st.session_state.of_step = 'IDLE'
                            st.session_state.of_df_dispatch = pd.DataFrame()
                            st.rerun()

                with col_limp:
                    if st.button("🧹 3. Limpar Mesa e Finalizar", type="secondary", use_container_width=True):
                        st.session_state.df_carrinho_oficial = pd.DataFrame()
                        st.session_state.of_step = 'IDLE'
                        st.session_state.of_df_dispatch = pd.DataFrame()
                        if 'contador_oficial_temp' in st.session_state:
                            del st.session_state.contador_oficial_temp
                        st.success("Mesa limpa e pronta para o próximo lote!")
                        time.sleep(1)
                        st.rerun()

            # ---------------------------------------------------------------------
            # ESTADO: PROCESSING (Renderizado em LARGURA TOTAL da tela)
            # ---------------------------------------------------------------------
            elif st.session_state.of_step == 'PROCESSING':
                st.markdown("---")
                st.markdown("## 📡 Monitor de Transmissão Oficial")
                st.error("⚠️ **PROCESSO EM ANDAMENTO - NÃO ATUALIZE OU MUDE DE ABA!**")

                df_dispatch = st.session_state.of_df_dispatch.copy()
                if df_dispatch.empty:
                    df_dispatch = df_editado_oficial.copy()
                    st.session_state.of_df_dispatch = df_dispatch

                dict_tel = {}
                dict_nom = {}
                if not DF_AGENTES.empty:
                    for _, r in DF_AGENTES.iterrows():
                        login_ag = str(r.get('LOGIN DO AGENTE', '')).strip().lower()
                        if login_ag:
                            num_limpo = re.sub(r'\D', '', str(r.get('TELEFONE', '')))
                            if num_limpo and not num_limpo.startswith('55') and len(num_limpo) <= 11:
                                num_limpo = '55' + num_limpo
                            dict_tel[login_ag] = num_limpo
                            dict_nom[login_ag] = str(r.get('NOME DO AGENTE', '')).strip()

                agentes_selecionados = df_dispatch['AGENTE_RAW'].dropna().unique()
                total_agentes = len(agentes_selecionados)
                if total_agentes == 0:
                    st.error("Nenhum motorista válido foi encontrado para disparo.")
                    st.session_state.of_step = 'IDLE'
                    st.rerun()

                st.session_state.of_resultados_disparo = {}
                sucesso_total = 0
                falha_total = 0
                id_evento = f"OFICIAL-{datetime.now(FUSO_BR).strftime('%Y%m%d%H%M%S')}"

                col_live_of, col_side_of = st.columns([2, 1])

                with col_side_of:
                    st.markdown("<div class='of-terminal'><div style='font-size:12px; font-weight:800; letter-spacing:1.4px; text-transform:uppercase; color:#93C5FD; margin-bottom:8px;'>Painel lateral fixo</div><div style='font-size:16px; font-weight:900; color:#FFFFFF; line-height:1.2; margin-bottom:8px;'>Motorista em processamento</div><div style='font-size:13px; color:#E2E8F0; line-height:1.5;'>Este bloco acompanha a execução em tempo real e ocupa uma faixa fixa da página.</div></div>", unsafe_allow_html=True)
                    driver_placeholder = st.empty()

                with col_live_of:
                    metrics_placeholder = st.empty()
                    progress_bar = st.progress(0)
                    logs_placeholder = st.container(border=True)
                    log_table_placeholder = logs_placeholder.empty()
                    logs_df_data = []

                    metrics_placeholder.markdown(render_big_metrics_off(total_agentes, total_agentes, 0, 0), unsafe_allow_html=True)

                # Carrega a memória uma única vez e grava em lote no final do processamento.
                aba_m_status = None
                df_nuvem_status = pd.DataFrame()
                pedidos_marcacao_zap = []
                try:
                    aba_m_status = planilha_db.worksheet("Memoria_Sistema")
                    dados_status = gsheets_call("leitura status Memoria_Sistema", aba_m_status.get_all_values)
                    if len(dados_status) > 1:
                        df_nuvem_status = pd.DataFrame(dados_status[1:], columns=dados_status[0])
                    elif len(dados_status) == 1:
                        df_nuvem_status = pd.DataFrame(columns=dados_status[0])
                except Exception:
                    aba_m_status = None

                for idx_ag, ag in enumerate(agentes_selecionados):
                    if not str(ag).strip(): continue

                    try:
                        df_ag_of = df_dispatch[df_dispatch['AGENTE_RAW'] == ag]
                        ag_key = str(ag).strip().lower()
                        tel = dict_tel.get(ag_key, "")
                        nom = dict_nom.get(ag_key, str(ag).upper())

                        st.session_state.of_resultados_disparo[nom] = {'total': len(df_ag_of), 'sucesso': 0, 'pedidos': df_ag_of['PEDIDO'].tolist()}

                        if not tel: raise ValueError(f"Telefone não localizado no banco para {nom}.")

                        driver_placeholder.markdown(render_current_driver_off(nom, idx_ag + 1, total_agentes), unsafe_allow_html=True)

                        datas_na_rota = pd.to_datetime(df_ag_of['DATA'], format='%d/%m/%Y', errors='coerce').dropna().dt.date
                        if not datas_na_rota.empty:
                            d_min_zap = datas_na_rota.min().strftime('%d/%m/%Y')
                            d_max_zap = datas_na_rota.max().strftime('%d/%m/%Y')
                            data_str = f"{d_min_zap}" if d_min_zap == d_max_zap else f"{d_min_zap} a {d_max_zap}"
                        else:
                            data_str = hoje_br.strftime('%d/%m/%Y')

                        uf_agente_of = ""
                        if 'UF' in df_ag_of.columns:
                            ufs_unicos_of = df_ag_of['UF'].dropna().unique()
                            if len(ufs_unicos_of) > 0:
                                uf_agente_of = str(ufs_unicos_of[0]).upper().strip()

                        saudacao, fechamento = gerar_saudacao_spintax(nom, uf_agente_of)
                        sep1 = random.choice(['-------------------------------', '...............................', '=========================', '〰️〰️〰️〰️〰️〰️〰️〰️〰️'])
                        sep2 = random.choice(['---', '...', '===', ' '])
                        bullet = random.choice(['> 🔸', '👉', '📌', '📦', '➖'])
                        lab_lbl = random.choice(['LABORATÓRIO', 'LOCAL', 'PONTO DE COLETA'])

                        df_msg_of = df_ag_of.copy()
                        if 'CIDADE' in df_msg_of.columns:
                            df_msg_of['_CIDADE_WHATS'] = df_msg_of['CIDADE'].apply(lambda c: normalizar_cidade_operacao(c, DF_AGENTES))
                        else:
                            df_msg_of['_CIDADE_WHATS'] = ''
                        if 'BAIRRO' in df_msg_of.columns:
                            df_msg_of['_BAIRRO_WHATS'] = df_msg_of.apply(
                                lambda row: normalizar_bairro_whatsapp(row.get('BAIRRO', ''), row.get('TOMADOR', tom_sandbox)),
                                axis=1,
                            )
                        else:
                            df_msg_of['_BAIRRO_WHATS'] = ''
                        df_msg_of['_CIDADE_WHATS'] = df_msg_of['_CIDADE_WHATS'].replace('', 'SEM CIDADE')
                        df_msg_of['_BAIRRO_WHATS'] = df_msg_of['_BAIRRO_WHATS'].replace('', 'SEM BAIRRO')

                        msg_parts = [f"{saudacao}rota de 🗓️ {data_str}\n", "RESUMO DA ROTA:\n", "CIDADE | QTD", sep1]
                        tot_qtd = 0
                        for cid, count in df_msg_of['_CIDADE_WHATS'].value_counts().items():
                            msg_parts.append(f"{str(cid).strip().ljust(20)} | {count:02d}")
                            tot_qtd += count
                        msg_parts.extend([sep1, f"TOTAL | {tot_qtd:02d}\n\n", "⬇️ DETALHES:", f"{sep2}\n"])

                        for cid, group in df_msg_of.groupby('_CIDADE_WHATS', sort=False):
                            msg_parts.extend([sep2, f"{str(cid).strip().center(30)}", f"{sep2}\n"])
                            items = []
                            group = ordenar_grupo_por_bairro(group)
                            for _, row in group.iterrows():
                                bairro_msg = row.get('_BAIRRO_WHATS', normalizar_bairro_whatsapp(row.get('BAIRRO', ''), row.get('TOMADOR', tom_sandbox)))
                                item_str = f"{bullet} PEDIDO: {row.get('PEDIDO', '')}\n> 🔬 {lab_lbl}: {row.get('LABORATORIO', '')}\n> 📍 Rua: {row.get('ENDERECO', '')}, {row.get('NUMERO', '')}\n> 🏘️ Bairro: {bairro_msg}\n> 🏢 Tomador: {row.get('TOMADOR', '')}"
                                obs = str(row.get('OBSERVACOES', '')).strip()
                                if (not obs or obs.upper() in ['NAN', 'NONE']) and str(row.get('HORARIO', '')).strip():
                                    obs = f"[COLETA: {str(row.get('HORARIO', '')).strip()}]"
                                if obs and obs.upper() != 'NAN': item_str += f"\n> 📝 Aviso: {obs}"
                                items.append(item_str)
                            msg_parts.append(f"\n\n{random.choice(['. . . .', '---', ' '])}\n\n".join(items) + "\n")

                        msg_parts.append(f"\n{fechamento}")

                        INSTANCIA = "3F14E62A63D2B28DC385B20DE66F3711"
                        TOKEN = "2321563615C4242CB6031504"
                        CLIENT_TOKEN = "Ffaa43dcff1e14f0e985c91e92b24ed89S"
                                
                        try:
                            requests.post(f"https://api.z-api.io/instances/{INSTANCIA}/token/{TOKEN}/presence", json={"phone": tel, "presence": "composing"}, headers={"Client-Token": CLIENT_TOKEN}, timeout=2)
                            time.sleep(random.uniform(2.0, 3.0))
                        except BaseException: pass

                        resultado_msg = "✅"
                        if enviar_whatsapp_zapi(tel, "\n".join(msg_parts)):
                            time.sleep(random.uniform(2.0, 3.0))
                            if df_ag_of.empty: raise ValueError("Lote vazio para o motorista atual.")

                            try:
                                try: requests.post(f"https://api.z-api.io/instances/{INSTANCIA}/token/{TOKEN}/presence", json={"phone": tel, "presence": "composing"}, headers={"Client-Token": CLIENT_TOKEN}, timeout=2)
                                except BaseException: pass

                                if ag_key == 'luiz.paulo':
                                    df_para_pdf = df_dispatch[df_dispatch['UF'] == 'RJ']
                                    nome_arq_pdf = f"COLETAS_GERAL_RJ_{hoje_br.strftime('%d%m')}.pdf"
                                    pdf_bytes = gerar_pdf_rota_whatsapp("RJ - GERAL", data_str, df_para_pdf)
                                else:
                                    df_para_pdf = df_ag_of
                                    nome_arq_pdf = f"ROTA_IGO_{nom.replace(' ', '_')}_{hoje_br.strftime('%d%m')}.pdf"
                                    pdf_bytes = gerar_pdf_rota_whatsapp(nom, data_str, df_para_pdf)

                                if df_para_pdf is not None and not df_para_pdf.empty and is_autorizado_pdf:
                                    enviar_pdf_zapi(tel, pdf_bytes, nome_arq_pdf)
                                    time.sleep(2.0)
                            except Exception:
                                resultado_msg += " (Sem PDF)"

                            try:
                                try: requests.post(f"https://api.z-api.io/instances/{INSTANCIA}/token/{TOKEN}/presence", json={"phone": tel, "presence": "composing"}, headers={"Client-Token": CLIENT_TOKEN}, timeout=2)
                                except BaseException: pass
                                        
                                if ag_key == 'luiz.paulo':
                                    df_para_xls = df_dispatch[df_dispatch['UF'] == 'RJ']
                                    nome_arq_xls = f"COLETAS_GERAL_RJ_{hoje_br.strftime('%d%m')}.xlsx"
                                else:
                                    df_para_xls = df_ag_of
                                    nome_arq_xls = f"ROTA_ESTRUTURADA_{nom.replace(' ', '_')}_{hoje_br.strftime('%d%m')}.xlsx"
                                        
                                if df_para_xls is not None and not df_para_xls.empty and is_autorizado_xls:
                                    enviar_excel_zapi(tel, gerar_excel_rota_whatsapp(df_para_xls), nome_arq_xls)
                                    time.sleep(2.0)
                            except Exception:
                                resultado_msg += " (Sem XLS)"

                            sucesso_total += 1
                            st.session_state.of_resultados_disparo[nom]['sucesso'] = len(df_ag_of)
                        else:
                            resultado_msg = "❌ Erro Z-API"
                            falha_total += 1
                            st.session_state.of_resultados_disparo[nom]['sucesso'] = 0

                        pending = total_agentes - (idx_ag + 1)
                        metrics_placeholder.markdown(render_big_metrics_off(total_agentes, pending, sucesso_total, falha_total), unsafe_allow_html=True)
                        pedidos_list = df_ag_of['PEDIDO'].astype(str).tolist() if 'PEDIDO' in df_ag_of.columns else []
                        logs_df_data.append({"Hora": datetime.now(FUSO_BR).strftime('%H:%M:%S'), "Status": resultado_msg, "Motorista": nom, "Msg": f"Enviados {len(df_ag_of)} vols"})
                        log_table_placeholder.dataframe(pd.DataFrame(logs_df_data), use_container_width=True, hide_index=True)
                        progress_bar.progress((idx_ag + 1) / total_agentes)

                        pedidos_marcacao_zap.extend([str(p).strip() for p in df_ag_of['PEDIDO'].tolist() if str(p).strip()])

                    except Exception as e:
                        falha_total += 1
                        nom_err = nom if 'nom' in locals() else f"ID: {ag}"
                        st.session_state.of_resultados_disparo[nom_err] = {'total': len(df_ag_of) if 'df_ag_of' in locals() else 0, 'sucesso': 0, 'pedidos': []}
                        logs_df_data.append({"Hora": datetime.now(FUSO_BR).strftime('%H:%M:%S'), "Status": "❌ ERRO", "Motorista": nom_err, "Msg": str(e)[:35]})
                        log_table_placeholder.dataframe(pd.DataFrame(logs_df_data), use_container_width=True, hide_index=True)
                        pending = total_agentes - (idx_ag + 1)
                        metrics_placeholder.markdown(render_big_metrics_off(total_agentes, pending, sucesso_total, falha_total), unsafe_allow_html=True)
                        progress_bar.progress((idx_ag + 1) / total_agentes)

                # Persistencia unica na nuvem para reduzir requests e risco de bloqueio.
                if aba_m_status is not None and not df_nuvem_status.empty and pedidos_marcacao_zap:
                    try:
                        pedidos_unicos = list(dict.fromkeys(pedidos_marcacao_zap))
                        if 'ZAP_ENVIADO' not in df_nuvem_status.columns:
                            df_nuvem_status['ZAP_ENVIADO'] = ""
                        if 'PEDIDO' in df_nuvem_status.columns:
                            carimbo = f"SIM|{datetime.now(FUSO_BR).strftime('%H:%M')}"
                            df_nuvem_status.loc[
                                df_nuvem_status['PEDIDO'].astype(str).isin(pedidos_unicos),
                                'ZAP_ENVIADO'
                            ] = carimbo
                            gsheets_call("limpeza status Memoria_Sistema", aba_m_status.clear)
                            gsheets_call(
                                "atualizacao status Memoria_Sistema",
                                aba_m_status.update,
                                "A1",
                                [df_nuvem_status.columns.tolist()] + df_nuvem_status.fillna("").astype(str).values.tolist()
                            )
                    except Exception:
                        pass

                st.session_state.of_final_metrics = {'total': total_agentes, 'sucesso': sucesso_total, 'falhas': falha_total}
                st.session_state.of_step = 'COMPLETED'
                st.rerun()

            # ---------------------------------------------------------------------
            # ESTADO: COMPLETED (Também em largura total)
            # ---------------------------------------------------------------------
            elif st.session_state.of_step == 'COMPLETED':
                st.markdown("---")
                st.markdown("## 📊 Relatório Final da Missão")
                metrics = st.session_state.of_final_metrics
                st.markdown(render_big_metrics_off(metrics['total'], 0, metrics['sucesso'], metrics['falhas']), unsafe_allow_html=True)
                st.success("🎉 O disparo em lote foi finalizado! O histórico foi consolidado na nuvem.")

                if st.button("🔄 Liberar Mesa para Novo Disparo", use_container_width=True):
                    st.session_state.of_step = 'IDLE'
                    st.session_state.of_df_dispatch = pd.DataFrame()
                    st.session_state.of_resultados_disparo = {}
                    st.rerun()
        else:
            st.info("🛒 O carrinho está vazio. Cole uma matriz acima para começar ou marque o interruptor dos pedidos fixos para adicioná-los.")

# =============================================================================
# 🔥 MÓDULO SANDBOX (PARALELO): IMPORTAÇÕES UMOVE 🔥
# =============================================================================
elif menu == "📥 Importações Umove":
    import streamlit.components.v1 as components
    # Garante que o AgGrid está disponível neste bloco
    from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode

    UMOVE_PEDIDO_INICIAL = 900000

    st.markdown(
        """
        <style>
        div[data-testid="stTabs"] div[data-baseweb="tab-list"] {
                gap: 14px;
            margin-bottom: 14px;
                align-items: stretch;
        }
        div[data-testid="stTabs"] button[role="tab"] {
            background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%) !important;
            border: 1px solid #dbe3ef !important;
            border-radius: 12px !important;
            color: #334155 !important;
            font-weight: 700 !important;
                min-height: 50px !important;
                padding: 0 18px !important;
                line-height: 1.25 !important;
                letter-spacing: 0.15px !important;
                display: inline-flex !important;
                align-items: center !important;
                justify-content: center !important;
            box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04) !important;
            transition: all 0.2s ease !important;
        }
            div[data-testid="stTabs"] button[role="tab"] {
                padding: 0 18px !important;
                min-height: 50px !important;
                line-height: 1.25 !important;
            }
            div[data-testid="stTabs"] button[role="tab"] p {
                margin: 0 !important;
                line-height: 1.25 !important;
                white-space: nowrap !important;
            }
        div[data-testid="stTabs"] button[role="tab"]:hover {
            border-color: #93c5fd !important;
            color: #0f172a !important;
            transform: translateY(-1px);
            box-shadow: 0 6px 16px rgba(37, 99, 235, 0.10) !important;
        }
        div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
            background: linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%) !important;
            border-color: #1d4ed8 !important;
            border-radius: 12px !important;
            color: #ffffff !important;
            box-shadow: 0 10px 20px rgba(37, 99, 235, 0.22) !important;
            overflow: hidden !important;
                padding: 0 20px !important;
        }
            div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] p {
                letter-spacing: 0.2px !important;
                line-height: 1.3 !important;
            }
        div[data-testid="stVerticalBlock"] div[data-testid="stExpander"] {
            border: 1px solid #dbe3ef !important;
            border-radius: 14px !important;
            background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%) !important;
            box-shadow: 0 6px 16px rgba(15, 23, 42, 0.05) !important;
        }
        div[data-testid="stForm"],
        div[data-testid="stFileUploaderDropzone"],
        div[data-testid="stDataFrame"],
        div[data-testid="stMarkdownContainer"] > div.of-card {
            border-radius: 14px !important;
        }
        div[data-testid="stTextArea"] textarea,
        div[data-testid="stTextInput"] input,
        div[data-testid="stDateInput"] input,
        div[data-testid="stDateInput"] button,
        div[data-testid="stSelectbox"] > div[data-baseweb="select"] > div,
        div[data-testid="stMultiSelect"] > div[data-baseweb="select"] > div {
            background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%) !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 10px !important;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05) !important;
        }
        div[data-testid="stTextArea"] textarea:focus,
        div[data-testid="stTextInput"] input:focus,
        div[data-testid="stDateInput"] input:focus {
            border-color: #60a5fa !important;
            box-shadow: 0 0 0 1px #93c5fd !important;
        }
        div[data-testid="stFormSubmitButton"] > button,
        div.stButton > button:not([kind="primary"]),
        div[data-testid="stPopover"] > div > button,
        div[data-testid="stPopover"] > button {
            background: linear-gradient(180deg, #eff6ff 0%, #dbeafe 100%) !important;
            color: #0f172a !important;
            border: 1px solid #93c5fd !important;
            border-radius: 10px !important;
            font-weight: 700 !important;
            box-shadow: 0 4px 10px rgba(37, 99, 235, 0.10) !important;
            min-height: 42px !important;
            transition: all 0.2s ease !important;
        }
        div[data-testid="stFormSubmitButton"] > button:hover,
        div.stButton > button:not([kind="primary"]):hover,
        div[data-testid="stPopover"] > div > button:hover,
        div[data-testid="stPopover"] > button:hover {
            background: linear-gradient(180deg, #dbeafe 0%, #bfdbfe 100%) !important;
            border-color: #60a5fa !important;
            box-shadow: 0 8px 18px rgba(37, 99, 235, 0.18) !important;
            transform: translateY(-1px) !important;
        }
        div.stButton > button[kind="primary"],
        div[data-testid="stFormSubmitButton"] > button[kind="primary"] {
            background: linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%) !important;
            border: 1px solid #1d4ed8 !important;
            color: #ffffff !important;
            box-shadow: 0 10px 20px rgba(37, 99, 235, 0.22) !important;
        }
        div.stButton > button[kind="primary"]:hover,
        div[data-testid="stFormSubmitButton"] > button[kind="primary"]:hover {
            background: linear-gradient(135deg, #0284c7 0%, #1d4ed8 100%) !important;
            border-color: #1e40af !important;
            color: #ffffff !important;
        }
        div[data-testid="stToggle"] label,
        div[data-testid="stCheckbox"] label {
            font-weight: 700 !important;
            color: #334155 !important;
        }
        .ag-theme-alpine {
            --ag-font-family: Inter, sans-serif;
            --ag-font-size: 13px;
            --ag-row-height: 40px;
            --ag-header-height: 44px;
            border: 1px solid #dbe3ef !important;
            border-radius: 12px !important;
            overflow: hidden !important;
            box-shadow: 0 8px 20px rgba(15, 23, 42, 0.07) !important;
            background-color: #ffffff !important;
        }
        .ag-theme-alpine .ag-root-wrapper,
        .ag-theme-alpine .ag-root-wrapper-body,
        .ag-theme-alpine .ag-body-viewport {
            background-color: #ffffff !important;
        }
        .ag-theme-alpine .ag-header {
            background: linear-gradient(180deg, #f8fafc 0%, #e2e8f0 100%) !important;
            border-bottom: 1px solid #cbd5e1 !important;
        }
        .ag-theme-alpine .ag-header-cell {
            border-right: 1px solid #dbe3ef !important;
            padding-top: 5px !important;
            padding-bottom: 5px !important;
        }
        .ag-theme-alpine .ag-header-cell-text {
            color: #0f172a !important;
            font-weight: 800 !important;
            font-size: 12px !important;
            letter-spacing: 0.35px !important;
            text-transform: uppercase !important;
        }
        .ag-theme-alpine .ag-row {
            border-bottom: 1px solid #eef2f7 !important;
            transition: background-color 0.2s ease !important;
        }
        .ag-theme-alpine .ag-row:hover {
            background-color: #dbeafe !important;
            box-shadow: inset 3px 0 0 #2563eb !important;
        }
        .ag-theme-alpine .ag-row-odd {
            background: linear-gradient(90deg, #ffffff 0%, #fcfdff 100%) !important;
        }
        .ag-theme-alpine .ag-row-even {
            background: linear-gradient(90deg, #f8fafc 0%, #f1f5f9 100%) !important;
        }
        .ag-theme-alpine .ag-cell {
            display: flex !important;
            align-items: center !important;
            border-right: 1px solid #eef2f7 !important;
        }
        .ag-theme-alpine .ag-paging-panel {
            background: #f8fafc !important;
            border-top: 1px solid #dbe3ef !important;
            padding: 8px 10px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # 🔥 PING SILENCIOSO (ANTI-TIMEOUT DO RENDER) 🔥
    components.html(
        """
        <script>
        setInterval(function() {
            fetch(window.location.href);
        }, 240000);
        </script>
        """,
        height=0, width=0
    )

    st.markdown(
        "<div class='dinamic-border'><h3 class='dinamic-text' style='margin:0;'>🛠️ Zona de Importação & Central de Envios</h3></div>",
        unsafe_allow_html=True)

    if planilha_sandbox is None or planilha_db is None:
        st.error("❌ Erro de conexão com as planilhas no Drive. Verifique as permissões.")
        st.stop()

    if "df_sandbox_mem" not in st.session_state:
        st.session_state.df_sandbox_mem = pd.DataFrame()
    if "df_preview_sb" not in st.session_state:
        st.session_state.df_preview_sb = pd.DataFrame()

    # --- INÍCIO: VARIÁVEIS DA MÁQUINA DE ESTADOS ---
    if "df_sandbox_mem" not in st.session_state:
        st.session_state.df_sandbox_mem = pd.DataFrame()
    if "df_preview_sb" not in st.session_state:
        st.session_state.df_preview_sb = pd.DataFrame()

    @st.cache_data(ttl=600, show_spinner=False)
    def carregar_agendamentos_fixos():
        colunas_fixos_padrao = [
            'ID_REGRA', 'TOMADOR', 'LABORATORIO', 'ENDERECO', 'NUMERO', 'BAIRRO', 'CIDADE', 'UF', 'CEP',
            'OBSERVACOES', 'MOTORISTA', 'SCHEDULE_TYPE', 'SEG', 'TER', 'QUA', 'QUI', 'SEX', 'SAB', 'STATUS'
        ]
        try:
            aba = planilha_db.worksheet("Agendamentos_Fixos")
            dados = aba.get_all_values()
            if len(dados) > 1:
                df_fixos = pd.DataFrame(dados[1:], columns=dados[0])
                for col in colunas_fixos_padrao:
                    if col not in df_fixos.columns:
                        df_fixos[col] = ""

                df_fixos['SCHEDULE_TYPE'] = df_fixos['SCHEDULE_TYPE'].astype(str).str.strip().str.lower()
                df_fixos.loc[~df_fixos['SCHEDULE_TYPE'].isin(['visita_tox', 'entrega']), 'SCHEDULE_TYPE'] = 'visita_tox'
                return df_fixos[colunas_fixos_padrao]
        except Exception:
            pass
        return pd.DataFrame(columns=colunas_fixos_padrao)

    # --- INÍCIO: VARIÁVEIS DA MÁQUINA DE ESTADOS ---
    if "umove_lote_atual_id" not in st.session_state:
        st.session_state.umove_lote_atual_id = None

    def gerenciar_estado_lote(acao, lote_id=None, df_carrinho=None, resultados=None):
        if planilha_sandbox is None:
            return pd.DataFrame() if acao == "LISTAR_RASCUNHOS" else False
        try:
            try:
                aba = planilha_sandbox.worksheet("Historico_Disparos_Umove")
            except:
                aba = planilha_sandbox.add_worksheet("Historico_Disparos_Umove", 200, 20)
                aba.update("A1", [["ID_EVENTO", "DATA_DISPARO", "PERIODO", "MOTORISTA", "TOTAL_PEDIDOS", "SUCESSOS", "FALHAS", "PEDIDOS", "STATUS_LOTE", "DADOS_JSON"]])
                    
            dados = aba.get_all_values()
            cabecalho = dados[0] if len(dados) > 0 else []
                    
            if "STATUS_LOTE" not in cabecalho:
                cabecalho.extend(["STATUS_LOTE", "DADOS_JSON"])
                aba.update("A1", [cabecalho])
                        
            # 🔥 CORREÇÃO ANTI-CRASH: Força todas as linhas a terem o mesmo tamanho da coluna do cabeçalho
            dados_pad = []
            for linha in dados[1:]:
                linha_completa = linha + [""] * (len(cabecalho) - len(linha))
                dados_pad.append(linha_completa)
                        
            df_hist = pd.DataFrame(dados_pad, columns=cabecalho) if dados_pad else pd.DataFrame(columns=cabecalho)
                    
            if acao == "SALVAR_RASCUNHO":
                if df_carrinho is None or df_carrinho.empty:
                    return False
                json_dados = df_carrinho.to_json(orient='records')
                agora = datetime.now(FUSO_BR).strftime('%d/%m/%Y %H:%M:%S')
                        
                if lote_id in df_hist['ID_EVENTO'].values:
                    linha_idx = df_hist.index[df_hist['ID_EVENTO'] == lote_id][0] + 2
                            
                    # Atualização em lote (Batch Update) - Uma única requisição!
                    aba.update(
                        f"{gspread.utils.rowcol_to_a1(linha_idx, cabecalho.index('TOTAL_PEDIDOS') + 1)}", 
                        [[len(df_carrinho)]]
                    )
                    aba.update(
                        f"{gspread.utils.rowcol_to_a1(linha_idx, cabecalho.index('STATUS_LOTE') + 1)}", 
                        [["RASCUNHO", json_dados]]
                    )
                else:
                    nova_linha = {c: "" for c in cabecalho}
                    nova_linha["ID_EVENTO"] = lote_id
                    nova_linha["DATA_DISPARO"] = agora
                    nova_linha["PERIODO"] = "Lote em Rascunho"
                    nova_linha["TOTAL_PEDIDOS"] = len(df_carrinho)
                    nova_linha["STATUS_LOTE"] = "RASCUNHO"
                    nova_linha["DADOS_JSON"] = json_dados
                    aba.append_row([nova_linha.get(c, "") for c in cabecalho], value_input_option='USER_ENTERED')
                            
            elif acao == "LISTAR_RASCUNHOS":
                if not df_hist.empty and 'STATUS_LOTE' in df_hist.columns:
                    return df_hist[df_hist['STATUS_LOTE'].str.contains("RASCUNHO", case=False, na=False)]
                return pd.DataFrame()
                        
            elif acao == "EXCLUIR_RASCUNHO":
                if lote_id in df_hist['ID_EVENTO'].values:
                    linha_idx = df_hist.index[df_hist['ID_EVENTO'] == lote_id][0] + 2
                    aba.delete_rows(int(linha_idx))
                            
            elif acao == "CONCLUIR":
                if lote_id in df_hist['ID_EVENTO'].values:
                    linha_idx = df_hist.index[df_hist['ID_EVENTO'] == lote_id][0] + 2
                    suc = sum([d.get('sucesso', 0) for d in resultados.values()]) if resultados else 0
                    fal = sum([(d.get('total', 0) - d.get('sucesso', 0)) for d in resultados.values()]) if resultados else 0
                            
                    motoristas_list = list(resultados.keys()) if resultados else []
                    motoristas_str = ", ".join(motoristas_list)[:200]
                            
                    pedidos_list = []
                    if resultados:
                        for d in resultados.values(): pedidos_list.extend(d.get('pedidos', []))
                    pedidos_text = ", ".join([str(p) for p in pedidos_list])[:3000]

                    aba.update_cell(linha_idx, cabecalho.index("STATUS_LOTE") + 1, "CONCLUÍDO")
                    aba.update_cell(linha_idx, cabecalho.index("DADOS_JSON") + 1, "[]") # Apaga o peso da memória
                    aba.update_cell(linha_idx, cabecalho.index("SUCESSOS") + 1, suc)
                    aba.update_cell(linha_idx, cabecalho.index("FALHAS") + 1, fal)
                    aba.update_cell(linha_idx, cabecalho.index("MOTORISTA") + 1, motoristas_str)
                    aba.update_cell(linha_idx, cabecalho.index("PEDIDOS") + 1, pedidos_text)
                else:
                    return False
            return True
        except Exception as e:
            return pd.DataFrame() if acao == "LISTAR_RASCUNHOS" else False

    def obter_proximo_id_umove_seguro_global():
        candidatos = []

        if not st.session_state.df_sandbox_mem.empty and 'PEDIDO' in st.session_state.df_sandbox_mem.columns:
            candidatos.append(st.session_state.df_sandbox_mem[['PEDIDO']].copy())

        if not st.session_state.df_preview_sb.empty and 'PEDIDO' in st.session_state.df_preview_sb.columns:
            candidatos.append(st.session_state.df_preview_sb[['PEDIDO']].copy())

        try:
            df_rascunhos = gerenciar_estado_lote("LISTAR_RASCUNHOS")
            if df_rascunhos is not None and not df_rascunhos.empty and 'DADOS_JSON' in df_rascunhos.columns:
                for dados_json in df_rascunhos['DADOS_JSON'].dropna().astype(str):
                    try:
                        df_rasc = pd.read_json(io.StringIO(dados_json), orient='records')
                        if not df_rasc.empty and 'PEDIDO' in df_rasc.columns:
                            candidatos.append(df_rasc[['PEDIDO']].copy())
                    except Exception:
                        pass
        except Exception:
            pass

        df_base_ids = pd.concat(candidatos, ignore_index=True) if candidatos else pd.DataFrame(columns=['PEDIDO'])
        proximo_base = obter_proximo_id(df_base_ids, minimo_inicial=UMOVE_PEDIDO_INICIAL)

        try:
            aba_contador = planilha_sandbox.worksheet("Contador")
            val = aba_contador.acell('A1').value
            if val and str(val).isdigit():
                proximo_base = max(proximo_base, int(val))
        except Exception:
            pass

        if 'contador_temp' in st.session_state:
            proximo_base = max(proximo_base, int(st.session_state.contador_temp))

        return max(proximo_base, UMOVE_PEDIDO_INICIAL)
    # --- FIM: MOTOR DE ESTADOS ---

    if 'cep_version_of' not in st.session_state:
        st.session_state['cep_version_of'] = 0

    tab_matriz, tab_fixos, tab_carrinho, tab_envios, tab_backup = st.tabs(
        ["📋 1. Colar Matriz", "🔁 2. Gestão de Pedidos Fixos", "🛒 3. Carrinho & Arquivos", "🚀 4. Central de Envios", "🛟 5. Recuperação Offline"])

    # -------------------------------------------------------------------------
    # ABA 1: COLAR MATRIZ TRADICIONAL (Layout Super Premium + Contador Blindado)
    # -------------------------------------------------------------------------
    with tab_matriz:
        # Cabeçalho Premium
        st.markdown("""
        <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 25px;">
            <div style="background-color: #EFF6FF; padding: 12px 15px; border-radius: 12px; border: 1px solid #BFDBFE; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                <span style="font-size: 26px;">📋</span>
            </div>
            <div>
                <h3 style="margin: 0; color: #1E293B; font-weight: 800;">Importação de Matriz Externa</h3>
                <p style="margin: 0; color: #64748B; font-size: 13px;">Insira os parâmetros operacionais e cole os dados brutos para mapeamento geográfico automático.</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
                
        # Passo 1: Parâmetros
        st.markdown("#### 1️⃣ Configuração da Carga")
        with st.container(border=True):
            c1_sb, c2_sb = st.columns([2, 1], vertical_alignment="center")
            with c1_sb:
                tom_sandbox = st.selectbox("🏢 Tomador Desta Carga *", ["Selecione..."] + CLIENTES_AUTORIZADOS, key="tom_sb")
            with c2_sb:
                dt_sandbox = st.date_input("📅 Data da Rota *", format="DD/MM/YYYY", value=hoje_br, key="dt_sb")

        # Passo 2: Inserção
        st.markdown("#### 2️⃣ Inserção de Dados Legados")
        with st.container(border=True):
            st.markdown("<span style='font-size:13px; font-weight:bold; color:#475569;'>Área de Transferência (Ctrl+V)</span>", unsafe_allow_html=True)
            txt_sb = st.text_area("Dados Brutos", height=180, placeholder="Cole aqui as colunas copiadas do Excel ou do seu sistema legado...", label_visibility="collapsed")
                    
            st.write("") # Respiro visual
            if st.button("🔍 PROCESSAR E VALIDAR MATRIZ", type="primary", use_container_width=True):
                if not txt_sb or tom_sandbox == "Selecione...":
                    st.error("⚠️ **Bloqueio:** Por favor, selecione o Tomador e cole os dados da matriz antes de processar.")
                else:
                    with st.spinner("Analisando estrutura de colunas e cruzando dados geográficos..."):
                        try:
                            delim = '\t' if '\t' in txt_sb else (';' if ';' in txt_sb else ',')
                            df_raw_sb = pd.read_csv(io.StringIO(txt_sb), sep=delim, header=None, dtype=str).fillna("")

                            idx_h, max_matches = 0, 0
                            for i in range(min(15, len(df_raw_sb))):
                                row_str = unicodedata.normalize('NFKD', " ".join(df_raw_sb.iloc[i].astype(str).values).upper()).encode('ASCII', 'ignore').decode('utf-8')
                                matches = sum(1 for kw in ['PEDIDO', 'CODIGO', 'CNPJ', 'CPF', 'DOCUMENTO', 'DOC', 'ID', 'CIDADE', 'MUNIC', 'LABORAT', 'POSTO', 'NOME', 'CLIENTE', 'ENDERE', 'RUA', 'BAIRRO', 'CEP', 'HORARIO', 'FUNCIONAMENTO', 'OBSERVA'] if kw in row_str)
                                if matches > max_matches:
                                    max_matches, idx_h = matches, i

                            df_limpo_sb = df_raw_sb.iloc[idx_h + 1:].copy()
                            df_limpo_sb.columns = [str(c).strip() for c in df_raw_sb.iloc[idx_h].values]
                            df_limpo_sb = df_limpo_sb.loc[:, ~df_limpo_sb.columns.duplicated()]

                            for col in df_limpo_sb.columns:
                                df_limpo_sb[col] = df_limpo_sb[col].apply(tratar_texto_global)

                            mapa_sb = {}
                            for c in df_limpo_sb.columns:
                                c_upper = str(c).upper().strip()
                                cl = ''.join(e for e in unicodedata.normalize('NFKD', c_upper).encode('ASCII', 'ignore').decode('utf-8') if e.isalnum())
                                if c_upper in ['Nº', 'N°', 'N.', 'N', 'NUM', 'NUMERO', 'NRO'] or cl in ['N', 'NO', 'NR', 'NUM', 'NUMERO']: mapa_sb[c] = 'NUMERO'
                                elif any(x in cl for x in ['PEDIDO', 'SOLICITA', 'CODIGO', 'CDIGO']) or cl == 'ID': mapa_sb[c] = 'PEDIDO'
                                elif any(x in cl for x in ['CNPJ', 'CPF', 'DOCUMENTO', 'DOC']): mapa_sb[c] = 'CNPJ'
                                elif any(x in cl for x in ['LABORAT', 'CLINIC', 'POSTO', 'NOME', 'CLIENTE']): mapa_sb[c] = 'LABORATORIO'
                                elif any(x in cl for x in ['ENDERE', 'RUA', 'LOGRADOURO', 'AVENIDA']): mapa_sb[c] = 'ENDERECO'
                                elif 'BAIRRO' in cl: mapa_sb[c] = 'BAIRRO'
                                elif any(x in cl for x in ['CIDADE', 'MUNIC']): mapa_sb[c] = 'CIDADE'
                                elif any(x in cl for x in ['ESTADO', 'UF']): mapa_sb[c] = 'UF'
                                elif 'CEP' in cl: mapa_sb[c] = 'CEP'
                                elif any(x in cl for x in ['HORARIO', 'HORA', 'FUNCIONAMENTO', 'PERIODO']): mapa_sb[c] = 'HORARIO'
                                elif any(x in cl for x in ['OBSERVA', 'OBS', 'NOTA']): mapa_sb[c] = 'OBSERVACOES'

                            df_limpo_sb.rename(columns=mapa_sb, inplace=True)

                            for c in ['PEDIDO', 'LABORATORIO', 'CNPJ', 'CEP', 'ENDERECO', 'NUMERO', 'BAIRRO', 'CIDADE', 'UF', 'OBSERVACOES']:
                                if c not in df_limpo_sb.columns:
                                    df_limpo_sb[c] = ""

                            if 'HORARIO' in df_limpo_sb.columns:
                                for idx, row in df_limpo_sb.iterrows():
                                    horario_val = str(row['HORARIO']).strip()
                                    obs_val = str(row['OBSERVACOES']).strip()
                                    if horario_val and horario_val.upper() not in ['NAN', 'NONE']:
                                        nova_obs = f"[COLETA: {horario_val}]"
                                        if obs_val and obs_val.upper() not in ['NAN', 'NONE']:
                                            nova_obs += f" - {obs_val}"
                                        df_limpo_sb.at[idx, 'OBSERVACOES'] = nova_obs

                            df_limpo_sb['PEDIDO'] = ""
                            for idx, row in df_limpo_sb.iterrows():
                                e, n, b = str(row['ENDERECO']), str(row['NUMERO']), str(row['BAIRRO'])
                                if e and (not n or not b):
                                    cep_m = re.search(r'(\d{5}-?\d{3})', e)
                                    if cep_m:
                                        df_limpo_sb.at[idx, 'CEP'] = cep_m.group(1)
                                        e = e.replace(cep_m.group(1), '').strip(' ,-')
                                    if ',' in e and not n:
                                        pts = e.split(',')
                                        df_limpo_sb.at[idx, 'ENDERECO'], df_limpo_sb.at[idx, 'NUMERO'] = pts[0].strip(), pts[1].strip()

                            df_limpo_sb['UF'] = df_limpo_sb['UF'].astype(str).str.upper().str.strip()
                            df_limpo_sb['TOMADOR'] = tom_sandbox
                            df_limpo_sb['DATA'] = dt_sandbox.strftime("%d/%m/%Y")

                            df_limpo_sb['CIDADE'] = df_limpo_sb['CIDADE'].apply(lambda c: normalizar_cidade_operacao(corrigir_cidade_inteligente(c, DF_AGENTES), DF_AGENTES))
                            df_limpo_sb['AGENTE_RAW'] = df_limpo_sb.apply(lambda r: obter_login_agente(r['CIDADE'], r['BAIRRO'], r['LABORATORIO'], r['ENDERECO'], DF_AGENTES), axis=1)
                            # A normalizacao ocorre apos o roteamento para nao quebrar mapeamentos legados de rota.
                            df_limpo_sb['BAIRRO'] = df_limpo_sb['BAIRRO'].apply(normalizar_bairro_whatsapp)

                            df_final_sb = df_limpo_sb[df_limpo_sb['LABORATORIO'].str.strip() != ""][['DATA', 'TOMADOR', 'PEDIDO', 'LABORATORIO', 'CNPJ', 'ENDERECO', 'NUMERO', 'BAIRRO', 'CIDADE', 'UF', 'CEP', 'OBSERVACOES', 'AGENTE_RAW']]

                            st.session_state.df_preview_sb = df_final_sb
                            time.sleep(0.5)
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Falha crítica no processamento da matriz: {e}")

        # Passo 3: PREVIEW DA MATRIZ - Seção Visual de Tratamento de Erros
        if not st.session_state.df_preview_sb.empty:
            st.markdown("---")
            st.markdown("#### 3️⃣ Validação de Roteirização")
            df_preview = st.session_state.df_preview_sb
            mask_err = (df_preview['AGENTE_RAW'].astype(str).str.strip() == "") | (df_preview['AGENTE_RAW'].astype(str).str.upper() == "NAN")
            df_err = df_preview[mask_err]
            df_ok = df_preview[~mask_err]

            if not df_err.empty:
                st.markdown(f"""
                <div style='background-color:#FEF2F2; border: 1px solid #FCA5A5; padding:20px; border-radius:12px; margin-bottom:20px; display:flex; gap:15px; align-items:center; box-shadow: 0 4px 6px rgba(220, 38, 38, 0.05);'>
                    <div style='font-size: 38px;'>🚨</div>
                    <div>
                        <h5 style='color:#991B1B; margin:0; font-weight:800; font-size:16px;'>Tratamento de Exceções Requerido</h5>
                        <p style='color:#7F1D1D; font-size:14px; margin:5px 0 0 0;'>O motor de IA detectou <b>{len(df_err)} pedido(s)</b> sem motorista correspondente na base geográfica. Atribua um motorista manualmente para liberar a carga.</p>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                        
                with st.container(border=True):
                    correcoes = {}
                    logins_disp = sorted(DF_AGENTES['LOGIN DO AGENTE'].unique().tolist()) if not DF_AGENTES.empty else []
                            
                    # Layout limpo para correção manual
                    for idx, row in df_err.iterrows():
                        cx1, cx2 = st.columns([2.5, 1])
                        cx1.markdown(f"<div style='padding-top:8px;'>🔬 <b>{row['LABORATORIO']}</b> <br><span style='font-size:12px; color:#64748B;'>📍 {row['CIDADE']} - {row['BAIRRO']}</span></div>", unsafe_allow_html=True)
                        correcoes[idx] = cx2.selectbox(f"Motorista", ["Selecione..."] + logins_disp, key=f"fix_mot_sb_{idx}", label_visibility="collapsed")
                        st.markdown("<hr style='margin: 10px 0; border-color: #F1F5F9;'>", unsafe_allow_html=True)
                            
                    if st.button("💾 Salvar Roteirização Manual e Validar", type="primary", use_container_width=True):
                        novas_rotas = []
                        for idx, novo_mot in correcoes.items():
                            if novo_mot != "Selecione...":
                                st.session_state.df_preview_sb.at[idx, 'AGENTE_RAW'] = novo_mot
                                r_cid = str(st.session_state.df_preview_sb.at[idx, 'CIDADE'])
                                r_bai = str(st.session_state.df_preview_sb.at[idx, 'BAIRRO'])
                                rota_str = " ➔ ".join([p for p in [limpar_nome_local_rota(r_cid), limpar_nome_local_rota(r_bai)] if p])
                                if not DF_AGENTES.empty:
                                    dados_ag = DF_AGENTES[DF_AGENTES['LOGIN DO AGENTE'] == novo_mot].iloc[0]
                                    novas_rotas.append({"ROTA MAPEADA": rota_str, "LOGIN DO AGENTE": novo_mot, "NOME DO AGENTE": dados_ag['NOME DO AGENTE'], "TELEFONE": dados_ag['TELEFONE']})

                        if novas_rotas:
                            try:
                                df_novas_rotas = pd.DataFrame(novas_rotas)
                                aba_agentes = planilha_db.worksheet("Agentes")
                                dados_atuais_ag = aba_agentes.get_all_values()
                                df_ag_atual = pd.DataFrame(dados_atuais_ag[1:], columns=dados_atuais_ag[0]) if len(dados_atuais_ag) > 1 else pd.DataFrame(columns=["ROTA MAPEADA", "LOGIN DO AGENTE", "NOME DO AGENTE", "TELEFONE"])
                                df_novo = pd.concat([df_ag_atual, df_novas_rotas], ignore_index=True).drop_duplicates(subset=["ROTA MAPEADA", "LOGIN DO AGENTE"])
                                aba_agentes.clear()
                                aba_agentes.update("A1", [df_novo.columns.tolist()] + df_novo.fillna("").astype(str).values.tolist())
                                carregar_dados_agentes.clear()
                            except Exception as e:
                                st.warning(f"Aviso: Não foi possível salvar a rota inteligente no banco de dados: {e}")
                        st.rerun()
            else:
                st.markdown(f"""
                <div style='background-color:#F0FDF4; border: 1px solid #BBF7D0; padding:20px; border-radius:12px; margin-bottom:20px; display:flex; gap:15px; align-items:center; box-shadow: 0 4px 6px rgba(22, 101, 52, 0.05);'>
                    <div style='font-size: 38px;'>✅</div>
                    <div>
                        <h5 style='color:#166534; margin:0; font-weight:800; font-size:16px;'>Validação Concluída com Sucesso!</h5>
                        <p style='color:#14532D; font-size:14px; margin:5px 0 0 0;'>A IA processou e roteirizou <b>{len(df_ok)} pedidos</b> com base na malha de agentes disponível.</p>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                        
                with st.container(border=True):
                    st.dataframe(df_ok, hide_index=True, use_container_width=True, height=250)
                        
                st.write("")
                if st.button("➕ ADICIONAR TUDO AO CARRINHO DE EXPEDIÇÃO", type="primary", use_container_width=True, key="add_carrinho_sb"):
                    with st.spinner("Registrando identificadores de controle (IDs) blindados..."):
                        try:
                            prox_id_sb = obter_proximo_id_umove_seguro_global()

                            aba_contador = None
                            try:
                                aba_contador = planilha_sandbox.worksheet("Contador")
                            except Exception:
                                try:
                                    aba_contador = planilha_sandbox.add_worksheet(title="Contador", rows=10, cols=10)
                                    aba_contador.update("A1", [[str(prox_id_sb)]])
                                except Exception:
                                    try:
                                        aba_contador = planilha_sandbox.worksheet("Contador")
                                    except Exception:
                                        pass

                            for idx, row in df_ok.iterrows():
                                df_ok.at[idx, 'PEDIDO'] = str(prox_id_sb)
                                prox_id_sb += 1
                                        
                            st.session_state.contador_temp = prox_id_sb

                            if aba_contador:
                                try: aba_contador.update("A1", [[str(prox_id_sb)]])
                                except Exception: pass

                            if st.session_state.df_sandbox_mem.empty:
                                st.session_state.df_sandbox_mem = df_ok
                            else:
                                st.session_state.df_sandbox_mem = pd.concat([st.session_state.df_sandbox_mem, df_ok], ignore_index=True)

                            if st.session_state.umove_lote_atual_id is None:
                                st.session_state.umove_lote_atual_id = f"LOTE-{datetime.now(FUSO_BR).strftime('%d%m%H%M')}"
                            gerenciar_estado_lote("SALVAR_RASCUNHO", st.session_state.umove_lote_atual_id, st.session_state.df_sandbox_mem)

                            st.session_state.df_preview_sb = pd.DataFrame()
                            st.session_state.ui_toast = {'msg': "Importação concluída! Carga consolidada no Carrinho de Expedição.", 'icon': "🚀"}
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao injetar dados no carrinho: {e}")

    # -------------------------------------------------------------------------
    # ABA 2: GESTÃO DE PEDIDOS FIXOS (A FÁBRICA) - ATUALIZADO COM AGGRID
    # -------------------------------------------------------------------------
    with tab_fixos:
        st.markdown("#### 🏭 Criar Novo Agendamento Fixo")

        cols_fixos = ['ID_REGRA', 'TOMADOR', 'LABORATORIO', 'ENDERECO', 'NUMERO', 'BAIRRO', 'CIDADE', 'UF', 'CEP', 'OBSERVACOES', 'MOTORISTA', 'SCHEDULE_TYPE', 'SEG', 'TER', 'QUA', 'QUI', 'SEX', 'SAB', 'STATUS']
        df_regras = carregar_agendamentos_fixos()
                
        try:
            aba_fixos = planilha_db.worksheet("Agendamentos_Fixos")
        except Exception:
            try:
                aba_fixos = planilha_db.add_worksheet("Agendamentos_Fixos", 100, 20)
                aba_fixos.update("A1", [cols_fixos])
            except Exception:
                pass

        if 'f_rua' not in st.session_state: st.session_state['f_rua'] = ""
        if 'f_bai' not in st.session_state: st.session_state['f_bai'] = ""
        if 'f_cid' not in st.session_state: st.session_state['f_cid'] = ""
        if 'f_uf' not in st.session_state: st.session_state['f_uf'] = ""
        if 'cep_version' not in st.session_state: st.session_state['cep_version'] = 0

        def buscar_cep_fixo_callback():
            chave_atual = f"cep_input_fixo_{st.session_state.cep_version}"
            cep_digitado = st.session_state.get(chave_atual, "")
            cep_limpo = re.sub(r'\D', '', cep_digitado)
            if len(cep_limpo) == 8:
                try:
                    resp = requests.get(f"https://viacep.com.br/ws/{cep_limpo}/json/").json()
                    if "erro" not in resp:
                        st.session_state['f_rua'] = padronizar_texto(resp.get("logradouro", ""))
                        st.session_state['f_bai'] = padronizar_texto(resp.get("bairro", ""))
                        st.session_state['f_cid'] = padronizar_texto(resp.get("localidade", ""))
                        st.session_state['f_uf'] = padronizar_texto(resp.get("uf", ""))
                except Exception: pass

        cc1_f, cc2_f, cc3_f = st.columns([2, 1, 3], vertical_alignment="bottom")
        key_dinamica = f"cep_input_fixo_{st.session_state.cep_version}"
        cc1_f.text_input("Digite o CEP e aperte ENTER", max_chars=9, key=key_dinamica, on_change=buscar_cep_fixo_callback)

        if cc2_f.button("🔍 Buscar CEP", key="btn_busc_cep_fixo", use_container_width=True):
            buscar_cep_fixo_callback()

        st.markdown("---")

        with st.form("form_novo_fixo", clear_on_submit=True):
            col_f1, col_f2 = st.columns(2)
            f_tomador = col_f1.selectbox("Tomador *", ["Selecione..."] + CLIENTES_AUTORIZADOS)
            f_lab = col_f2.text_input("Ponto de Coleta / Laboratório *")

            c_rua, c_num = st.columns([3, 1])
            f_rua = c_rua.text_input("Logradouro *", value=st.session_state['f_rua'])
            f_num = c_num.text_input("Número *")

            c_bai, c_cid, c_uf = st.columns([2, 2, 1])
            f_bai = c_bai.text_input("Bairro *", value=st.session_state['f_bai'])
            f_cid = c_cid.text_input("Cidade *", value=st.session_state['f_cid'])
            f_uf = c_uf.text_input("UF *", value=st.session_state['f_uf'])

            f_obs = st.text_input("Observações Padrão (Ex: [COLETA: 08:00 - 12:00])")

            st.markdown("**Dias da Semana com Coleta Fixa:**")
            d1, d2, d3, d4, d5, d6 = st.columns(6)
            b_seg = d1.checkbox("Segunda")
            b_ter = d2.checkbox("Terça")
            b_qua = d3.checkbox("Quarta")
            b_qui = d4.checkbox("Quinta")
            b_sex = d5.checkbox("Sexta")
            b_sab = d6.checkbox("Sábado")

            logins_disp = sorted(DF_AGENTES['LOGIN DO AGENTE'].unique().tolist()) if not DF_AGENTES.empty else []
            f_agente = st.selectbox("Motorista Fixo:", ["Automático (Por Rota)"] + logins_disp)
            f_schedule_type = st.selectbox("Tipo no AGD para este fixo:", ["visita_tox", "entrega"], index=0)

            if st.form_submit_button("💾 Salvar Agendamento Fixo", type="primary"):
                if f_tomador == "Selecione..." or not f_lab or not f_rua or not f_num or not f_bai or not f_cid:
                    st.error("Preencha todos os campos obrigatórios (*).")
                elif not any([b_seg, b_ter, b_qua, b_qui, b_sex, b_sab]):
                    st.error("Selecione pelo menos um dia da semana.")
                else:
                    with st.spinner("Salvando regra..."):
                        if f_agente == "Automático (Por Rota)":
                            f_agente = obter_login_agente(f_cid, f_bai, f_lab, f_rua, DF_AGENTES)

                        nova_regra = [
                            f"REG-{str(uuid.uuid4())[:6].upper()}", f_tomador, padronizar_texto(f_lab),
                            padronizar_texto(f_rua), padronizar_texto(f_num), padronizar_texto(f_bai),
                            padronizar_texto(f_cid), padronizar_texto(f_uf), st.session_state.get(key_dinamica, ""),
                            str(f_obs), f_agente, f_schedule_type, "SIM" if b_seg else "NAO", "SIM" if b_ter else "NAO", "SIM" if b_qua else "NAO",
                            "SIM" if b_qui else "NAO", "SIM" if b_sex else "NAO", "SIM" if b_sab else "NAO", "ATIVO"
                        ]
                        try:
                            aba_fixos.append_row(nova_regra)
                            carregar_agendamentos_fixos.clear()
                            st.success("✅ Regra Fixa cadastrada com sucesso!")
                            st.session_state['f_rua'] = ""
                            st.session_state['f_bai'] = ""
                            st.session_state['f_cid'] = ""
                            st.session_state['f_uf'] = ""
                            st.session_state.cep_version += 1
                            time.sleep(1.5)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro: {e}")

        st.markdown("---")
        st.markdown("#### 📋 Gerenciar Laboratórios Fixos")
        st.info("💡 **Edite diretamente na tabela dando dois cliques!** Para deletar uma regra, marque a caixa (checkbox) na primeira coluna e clique em 'Excluir Selecionados'.")

        if not df_regras.empty:
            logins_p_tabela = sorted(DF_AGENTES['LOGIN DO AGENTE'].unique().tolist()) if not DF_AGENTES.empty else []

            gb_fixos = GridOptionsBuilder.from_dataframe(df_regras)
            gb_fixos.configure_default_column(editable=True, resizable=True, sortable=True, filter=True)
                    
            opcoes_sim_nao = ["SIM", "NAO"]
            for col_dia in ["SEG", "TER", "QUA", "QUI", "SEX", "SAB"]:
                gb_fixos.configure_column(col_dia, cellEditor='agSelectCellEditor', cellEditorParams={'values': opcoes_sim_nao})
                    
            gb_fixos.configure_column("STATUS", cellEditor='agSelectCellEditor', cellEditorParams={'values': ["ATIVO", "INATIVO"]})
            gb_fixos.configure_column("MOTORISTA", cellEditor='agSelectCellEditor', cellEditorParams={'values': logins_p_tabela})
            gb_fixos.configure_column("SCHEDULE_TYPE", cellEditor='agSelectCellEditor', cellEditorParams={'values': ["visita_tox", "entrega"]})
                    
            gb_fixos.configure_selection('multiple', use_checkbox=True)
            grid_options_fixos = gb_fixos.build()

            resposta_grid_fixos = AgGrid(
                df_regras,
                gridOptions=grid_options_fixos,
                update_mode=GridUpdateMode.MODEL_CHANGED | GridUpdateMode.SELECTION_CHANGED,
                data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
                theme='alpine',
                height=450,
                allow_unsafe_jscode=True,
                key="aggrid_regras_fixas"
            )

            df_regras_edit = pd.DataFrame(resposta_grid_fixos['data'])
            linhas_selecionadas_fixos = resposta_grid_fixos['selected_rows']

            c_btn_salvar, c_btn_excluir = st.columns([3, 1])

            if c_btn_salvar.button("💾 Salvar Alterações na Base de Regras", type="primary", use_container_width=True):
                with st.spinner("Atualizando banco de dados..."):
                    try:
                        for col in cols_fixos:
                            if col not in df_regras_edit.columns:
                                df_regras_edit[col] = ""

                        df_regras_edit = df_regras_edit[cols_fixos].copy()
                        df_regras_edit['SCHEDULE_TYPE'] = df_regras_edit['SCHEDULE_TYPE'].astype(str).str.strip().str.lower()
                        df_regras_edit.loc[~df_regras_edit['SCHEDULE_TYPE'].isin(['visita_tox', 'entrega']), 'SCHEDULE_TYPE'] = 'visita_tox'

                        aba_fixos.clear()
                        if df_regras_edit.empty:
                            aba_fixos.update("A1", [cols_fixos])
                        else:
                            aba_fixos.update("A1", [cols_fixos] + df_regras_edit.fillna("").astype(str).values.tolist())
                        carregar_agendamentos_fixos.clear()
                        st.success("✅ Regras atualizadas com sucesso!")
                        time.sleep(1.5)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao salvar regras: {e}")

            if isinstance(linhas_selecionadas_fixos, list) and len(linhas_selecionadas_fixos) > 0:
                if c_btn_excluir.button("🗑️ Excluir Regras", type="secondary", use_container_width=True):
                    try:
                        df_selecionados = pd.DataFrame(linhas_selecionadas_fixos)
                        ids_para_remover = df_selecionados['ID_REGRA'].tolist()
                        df_regras_edit = df_regras_edit[~df_regras_edit['ID_REGRA'].isin(ids_para_remover)]

                        for col in cols_fixos:
                            if col not in df_regras_edit.columns:
                                df_regras_edit[col] = ""

                        df_regras_edit = df_regras_edit[cols_fixos].copy()
                        df_regras_edit['SCHEDULE_TYPE'] = df_regras_edit['SCHEDULE_TYPE'].astype(str).str.strip().str.lower()
                        df_regras_edit.loc[~df_regras_edit['SCHEDULE_TYPE'].isin(['visita_tox', 'entrega']), 'SCHEDULE_TYPE'] = 'visita_tox'
                                
                        aba_fixos.clear()
                        if df_regras_edit.empty:
                            aba_fixos.update("A1", [cols_fixos])
                        else:
                            aba_fixos.update("A1", [cols_fixos] + df_regras_edit.fillna("").astype(str).values.tolist())
                        carregar_agendamentos_fixos.clear()
                        st.success(f"✅ {len(ids_para_remover)} regras excluídas!")
                        time.sleep(1.5)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao excluir: {e}")
        else:
            st.info("Nenhuma regra de agendamento cadastrada ainda.")

    # -------------------------------------------------------------------------
    # ABA 3: CARRINHO & ARQUIVOS (Layout Premium + Toggle Blindado)
    # -------------------------------------------------------------------------
    with tab_carrinho:
        def obter_proximo_id_umove_seguro():
            return obter_proximo_id_umove_seguro_global()

        # --- BLOCAGEM DE PROCESSAMENTO: AGENDAMENTOS FIXOS ---
        df_fixos_hoje = pd.DataFrame()
        prox_id_sb = UMOVE_PEDIDO_INICIAL
        try:
            aba_fixos = planilha_db.worksheet("Agendamentos_Fixos")
            dados_fixos = aba_fixos.get_all_values()
            if len(dados_fixos) > 1:
                df_regras_temp = pd.DataFrame(dados_fixos[1:], columns=dados_fixos[0])
                if 'SCHEDULE_TYPE' not in df_regras_temp.columns:
                    df_regras_temp['SCHEDULE_TYPE'] = 'visita_tox'
                df_regras_temp['SCHEDULE_TYPE'] = df_regras_temp['SCHEDULE_TYPE'].astype(str).str.strip().str.lower()
                df_regras_temp.loc[~df_regras_temp['SCHEDULE_TYPE'].isin(['visita_tox', 'entrega']), 'SCHEDULE_TYPE'] = 'visita_tox'
                mapa_dias = {0: 'SEG', 1: 'TER', 2: 'QUA', 3: 'QUI', 4: 'SEX', 5: 'SAB', 6: 'DOM'}
                dia_atual = mapa_dias[hoje_br.weekday()]

                if dia_atual != 'DOM':
                    df_alvo = df_regras_temp[(df_regras_temp[dia_atual] == "SIM") & (df_regras_temp['STATUS'] == "ATIVO")].copy()
                    if not df_alvo.empty:
                        prox_id_sb = obter_proximo_id_umove_seguro()

                        novos_pedidos = []
                        for _, regra in df_alvo.iterrows():
                            novo_pedido = {
                                'DATA': hoje_br.strftime("%d/%m/%Y"),
                                'TOMADOR': regra['TOMADOR'],
                                'PEDIDO': str(prox_id_sb),
                                'LABORATORIO': regra['LABORATORIO'],
                                'CNPJ': "",
                                'ENDERECO': regra['ENDERECO'],
                                'NUMERO': regra['NUMERO'],
                                'BAIRRO': regra['BAIRRO'],
                                'CIDADE': regra['CIDADE'],
                                'UF': regra['UF'],
                                'CEP': regra['CEP'],
                                'OBSERVACOES': str(regra['OBSERVACOES']) + " [FIXO]",
                                'SCHEDULE_TYPE': str(regra.get('SCHEDULE_TYPE', 'visita_tox')).strip().lower(),
                                'AGENTE_RAW': regra['MOTORISTA']}
                            novos_pedidos.append(novo_pedido)
                            prox_id_sb += 1

                        df_fixos_hoje = pd.DataFrame(novos_pedidos)
        except Exception:
            pass

        # Lógica Inteligente para a Chave Seletiva (Toggle)
        tem_fixos_na_memoria = False
        if not st.session_state.df_sandbox_mem.empty and 'OBSERVACOES' in st.session_state.df_sandbox_mem.columns:
            tem_fixos_na_memoria = st.session_state.df_sandbox_mem['OBSERVACOES'].astype(str).str.contains(r'\[FIXO\]', regex=True, na=False).any()

        # 🔥 CORREÇÃO: O Toggle DEVE aparecer se a API cair, MAS os pedidos fixos já estiverem na memória do carrinho.
        mostrar_painel_fixos = (not df_fixos_hoje.empty) or tem_fixos_na_memoria

        if mostrar_painel_fixos:
            qtd_msg = f"{len(df_fixos_hoje)} agendamentos fixos" if not df_fixos_hoje.empty else "agendamentos fixos (preservados na memória)"
            dia_msg = f" para esta <b>{dia_atual}-feira</b>" if 'dia_atual' in locals() else ""
                    
            st.markdown(f"""
            <div style='background-color:#FFFBEB; border: 1px solid #FCD34D; padding:15px; border-radius:10px; margin-bottom:15px; display:flex; justify-content:space-between; align-items:center;'>
                <div style='margin-right:10px;'>
                    <h5 style='color:#92400E; margin:0;'>📅 Rotinas Fixas Disponíveis</h5>
                    <p style='color:#B45309; font-size:13px; margin:3px 0 0 0;'>Identificamos <b>{qtd_msg}</b> programados automáticos{dia_msg}.</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
                    
            # A chave seletiva que reflete o estado real da memória
            incluir_fixos = st.toggle("⚡ Injetar/Manter Pedidos Fixos no Carrinho", value=tem_fixos_na_memoria, key="toggle_seguro_fixos")
                    
            # Gerenciador de mudança de estado (Só roda se houver clique na chave)
            if incluir_fixos != tem_fixos_na_memoria:
                if incluir_fixos:
                    if not df_fixos_hoje.empty:
                        with st.spinner("Consolidando rotinas permanentes..."):
                            if st.session_state.df_sandbox_mem.empty:
                                st.session_state.df_sandbox_mem = df_fixos_hoje
                            else:
                                st.session_state.df_sandbox_mem = pd.concat([st.session_state.df_sandbox_mem, df_fixos_hoje], ignore_index=True)
                                    
                            try:
                                planilha_sandbox.worksheet("Contador").update("A1", [[str(prox_id_sb)]])
                            except: pass
                                    
                            if st.session_state.umove_lote_atual_id is None:
                                st.session_state.umove_lote_atual_id = f"LOTE-{datetime.now(FUSO_BR).strftime('%d%m%H%M')}"
                            gerenciar_estado_lote("SALVAR_RASCUNHO", st.session_state.umove_lote_atual_id, st.session_state.df_sandbox_mem)
                            st.rerun()
                    else:
                        st.error("⚠️ Banco de dados instável no momento. Tente acionar novamente.")
                        time.sleep(1.5)
                        st.rerun()
                else:
                    with st.spinner("Desfazendo injeção de pedidos fixos..."):
                        mask_fixos = st.session_state.df_sandbox_mem['OBSERVACOES'].astype(str).str.contains(r'\[FIXO\]', regex=True, na=False)
                        st.session_state.df_sandbox_mem = st.session_state.df_sandbox_mem[~mask_fixos]
                                
                        if st.session_state.umove_lote_atual_id:
                            gerenciar_estado_lote("SALVAR_RASCUNHO", st.session_state.umove_lote_atual_id, st.session_state.df_sandbox_mem)
                        st.rerun()
        else:
            st.markdown("<p style='font-size:13px; color:#64748B;'>ℹ️ Sem registros fixos programados para o dia atual no sistema.</p>", unsafe_allow_html=True)

        # --- EXIBIÇÃO DO CARRINHO CONSOLIDADO ---
        df_sb = st.session_state.df_sandbox_mem.copy()

        if not df_sb.empty:
            resumo_tom = df_sb.groupby('TOMADOR').size().reset_index(name='QTD').sort_values(by='QTD', ascending=False)
            total_volumes = len(df_sb)
            clientes_unicos = int(resumo_tom['TOMADOR'].nunique())
            top_cliente_qtd = int(resumo_tom.iloc[0]['QTD']) if not resumo_tom.empty else 0
            top_cliente_pct = round((top_cliente_qtd / total_volumes) * 100, 1) if total_volumes else 0
            resumo_tom_str = " | ".join([
                f"{str(row.get('TOMADOR', '')).strip() or 'SEM TOMADOR'}: {int(row.get('QTD', 0))}"
                for _, row in resumo_tom.iterrows()
            ])

            st.markdown("### 🛒 Carrinho de Expedição Oficial")
            st.markdown("<p style='font-size:13px; color:#64748B; margin-top:-8px;'>Mesa cumulativa com edição direta, mantendo a injeção na própria base oficial.</p>", unsafe_allow_html=True)

            col_kpi_of_1, col_kpi_of_2, col_kpi_of_3 = st.columns([1.15, 2.35, 1])
            with col_kpi_of_1:
                st.markdown(f"""
                    <div class='of-card' style='text-align:center; background:linear-gradient(135deg, #0F172A 0%, #1E293B 100%); border:1px solid #334155;'>
                        <div style='font-size:11px; font-weight:800; color:#93C5FD; text-transform:uppercase; letter-spacing:0.7px;'>Volumes no Carrinho</div>
                        <div style='font-size:44px; font-weight:900; color:#FFFFFF; line-height:1.05; margin-top:2px;'>{total_volumes}</div>
                        <div style='font-size:12px; color:#CBD5E1; margin-top:4px;'>Clientes ativos: <b>{clientes_unicos}</b></div>
                        <div style='margin-top:10px; padding-top:8px; border-top:1px solid rgba(148,163,184,0.35); font-size:11px; color:#E2E8F0;'>
                            Maior concentração: <b>{top_cliente_pct}%</b>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
            with col_kpi_of_2:
                st.markdown(f"""
                    <div class='of-card' style='padding:14px;'>
                        <div class='of-card-title'>Detalhamento por Conta de Cliente</div>
                        <div style='font-size:14px; font-weight:600; color:#334155; margin:10px 0 2px 0; line-height:1.7;'>
                            {resumo_tom_str}
                        </div>
                    </div>
                """, unsafe_allow_html=True)
            with col_kpi_of_3:
                if st.button("🗑️ Esvaziar Todo Carrinho", type="secondary", use_container_width=True, help="Zera completamente a memória temporária"):
                    st.session_state.df_sandbox_mem = pd.DataFrame()
                    st.session_state.umove_lote_atual_id = None
                    try: planilha_sandbox.sheet1.clear()
                    except: pass
                    st.session_state.ui_toast = {'msg': "Mesa limpa com sucesso!", 'icon': "🧹"}
                    st.rerun()

            st.markdown("#### 🕵️‍♂️ Mesa de Conferência e Modificações")

            # Renderização Customizada do AgGrid Master
            gb_sb = GridOptionsBuilder.from_dataframe(df_sb)
            gb_sb.configure_default_column(editable=True, resizable=True, sortable=True, filter=True)
            # A linha gb_sb.configure_selection() foi removida para limpar as caixas de seleção
            gb_sb.configure_column("AGENTE_RAW", pinned='right', cellStyle={'backgroundColor': '#FFFBEB', 'fontWeight': 'bold', 'color': '#92400E'})
            grid_options_sb = gb_sb.build()

            resposta_grid_sb = AgGrid(
                df_sb,
                gridOptions=grid_options_sb,
                update_mode=GridUpdateMode.MODEL_CHANGED, # SELECTION_CHANGED removido
                data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
                theme='alpine',
                height=400,
                allow_unsafe_jscode=True,
                key="aggrid_master_umove"
            )

            df_editado_sb = pd.DataFrame(resposta_grid_sb['data'])
                    
            # Painel de Controle Inferior da Grid (Agora limpo, apenas com o botão principal)
            if st.button("💾 Persistir Alterações da Tabela na Nuvem", type="primary", use_container_width=True):
                st.session_state.df_sandbox_mem = df_editado_sb
                if st.session_state.umove_lote_atual_id is None:
                    st.session_state.umove_lote_atual_id = f"UMOVE-{datetime.now(FUSO_BR).strftime('%Y%m%d%H%M%S')}"
                gerenciar_estado_lote("SALVAR_RASCUNHO", st.session_state.umove_lote_atual_id, st.session_state.df_sandbox_mem)
                st.toast("✅ Base de rascunhos atualizada com sucesso na nuvem!", icon="💾")
                time.sleep(0.5)
                st.rerun()

            # Sincronização direta com a Aba de Disparos
            if not df_editado_sb.empty:
                st.session_state.sandbox_grid_master_umove = df_editado_sb

            # Bloco de Exportação e Central de Envio Oficial
            st.markdown("---")
            st.markdown("### 🚀 Central de Envio Oficial")
            st.info("A base oficial mantém a lógica de injeção na própria grid, mas a central abaixo organiza envio, exportação e conferência em um único painel.")
                    
            col_env1, col_env2, col_env3 = st.columns([1, 1, 1])

            with col_env1:
                st.markdown("<div class='of-card'><div class='of-card-title'>Etapa 1</div><div class='of-card-subtitle'><b>Injetar no Banco</b><br>Persistência oficial dos pedidos editados na própria planilha.</div></div>", unsafe_allow_html=True)
            with col_env2:
                st.markdown("<div class='of-card'><div class='of-card-title'>Etapa 2</div><div class='of-card-subtitle'><b>Disparar WhatsApp</b><br>Envio das mensagens e anexos por motorista.</div></div>", unsafe_allow_html=True)
            with col_env3:
                st.markdown("<div class='of-card'><div class='of-card-title'>Etapa 3</div><div class='of-card-subtitle'><b>Exportar Excel / Legados</b><br>Baixe o carrinho em XLS ou gere os arquivos `.LOC` e `.AGD`.</div></div>", unsafe_allow_html=True)

            col_cmd1, col_cmd2, col_cmd3 = st.columns([1, 1, 1])

            def criar_arquivos_legados(df):
                loc_lines = ["alternativeIdentifier;description;corporateName;state;city;cityNeighborhood;street;streetNumber;zipCode;CF_loc_responsavel_cliente;CF_loc_whats;CF_CNPJ;active"]
                agd_lines = ["C", "command;serviceLocal;scheduleType;activitiesOrigin;active;date;hour;situation;alternativeIdentifier;agent;CF_tar_valor"]

                def _formatar_data_agendada(valor_data):
                    data_padrao = hoje_br.strftime('%d/%m/%Y')
                    if valor_data is None:
                        return data_padrao

                    # Aceita datetime/date/Timestamp já prontos.
                    if hasattr(valor_data, "strftime"):
                        try:
                            return valor_data.strftime('%d/%m/%Y')
                        except Exception:
                            pass

                    texto = str(valor_data).strip()
                    if not texto or texto.upper() in ["NAN", "NONE", "NAT"]:
                        return data_padrao

                    for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y'):
                        try:
                            return datetime.strptime(texto, fmt).strftime('%d/%m/%Y')
                        except Exception:
                            continue

                    try:
                        data_parseada = pd.to_datetime(texto, dayfirst=True, errors='coerce')
                        if pd.notna(data_parseada):
                            return data_parseada.strftime('%d/%m/%Y')
                    except Exception:
                        pass

                    return data_padrao

                for idx, row in df.iterrows():
                    id_agd = str(row['PEDIDO'])
                    tomador = str(row.get('TOMADOR', '')).upper()
                    lab = str(row.get('LABORATORIO', '')).upper()
                    cep = str(row.get('CEP', ''))
                    bairro_legado = normalizar_bairro_whatsapp(row.get('BAIRRO', ''), tomador)

                    id_loc = f"{tomador}-{lab}-{cep}"
                    corp_name = f"{tomador}-{lab}"
                    cnpj = str(row.get('CNPJ', ''))
                    if cnpj: cnpj = f"'{cnpj}"

                    numero_limpo = re.sub(r'\D', '', str(row.get('NUMERO', '')))
                    linha_loc = f"{id_loc};{id_loc};{corp_name};{row.get('UF', '')};{row.get('CIDADE', '')};{bairro_legado};{row.get('ENDERECO', '')};{numero_limpo};{cep};{tomador};;{cnpj};1"
                    loc_lines.append(linha_loc)

                    agente_raw = str(row.get('AGENTE_RAW', ''))
                    agente_agd = agente_raw.split('|')[0].strip()

                    eh_fixo = bool(re.search(r'\[FIXO\]', str(row.get('OBSERVACOES', '')), flags=re.IGNORECASE))
                    if eh_fixo:
                        schedule_type = str(row.get('SCHEDULE_TYPE', 'visita_tox')).strip().lower()
                        if schedule_type not in ['visita_tox', 'entrega']:
                            schedule_type = 'visita_tox'
                    else:
                        schedule_type = "visita_tox"
                    data_agendada = _formatar_data_agendada(row.get('DATA', ''))
                    linha_agd = f";{id_loc};{schedule_type};7;1;{data_agendada};00:10;;{id_agd};{agente_agd};"
                    agd_lines.append(linha_agd)

                loc_lines_unique = [loc_lines[0]] + list(dict.fromkeys(loc_lines[1:]))
                return "\n".join(loc_lines_unique).encode('utf-8'), "\n".join(agd_lines).encode('utf-8')

            bytes_loc, bytes_agd = criar_arquivos_legados(df_editado_sb)

            with col_cmd1:
                st.download_button("💾 Baixar Arquivo de Locais (.LOC)", data=bytes_loc, file_name=f"LOC_GERAL_{hoje_br.strftime('%d%m%y')}.csv", mime="text/csv", use_container_width=True, on_click=lambda: st.toast("Baixando arquivo LOC...", icon="📥"))
            with col_cmd2:
                st.download_button("💾 Baixar Arquivo de Agendas (.AGD)", data=bytes_agd, file_name=f"AGD_GERAL_{hoje_br.strftime('%d%m%y')}.csv", mime="text/csv", use_container_width=True, on_click=lambda: st.toast("Baixando arquivo AGD...", icon="📥"))
            with col_cmd3:
                st.download_button(
                    "📥 Baixar o Carrinho como Excel",
                    data=gerar_excel_memoria(df_editado_sb),
                    file_name=f"MESA_CONFERENCIA_{hoje_br.strftime('%d%m%y')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    on_click=lambda: st.toast("Baixando XLS da Mesa de Conferência...", icon="📥")
                )
        else:
            st.markdown("""
            <div style="text-align: center; padding: 40px; background-color: #F8FAFC; border: 2px dashed #CBD5E1; border-radius: 12px; margin-top: 20px;">
                <p style="font-size: 48px; margin: 0;">🛒</p>
                <h5 style="color: #475569; margin: 10px 0 5px 0;">O Carrinho de Expedição está Vazio</h5>
                <p style="color: #94A3B8; font-size: 13px; margin: 0;">Processe uma matriz na <b>Aba 1</b> ou injete agendamentos automáticos fixos para carregar a mesa de trabalho.</p>
            </div>
            """, unsafe_allow_html=True)

    # =============================================================================
    # 🚀 ABA 4: CENTRAL DE ENVIOS (Dashboard Premium e Disparo em Lote Blindado)
    # =============================================================================
    with tab_envios:
        def render_big_metrics(tot, pend, suc, fal):
            return f"""
            <div style="display:flex; gap:12px; text-align:center; margin-bottom: 20px;">
                <div style="flex:1; background:#F8FAFC; border: 2px solid #E2E8F0; padding:15px; border-radius:12px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                    <div style="font-size:13px; font-weight:800; color:#64748B; text-transform:uppercase;">Alvos Totais</div>
                    <div style="font-size:38px; font-weight:900; color:#0F172A; line-height:1.2;">{tot}</div>
                </div>
                <div style="flex:1; background:#FFFBEB; border: 2px solid #FDE68A; padding:15px; border-radius:12px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                    <div style="font-size:13px; font-weight:800; color:#D97706; text-transform:uppercase;">Pendentes</div>
                    <div style="font-size:38px; font-weight:900; color:#B45309; line-height:1.2;">{pend}</div>
                </div>
                <div style="flex:1; background:#F0FDF4; border: 2px solid #A7F3D0; padding:15px; border-radius:12px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                    <div style="font-size:13px; font-weight:800; color:#059669; text-transform:uppercase;">Sucessos (✅)</div>
                    <div style="font-size:38px; font-weight:900; color:#047857; line-height:1.2;">{suc}</div>
                </div>
                <div style="flex:1; background:#FEF2F2; border: 2px solid #FECACA; padding:15px; border-radius:12px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                    <div style="font-size:13px; font-weight:800; color:#DC2626; text-transform:uppercase;">Falhas (❌)</div>
                    <div style="font-size:38px; font-weight:900; color:#B91C1C; line-height:1.2;">{fal}</div>
                </div>
            </div>
            """

        def render_current_driver(nom, idx, total):
            return f"""
            <div style="background: linear-gradient(135deg, #0F172A 0%, #334155 100%); color: white; padding: 25px 20px; border-radius: 12px; margin-bottom: 25px; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1); border-left: 5px solid #3B82F6;">
                <div style="font-size: 13px; font-weight: 800; color: #94A3B8; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 5px;">🚀 Transmitindo Lote ({idx}/{total})</div>
                <div style="font-size: 36px; font-weight: 900; letter-spacing: -0.5px; color: #FFFFFF;">👤 {nom}</div>
            </div>
            """

        if 'umove_step' not in st.session_state: st.session_state.umove_step = 'IDLE'
        if 'umove_df_dispatch' not in st.session_state: st.session_state.umove_df_dispatch = pd.DataFrame()
        if 'umove_resultados_disparo' not in st.session_state: st.session_state.umove_resultados_disparo = {}
        if 'umove_xls_bytes' not in st.session_state: st.session_state.umove_xls_bytes = None
        if 'umove_final_metrics' not in st.session_state: st.session_state.umove_final_metrics = {'total': 0, 'sucesso': 0, 'falhas': 0}
        if 'umove_sync_status' not in st.session_state:
            st.session_state.umove_sync_status = {'ok': True, 'pendencias': []}

        # 🛡️ CORREÇÃO 1: Dicionários de mapeamento com injeção automática do DDI (55)
        dict_tel = {}
        dict_nom = {}
        if not DF_AGENTES.empty:
            for _, r in DF_AGENTES.iterrows():
                login_ag = str(r.get('LOGIN DO AGENTE', '')).strip().lower()
                        
                # Se o login contém pipe (ex: igo.log|anderson), não corta ele aqui, grava inteiro para consulta da ZAPI.
                if login_ag:
                    num_limpo = re.sub(r'\D', '', str(r.get('TELEFONE', '')))
                    # Se não vier com 55 e tiver os 10 ou 11 dígitos, injeta o 55 da Z-API.
                    if num_limpo and not num_limpo.startswith('55') and len(num_limpo) <= 11:
                        num_limpo = '55' + num_limpo
                            
                    dict_tel[login_ag] = num_limpo
                    dict_nom[login_ag] = str(r.get('NOME DO AGENTE', '')).strip()

        if st.session_state.umove_step == 'IDLE':
            df_rascunhos = gerenciar_estado_lote("LISTAR_RASCUNHOS")
            if df_rascunhos is not None and not df_rascunhos.empty:
                st.warning("⚠️ **ATENÇÃO:** Lotes inativos ou pendentes encontrados na nuvem.")
                with st.expander("🔄 Resgatar Lotes Inacabados", expanded=False):
                    for i, row_rasc in enumerate(df_rascunhos.to_dict('records')):
                        c_r1, c_r2, c_r3 = st.columns([2.5, 1, 1], vertical_alignment="center")
                        c_r1.markdown(f"**Lote:** `{row_rasc.get('ID_EVENTO','')}` | **Criado:** {row_rasc.get('DATA_DISPARO','')} | **Volumes:** {row_rasc.get('TOTAL_PEDIDOS','')}")
                        if c_r2.button("Resgatar", key=f"resg_t4_{i}_{row_rasc.get('ID_EVENTO','')}", use_container_width=True, type="primary"):
                            try:
                                df_resgatado = pd.read_json(io.StringIO(str(row_rasc.get('DADOS_JSON','[]'))), orient='records')
                                st.session_state.df_sandbox_mem = df_resgatado.astype(str)
                                st.session_state.umove_lote_atual_id = row_rasc.get('ID_EVENTO')
                                st.session_state.umove_step = 'IDLE'
                                st.toast("✅ Lote resgatado para o Carrinho!")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e: st.error(f"Falha ao resgatar: {e}")
                        if c_r3.button("🗑️ Excluir", key=f"excl_t4_{i}_{row_rasc.get('ID_EVENTO','')}", use_container_width=True):
                            try:
                                gerenciar_estado_lote("EXCLUIR_RASCUNHO", lote_id=row_rasc.get('ID_EVENTO'))
                                st.toast("🗑️ Lote apagado!")
                                time.sleep(1)
                                st.rerun()
                            except: pass

        # Fonte da verdade sempre será a memória em sessão
        df_fonte_envio = st.session_state.df_sandbox_mem.copy()

        def salvar_backup_completo_umove(df_bkp, id_ev, planilha):
            if planilha is None or df_bkp.empty:
                return False
            try:
                try: aba_bkp = planilha.worksheet("Backup_Umove_Rotas")
                except:
                    aba_bkp = planilha.add_worksheet("Backup_Umove_Rotas", 100, 20)
                    cabecalho = ["ID_EVENTO", "DATA_DISPARO"] + df_bkp.columns.tolist()
                    aba_bkp.update("A1", [cabecalho])
                        
                df_to_save = df_bkp.copy()
                df_to_save.insert(0, "DATA_DISPARO", datetime.now(FUSO_BR).strftime('%d/%m/%Y %H:%M:%S'))
                df_to_save.insert(0, "ID_EVENTO", id_ev)
                aba_bkp.append_rows(df_to_save.fillna("").astype(str).values.tolist(), value_input_option='USER_ENTERED')
                return True
            except:
                return False

        if df_fonte_envio.empty and st.session_state.umove_step not in ['PROCESSING', 'COMPLETED']:
            st.markdown("""
            <div style="text-align: center; padding: 40px; background-color: #F8FAFC; border: 2px dashed #CBD5E1; border-radius: 12px; margin-top: 20px;">
                <p style="font-size: 48px; margin: 0;">📡</p>
                <h5 style="color: #475569; margin: 10px 0 5px 0;">Mesa de Transmissão Inativa</h5>
                <p style="color: #94A3B8; font-size: 13px; margin: 0;">O carrinho de expedição está vazio. Adicione pedidos na aba anterior para habilitar os controles de disparo.</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            if st.session_state.umove_step in ['IDLE', 'CONFIRMING']:
                st.markdown("### 🎛️ Terminal de Comando e Lançamento")
                st.markdown("<p style='font-size:13px; color:#64748B; margin-top:-10px;'>Configure os parâmetros operacionais e inicie a transmissão da carga para os agentes.</p>", unsafe_allow_html=True)
                        
                # DIVISÃO MESTRA: Painel de Controle à Esquerda, Detalhamento à Direita
                col_main, col_side = st.columns([2.3, 1], gap="large")
                        
                with col_main:
                    st.markdown("#### 1️⃣ Configuração do Alvo")
                    with st.container(border=True):
                        c_opt, c_cal = st.columns([2.2, 1], vertical_alignment="center")
                        with c_opt:
                            dispatch_choice = st.radio(
                                "Selecione a abrangência do disparo:",
                                ["Todos os pedidos do carrinho", "Filtrar por data específica", "Reenviar Falhas (Recuperação)"],
                                horizontal=True,
                                key="ui_dispatch_choice")

                        dispatch_period = None
                        with c_cal:
                            if dispatch_choice == "Filtrar por data específica":
                                dispatch_period = st.date_input("📅 Período da Rota:", value=(hoje_br, hoje_br), format="DD/MM/YYYY")
                            else:
                                st.write("")

                # Filtragem aplicada globalmente na memória temporária para alimentar ambos os lados
                df_preview = df_fonte_envio.copy()
                        
                if dispatch_choice == "Filtrar por data específica":
                    df_preview['__DATA_FILTRADA'] = pd.to_datetime(df_preview['DATA'], dayfirst=True, errors='coerce').dt.date
                    if isinstance(dispatch_period, (tuple, list)) and len(dispatch_period) == 2:
                        start_date, end_date = dispatch_period
                    else:
                        start_date = end_date = dispatch_period
                            
                    if start_date and end_date:
                        if start_date > end_date: start_date, end_date = end_date, start_date
                        df_preview = df_preview[(df_preview['__DATA_FILTRADA'] >= start_date) & (df_preview['__DATA_FILTRADA'] <= end_date)]
                        df_preview = df_preview.drop(columns=['__DATA_FILTRADA'])
                                
                elif dispatch_choice == "Reenviar Falhas (Recuperação)":
                    todos_agentes = df_preview['AGENTE_RAW'].dropna().unique()
                    falhas = []
                    for ag in todos_agentes:
                        ag_key = str(ag).strip().lower().split('|')[0].split('/')[0].strip()
                        nom = dict_nom.get(ag_key, str(ag).upper())
                        if nom in st.session_state.umove_resultados_disparo and st.session_state.umove_resultados_disparo[nom].get('sucesso', 1) == 0:
                            falhas.append(ag)
                    df_preview = df_preview[df_preview['AGENTE_RAW'].isin(falhas)]

                qtd_pedidos = len(df_preview)
                qtd_motoristas = len(df_preview['AGENTE_RAW'].dropna().unique())

                # CONTINUAÇÃO DA COLUNA ESQUERDA (Controles e Ações)
                with col_main:
                    if st.session_state.umove_step == 'IDLE':
                        st.markdown("#### 2️⃣ Pré-Visualização da Carga")
                        if qtd_pedidos == 0:
                            st.markdown("""
                            <div style="background-color: #FEF2F2; border: 1px solid #FCA5A5; border-radius: 8px; padding: 15px; margin-bottom: 20px;">
                                <span style="color: #991B1B; font-weight: bold;">🚨 Bloqueio Operacional:</span> <span style="color: #7F1D1D;">Nenhum pedido atende aos filtros atuais. Modifique a configuração acima.</span>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            datas_temp = pd.to_datetime(df_preview['DATA'], format='%d/%m/%Y', errors='coerce').dropna().dt.date
                            if not datas_temp.empty:
                                d_min = datas_temp.min().strftime('%d/%m/%Y')
                                d_max = datas_temp.max().strftime('%d/%m/%Y')
                                periodo_str = f"{d_min}" if d_min == d_max else f"de {d_min} até {d_max}"
                            else:
                                periodo_str = "Desconhecido"
                                    
                            st.markdown(f"""
                            <div style="display:flex; gap:15px; margin-bottom: 25px;">
                                <div style="flex:1; background:#F8FAFC; border-left: 4px solid #3B82F6; padding:15px; border-radius:8px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                                    <div style="font-size:11px; font-weight:800; color:#64748B; text-transform:uppercase;">Volumes Mapeados</div>
                                    <div style="font-size:28px; font-weight:900; color:#0F172A; line-height:1.2;">{qtd_pedidos}</div>
                                </div>
                                <div style="flex:1; background:#F8FAFC; border-left: 4px solid #10B981; padding:15px; border-radius:8px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                                    <div style="font-size:11px; font-weight:800; color:#64748B; text-transform:uppercase;">Motoristas Acionados</div>
                                    <div style="font-size:28px; font-weight:900; color:#0F172A; line-height:1.2;">{qtd_motoristas}</div>
                                </div>
                                <div style="flex:2; background:#F8FAFC; border-left: 4px solid #8B5CF6; padding:15px; border-radius:8px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                                    <div style="font-size:11px; font-weight:800; color:#64748B; text-transform:uppercase;">Período da Rota</div>
                                    <div style="font-size:18px; font-weight:700; color:#0F172A; line-height:1.4; margin-top:2px;">📅 {periodo_str}</div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                                    
                            st.markdown("#### 3️⃣ Autorização de Disparo")
                            st.info("ℹ️ O sistema conectará à Z-API e transmitirá sequencialmente as mensagens, PDFs e planilhas para todos os motoristas alocados.")
                                    
                            if st.button("🚀 INICIAR TRANSMISSÃO EM LOTE AGORA", type="primary", use_container_width=True):
                                st.session_state.umove_df_dispatch = df_preview
                                st.session_state.umove_step = 'CONFIRMING'
                                st.rerun()

                    elif st.session_state.umove_step == 'CONFIRMING':
                        st.markdown("---")
                        st.markdown(f"""
                        <div style="background-color: #FEF2F2; border: 2px solid #FCA5A5; border-radius: 12px; padding: 25px; text-align: center; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(220, 38, 38, 0.1);">
                            <h3 style="color: #991B1B; margin-top: 0;">⚠️ Confirmação de Disparo Crítico</h3>
                            <p style="color: #7F1D1D; font-size: 16px; margin-bottom: 5px;">Você está prestes a disparar mensagens oficiais via WhatsApp para <b>{qtd_motoristas} motoristas</b>.</p>
                            <p style="color: #7F1D1D; font-size: 14px; font-weight: bold; margin-bottom: 0;">Esta ação entrará na fila de processamento e não deverá ser interrompida.</p>
                        </div>
                        """, unsafe_allow_html=True)
                                
                        c_sim, c_nao = st.columns(2)
                        if c_sim.button("✔️ CONFIRMAR E DISPARAR", type="primary", use_container_width=True):
                            st.session_state.umove_step = 'PROCESSING'
                            st.rerun()
                        if c_nao.button("❌ Cancelar Operação", use_container_width=True):
                            st.session_state.umove_step = 'IDLE'
                            st.rerun()

                # PAINEL DA COLUNA DIREITA (Composição da Carga Dinâmica - APENAS TOMADORES)
                with col_side:
                    st.markdown("#### 📦 Composição da Carga")
                    with st.container(border=True):
                        if qtd_pedidos == 0:
                            st.markdown("<span style='color:#94A3B8; font-size:13px;'>Nenhum volume alocado.</span>", unsafe_allow_html=True)
                        else:
                            # Tabela de Clientes (Tomadores) - Tudo em 1 linha de HTML para o Streamlit não interpretar como Bloco de Código Markdown
                            resumo_tom = df_preview.groupby('TOMADOR').size().reset_index(name='QTD').sort_values(by='QTD', ascending=False)
                            html_breakdown = "<div style='display: flex; flex-direction: column; gap: 8px;'>"
                            for _, row in resumo_tom.iterrows():
                                html_breakdown += f"<div style='background: #F1F5F9; border: 1px solid #E2E8F0; border-radius: 6px; padding: 8px 12px; display: flex; justify-content: space-between; align-items: center;'><span style='font-weight: 600; color: #334155; font-size: 13px;'>{row['TOMADOR']}</span><span style='background: #DBEAFE; color: #1D4ED8; padding: 2px 8px; border-radius: 10px; font-weight: 700; font-size: 13px;'>{row['QTD']}</span></div>"
                            html_breakdown += "</div>"
                            st.markdown(html_breakdown, unsafe_allow_html=True)

            elif st.session_state.umove_step == 'PROCESSING':
                st.markdown("## 📡 Monitor de Transmissão")
                st.error("⚠️ **PROCESSO EM ANDAMENTO - NÃO ATUALIZE OU MUDE DE ABA!**")
                        
                df_dispatch = st.session_state.umove_df_dispatch
                agentes_selecionados = df_dispatch['AGENTE_RAW'].dropna().unique()
                total_agentes = len(agentes_selecionados)

                st.session_state.umove_resultados_disparo = {}
                sucessos_sb = 0
                falhas_calc = 0
                logs_google_sheets_zap = []
                id_evento = f"UMOVE-{datetime.now(FUSO_BR).strftime('%Y%m%d%H%M%S')}"
                        
                metrics_placeholder = st.empty()
                driver_placeholder = st.empty()
                progress_bar = st.progress(0)
                        
                metrics_placeholder.markdown(render_big_metrics(total_agentes, total_agentes, 0, 0), unsafe_allow_html=True)

                st.markdown("#### 🖥️ Terminal de Registros")
                container_log = st.container(border=True, height=250)
                log_table_placeholder = container_log.empty()
                logs_df_data = []

                # LOOP DO DISPARO EM LOTE BLINDADO
                for idx_ag, ag in enumerate(agentes_selecionados):
                    if not str(ag).strip(): continue
                            
                    try:
                        import os
                        import requests
                        df_ag_sb = df_dispatch[df_dispatch['AGENTE_RAW'] == ag]
                                
                        # Mantemos a chave completa para achar o WhatsApp do Anderson
                        ag_key = str(ag).strip().lower() 
                        tel = dict_tel.get(ag_key, "")
                        nom = dict_nom.get(ag_key, str(ag).upper())
                                
                        ag_login = ag_key
                        modo_disparo = obter_modo_disparo_whatsapp(ag_login)
                        is_autorizado_pdf = modo_disparo in ['PDF', 'PDF_XLS']
                        is_autorizado_xls = modo_disparo in ['XLS', 'PDF_XLS']

                        st.session_state.umove_resultados_disparo[nom] = {'total': len(df_ag_sb), 'sucesso': 0, 'pedidos': df_ag_sb['PEDIDO'].tolist()}

                        # Validação do telefone - Se não tiver, pula diretamente pro except blindado sem derrubar a aplicação
                        if not tel:
                            raise ValueError(f"Telefone não localizado no banco para {nom}.")

                        driver_placeholder.markdown(render_current_driver(nom, idx_ag + 1, total_agentes), unsafe_allow_html=True)
                                
                        datas_na_rota = pd.to_datetime(df_ag_sb['DATA'], format='%d/%m/%Y', errors='coerce').dropna().dt.date
                        if not datas_na_rota.empty:
                            d_min_zap = datas_na_rota.min().strftime('%d/%m/%Y')
                            d_max_zap = datas_na_rota.max().strftime('%d/%m/%Y')
                            data_str = f"{d_min_zap}" if d_min_zap == d_max_zap else f"{d_min_zap} a {d_max_zap}"
                        else:
                            data_str = hoje_br.strftime('%d/%m/%Y')

                        uf_agente_sb = ""
                        if 'UF' in df_ag_sb.columns:
                            ufs_unicos_sb = df_ag_sb['UF'].dropna().unique()
                            if len(ufs_unicos_sb) > 0:
                                uf_agente_sb = str(ufs_unicos_sb[0]).upper().strip()
                                
                        saudacao, fechamento = gerar_saudacao_spintax(nom, uf_agente_sb)
                                
                        sep1 = random.choice(['-------------------------------', '...............................', '=========================', '〰️〰️〰️〰️〰️〰️〰️〰️〰️'])
                        sep2 = random.choice(['---', '...', '===', ' '])
                        bullet = random.choice(['> 🔸', '👉', '📌', '📦', '➖'])
                        lab_lbl = random.choice(['LABORATÓRIO', 'LOCAL', 'PONTO DE COLETA'])

                        df_msg_sb = df_ag_sb.copy()
                        if 'CIDADE' in df_msg_sb.columns:
                            df_msg_sb['_CIDADE_WHATS'] = df_msg_sb['CIDADE'].apply(lambda c: normalizar_cidade_operacao(c, DF_AGENTES))
                        else:
                            df_msg_sb['_CIDADE_WHATS'] = ''
                        if 'BAIRRO' in df_msg_sb.columns:
                            df_msg_sb['_BAIRRO_WHATS'] = df_msg_sb.apply(
                                lambda row: normalizar_bairro_whatsapp(row.get('BAIRRO', ''), row.get('TOMADOR', tom_sandbox)),
                                axis=1,
                            )
                        else:
                            df_msg_sb['_BAIRRO_WHATS'] = ''
                        df_msg_sb['_CIDADE_WHATS'] = df_msg_sb['_CIDADE_WHATS'].replace('', 'SEM CIDADE')
                        df_msg_sb['_BAIRRO_WHATS'] = df_msg_sb['_BAIRRO_WHATS'].replace('', 'SEM BAIRRO')

                        msg_parts = [f"{saudacao}rota de 🗓️ {data_str}\n", "RESUMO DA ROTA:\n", "CIDADE | QTD", sep1]
                        tot_qtd = 0
                        for cid, count in df_msg_sb['_CIDADE_WHATS'].value_counts().items():
                            msg_parts.append(f"{str(cid).strip().ljust(20)} | {count:02d}")
                            tot_qtd += count
                        msg_parts.extend([sep1, f"TOTAL | {tot_qtd:02d}\n\n", "⬇️ DETALHES:", f"{sep2}\n"])

                        for cid, group in df_msg_sb.groupby('_CIDADE_WHATS', sort=False):
                            msg_parts.extend([sep2, f"{str(cid).strip().center(30)}", f"{sep2}\n"])
                            items = []
                            group = ordenar_grupo_por_bairro(group)
                            for _, row in group.iterrows():
                                bairro_msg = row.get('_BAIRRO_WHATS', normalizar_bairro_whatsapp(row.get('BAIRRO', ''), row.get('TOMADOR', tom_sandbox)))
                                item_str = f"{bullet} PEDIDO: {row.get('PEDIDO', 'SEM NUM')}\n> 🔬 {lab_lbl}: {row.get('LABORATORIO', '')}\n> 📍 Rua: {row.get('ENDERECO', '')}, {row.get('NUMERO', '')}\n> 🏘️ Bairro: {bairro_msg}\n> 📮 CEP: {row.get('CEP', '')}\n> 🏢 Tomador: {row.get('TOMADOR', '')}"
                                obs = str(row.get('OBSERVACOES', '')).strip()
                                if (not obs or obs.upper() in ['NAN', 'NONE']) and str(row.get('HORARIO', '')).strip():
                                    obs = f"[COLETA: {str(row.get('HORARIO', '')).strip()}]"
                                if obs and obs.upper() != 'NAN': item_str += f"\n> 📝 Aviso: {obs}"
                                items.append(item_str)
                            msg_parts.append(f"\n\n{random.choice(['. . . .', '---', ' '])}\n\n".join(items) + "\n")
                        msg_parts.append(f"\n{fechamento}")

                        INSTANCIA = "3F14E62A63D2B28DC385B20DE66F3711"
                        TOKEN = "2321563615C4242CB6031504"
                        CLIENT_TOKEN = "Ffaa43dcff1e14f0e985c91e92b24ed89S"
                        try:
                            requests.post(f"https://api.z-api.io/instances/{INSTANCIA}/token/{TOKEN}/presence", json={"phone": tel, "presence": "composing"}, headers={"Client-Token": CLIENT_TOKEN}, timeout=2)
                            time.sleep(random.uniform(2.0, 3.0))
                        except: pass

                        resultado_msg = "✅"
                        # Executa o envio principal do zap
                        if enviar_whatsapp_zapi(tel, "\n".join(msg_parts)):
                            time.sleep(random.uniform(2.0, 3.0))

                            # 🛡️ CORREÇÃO 2: Isolamento de falhas nos anexos. Se o PDF falhar, não derruba o sucesso da mensagem.
                            if is_autorizado_pdf:
                                try:
                                    try: requests.post(f"https://api.z-api.io/instances/{INSTANCIA}/token/{TOKEN}/presence", json={"phone": tel, "presence": "composing"}, headers={"Client-Token": CLIENT_TOKEN}, timeout=2)
                                    except: pass
                                            
                                    # NOVA LÓGICA: Arquivo PDF com RJ inteiro apenas para o luiz.paulo
                                    if ag_login == 'luiz.paulo':
                                        df_para_pdf = df_dispatch[df_dispatch['UF'] == 'RJ']
                                        nome_arq_pdf = f"COLETAS_GERAL_RJ_{hoje_br.strftime('%d%m')}.pdf"
                                        # Passamos "RJ - GERAL" no lugar do nome dele para o cabeçalho do PDF ficar coerente
                                        pdf_bytes = gerar_pdf_rota_whatsapp("RJ - GERAL", data_str, df_para_pdf)
                                    else:
                                        df_para_pdf = df_ag_sb
                                        nome_arq_pdf = f"ROTA_IGO_{nom.replace(' ', '_')}_{hoje_br.strftime('%d%m')}.pdf"
                                        pdf_bytes = gerar_pdf_rota_whatsapp(nom, data_str, df_para_pdf)
                                                
                                    enviar_pdf_zapi(tel, pdf_bytes, nome_arq_pdf)
                                    time.sleep(2.5)
                                except Exception as e_pdf:
                                    resultado_msg += " (Sem PDF)"

                            if is_autorizado_xls:
                                try:
                                    try: requests.post(f"https://api.z-api.io/instances/{INSTANCIA}/token/{TOKEN}/presence", json={"phone": tel, "presence": "composing"}, headers={"Client-Token": CLIENT_TOKEN}, timeout=2)
                                    except: pass
                                    if ag_login == 'luiz.paulo':
                                        df_para_xls = df_dispatch[df_dispatch['UF'] == 'RJ']
                                        nome_arq_xls = f"COLETAS_GERAL_RJ_{hoje_br.strftime('%d%m')}.xlsx"
                                    else:
                                        df_para_xls = df_ag_sb
                                        nome_arq_xls = f"ROTA_ESTRUTURADA_{nom.replace(' ', '_')}_{hoje_br.strftime('%d%m')}.xlsx"
                                    enviar_excel_zapi(tel, gerar_excel_rota_whatsapp(df_para_xls), nome_arq_xls)
                                    time.sleep(2.0)
                                except Exception as e_xls:
                                    resultado_msg += " (Sem XLS)"

                            sucessos_sb += 1
                            st.session_state.umove_resultados_disparo[nom]['sucesso'] = len(df_ag_sb)
                        else:
                            resultado_msg = "❌ Erro Z-API"
                            falhas_calc += 1
                            st.session_state.umove_resultados_disparo[nom]['sucesso'] = 0

                        pendentes_agora = total_agentes - (idx_ag + 1)
                        metrics_placeholder.markdown(render_big_metrics(total_agentes, pendentes_agora, sucessos_sb, falhas_calc), unsafe_allow_html=True)

                        pedidos_list = df_ag_sb['PEDIDO'].astype(str).tolist() if 'PEDIDO' in df_ag_sb.columns else []
                        pedidos_str = ", ".join(pedidos_list)[:200] + "..." if len(", ".join(pedidos_list)) > 200 else ", ".join(pedidos_list)

                        logs_google_sheets_zap.append([datetime.now(FUSO_BR).strftime('%d/%m/%Y %H:%M:%S'), nom, len(df_ag_sb), pedidos_str, 'SUCESSO' if '✅' in resultado_msg else 'FALHA', tel, 'SIM' if is_autorizado_pdf else 'NÃO', 'SIM' if is_autorizado_xls else 'NÃO', '', id_evento])
                        logs_df_data.append({"Hora": datetime.now(FUSO_BR).strftime('%H:%M:%S'), "Status": resultado_msg, "Motorista": nom, "Msg": f"Enviados {len(df_ag_sb)} vols"})

                    except Exception as e:
                        # 🔥 CAPA PROTETORA CONTRA QUEDAS: Se ocorrer erro grave (ex: Falta telefone), marca e segue.
                        falhas_calc += 1
                        nom_err = nom if 'nom' in locals() else f"ID: {ag}"
                        if nom_err not in st.session_state.umove_resultados_disparo:
                            st.session_state.umove_resultados_disparo[nom_err] = {'total': len(df_ag_sb) if 'df_ag_sb' in locals() else 0, 'sucesso': 0, 'pedidos': []}
                        logs_df_data.append({"Hora": datetime.now(FUSO_BR).strftime('%H:%M:%S'), "Status": "❌ ERRO", "Motorista": nom_err, "Msg": str(e)[:35]})
                                
                        pendentes_agora = total_agentes - (idx_ag + 1)
                        metrics_placeholder.markdown(render_big_metrics(total_agentes, pendentes_agora, sucessos_sb, falhas_calc), unsafe_allow_html=True)

                    log_table_placeholder.dataframe(pd.DataFrame(logs_df_data), use_container_width=True, hide_index=True)
                    progress_bar.progress((idx_ag + 1) / total_agentes)

                st.session_state.umove_final_metrics = {'total': total_agentes, 'sucesso': sucessos_sb, 'falhas': falhas_calc}
                driver_placeholder.empty() 
                        
                if logs_google_sheets_zap:
                    try:
                        import json
                        import gspread
                        from google.oauth2.credentials import Credentials
                        token_str = os.environ.get("google_token_json", st.secrets.get("google_token_json"))
                        token_info = json.loads(token_str)
                        creds = Credentials.from_authorized_user_info(token_info, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
                        cliente_gspread_novo = gspread.authorize(creds)
                        planilha_logs_externa = cliente_gspread_novo.open_by_key('1ckrOm_UyvD-Pc4TeLFfdVJA-48jXmULoisF7T5Pqv20')
                        aba_logs = planilha_logs_externa.worksheet("Disparos")
                        aba_logs.append_rows(logs_google_sheets_zap, value_input_option='USER_ENTERED')
                    except: pass

                sync_pendencias = []
                try:
                    if 'PEDIDO' in df_dispatch.columns:
                        aba_contador = planilha_sandbox.worksheet("Contador")
                        max_id_gerado = df_dispatch['PEDIDO'].astype(int).max()
                        aba_contador.update("A1", [[str(max_id_gerado + 1)]])
                except:
                    sync_pendencias.append("Falha ao atualizar aba Contador")

                st.session_state.umove_xls_bytes = gerar_relatorio_umove_xls(df_dispatch, st.session_state.umove_resultados_disparo)
                        
                lote_id_final = st.session_state.umove_lote_atual_id if st.session_state.umove_lote_atual_id else id_evento
                concluiu_hist = gerenciar_estado_lote("CONCLUIR", lote_id_final, resultados=st.session_state.umove_resultados_disparo)
                if not concluiu_hist:
                    sync_pendencias.append("Falha ao consolidar Historico_Disparos_Umove")
                        
                backup_ok = salvar_backup_completo_umove(df_dispatch, lote_id_final, planilha_sandbox)
                if not backup_ok:
                    sync_pendencias.append("Falha ao salvar Backup_Umove_Rotas")

                st.session_state.umove_sync_status = {
                    'ok': len(sync_pendencias) == 0,
                    'pendencias': sync_pendencias
                }
                        
                st.session_state.umove_lote_atual_id = None
                st.session_state.umove_step = 'COMPLETED'
                st.rerun()

            elif st.session_state.umove_step == 'COMPLETED':
                st.markdown("## 📊 Relatório Final da Missão")
                        
                metrics = st.session_state.umove_final_metrics
                st.markdown(render_big_metrics(metrics['total'], 0, metrics['sucesso'], metrics['falhas']), unsafe_allow_html=True)

                sync_ok = st.session_state.get('umove_sync_status', {}).get('ok', True)
                pendencias = st.session_state.get('umove_sync_status', {}).get('pendencias', [])
                if sync_ok:
                    st.success("🎉 O disparo em lote foi finalizado! O histórico foi consolidado na nuvem.")
                else:
                    st.warning("⚠️ Disparo concluído, porém ainda há pendências de gravação no Sheets. A mesa permanece bloqueada até concluir a sincronização.")
                    for p in pendencias:
                        st.markdown(f"- {p}")
                        
                col_rel1, col_rel2 = st.columns(2)
                with col_rel1:
                    if st.session_state.umove_xls_bytes:
                        st.download_button(
                            "📥 Baixar Relatório Sintético (XLS)",
                            data=st.session_state.umove_xls_bytes,
                            file_name=f"RELATORIO_DISPAROS_{hoje_br.strftime('%d%m%y_%H%M%S')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True,
                            type="primary")
                with col_rel2:
                    if st.button("🔄 Liberar Mesa para Novo Disparo", use_container_width=True, disabled=not sync_ok):
                        st.session_state.umove_step = 'IDLE'
                        st.session_state.umove_xls_bytes = None
                        st.session_state.umove_resultados_disparo = {}
                        st.session_state.umove_sync_status = {'ok': True, 'pendencias': []}
                        st.session_state.ui_toast = {'msg': "Mesa liberada para novo disparo.", 'icon': "✅"}
                        st.rerun()

    # =============================================================================
    # 🛟 ABA 5: RECUPERAÇÃO OFFLINE E REPROCESSAMENTO
    # =============================================================================
    with tab_backup:
        st.markdown("#### 🛟 Resgate de Lotes Inacabados (Nuvem)")
        df_rascunhos_bkp = gerenciar_estado_lote("LISTAR_RASCUNHOS")
        if df_rascunhos_bkp is not None and not df_rascunhos_bkp.empty:
            st.success("✅ **Lotes salvos na nuvem encontrados!**")
            for i, row_rasc in enumerate(df_rascunhos_bkp.to_dict('records')):
                with st.container(border=True):
                    col_r1, col_r2, col_r3 = st.columns([2.5, 1, 1], vertical_alignment="center")
                    col_r1.markdown(f"**Lote:** `{row_rasc.get('ID_EVENTO','')}` | **Criado em:** {row_rasc.get('DATA_DISPARO','')} | **Volumes:** {row_rasc.get('TOTAL_PEDIDOS','')}")
                            
                    if col_r2.button("Resgatar para o Carrinho", key=f"resg_t5_{i}_{row_rasc.get('ID_EVENTO','')}", use_container_width=True, type="primary"):
                        try:
                            df_resgatado = pd.read_json(io.StringIO(str(row_rasc.get('DADOS_JSON','[]'))), orient='records')
                            st.session_state.df_sandbox_mem = df_resgatado.astype(str)
                            st.session_state.umove_lote_atual_id = row_rasc.get('ID_EVENTO')
                            st.session_state.umove_step = 'IDLE'
                            st.toast("✅ Lote resgatado com sucesso!")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error("Falha na leitura do lote.")
                                    
                    if col_r3.button("🗑️ Excluir Backup", key=f"excl_t5_{i}_{row_rasc.get('ID_EVENTO','')}", use_container_width=True):
                        try:
                            with st.spinner("Excluindo lote da nuvem..."):
                                gerenciar_estado_lote("EXCLUIR_RASCUNHO", lote_id=row_rasc.get('ID_EVENTO'))
                                st.toast("🗑️ Lote excluído permanentemente!")
                                time.sleep(1)
                                st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao excluir: {e}")
        else:
            st.info("Nenhum lote salvo na nuvem no momento.")
                    
        st.markdown("---")
        st.markdown("#### 📂 Reconstrução por Arquivo (LOC/AGD)")
        st.info("Caso os arquivos não estejam na nuvem, você pode reconstruir a mesa fazendo o upload do par **LOC** e **AGD** gerados anteriormente.")
                
        with st.container(border=True):
            arquivos_upload = st.file_uploader("📂 Arraste e solte os arquivos LOC_GERAL e AGD_GERAL aqui (.csv)", type=["csv"], accept_multiple_files=True, key="upload_recuperacao")
                    
            if arquivos_upload and len(arquivos_upload) == 2:
                try:
                    df_loc = None
                    df_agd = None

                    for arquivo in arquivos_upload:
                        if "LOC" in arquivo.name.upper():
                            df_loc = pd.read_csv(arquivo, sep=";", encoding="utf-8-sig")
                        elif "AGD" in arquivo.name.upper():
                            df_agd = pd.read_csv(arquivo, sep=";", skiprows=1, encoding="utf-8-sig")

                    if df_loc is not None and df_agd is not None:
                        df_loc['corporateName'] = df_loc['corporateName'].str.replace('CAEP', 'SYNVIA', regex=False).str.replace('CUNHA', 'GRALAB', regex=False)
                        df_loc['alternativeIdentifier'] = df_loc['alternativeIdentifier'].str.replace('CAEP', 'SYNVIA', regex=False).str.replace('CUNHA', 'GRALAB', regex=False)
                        df_agd['serviceLocal'] = df_agd['serviceLocal'].str.replace('CAEP', 'SYNVIA', regex=False).str.replace('CUNHA', 'GRALAB', regex=False)
                        if 'city' in df_loc.columns: df_loc['city'] = df_loc['city'].str.replace('Brodosqui', 'Brodowski', regex=False)

                        df_cruzado = pd.merge(df_agd, df_loc, left_on="serviceLocal", right_on="alternativeIdentifier", how="inner")
                        df_cruzado = df_cruzado.dropna(subset=['agent'])

                        st.success(f"✅ Arquivos lidos e cruzados com sucesso: {len(df_cruzado)} volumes encontrados.")

                        if st.button("🚀 Restaurar Carrinho e Salvar Rascunho", type="primary", use_container_width=True):
                            with st.spinner("Reconstruindo estrutura original..."):
                                df_rec = pd.DataFrame()
                                df_rec['PEDIDO'] = df_cruzado['alternativeIdentifier_x']
                                df_rec['AGENTE_RAW'] = df_cruzado['agent']
                                df_rec['DATA'] = df_cruzado['date']
                                df_rec['TOMADOR'] = df_cruzado['CF_loc_responsavel_cliente']
                                        
                                def extract_lab(row):
                                    corp = str(row.get('corporateName', ''))
                                    tom = str(row.get('CF_loc_responsavel_cliente', ''))
                                    if corp.startswith(tom + "-"): return corp[len(tom)+1:]
                                    return corp
                                        
                                df_rec['LABORATORIO'] = df_cruzado.apply(extract_lab, axis=1)
                                df_rec['ENDERECO'] = df_cruzado['street']
                                df_rec['NUMERO'] = df_cruzado['streetNumber'].apply(lambda x: str(x).replace('.0', '') if x else '')
                                df_rec['BAIRRO'] = df_cruzado['cityNeighborhood']
                                df_rec['CIDADE'] = df_cruzado['city']
                                df_rec['UF'] = df_cruzado['state']
                                df_rec['CEP'] = df_cruzado['zipCode']
                                df_rec['CNPJ'] = df_cruzado['CF_CNPJ'].apply(lambda x: str(x).replace("'", "") if x else "")
                                df_rec['OBSERVACOES'] = ""

                                st.session_state.df_sandbox_mem = df_rec

                                if st.session_state.umove_lote_atual_id is None:
                                    st.session_state.umove_lote_atual_id = f"UMOVE-{datetime.now(FUSO_BR).strftime('%Y%m%d%H%M%S')}"
                                gerenciar_estado_lote("SALVAR_RASCUNHO", st.session_state.umove_lote_atual_id, st.session_state.df_sandbox_mem)
                                        
                                st.success("✅ Mesa reconstruída e rascunho salvo na nuvem! Volte à '🚀 Central de Envios' para disparar.")
                                time.sleep(1.5)
                                st.rerun()
                except Exception as e:
                    st.error(f"Erro ao processar a recuperação: {e}")
            else:
                st.warning("⚠️ Insira exatamente os dois arquivos (LOC_GERAL e AGD_GERAL) gerados pela plataforma simultaneamente para reprocessar os dados.")
# =============================================================================
# 📋 MÓDULO 3: TRIAGEM E ROMANEIO (COM CONTINGÊNCIA AVULSA E HISTÓRICO)
# =============================================================================
elif menu == "🔬 Triagem":
    import streamlit.components.v1 as components

    # 🔥 PING SILENCIOSO (ANTI-TIMEOUT DO RENDER) 🔥
    components.html(
        """
        <script>
        setInterval(function() {
            fetch(window.location.href);
        }, 240000);
        </script>
        """,
        height=0, width=0
    )

    st.markdown(
        "<div class='dinamic-border'><h3 class='dinamic-text' style='margin:0;'>🔬 Terminal de Triagem e Expedição</h3></div>",
        unsafe_allow_html=True)
    df_raw = carregar_dados_completos(planilha_db)

    # =========================================================================
    # ⚙️ RECURSOS VISUAIS GLOBAIS E COMPONENTES UI
    # =========================================================================
            
    def exibir_empty_state(icone, titulo, subtitulo):
        html = (
            f'<div style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 50px 20px; text-align: center; background-color: #f8fafc; border-radius: 12px; border: 2px dashed #cbd5e1; margin-top: 10px; margin-bottom: 20px;">'
            f'<div style="font-size: 50px; margin-bottom: 12px; opacity: 0.9;">{icone}</div>'
            f'<h4 style="color: #0f172a; margin-bottom: 6px; font-weight: 800;">{titulo}</h4>'
            f'<p style="color: #64748b; font-size: 14px; max-width: 450px; margin: 0;">{subtitulo}</p>'
            f'</div>'
        )
        st.markdown(html, unsafe_allow_html=True)

    def renderizar_kpis(lista_kpis):
        html = '<div style="display: flex; gap: 15px; margin-bottom: 20px; margin-top: 10px;">'
        for val, lbl, c1, c2 in lista_kpis:
            html += f'<div style="flex: 1; background: linear-gradient(135deg, {c1} 0%, {c2} 100%); border-radius: 10px; height: 80px; display: flex; flex-direction: column; justify-content: center; align-items: center; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -1px rgba(0,0,0,0.03);">'
            html += f'<p style="color: rgba(255,255,255,0.9); font-weight: 800; font-size: 12px; margin: 0; text-transform: uppercase; letter-spacing: 0.5px;">{lbl}</p>'
            html += f'<p style="color: white; font-weight: 900; font-size: 26px; margin: 2px 0 0 0; line-height: 1;">{val}</p>'
            html += '</div>'
        html += '</div>'
        st.markdown(html, unsafe_allow_html=True)

    st.markdown(
        """
        <style>
        div[data-testid="stTabs"] div[data-baseweb="tab-list"] {
            gap: 14px;
            margin-bottom: 16px;
            align-items: stretch;
        }
        div[data-testid="stTabs"] button[role="tab"] {
            background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%) !important;
            border: 1px solid #dbe3ef !important;
            border-radius: 12px !important;
            color: #334155 !important;
            font-weight: 700 !important;
            min-height: 50px !important;
            padding: 0 18px !important;
            line-height: 1.25 !important;
            letter-spacing: 0.15px !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04) !important;
            transition: all 0.2s ease !important;
        }
        div[data-testid="stTabs"] button[role="tab"] {
            padding: 0 18px !important;
            min-height: 50px !important;
            line-height: 1.25 !important;
        }
        div[data-testid="stTabs"] button[role="tab"] p {
            margin: 0 !important;
            line-height: 1.25 !important;
            white-space: nowrap !important;
        }
        div[data-testid="stTabs"] button[role="tab"]:hover {
            border-color: #93c5fd !important;
            color: #0f172a !important;
            transform: translateY(-1px);
            box-shadow: 0 6px 16px rgba(37, 99, 235, 0.10) !important;
        }
        div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
            background: linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%) !important;
            border-color: #1d4ed8 !important;
            border-radius: 12px !important;
            color: #ffffff !important;
            box-shadow: 0 10px 20px rgba(37, 99, 235, 0.22) !important;
            overflow: hidden !important;
            padding: 0 20px !important;
        }
        div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] p {
            letter-spacing: 0.2px !important;
            line-height: 1.3 !important;
        }
        div[data-testid="stForm"],
        div[data-testid="stExpander"],
        div[data-testid="stDataFrame"],
        div[data-testid="stVerticalBlockBorderWrapper"],
        div[data-testid="stAlert"] {
            border-radius: 14px !important;
        }
        div[data-testid="stExpander"] {
            border: 1px solid #dbe3ef !important;
            background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%) !important;
            box-shadow: 0 6px 16px rgba(15, 23, 42, 0.05) !important;
        }
        div[data-testid="stTextArea"] textarea,
        div[data-testid="stTextInput"] input,
        div[data-testid="stDateInput"] input,
        div[data-testid="stDateInput"] button,
        div[data-testid="stSelectbox"] > div[data-baseweb="select"] > div,
        div[data-testid="stMultiSelect"] > div[data-baseweb="select"] > div {
            background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%) !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 10px !important;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05) !important;
        }
        div[data-testid="stTextArea"] textarea:focus,
        div[data-testid="stTextInput"] input:focus,
        div[data-testid="stDateInput"] input:focus {
            border-color: #60a5fa !important;
            box-shadow: 0 0 0 1px #93c5fd !important;
        }
        div[data-testid="stFormSubmitButton"] > button,
        div.stButton > button:not([kind="primary"]),
        div[data-testid="stPopover"] > div > button,
        div[data-testid="stPopover"] > button {
            background: linear-gradient(180deg, #eff6ff 0%, #dbeafe 100%) !important;
            color: #0f172a !important;
            border: 1px solid #93c5fd !important;
            border-radius: 10px !important;
            font-weight: 700 !important;
            box-shadow: 0 4px 10px rgba(37, 99, 235, 0.10) !important;
            min-height: 42px !important;
            transition: all 0.2s ease !important;
        }
        div[data-testid="stFormSubmitButton"] > button:hover,
        div.stButton > button:not([kind="primary"]):hover,
        div[data-testid="stPopover"] > div > button:hover,
        div[data-testid="stPopover"] > button:hover {
            background: linear-gradient(180deg, #dbeafe 0%, #bfdbfe 100%) !important;
            border-color: #60a5fa !important;
            box-shadow: 0 8px 18px rgba(37, 99, 235, 0.18) !important;
            transform: translateY(-1px) !important;
        }
        div.stButton > button[kind="primary"],
        div[data-testid="stFormSubmitButton"] > button[kind="primary"] {
            background: linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%) !important;
            border: 1px solid #1d4ed8 !important;
            color: #ffffff !important;
            box-shadow: 0 10px 20px rgba(37, 99, 235, 0.22) !important;
        }
        div.stButton > button[kind="primary"]:hover,
        div[data-testid="stFormSubmitButton"] > button[kind="primary"]:hover {
            background: linear-gradient(135deg, #0284c7 0%, #1d4ed8 100%) !important;
            border-color: #1e40af !important;
            color: #ffffff !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    custom_css_premium = {
        ".ag-theme-alpine": {
            "--ag-font-family": "Inter, sans-serif",
            "--ag-font-size": "13px",
            "--ag-row-height": "40px",
            "--ag-header-height": "44px",
            "background-color": "#ffffff !important",
            "border": "1px solid #dbe3ef",
            "border-radius": "12px",
            "overflow": "hidden",
            "box-shadow": "0 8px 20px rgba(15, 23, 42, 0.07)"
        },
        ".ag-root-wrapper": {"background-color": "#ffffff !important"},
        ".ag-root-wrapper-body": {"background-color": "#ffffff !important"},
        ".ag-body-viewport": {"background-color": "#ffffff !important"},
        ".ag-header": {
            "background": "linear-gradient(180deg, #f8fafc 0%, #e2e8f0 100%) !important",
            "border-bottom": "1px solid #cbd5e1 !important"
        },
        ".ag-header-cell": {
            "border-right": "1px solid #dbe3ef !important",
            "padding-top": "5px !important",
            "padding-bottom": "5px !important"
        },
        ".ag-header-cell-text": {
            "color": "#0f172a !important",
            "font-weight": "800 !important",
            "font-size": "12px !important",
            "letter-spacing": "0.35px !important",
            "text-transform": "uppercase !important"
        },
        ".ag-row": {
            "border-bottom": "1px solid #eef2f7 !important",
            "transition": "background-color 0.2s ease !important"
        },
        ".ag-row:hover": {
            "background-color": "#dbeafe !important",
            "cursor": "pointer",
            "box-shadow": "inset 3px 0 0 #2563eb !important"
        },
        ".ag-row-odd": {"background": "linear-gradient(90deg, #ffffff 0%, #fcfdff 100%) !important"},
        ".ag-row-even": {"background": "linear-gradient(90deg, #f8fafc 0%, #f1f5f9 100%) !important"},
        ".ag-cell": {
            "display": "flex !important",
            "align-items": "center !important",
            "border-right": "1px solid #eef2f7 !important"
        },
        ".ag-paging-panel": {
            "background": "#f8fafc !important",
            "border-top": "1px solid #dbe3ef !important",
            "padding": "8px 10px !important"
        }
    }

    status_jscode_tri = JsCode("""
    class StatusBadgeRenderer {
    init(params) {
        this.eGui = document.createElement('div');
        this.eGui.style.cssText = 'display: flex; align-items: center; height: 100%;';
        let badge = document.createElement('span');
        badge.style.cssText = 'display: inline-flex; align-items: center; justify-content: center; padding: 4px 10px; border-radius: 99px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; height: 22px;';
        let text = params.value || '';
        let status = text.toUpperCase();

        if (status.includes('ENTREGUE') || status.includes('CONFERIDO')) { badge.style.backgroundColor = '#dcfce7'; badge.style.color = '#166534'; badge.style.border = '1px solid #bbf7d0'; }
        else if (status.includes('FRUSTRADA') || status.includes('PROBLEMA') || status.includes('CANCELADO')) { badge.style.backgroundColor = '#fee2e2'; badge.style.color = '#991b1b'; badge.style.border = '1px solid #fecaca'; }
        else if (status.includes('COLETADO') || status.includes('EM ROTA DE ENTREGA') || status.includes('ROTA')) { badge.style.backgroundColor = '#dbeafe'; badge.style.color = '#1e40af'; badge.style.border = '1px solid #bfdbfe'; }
        else if (status.includes('PENDENTE') || status.includes('AGUARDANDO')) { badge.style.backgroundColor = '#fef3c7'; badge.style.color = '#b45309'; badge.style.border = '1px solid #fde68a'; }
        else { badge.style.backgroundColor = '#f1f5f9'; badge.style.color = '#475569'; badge.style.border = '1px solid #e2e8f0'; }

        badge.innerText = text;
        this.eGui.appendChild(badge);
    }
    getGui() { return this.eGui; }
    }
    """)

    CLIENTES_ATUALIZADOS = sorted(list(set([c.replace('CAEP', 'SYNVIA').replace('CUNHA', 'GRALAB') for c in CLIENTES_AUTORIZADOS])))

    # --- CONEXÃO COM O COFRE DE AVULSOS ---
    @st.cache_resource
    def obter_planilha_avulsos():
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        try:
            import json
            from google.oauth2.credentials import Credentials
            token_str = os.environ.get("google_token_json")
            if not token_str:
                try: token_str = st.secrets.get("google_token_json")
                except BaseException: pass
            if not token_str: return None
            token_info = json.loads(token_str)
            creds = Credentials.from_authorized_user_info(token_info, scopes=scopes)
            gc = gspread.authorize(creds)
            return gc.open_by_key("1puECAowymzkiwAObEt4KPeAYiBeIOKtCsSLOIklZJgk")
        except BaseException:
            return None

    # 🔥 IMPRESSORA EXCLUSIVA PARA TRIAGEM MANUAL 🔥
    def gerar_pdf_triagem_manual(id_lote, data_str, tomador, lista_itens):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_draw_color(15, 23, 42)
        pdf.set_line_width(0.3)
        pdf.rect(5, 5, 200, 287)
        try:
            logo_path = os.path.join(tempfile.gettempdir(), "igo_logo_temp.png")
            if not os.path.exists(logo_path):
                req = urllib.request.Request("https://i.postimg.cc/x84nnjjq/IGO-LOGO.png", headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response, open(logo_path, 'wb') as out_file:
                    out_file.write(response.read())
            pdf.image(logo_path, x=10, y=8, w=30)
        except BaseException: pass

        pdf.set_y(15)
        pdf.set_font("Arial", "B", 14)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(0, 6, "PROTOCOLO DE TRIAGEM MANUAL DE ENVELOPES", ln=True, align="C")
        pdf.set_font("Arial", "B", 10)
        pdf.set_text_color(2, 132, 199)
        pdf.cell(0, 5, f"LOTE: {id_lote}", ln=True, align="C")
        pdf.set_font("Arial", "", 8)
        pdf.set_text_color(100, 116, 139)

        dt_s = data_str if isinstance(data_str, str) else data_str.strftime('%d/%m/%Y')
        pdf.cell(0, 4, f"Data da Triagem: {dt_s} | Hub de Destino: {tomador}", ln=True, align="C")
        pdf.ln(3)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(3)

        def cortar_texto(valor, limite):
            texto = str(valor).strip()
            if len(texto) <= limite:
                return texto
            return texto[:max(0, limite - 3)].rstrip() + "..."

        tem_campos_opcionais = any(
            str(item.get('PEDIDO', '')).strip() or str(item.get('CLIENTE', '')).strip()
            for item in lista_itens
        )
        larguras_tabela = [12, 18, 34, 32, 28, 28] if tem_campos_opcionais else [20, 90, 40, 40]
        inicio_tabela = (pdf.w - sum(larguras_tabela)) / 2

        pdf.set_fill_color(15, 23, 42)
        pdf.set_text_color(255, 255, 255)
        pdf.set_x(inicio_tabela)
        if tem_campos_opcionais:
            pdf.set_font("Arial", "B", 6)
            pdf.cell(12, 6, "ITEM", 1, 0, "C", True)
            pdf.cell(18, 6, "PEDIDO", 1, 0, "C", True)
            pdf.cell(34, 6, "CLIENTE", 1, 0, "C", True)
            pdf.cell(32, 6, "ENV.", 1, 0, "C", True)
            pdf.cell(28, 6, "DATA", 1, 0, "C", True)
            pdf.cell(28, 6, "HORA", 1, 1, "C", True)
        else:
            pdf.set_font("Arial", "B", 8)
            pdf.cell(20, 6, "ITEM", 1, 0, "C", True)
            pdf.cell(90, 6, "NUMERO DO ENVELOPE", 1, 0, "C", True)
            pdf.cell(40, 6, "DATA DA BIPAGEM", 1, 0, "C", True)
            pdf.cell(40, 6, "HORA DA BIPAGEM", 1, 1, "C", True)

        pdf.set_text_color(51, 65, 85)
        pdf.set_font("Arial", "", 6 if tem_campos_opcionais else 8)

        for idx, item in enumerate(lista_itens, 1):
            fill = (idx % 2 == 0)
            pdf.set_fill_color(241, 245, 249) if fill else pdf.set_fill_color(255, 255, 255)
            env = str(item.get('ENVELOPE', ''))
            pedido = str(item.get('PEDIDO', '')).strip()
            cliente = str(item.get('CLIENTE', '')).strip()
            dt_bip = str(item.get('DATA', ''))
            hr_bip = str(item.get('HORA', ''))

            pdf.set_x(inicio_tabela)
            if tem_campos_opcionais:
                pdf.cell(12, 6, str(idx), 1, 0, "C", True)
                pdf.cell(18, 6, cortar_texto(pedido, 9), 1, 0, "C", True)
                pdf.cell(34, 6, cortar_texto(cliente, 14), 1, 0, "C", True)
                pdf.cell(32, 6, cortar_texto(env, 14), 1, 0, "C", True)
                pdf.cell(28, 6, dt_bip, 1, 0, "C", True)
                pdf.cell(28, 6, hr_bip, 1, 1, "C", True)
            else:
                pdf.cell(20, 6, str(idx), 1, 0, "C", True)
                pdf.cell(90, 6, env, 1, 0, "C", True)
                pdf.cell(40, 6, dt_bip, 1, 0, "C", True)
                pdf.cell(40, 6, hr_bip, 1, 1, "C", True)

        pdf.ln(6)
        pdf.set_font("Arial", "B", 8)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(0, 5, f"TOTAL DE ENVELOPES CONFERIDOS: {len(lista_itens)}", ln=True, align="R")
        pdf.set_y(-25)
        pdf.line(55, pdf.get_y(), 155, pdf.get_y())
        pdf.set_font("Arial", "B", 7)
        pdf.cell(0, 4, "ASSINATURA DO RESPONSAVEL PELA TRIAGEM", 0, 1, "C")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
            pdf.output(tmp_pdf.name)
            with open(tmp_pdf.name, "rb") as f:
                pdf_bytes = f.read()
        return pdf_bytes

    # --- CONTROLES DE MEMÓRIA ---
    if 'triagem_avulsa_lote' not in st.session_state: st.session_state.triagem_avulsa_lote = []
    if 'pdf_avulso_pronto' not in st.session_state: st.session_state.pdf_avulso_pronto = None
    if 'id_avulso_pronto' not in st.session_state: st.session_state.id_avulso_pronto = None
    if 'log_triagem' not in st.session_state: st.session_state.log_triagem = []
    if 'romaneio_sucesso' not in st.session_state: st.session_state.romaneio_sucesso = False

    t1, t2, t3, t4 = st.tabs(["📦 1. Validação Manual & Bipar", "🚚 2. Gerar Documento de Romaneio",
                            "📦 3. Volumes Despachados", "📝 4. Triagem Manual (Envelopes)"])

    # =========================================================================
    # ABA 1: VALIDAÇÃO MANUAL E BIPAR
    # =========================================================================
    with t1:
        if df_raw.empty:
            exibir_empty_state("📭", "Banco Vazio", "Aguardando sincronização de dados operacionais da nuvem.")
        else:
            st.info("💡 A auditoria de triagem oficial aceita apenas materiais **COLETADOS** pelo aplicativo do motorista.")
                    
            col_bip_esq, col_bip_dir = st.columns([1.5, 1])
            with col_bip_esq:
                with st.form("form_bip", clear_on_submit=True):
                    col_bip, col_btn = st.columns([3, 1])
                    # Flag para bloquear bipagem enquanto está sincronizando
                    if 'bipagem_em_progresso' not in st.session_state:
                        st.session_state.bipagem_em_progresso = False
                            
                    bip_input = col_bip.text_input("🔍 Bipar QR Code de Validação / Pedido:", disabled=st.session_state.bipagem_em_progresso)
                    if col_btn.form_submit_button("Auditar", use_container_width=True, disabled=st.session_state.bipagem_em_progresso) and bip_input:
                        termo = re.sub(r'[^A-Z0-9]', '', bip_input.upper())
                        ped_limpo = df_raw['PEDIDO'].astype(str).str.upper().apply(lambda x: re.sub(r'[^A-Z0-9]', '', str(x)))
                        mask = (ped_limpo == termo)
                        if 'QR_CODE' in df_raw.columns:
                            qr_limpo = df_raw['QR_CODE'].astype(str).str.upper().apply(lambda x: re.sub(r'[^A-Z0-9]', '', str(x)))
                            mask = mask | (qr_limpo == termo)
                                
                        if mask.any():
                            idx = df_raw[mask].index[-1]
                            status_atual_bip = str(df_raw.at[idx, 'STATUS']).strip().upper()
                            if status_atual_bip == 'COLETADO':
                                # 🔥 BLOQUEIO: Marca bipagem em progresso
                                st.session_state.bipagem_em_progresso = True
                                try:
                                    # 🔥 PROTEÇÃO CONTRA TIMEOUT: Mostra spinner e aguarda sincronização com Google Sheets
                                    with st.spinner("⏳ Sincronizando com a nuvem (Google Sheets)... Aguarde até 10s"):
                                        # 🔥 RETRY COM TIMEOUT AUMENTADO (até 3 tentativas com espera progressiva)
                                        aba = planilha_db.worksheet("Memoria_Sistema")
                                        pedido_alvo = str(df_raw.at[idx, 'PEDIDO'])
                                        headers = aba.row_values(1)
                                        agora_bip = datetime.now(FUSO_BR)
                                        data_bip_str = agora_bip.strftime('%d/%m/%Y')
                                        hora_bip_str = agora_bip.strftime('%H:%M:%S')
                                        if 'PEDIDO' in headers and 'STATUS' in headers:
                                            col_pedido = headers.index('PEDIDO') + 1
                                            col_status = headers.index('STATUS') + 1
                                                    
                                            # 🔥 RETRY LOOP: Tenta 3 vezes com pequeno delay entre tentativas
                                            tentativas = 0
                                            max_tentativas = 3
                                            sucesso_update = False
                                            ultima_excecao = None
                                                    
                                            while tentativas < max_tentativas and not sucesso_update:
                                                try:
                                                    cell = aba.find(pedido_alvo, in_column=col_pedido)
                                                    if cell:
                                                        updates = [{'range': gspread.utils.rowcol_to_a1(cell.row, col_status), 'values': [['CONFERIDO']]}]
                                                        # Registrar data e hora do bip se as colunas existirem
                                                        if 'DATA_BIP' in headers:
                                                            col_data_bip = headers.index('DATA_BIP') + 1
                                                            updates.append({'range': gspread.utils.rowcol_to_a1(cell.row, col_data_bip), 'values': [[data_bip_str]]})
                                                        if 'HORA_BIP' in headers:
                                                            col_hora_bip = headers.index('HORA_BIP') + 1
                                                            updates.append({'range': gspread.utils.rowcol_to_a1(cell.row, col_hora_bip), 'values': [[hora_bip_str]]})
                                                                
                                                        # Update - aguarda resposta do Google Sheets
                                                        aba.batch_update(updates)
                                                        sucesso_update = True
                                                    else:
                                                        raise Exception(f"Pedido {pedido_alvo} não encontrado")
                                                except Exception as e:
                                                    ultima_excecao = e
                                                    tentativas += 1
                                                    if tentativas < max_tentativas:
                                                        # Aguarda 1s antes de tentar novamente
                                                        time.sleep(1)       
                                                        continue
                                                    else:
                                                        raise ultima_excecao
                                                    
                                            if sucesso_update:
                                                pass  # Sem delay adicional - fluido!
                                                st.session_state.log_triagem.insert(0, {'PEDIDO': str(df_raw.at[idx, 'PEDIDO']), 'TOMADOR': str(df_raw.at[idx, 'TOMADOR']), 'LABORATORIO': str(df_raw.at[idx, 'LABORATORIO']), 'CIDADE': str(df_raw.at[idx, 'CIDADE']), 'DATA_BIP': data_bip_str, 'HORA': hora_bip_str})
                                                st.session_state.ui_toast = {'msg': f"Pedido {pedido_alvo} VALIDADO! ✅ ({hora_bip_str})", 'icon': "✅"}
                                                carregar_dados_completos.clear()
                                                # 🔥 LIBERA: Próxima bipagem pode começar
                                                st.session_state.bipagem_em_progresso = False
                                                st.rerun()
                                            else:
                                                st.error("❌ Pedido não encontrado na nuvem. Verifique a digitação.")
                                                st.session_state.bipagem_em_progresso = False
                                        else:
                                            st.error("❌ Colunas PEDIDO ou STATUS não encontradas na planilha.")
                                            st.session_state.bipagem_em_progresso = False
                                except Exception as e:
                                    st.error(f"⚠️ Erro de sincronização com a nuvem: {str(e)[:80]}. Aguarde alguns segundos e tente novamente.")
                                    # 🔥 LIBERA: Permite tentar novamente
                                    st.session_state.bipagem_em_progresso = False
                            elif status_atual_bip == 'CONFERIDO':
                                pedido_ja_triado = str(df_raw.at[idx, 'PEDIDO'])
                                lab_ja_triado = str(df_raw.at[idx, 'LABORATORIO'])
                                hora_bip_anterior = str(df_raw.at[idx, 'HORA_BIP']) if 'HORA_BIP' in df_raw.columns and str(df_raw.at[idx, 'HORA_BIP']).strip() not in ['', 'nan', 'None'] else ''
                                data_bip_anterior = str(df_raw.at[idx, 'DATA_BIP']) if 'DATA_BIP' in df_raw.columns and str(df_raw.at[idx, 'DATA_BIP']).strip() not in ['', 'nan', 'None'] else ''
                                info_bip = f" em {data_bip_anterior} às {hora_bip_anterior}" if data_bip_anterior and hora_bip_anterior else ""
                                st.warning(f"⚠️ **ATENÇÃO: Pedido já triado!**\n\n**{pedido_ja_triado}** — {lab_ja_triado}\n\nEste volume já foi bipado e está aguardando na **Aba 2 (Romaneio)**{info_bip}. Não é necessário bipar novamente.")
                                st.session_state.bipagem_em_progresso = False
                            else:
                                st.error("❌ Volume não está com status COLETADO. Verifique se foi coletado no app.")
                                st.session_state.bipagem_em_progresso = False
                        else:
                            st.error("❌ Assinatura ou Pedido não reconhecido. Verifique o QR Code.")
                            st.session_state.bipagem_em_progresso = False
                    
            with col_bip_dir:
                st.markdown("<div style='border: 1px solid #E2E8F0; padding: 10px; border-radius: 8px; background-color: #F8FAFC; height: 130px; overflow-y: auto;'>", unsafe_allow_html=True)
                st.markdown("<p style='margin-bottom: 5px; font-weight: bold; color: #0F172A; font-size: 14px;'>⏱️ Últimos Bips (Sessão):</p>", unsafe_allow_html=True)
                if st.session_state.log_triagem:
                    for item in st.session_state.log_triagem[:5]:
                        data_bip_disp = item.get('DATA_BIP', hoje_br.strftime('%d/%m/%Y'))
                        st.markdown(
                            f"<div style='font-size: 11px; color: #334155; margin-bottom: 3px;'>🟢 <b>{item['PEDIDO']}</b> - {item['LABORATORIO']} <br><span style='color: #64748B; padding-left: 15px;'>{item['TOMADOR']} | {item['CIDADE']} | 📅 {data_bip_disp} {item['HORA']}</span></div>",
                            unsafe_allow_html=True)
                else:
                    st.markdown("<p style='font-size: 12px; color: #94A3B8;'>Nenhum volume bipado ainda.</p>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("---")
            df_fila = df_raw[df_raw['STATUS'].astype(str).str.upper() == 'COLETADO'].copy()
            if not df_fila.empty:
                with st.expander("🔎 Filtrar Fila de Triagem", expanded=False):
                    tomador_filtro_t1 = st.selectbox("🏢 Filtrar por Hub de Destino:", ["Todos"] + sorted(df_fila['TOMADOR'].astype(str).unique().tolist()), key="filtro_tomador_t1")
                if tomador_filtro_t1 != "Todos":
                    df_fila = df_fila[df_fila['TOMADOR'] == tomador_filtro_t1]

                renderizar_kpis([
                    (len(df_fila), "📦 Volumes Aguardando Bipagem", "#1E293B", "#334155"),
                    (len(st.session_state.log_triagem), "✅ Bipados Nesta Sessão", "#059669", "#10B981")
                ])

                # Preparando as colunas blindadas para evitar erros de render
                colunas_validas = [c for c in ['DATA', 'PEDIDO', 'TOMADOR', 'LABORATORIO', 'CIDADE', 'STATUS'] if c in df_fila.columns]
                df_fila_show = df_fila[colunas_validas].fillna("").astype(str).copy()
                        
                gb_fila = GridOptionsBuilder.from_dataframe(df_fila_show)
                gb_fila.configure_selection('multiple', use_checkbox=True, header_checkbox=True, header_checkbox_filtered_only=True)
                gb_fila.configure_default_column(resizable=True, filterable=True, sortable=True)
                        
                if "DATA" in df_fila_show.columns: gb_fila.configure_column("DATA", header_name="📅 Coleta", width=110)
                if "PEDIDO" in df_fila_show.columns: gb_fila.configure_column("PEDIDO", header_name="📦 Pedido", width=120)
                if "TOMADOR" in df_fila_show.columns: gb_fila.configure_column("TOMADOR", header_name="🏢 Hub Destino", width=160)
                if "LABORATORIO" in df_fila_show.columns: gb_fila.configure_column("LABORATORIO", header_name="🏭 Ponto de Coleta", width=250)
                if "CIDADE" in df_fila_show.columns: gb_fila.configure_column("CIDADE", header_name="📍 Cidade", width=150)
                if "STATUS" in df_fila_show.columns: gb_fila.configure_column("STATUS", header_name="🚦 Status", cellRenderer=status_jscode_tri, width=150)
                        
                st.markdown("<p style='font-size: 13px; color: #64748b; margin-bottom: 5px;'>Selecione volumes avulsos caso precise forçar a conferência sem o leitor de código de barras.</p>", unsafe_allow_html=True)
                        
                grid_fila = AgGrid(
                    df_fila_show, 
                    gridOptions=gb_fila.build(), 
                    theme="alpine", 
                    columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS, 
                    height=350, 
                    allow_unsafe_jscode=True, 
                    custom_css=custom_css_premium,
                    key="grid_triagem_fila")

                sel_fila_raw = grid_fila.get('selected_rows', [])
                if isinstance(sel_fila_raw, pd.DataFrame):
                    df_sel_fila = sel_fila_raw
                elif isinstance(sel_fila_raw, list) and len(sel_fila_raw) > 0:
                    df_sel_fila = pd.DataFrame(sel_fila_raw)
                else:
                    df_sel_fila = pd.DataFrame(columns=df_fila_show.columns)
                        
                if st.button("✅ Enviar Selecionados para Despacho (Forçar Validação)", type="primary"):
                    if df_sel_fila.empty:
                        st.toast("Marque os pedidos na tabela primeiro!", icon="⚠️")
                    else:
                        with st.spinner("Conferindo lote em massa..."):
                            p_ids = df_sel_fila['PEDIDO'].astype(str).tolist()
                            try:
                                aba = planilha_db.worksheet("Memoria_Sistema")
                                dados_nuvem = aba.get_all_values()
                                df_nuvem = pd.DataFrame(dados_nuvem[1:], columns=dados_nuvem[0])
                                df_nuvem.loc[df_nuvem['PEDIDO'].isin(p_ids), 'STATUS'] = 'CONFERIDO'
                                aba.update("A1", [df_nuvem.columns.tolist()] + df_nuvem.fillna("").astype(str).values.tolist())
                                st.session_state.ui_toast = {'msg': f"{len(p_ids)} volumes liberados!", 'icon': "🎉"}
                                time.sleep(1.0)
                                carregar_dados_completos.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro: {e}")
            else:
                exibir_empty_state("🧹", "Salão Limpo", "Não há nenhum volume com status COLETADO aguardando conferência.")

    # =========================================================================
    # ABA 2: GERAR DOCUMENTO DE ROMANEIO
    # =========================================================================
    with t2:
        if st.session_state.romaneio_sucesso:
            st.markdown("#### 🚚 Romaneio de Expedição Finalizado")
            st.success(f"🎉 O Lote de Embarque {st.session_state.romaneio_id} foi selado e registrado com sucesso!")
                    
            c_b1, c_b2 = st.columns(2)
            c_b1.download_button(
                label="📥 BAIXAR PROTOCOLO DE ROMANEIO (PDF)",
                data=st.session_state.romaneio_pdf,
                file_name=f"Romaneio_IGO_{st.session_state.romaneio_id}.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True
            )
            if c_b2.button("🔄 Voltar / Novo Despacho", use_container_width=True):
                st.session_state.romaneio_sucesso = False
                st.rerun()
        else:
            if df_raw.empty:
                exibir_empty_state("📭", "Banco Vazio", "Aguardando dados...")
            else:
                df_conf = df_raw[df_raw['STATUS'].astype(str).str.upper() == 'CONFERIDO'].copy()
                if not df_conf.empty:
                    # 🔥 BARRA DE BUSCA RÁPIDA + FILTRO DE HUB 🔥
                    col_busca_rom, col_filtro_rom = st.columns([2, 1])
                    busca_romaneio = col_busca_rom.text_input(
                        "🔍 Localizar Pedido:",
                        placeholder="Digite o nº do pedido, laboratório ou cidade...",
                        key="busca_romaneio_t2"
                    )
                    tomador_filtro = col_filtro_rom.selectbox(
                        "🏢 Filtrar Hub:",
                        ["Todos"] + sorted(df_conf['TOMADOR'].astype(str).unique().tolist()),
                        key="filtro_tomador_t2"
                    )

                    if tomador_filtro != "Todos":
                        df_conf = df_conf[df_conf['TOMADOR'] == tomador_filtro]

                    # Aplica busca em texto sobre todas as colunas
                    if busca_romaneio.strip():
                        mask_busca = df_conf.apply(
                            lambda row: row.astype(str).str.contains(busca_romaneio.strip(), case=False, na=False).any(), axis=1
                        )
                        df_conf_busca = df_conf[mask_busca]
                        if df_conf_busca.empty:
                            st.warning(f"⚠️ Nenhum pedido encontrado com '{busca_romaneio}'.")
                        else:
                            st.success(f"✅ {len(df_conf_busca)} pedido(s) encontrado(s) para '{busca_romaneio}'.")
                        df_conf = df_conf_busca

                    renderizar_kpis([
                        (len(df_conf), "📦 Volumes Prontos p/ Embarque", "#0ea5e9", "#06b6d4"),
                        (df_conf['TOMADOR'].nunique(), "🏢 Hubs com Carga", "#6366f1", "#8b5cf6")
                    ])

                    # Incluir campos operacionais extras (bairro e motorista) quando disponíveis
                    colunas_validas_conf = [
                        c for c in ['DATA', 'PEDIDO', 'TOMADOR', 'LABORATORIO', 'CIDADE', 'BAIRRO', 'UF', 'DATA_BIP', 'HORA_BIP']
                        if c in df_conf.columns
                    ]
                    df_conf_show = df_conf[colunas_validas_conf].fillna("").astype(str).copy()

                    if 'MOTORISTA' in df_conf.columns:
                        df_conf_show['MOTORISTA'] = df_conf['MOTORISTA'].fillna("").astype(str)
                    elif 'AGENTE_RAW' in df_conf.columns:
                        df_conf_show['MOTORISTA'] = df_conf['AGENTE_RAW'].fillna("").astype(str)
                            
                    gb_conf = GridOptionsBuilder.from_dataframe(df_conf_show)
                    gb_conf.configure_selection('multiple', use_checkbox=True, header_checkbox=True, header_checkbox_filtered_only=True)
                    gb_conf.configure_default_column(resizable=True, filterable=True, sortable=True)
                            
                    if "DATA" in df_conf_show.columns: gb_conf.configure_column("DATA", header_name="📅 Coleta", width=110)
                    if "PEDIDO" in df_conf_show.columns: gb_conf.configure_column("PEDIDO", header_name="📦 Pedido", width=120)
                    if "TOMADOR" in df_conf_show.columns: gb_conf.configure_column("TOMADOR", header_name="🏢 Hub Destino", width=160)
                    if "LABORATORIO" in df_conf_show.columns: gb_conf.configure_column("LABORATORIO", header_name="🏭 Laboratório", width=250)
                    if "CIDADE" in df_conf_show.columns: gb_conf.configure_column("CIDADE", header_name="📍 Cidade", width=150)
                    if "BAIRRO" in df_conf_show.columns: gb_conf.configure_column("BAIRRO", header_name="🏘️ Bairro", width=170)
                    if "UF" in df_conf_show.columns: gb_conf.configure_column("UF", header_name="🗺️ UF", width=90)
                    if "MOTORISTA" in df_conf_show.columns: gb_conf.configure_column("MOTORISTA", header_name="👤 Motorista", width=150)
                    if "DATA_BIP" in df_conf_show.columns: gb_conf.configure_column("DATA_BIP", header_name="📅 Data Bip", width=110)
                    if "HORA_BIP" in df_conf_show.columns: gb_conf.configure_column("HORA_BIP", header_name="⏱️ Hora Bip", width=100)

                    st.markdown("<p style='font-size: 13px; color: #64748b; margin-bottom: 5px;'>Selecione os pacotes na tabela para formar o lote do motorista.</p>", unsafe_allow_html=True)
                    grid_conf = AgGrid(
                        df_conf_show, 
                        gridOptions=gb_conf.build(), 
                        theme="alpine", 
                        columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS, 
                        height=350,
                        custom_css=custom_css_premium, 
                        key="grid_triagem_conf")

                    sel_conf_raw = grid_conf.get('selected_rows', [])
                    if isinstance(sel_conf_raw, pd.DataFrame):
                        df_sel_conf = sel_conf_raw
                    elif isinstance(sel_conf_raw, list) and len(sel_conf_raw) > 0:
                        df_sel_conf = pd.DataFrame(sel_conf_raw)
                    else:
                        df_sel_conf = pd.DataFrame(columns=df_conf_show.columns)

                    # Ação de reversão logo abaixo da tabela, sem empurrar para o fim da página
                    if not df_sel_conf.empty:
                        qtd_sel_rev = len(df_sel_conf)
                        st.caption(f"{qtd_sel_rev} volume(s) selecionado(s) para ação reversa.")
                        if st.button(f"↩️ Reverter Selecionados para Triagem ({qtd_sel_rev} vol.) — Desfaz Bipagem", use_container_width=True, type="secondary"):
                            p_ids_reverter = df_sel_conf['PEDIDO'].astype(str).tolist()
                            with st.spinner("Revertendo bipagem e devolvendo para Aba 1..."):
                                try:
                                    aba = planilha_db.worksheet("Memoria_Sistema")
                                    dados_nuvem = aba.get_all_values()
                                    df_nuvem = pd.DataFrame(dados_nuvem[1:], columns=dados_nuvem[0])
                                    for pid in p_ids_reverter:
                                        mask = df_nuvem['PEDIDO'] == pid
                                        df_nuvem.loc[mask, 'STATUS'] = 'COLETADO'
                                        if 'DATA_BIP' in df_nuvem.columns:
                                            df_nuvem.loc[mask, 'DATA_BIP'] = ''
                                        if 'HORA_BIP' in df_nuvem.columns:
                                            df_nuvem.loc[mask, 'HORA_BIP'] = ''
                                        if 'ROMANEIO' in df_nuvem.columns:
                                            df_nuvem.loc[mask, 'ROMANEIO'] = ''
                                    aba.update("A1", [df_nuvem.columns.tolist()] + df_nuvem.fillna("").astype(str).values.tolist())
                                    st.session_state.ui_toast = {'msg': f"{len(p_ids_reverter)} volume(s) revertidos para Aba 1 (Triagem)!", 'icon': "↩️"}
                                    carregar_dados_completos.clear()
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro ao reverter: {e}")

                    st.markdown("---")
                    st.markdown("#### 🚚 Controle de Despacho e Embarque")
                    c_mot, c_data, c_btn = st.columns([2, 1, 2], vertical_alignment="bottom")
                    motorista_escolhido = c_mot.selectbox("👤 Atribuir Motorista:", ["Selecione..."] + (sorted(DF_AGENTES['LOGIN DO AGENTE'].unique().tolist()) if not DF_AGENTES.empty else []))
                    data_despacho = c_data.date_input("📅 Data de Embarque:", format="DD/MM/YYYY", value=hoje_br)


                    qtd_selecionados = len(df_sel_conf)

                    if c_btn.button(f"🚀 Selar Lote e Despachar ({qtd_selecionados} volumes)", type="primary", use_container_width=True):
                        if df_sel_conf.empty or motorista_escolhido == "Selecione...":
                            st.toast("Selecione os pacotes na tabela e informe o motorista.", icon="⚠️")
                        else:
                            p_ids_sel = df_sel_conf['PEDIDO'].astype(str).tolist()
                            sel_lista_full = df_conf[df_conf['PEDIDO'].isin(p_ids_sel)].to_dict('records')
                                    
                            tomadores_unicos = list(set([str(r.get('TOMADOR', '')).strip() for r in sel_lista_full]))
                            if len(tomadores_unicos) > 1:
                                st.error("🚨 VIOLAÇÃO DE ROTA: Você selecionou pacotes com Destinos (Hubs) diferentes. O sistema impede a mistura de cargas.")
                            else:
                                with st.spinner("Selando romaneio e gerando documentação..."):
                                    id_romaneio = f"ROM-{datetime.now().strftime('%d%m')}-{random.randint(100, 999)}"
                                    try:
                                        aba = planilha_db.worksheet("Memoria_Sistema")
                                        dados_nuvem = aba.get_all_values()
                                        if len(dados_nuvem) > 1:
                                            df_nuvem = pd.DataFrame(dados_nuvem[1:], columns=dados_nuvem[0])
                                            df_nuvem.loc[df_nuvem['PEDIDO'].isin(p_ids_sel), ['STATUS', 'ROMANEIO', 'AGENTE_RAW']] = ['EM ROTA DE ENTREGA', id_romaneio, motorista_escolhido]
                                            aba.update("A1", [df_nuvem.columns.tolist()] + df_nuvem.fillna("").astype(str).values.tolist())
                                                
                                        despachar_para_appsheet([{
                                            'PEDIDO': id_romaneio, 'MOTORISTA': motorista_escolhido,
                                            'ENDERECO': "Lote Hub", 'NUMERO': f"{len(p_ids_sel)} V",
                                            'BAIRRO': tomadores_unicos[0], 'CIDADE': sel_lista_full[0].get('CIDADE', ''),
                                            'CEP': "---", 'LABORATORIO': f"Lote {len(sel_lista_full)}",
                                            'TOMADOR': tomadores_unicos[0], 'ROMANEIO': id_romaneio
                                        }])
                                                
                                        pdf_bytes = gerar_pdf_romaneio(id_romaneio, data_despacho, motorista_escolhido, sel_lista_full)
                                                
                                        carregar_dados_completos.clear()
                                        st.session_state.romaneio_pdf = pdf_bytes
                                        st.session_state.romaneio_id = id_romaneio
                                        st.session_state.romaneio_sucesso = True
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Erro ao selar romaneio: {e}")
                else:
                    exibir_empty_state("🚛", "Nada para Despachar", "Todos os volumes do galpão já foram despachados ou não há itens conferidos na fila.")

    # =========================================================================
    # ABA 3: VOLUMES DESPACHADOS
    # =========================================================================
    with t3:
        if df_raw.empty:
            exibir_empty_state("📭", "Banco Vazio", "Aguardando geração de dados.")
        else:
            df_hist = df_raw[df_raw['STATUS'].astype(str).str.upper().isin(['CONFERIDO', 'EM ROTA DE ENTREGA', 'ENTREGUE', 'FRUSTRADA', 'PROBLEMA', 'CANCELADO'])].copy()
                    
            # --- NORMALIZAÇÃO DE DADOS ---
            if 'TOMADOR' in df_hist.columns:
                df_hist['TOMADOR'] = df_hist['TOMADOR'].replace({'CAEP': 'SYNVIA', 'CUNHA': 'GRALAB'})
            if 'CIDADE' in df_hist.columns:
                df_hist['CIDADE'] = df_hist['CIDADE'].replace({'Brodosqui': 'Brodowski'})
            # -----------------------------
                    
            if not df_hist.empty:
                renderizar_kpis([
                    (df_hist['ROMANEIO'].nunique(), "📄 Romaneios Emitidos", "#1E293B", "#334155"),
                    (len(df_hist), "📦 Volumes Processados", "#059669", "#10B981")
                ])

                with st.expander("🖨️ Reimpressão de Romaneios Específicos", expanded=False):
                    st.markdown("<p style='font-size: 14px; color: #475569;'>Filtre para encontrar o romaneio desejado:</p>", unsafe_allow_html=True)
                            
                    # 1. Filtros de Pesquisa
                    col_f1, col_f2 = st.columns(2)
                    with col_f1:
                        data_filtro = st.date_input("🗓️ Data da Coleta:", value=[], format="DD/MM/YYYY")
                    with col_f2:
                        lista_tomadores = ["TODOS"] + sorted([str(x) for x in df_hist['TOMADOR'].dropna().unique() if str(x).strip() != ''])
                        tomador_filtro = st.selectbox("🏢 Hub (Tomador):", lista_tomadores)

                    # 2. Aplicação dos Filtros
                    df_filtrado = df_hist.copy()

                    if len(data_filtro) == 2: # Período
                        dt_inicio, dt_fim = data_filtro
                        if 'DATA' in df_filtrado.columns:
                            df_filtrado['DATA_OBJ'] = pd.to_datetime(df_filtrado['DATA'], format='%d/%m/%Y', errors='coerce').dt.date
                            df_filtrado = df_filtrado[(df_filtrado['DATA_OBJ'] >= dt_inicio) & (df_filtrado['DATA_OBJ'] <= dt_fim)]
                    elif len(data_filtro) == 1: # Data Única
                        dt_unica = data_filtro[0]
                        if 'DATA' in df_filtrado.columns:
                            df_filtrado['DATA_OBJ'] = pd.to_datetime(df_filtrado['DATA'], format='%d/%m/%Y', errors='coerce').dt.date
                            df_filtrado = df_filtrado[df_filtrado['DATA_OBJ'] == dt_unica]

                    if tomador_filtro != "TODOS":
                        df_filtrado = df_filtrado[df_filtrado['TOMADOR'] == tomador_filtro]

                    romaneios_disponiveis = [r for r in df_filtrado['ROMANEIO'].unique() if str(r).strip() and str(r).upper() != 'NAN']

                    # 3. Construção do Menu Inteligente e Botão de Download
                    if romaneios_disponiveis:
                        opcoes_romaneio = ["Selecione..."]
                        mapa_romaneio_id = {}
                                
                        for rom in sorted(romaneios_disponiveis, reverse=True):
                            detalhes = df_filtrado[df_filtrado['ROMANEIO'] == rom].iloc[0]
                                    
                            # Função interna para limpar textos nulos, "None" ou "nan"
                            def limpar_texto_none(val):
                                v_str = str(val).strip()
                                if v_str.lower() in ['none', 'nan', '', 'nat', '<na>']:
                                    return '---'
                                return v_str

                            r_data = limpar_texto_none(detalhes.get('DATA'))
                            r_tomador = limpar_texto_none(detalhes.get('TOMADOR'))
                            r_agente = limpar_texto_none(detalhes.get('AGENTE_RAW'))
                                    
                            texto_exibicao = f"🔖 {rom}  |  📅 {r_data}  |  🏢 {r_tomador}  |  👤 {r_agente}"
                            opcoes_romaneio.append(texto_exibicao)
                            mapa_romaneio_id[texto_exibicao] = rom
                                    
                        st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
                        col_re_1, col_re_2 = st.columns([2, 1])
                        rom_sel_texto = col_re_1.selectbox("Selecione o Lote (Romaneio):", opcoes_romaneio)
                                
                        if rom_sel_texto != "Selecione...":
                            rom_sel_id = mapa_romaneio_id[rom_sel_texto]
                            df_rom = df_hist[df_hist['ROMANEIO'] == rom_sel_id].copy()
                                    
                            pdf_reprint = gerar_pdf_romaneio(rom_sel_id, hoje_br, df_rom.iloc[0].get('AGENTE_RAW', '---'), df_rom.to_dict('records'))
                                    
                            col_re_2.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                            col_re_2.download_button("📥 REIMPRIMIR PDF", pdf_reprint, file_name=f"Reprint_{rom_sel_id}.pdf", mime="application/pdf", type="primary", use_container_width=True)
                    else:
                        st.info("Nenhum romaneio encontrado com os filtros selecionados.")

                # 4. Trilha de Auditoria (com busca por pedido e timestamps de bipagem)
                st.markdown("#### 📜 Trilha de Auditoria (Volumes Despachados)")

                col_busca_hist, col_info_hist = st.columns([2, 1], vertical_alignment="bottom")
                busca_hist_pedido = col_busca_hist.text_input(
                    "🔍 Buscar Pedido na Trilha:",
                    placeholder="Digite o número do pedido...",
                    key="busca_hist_pedido_t3"
                )

                df_hist_audit = df_hist.copy()
                if busca_hist_pedido.strip():
                    mask_hist = df_hist_audit['PEDIDO'].astype(str).str.contains(busca_hist_pedido.strip(), case=False, na=False)
                    df_hist_audit = df_hist_audit[mask_hist]
                    if df_hist_audit.empty:
                        st.warning(f"⚠️ Nenhum pedido encontrado com '{busca_hist_pedido}'.")
                    else:
                        col_info_hist.info(f"✅ {len(df_hist_audit)} pedido(s) localizado(s).")
                        
                colunas_validas_hist = [c for c in ['DATA', 'PEDIDO', 'TOMADOR', 'LABORATORIO', 'CIDADE', 'STATUS', 'AGENTE_RAW', 'ROMANEIO', 'DATA_BIP', 'HORA_BIP'] if c in df_hist_audit.columns]
                df_hist_show = df_hist_audit[colunas_validas_hist].copy()
                        
                if 'DATA' in df_hist_show.columns and 'PEDIDO' in df_hist_show.columns:
                    ordem_sort = ['DATA']
                    if 'HORA_BIP' in df_hist_show.columns:
                        ordem_sort.append('HORA_BIP')
                    ordem_sort.append('PEDIDO')
                    df_hist_show = df_hist_show.sort_values(by=ordem_sort, ascending=[False] * len(ordem_sort))
                        
                gb_hist = GridOptionsBuilder.from_dataframe(df_hist_show)
                gb_hist.configure_default_column(resizable=True, filterable=True, sortable=True)
                        
                if "DATA" in df_hist_show.columns: gb_hist.configure_column("DATA", header_name="📅 Coleta", width=110)
                if "PEDIDO" in df_hist_show.columns: gb_hist.configure_column("PEDIDO", header_name="📦 Pedido", width=120)
                if "TOMADOR" in df_hist_show.columns: gb_hist.configure_column("TOMADOR", header_name="🏢 Hub", width=140)
                if "LABORATORIO" in df_hist_show.columns: gb_hist.configure_column("LABORATORIO", header_name="🏭 Laboratório", width=200)
                if "CIDADE" in df_hist_show.columns: gb_hist.configure_column("CIDADE", header_name="📍 Cidade", width=150)
                if "STATUS" in df_hist_show.columns: gb_hist.configure_column("STATUS", header_name="🚦 Status", cellRenderer=status_jscode_tri, width=150)
                if "AGENTE_RAW" in df_hist_show.columns: gb_hist.configure_column("AGENTE_RAW", header_name="👤 Agente", width=120)
                if "ROMANEIO" in df_hist_show.columns: gb_hist.configure_column("ROMANEIO", header_name="🔖 Romaneio", width=130)
                if "DATA_BIP" in df_hist_show.columns: gb_hist.configure_column("DATA_BIP", header_name="📅 Data Bip", width=110)
                if "HORA_BIP" in df_hist_show.columns: gb_hist.configure_column("HORA_BIP", header_name="⏱️ Hora Bip", width=100)

                AgGrid(
                    df_hist_show, 
                    gridOptions=gb_hist.build(), 
                    theme="alpine", 
                    columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS, 
                    height=450, 
                    allow_unsafe_jscode=True, 
                    custom_css=custom_css_premium,
                    key="grid_historico_triagem")
            else:
                exibir_empty_state("📭", "Sem Histórico", "Nenhum histórico de varredura ou romaneio gerado.")

    # =========================================================================
    # ABA 4: TRIAGEM MANUAL (ENVELOPES AVULSOS)
    # =========================================================================
    with t4:
        st.markdown("#### 📝 Triagem Manual de Contingência (Envelopes)")
        st.info("Utilize esta aba para bipar envelopes e amostras que **não** estão cadastradas no sistema digital, gerando um protocolo isolado de recebimento no Hub.")

        with st.container(border=True):
            c1, c2 = st.columns([2, 1])
            av_tomador = c1.selectbox("🏢 Hub de Destino:", ["Selecione..."] + CLIENTES_ATUALIZADOS, key="av_hub_man")
            av_data = c2.date_input("📅 Data da Triagem:", value=hoje_br, format="DD/MM/YYYY", key="av_dt_man")

        if not st.session_state.pdf_avulso_pronto:
            st.markdown("---")
            with st.form("form_bip_avulso_manual", clear_on_submit=True):
                col_bip, col_pedido, col_cliente = st.columns([2.2, 1.2, 2.6], vertical_alignment="bottom")
                bip_envelope = col_bip.text_input("🔍 Bipar Código ou Digitar Número do Envelope:")
                bip_pedido = col_pedido.text_input("🧾 Número do Pedido (opcional):", placeholder="Se houver")
                bip_cliente = col_cliente.text_input("👤 Nome do Cliente (opcional):", placeholder="Se houver")

                if st.form_submit_button("➕ Adicionar", use_container_width=True):
                    if bip_envelope.strip():
                        novo_item_manual = {
                            'ENVELOPE': bip_envelope.strip(),
                            'PEDIDO': bip_pedido.strip(),
                            'CLIENTE': bip_cliente.strip(),
                            'DATA': av_data.strftime("%d/%m/%Y"),
                            'HORA': datetime.now(FUSO_BR).strftime('%H:%M:%S'),
                            'TOMADOR': av_tomador if av_tomador != "Selecione..." else ""
                        }
                        st.session_state.triagem_avulsa_lote.append(novo_item_manual)
                        st.session_state.ui_toast = {'msg': f"Envelope {bip_envelope.strip()} adicionado!", 'icon': "✅"}
                        st.rerun()

            if st.session_state.triagem_avulsa_lote:
                st.markdown(f"### 📦 Envelopes na Cesta: **{len(st.session_state.triagem_avulsa_lote)}**")

                tem_campos_opcionais = any(
                    str(item.get('PEDIDO', '')).strip() or str(item.get('CLIENTE', '')).strip()
                    for item in st.session_state.triagem_avulsa_lote
                )
                        
                with st.container(border=True):
                    df_av_disp = pd.DataFrame(st.session_state.triagem_avulsa_lote)
                    col_list1, col_list2 = st.columns([2, 1])
                            
                    with col_list1:
                        colunas_disp = ['ENVELOPE', 'DATA', 'HORA']
                        if tem_campos_opcionais:
                            colunas_disp = ['PEDIDO', 'CLIENTE'] + colunas_disp
                        gb_av = GridOptionsBuilder.from_dataframe(df_av_disp[colunas_disp])
                        gb_av.configure_default_column(resizable=True)
                        if tem_campos_opcionais:
                            gb_av.configure_column("PEDIDO", header_name="🧾 Nº Pedido")
                            gb_av.configure_column("CLIENTE", header_name="👤 Cliente")
                        gb_av.configure_column("ENVELOPE", header_name="✉️ Nº Envelope")
                        gb_av.configure_column("DATA", header_name="📅 Data")
                        gb_av.configure_column("HORA", header_name="⏱️ Hora")
                                
                        AgGrid(
                            df_av_disp[colunas_disp], 
                            gridOptions=gb_av.build(), 
                            theme="alpine", 
                            height=250,
                            custom_css=custom_css_premium)

                    with col_list2:
                        renderizar_kpis([(len(st.session_state.triagem_avulsa_lote), "Total Escaneado", "#1E293B", "#334155")])
                        c_ctrl1, c_ctrl2 = st.columns(2)
                        if c_ctrl1.button("↩️ Desfazer", use_container_width=True):
                            if st.session_state.triagem_avulsa_lote:
                                removido = st.session_state.triagem_avulsa_lote.pop()
                                st.session_state.ui_toast = {'msg': f"Removido: {removido['ENVELOPE']}", 'icon': "⚠️"}
                                st.rerun()
                        if c_ctrl2.button("🗑️ Limpar", use_container_width=True):
                            st.session_state.triagem_avulsa_lote.clear()
                            st.session_state.ui_toast = {'msg': "Cesta esvaziada", 'icon': "🗑️"}
                            st.rerun()

                if st.button("📄 SELAR E GERAR PROTOCOLO MANUAL", type="primary", use_container_width=True):
                    if av_tomador == "Selecione...":
                        st.toast("Preencha o Hub de Destino no cabeçalho antes de gerar o PDF!", icon="⚠️")
                    else:
                        with st.spinner("Registrando e desenhando PDF..."):
                            id_rom_av = f"MAN-{datetime.now().strftime('%d%m%H%M')}"
                            plan_av = obter_planilha_avulsos()
                            if plan_av:
                                try:
                                    aba_av = plan_av.sheet1
                                    linhas_bkp = [[id_rom_av, i['DATA'], "TRIAGEM MANUAL", i.get('TOMADOR', ''), "", "", i['ENVELOPE'], i['HORA'], i.get('PEDIDO', ''), i.get('CLIENTE', '')] for i in st.session_state.triagem_avulsa_lote]
                                    aba_av.append_rows(linhas_bkp, value_input_option='USER_ENTERED')
                                except BaseException:
                                    st.warning("⚠️ Não foi possível salvar o histórico na nuvem neste momento, mas o PDF será gerado.")

                            pdf_manual = gerar_pdf_triagem_manual(id_rom_av, av_data, av_tomador, st.session_state.triagem_avulsa_lote)
                            st.session_state.pdf_avulso_pronto = pdf_manual
                            st.session_state.id_avulso_pronto = id_rom_av
                            st.session_state.triagem_avulsa_lote = []
                            st.rerun()
            else:
                exibir_empty_state("🔍", "Cesta de Bipagem Vazia", "Aponte o scanner de código de barras ou digite o número do envelope acima para começar.")

        # TELA DE SUCESSO DO PROTOCOLO MANUAL
        if st.session_state.pdf_avulso_pronto:
            st.success(f"✅ Protocolo Manual {st.session_state.id_avulso_pronto} pronto para impressão!")
            c_m1, c_m2 = st.columns(2)
            c_m1.download_button(
                "📥 BAIXAR PROTOCOLO",
                st.session_state.pdf_avulso_pronto,
                file_name=f"Triagem_Manual_{st.session_state.id_avulso_pronto}.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True)
            if c_m2.button("🔄 Nova Triagem de Envelopes", use_container_width=True):
                st.session_state.pdf_avulso_pronto = None
                st.rerun()

        st.markdown("---")
        with st.expander("🗄️ Histórico de Lotes Manuais (Cofre)", expanded=False):
            plan_av = obter_planilha_avulsos()
            if plan_av:
                try:
                    aba_av = plan_av.sheet1
                    dados_av = aba_av.get_all_values()
                    if len(dados_av) > 1:
                        lotes_man_dict = {}
                        for linha in dados_av[1:]:
                            if "MAN-" in str(linha[0]):
                                lote_num = linha[0]
                                data_val = linha[1] if len(linha) > 1 else ""
                                tomador_val = linha[3] if len(linha) > 3 else ""
                                chave = f"{lote_num} - {data_val} - {tomador_val}" if data_val and tomador_val else lote_num
                                if chave not in lotes_man_dict:
                                    lotes_man_dict[chave] = lote_num

                        c_h1, c_h2 = st.columns([2, 1], vertical_alignment="bottom")
                        lote_re = c_h1.selectbox("Reimprimir Lote Manual:", ["Selecione..."] + sorted(lotes_man_dict.keys(), reverse=True))

                        if lote_re != "Selecione...":
                            lote_re_id = lotes_man_dict[lote_re]
                            linhas_re = [linha for linha in dados_av[1:] if linha[0] == lote_re_id]
                            lista_re = []
                            for ln in linhas_re:
                                env_val = ln[6] if len(ln) > 6 else ""
                                hora_val = ln[7] if len(ln) > 7 else ""
                                data_val = ln[1] if len(ln) > 1 else ""
                                tomador_val = ln[3] if len(ln) > 3 else ""
                                pedido_val = ln[8] if len(ln) > 8 else ""
                                cliente_val = ln[9] if len(ln) > 9 else ""
                                lista_re.append({'ENVELOPE': env_val, 'DATA': data_val, 'HORA': hora_val, 'TOMADOR': tomador_val, 'PEDIDO': pedido_val, 'CLIENTE': cliente_val})

                            pdf_rep_man = gerar_pdf_triagem_manual(lote_re_id, lista_re[0].get('DATA', ''), lista_re[0].get('TOMADOR', ''), lista_re)
                            c_h2.download_button("📥 REIMPRIMIR", pdf_rep_man, file_name=f"Reprint_{lote_re_id}.pdf", mime="application/pdf", type="primary", use_container_width=True)
                except Exception as e:
                    st.warning("⚠️ Não foi possível carregar o histórico no momento.")
# =============================================================================
# 🏷️ MÓDULO: GERADOR DE ETIQUETAS (ESTÚDIO PREMIUM & AGGRID)
# =============================================================================
elif menu == "🏷️ Gerador de Etiquetas":
    st.markdown("<div class='dinamic-border'><h3 class='dinamic-text' style='margin:0;'>🏷️ Estúdio de Etiquetas Térmicas</h3></div>", unsafe_allow_html=True)
    st.markdown("<p style='color: #64748B; font-size: 14px;'>Geração e rastreabilidade de rolos em papel contínuo com design em tempo real.</p>", unsafe_allow_html=True)
            
    st.markdown("<br>", unsafe_allow_html=True)
            
    # --- SISTEMA DE MEMÓRIA NA NUVEM PARA AS CONFIGURAÇÕES ---
    def fetch_configs_etiquetas():
        if planilha_db:
            try:
                aba = planilha_db.worksheet("Config_Etiquetas")
                dados = aba.get_all_values()
                if len(dados) > 1:
                    return {d[0]: float(d[1]) for d in dados[1:]}
            except:
                pass
        return {}
                
    if 'etiquetas_config' not in st.session_state:
        st.session_state.etiquetas_config = fetch_configs_etiquetas()

    conf = st.session_state.etiquetas_config
            
    # Funções de trava de segurança para sliders (impede crash)
    def get_c(k, df, mn, mx): return min(max(float(conf.get(k, df)), float(mn)), float(mx))
    def get_ci(k, df, mn, mx): return min(max(int(conf.get(k, df)), int(mn)), int(mx))

    col_form, col_preview = st.columns([1.2, 1], gap="large")
            
    with col_form:
        tab_setup, tab_design = st.tabs(["⚙️ Setup & Calibragem", "🎮 Estúdio Tetris (X/Y)"])
                
        with tab_setup:
            if not DF_AGENTES.empty:
                lista_agentes = sorted(DF_AGENTES['NOME DO AGENTE'].unique().tolist())
                agente_selecionado = st.selectbox("👤 Agente/Prestador (Região):", ["GERAL/SEM AGENTE"] + lista_agentes)
            else:
                agente_selecionado = "GERAL/SEM AGENTE"
                st.selectbox("👤 Agente/Prestador:", ["GERAL/SEM AGENTE"], disabled=True)
                    
            sigla_inteligente = gerar_sigla_regiao(agente_selecionado, DF_AGENTES)
            st.caption(f"📍 **Tarja Calculada:** `{sigla_inteligente}`")
                    
            qtd_etiquetas = st.number_input("📦 Quantidade Total do Rolo:", min_value=2, max_value=5000, value=100, step=2)
                    
            st.markdown("##### 📏 Calibragem da Impressora")
            st.info("As bordas do papel. Se sair cortada ou sobrando espaço branco na direita, mexa aqui.")
                    
            c_med1, c_med2 = st.columns(2)
            larg_pagina = c_med1.number_input("Largura TOTAL Papel (mm):", value=get_c('larg_pagina', 103.0, 50, 200), step=0.5)
            alt_pagina = c_med2.number_input("Altura do Papel (mm):", value=get_c('alt_pagina', 31.0, 10, 100), step=0.5)
                    
            c_med3, c_med4, c_med5, c_med6 = st.columns(4)
            larg_etiq = c_med3.number_input("Larg. Etiqueta:", value=get_c('larg_etiq', 48.5, 10, 100), step=0.5)
            alt_etiq = c_med4.number_input("Alt. Etiqueta:", value=get_c('alt_etiq', 28.0, 10, 100), step=0.5)
            margem_esq = c_med5.number_input("Margem Esq.:", value=get_c('margem_esq', 2.0, -10, 50), step=0.1)
            gap_central = c_med6.number_input("Espaço Meio:", value=get_c('gap_central', 2.0, -10, 50), step=0.1)
                    
        with tab_design:
            st.markdown("<p style='font-size: 13px; color: #64748b;'>Movimente os blocos como peças de montar. Eixo X = Lados. Eixo Y = Cima/Baixo.</p>", unsafe_allow_html=True)
                    
            with st.expander("⬛ Tarja Preta e Texto", expanded=True):
                usar_sigla_manual = st.toggle(
                    "✍️ Editar texto da tarja manualmente",
                    value=bool(st.session_state.get('usar_sigla_manual_tarja', False)),
                    key="usar_sigla_manual_tarja",
                    help="Ative para sobrescrever a sigla automática da rota (ex.: ANC -> VIX)."
                )
                st.text_input(
                    "Texto da Tarja (manual)",
                    value=st.session_state.get('sigla_manual_tarja', sigla_inteligente),
                    key="sigla_manual_tarja",
                    max_chars=8,
                    disabled=not usar_sigla_manual,
                    help="Use letras/números curtos. Exemplo: VIX"
                )

                sigla_manual_normalizada = re.sub(
                    r'[^A-Z0-9]',
                    '',
                    str(st.session_state.get('sigla_manual_tarja', '')).upper()
                )[:8]
                if usar_sigla_manual and not sigla_manual_normalizada:
                    st.warning("Digite ao menos 1 letra/número para usar a sigla manual. Mantendo automática.")
                sigla_tarja_final = sigla_manual_normalizada if (usar_sigla_manual and sigla_manual_normalizada) else sigla_inteligente
                st.caption(f"🏷️ **Tarja em uso:** `{sigla_tarja_final}`")

                st.divider()
                c_tj1, c_tj2 = st.columns(2)
                largura_tarja = c_tj1.slider("Largura Tarja", 50, 300, get_ci('largura_tarja', 110, 50, 300), 5)
                altura_tarja = c_tj2.slider("Altura Tarja", 100, 500, get_ci('altura_tarja', 350, 100, 500), 5)
                        
                c_tj3, c_tj4 = st.columns(2)
                off_x_tarja = c_tj3.slider("Mover Tarja (X)", -50, 150, get_ci('off_x_tarja', 0, -50, 150), 2)
                off_y_tarja = c_tj4.slider("Mover Tarja (Y)", -100, 100, get_ci('off_y_tarja', -10, -100, 100), 2)
                        
                st.divider()
                c_tx1, c_tx2 = st.columns(2)
                tam_fonte = c_tx1.slider("Tamanho da Fonte", 30, 120, get_ci('tam_fonte', 75, 30, 120), 1)
                off_x_txt = c_tx2.slider("Mover Texto (X)", -50, 50, get_ci('off_x_txt', 0, -50, 50), 2)
                off_y_txt = st.slider("Mover Texto (Y)", -150, 150, get_ci('off_y_txt', 0, -150, 150), 2)

            with st.expander("🔳 Ajustes do QR Code"):
                tam_qr = st.slider("Tamanho do QR", min_value=100, max_value=350, value=get_ci('tam_qr', 290, 100, 350), step=5)
                c_qr1, c_qr2 = st.columns(2)
                off_x_qr = c_qr1.slider("Eixo X (Lados)", -150, 150, get_ci('off_x_qr', 0, -150, 150), 2)
                off_y_qr = c_qr2.slider("Eixo Y (Cima/Baixo)", -150, 150, get_ci('off_y_qr', 0, -150, 150), 2)

            with st.expander("🏢 Logotipo"):
                mostrar_logo = st.toggle("Exibir Logotipo IGO", value=bool(conf.get('mostrar_logo', 1)))
                tam_logo = st.slider("Tamanho Logo", 50, 250, get_ci('tam_logo', 120, 50, 250), 5)
                c_lg1, c_lg2 = st.columns(2)
                off_x_logo = c_lg1.slider("Mover Logo (X)", -150, 150, get_ci('off_x_logo', 0, -150, 150), 2)
                off_y_logo = c_lg2.slider("Mover Logo (Y)", -150, 150, get_ci('off_y_logo', 0, -150, 150), 2)

        # Atualização inteligente de UUIDs
        if 'lote_atual_uuid' not in st.session_state or st.session_state.get('lote_qtd_atual') != qtd_etiquetas:
            st.session_state.lote_atual_uuid = [gerar_codigo_unico_etiqueta() for _ in range(qtd_etiquetas)]
            st.session_state.lote_qtd_atual = qtd_etiquetas

        st.markdown("<br>", unsafe_allow_html=True)

        # --- BOTÃO SALVAR DEFAULT ---
        if st.button("💾 Salvar Configuração Como Padrão (Nuvem)", use_container_width=True):
            nova_conf = {
                'larg_pagina': larg_pagina, 'alt_pagina': alt_pagina, 'larg_etiq': larg_etiq, 'alt_etiq': alt_etiq,
                'margem_esq': margem_esq, 'gap_central': gap_central, 'tam_qr': tam_qr, 'off_x_qr': off_x_qr, 'off_y_qr': off_y_qr,
                'largura_tarja': largura_tarja, 'altura_tarja': altura_tarja, 'off_x_tarja': off_x_tarja, 'off_y_tarja': off_y_tarja,
                'tam_fonte': tam_fonte, 'off_x_txt': off_x_txt, 'off_y_txt': off_y_txt,
                'mostrar_logo': 1 if mostrar_logo else 0, 'tam_logo': tam_logo, 'off_x_logo': off_x_logo, 'off_y_logo': off_y_logo
            }
            st.session_state.etiquetas_config = nova_conf
            try:
                try: aba = planilha_db.worksheet("Config_Etiquetas")
                except: aba = planilha_db.add_worksheet("Config_Etiquetas", 50, 2)
                linhas = [["CHAVE", "VALOR"]] + [[k, str(v)] for k, v in nova_conf.items()]
                aba.clear()
                aba.update("A1", linhas)
                st.toast("✅ Setup salvo na nuvem com sucesso!", icon="💾")
            except Exception as e:
                st.error(f"Erro ao salvar na nuvem: {e}")
                
        # --- TRAVA DE MEMÓRIA DO PDF ---
        if 'pdf_etiquetas_cache' not in st.session_state:
            st.session_state.pdf_etiquetas_cache = None
            st.session_state.pdf_etiquetas_nome = ""

        c_btn1, c_btn2 = st.columns(2)
                
        if c_btn1.button("⚙️ PROCESSAR E RENDERIZAR LOTE", use_container_width=True): 
            with st.spinner("Processando layout vetorial..."):
                st.session_state.pdf_etiquetas_cache = gerar_pdf_rolo_duplo_premium(
                    st.session_state.lote_atual_uuid, sigla_tarja_final, larg_pagina, alt_pagina, larg_etiq, alt_etiq,
                    margem_esq, gap_central, tam_qr, tam_fonte, mostrar_logo, largura_tarja, altura_tarja, tam_logo,
                    off_x_tarja, off_y_tarja, off_x_txt, off_y_txt, off_x_qr, off_y_qr, off_x_logo, off_y_logo
                )
                st.session_state.pdf_etiquetas_nome = f"Lote_{qtd_etiquetas}x_{sigla_tarja_final}_{datetime.now().strftime('%H%M%S')}.pdf"
                st.rerun()

        if st.session_state.pdf_etiquetas_cache is not None:
            c_btn2.download_button(
                label="📥 BAIXAR (.PDF) AGORA",
                data=st.session_state.pdf_etiquetas_cache,
                file_name=st.session_state.pdf_etiquetas_nome,
                mime="application/pdf",
                use_container_width=True,
                type="primary"
            )

    with col_preview:
        st.markdown("#### 👀 Preview em Tempo Real")
        img_preview_path = criar_imagem_etiqueta_pil(
            "IGO-PREV12", sigla_tarja_final, tam_qr, tam_fonte, mostrar_logo,
            largura_tarja, altura_tarja, tam_logo, off_x_tarja, off_y_tarja,
            off_x_txt, off_y_txt, off_x_qr, off_y_qr, off_x_logo, off_y_logo
        )
        with st.container(border=True):
            st.image(img_preview_path, caption=f"Saída Física de cada Etiqueta: {larg_etiq} x {alt_etiq} mm", use_container_width=True)

    # ---------------------------------------------------------
    # LAYOUT INFERIOR: DATA GRID (AGGRID)
    # ---------------------------------------------------------
    st.markdown("---")
    col_grid_title, col_btn_renovar = st.columns([3, 1], vertical_alignment="bottom")
    col_grid_title.markdown("### 📊 Rastreabilidade do Lote")
    col_grid_title.markdown("<p style='color: #64748B; font-size: 13px;'>Estes são os códigos exclusivos que compõem o lote atual.</p>", unsafe_allow_html=True)
            
    if col_btn_renovar.button("🔄 Sortear Novos Códigos", use_container_width=True):
        st.session_state.lote_atual_uuid = [gerar_codigo_unico_etiqueta() for _ in range(qtd_etiquetas)]
        st.session_state.lote_qtd_atual = qtd_etiquetas
        st.session_state.agente_lote_atual = agente_selecionado
        st.session_state.pdf_etiquetas_cache = None 
        st.rerun()

    if ('lote_atual_uuid' not in st.session_state or 
        st.session_state.get('lote_qtd_atual') != qtd_etiquetas or 
        st.session_state.get('agente_lote_atual') != agente_selecionado):
        st.session_state.lote_atual_uuid = [gerar_codigo_unico_etiqueta() for _ in range(qtd_etiquetas)]
        st.session_state.lote_qtd_atual = qtd_etiquetas
        st.session_state.agente_lote_atual = agente_selecionado

    df_lote = pd.DataFrame({
        "Nº": range(1, qtd_etiquetas + 1),
        "CÓDIGO (UUID)": st.session_state.lote_atual_uuid,
        "TARJA REGIONAL": [sigla_tarja_final] * qtd_etiquetas,
        "STATUS": ["A IMPRIMIR 🖨️"] * qtd_etiquetas
    })

    custom_css_etiquetas = {
        ".ag-theme-alpine": {"--ag-font-family": "Inter, sans-serif", "--ag-font-size": "13px", "background-color": "#ffffff !important", "border": "1px solid #e2e8f0"},
        ".ag-header": {"background-color": "#f1f5f9 !important", "border-bottom": "2px solid #e2e8f0 !important"},
        ".ag-header-cell-text": {"color": "#0f172a !important", "font-weight": "700 !important", "font-size": "13px !important"}
    }

    gb_lote = GridOptionsBuilder.from_dataframe(df_lote)
    gb_lote.configure_default_column(resizable=True, filterable=True, sortable=True)
    gb_lote.configure_column("Nº", width=80)
    gb_lote.configure_column("CÓDIGO (UUID)", width=150, cellStyle={'fontWeight': 'bold', 'color': '#0F172A'})
    gb_lote.configure_column("TARJA REGIONAL", width=130)
            
    AgGrid(
        df_lote,
        gridOptions=gb_lote.build(),
        theme="alpine",
        height=300,
        custom_css=custom_css_etiquetas,
        columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS,
        key="grid_lote_etiquetas"
    )
# =============================================================================
# 📁 MÓDULO 4: EXPORTAR RELATÓRIOS (NOVO E INTELIGENTE)
# =============================================================================

elif menu == "📁 Relatórios":

    st.markdown(
        "<div class='dinamic-border'><h3 class='dinamic-text' style='margin:0;'>📥 Central de Datamining e Exportação</h3></div>",
        unsafe_allow_html=True)
    df_raw = carregar_dados_completos(planilha_db)

    if not df_raw.empty:
        def get_detalhes_rel(row):
            obs = str(row.get('A_OB', row.get('OBSERVACOES', ''))).strip()
            if obs and obs.upper() != 'NAN':
                return obs
            return "-"
        df_raw['DETALHES'] = df_raw.apply(get_detalhes_rel, axis=1)

        # 🔥 1. FILTRO INTELIGENTE DE DATAS 🔥
        st.markdown("#### 📅 1. Selecione o Período Base")
        col_data = st.columns([1, 2])[0]
        periodo_rel = col_data.date_input(
            "Filtro de Datas para os Relatórios:",
            value=(
                hoje_br -
                timedelta(
                    days=7),
                hoje_br),
            format="DD/MM/YYYY")

        df_filtered = df_raw.copy()
        if isinstance(periodo_rel, (tuple, list)) and len(periodo_rel) == 2:
            df_filtered = df_filtered[(df_filtered['DATA_OBJ'] >= periodo_rel[0]) & (
                df_filtered['DATA_OBJ'] <= periodo_rel[1])]

        st.markdown("---")
        st.markdown(
            "#### 📊 2. Extrações Rápidas (Baseado no período selecionado)")

        df_export_base = df_filtered[['DATA',
                                    'PEDIDO',
                                    'TOMADOR',
                                    'LABORATORIO',
                                    'ENDERECO',
                                    'NUMERO',
                                    'BAIRRO',
                                    'CIDADE',
                                    'UF',
                                    'CEP',
                                    'STATUS',
                                    'DETALHES',
                                    'DATA_ENTREGA',
                                    'AGENTE_RAW',
                                    'DATA_LIMITE']].copy()
        df_export_base = df_export_base.rename(
            columns={'AGENTE_RAW': 'MOTORISTA'})
        col_rel1, col_rel2, col_rel3 = st.columns(3)

        df_rj = df_export_base[df_export_base['UF'].str.upper(
        ) == 'RJ'] if 'UF' in df_export_base.columns else pd.DataFrame()
        df_jf = df_export_base[df_export_base['CIDADE'].str.upper().str.contains(
            'JUIZ DE FORA', na=False)] if 'CIDADE' in df_export_base.columns else pd.DataFrame()
        df_rjjf = pd.concat([df_rj, df_jf]).drop_duplicates(subset=['PEDIDO'])
        if not df_rjjf.empty:
            col_rel1.download_button(
                f"📥 Extrair Bloco RJ/JF ({len(df_rjjf)} col.)",
                data=gerar_excel_memoria(df_rjjf),
                file_name=f"RJ_JF_{datetime.now(FUSO_BR).strftime('%d%m%Y')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True)
        else:
            col_rel1.button(
                "📥 Extrair Bloco RJ/JF (Vazio)",
                disabled=True,
                use_container_width=True)

        df_lud = df_export_base[df_export_base['MOTORISTA'].str.lower().str.contains(
            'ludmila|veloz', na=False)] if 'MOTORISTA' in df_export_base.columns else pd.DataFrame()
        if not df_lud.empty:
            col_rel2.download_button(
                f"📥 Extrair Ludmila/Veloz ({len(df_lud)} col.)",
                data=gerar_excel_memoria(df_lud),
                file_name=f"Ludmila_{datetime.now(FUSO_BR).strftime('%d%m%Y')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True)
        else:
            col_rel2.button(
                "📥 Extrair Ludmila/Veloz (Vazio)",
                disabled=True,
                use_container_width=True)

        df_full_bkp = df_raw[['DATA',
                            'PEDIDO',
                            'TOMADOR',
                            'LABORATORIO',
                            'ENDERECO',
                            'NUMERO',
                            'BAIRRO',
                            'CIDADE',
                            'UF',
                            'CEP',
                            'STATUS',
                            'DETALHES',
                            'DATA_ENTREGA',
                            'AGENTE_RAW',
                            'DATA_LIMITE']].copy()
        df_full_bkp = df_full_bkp.rename(columns={'AGENTE_RAW': 'MOTORISTA'})
        col_rel3.download_button(
            "☁️ Backup Completo (Toda a Nuvem)",
            data=gerar_excel_memoria(df_full_bkp),
            file_name=f"BKP_COMPLETO_{datetime.now(FUSO_BR).strftime('%d%m%Y')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True)

        st.markdown("---")
        st.markdown("#### 🔎 3. Pesquisa Customizada (No período selecionado)")
        with st.form("form_rel_custom"):
            cf1, cf2 = st.columns(2)
            c_ag = cf1.text_input("👤 Codinome do Agente:")
            c_cid = cf2.text_input("🏙️ Raio de Busca (Cidade):")
            c_uf = cf1.text_input("🗺️ Vetor Estadual (UF):")
            c_base = cf2.text_input("🏢 Hub Logístico (Tomador/Clínica):")

            if st.form_submit_button("Executar Pesquisa e Compilar Tabela"):
                df_custom = df_export_base.copy()
                if c_ag and 'MOTORISTA' in df_custom.columns:
                    df_custom = df_custom[df_custom['MOTORISTA'].str.upper(
                    ).str.contains(c_ag.upper(), na=False)]
                if c_cid and 'CIDADE' in df_custom.columns:
                    df_custom = df_custom[df_custom['CIDADE'].str.upper(
                    ).str.contains(c_cid.upper(), na=False)]
                if c_uf and 'UF' in df_custom.columns:
                    df_custom = df_custom[df_custom['UF'].str.upper(
                    ) == c_uf.upper()]
                if c_base:
                    df_custom = df_custom[df_custom['TOMADOR'].str.upper().str.contains(c_base.upper(
                    ), na=False) | df_custom['LABORATORIO'].str.upper().str.contains(c_base.upper(), na=False)]

                if not df_custom.empty:
                    st.success(f"✅ Encontrados {len(df_custom)} registros.")
                    st.download_button(
                        "📥 Fazer Download do Relatório Cru (Excel)",
                        data=gerar_excel_memoria(df_custom),
                        file_name=f"Pesquisa_Customizada_IGO.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        type="primary")
                else:
                    st.warning(
                        "Nenhum dado encontrado para os filtros e período selecionados.")

        st.markdown("---")
        st.markdown("#### 🧠 4. Relatório Executivo Premium (Base Importação Web)")
        st.caption("Visão analítica com filtros, indicadores, gráficos e exportação consolidada usando a própria base da Importação Web.")

        import plotly.express as px
        import plotly.graph_objects as go

        df_exec = df_filtered.copy()
        if 'AGENTE_RAW' in df_exec.columns and 'MOTORISTA' not in df_exec.columns:
            df_exec['MOTORISTA'] = df_exec['AGENTE_RAW']
        if 'STATUS_DISPLAY' not in df_exec.columns:
            df_exec['STATUS_DISPLAY'] = df_exec.apply(calc_status_display, axis=1)

        if 'DATA' in df_exec.columns:
            df_exec['DATA_TS_EXEC'] = pd.to_datetime(df_exec['DATA'], dayfirst=True, errors='coerce')
        else:
            df_exec['DATA_TS_EXEC'] = pd.to_datetime(df_exec.get('DATA_OBJ'), errors='coerce')

        with st.expander("⚙️ Filtros Avançados do Relatório Executivo", expanded=False):
            f1, f2, f3, f4 = st.columns(4)
            op_uf = sorted(df_exec['UF'].dropna().astype(str).str.upper().unique().tolist()) if 'UF' in df_exec.columns else []
            op_cid = sorted(df_exec['CIDADE'].dropna().astype(str).str.upper().unique().tolist()) if 'CIDADE' in df_exec.columns else []
            op_tom = sorted(df_exec['TOMADOR'].dropna().astype(str).str.upper().unique().tolist()) if 'TOMADOR' in df_exec.columns else []
            op_mot = sorted(df_exec['MOTORISTA'].dropna().astype(str).str.upper().unique().tolist()) if 'MOTORISTA' in df_exec.columns else []

            filtro_uf = f1.multiselect("UF", options=op_uf)
            filtro_cid = f2.multiselect("Cidade", options=op_cid)
            filtro_tom = f3.multiselect("Tomador", options=op_tom)
            filtro_mot = f4.multiselect("Motorista", options=op_mot)

        if filtro_uf and 'UF' in df_exec.columns:
            df_exec = df_exec[df_exec['UF'].astype(str).str.upper().isin(filtro_uf)]
        if filtro_cid and 'CIDADE' in df_exec.columns:
            df_exec = df_exec[df_exec['CIDADE'].astype(str).str.upper().isin(filtro_cid)]
        if filtro_tom and 'TOMADOR' in df_exec.columns:
            df_exec = df_exec[df_exec['TOMADOR'].astype(str).str.upper().isin(filtro_tom)]
        if filtro_mot and 'MOTORISTA' in df_exec.columns:
            df_exec = df_exec[df_exec['MOTORISTA'].astype(str).str.upper().isin(filtro_mot)]

        if df_exec.empty:
            st.warning("Nenhum registro encontrado no relatório executivo com os filtros aplicados.")
        else:
            mask_entregues = df_exec['STATUS_DISPLAY'].astype(str).str.contains('Entregue|Coletado|Conferido', case=False, na=False)
            mask_pendentes = df_exec['STATUS_DISPLAY'].astype(str).str.contains('Pendente|Rota', case=False, na=False)
            mask_falhas = df_exec['STATUS_DISPLAY'].astype(str).str.contains('Frustrada|Problema|Cancelado', case=False, na=False)
            mask_atrasados = df_exec['STATUS_DISPLAY'].astype(str).str.contains('ATRASADO', case=False, na=False)

            vol_total_exec = len(df_exec)
            entregues_exec = int(mask_entregues.sum())
            pendentes_exec = int(mask_pendentes.sum())
            falhas_exec = int(mask_falhas.sum())
            atrasados_exec = int(mask_atrasados.sum())
            taxa_exec = (entregues_exec / vol_total_exec * 100) if vol_total_exec else 0

            k1, k2, k3, k4, k5, k6 = st.columns(6)
            k1.metric("Volumes", f"{vol_total_exec}")
            k2.metric("Entregues/Coletados", f"{entregues_exec}")
            k3.metric("Pendentes", f"{pendentes_exec}")
            k4.metric("Falhas", f"{falhas_exec}")
            k5.metric("Atrasados", f"{atrasados_exec}")
            k6.metric("Taxa Sucesso", f"{taxa_exec:.1f}%")

            df_diario = df_exec.dropna(subset=['DATA_TS_EXEC']).groupby(df_exec['DATA_TS_EXEC'].dt.date).size().reset_index(name='VOLUMES')
            df_diario.rename(columns={'DATA_TS_EXEC': 'DATA'}, inplace=True)

            df_status = df_exec.groupby('STATUS_DISPLAY').size().reset_index(name='QTD').sort_values('QTD', ascending=False)
            df_cidades = df_exec.groupby('CIDADE').size().reset_index(name='VOLUMES').sort_values('VOLUMES', ascending=False).head(15) if 'CIDADE' in df_exec.columns else pd.DataFrame()
            df_tomadores = df_exec.groupby('TOMADOR').size().reset_index(name='VOLUMES').sort_values('VOLUMES', ascending=False).head(15) if 'TOMADOR' in df_exec.columns else pd.DataFrame()

            df_mensal = df_exec.dropna(subset=['DATA_TS_EXEC']).copy()
            if not df_mensal.empty:
                df_mensal['MES_REF'] = df_mensal['DATA_TS_EXEC'].dt.to_period('M').dt.to_timestamp()
                df_mensal = df_mensal.groupby('MES_REF').size().reset_index(name='VOLUMES').sort_values('MES_REF')
                df_mensal['MES'] = df_mensal['MES_REF'].dt.strftime('%m/%Y')

            col_g1, col_g2 = st.columns(2)
            with col_g1:
                if not df_diario.empty:
                    fig_diario = px.line(df_diario, x='DATA', y='VOLUMES', markers=True, title='Evolução Diária de Volumes')
                    fig_diario.update_layout(height=320, margin=dict(l=8, r=8, t=45, b=8))
                    st.plotly_chart(fig_diario, use_container_width=True)
            with col_g2:
                if not df_status.empty:
                    fig_status = px.pie(df_status, names='STATUS_DISPLAY', values='QTD', hole=0.5, title='Distribuição por Status')
                    fig_status.update_layout(height=320, margin=dict(l=8, r=8, t=45, b=8))
                    st.plotly_chart(fig_status, use_container_width=True)

            col_g3, col_g4 = st.columns(2)
            with col_g3:
                if not df_cidades.empty:
                    fig_cid = px.bar(df_cidades.sort_values('VOLUMES'), x='VOLUMES', y='CIDADE', orientation='h', title='Top Cidades por Volume')
                    fig_cid.update_layout(height=420, margin=dict(l=8, r=8, t=45, b=8))
                    st.plotly_chart(fig_cid, use_container_width=True)
            with col_g4:
                if not df_tomadores.empty:
                    fig_tom = px.bar(df_tomadores.sort_values('VOLUMES'), x='VOLUMES', y='TOMADOR', orientation='h', title='Top Tomadores por Volume')
                    fig_tom.update_layout(height=420, margin=dict(l=8, r=8, t=45, b=8))
                    st.plotly_chart(fig_tom, use_container_width=True)

            if 'df_mensal' in locals() and not df_mensal.empty:
                fig_mes = px.bar(
                    df_mensal,
                    x='MES',
                    y='VOLUMES',
                    text='VOLUMES',
                    title='Pedidos Mês a Mês'
                )
                fig_mes.update_traces(textposition='outside', marker_color='#1f77b4')
                fig_mes.update_layout(
                    height=360,
                    margin=dict(l=8, r=8, t=45, b=8),
                    xaxis_title='Mês',
                    yaxis_title='Pedidos',
                    uniformtext_minsize=8,
                    uniformtext_mode='hide'
                )
                st.plotly_chart(fig_mes, use_container_width=True)

            st.markdown("##### 🧭 Matriz Cidade x Tomador")
            if 'CIDADE' in df_exec.columns and 'TOMADOR' in df_exec.columns:
                top_cid = df_exec['CIDADE'].value_counts().head(12).index
                top_tom = df_exec['TOMADOR'].value_counts().head(10).index
                df_matrix = pd.crosstab(df_exec['CIDADE'], df_exec['TOMADOR'])
                df_matrix = df_matrix.reindex(index=top_cid, columns=top_tom, fill_value=0)
                st.dataframe(df_matrix, use_container_width=True)
            else:
                df_matrix = pd.DataFrame()
                st.info("Não foi possível montar a matriz (colunas CIDADE/TOMADOR ausentes).")

            st.markdown("##### 🚨 Inatividade Geográfica")
            if 'CIDADE' in df_exec.columns:
                data_ref = periodo_rel[1] if isinstance(periodo_rel, (tuple, list)) and len(periodo_rel) == 2 else hoje_br
                df_inatividade = df_exec.dropna(subset=['DATA_TS_EXEC']).groupby('CIDADE')['DATA_TS_EXEC'].max().reset_index()
                df_inatividade['ULTIMO_MOVIMENTO'] = df_inatividade['DATA_TS_EXEC'].dt.date
                df_inatividade['DIAS_INATIVO'] = df_inatividade['ULTIMO_MOVIMENTO'].apply(lambda d: (data_ref - d).days if pd.notna(d) else 999)
                df_inatividade = df_inatividade[['CIDADE', 'ULTIMO_MOVIMENTO', 'DIAS_INATIVO']].sort_values('DIAS_INATIVO', ascending=False)
                st.dataframe(df_inatividade.head(50), use_container_width=True)
            else:
                df_inatividade = pd.DataFrame()

            def gerar_relatorio_executivo_importacao_web():
                output = io.BytesIO()
                kpi_df = pd.DataFrame([
                    {'INDICADOR': 'Volumes', 'VALOR': vol_total_exec},
                    {'INDICADOR': 'Entregues/Coletados', 'VALOR': entregues_exec},
                    {'INDICADOR': 'Pendentes', 'VALOR': pendentes_exec},
                    {'INDICADOR': 'Falhas', 'VALOR': falhas_exec},
                    {'INDICADOR': 'Atrasados', 'VALOR': atrasados_exec},
                    {'INDICADOR': 'Taxa de Sucesso (%)', 'VALOR': round(taxa_exec, 2)},
                ])

                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_exec.to_excel(writer, sheet_name='Base_Filtrada', index=False)
                    kpi_df.to_excel(writer, sheet_name='KPIs', index=False)
                    df_status.to_excel(writer, sheet_name='Status', index=False)
                    if not df_cidades.empty:
                        df_cidades.to_excel(writer, sheet_name='Top_Cidades', index=False)
                    if not df_tomadores.empty:
                        df_tomadores.to_excel(writer, sheet_name='Top_Tomadores', index=False)
                    if not df_diario.empty:
                        df_diario.to_excel(writer, sheet_name='Evolucao_Diaria', index=False)
                    if 'df_mensal' in locals() and not df_mensal.empty:
                        df_mensal.to_excel(writer, sheet_name='Evolucao_Mensal', index=False)
                    if not df_matrix.empty:
                        df_matrix.reset_index().to_excel(writer, sheet_name='Matriz_Cid_Tom', index=False)
                    if not df_inatividade.empty:
                        df_inatividade.to_excel(writer, sheet_name='Inatividade', index=False)
                return output.getvalue()

            def gerar_relatorio_executivo_html_importacao_web():
                periodo_ini = periodo_rel[0].strftime('%d/%m/%Y') if isinstance(periodo_rel, (tuple, list)) and len(periodo_rel) == 2 else hoje_br.strftime('%d/%m/%Y')
                periodo_fim = periodo_rel[1].strftime('%d/%m/%Y') if isinstance(periodo_rel, (tuple, list)) and len(periodo_rel) == 2 else hoje_br.strftime('%d/%m/%Y')

                media_dia_exec = (vol_total_exec / max(1, len(df_diario))) if not df_diario.empty else float(vol_total_exec)
                ticket_exec = 0.0

                # Embute a logo no HTML para funcionar mesmo offline/sem bloqueio externo.
                logo_src = "https://i.postimg.cc/x84nnjjq/IGO-LOGO.png"
                try:
                    logo_path = os.path.join(tempfile.gettempdir(), "igo_logo_html_cache.png")
                    if not os.path.exists(logo_path) or os.path.getsize(logo_path) == 0:
                        req_logo = urllib.request.Request(logo_src, headers={'User-Agent': 'Mozilla/5.0'})
                        with urllib.request.urlopen(req_logo, timeout=8) as response, open(logo_path, 'wb') as out_file:
                            out_file.write(response.read())

                    with open(logo_path, 'rb') as f_logo:
                        logo_b64 = base64.b64encode(f_logo.read()).decode('ascii')
                        logo_src = f"data:image/png;base64,{logo_b64}"
                except Exception:
                    pass

                html_evol = fig_diario.to_html(full_html=False, include_plotlyjs='cdn') if 'fig_diario' in locals() else "<div style='padding:20px;'>Sem dados de evolução.</div>"
                html_status = fig_status.to_html(full_html=False, include_plotlyjs=False) if 'fig_status' in locals() else "<div style='padding:20px;'>Sem dados de status.</div>"
                html_cidades = fig_cid.to_html(full_html=False, include_plotlyjs=False) if 'fig_cid' in locals() else "<div style='padding:20px;'>Sem dados de cidades.</div>"
                html_tom = fig_tom.to_html(full_html=False, include_plotlyjs=False) if 'fig_tom' in locals() else "<div style='padding:20px;'>Sem dados de tomadores.</div>"
                html_mes = fig_mes.to_html(full_html=False, include_plotlyjs=False) if 'fig_mes' in locals() else "<div style='padding:20px;'>Sem dados mensais.</div>"

                df_top_tom_html = df_tomadores.copy() if not df_tomadores.empty else pd.DataFrame(columns=['TOMADOR', 'VOLUMES'])
                df_top_tom_html['MOM'] = 0.0

                matriz_vol = pd.DataFrame()
                matriz_fin = pd.DataFrame()
                if not df_exec.dropna(subset=['DATA_TS_EXEC']).empty and 'CIDADE' in df_exec.columns:
                    df_aux_m = df_exec.dropna(subset=['DATA_TS_EXEC']).copy()
                    df_aux_m['MES_NUM'] = df_aux_m['DATA_TS_EXEC'].dt.month
                    matriz_vol = df_aux_m.groupby(['CIDADE', 'MES_NUM']).size().unstack(fill_value=0).reindex(columns=range(1, 13), fill_value=0).reset_index()
                    matriz_vol['VOL'] = matriz_vol[[m for m in range(1, 13)]].sum(axis=1)
                    matriz_vol['MED_DIA'] = (matriz_vol['VOL'] / max(1, len(df_diario))).round(1)
                    matriz_vol['TKT'] = 0.0
                    matriz_vol = matriz_vol.sort_values('VOL', ascending=False).head(40)

                    matriz_fin = matriz_vol[['CIDADE'] + [m for m in range(1, 13)] + ['VOL']].copy()
                    matriz_fin.rename(columns={'VOL': 'FAT'}, inplace=True)

                tabela_status_html = df_status.to_html(index=False, classes='') if not df_status.empty else "<p>Sem dados.</p>"
                tabela_matrix_html = df_matrix.reset_index().to_html(index=False, classes='') if not df_matrix.empty else "<p>Sem dados.</p>"
                tabela_inat_html = df_inatividade.to_html(index=False, classes='') if not df_inatividade.empty else "<p>Sem dados.</p>"
                tabela_tom_html = df_top_tom_html.to_html(index=False, classes='') if not df_top_tom_html.empty else "<p>Sem dados.</p>"
                tabela_matriz_vol_html = matriz_vol.to_html(index=False, classes='') if not matriz_vol.empty else "<p>Sem dados.</p>"
                tabela_matriz_fin_html = matriz_fin.to_html(index=False, classes='') if not matriz_fin.empty else "<p>Sem dados.</p>"

                html_template = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard Operacional IGO</title>
    <style>
body {
    font-family: 'Montserrat', 'Segoe UI', sans-serif;
    background-color: #f4f7fa;
    color: #0b1426;
    margin: 0;
    padding: 30px;
}
.container {
    max-width: 1200px;
    margin: 0 auto;
    background: #ffffff;
    padding: 34px;
    border-radius: 12px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.05);
}
.header {
    display: flex;
    align-items: end;
    justify-content: space-between;
    border-bottom: 3px solid #C5A059;
    padding-bottom: 16px;
    margin-bottom: 26px;
}
.header-brand {
    display: flex;
    align-items: center;
    gap: 12px;
}
.logo-igo {
    height: 52px;
    width: auto;
    object-fit: contain;
}
.header-title h1 {
    color: #0b1426;
    margin: 0 0 5px 0;
    font-size: 24px;
    text-transform: uppercase;
    letter-spacing: 0.4px;
}
.header-title p {
    color: #7f8c8d;
    margin: 0;
    font-size: 13px;
    font-weight: 600;
}
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: 12px;
    margin-bottom: 28px;
}
.kpi-card {
    background: linear-gradient(135deg, #0b1426, #16294d);
    border-radius: 8px;
    padding: 14px;
    color: white;
    text-align: center;
    box-shadow: 0 4px 15px rgba(11, 20, 38, 0.2);
    border-bottom: 4px solid #C5A059;
}
.kpi-card h3 { margin: 0 0 8px 0; font-size: 10px; font-weight: 600; color: #d0d7e6; text-transform: uppercase; }
.kpi-card h2 { margin: 0; font-size: 20px; color: #C5A059; font-weight: 800; }
.chart-container { display: flex; gap: 16px; margin-bottom: 10px; }
.chart-box {
    background: #fff;
    border-radius: 8px;
    border: 1px solid #e1e8ed;
    padding: 12px;
    flex: 1;
    box-shadow: 0 2px 10px rgba(0,0,0,0.03);
    text-align: center;
    overflow: hidden;
}
.chart-box.full { width: 100%; flex: unset; }
.section-title {
    font-size: 15px;
    font-weight: 800;
    color: #5b9bd5;
    margin-bottom: 14px;
    margin-top: 28px;
    text-transform: uppercase;
    border-left: 4px solid #C5A059;
    padding-left: 10px;
}
table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 24px;
    font-size: 11px;
    background: #fff;
}
th {
    background-color: #0b1426;
    color: #fff;
    font-weight: 600;
    padding: 9px;
    text-align: center;
    border: 1px solid #16294d;
}
td { padding: 7px 9px; border: 1px solid #e1e8ed; text-align: center; color: #2c3e50; }
tr:nth-child(even) { background-color: #f8f9fa; }
.page-break { page-break-before: always; margin-top: 20px; }
@media print {
    body { background-color: #fff; padding: 0; }
    .container { box-shadow: none; padding: 0; max-width: 100%; }
    @page { margin: 1cm; size: A4 landscape; }
}
@media (max-width: 1100px) {
    .kpi-grid { grid-template-columns: repeat(2, 1fr); }
    .chart-container { flex-direction: column; }
}
    </style>
</head>
<body>
    <div class="container">
<div class="header">
    <div class="header-brand">
        <img class="logo-igo" src="__LOGO_SRC__" alt="Logo IGO">
        <div class="header-title">
            <h1>Dashboard Operacional IGO</h1>
            <p>Operação Global | __PERIODO__</p>
        </div>
    </div>
    <div class="header-title">
        <p>Gerado em __GERADO__</p>
    </div>
</div>

<div class="kpi-grid">
    <div class="kpi-card"><h3>Volume Total</h3><h2>__VOL__</h2></div>
    <div class="kpi-card"><h3>Média / Dia</h3><h2>__MEDIA__</h2></div>
    <div class="kpi-card"><h3>Ticket Médio</h3><h2>R$ __TKT__</h2></div>
    <div class="kpi-card"><h3>Entregues</h3><h2>__ENT__</h2></div>
    <div class="kpi-card"><h3>Pendentes</h3><h2>__PEND__</h2></div>
    <div class="kpi-card"><h3>Taxa Sucesso</h3><h2>__TAXA__</h2></div>
</div>

<div class="chart-container">
    <div class="chart-box">__CHART_EVOL__</div>
    <div class="chart-box">__CHART_STATUS__</div>
</div>

<div class="section-title">Análise Geográfica e Representatividade</div>
<div class="chart-container">
    <div class="chart-box">__CHART_CIDADES__</div>
    <div class="chart-box">__CHART_TOMADORES__</div>
</div>

<div class="chart-box full">__CHART_MES__</div>

<div class="page-break"></div>

<div class="section-title">Resumo por Status</div>
__TABELA_STATUS__

<div class="section-title">Matriz Cidade x Tomador</div>
__TABELA_MATRIZ__

<div class="section-title">Análise de Performance por Tomador (Cliente)</div>
__TABELA_TOM__

<div class="page-break"></div>

<div class="section-title">Matriz de Volumetria Mês a Mês</div>
__TABELA_MATRIZ_VOL__

<div class="section-title">Matriz de Faturamento Mês a Mês (R$)</div>
__TABELA_MATRIZ_FIN__

<div class="section-title">Alerta Executivo: Inatividade Geográfica</div>
__TABELA_INATIVIDADE__
    </div>
</body>
</html>
"""

                html_pronto = (
                    html_template
                    .replace('__PERIODO__', f'{periodo_ini} a {periodo_fim}')
                    .replace('__GERADO__', datetime.now(FUSO_BR).strftime('%d/%m/%Y %H:%M'))
                    .replace('__VOL__', str(vol_total_exec))
                    .replace('__MEDIA__', f'{media_dia_exec:.1f}')
                    .replace('__TKT__', f'{ticket_exec:.2f}'.replace('.', ','))
                    .replace('__ENT__', str(entregues_exec))
                    .replace('__PEND__', str(pendentes_exec))
                    .replace('__TAXA__', f'{taxa_exec:.1f}%')
                    .replace('__LOGO_SRC__', logo_src)
                    .replace('__CHART_EVOL__', html_evol)
                    .replace('__CHART_STATUS__', html_status)
                    .replace('__CHART_CIDADES__', html_cidades)
                    .replace('__CHART_TOMADORES__', html_tom)
                    .replace('__CHART_MES__', html_mes)
                    .replace('__TABELA_STATUS__', tabela_status_html)
                    .replace('__TABELA_MATRIZ__', tabela_matrix_html)
                    .replace('__TABELA_TOM__', tabela_tom_html)
                    .replace('__TABELA_MATRIZ_VOL__', tabela_matriz_vol_html)
                    .replace('__TABELA_MATRIZ_FIN__', tabela_matriz_fin_html)
                    .replace('__TABELA_INATIVIDADE__', tabela_inat_html)
                )
                return html_pronto.encode('utf-8')

            col_down_xls, col_down_html = st.columns(2)
            col_down_xls.download_button(
                "📥 Baixar Relatório Executivo Premium (Excel)",
                data=gerar_relatorio_executivo_importacao_web(),
                file_name=f"Relatorio_Executivo_ImportacaoWeb_{datetime.now(FUSO_BR).strftime('%d%m%Y_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                use_container_width=True)
            col_down_html.download_button(
                "🌐 Baixar Dashboard Premium (HTML)",
                data=gerar_relatorio_executivo_html_importacao_web(),
                file_name=f"Dashboard_Executivo_ImportacaoWeb_{datetime.now(FUSO_BR).strftime('%d%m%Y_%H%M')}.html",
                mime="text/html",
                use_container_width=True)
    else:
        st.warning("O banco de dados está vazio.")

# =============================================================================
# ⚙️ MÓDULO 5: CONFIGURAR ROTAS E AGENTES
# =============================================================================
elif menu == "⚙️ Rotas":
    # Botão de atualizar solto no topo, ao lado do título
    col_tit_rotas, col_btn_atualizar = st.columns([5, 1], vertical_alignment="center")
            
    with col_tit_rotas:
        st.markdown(
            "<div class='dinamic-border'><h3 class='dinamic-text' style='margin:0;'>⚙️ Matriz Inteligente de Rotas e Equipe</h3></div>",
            unsafe_allow_html=True)
                    
    with col_btn_atualizar:
        if st.button("🔄 Atualizar Dados", use_container_width=True):
            with st.spinner("Sincronizando com a nuvem..."):
                carregar_dados_agentes.clear()
                carregar_dados_completos.clear()
                time.sleep(0.5)
                st.rerun()

    st.markdown(
        """
        <style>
        div[data-baseweb="tab-list"] {
            gap: 14px;
            margin-bottom: 16px;
            align-items: stretch;
        }
        div[data-baseweb="tab"] {
            background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%) !important;
            border: 1px solid #dbe3ef !important;
            border-radius: 12px !important;
            color: #334155 !important;
            font-weight: 700 !important;
            min-height: 50px !important;
            padding: 0 18px !important;
            line-height: 1.25 !important;
            letter-spacing: 0.15px !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04) !important;
            transition: all 0.2s ease !important;
        }
        button[role="tab"] {
            padding: 0 18px !important;
            min-height: 50px !important;
            line-height: 1.25 !important;
        }
        button[role="tab"] p {
            margin: 0 !important;
            line-height: 1.25 !important;
            white-space: nowrap !important;
        }
        div[data-baseweb="tab"]:hover {
            border-color: #93c5fd !important;
            color: #0f172a !important;
            transform: translateY(-1px);
            box-shadow: 0 6px 16px rgba(37, 99, 235, 0.10) !important;
        }
        button[role="tab"][aria-selected="true"] {
            background: linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%) !important;
            border-color: #1d4ed8 !important;
            border-radius: 12px !important;
            color: #ffffff !important;
            box-shadow: 0 10px 20px rgba(37, 99, 235, 0.22) !important;
            overflow: hidden !important;
            padding: 0 20px !important;
        }
        button[role="tab"][aria-selected="true"] p {
            letter-spacing: 0.2px !important;
            line-height: 1.3 !important;
        }
        div[data-testid="stForm"],
        div[data-testid="stExpander"],
        div[data-testid="stDataFrame"],
        div[data-testid="stVerticalBlockBorderWrapper"],
        div[data-testid="stAlert"] {
            border-radius: 14px !important;
        }
        div[data-testid="stExpander"] {
            border: 1px solid #dbe3ef !important;
            background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%) !important;
            box-shadow: 0 6px 16px rgba(15, 23, 42, 0.05) !important;
        }
        div[data-testid="stTextArea"] textarea,
        div[data-testid="stTextInput"] input,
        div[data-testid="stDateInput"] input,
        div[data-testid="stDateInput"] button,
        div[data-testid="stSelectbox"] > div[data-baseweb="select"] > div,
        div[data-testid="stMultiSelect"] > div[data-baseweb="select"] > div {
            background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%) !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 10px !important;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05) !important;
        }
        div[data-testid="stTextArea"] textarea:focus,
        div[data-testid="stTextInput"] input:focus,
        div[data-testid="stDateInput"] input:focus {
            border-color: #60a5fa !important;
            box-shadow: 0 0 0 1px #93c5fd !important;
        }
        div[data-testid="stFormSubmitButton"] > button,
        div.stButton > button:not([kind="primary"]),
        div[data-testid="stPopover"] > div > button,
        div[data-testid="stPopover"] > button {
            background: linear-gradient(180deg, #eff6ff 0%, #dbeafe 100%) !important;
            color: #0f172a !important;
            border: 1px solid #93c5fd !important;
            border-radius: 10px !important;
            font-weight: 700 !important;
            box-shadow: 0 4px 10px rgba(37, 99, 235, 0.10) !important;
            min-height: 42px !important;
            transition: all 0.2s ease !important;
        }
        div[data-testid="stFormSubmitButton"] > button:hover,
        div.stButton > button:not([kind="primary"]):hover,
        div[data-testid="stPopover"] > div > button:hover,
        div[data-testid="stPopover"] > button:hover {
            background: linear-gradient(180deg, #dbeafe 0%, #bfdbfe 100%) !important;
            border-color: #60a5fa !important;
            box-shadow: 0 8px 18px rgba(37, 99, 235, 0.18) !important;
            transform: translateY(-1px) !important;
        }
        div.stButton > button[kind="primary"],
        div[data-testid="stFormSubmitButton"] > button[kind="primary"] {
            background: linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%) !important;
            border: 1px solid #1d4ed8 !important;
            color: #ffffff !important;
            box-shadow: 0 10px 20px rgba(37, 99, 235, 0.22) !important;
        }
        div.stButton > button[kind="primary"]:hover,
        div[data-testid="stFormSubmitButton"] > button[kind="primary"]:hover {
            background: linear-gradient(135deg, #0284c7 0%, #1d4ed8 100%) !important;
            border-color: #1e40af !important;
            color: #ffffff !important;
        }
        div[data-testid="stMarkdownContainer"] h4,
        div[data-testid="stMarkdownContainer"] h5 {
            color: #0f172a !important;
            letter-spacing: -0.2px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # 🔄 ABAS REORGANIZADAS: 'Atrelar Rota' removida (agora 100% dentro de Gerenciar Perfil)
    tab_agente, tab_busca, tab_tabela, tab_sistema = st.tabs(
        ["👤 Cadastrar Motorista", "🔎 Explorador", "📋 Gerenciar Perfil e Transferências", "⚠️ Admin"])

    # -------------------------------------------------------------------------
    # CADASTRAR MOTORISTA
    # -------------------------------------------------------------------------
    with tab_agente:
        st.markdown("#### 👤 Registrar Novo Motorista / Agente")
        st.info("💡 **Dica de Logins Compartilhados:** Para usar o mesmo login no app, mas separar o WhatsApp, use o separador `|`. Ex: `igo.log|edgar` e `igo.log|anderson`. O sistema envia a rota para o telefone de cada um, mas o app usa apenas `igo.log`.")
                
        with st.container(border=True):
            with st.form("form_novo_agente", clear_on_submit=True):
                c1, c2, c3 = st.columns([1, 1.5, 1])
                login_ag = c1.text_input("ID de Login no App *", placeholder="Ex: carlos.rj")
                name_ag = c2.text_input("Nome Amigável *", placeholder="Ex: CARLOS SILVA")
                tel_ag = c3.text_input("WhatsApp (com DDD) *", placeholder="Ex: 5521999999999")
                        
                st.markdown("<br>", unsafe_allow_html=True)
                if st.form_submit_button("💾 Adicionar Motorista à Equipe", type="primary", use_container_width=True):
                    if not login_ag or not name_ag or not tel_ag:
                        st.error("⚠️ Preencha todos os campos obrigatórios (*).")
                    else:
                        df_novo = pd.concat([DF_AGENTES,
                                            pd.DataFrame([{"ROTA MAPEADA": "SEM ROTA DEFINIDA",
                                                            "LOGIN DO AGENTE": login_ag.lower().strip(),
                                                            "NOME DO AGENTE": name_ag.upper().strip(),
                                                            "TELEFONE": re.sub(r'\D', '', tel_ag)}])],
                                            ignore_index=True)
                        try:
                            planilha_db.worksheet("Agentes").clear()
                            planilha_db.worksheet("Agentes").update("A1", [df_novo.columns.tolist()] + df_novo.fillna("").astype(str).values.tolist())
                            st.session_state.ui_toast = {'msg': f"Campão! Agente {name_ag.upper()} cadastrado com sucesso!", 'icon': "🧑‍✈️"}
                            carregar_dados_agentes.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao cadastrar: {e}")

    # -------------------------------------------------------------------------
    # EXPLORADOR GEOGRÁFICO
    # -------------------------------------------------------------------------
    with tab_busca:
        st.markdown("#### 🔎 Explorador Geográfico de Rotas")
        st.info("Descubra rapidamente qual motorista é responsável por uma determinada região. Ideal para checar se uma cidade já está coberta pelo sistema.")
                
        with st.container(border=True):
            termo_busca = st.text_input("🌍 Digite o local (Cidade, Bairro ou Rua):", placeholder="Ex: ANGRA DOS REIS")
                    
            if termo_busca:
                mask_busca = DF_AGENTES['ROTA MAPEADA'].str.contains(padronizar_texto(termo_busca), case=False, na=False)
                df_result = DF_AGENTES[mask_busca].copy()

                if not df_result.empty:
                    st.success(f"✅ Encontrado(s) **{len(df_result)} mapeamento(s)** para esta pesquisa.")
                    df_result_show = df_result[['ROTA MAPEADA', 'NOME DO AGENTE', 'LOGIN DO AGENTE', 'TELEFONE']].copy()
                    df_result_show.rename(columns={'ROTA MAPEADA': '📍 Localidade Coberta', 'NOME DO AGENTE': '👤 Motorista', 'LOGIN DO AGENTE': '🔑 Login', 'TELEFONE': '📱 Contato'}, inplace=True)
                    st.dataframe(df_result_show, hide_index=True, use_container_width=True)
                else:
                    st.warning("⚠️ Nenhum motorista atrelado a este local. Mapeie uma nova rota para cobrir essa região.")

    # -------------------------------------------------------------------------
    # 📋 GERENCIAR PERFIL E TRANSFERÊNCIAS (VISUAL PREMIUM E BUSCA INTELIGENTE)
    # -------------------------------------------------------------------------
    with tab_tabela:
        if not DF_AGENTES.empty:
            st.markdown("#### 📋 Gerenciamento de Perfil, Rotas e Transferências")
                    
            # 🔥 Dicionário para mostrar "Nome Amigável (Login)" no Selectbox 🔥
            df_unicos_ag = DF_AGENTES.drop_duplicates('LOGIN DO AGENTE')
            dict_exibicao_ag = {
                row['LOGIN DO AGENTE']: f"{row['NOME DO AGENTE']} ({row['LOGIN DO AGENTE']})"
                for _, row in df_unicos_ag.iterrows()
            }
                    
            col_sel, _ = st.columns([1, 2])
            agente_filtro = col_sel.selectbox(
                "🔎 Selecione o Motorista em Análise:", 
                options=sorted(dict_exibicao_ag.keys()),
                format_func=lambda x: dict_exibicao_ag.get(x, x)
            )
                    
            df_ag_filtrado = DF_AGENTES[DF_AGENTES['LOGIN DO AGENTE'] == agente_filtro].copy()
            dados_atuais_ag = df_ag_filtrado.iloc[0]
            rotas_validas = [r for r in df_ag_filtrado['ROTA MAPEADA'].tolist() if str(r).strip() != "SEM ROTA DEFINIDA"]
            qtd_rotas = len(rotas_validas)
            modo_disparo_atual = obter_modo_disparo_whatsapp(agente_filtro)
            opcoes_modo_disparo = ['NOTIFICACAO', 'PDF', 'XLS', 'PDF_XLS']
            labels_modo_disparo = {item: etiqueta_modo_disparo_whatsapp(item) for item in opcoes_modo_disparo}
            chave_modo_disparo = f"modo_disparo_{agente_filtro}"
            if chave_modo_disparo not in st.session_state:
                st.session_state[chave_modo_disparo] = modo_disparo_atual
                    
            # 🔥 HEADER DO PERFIL (VISUAL APP MODERNO) 🔥
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%); border: 1px solid #e2e8f0; border-radius: 16px; padding: 24px; margin-bottom: 25px; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05);">
                <div style="display: flex; align-items: center; gap: 20px;">
                    <div style="background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%); width: 75px; height: 75px; border-radius: 50%; display: flex; justify-content: center; align-items: center; box-shadow: 0 4px 10px rgba(59, 130, 246, 0.3);">
                        <span style="font-size: 35px; color: white;">🧑‍✈️</span>
                    </div>
                    <div>
                        <div style="font-size: 22px; font-weight: 900; color: #0f172a; margin-bottom: 6px; letter-spacing: -0.5px;">{dados_atuais_ag['NOME DO AGENTE']}</div>
                        <div style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">
                            <span style="background: #eff6ff; color: #1d4ed8; padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 700; border: 1px solid #bfdbfe;">
                                🆔 {agente_filtro}
                            </span>
                            <span style="background: #f0fdf4; color: #15803d; padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 700; border: 1px solid #bbf7d0;">
                                📱 {dados_atuais_ag['TELEFONE']}
                            </span>
                        </div>
                    </div>
                </div>
                <div style="text-align: right; padding-left: 20px; border-left: 2px dashed #e2e8f0;">
                    <div style="font-size: 11px; color: #64748b; font-weight: 800; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px;">Rotas Ativas</div>
                    <div style="font-size: 42px; font-weight: 900; color: #3b82f6; line-height: 1;">{qtd_rotas}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            col_dados, col_rotas = st.columns([5, 7], gap="large")

            # ==========================================
            # LADO ESQUERDO: Edição e Adição de Rota
            # ==========================================
            with col_dados:
                st.markdown("##### ✏️ Editar Informações")
                with st.container(border=True):
                    edit_nome = st.text_input("Nome Amigável", value=dados_atuais_ag['NOME DO AGENTE'])
                    edit_tel = st.text_input("WhatsApp com DDD", value=dados_atuais_ag['TELEFONE'])
                    st.markdown("**Disparo no WhatsApp**")
                    btn_cols = st.columns(4, gap="small")
                    for idx_modo, modo_item in enumerate(opcoes_modo_disparo):
                        is_ativo = st.session_state[chave_modo_disparo] == modo_item
                        if btn_cols[idx_modo].button(
                            labels_modo_disparo.get(modo_item, modo_item),
                            key=f"btn_{chave_modo_disparo}_{modo_item}",
                            use_container_width=True,
                            type="primary" if is_ativo else "secondary"
                        ):
                            st.session_state[chave_modo_disparo] = modo_item
                            st.rerun()
                    st.caption(f"Seleção atual: {labels_modo_disparo.get(st.session_state[chave_modo_disparo], st.session_state[chave_modo_disparo])}")
                    edit_modo_disparo = st.session_state[chave_modo_disparo]
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("💾 Salvar Alterações", type="primary", use_container_width=True):
                        if not edit_nome or not edit_tel:
                            st.error("Preencha todos os campos!")
                        else:
                            df_ag_edit = DF_AGENTES.copy()
                            mask_edit = df_ag_edit['LOGIN DO AGENTE'] == agente_filtro
                            df_ag_edit.loc[mask_edit, 'NOME DO AGENTE'] = edit_nome.upper().strip()
                            df_ag_edit.loc[mask_edit, 'TELEFONE'] = re.sub(r'\D', '', edit_tel)
                            df_ag_edit.loc[mask_edit, 'TIPO_DISPARO_WHATSAPP'] = edit_modo_disparo
                            try:
                                aba_ag = planilha_db.worksheet("Agentes")
                                aba_ag.clear()
                                aba_ag.update("A1", [df_ag_edit.columns.tolist()] + df_ag_edit.fillna("").astype(str).values.tolist())
                                st.session_state.ui_toast = {'msg': "Cadastro atualizado com sucesso!", 'icon': "✅"}
                                carregar_dados_agentes.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao editar: {e}")

                st.markdown("<br>", unsafe_allow_html=True)
                        
                st.markdown("##### 📍 Adicionar Rota Rápida")
                with st.container(border=True):
                    with st.form(f"form_rapido_{agente_filtro}", clear_on_submit=True):
                        r_cid = st.text_input("Cidade *", placeholder="Obrigatório")
                        ca1, ca2 = st.columns(2)
                        r_bai = ca1.text_input("Bairro (Opç)")
                        r_rua = ca2.text_input("Endereço (Opç)")
                                
                        if st.form_submit_button("➕ Adicionar Rota", use_container_width=True):
                            if not r_cid:
                                st.error("A Cidade é obrigatória!")
                            else:
                                rota_str = " ➔ ".join([p for p in [limpar_nome_local_rota(r_cid), limpar_nome_local_rota(r_bai), tratar_texto_global(r_rua)] if p])
                                df_novo = pd.concat([DF_AGENTES,
                                                    pd.DataFrame([{"ROTA MAPEADA": rota_str,
                                                                    "LOGIN DO AGENTE": agente_filtro,
                                                                    "NOME DO AGENTE": dados_atuais_ag['NOME DO AGENTE'],
                                                                    "TELEFONE": dados_atuais_ag['TELEFONE'],
                                                                    "TIPO_DISPARO_WHATSAPP": dados_atuais_ag.get('TIPO_DISPARO_WHATSAPP', modo_disparo_atual)}])],
                                                    ignore_index=True)
                                try:
                                    planilha_db.worksheet("Agentes").clear()
                                    planilha_db.worksheet("Agentes").update("A1", [df_novo.columns.tolist()] + df_novo.fillna("").astype(str).values.tolist())
                                    st.session_state.ui_toast = {'msg': "Rota adicionada!", 'icon': "📍"}
                                    carregar_dados_agentes.clear()
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro ao salvar: {e}")

                st.markdown("<br>", unsafe_allow_html=True)

                st.markdown("##### 🚨 Zona de Risco")
                with st.expander("Excluir Motorista Definitivamente"):
                    st.error("⚠️ **Atenção:** Isso apagará o login e todas as rotas atreladas a ele de forma permanente.")
                    with st.form(f"form_excluir_agente_{agente_filtro}"):
                        senha_excluir_ag = st.text_input("🔑 Senha Master para Exclusão:", type="password")
                        if st.form_submit_button(f"APAGAR '{agente_filtro}'", type="primary", use_container_width=True):
                            if senha_excluir_ag == "123":
                                with st.spinner("Excluindo registro..."):
                                    df_ag_novo = DF_AGENTES[DF_AGENTES['LOGIN DO AGENTE'] != agente_filtro].copy()
                                    try:
                                        aba_ag = planilha_db.worksheet("Agentes")
                                        aba_ag.clear()
                                        if df_ag_novo.empty:
                                            aba_ag.update("A1", [["ROTA MAPEADA", "LOGIN DO AGENTE", "NOME DO AGENTE", "TELEFONE"]])
                                        else:
                                            aba_ag.update("A1", [df_ag_novo.columns.tolist()] + df_ag_novo.fillna("").astype(str).values.tolist())
                                        st.session_state.ui_toast = {'msg': "Motorista apagado com sucesso!", 'icon': "🗑️"}
                                        carregar_dados_agentes.clear()
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Erro ao excluir: {e}")
                            else:
                                st.error("❌ Senha incorreta.")

            # ==========================================
            # LADO DIREITO: GRID DE ROTAS ESTILO "CARDS"
            # ==========================================
            with col_rotas:
                col_t_title, col_t_all = st.columns([3, 2], vertical_alignment="center")
                col_t_title.markdown(f"##### 🗺️ Mapeamento de Rotas")
                        
                # Lista de destino com formato NOME (login) para a transferência
                dict_para = dict_exibicao_ag.copy()
                if agente_filtro in dict_para:
                    del dict_para[agente_filtro] # Remove o agente atual das opções de destino
                        
                # Botão Global: Transferir todas
                if qtd_rotas > 0:
                    with col_t_all.popover("🚀 Transferir Todas", use_container_width=True):
                        st.markdown("**Transferir TODAS as rotas deste perfil para:**")
                        para_todos = st.selectbox(
                            "Selecione o destino:", 
                            options=["Selecione..."] + sorted(dict_para.keys()),
                            format_func=lambda x: dict_para.get(x, x),
                            key="transf_all_sel"
                        )
                        if st.button("Confirmar Envio", key="btn_confirm_all_transf", type="primary", use_container_width=True):
                            if para_todos != "Selecione...":
                                with st.spinner(f"Transferindo tudo para {para_todos}..."):
                                    df_rotas_full = DF_AGENTES.copy()
                                    dados_novo = df_rotas_full[df_rotas_full['LOGIN DO AGENTE'] == para_todos].iloc[0]
                                    dados_agente_original = df_rotas_full[df_rotas_full['LOGIN DO AGENTE'] == agente_filtro].iloc[0]
                                            
                                    # Transferir todas as rotas (exceto "SEM ROTA DEFINIDA")
                                    mask_transfer = (df_rotas_full['LOGIN DO AGENTE'] == agente_filtro) & (df_rotas_full['ROTA MAPEADA'] != "SEM ROTA DEFINIDA")
                                    df_rotas_full.loc[mask_transfer, ['LOGIN DO AGENTE', 'NOME DO AGENTE', 'TELEFONE']] = [para_todos, dados_novo['NOME DO AGENTE'], dados_novo['TELEFONE']]
                                    df_rotas_full = df_rotas_full.drop_duplicates(subset=["ROTA MAPEADA", "LOGIN DO AGENTE"])
                                            
                                    # 🔥 GARANTIA: Mantém o agente original com "SEM ROTA DEFINIDA" para não sumir do cadastro
                                    if not any((df_rotas_full['LOGIN DO AGENTE'] == agente_filtro) & (df_rotas_full['ROTA MAPEADA'] == "SEM ROTA DEFINIDA")):
                                        df_rotas_full = pd.concat([
                                            df_rotas_full,
                                            pd.DataFrame([{
                                                "ROTA MAPEADA": "SEM ROTA DEFINIDA",
                                                "LOGIN DO AGENTE": agente_filtro,
                                                "NOME DO AGENTE": dados_agente_original['NOME DO AGENTE'],
                                                    "TELEFONE": dados_agente_original['TELEFONE'],
                                                    "TIPO_DISPARO_WHATSAPP": dados_agente_original.get('TIPO_DISPARO_WHATSAPP', modo_disparo_atual)
                                            }])
                                        ], ignore_index=True)
                                            
                                    try:
                                        planilha_db.worksheet("Agentes").clear()
                                        planilha_db.worksheet("Agentes").update("A1", [df_rotas_full.columns.tolist()] + df_rotas_full.fillna("").astype(str).values.tolist())
                                        st.session_state.ui_toast = {'msg': f"Rotas migradas para {para_todos}!", 'icon': "🚀"}
                                        carregar_dados_agentes.clear()
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Erro na transferência: {e}")
                        
                if qtd_rotas == 0:
                    st.info("Nenhuma rota cadastrada para este motorista.")
                else:
                    # RESTAURADO o height=650 com a barra de rolagem (Container Scrollável)
                    with st.container(height=650, border=True):
                        for idx_ui, (idx, row) in enumerate(df_ag_filtrado.iterrows()):
                            rota_nome = row['ROTA MAPEADA']
                            if str(rota_nome).strip() == "SEM ROTA DEFINIDA": 
                                continue
                                    
                            col_r, col_transf, col_del = st.columns([11, 2, 2], vertical_alignment="center")
                                    
                            col_r.markdown(
                                f"""<div style='padding: 14px 16px; background: white; border-radius: 10px; border: 1px solid #e2e8f0; border-left: 4px solid #3b82f6; margin-bottom: 2px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); display: flex; align-items: center;'>
                                    <div style='background: #eff6ff; width: 36px; height: 36px; border-radius: 8px; display: flex; justify-content: center; align-items: center; margin-right: 15px; flex-shrink: 0;'>
                                        <span style='font-size: 16px;'>📍</span>
                                    </div>
                                    <div>
                                        <div style='font-size: 10px; color: #64748b; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;'>Destino / Rota</div>
                                        <div style='color: #1e293b; font-size: 14px; font-weight: 800;'>{rota_nome.replace('---', ' ➔ ')}</div>
                                    </div>
                                </div>""", 
                                unsafe_allow_html=True
                            )
                                    
                            # 🔥 A MÁGICA DOS BOTÕES INVISÍVEIS: Usa "Zero-width spaces" (\u200b) para diferenciar IDs sem aparecer texto 🔥
                            lbl_popover = "🔄" + ("\u200b" * idx_ui)
                                    
                            with col_transf.popover(lbl_popover, help="Mover apenas esta rota para outro motorista"):
                                st.markdown(f"**Transferir esta rota para:**")
                                para_motorista = st.selectbox(
                                    "Escolha o destino:", 
                                    options=["Selecione..."] + sorted(dict_para.keys()),
                                    format_func=lambda x: dict_para.get(x, x),
                                    key=f"transf_sel_{idx}"
                                )
                                if st.button("Confirmar", key=f"btn_confirm_transf_{idx}", type="primary", use_container_width=True):
                                    if para_motorista != "Selecione...":
                                        with st.spinner("Movendo rota..."):
                                            df_rotas_full = DF_AGENTES.copy()
                                            dados_novo = df_rotas_full[df_rotas_full['LOGIN DO AGENTE'] == para_motorista].iloc[0]
                                            dados_agente_original = df_rotas_full[df_rotas_full['LOGIN DO AGENTE'] == agente_filtro].iloc[0]
                                                    
                                            # Transferir esta rota específica
                                            mask_transfer = (df_rotas_full['LOGIN DO AGENTE'] == agente_filtro) & (df_rotas_full['ROTA MAPEADA'] == rota_nome)
                                            df_rotas_full.loc[mask_transfer, ['LOGIN DO AGENTE', 'NOME DO AGENTE', 'TELEFONE']] = [para_motorista, dados_novo['NOME DO AGENTE'], dados_novo['TELEFONE']]
                                            df_rotas_full = df_rotas_full.drop_duplicates(subset=["ROTA MAPEADA", "LOGIN DO AGENTE"])
                                                    
                                            # 🔥 GARANTIA: Se o agente ficou sem rotas reais, adiciona "SEM ROTA DEFINIDA"
                                            rotas_reais_agente = df_rotas_full[(df_rotas_full['LOGIN DO AGENTE'] == agente_filtro) & (df_rotas_full['ROTA MAPEADA'] != "SEM ROTA DEFINIDA")]
                                            if rotas_reais_agente.empty and not any((df_rotas_full['LOGIN DO AGENTE'] == agente_filtro) & (df_rotas_full['ROTA MAPEADA'] == "SEM ROTA DEFINIDA")):
                                                df_rotas_full = pd.concat([
                                                    df_rotas_full,
                                                    pd.DataFrame([{
                                                        "ROTA MAPEADA": "SEM ROTA DEFINIDA",
                                                        "LOGIN DO AGENTE": agente_filtro,
                                                        "NOME DO AGENTE": dados_agente_original['NOME DO AGENTE'],
                                                        "TELEFONE": dados_agente_original['TELEFONE'],
                                                        "TIPO_DISPARO_WHATSAPP": dados_agente_original.get('TIPO_DISPARO_WHATSAPP', modo_disparo_atual)
                                                    }])
                                                ], ignore_index=True)
                                                    
                                            try:
                                                planilha_db.worksheet("Agentes").clear()
                                                planilha_db.worksheet("Agentes").update("A1", [df_rotas_full.columns.tolist()] + df_rotas_full.fillna("").astype(str).values.tolist())
                                                carregar_dados_agentes.clear()
                                                time.sleep(0.5)
                                                st.rerun()
                                            except Exception as e:
                                                st.error(f"Erro: {e}")
                                    
                            # ❌ Botão de exclusão
                            if col_del.button("❌", key=f"del_{idx}", help="Excluir esta rota", use_container_width=True):
                                try:
                                    planilha_db.worksheet("Agentes").clear()
                                    planilha_db.worksheet("Agentes").update("A1", [DF_AGENTES.drop(idx).columns.tolist()] + DF_AGENTES.drop(idx).fillna("").astype(str).values.tolist())
                                    st.session_state.ui_toast = {'msg': "Rota excluída!", 'icon': "✂️"}
                                    carregar_dados_agentes.clear()
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro ao remover: {e}")
        else:
            st.warning("Nenhum dado encontrado no banco de agentes.")

    # -------------------------------------------------------------------------
    # ADMIN
    # -------------------------------------------------------------------------
    with tab_sistema:
        st.markdown("#### ⚠️ Administração do Sistema")
        col_sys1, col_sys2 = st.columns(2, gap="large")
                
        with col_sys1:
            with st.container(border=True):
                st.markdown("<h5 style='color: #D97706; margin-bottom: 0px;'>🧹 Faxina de 30 Dias (Arquivo Morto)</h5>", unsafe_allow_html=True)
                st.markdown("<p style='font-size: 13px; color: #64748B;'>Move pedidos finalizados com mais de 30 dias para a aba 'ARQUIVO_MORTO'. O CCO fica rápido e a contagem de IDs originais é preservada.</p>", unsafe_allow_html=True)
                        
                with st.form("form_limpeza_30_dias"):
                    senha_limpeza = st.text_input("🔑 Senha de Autorização (123):", type="password")
                    if st.form_submit_button("🚀 EXECUTAR FAXINA", type="primary", use_container_width=True):
                        if senha_limpeza == "123":
                            with st.spinner("Analisando linha do tempo e arquivando histórico antigo..."):
                                try:
                                    aba_m = planilha_db.worksheet("Memoria_Sistema")
                                    df_m = pd.DataFrame(aba_m.get_all_values()[1:], columns=aba_m.get_all_values()[0])
                                    df_m['DT_TEMP'] = pd.to_datetime(df_m['DATA'], format='%d/%m/%Y', errors='coerce').dt.date
                                    corte = hoje_br - timedelta(days=30)

                                    df_velhos = df_m[df_m['DT_TEMP'] < corte].drop(columns=['DT_TEMP'])
                                    df_novos = df_m[df_m['DT_TEMP'] >= corte].drop(columns=['DT_TEMP'])

                                    if not df_velhos.empty:
                                        try: aba_morto = planilha_db.worksheet("ARQUIVO_MORTO")
                                        except:
                                            aba_morto = planilha_db.add_worksheet("ARQUIVO_MORTO", 100, 20)
                                            aba_morto.update("A1", [df_velhos.columns.tolist()])

                                        aba_morto.append_rows(df_velhos.fillna("").astype(str).values.tolist())
                                        aba_m.clear()
                                        aba_m.update("A1", [df_novos.columns.tolist()] + df_novos.fillna("").astype(str).values.tolist())

                                        pedidos_preservados = df_novos['PEDIDO'].astype(str).tolist()
                                        try:
                                            aba_app = planilha_db.worksheet("App_Tarefas")
                                            df_app = pd.DataFrame(aba_app.get_all_values()[1:], columns=aba_app.get_all_values()[0])
                                            if 'PEDIDO' in df_app.columns:
                                                df_app_novo = df_app[df_app['PEDIDO'].astype(str).isin(pedidos_preservados)]
                                                aba_app.clear()
                                                aba_app.update("A1", [df_app_novo.columns.tolist()] + df_app_novo.fillna("").astype(str).values.tolist())
                                        except: pass
                                        st.success(f"✅ Limpeza concluída! 🗑️ {len(df_velhos)} registros antigos arquivados.")
                                    else:
                                        st.info("👍 A base já está leve! Não foram encontrados pedidos antigos.")
                                            
                                    carregar_dados_completos.clear()
                                    time.sleep(2.5)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro ao realizar a limpeza: {e}")
                        else:
                            if senha_limpeza: st.error("❌ Senha incorreta.")

        with col_sys2:
            with st.container(border=True):
                st.markdown("<h5 style='color: #DC2626; margin-bottom: 0px;'>🚨 Reset Total do Banco</h5>", unsafe_allow_html=True)
                st.markdown("<p style='font-size: 13px; color: #64748B;'>Zera completamente a base de dados (Memoria_Sistema e App_Tarefas), preservando apenas os cabeçalhos. Ação irreversível.</p>", unsafe_allow_html=True)
                        
                with st.form("form_reset_banco"):
                    senha_reset = st.text_input("🔑 Senha Master (123):", type="password")
                    if st.form_submit_button("🗑️ ZERAR TUDO", type="primary", use_container_width=True):
                        if senha_reset == "123":
                            with st.spinner("Limpando banco de dados com segurança..."):
                                try:
                                    aba_m = planilha_db.worksheet("Memoria_Sistema")
                                    cabecalho_m = aba_m.row_values(1)
                                    aba_m.clear()
                                    aba_m.update("A1", [cabecalho_m])
                                    try:
                                        aba_app = planilha_db.worksheet("App_Tarefas")
                                        cabecalho_app = aba_app.row_values(1)
                                        aba_app.clear()
                                        aba_app.update("A1", [cabecalho_app])
                                    except: pass
                                    st.success("✅ Banco zerado com sucesso! Pronto para nova rodagem.")
                                    carregar_dados_completos.clear()
                                    time.sleep(2)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro Crítico ao limpar o banco: {e}")
                        else:
                            if senha_reset: st.error("❌ Senha incorreta.")
# =============================================================================
# 🎧 MÓDULO NOVO: ATENDIMENTO / HELPDESK
# =============================================================================
elif menu == "🎧 Atendimento":
    st.markdown(
        "<div class='dinamic-border'><h3 class='dinamic-text' style='margin:0;'>🎧 Central de Atendimento (Helpdesk)</h3></div>",
        unsafe_allow_html=True)
    st.info("Gerencie as solicitações e chamados abertos pelos clientes no Portal.")

    try:
        aba_chamados = planilha_db.worksheet("Base_Chamados")
        dados_tkt = aba_chamados.get_all_values()

        if len(dados_tkt) > 1:
            df_tkt = pd.DataFrame(dados_tkt[1:], columns=dados_tkt[0])

            # 🔥 CRIANDO AS ABAS DE TRABALHO E HISTÓRICO 🔥
            tab_abertos, tab_historico_tkt = st.tabs(
                ["🟡 Fila de Chamados", "🟢 Histórico Resolvidos"])

            with tab_abertos:
                # Filtra apenas os chamados que estão "Em Análise"
                df_abertos = df_tkt[df_tkt['STATUS'].str.contains(
                    'ANÁLISE', case=False, na=False)]

                if df_abertos.empty:
                    st.success(
                        "🎉 Excelente! Não há nenhum chamado pendente de resposta no momento.")
                else:
                    st.warning(
                        f"⚠️ Você possui {
                            len(df_abertos)} chamado(s) aguardando resposta.")

                    for idx, row in df_abertos.iterrows():
                        with st.container(border=True):
                            c1, c2 = st.columns([3, 1])
                            c1.markdown(f"#### 🏢 {row['TOMADOR']}")
                            c2.markdown(
                                f"<div style='text-align:right;'><span style='background:#fef3c7; color:#92400e; padding:4px 12px; border-radius:99px; font-weight:bold; font-size:12px;'>🎫 {
                                    row['TICKET']}</span></div>", unsafe_allow_html=True)

                            st.markdown(
                                f"**Data:** {row['DATA']} | **Pedido Ref:** {row['PEDIDO'] if row['PEDIDO'] else 'N/A'}")
                            st.info(
                                f"💬 **Mensagem do Cliente:**\n\n{row['MENSAGEM']}")

                            with st.form(f"form_resp_{row['TICKET']}", clear_on_submit=True):
                                resp_texto = st.text_area(
                                    "Sua Resposta Oficial:",
                                    placeholder="Digite aqui a solução ou retorno para o cliente...")

                                if st.form_submit_button(
                                        "✅ Enviar Resposta e Encerrar Ticket", type="primary"):
                                    if not resp_texto.strip():
                                        st.error(
                                            "A resposta não pode estar vazia.")
                                    else:
                                        with st.spinner("Atualizando banco de dados e notificando o cliente..."):
                                            coluna_tickets = aba_chamados.col_values(
                                                1)  # Pega a coluna A (TICKETS)
                                            try:
                                                # +1 porque o sheets começa no índice 1
                                                linha_idx = coluna_tickets.index(
                                                    row['TICKET']) + 1

                                                # Atualiza Status (Coluna 6 =
                                                # F) e Resposta (Coluna 7 = G)
                                                aba_chamados.update_cell(
                                                    linha_idx, 6, "🟢 RESOLVIDO")
                                                aba_chamados.update_cell(
                                                    linha_idx, 7, resp_texto)

                                                # Notificar por WhatsApp
                                                # (usando seu número de
                                                # retorno)
                                                texto_aviso = (
                                                    f"🔔 *ATUALIZAÇÃO DE CHAMADO* [{row['TICKET']}]\n\n"
                                                    f"Olá, equipe *{row['TOMADOR']}*! O C.C.O da IGO Logística acabou de responder à sua solicitação.\n\n"
                                                    f"👨‍💻 *Resposta:* {resp_texto}\n\n"
                                                    f"Acesse o seu Portal do Cliente para visualizar o histórico completo."
                                                )
                                                enviar_whatsapp_zapi(
                                                    "5511947996371", texto_aviso)

                                                st.success(
                                                    f"Ticket {
                                                        row['TICKET']} encerrado com sucesso!")
                                                time.sleep(1.5)
                                                st.rerun()

                                            except Exception as erro_sheets:
                                                st.error(
                                                    f"Erro ao salvar no banco: {erro_sheets}")

            with tab_historico_tkt:
                # Pega tudo que NÃO está em análise (já foi resolvido)
                df_fechados = df_tkt[~df_tkt['STATUS'].str.contains(
                    'ANÁLISE', case=False, na=False)]

                if df_fechados.empty:
                    st.info("Nenhum chamado foi resolvido ainda.")
                else:
                    # Inverte para o mais recente aparecer no topo
                    df_fechados = df_fechados.iloc[::-1]
                    st.markdown("#### 🗄️ Arquivo de Chamados Encerrados")
                    st.dataframe(
                        df_fechados[['TICKET', 'DATA', 'TOMADOR', 'PEDIDO', 'STATUS', 'MENSAGEM', 'RESPOSTA']],
                        hide_index=True,
                        use_container_width=True
                    )

        else:
            st.info("O banco de chamados ainda está vazio.")

    except Exception as e:
        st.error(f"Erro ao conectar com a base de chamados: {e}")
# =============================================================================
# 👥 MÓDULO: CADASTRO DE USUÁRIOS
# =============================================================================
elif menu == "👥 Cadastro de Usuários":
    st.markdown("### 👥 Cadastro de Usuários")
    st.caption("Gerencie os usuários de acesso ao sistema (cadastrar, trocar senha e remover).")

    feedback_cadastro = st.session_state.pop("cadastro_usuario_feedback", None)
    if feedback_cadastro:
        tipo_feedback = feedback_cadastro.get("tipo", "info")
        mensagem_feedback = feedback_cadastro.get("mensagem", "")
        if tipo_feedback == "success":
            st.success(mensagem_feedback)
        elif tipo_feedback == "warning":
            st.warning(mensagem_feedback)
        elif tipo_feedback == "error":
            st.error(mensagem_feedback)
        else:
            st.info(mensagem_feedback)

    usuarios_login = st.session_state.usuarios_login

    portal_clientes = st.session_state.portal_clientes_login
    tomadores_portal_disponiveis = ["TODOS"] + sorted(list(set(CLIENTES_AUTORIZADOS)))

    usuarios_lista = [
        {
            "Usuário": usuario,
            "Perfil": "Administrador" if info.get("admin", False) else "Operacional",
        }
        for usuario, info in sorted(usuarios_login.items())
    ]
    portal_lista = [
        {
            "Usuário": usuario,
            "Tomador": str(info.get("tomador", info.get("filtro", "TODOS"))),
        }
        for usuario, info in sorted(portal_clientes.items())
    ]

    def rotular_usuario_portal(usuario, info):
        tomador = str(info.get("tomador", info.get("filtro", "TODOS"))).strip() or "TODOS"
        return f"{usuario} | Tomador: {tomador}"

    st.markdown(
        f"""
        <style>
        .cadastro-premium-shell {{
            background: linear-gradient(145deg, #0f172a 0%, #1e293b 50%, #334155 100%);
            border: 1px solid rgba(148, 163, 184, 0.24);
            border-radius: 18px;
            padding: 16px 18px 14px 18px;
            margin-bottom: 12px;
            box-shadow: 0 16px 36px rgba(15, 23, 42, 0.18);
        }}
        .cadastro-premium-kicker {{
            color: #93c5fd;
            font-size: 11px;
            font-weight: 900;
            letter-spacing: 1.4px;
            text-transform: uppercase;
            margin-bottom: 4px;
        }}
        .cadastro-premium-title {{
            color: #f8fafc;
            font-size: 22px;
            font-weight: 900;
            line-height: 1.1;
            margin-bottom: 4px;
        }}
        .cadastro-premium-subtitle {{
            color: #cbd5e1;
            font-size: 12px;
            line-height: 1.45;
            margin: 0;
        }}
        .cadastro-stat {{
            background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
            border: 1px solid #dbe3ef;
            border-radius: 14px;
            padding: 12px 14px;
            box-shadow: 0 6px 16px rgba(15, 23, 42, 0.05);
            min-height: 76px;
        }}
        .cadastro-stat-label {{
            color: #64748b;
            font-size: 11px;
            font-weight: 800;
            letter-spacing: 0.4px;
            text-transform: uppercase;
            margin-bottom: 2px;
        }}
        .cadastro-stat-value {{
            color: #0f172a;
            font-size: 26px;
            font-weight: 900;
            line-height: 1;
        }}
        .cadastro-stat-hint {{
            color: #475569;
            font-size: 11px;
            font-weight: 600;
            margin-top: 4px;
        }}
        </style>
        <div class="cadastro-premium-shell">
            <div class="cadastro-premium-kicker">Administração de Acessos</div>
            <div class="cadastro-premium-title">Cadastro de Usuários</div>
            <p class="cadastro-premium-subtitle">Controle usuários internos e usuários do Portal do Cliente com tomador vinculado. Use as listas suspensas para localizar e editar rapidamente quando a base crescer.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    stat1, stat2, stat3 = st.columns(3)
    with stat1:
        st.markdown(f"<div class='cadastro-stat'><div class='cadastro-stat-label'>Usuários internos</div><div class='cadastro-stat-value'>{len(usuarios_login)}</div><div class='cadastro-stat-hint'>Acesso ao sistema operacional</div></div>", unsafe_allow_html=True)
    with stat2:
        st.markdown(f"<div class='cadastro-stat'><div class='cadastro-stat-label'>Usuários do portal</div><div class='cadastro-stat-value'>{len(portal_clientes)}</div><div class='cadastro-stat-hint'>Com tomador já definido no cadastro</div></div>", unsafe_allow_html=True)
    with stat3:
        st.markdown(f"<div class='cadastro-stat'><div class='cadastro-stat-label'>Tomadores disponíveis</div><div class='cadastro-stat-value'>{len(tomadores_portal_disponiveis)}</div><div class='cadastro-stat-hint'>Lista usada no dropdown do portal</div></div>", unsafe_allow_html=True)

    tab_novo, tab_editar, tab_remover = st.tabs(["➕ Novo", "🔑 Editar", "🗑️ Remover"])

    with tab_novo:
        with st.container(border=True):
            st.markdown("#### ➕ Novo usuário")
            sistema_alvo = st.selectbox("Sistema alvo", ["Sistema interno", "Portal do Cliente"], key="sel_sistema_alvo_usuario")
            if sistema_alvo == "Portal do Cliente":
                st.info("A senha do Portal do Cliente e salva na planilha como SENHA_HASH. O codigo que aparece la e esperado e representa a senha protegida, nao a senha em texto puro.")
            with st.form("form_novo_usuario", clear_on_submit=True):
                novo_usuario = normalizar_usuario_login(st.text_input("Usuário"))
                nova_senha = st.text_input("Senha", type="password")
                if sistema_alvo == "Sistema interno":
                    novo_admin = st.checkbox("Administrador", value=False)
                    novo_logo = ""
                    novo_filtro = ""
                    novo_tomador = ""
                else:
                    novo_admin = False
                    novo_logo = "https://i.postimg.cc/x84nnjjq/IGO-LOGO.png"
                    novo_tomador = st.selectbox("Tomador autorizado", tomadores_portal_disponiveis, index=0, key="sel_tomador_portal_novo")
                    novo_filtro = novo_tomador
                cadastrar_usuario = st.form_submit_button("Cadastrar usuário", type="primary", use_container_width=True)

                if cadastrar_usuario:
                    if not novo_usuario or not nova_senha:
                        st.error("Preencha usuário e senha para cadastrar.")
                    else:
                        if sistema_alvo == "Sistema interno":
                            if novo_usuario in usuarios_login:
                                st.error("Este usuário já existe.")
                            else:
                                usuarios_login[novo_usuario] = {
                                    "senha_hash": gerar_hash_senha(nova_senha),
                                    "admin": novo_admin,
                                }
                                salvar_usuarios_login(usuarios_login)
                                st.session_state.usuarios_login = carregar_usuarios_login()
                                registrar_feedback_cadastro_usuario("success", f"Usuario {novo_usuario} cadastrado no sistema interno com sucesso.")
                                st.rerun()
                        else:
                            portal_clientes = st.session_state.portal_clientes_login
                            if novo_usuario in portal_clientes:
                                st.error("Este usuário já existe no Portal do Cliente.")
                            else:
                                portal_clientes[novo_usuario] = {
                                    "senha_hash": gerar_hash_senha(nova_senha),
                                    "logo": novo_logo,
                                    "filtro": novo_filtro,
                                    "tomador": novo_tomador,
                                }
                                salvou_nuvem, recarregado = persistir_e_recarregar_portal_clientes(portal_clientes)
                                if novo_usuario in recarregado:
                                    if salvou_nuvem:
                                        registrar_feedback_cadastro_usuario("success", f"Usuario {novo_usuario} cadastrado no Portal do Cliente com sucesso. A senha foi salva na planilha como SENHA_HASH.")
                                    else:
                                        registrar_feedback_cadastro_usuario("warning", f"Usuario {novo_usuario} salvo apenas localmente. Verifique a conexao com a planilha no Render antes de testar o login no portal.")
                                    st.rerun()
                                else:
                                    st.error("O cadastro não foi persistido. Verifique a conexão com a planilha de login do portal.")

    with tab_editar:
        with st.container(border=True):
            st.markdown("#### 🔑 Alterar senha")
            alvo_edicao = st.selectbox("Sistema para editar", ["Sistema interno", "Portal do Cliente"], key="sel_sistema_edicao_usuario")
            if alvo_edicao == "Sistema interno":
                lista_usuarios = sorted(usuarios_login.keys())
                if lista_usuarios:
                    usuario_edicao = st.selectbox("Selecione o usuário", lista_usuarios, key="sel_usuario_edicao_login")
                    nova_senha_usuario = st.text_input("Nova senha", type="password", key="txt_nova_senha_usuario_login")
                    if st.button("Salvar nova senha", use_container_width=True):
                        if not nova_senha_usuario:
                            st.error("Informe a nova senha.")
                        else:
                            usuarios_login[usuario_edicao]["senha_hash"] = gerar_hash_senha(nova_senha_usuario)
                            salvar_usuarios_login(usuarios_login)
                            st.session_state.usuarios_login = carregar_usuarios_login()
                            registrar_feedback_cadastro_usuario("success", f"Senha do usuario {usuario_edicao} atualizada com sucesso.")
                            st.rerun()
                else:
                    st.info("Não há usuários cadastrados no sistema interno.")
            else:
                if portal_lista:
                    portal_labels = [rotular_usuario_portal(u["Usuário"], portal_clientes[u["Usuário"]]) for u in portal_lista]
                    portal_label_selecionado = st.selectbox("Selecione o usuário", portal_labels, key="sel_usuario_edicao_portal_login")
                    usuario_edicao_portal = portal_label_selecionado.split(" | ", 1)[0].strip()
                    nova_senha_portal = st.text_input("Nova senha do portal", type="password", key="txt_nova_senha_portal_login")
                    tomador_atual_portal = str(portal_clientes[usuario_edicao_portal].get("tomador", portal_clientes[usuario_edicao_portal].get("filtro", "TODOS"))).upper().strip() or "TODOS"
                    indice_tomador_atual = tomadores_portal_disponiveis.index(tomador_atual_portal) if tomador_atual_portal in tomadores_portal_disponiveis else 0
                    novo_tomador_portal = st.selectbox("Tomador autorizado", tomadores_portal_disponiveis, index=indice_tomador_atual, key="sel_tomador_portal_edicao")
                    if st.button("Salvar alterações do portal", use_container_width=True):
                        if not nova_senha_portal:
                            st.error("Informe a nova senha do portal.")
                        else:
                            portal_clientes[usuario_edicao_portal]["senha_hash"] = gerar_hash_senha(nova_senha_portal)
                            portal_clientes[usuario_edicao_portal]["tomador"] = novo_tomador_portal
                            portal_clientes[usuario_edicao_portal]["filtro"] = novo_tomador_portal
                            salvou_nuvem, recarregado = persistir_e_recarregar_portal_clientes(portal_clientes)
                            if usuario_edicao_portal in recarregado:
                                if salvou_nuvem:
                                    registrar_feedback_cadastro_usuario("success", f"Usuario {usuario_edicao_portal} atualizado no Portal do Cliente. A planilha mostra SENHA_HASH, nao a senha em texto puro.")
                                else:
                                    registrar_feedback_cadastro_usuario("warning", f"Usuario {usuario_edicao_portal} atualizado apenas localmente. Verifique a conexao com a planilha no Render antes de testar o login no portal.")
                                st.rerun()
                            else:
                                st.error("A alteração não foi persistida na base de login do portal.")
                else:
                    st.info("Não há usuários cadastrados no Portal do Cliente.")

    with tab_remover:
        with st.container(border=True):
            st.markdown("#### 🗑️ Remover usuário")
            alvo_remocao = st.selectbox("Sistema para remover", ["Sistema interno", "Portal do Cliente"], key="sel_sistema_remocao_usuario")
            if alvo_remocao == "Sistema interno":
                usuarios_remocao = [u for u in sorted(usuarios_login.keys()) if u != st.session_state.usuario_logado]
                if usuarios_remocao:
                    usuario_remover = st.selectbox("Usuário para remover", usuarios_remocao, key="sel_usuario_remover_login")
                    if st.button("Remover usuário", type="secondary", use_container_width=True):
                        qtd_admins = sum(1 for _, info in usuarios_login.items() if info.get("admin", False))
                        if usuarios_login.get(usuario_remover, {}).get("admin", False) and qtd_admins <= 1:
                            st.error("Não é possível remover o último administrador do sistema.")
                        else:
                            usuarios_login.pop(usuario_remover, None)
                            salvar_usuarios_login(usuarios_login)
                            st.session_state.usuarios_login = carregar_usuarios_login()
                            registrar_feedback_cadastro_usuario("success", f"Usuario {usuario_remover} removido com sucesso.")
                            st.rerun()
                else:
                    st.info("Não há usuários disponíveis para remoção.")
            else:
                if portal_lista:
                    portal_labels_rem = [rotular_usuario_portal(u["Usuário"], portal_clientes[u["Usuário"]]) for u in portal_lista]
                    portal_label_remover = st.selectbox("Usuário do portal para remover", portal_labels_rem, key="sel_usuario_remover_portal_login")
                    usuario_remover_portal = portal_label_remover.split(" | ", 1)[0].strip()
                    if st.button("Remover usuário do portal", type="secondary", use_container_width=True):
                        portal_clientes.pop(usuario_remover_portal, None)
                        salvou_nuvem, recarregado = persistir_e_recarregar_portal_clientes(portal_clientes, permitir_remocoes=True)
                        if usuario_remover_portal not in recarregado:
                            if salvou_nuvem:
                                registrar_feedback_cadastro_usuario("success", f"Usuario {usuario_remover_portal} removido do Portal do Cliente com sucesso.")
                            else:
                                registrar_feedback_cadastro_usuario("warning", f"Usuario {usuario_remover_portal} removido apenas localmente. Verifique a conexao com a planilha no Render.")
                            st.rerun()
                        else:
                            st.error("A remoção não foi persistida na base de login do portal.")
                else:
                    st.info("Não há usuários disponíveis para remoção no Portal do Cliente.")

# =============================================================================
# 📈 MÓDULO: DASHBOARD EXECUTIVO (MODO CNN REAL - TV - PROGRESSO + ANÁLISE 30D)
# =============================================================================
elif menu == "📈 Dashboard":
    import plotly.express as px
    import plotly.graph_objects as go
    import requests
    import urllib.parse
    import pandas as pd
    from datetime import timedelta, datetime

    st.markdown("""
        <style>
        /* FUNDO BRANCO E ALINHAMENTO 100% NAS BORDAS */
        [data-testid="stAppViewContainer"] { background-color: #FFFFFF !important; }
        header[data-testid="stHeader"] { display: none !important; }
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 100px !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
            max-width: 100% !important;
        }
        hr { margin: 0.5em 0 !important; border-color: #E2E8F0 !important; }

        @keyframes pulse-red {
            0% { box-shadow: 0 0 0 0 rgba(220, 38, 38, 0.4); }
            70% { box-shadow: 0 0 0 10px rgba(220, 38, 38, 0); }
            100% { box-shadow: 0 0 0 0 rgba(220, 38, 38, 0); }
        }
        .alerta-sirene { animation: pulse-red 2s infinite; border: 1px solid #EF4444 !important; }
        </style>
    """, unsafe_allow_html=True)

    st_autorefresh(
        interval=120000,
        limit=None,
        key="refresh_dashboard_v_final")

    df_raw = carregar_dados_completos(planilha_db)

    if df_raw.empty:
        st.warning("⚠️ Aguardando sincronização de dados...")
    else:
        df_raw['STATUS_DISPLAY'] = df_raw.apply(calc_status_display, axis=1)

        hoje = hoje_br
        ontem_util = hoje - timedelta(days=1)
        while ontem_util.weekday() >= 5 or ontem_util in FERIADOS_BR:
            ontem_util -= timedelta(days=1)

        df_hoje = df_raw[df_raw['DATA_OBJ'] == hoje].copy()
        df_ontem = df_raw[df_raw['DATA_OBJ'] == ontem_util].copy()

        def calc_variacao(val_hoje, val_ontem):
            if val_ontem == 0:
                return ("+100%", "▲") if val_hoje > 0 else ("0%", "-")
            var = ((val_hoje - val_ontem) / val_ontem) * 100
            if var > 0:
                return f"+{var:.1f}%", "▲"
            elif var < 0:
                return f"{var:.1f}%", "▼"
            return "0%", "-"

        # ---------------------------------------------------------
        # VARIÁVEIS DOS 8 BLOCOS
        # ---------------------------------------------------------
        vol_total_h, vol_total_o = len(df_hoje), len(df_ontem)
        realizados_h = len(df_hoje[df_hoje['STATUS_DISPLAY'].str.contains(
            'Entregue|Coletado|Frustrada|Problema|Cancelado|Conferido', case=False)])
        col_h = len(
            df_hoje[df_hoje['STATUS_DISPLAY'].str.contains('Coletado', case=False)])
        ent_h = len(
            df_hoje[df_hoje['STATUS_DISPLAY'].str.contains('Entregue', case=False)])
        pend_h = len(df_hoje[df_hoje['STATUS_DISPLAY'].str.contains(
            'Pendente|Rota', case=False)])
        frus_h = len(df_hoje[df_hoje['STATUS_DISPLAY'].str.contains(
            'Frustrada|Problema|Cancelado', case=False)])
        atra_h = len(
            df_hoje[df_hoje['STATUS_DISPLAY'].str.contains('ATRASADO', case=False)])

        taxa_sucesso_h = (
            realizados_h /
            vol_total_h *
            100) if vol_total_h > 0 else 0
        atra_total = len(
            df_raw[df_raw['STATUS_DISPLAY'].str.contains('ATRASADO', case=False)])
        qtd_chamados = checar_chamados_pendentes(planilha_db)

        # Cálculo da variação seca de volume total (hoje vs ontem)
        v_tot_str, s_tot = calc_variacao(vol_total_h, vol_total_o)

        v_ent_str, s_ent = calc_variacao(ent_h, len(
            df_ontem[df_ontem['STATUS_DISPLAY'].str.contains('Entregue', case=False)]))
        v_pend_str, s_pend = calc_variacao(pend_h, len(
            df_ontem[df_ontem['STATUS_DISPLAY'].str.contains('Pendente|Rota', case=False)]))
        v_frus_str, s_frus = calc_variacao(frus_h, len(
            df_ontem[df_ontem['STATUS_DISPLAY'].str.contains('Frustrada|Problema|Cancelado', case=False)]))

        # ---------------------------------------------------------
        # OS 8 KPI CARDS INTACTOS
        # ---------------------------------------------------------
        def render_kpi_card(
                title,
                value,
                var_str,
                color,
                bg_color,
                icon,
                alert=False):
            cls = "alerta-sirene" if alert else ""
            st.markdown(f"""
                <div class="{cls}" style="background-color: {bg_color}; border: 1px solid {color}40; border-radius: 12px; padding: 14px 16px; position: relative; overflow: hidden; height: 105px; margin-bottom: 15px;">
                    <div style="position: absolute; right: -5px; bottom: -15px; font-size: 80px; opacity: 0.45; z-index: 0;">{icon}</div>
                    <div style="position: relative; z-index: 1; display: flex; flex-direction: column; height: 100%; justify-content: space-between;">
                        <div style="font-size: 12px; font-weight: 800; color: {color}; text-transform: uppercase;">{title}</div>
                        <div style="display: flex; justify-content: space-between; align-items: flex-end;">
                            <div style="font-size: 30px; font-weight: 900; color: #0F172A;">{value}</div>
                            <div style="font-size: 11px; font-weight: 700; color: {color}; background: rgba(255,255,255,0.8); padding: 2px 6px; border-radius: 4px; white-space: nowrap;">{var_str}</div>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

        cor_tkt, bg_tkt = (
            "#EF4444", "#FEF2F2") if qtd_chamados > 0 else (
            "#64748B", "#F8FAFC")
        sub_tkt = "🚨 Atenção" if qtd_chamados > 0 else "✅ Limpo"
        cor_atra, bg_atra = (
            "#F43F5E", "#FDF2F8") if atra_total > 0 else (
            "#64748B", "#F8FAFC")

        # Injeção da taxa de sucesso + Variação do Volume Total Seco
        texto_badge_realizados = f"{
            int(taxa_sucesso_h)}% Conc. | Vol: {s_tot}{v_tot_str}"

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            render_kpi_card(
                "REALIZADOS (HOJE)",
                f"{realizados_h}/{vol_total_h}",
                texto_badge_realizados,
                "#3B82F6",
                "#EFF6FF",
                "📦")
        with c2:
            render_kpi_card("EFICIÊNCIA (HOJE)",
                            f"{taxa_sucesso_h:.1f}%",
                            "Ação/Vol",
                            "#10B981",
                            "#F0FDF4",
                            "🎯")
        with c3:
            render_kpi_card(
                "CHAMADOS",
                qtd_chamados,
                sub_tkt,
                cor_tkt,
                bg_tkt,
                "🎧",
                alert=(
                    qtd_chamados > 0))
        with c4:
            render_kpi_card(
                "ATRASADOS (GERAL)",
                atra_total,
                "BACKLOG",
                cor_atra,
                bg_atra,
                "⏳",
                alert=(
                    atra_total > 0))

        c5, c6, c7, c8 = st.columns(4)
        with c5:
            render_kpi_card(
                "PENDENTES (HOJE)",
                pend_h,
                f"{s_pend}{v_pend_str}",
                "#F59E0B",
                "#FFFBEB",
                "🚚")
        with c6:
            render_kpi_card(
                "COLETADOS (HOJE)",
                col_h,
                "Visitas Hoje",
                "#6366F1",
                "#EEF2FF",
                "📥")
        with c7:
            render_kpi_card(
                "FRUSTRADAS (HOJE)",
                frus_h,
                f"{s_frus}{v_frus_str}",
                "#EF4444",
                "#FEF2F2",
                "🛑")
        with c8:
            render_kpi_card(
                "BASE ONTEM",
                vol_total_o,
                "Ref. Cálculo",
                "#64748B",
                "#F8FAFC",
                "📊")

        st.markdown("<br>", unsafe_allow_html=True)

        # ---------------------------------------------------------
        # GRÁFICO E TABELA (COM A BARRA GRADATIVA E ANÁLISE 30D)
        # ---------------------------------------------------------
        col_pie, col_table = st.columns([1, 1.5])
        with col_pie:
            st.markdown(
                "<p style='font-weight: 800; font-size: 13px; color: #475569; margin-bottom: 0px;'>📊 STATUS DA OPERAÇÃO HOJE</p>",
                unsafe_allow_html=True)
            df_status = pd.DataFrame(
                {
                    'S': [
                        'Coletado',
                        'Entregue',
                        'Pendente',
                        'Frustrada',
                        'Atrasado'],
                    'V': [
                        col_h,
                        ent_h,
                        pend_h,
                        frus_h,
                        atra_h]})
            df_status = df_status[df_status['V'] > 0]
            if not df_status.empty:
                cores_map = {
                    'Coletado': '#6366F1',
                    'Entregue': '#10B981',
                    'Pendente': '#F59E0B',
                    'Frustrada': '#EF4444',
                    'Atrasado': '#991B1B'}
                fig_donut = px.pie(
                    df_status,
                    values='V',
                    names='S',
                    hole=0.6,
                    color='S',
                    color_discrete_map=cores_map)
                fig_donut.update_traces(
                    textinfo='percent',
                    textfont_size=12,
                    textfont_color='white',
                    marker=dict(
                        line=dict(
                            color="#FFFFFF",
                            width=2)))
                fig_donut.update_layout(
                    template="plotly_white",
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    margin=dict(
                        t=10,
                        b=0,
                        l=0,
                        r=0),
                    showlegend=True,
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=-0.2,
                        xanchor="center",
                        x=0.5,
                        font=dict(
                            size=11,
                            color="#64748B")),
                    height=240)
                st.plotly_chart(fig_donut, use_container_width=True)
            else:
                st.info("Sem dados.")

        with col_table:
            st.markdown(
                "<p style='font-weight: 900; font-size: 13px; color: #475569; margin-bottom: 12px; text-transform: uppercase;'>🏢 Volumes e Conclusões por Tomador</p>",
                unsafe_allow_html=True)
            if not df_hoje.empty:
                tomadores_stats = []
                data_limite_30d = hoje - timedelta(days=30)

                for tomador in df_hoje['TOMADOR'].dropna().unique():
                    if str(tomador).strip() == "":
                        continue

                    df_tom = df_hoje[df_hoje['TOMADOR'] == tomador]
                    vol_tot = len(df_tom)
                    vol_real = len(df_tom[df_tom['STATUS_DISPLAY'].str.contains(
                        'Entregue|Coletado|Frustrada|Problema|Cancelado|Conferido', case=False)])
                    pct = int((vol_real / vol_tot) * 100) if vol_tot > 0 else 0

                    df_tom_hist = df_raw[(df_raw['TOMADOR'] == tomador) & (
                        df_raw['DATA_OBJ'] < hoje)]

                    vol_ant = 0
                    if not df_tom_hist.empty:
                        datas_unicas = sorted(
                            df_tom_hist['DATA_OBJ'].unique(), reverse=True)
                        for d in datas_unicas:
                            dt_check = pd.to_datetime(d).date() if hasattr(
                                d, 'date') else pd.to_datetime(d)
                            if hasattr(dt_check, 'weekday') and dt_check.weekday(
                            ) < 5 and dt_check not in FERIADOS_BR:
                                vol_ant = len(
                                    df_tom_hist[df_tom_hist['DATA_OBJ'] == d])
                                break

                    if vol_ant == 0:
                        var_pct = 100 if vol_tot > 0 else 0
                        var_str = f"▲ +{var_pct}%"
                        cor_var = "#10B981"
                    else:
                        var_pct = ((vol_tot - vol_ant) / vol_ant) * 100
                        if var_pct > 0:
                            var_str = f"▲ +{var_pct:.0f}%"
                            cor_var = "#10B981"
                        elif var_pct < 0:
                            var_str = f"▼ {var_pct:.0f}%"
                            cor_var = "#EF4444"
                        else:
                            var_str = "- 0%"
                            cor_var = "#64748B"

                    media_30d = 0
                    if not df_tom_hist.empty:
                        df_30d = df_tom_hist[df_tom_hist['DATA_OBJ']
                                            >= data_limite_30d]
                        if not df_30d.empty:
                            dias_ativos = df_30d['DATA_OBJ'].nunique()
                            if dias_ativos > 0:
                                media_30d = int(len(df_30d) / dias_ativos)

                    tomadores_stats.append({
                        'Cliente': tomador,
                        'Total': vol_tot,
                        'Realizado': vol_real,
                        'Pct': pct,
                        'Media': media_30d,
                        'VarStr': var_str,
                        'CorVar': cor_var
                    })

                if tomadores_stats:
                    tomadores_df = pd.DataFrame(tomadores_stats).sort_values(
                        by='Total', ascending=False)

                    def get_logo_url(tomador):
                        logos = {
                            "ECOLYZER": "https://lh3.googleusercontent.com/d/1NdbO7olL6GUQDN3krRnyICfgNC07Di2Z",
                            "GRALAB": "https://lh3.googleusercontent.com/d/1SeNj-i590Q6ft-pUcSIk-OKKHiOYtAxU",
                            "CUNHA": "https://lh3.googleusercontent.com/d/1SeNj-i590Q6ft-pUcSIk-OKKHiOYtAxU",
                            "LABEST": "https://lh3.googleusercontent.com/d/15pSrGXFBvpaJwVYrgJkBa01RPgPNsdnT",
                            "SOUZA CRUZ": "https://lh3.googleusercontent.com/d/1qnaukWDnGDAJ8G5zCFBg0Zw2BsXW4QEb",
                            "HEXALIFE": "https://lh3.googleusercontent.com/d/1FAoDyfWdfaUFUjyB2z_7cpiWAdH5AzMd",
                            "INNOVATOX": "https://lh3.googleusercontent.com/d/1f-pKadqlAEeDnUw5YDMT1qJ52_LCxhPH",
                            "SODRE": "https://lh3.googleusercontent.com/d/1n17pTrQ6i0ymgfw0alc8Ie6BEQOuJSxq",
                            "SYNVIA": "https://lh3.googleusercontent.com/d/1MYi7GKT6aAtYJALMoHFOxqmOjdV_Qjoh",
                            "CAEP": "https://lh3.googleusercontent.com/d/1MYi7GKT6aAtYJALMoHFOxqmOjdV_Qjoh",
                            "SAPIENS": "https://lh3.googleusercontent.com/d/1SeimGoz8sEhF-_63LpFkHJLgXbWzrBIP"}
                        return logos.get(
                            str(tomador).strip().upper(),
                            "https://lh3.googleusercontent.com/d/10dZJLyT3lMO6q1pq0ZQCA9WwTu_B4bLY")

                    html_cards = "<div style='display: flex; flex-direction: column; gap: 8px; height: 240px; overflow-y: auto; padding-right: 5px;'>"
                    for _, row in tomadores_df.iterrows():
                        cli = row['Cliente']
                        tot = row['Total']
                        real = row['Realizado']
                        pct = row['Pct']
                        media = row['Media']
                        var_str = row['VarStr']
                        cor_var = row['CorVar']

                        cor_bg = "#EF4444"
                        if pct > 40:
                            cor_bg = "#F59E0B"
                        if pct > 80:
                            cor_bg = "#10B981"

                        html_cards += f"""<div style="display: flex; align-items: center; padding: 12px; background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.03); margin-bottom: 2px;">
                            <div style="width: 42px; height: 42px; border-radius: 8px; background: #F8FAFC; display: flex; justify-content: center; align-items: center; margin-right: 15px; border: 1px solid #F1F5F9; padding: 3px; flex-shrink: 0;">
                                <img src="{get_logo_url(cli)}" style="max-width: 100%; max-height: 100%; object-fit: contain;">
                            </div>
                            <div style="flex-grow: 1;">
                                <div style="display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 6px;">
                                    <span style="font-size: 13px; font-weight: 800; color: #1E293B;">{str(cli).upper()}</span>
                                    <span style="font-size: 15px; font-weight: 900; color: #0F172A;">{real}/
    {tot} <span style="font-size: 10px; color: #64748B; font-weight: 700;">({pct}%)</span></span>
                                </div>
                                <div style="height: 6px; background-color: #F1F5F9; border-radius: 4px; overflow: hidden; margin-bottom: 5px;">
                                    <div style="width: {pct}%; height: 100%; background: linear-gradient(90deg, #EF4444 0%, {cor_bg} 100%); border-radius: 4px; transition: width 0.5s;"></div>
                                </div>
                                <div style="display: flex; justify-content: space-between; font-size: 10.5px; font-weight: 700;">
                                    <span style="color: #64748B;">📊 Média: {media} vols/dia</span>
                                    <span style="color: {cor_var};">{var_str}</span>
                                </div>
                            </div>
                        </div>"""
                    html_cards += "</div>"
                    st.markdown(html_cards, unsafe_allow_html=True)
            else:
                st.info("Sem dados de movimentação hoje.")

        st.markdown("<br>", unsafe_allow_html=True)

        # ---------------------------------------------------------
        # PÓDIO DA EQUIPE (AGORA TOP 5!)
        # ---------------------------------------------------------
        dict_nomes_dash = {
            str(
                r.get(
                    'LOGIN DO AGENTE',
                    '')).strip().lower(): str(
                r.get(
                    'NOME DO AGENTE',
                    '')).strip() for _,
            r in DF_AGENTES.iterrows() if str(
                        r.get(
                            'LOGIN DO AGENTE',
                            '')).strip()}
        frota_stats = {}
        if not df_hoje.empty:
            for ag in df_hoje['AGENTE_RAW'].dropna().unique():
                if not str(ag).strip() or str(ag).upper() == 'NAN':
                    continue
                nome_amigavel = dict_nomes_dash.get(
                    str(ag).strip().lower(), str(ag).upper().split('|')[0])
                df_ag = df_hoje[df_hoje['AGENTE_RAW'] == ag]
                total_ag = len(df_ag)
                concluidos_ag = len(df_ag[df_ag['STATUS_DISPLAY'].str.contains(
                    'Entregue|Coletado|Frustrada|Problema|Cancelado', case=False)])
                perc_ag = int((concluidos_ag / total_ag)
                            * 100) if total_ag > 0 else 0
                frota_stats[nome_amigavel] = {
                    "perc": perc_ag, "conc": concluidos_ag, "total": total_ag}
        frota_ordenada = sorted(
            frota_stats.items(),
            key=lambda x: x[1]['perc'],
            reverse=True)

        if len(frota_ordenada) > 0:
            st.markdown(
                "<p style='font-weight: 800; font-size: 13px; color: #475569;'>🏆 PERFORMANCE DA EQUIPE (TOP 5 HOJE)</p>",
                unsafe_allow_html=True)
            # Layout em 5 colunas
            rf1, rf2, rf3, rf4, rf5 = st.columns(5)

            # Layout do card ajustado sutilmente para acomodar os 5 blocos sem
            # quebrar o texto
            def podio_ui(pos, ic, ag, pct, vols, color, bg_color):
                return f"""<div style="background-color: {bg_color}; border: 1px solid {color}40; border-bottom: 3px solid {color}; padding: 10px 12px; border-radius: 8px; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 2px 4px rgba(0,0,0,0.02);"><div style="display: flex; align-items: center; gap: 8px;"><span style="font-size: 22px;">{ic}</span><div><div style="font-size: 11.5px; font-weight: 800; color: #0F172A; letter-spacing: 0.2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 80px;">{ag}</div><div style="font-size: 10px; color: #64748B; font-weight: 600;">{vols} vols</div></div></div><div style="font-size: 18px; font-weight: 900; color: {color};">{pct}%</div></div>"""

            if len(frota_ordenada) >= 1:
                rf1.markdown(
                    podio_ui(
                        "1", "🥇", frota_ordenada[0][0], frota_ordenada[0][1]['perc'], f"{
                            frota_ordenada[0][1]['conc']}/{
                            frota_ordenada[0][1]['total']}", "#10B981", "#F0FDF4"), unsafe_allow_html=True)
            if len(frota_ordenada) >= 2:
                rf2.markdown(
                    podio_ui(
                        "2", "🥈", frota_ordenada[1][0], frota_ordenada[1][1]['perc'], f"{
                            frota_ordenada[1][1]['conc']}/{
                            frota_ordenada[1][1]['total']}", "#64748B", "#FFFFFF"), unsafe_allow_html=True)
            if len(frota_ordenada) >= 3:
                rf3.markdown(
                    podio_ui(
                        "3", "🥉", frota_ordenada[2][0], frota_ordenada[2][1]['perc'], f"{
                            frota_ordenada[2][1]['conc']}/{
                            frota_ordenada[2][1]['total']}", "#F59E0B", "#FFFBEB"), unsafe_allow_html=True)
            if len(frota_ordenada) >= 4:
                rf4.markdown(
                    podio_ui(
                        "4", "🎖️", frota_ordenada[3][0], frota_ordenada[3][1]['perc'], f"{
                            frota_ordenada[3][1]['conc']}/{
                            frota_ordenada[3][1]['total']}", "#8B5CF6", "#F5F3FF"), unsafe_allow_html=True)
            if len(frota_ordenada) >= 5:
                rf5.markdown(
                    podio_ui(
                        "5", "🎖️", frota_ordenada[4][0], frota_ordenada[4][1]['perc'], f"{
                            frota_ordenada[4][1]['conc']}/{
                            frota_ordenada[4][1]['total']}", "#06B6D4", "#ECFEFF"), unsafe_allow_html=True)
        else:
            st.info(
                "Aguardando finalizações da frota no dia de hoje para compor o pódio.")

        # ---------------------------------------------------------
        # LETREIRO CNN DE NOTÍCIAS (COM TÊNIS, CLIMA E TRÂNSITO)
        # ---------------------------------------------------------
        @st.cache_data(ttl=1800)
        def buscar_noticias_transito_radar(cidades_com_uf):
            noticias_radar = []
            import xml.etree.ElementTree as ET
            cidades_alvo = [str(c).split('/')[0].strip()
                            for c in cidades_com_uf if str(c).strip()][:4]
            for cidade in cidades_alvo:
                query = f'(trânsito OR acidente OR rodovia) "{cidade}"'
                url = f'https://news.google.com/rss/search?q={
                    urllib.parse.quote(query)}&hl=pt-BR&gl=BR&ceid=BR:pt-419'
                try:
                    resp = requests.get(url, timeout=3)
                    root = ET.fromstring(resp.content)
                    items = root.findall('.//item')[:1]
                    for item in items:
                        titulo = item.find('title').text.split(" - ")[0]
                        noticias_radar.append(
                            f"🌍 [RADAR EXTERNO] Trânsito em {
                                cidade.upper()}: {titulo}")
                except BaseException:
                    continue
            return noticias_radar

        @st.cache_data(ttl=3600)
        def buscar_alertas_climaticos(cidades_com_uf):
            alertas = []
            for item in cidades_com_uf:
                if not item or str(item).upper() == "NAN":
                    continue
                try:
                    cidade_busca = str(item).split(
                        '/')[0].strip() if '/' in str(item) else str(item).strip()
                    resp = requests.get(
                        f"https://wttr.in/{urllib.parse.quote(cidade_busca)}?format=j1", timeout=3)
                    if resp.status_code == 200:
                        condicao = str(
                            resp.json()['current_condition'][0]['weatherDesc'][0]['value']).lower()
                        if any(
                            x in condicao for x in [
                                'rain',
                                'shower',
                                'storm',
                                'thunder']):
                            alertas.append(
                                f"🌍 [RADAR EXTERNO] Clima: Alerta de Chuva na rota de {item}!")
                except BaseException:
                    continue
            return alertas

        @st.cache_data(ttl=300)
        def buscar_placares_tenis_ao_vivo():
            placares = []
            try:
                urls = [
                    "http://site.api.espn.com/apis/site/v2/sports/tennis/atp/scoreboard",
                    "http://site.api.espn.com/apis/site/v2/sports/tennis/wta/scoreboard"]
                for url in urls:
                    resp = requests.get(url, timeout=4)
                    if resp.status_code == 200:
                        data = resp.json()
                        eventos = data.get('events', [])
                        for ev in eventos:
                            try:
                                status_state = ev.get(
                                    'status',
                                    {}).get(
                                    'type',
                                    {}).get(
                                    'state',
                                    '')
                                status_detail = ev.get(
                                    'status',
                                    {}).get(
                                    'type',
                                    {}).get(
                                    'detail',
                                    '')

                                if status_state in ['in', 'post']:
                                    comp = ev['competitions'][0]['competitors']
                                    j1 = comp[0]['athlete']['shortName']
                                    s1 = comp[0].get('score', '0')
                                    j2 = comp[1]['athlete']['shortName']
                                    s2 = comp[1].get('score', '0')

                                    torneio = ev.get(
                                        'season',
                                        {}).get(
                                        'slug',
                                        'Torneio').replace(
                                        '-',
                                        ' ').title()

                                    if status_state == 'in':
                                        placares.append(
                                            f"🔴 [AO VIVO - {torneio}] {j1} {s1} x {s2} {j2} ({status_detail})")
                                    elif status_state == 'post' and len(placares) < 4:
                                        placares.append(
                                            f"🎾 [RESULTADO - {torneio}] {j1} {s1} x {s2} {j2}")
                            except BaseException:
                                continue
                            if len(placares) >= 5:
                                break
            except BaseException:
                pass
            return placares[:5]

        manchetes = [
            f"🟢 [STATUS] C.C.O OPERACIONAL - {datetime.now(FUSO_BR).strftime('%H:%M')}",
            f"📊 [DESEMPENHO] {realizados_h}/{vol_total_h} PEDIDOS PROCESSADOS ({int(taxa_sucesso_h)}% DA OPERAÇÃO)"
        ]

        if atra_total > 0:
            manchetes.append(
                f"🚨 [ALERTA] BACKLOG: {atra_total} PEDIDOS ATRASADOS NA GRID GERAL!")
        if qtd_chamados > 0:
            manchetes.append(
                f"🎧 [HELPDESK] EXISTEM {qtd_chamados} CHAMADOS PENDENTES!")

        if not df_hoje.empty:
            df_concluidos = df_hoje[df_hoje['STATUS_DISPLAY'].str.contains(
                'Entregue|Frustrada|Coletado', case=False)]
            if not df_concluidos.empty:
                ultimas_baixas = df_concluidos.tail(3)
                for _, row in ultimas_baixas.iterrows():
                    pcl_nome = ""
                    colunas_busca = [
                        'LABORATÓRIO',
                        'LABORATORIO',
                        'NOME DO LABORATÓRIO',
                        'TOMADOR',
                        'DESTINATARIO',
                        'NOME DO PCL',
                        'NOME FANTASIA',
                        'CLIENTE']
                    for col_nome in colunas_busca:
                        if col_nome in row.index:
                            val = str(row[col_nome]).strip()
                            if val and val.upper() != 'NAN' and not val.isnumeric():
                                pcl_nome = val
                                break

                    if not pcl_nome:
                        val_pcl = str(row.get('PCL', '')).strip()
                        if val_pcl and val_pcl.upper() != 'NAN':
                            pcl_nome = f"Cód {val_pcl}" if val_pcl.isnumeric(
                            ) else val_pcl
                        else:
                            pcl_nome = f"Pedido {str(row.get('PEDIDO', 'N/A'))}"

                    cidade = str(row.get('CIDADE', '')).strip().title()
                    local_str = f" em {cidade}" if cidade and cidade.upper(
                    ) != "NAN" else ""
                    st_disp = str(
                        row.get(
                            'STATUS_DISPLAY',
                            'ATUALIZADO')).upper()
                    ag_bruto = str(
                        row.get(
                            'AGENTE_RAW',
                            'EQUIPE')).split('|')[0]
                    ag = dict_nomes_dash.get(
                        ag_bruto.lower(), ag_bruto.upper())

                    manchetes.append(
                        f"🚚 [GIRO DE ROTA] {pcl_nome}{local_str} registrado como {st_disp} por {ag}.")

        cidades_alvo = []
        if not df_hoje.empty:
            top_cids = df_hoje['CIDADE'].value_counts().head(3).index.tolist()
            col_uf = 'UF' if 'UF' in df_hoje.columns else (
                'ESTADO' if 'ESTADO' in df_hoje.columns else None)
            for cid in top_cids:
                try:
                    cidades_alvo.append(
                        f"{str(cid).strip().title()}/{str(df_hoje[df_hoje['CIDADE'] == cid][col_uf].mode()[0]).strip().upper()}" if col_uf else str(cid).strip().title())
                except BaseException:
                    cidades_alvo.append(str(cid).strip().title())

        manchetes.extend(buscar_placares_tenis_ao_vivo())

        if cidades_alvo:
            manchetes.extend(buscar_alertas_climaticos(cidades_alvo))
            manchetes.extend(buscar_noticias_transito_radar(cidades_alvo))

        ticker_text = "      <span style='color: #FFC000; font-weight: 900;'>|</span>      ".join([
                                                                                                m for m in manchetes])

        st.markdown(f"""
            <div class="ticker-wrap-fixed">
                <div class="badge-radar-fixed">NOTÍCIAS</div>
                <div class="ticker-move">
                    <span class="ticker-item">{ticker_text}</span>
                </div>
            </div>
            <style>
            .ticker-wrap-fixed {{ position: fixed; bottom: 0; left: 0; width: 100%; background: #09090B; padding: 14px 0; border-top: 4px solid #CC0000; z-index: 999999; overflow: hidden; }}
            .ticker-move {{ display: inline-block; white-space: nowrap; padding-left: 100%; animation: ticker 130s linear infinite; }}
            @keyframes ticker {{ 0% {{ transform: translate3d(0, 0, 0); }} 100% {{ transform: translate3d(-100%, 0, 0); }} }}
            .ticker-item {{ font-size: 22px; font-weight: 700; color: #FFFFFF; font-family: 'Arial', sans-serif; letter-spacing: 0.5px; }}
            .badge-radar-fixed {{ position: absolute; left: 0; top: 0; bottom: 0; background: #CC0000; color: #FFFFFF; padding: 0 30px; z-index: 10; display: flex; align-items: center; font-weight: 900; font-size: 20px; text-transform: uppercase; }}
            </style>
        """, unsafe_allow_html=True)
