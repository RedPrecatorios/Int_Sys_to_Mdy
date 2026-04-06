"""
Identifica o tipo de template recebido na requisição.

Regra de identificação:
- Cumprimento → possui o campo 'numero_do_cumprimento' (ou variações)
- Externo     → payload com ID, agente, nome, usuário (ou usuario), email, tipo, status
- PRC-TJSP    → possui o campo 'Numero_do_Incidente' (ou variações)
"""

from typing import Dict, Any, Set

TIPO_PRC = "PRC-TJSP"
TIPO_CUMPRIM = "Cumprimento"
TIPO_EXTERNO = "externo"

_CHAVES_PRC = {
    "numero_do_incidente",
    "numero do incidente",
    "incidente",
}

_CHAVES_CUMPRIM = {
    "numero_do_cumprimento",
    "numero do cumprimento",
}

_OBRIGATORIOS_EXTERNO = {"id", "agente", "nome", "email", "tipo", "status"}


def _chaves_template_externo(chaves: Set[str]) -> bool:
    if not _OBRIGATORIOS_EXTERNO <= chaves:
        return False
    return "usuario" in chaves or "usuário" in chaves


def identificar_template(dados: Dict[str, Any]) -> str:
    """
    Espera chaves já normalizadas (receptor: minúsculas, espaços → _).

    Returns:
        "PRC-TJSP" | "Cumprimento" | "externo"

    Raises:
        ValueError: se o template não puder ser identificado.
    """
    chaves = set(dados.keys())

    if chaves & _CHAVES_CUMPRIM:
        return TIPO_CUMPRIM

    if _chaves_template_externo(chaves):
        return TIPO_EXTERNO

    chaves_lower = {k.lower().strip() for k in dados.keys()}
    if chaves_lower & _CHAVES_PRC:
        return TIPO_PRC

    raise ValueError(
        "Não foi possível identificar o template dos dados recebidos. "
        "Use PRC-TJSP, Cumprimento, ou o conjunto ID/agente/nome/usuário/email/tipo/status."
    )
