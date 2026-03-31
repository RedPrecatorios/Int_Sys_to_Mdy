"""
Identifica o tipo de template recebido na requisição.

Regra de identificação:
- PRC-TJSP   → possui o campo 'Numero_do_Incidente' (ou variações)
- Cumprimento → possui o campo 'numero_do_cumprimento' (ou variações)
  e NÃO possui campo de incidente
"""

from typing import Dict, Any

TIPO_PRC      = "PRC-TJSP"
TIPO_CUMPRIM  = "Cumprimento"

# Chaves que identificam cada template (busca case-insensitive)
_CHAVES_PRC = {
    "numero_do_incidente",
    "numero do incidente",
    "incidente",
}

_CHAVES_CUMPRIM = {
    "numero_do_cumprimento",
    "numero do cumprimento",
}


def identificar_template(dados: Dict[str, Any]) -> str:
    """
    Recebe o dicionário bruto da requisição e retorna o tipo de template.

    Returns:
        "PRC-TJSP" | "Cumprimento"

    Raises:
        ValueError: se o template não puder ser identificado.
    """
    chaves_lower = {k.lower().strip() for k in dados.keys()}

    if chaves_lower & _CHAVES_CUMPRIM:
        return TIPO_CUMPRIM

    if chaves_lower & _CHAVES_PRC:
        return TIPO_PRC

    raise ValueError(
        "Não foi possível identificar o template dos dados recebidos. "
        "Verifique se os campos 'Numero_do_Incidente' (PRC-TJSP) ou "
        "'numero_do_cumprimento' (Cumprimento) estão presentes."
    )
