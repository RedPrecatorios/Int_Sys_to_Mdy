"""
Formato de entrada: o cliente pode enviar o payload «plano» (campos de negócio)
ou um envelope com metadados + payload interno:

  {"received_at": "...", "client_ip": "...", "payload": { ... }}

Neste caso apenas `payload` é validado/mapeado; o corpo completo continua
a ser auditado (ficheiro/MySQL) como recebido.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

# Template ligação: só estes acionamentos geram item na Monday.
LIGACAO_ACIONAMENTO_ENVIA_MONDAY = frozenset(
    {
        "Inclusão Monday",
        "Inclusão Pré Cálculo",
    }
)


def eh_envelope_com_payload(body: Dict[str, Any]) -> bool:
    if not isinstance(body, dict):
        return False
    inner = body.get("payload")
    if not isinstance(inner, dict):
        return False
    return "received_at" in body or "client_ip" in body


def extrair_payload_negocio(body: Dict[str, Any]) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    """
    Returns:
        (dados_para_processar, envelope_ou_none)
    """
    if eh_envelope_com_payload(body):
        return body["payload"], body
    return body, None
