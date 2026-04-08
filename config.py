import os
import ipaddress
from typing import List
from dotenv import load_dotenv

load_dotenv()

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

CAMPOS_FIXOS = {
    "subelementos": "",
    "etapa": "Aguardando Atualização",
    "permissao": os.getenv("PERMISSAO", "aline.chaves@redprecatorios.com.br"),
}
