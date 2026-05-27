"""
Parse do campo custom_data (lista JSON de linhas 'Chave: valor').
Usado na identificação de template e no mapeamento para Monday.
"""

from __future__ import annotations

import json
from typing import Any, Dict


def _get_raw_custom_data(dados: Dict[str, Any]) -> str:
    for key, val in dados.items():
        if str(key).lower().strip().replace(" ", "_") == "custom_data":
            if val is not None and str(val).strip():
                return str(val).strip()
    return ""


def parse_custom_data_kv(dados: Dict[str, Any]) -> Dict[str, str]:
    """
    Retorna dicionário chave_normalizada (minúsculas) → valor (strip).
  """
    out: Dict[str, str] = {}
    s = _get_raw_custom_data(dados)
    if not s:
        return out
    try:
        parsed = json.loads(s)
        if isinstance(parsed, list):
            for item in parsed:
                line = str(item).strip()
                if ":" not in line:
                    continue
                k, v = line.split(":", 1)
                key = k.strip().lower()
                val = v.strip().replace("\\r\\n", " ").replace("\r\n", " ").strip()
                if key and val:
                    out[key] = val
        elif isinstance(parsed, dict):
            for k, v in parsed.items():
                if v is not None and str(v).strip():
                    out[str(k).strip().lower()] = str(v).strip()
    except (json.JSONDecodeError, TypeError):
        pass
    return out


_CHAVES_NUMERO_CUMPRIMENTO = frozenset(
    {
        "numero do cumprimento",
        "número do cumprimento",
        "numero_do_cumprimento",
    }
)


def tem_numero_cumprimento(dados: Dict[str, Any]) -> bool:
    """True se o payload (topo ou custom_data) indica caso de cumprimento."""
    for key in dados:
        kn = str(key).lower().strip().replace(" ", "_")
        if kn == "numero_do_cumprimento":
            return True
    kv = parse_custom_data_kv(dados)
    return bool(_CHAVES_NUMERO_CUMPRIMENTO & set(kv.keys()))


def valor_numero_cumprimento(dados: Dict[str, Any]) -> str:
    kv = parse_custom_data_kv(dados)
    for k in _CHAVES_NUMERO_CUMPRIMENTO:
        if kv.get(k):
            return kv[k].strip()
    for key in ("numero_do_cumprimento", "numero do cumprimento"):
        v = dados.get(key)
        if v is not None and str(v).strip():
            return str(v).strip()
    return ""
