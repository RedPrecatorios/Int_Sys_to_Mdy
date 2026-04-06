"""
Ponto de entrada da aplicação.

Endpoint principal:
    POST /incluir  →  recebe os dados, mapeia e insere na Monday.
    GET  /health   →  verifica se o serviço está no ar.
"""

import logging
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from config import CAMPOS_FIXOS, MONDAY_API_TOKEN
from Modulos.receptor import processar_requisicao
from Modulos.mapeador import mapear
from Modulos.monday_api import criar_item, buscar_usuario_por_email

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

_PERMISSAO_EMAIL = CAMPOS_FIXOS["permissao"]
_PERMISSAO_USER_ID = None


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


@app.post("/incluir", summary="Incluir item na Monday")
async def incluir(request: Request) -> JSONResponse:
    try:
        dados_brutos: Dict[str, Any] = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="JSON inválido ou ausente no corpo da requisição.")

    try:
        dados_normalizados = processar_requisicao(dados_brutos)
        dados_mapeados = mapear(dados_normalizados)
        resultado = criar_item(dados_mapeados, _PERMISSAO_USER_ID)
        logger.info(
            f"Item criado: id={resultado.get('id')} | "
            f"processo={dados_mapeados.get('processo')} | "
            f"tipo={dados_mapeados.get('rpv_prc')}"
        )

        return JSONResponse(
            status_code=201,
            content={
                "sucesso": True,
                "mensagem": "Item criado com sucesso na Monday.",
                "item": resultado,
            },
        )

    except ValueError as e:
        logger.warning(f"Erro de validação: {e}")
        raise HTTPException(status_code=422, detail=str(e))

    except RuntimeError as e:
        logger.error(f"Erro na API Monday: {e}")
        raise HTTPException(status_code=502, detail=str(e))

    except Exception as e:
        logger.exception("Erro inesperado")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


@app.get("/health", summary="Verificar status da aplicação")
def health() -> Dict[str, str]:
    return {"status": "ok"}
