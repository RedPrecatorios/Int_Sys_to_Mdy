"""
Mapeamento dos campos para o board SMS da Monday.

Campos gerados:
  - contato  : "55" + número de telefone
  - nome     : nome formatado (primeiro + iniciais do meio + último)
  - processo : mesmo valor do campo processo
"""

from typing import Dict, Any
from Modulos.formatador_nome import formatar_nome_sms


def _formatar_contato(telefone: str) -> str:
    """Prepend '55' ao número, removendo caracteres não numéricos."""
    numero_limpo = "".join(c for c in str(telefone) if c.isdigit())
    if not numero_limpo:
        return ""
    return f"55{numero_limpo}"


def mapear_sms(dados_mapeados: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recebe os dados já mapeados (saída do mapeador principal)
    e retorna os 3 campos do board SMS.

    Args:
        dados_mapeados: dicionário com campos internos normalizados

    Returns:
        {
            "contato":  "55<telefone>",
            "nome":     "Primeiro I. I. Ultimo",
            "processo": "<numero_do_processo>",
        }
    """
    return {
        "contato":  _formatar_contato(dados_mapeados.get("telefone", "")),
        "nome":     formatar_nome_sms(dados_mapeados.get("requerente", "")),
        "processo": dados_mapeados.get("processo", ""),
    }
