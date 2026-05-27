"""
Mapeia os dados brutos recebidos na requisição para o formato
padronizado que será enviado à Monday.com.

Campos de saída (Monday):
    processo, subelementos, incidente, rpv_prc, requerente,
    comprador, status_compras, etapa, telefone,
    observacoes_compras, permissao
"""

from typing import Dict, Any
from config import (
    CAMPOS_FIXOS,
    LIGACAO_MONDAY_COMPRADOR_CAMPO,
    LIGACAO_MONDAY_COMPRADOR_MAP,
    LIGACAO_MONDAY_RPV_PRC,
    LIGACAO_MONDAY_STATUS_COMPRAS_LIGACAO,
)
from Modulos.custom_data import parse_custom_data_kv, valor_numero_cumprimento
from Modulos.identificador import (
    TIPO_PRC,
    TIPO_CUMPRIM,
    TIPO_EXTERNO,
    TIPO_LIGACAO,
    identificar_template,
)


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


def _custom_data_kv(dados: Dict[str, Any]) -> Dict[str, str]:
    return parse_custom_data_kv(dados)


def _comprador_ligacao(dados: Dict[str, Any]) -> str:
    agente = str(_get(dados, "user_agente") or "").strip()
    nome = str(_get(dados, "user_nome") or "").strip()
    if agente and LIGACAO_MONDAY_COMPRADOR_MAP.get(agente):
        return LIGACAO_MONDAY_COMPRADOR_MAP[agente]
    if LIGACAO_MONDAY_COMPRADOR_CAMPO == "user_agente":
        return agente
    return nome


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


def mapear_ligacao(dados: Dict[str, Any]) -> Dict[str, Any]:
    """
    Payload de integração (user_*, ligacao_*): operador + dados da ligação.

    A coluna Monday "Comprador" (status) só aceita *labels* já criados no board.
    Por omissão usa user_nome; código user_agente vai nas observações.
    Configure LIGACAO_MONDAY_COMPRADOR_CAMPO / LIGACAO_MONDAY_COMPRADOR_MAP_JSON no .env.

    A coluna "Status Compras" na Monday usa sempre o label configurado (por omissão
    "Inclusão - SysCALL"; ver LIGACAO_MONDAY_STATUS_COMPRAS_LIGACAO no .env).

    Nome do item (processo), incidente, requerente e telefone vêm do custom_data quando presentes
    (Processo, Numero do Incidente, Nome, Telefone). Observações de compras: só ligacao_observacao
    (vazio se não houver texto no SysCALL).
    """
    obs_lig = _get(dados, "ligacao_observacao")
    ligacao_id = str(_get(dados, "ligacao_id") or "").strip()

    kv = _custom_data_kv(dados)
    processo_monday = (
        (kv.get("processo") or kv.get("processo_principal") or "").strip() or ligacao_id
    )
    incidente_monday = (kv.get("numero do incidente") or kv.get("número do incidente") or "").strip()
    requerente_monday = (kv.get("nome") or "").strip()
    telefone_monday = (kv.get("telefone") or "").strip()

    obs = str(obs_lig).strip()

    return {
        "processo": processo_monday,
        "subelementos": CAMPOS_FIXOS["subelementos"],
        "incidente": incidente_monday,
        "rpv_prc": LIGACAO_MONDAY_RPV_PRC,
        "requerente": requerente_monday,
        "comprador": str(_comprador_ligacao(dados)),
        "status_compras": str(LIGACAO_MONDAY_STATUS_COMPRAS_LIGACAO),
        "etapa": CAMPOS_FIXOS["etapa"],
        "telefone": telefone_monday,
        "observacoes_compras": obs,
        "permissao": CAMPOS_FIXOS["permissao"],
    }


def mapear_cumprimento(dados: Dict[str, Any]) -> Dict[str, Any]:
    """
    Cumprimento «plano» (campos no topo) ou via template ligação + custom_data
    (Numero do cumprimento, Requerente, Telefone no JSON custom_data).
    """
    kv = _custom_data_kv(dados)
    ligacao_id = str(_get(dados, "ligacao_id") or "").strip()
    via_ligacao = bool(ligacao_id or _get(dados, "ligacao_acionamento"))

    processo = valor_numero_cumprimento(dados) or str(_get(dados, "numero_do_cumprimento") or "").strip()
    if not processo:
        processo = ligacao_id

    requerente = (kv.get("requerente") or str(_get(dados, "requerente", "nome") or "")).strip()
    telefone = (kv.get("telefone") or str(_get(dados, "contato", "telefone", "tell_1") or "")).strip()

    if via_ligacao:
        comprador = _comprador_ligacao(dados)
        status_compras = str(LIGACAO_MONDAY_STATUS_COMPRAS_LIGACAO)
        obs = str(_get(dados, "ligacao_observacao") or "").strip()
    else:
        comprador = str(_get(dados, "comprador") or "")
        status_compras = str(_get(dados, "status_compras", "status compras") or "")
        obs = str(_get(dados, "observacoes_compras", "observacoes", "obs") or "").strip()

    return {
        "processo": processo,
        "subelementos": CAMPOS_FIXOS["subelementos"],
        "incidente": "",
        "rpv_prc": TIPO_CUMPRIM,
        "requerente": requerente,
        "comprador": comprador,
        "status_compras": status_compras,
        "etapa": CAMPOS_FIXOS["etapa"],
        "telefone": telefone,
        "observacoes_compras": obs,
        "permissao": CAMPOS_FIXOS["permissao"],
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
    if tipo == TIPO_LIGACAO:
        return mapear_ligacao(dados)
    raise ValueError(f"Template não suportado: {tipo}")
