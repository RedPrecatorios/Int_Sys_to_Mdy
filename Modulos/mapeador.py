"""
Mapeia os dados brutos recebidos na requisição para o formato
padronizado que será enviado à Monday.com.

Campos de saída (Monday):
    processo, subelementos, incidente, rpv_prc, requerente,
    comprador, status_compras, etapa, telefone,
    observacoes_compras, permissao
"""

from typing import Dict, Any
from config import CAMPOS_FIXOS
from Modulos.identificador import TIPO_PRC, TIPO_CUMPRIM, TIPO_EXTERNO, identificar_template


def _get(dados: Dict[str, Any], *chaves: str, default: Any = "") -> Any:
    """Busca case-insensitive e insensível a espaços/underscores."""
    dados_norm = {
        k.lower().strip().replace(" ", "_"): v
        for k, v in dados.items()
    }
    for chave in chaves:
        valor = dados_norm.get(chave.lower().strip().replace(" ", "_"))
        if valor is not None:
            return valor
    return default


def mapear_prc_tjsp(dados: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "processo":           _get(dados, "processo", "processo_principal"),
        "subelementos":       CAMPOS_FIXOS["subelementos"],
        "incidente":          _get(dados, "numero_do_incidente", "incidente"),
        "rpv_prc":            TIPO_PRC,
        "requerente":         _get(dados, "nome", "requerente"),
        "comprador":          _get(dados, "comprador"),
        "status_compras":     _get(dados, "status_compras", "status compras"),
        "etapa":              CAMPOS_FIXOS["etapa"],
        "telefone":           _get(dados, "tell_1", "tell1", "telefone", "contato"),
        "observacoes_compras": _get(dados, "observacoes_compras", "observacoes", "obs"),
        "permissao":          CAMPOS_FIXOS["permissao"],
    }


def mapear_externo(dados: Dict[str, Any]) -> Dict[str, Any]:
    """
    Payload simulado da plataforma externa: ID, agente, nome, usuario/usuário, email, tipo, status.
    """
    usuario = _get(dados, "usuario", "usuário")
    email = _get(dados, "email")
    obs = f"Usuário: {usuario} | E-mail: {email}".strip()

    return {
        "processo": str(_get(dados, "id")),
        "subelementos": CAMPOS_FIXOS["subelementos"],
        "incidente": "",
        "rpv_prc": str(_get(dados, "tipo")),
        "requerente": str(_get(dados, "nome")),
        "comprador": str(_get(dados, "agente")),
        "status_compras": str(_get(dados, "status")),
        "etapa": CAMPOS_FIXOS["etapa"],
        "telefone": "",
        "observacoes_compras": obs,
        "permissao": CAMPOS_FIXOS["permissao"],
    }


def mapear_cumprimento(dados: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "processo":           _get(dados, "numero_do_cumprimento"),
        "subelementos":       CAMPOS_FIXOS["subelementos"],
        "incidente":          "",
        "rpv_prc":            TIPO_CUMPRIM,
        "requerente":         _get(dados, "requerente", "nome"),
        "comprador":          _get(dados, "comprador"),
        "status_compras":     _get(dados, "status_compras", "status compras"),
        "etapa":              CAMPOS_FIXOS["etapa"],
        "telefone":           _get(dados, "contato", "telefone", "tell_1"),
        "observacoes_compras": _get(dados, "observacoes_compras", "observacoes", "obs"),
        "permissao":          CAMPOS_FIXOS["permissao"],
    }


def mapear(dados: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ponto de entrada do mapeador.
    Identifica o template e retorna os dados no formato Monday.
    """
    tipo = identificar_template(dados)

    if tipo == TIPO_PRC:
        return mapear_prc_tjsp(dados)
    if tipo == TIPO_CUMPRIM:
        return mapear_cumprimento(dados)
    if tipo == TIPO_EXTERNO:
        return mapear_externo(dados)
    raise ValueError(f"Template não suportado: {tipo}")
