"""
Ponto de entrada da aplicação.

Endpoint principal:
    POST /incluir  →  recebe JSON (payload plano ou envelope com `payload`),
                      regista em auditoria (ficheiro e/ou MySQL), mapeia e,
                      para template de ligação, só cria item na Monday se
                      `ligacao_acionamento` for um dos valores configurados.
    GET  /health   →  verifica se o serviço está no ar.
"""

import logging
import ipaddress
import json
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from config import ALLOWED_SOURCE_IPS, CAMPOS_FIXOS, MONDAY_API_TOKEN, TRUST_PROXY
from Modulos.auditoria import (
    MONDAY_RESULTADO_ERRO,
    MONDAY_RESULTADO_IGNORADO,
    MONDAY_RESULTADO_NAO_TENTADO,
    MONDAY_RESULTADO_SUCESSO,
    registrar_resultado_monday_seguro,
    registrar_requisicao_incluir,
)
from Modulos.receptor import processar_requisicao
from Modulos.mapeador import mapear
from Modulos.monday_api import criar_item, buscar_usuario_por_email
from Modulos.payload_entrada import extrair_payload_negocio, LIGACAO_ACIONAMENTO_ENVIA_MONDAY
from Modulos.identificador import identificar_template, TIPO_LIGACAO

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

_PERMISSAO_EMAIL = CAMPOS_FIXOS["permissao"]
_PERMISSAO_USER_ID = None

# --- TEMPORÁRIO: log extra do corpo recebido em POST /incluir (remover após depuração) ---
_TEMP_LOG_RECEBIDO_PATH = os.path.join(os.path.dirname(__file__), "logs", "temp_recebido_post_incluir.jsonl")


