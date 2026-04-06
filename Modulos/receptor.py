"""
Recebe, valida e pré-processa os dados brutos da requisição
antes de encaminhá-los ao mapeador.
"""

from typing import Any, Dict


# Campos obrigatórios mínimos (ao menos um de cada grupo deve estar presente)
_CAMPOS_OBRIGATORIOS_PRC = {"nome", "processo", "tell_1", "tell1", "telefone"}
_CAMPOS_OBRIGATORIOS_CUMPRIM = {"requerente", "numero_do_cumprimento", "contato", "telefone"}
_OBRIGATORIOS_EXTERNO = {"id", "agente", "nome", "email", "tipo", "status"}


def _normalizar_chaves(dados: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normaliza as chaves do dicionário:
    - Remove espaços no início/fim
    - Converte para minúsculas
    - Substitui espaços internos por underscore
    """
    return {
        k.strip().lower().replace(" ", "_"): v
        for k, v in dados.items()
    }


def _validar_nao_vazio(dados: Dict[str, Any]) -> None:
    if not dados:
        raise ValueError("O corpo da requisição está vazio.")


def _campo_externo_vazio(val: Any) -> bool:
    if val is None:
        return True
    if isinstance(val, str) and not val.strip():
        return True
    return False


def _validar_template_externo(dados_norm: Dict[str, Any]) -> None:
    if not ("usuario" in dados_norm or "usuário" in dados_norm):
        raise ValueError(
            "Payload externo incompleto: falta o campo 'usuario' ou 'usuário'."
        )
    for k in _OBRIGATORIOS_EXTERNO:
        if _campo_externo_vazio(dados_norm.get(k)):
            raise ValueError(f"O campo '{k}' não pode estar vazio no payload externo.")
    uk = "usuario" if "usuario" in dados_norm else "usuário"
    if _campo_externo_vazio(dados_norm.get(uk)):
        raise ValueError(f"O campo '{uk}' não pode estar vazio no payload externo.")


def _validar_campos_minimos(dados_norm: Dict[str, Any]) -> None:
    chaves = set(dados_norm.keys())

    if _OBRIGATORIOS_EXTERNO <= chaves and ("usuario" in chaves or "usuário" in chaves):
        _validar_template_externo(dados_norm)
        return

    tem_prc = bool(chaves & _CAMPOS_OBRIGATORIOS_PRC)
    tem_cumprim = bool(chaves & _CAMPOS_OBRIGATORIOS_CUMPRIM)

    if not (tem_prc or tem_cumprim):
        raise ValueError(
            "Dados insuficientes. Certifique-se de que a requisição contém "
            "os campos necessários para PRC-TJSP, Cumprimento ou o template externo (ID, agente, …)."
        )


def processar_requisicao(dados_brutos: Dict[str, Any]) -> Dict[str, Any]:
    """
    Valida e normaliza os dados brutos recebidos.

    Returns:
        Dicionário com chaves normalizadas, pronto para o mapeador.

    Raises:
        ValueError: se os dados forem inválidos ou incompletos.
    """
    _validar_nao_vazio(dados_brutos)
    dados_norm = _normalizar_chaves(dados_brutos)
    _validar_campos_minimos(dados_norm)
    return dados_norm
