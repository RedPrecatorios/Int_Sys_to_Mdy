import ipaddress
import json
import os
from typing import Dict, List
from dotenv import load_dotenv

# Carrega .env de forma robusta (evita depender do "cwd" e de introspecção de stack)
_ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=_ENV_PATH)

# None ou string vazia se não definido (útil para aviso no arranque em cloud)
_raw_token = os.getenv("MONDAY_API_TOKEN")
MONDAY_API_TOKEN = _raw_token if _raw_token and str(_raw_token).strip() else None
MONDAY_BOARD_ID = int(os.getenv("MONDAY_BOARD_ID", "7345244366"))
MONDAY_API_URL = os.getenv("MONDAY_API_URL", "https://api.monday.com/v2")

TRUST_PROXY = os.getenv("TRUST_PROXY", "false").strip().lower() in {"1", "true", "yes", "y", "on"}


def _parse_allowed_ips(raw: str) -> List[str]:
    """
    Lista de IPs/CIDRs permitidos (ex.: "1.2.3.4, 10.0.0.0/24").
    Retorna lista vazia quando não configurado (não bloqueia).
    """
    if not raw or not raw.strip():
        return []
    partes = [p.strip() for p in raw.split(",")]
    itens = [p for p in partes if p]
    # valida apenas; o match é feito em main.py
    for item in itens:
        ipaddress.ip_network(item, strict=False)
    return itens


ALLOWED_SOURCE_IPS = _parse_allowed_ips(os.getenv("ALLOWED_SOURCE_IPS", ""))

# Template ligação: coluna Monday RPV/PRC só aceita labels fixos (ex.: PRC-TJSP).
# Se vazio, não envia valor nessa coluna (evita erro com user_tipo tipo "Operador").
_raw_ligacao_rpv = os.getenv("LIGACAO_MONDAY_RPV_PRC", "")
LIGACAO_MONDAY_RPV_PRC = _raw_ligacao_rpv.strip() if _raw_ligacao_rpv and str(_raw_ligacao_rpv).strip() else ""

# Coluna Monday "Comprador" (status): tem de ser um *label* existente no board, não o código user_agente.
# - user_nome (default): envia o nome do operador (ex.: "Jessica Silva") — típico para status de pessoa.
# - user_agente: envia o código (só use se a Monday tiver labels iguais aos códigos).
_raw_ligacao_comp = os.getenv("LIGACAO_MONDAY_COMPRADOR_CAMPO", "user_nome").strip().lower()
LIGACAO_MONDAY_COMPRADOR_CAMPO = _raw_ligacao_comp if _raw_ligacao_comp in {"user_nome", "user_agente"} else "user_nome"

# Opcional: JSON {"00805":"Jessica Silva","00788":"Karina Aparecida"} — tem prioridade sobre COMPRADOR_CAMPO.
_raw_ligacao_map = os.getenv("LIGACAO_MONDAY_COMPRADOR_MAP_JSON", "").strip()
LIGACAO_MONDAY_COMPRADOR_MAP: Dict[str, str] = {}
if _raw_ligacao_map:
    try:
        obj = json.loads(_raw_ligacao_map)
        if isinstance(obj, dict):
            LIGACAO_MONDAY_COMPRADOR_MAP = {str(k).strip(): str(v).strip() for k, v in obj.items() if str(v).strip()}
    except json.JSONDecodeError:
        LIGACAO_MONDAY_COMPRADOR_MAP = {}

# Template ligação → coluna Monday "Status Compras": um único label para todos os itens criados por esta API
# (ligacao_acionamento só define se envia à Monday, não o texto da coluna).
_raw_status_lig = os.getenv("LIGACAO_MONDAY_STATUS_COMPRAS_LIGACAO", "Inclusão - SysCALL")
LIGACAO_MONDAY_STATUS_COMPRAS_LIGACAO = (
    str(_raw_status_lig).strip() if str(_raw_status_lig).strip() else "Inclusão - SysCALL"
)

CAMPOS_FIXOS = {
    "subelementos": "",
    "etapa": "Aguardando Atualização",
    "permissao": os.getenv("PERMISSAO", "aline.chaves@redprecatorios.com.br"),
}
