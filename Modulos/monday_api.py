"""
Integração com a API GraphQL da Monday.com.

Responsabilidades:
  - Buscar colunas do board
  - Buscar usuários por e-mail
  - Criar itens no board com formatação correta por tipo de coluna
"""

import json
import requests
from typing import Dict, Any, List, Optional

from config import MONDAY_API_TOKEN, MONDAY_BOARD_ID, MONDAY_API_URL, MONDAY_SMS_BOARD_ID


def _headers() -> Dict[str, str]:
    return {
        "Authorization": MONDAY_API_TOKEN,
        "Content-Type":  "application/json",
        "API-Version":   "2024-01",
    }


def _executar_query(query: str, variables: Dict = None) -> Dict[str, Any]:
    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    response = requests.post(
        MONDAY_API_URL,
        headers=_headers(),
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    resultado = response.json()

    if "errors" in resultado:
        raise RuntimeError(f"Erro na API Monday: {resultado['errors']}")

    return resultado.get("data", {})


# ---------------------------------------------------------------------------
# Utilitário: listar colunas do board
# ---------------------------------------------------------------------------

def buscar_colunas() -> List[Dict[str, str]]:
    query = """
    query ($board_id: ID!) {
      boards(ids: [$board_id]) {
        columns {
          id
          title
          type
        }
      }
    }
    """
    data = _executar_query(query, {"board_id": str(MONDAY_BOARD_ID)})
    boards = data.get("boards", [])
    if not boards:
        return []
    return boards[0].get("columns", [])


# ---------------------------------------------------------------------------
# Utilitário: buscar ID de usuário por e-mail
# ---------------------------------------------------------------------------

def buscar_usuario_por_email(email: str) -> Optional[int]:
    """
    Retorna o ID do usuário na Monday pelo e-mail.
    Retorna None se não encontrado.
    """
    query = """
    query ($email: String!) {
      users(email: $email) {
        id
        email
      }
    }
    """
    data = _executar_query(query, {"email": email})
    users = data.get("users", [])
    if users:
        return int(users[0]["id"])
    return None


# ---------------------------------------------------------------------------
# Montagem dos column_values com formatação por tipo
# ---------------------------------------------------------------------------

# Mapeamento: campo interno → (column_id, tipo_monday)
COLUNAS_CONFIG: Dict[str, Dict[str, str]] = {
    "incidente":           {"id": "n_meros",          "tipo": "numbers"},
    "rpv_prc":             {"id": "color_mkvmnp2",    "tipo": "status"},
    "requerente":          {"id": "texto_2",           "tipo": "text"},
    "comprador":           {"id": "status5",           "tipo": "status"},
    "status_compras":      {"id": "status_23",         "tipo": "status"},
    "etapa":               {"id": "status__1",         "tipo": "status"},
    "telefone":            {"id": "texto_curto__1",    "tipo": "text"},
    "observacoes_compras": {"id": "texto_curto7__1",   "tipo": "text"},
    "permissao":           {"id": "pessoas__1",        "tipo": "people"},
}


def _formatar_valor(tipo: str, valor: Any, usuario_id: Optional[int] = None) -> Any:
    """Retorna o valor formatado conforme o tipo de coluna da Monday."""
    if valor == "" or valor is None:
        return None

    if tipo == "text":
        return str(valor)

    if tipo == "numbers":
        try:
            return str(int(valor))
        except (ValueError, TypeError):
            return str(valor)

    if tipo == "status":
        return {"label": str(valor)}

    if tipo == "people":
        if usuario_id:
            return {"personsAndTeams": [{"id": usuario_id, "kind": "person"}]}
        return None

    return str(valor)


def _montar_column_values(
    dados_mapeados: Dict[str, Any],
    usuario_permissao_id: Optional[int] = None,
) -> str:
    """Monta o JSON de column_values para a API da Monday."""
    values: Dict[str, Any] = {}

    for campo, config in COLUNAS_CONFIG.items():
        valor = dados_mapeados.get(campo)
        uid   = usuario_permissao_id if config["tipo"] == "people" else None
        valor_fmt = _formatar_valor(config["tipo"], valor, uid)

        if valor_fmt is not None:
            values[config["id"]] = valor_fmt

    return json.dumps(values, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Criação de item
# ---------------------------------------------------------------------------

def criar_item(
    dados_mapeados: Dict[str, Any],
    usuario_permissao_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Cria um item no board da Monday.

    Args:
        dados_mapeados        : saída do mapeador (campos internos normalizados)
        usuario_permissao_id  : ID Monday do usuário de permissão (campo Permissão)

    Returns:
        Dicionário com id e name do item criado.
    """
    nome_item      = dados_mapeados.get("processo") or "Sem título"
    column_values  = _montar_column_values(dados_mapeados, usuario_permissao_id)

    mutation = """
    mutation ($board_id: ID!, $item_name: String!, $column_values: JSON!) {
      create_item(
        board_id: $board_id
        item_name: $item_name
        column_values: $column_values
      ) {
        id
        name
      }
    }
    """
    variables = {
        "board_id":      str(MONDAY_BOARD_ID),
        "item_name":     nome_item,
        "column_values": column_values,
    }

    data = _executar_query(mutation, variables)
    return data.get("create_item", {})


# ---------------------------------------------------------------------------
# Colunas do board SMS
# Preencher os IDs após executar: python utils/listar_colunas.py --sms
# ---------------------------------------------------------------------------

COLUNAS_SMS_CONFIG: Dict[str, Dict[str, str]] = {
    # "campo_interno": {"id": "id_coluna_monday_sms", "tipo": "text"},
    "contato":  {"id": "PREENCHER", "tipo": "text"},
    "nome":     {"id": "PREENCHER", "tipo": "text"},
    "processo": {"id": "PREENCHER", "tipo": "text"},
}


def criar_item_sms(dados_sms: Dict[str, Any]) -> Dict[str, Any]:
    """
    Cria um item no board SMS da Monday.

    Args:
        dados_sms: saída do sms_mapeador
                   {"contato": "55...", "nome": "...", "processo": "..."}

    Returns:
        Dicionário com id e name do item criado.

    Raises:
        RuntimeError: se MONDAY_SMS_BOARD_ID não estiver configurado no .env
    """
    if not MONDAY_SMS_BOARD_ID:
        raise RuntimeError(
            "MONDAY_SMS_BOARD_ID não configurado no .env. "
            "Informe o ID do board SMS para habilitar esta funcionalidade."
        )

    values: Dict[str, Any] = {}
    for campo, config in COLUNAS_SMS_CONFIG.items():
        if config["id"] == "PREENCHER":
            continue
        valor = dados_sms.get(campo, "")
        if valor:
            values[config["id"]] = str(valor)

    nome_item     = dados_sms.get("processo") or "Sem título"
    column_values = json.dumps(values, ensure_ascii=False)

    mutation = """
    mutation ($board_id: ID!, $item_name: String!, $column_values: JSON!) {
      create_item(
        board_id: $board_id
        item_name: $item_name
        column_values: $column_values
      ) {
        id
        name
      }
    }
    """
    variables = {
        "board_id":      str(MONDAY_SMS_BOARD_ID),
        "item_name":     nome_item,
        "column_values": column_values,
    }

    data = _executar_query(mutation, variables)
    return data.get("create_item", {})
