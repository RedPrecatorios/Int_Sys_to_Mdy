"""
Identifica o tipo de template recebido na requisição.

Regra de identificação:
- Cumprimento → 'numero_do_cumprimento' no topo ou em custom_data (template ligação)
- Ligação     → user_* e ligacao_* sem número de cumprimento no custom_data (PRC-TJSP)
- Externo     → payload com ID, agente, nome, usuário (ou usuario), email, tipo, status
- PRC-TJSP    → possui o campo 'Numero_do_Incidente' (ou variações)
"""

from typing import Dict, Any, Set

from Modulos.custom_data import tem_numero_cumprimento

TIPO_PRC = "PRC-TJSP"
TIPO_CUMPRIM = "Cumprimento"
TIPO_EXTERNO = "externo"
TIPO_LIGACAO = "ligacao"

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

# Chaves mínimas para reconhecer template ligação (ligacao_observacao é opcional).
_CHAVES_MINIMAS_LIGACAO = {
    "user_id",
    "user_agente",
    "user_nome",
    "user_usuario",
    "user_email",
    "user_tipo",
    "ligacao_id",
    "ligacao_status",
    "ligacao_acionamento",
}


def _chaves_template_ligacao(chaves: Set[str]) -> bool:
    return _CHAVES_MINIMAS_LIGACAO <= chaves


def _chaves_template_externo(chaves: Set[str]) -> bool:
    if not _OBRIGATORIOS_EXTERNO <= chaves:
        return False
    return "usuario" in chaves or "usuário" in chaves


def identificar_template(dados: Dict[str, Any]) -> str:
    """
    Espera chaves já normalizadas (receptor: minúsculas, espaços → _).

    Returns:
        "PRC-TJSP" | "Cumprimento" | "externo" | "ligacao"

    Raises:
        ValueError: se o template não puder ser identificado.
    """
    chaves = set(dados.keys())

    # Cumprimento no topo ou dentro de custom_data (template ligação + SysCALL).
    if chaves & _CHAVES_CUMPRIM or tem_numero_cumprimento(dados):
        return TIPO_CUMPRIM

    if _chaves_template_ligacao(chaves):
        return TIPO_LIGACAO

    if _chaves_template_externo(chaves):
        return TIPO_EXTERNO

    chaves_lower = {k.lower().strip() for k in dados.keys()}
    if chaves_lower & _CHAVES_PRC:
        return TIPO_PRC

    raise ValueError(
        "Não foi possível identificar o template dos dados recebidos. "
        "Use PRC-TJSP, Cumprimento, template externo (ID/agente/…), "
        "ou template de ligação (user_*, ligacao_*)."
    )