def _temp_log_payload_incluir(client_ip: str, payload: Dict[str, Any]) -> None:
    """Grava uma linha JSON por requisição. Não deve quebrar a API se falhar."""
    try:
        os.makedirs(os.path.dirname(_TEMP_LOG_RECEBIDO_PATH), exist_ok=True)
        registro = {
            "received_at": datetime.now(timezone.utc).isoformat(),
            "client_ip": client_ip,
            "payload": payload,
        }
        with open(_TEMP_LOG_RECEBIDO_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(registro, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning(f"[TEMP log recebido] falha ao gravar: {e}")


def _ip_do_cliente(request: Request) -> str:
    """
    Retorna o IP do cliente. Se TRUST_PROXY estiver ativo, tenta usar X-Forwarded-For.
    """
    if TRUST_PROXY:
        xff = request.headers.get("x-forwarded-for")
        if xff:
            # primeiro IP é o originador em listas padrão "client, proxy1, proxy2"
            return xff.split(",")[0].strip()
    return request.client.host if request.client else ""


def _ip_permitido(ip: str) -> bool:
    """
    Se ALLOWED_SOURCE_IPS estiver vazio: não bloqueia.
    Caso contrário, permite se o IP bater em algum IP/CIDR configurado.
    """
    if not ALLOWED_SOURCE_IPS:
        return True
    try:
        ip_obj = ipaddress.ip_address(ip)
    except ValueError:
        return False

    for item in ALLOWED_SOURCE_IPS:
        try:
            net = ipaddress.ip_network(item, strict=False)
        except ValueError:
            # config inválida já deveria ter explodido no startup (config.py),
            # mas mantemos defensivo aqui para não quebrar requests.
            continue
        if ip_obj in net:
            return True
    return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _PERMISSAO_USER_ID
    if not MONDAY_API_TOKEN or not str(MONDAY_API_TOKEN).strip():
        logger.warning("MONDAY_API_TOKEN não definido ou vazio — /incluir falhará na Monday.")
    try:
        _PERMISSAO_USER_ID = buscar_usuario_por_email(_PERMISSAO_EMAIL)
        if _PERMISSAO_USER_ID:
            logger.info(f"Usuário de permissão encontrado: id={_PERMISSAO_USER_ID} ({_PERMISSAO_EMAIL})")
        else:
            logger.warning(f"Usuário de permissão não encontrado para o e-mail: {_PERMISSAO_EMAIL}")
    except Exception as e:
        logger.error(f"Erro ao resolver usuário de permissão: {e}")
    yield


app = FastAPI(
    title="Int_Sys_to_Mdy",
    description="Integração: recebe dados externos e insere no board da Monday.com",
    version="1.0.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def ip_allowlist_middleware(request: Request, call_next):
    # Protege apenas o endpoint de ingestão externa.
    if request.url.path == "/incluir":
        ip = _ip_do_cliente(request)
        if not _ip_permitido(ip):
            logger.warning(f"Bloqueado por allowlist: ip={ip!r} path={request.url.path}")
            return JSONResponse(
                status_code=403,
                content={"sucesso": False, "mensagem": "IP não permitido."},
            )
    return await call_next(request)


@app.post("/incluir", summary="Incluir item na Monday")
async def incluir(request: Request) -> JSONResponse:
    try:
        dados_corpo: Dict[str, Any] = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="JSON inválido ou ausente no corpo da requisição.")

    client_ip = _ip_do_cliente(request)

    # TEMPORÁRIO — remover: cópia explícita do JSON recebido (ver também auditoria oficial)
    _temp_log_payload_incluir(client_ip, dados_corpo)

    # Auditoria: regista o corpo **como recebido** (envelope ou payload plano)
    try:
        rid = registrar_requisicao_incluir(
            client_ip=client_ip,
            path=str(request.url.path),
            payload=dados_corpo,
            headers={
                "user-agent": request.headers.get("user-agent", ""),
                "content-type": request.headers.get("content-type", ""),
                "x-forwarded-for": request.headers.get("x-forwarded-for", ""),
            },
        )
        logger.info(f"Requisição auditada: request_id={rid}")
    except Exception as e:
        logger.warning(f"Falha ao auditar requisição: {e}")
        rid = ""

    dados_negocio, _envelope = extrair_payload_negocio(dados_corpo)

    dados_mapeados: Any = None
    try:
        dados_normalizados = processar_requisicao(dados_negocio)
        template = identificar_template(dados_normalizados)

        acionamento_raw = dados_normalizados.get("ligacao_acionamento")
        if acionamento_raw is not None and str(acionamento_raw).strip():
            acionamento = str(acionamento_raw).strip()
            if acionamento not in LIGACAO_ACIONAMENTO_ENVIA_MONDAY:
                logger.info(
                    "Requisição registada; Monday ignorada (acionamento=%r não elegível). request_id=%s",
                    acionamento,
                    rid,
                )
                registrar_resultado_monday_seguro(rid, MONDAY_RESULTADO_IGNORADO)
                return JSONResponse(
                    status_code=200,
                    content={
                        "sucesso": True,
                        "mensagem": (
                            "Requisição recebida e registada; não enviada à Monday "
                            "(ligacao_acionamento só é enviado para: "
                            + ", ".join(sorted(LIGACAO_ACIONAMENTO_ENVIA_MONDAY))
                            + ")."
                        ),
                        "request_id": rid,
                        "ligacao_acionamento": acionamento,
                        "monday": {"enviado": False},
                    },
                )

        dados_mapeados = mapear(dados_normalizados)
        resultado = criar_item(dados_mapeados, _PERMISSAO_USER_ID)
        logger.info(
            f"Item criado: id={resultado.get('id')} | "
            f"processo={dados_mapeados.get('processo')} | "
            f"tipo={dados_mapeados.get('rpv_prc')}"
        )
        registrar_resultado_monday_seguro(
            rid,
            MONDAY_RESULTADO_SUCESSO,
            monday_item_id=resultado.get("id"),
        )

        return JSONResponse(
            status_code=201,
            content={
                "sucesso": True,
                "mensagem": "Item criado com sucesso na Monday.",
                "request_id": rid,
                "item": resultado,
                "monday": {"enviado": True},
            },
        )

    except ValueError as e:
        logger.warning(f"Erro de validação: {e}")
        registrar_resultado_monday_seguro(rid, MONDAY_RESULTADO_NAO_TENTADO, monday_erro=str(e))
        raise HTTPException(status_code=422, detail=str(e))

    except RuntimeError as e:
        logger.error("Erro na API Monday: %s | dados_mapeados=%s", e, dados_mapeados)
        registrar_resultado_monday_seguro(rid, MONDAY_RESULTADO_ERRO, monday_erro=str(e))
        raise HTTPException(
            status_code=502,
            detail={
                "sucesso": False,
                "mensagem": str(e),
                "request_id": rid,
                "dados_mapeados_para_monday": dados_mapeados,
            },
        )

    except Exception as e:
        logger.exception("Erro inesperado")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


@app.get("/health", summary="Verificar status da aplicação")
def health() -> Dict[str, str]:
    return {"status": "ok"}
