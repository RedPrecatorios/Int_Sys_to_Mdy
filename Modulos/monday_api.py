"""
Integração com a API GraphQL da Monday.com.

Responsabilidades:
  - Buscar colunas do board
  - Buscar usuários por e-mail
  - Criar itens no board com formatação correta por tipo de coluna
"""

import json
import re
import requests
from typing import Any, Dict, List, Optional

from config import MONDAY_API_TOKEN, MONDAY_BOARD_ID, MONDAY_API_URL


def _coluna_id_para_campo_interno(column_id: str) -> Optional[str]:
    for campo, cfg in COLUNAS_CONFIG.items():
        if cfg.get("id") == column_id:
            return campo
    return None


def _extrair_label_status(column_value: Any) -> str:
    """Tenta obter o label enviado a partir do valor bruto da Monday (string JSON ou objeto)."""
    if column_value is None:
        return ""
    s = column_value if isinstance(column_value, str) else json.dumps(column_value, ensure_ascii=False)
    s = s.strip()
    if not s:
        return ""
    try:
        obj = json.loads(s)
        if isinstance(obj, dict) and "label" in obj:
            return str(obj.get("label") or "")
    except json.JSONDecodeError:
        pass
    m = re.search(r'"label"\s*=>\s*"([^"]*)"', s)
    if m:
        return m.group(1)
    m = re.search(r'"label"\s*:\s*"([^"]*)"', s)
    if m:
        return m.group(1)
    return s[:200]


def _formatar_erros_graphql_monday(errors: List[Any]) -> str:
    """
    Monta mensagem legível a partir de errors[] da Monday (ex.: label de status inexistente).
    """
    if not isinstance(errors, list) or not errors:
        return str(errors)

    partes: List[str] = []
    for err in errors:
        if not isinstance(err, dict):
            partes.append(str(err))
            continue

        msg = err.get("message") or ""
        ext = err.get("extensions") or {}
        ed = ext.get("error_data") or {}
        if not isinstance(ed, dict):
            partes.append(msg or str(err))
            continue

        col_name = ed.get("column_name") or "?"
        col_id = ed.get("column_id") or "?"
        col_type = ed.get("column_type") or ""
        col_val = ed.get("column_value")
        codigo = ed.get("column_validation_error_code") or ""

        campo_interno = _coluna_id_para_campo_interno(str(col_id)) if col_id else None
        label = _extrair_label_status(col_val)

        trecho = (
            f'Coluna Monday "{col_name}" (column_id={col_id}'
            f'{f", tipo={col_type}" if col_type else ""}'
            f'{f", campo interno={campo_interno!r}" if campo_interno else ""})'
        )
        if codigo:
            trecho += f" código={codigo}"
        if label or col_val is not None:
            trecho += f' — valor/label enviado: {label or repr(col_val)}'
        if msg and msg not in trecho:
            trecho += f" — {msg}"

        partes.append(trecho)

    return " | ".join(partes) if partes else str(errors)


def _headers() -> Dict[str, str]:
    token = MONDAY_API_TOKEN or ""
    return {
        "Authorization": token,
        "Content-Type":  "application/json",
        "API-Version":   "2024-01",
    }


def _executar_query(query: str, variables: Dict = None) -> Dict[str, Any]:
    if not MONDAY_API_TOKEN or not str(MONDAY_API_TOKEN).strip():
        raise RuntimeError("MONDAY_API_TOKEN não configurado. Defina no .env na máquina Ubuntu.")

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
        erros = resultado["errors"]
        resumo = _formatar_erros_graphql_monday(erros) if isinstance(erros, list) else str(erros)
        raise RuntimeError(f"Erro na API Monday: {resumo}")

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
    query ($emails: [String!]) {
      users(emails: $emails) {
        id
        email
      }
    }
    """
    data = _executar_query(query, {"emails": [email]})
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
