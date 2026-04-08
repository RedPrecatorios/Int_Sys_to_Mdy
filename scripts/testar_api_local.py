"""
Teste rápido (local) da API Int_Sys_to_Mdy.

O que valida:
  1) GET /health
  2) POST /incluir com payloads de exemplo (externo / PRC / Cumprimento)

Uso:
  python scripts/testar_api_local.py
  python scripts/testar_api_local.py --base-url http://127.0.0.1:8000
  python scripts/testar_api_local.py --somente health
  python scripts/testar_api_local.py --somente incluir
  python scripts/testar_api_local.py --template externo
  python scripts/testar_api_local.py --template prc
  python scripts/testar_api_local.py --template cumprimento
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, Literal, Optional

try:
    import requests
except ImportError:
    print("Instale requests: pip install requests", file=sys.stderr)
    raise

Template = Literal["externo", "prc", "cumprimento"]


def _print_json(data: Any, pretty: bool) -> None:
    indent = 2 if pretty else None
    print(json.dumps(data, ensure_ascii=False, indent=indent))


def payload_externo() -> Dict[str, Any]:
    return {
        "ID": "0022451-54.2023.8.26.0053",
        "agente": "TESTE RED",
        "nome": "PEDRO LUIZ GALRAO DE FRANCA",
        "usuário": "pgalrao",
        "email": "pedro.exemplo@empresa.com.br",
        "tipo": "PRC-TJSP",
        "status": "Incluir na carteira",
    }


def payload_prc() -> Dict[str, Any]:
    return {
        "processo": "0022451-54.2023.8.26.0053",
        "numero_do_incidente": "12345",
        "nome": "FULANO DE TAL",
        "tell_1": "11999990000",
        "comprador": "TESTE RED",
        "status_compras": "Incluir na carteira",
        "observacoes": "Payload PRC de teste",
    }


def payload_cumprimento() -> Dict[str, Any]:
    return {
        "numero_do_cumprimento": "0001234-56.2026.8.26.0000",
        "requerente": "FULANA DE TAL",
        "contato": "11999990000",
        "status_compras": "Incluir na carteira",
        "observacoes": "Payload Cumprimento de teste",
    }


def _post_incluir(url: str, body: Dict[str, Any], timeout_s: int, pretty: bool) -> bool:
    print(f"POST {url}")
    print("Corpo (JSON):")
    _print_json(body, pretty=True)
    print()
    try:
        r = requests.post(
            url,
            json=body,
            headers={"Content-Type": "application/json"},
            timeout=timeout_s,
        )
    except requests.RequestException as e:
        print("Erro de rede:", e, file=sys.stderr)
        return False

    print("HTTP", r.status_code)
    try:
        _print_json(r.json(), pretty=pretty)
    except Exception:
        print(r.text)

    return bool(r.ok)


def _get_health(url: str, timeout_s: int, pretty: bool) -> bool:
    print(f"GET {url}")
    try:
        r = requests.get(url, timeout=timeout_s)
    except requests.RequestException as e:
        print("Erro de rede:", e, file=sys.stderr)
        return False

    print("HTTP", r.status_code)
    try:
        _print_json(r.json(), pretty=pretty)
    except Exception:
        print(r.text)
    return bool(r.ok)


def _resolver_payload(template: Template) -> Dict[str, Any]:
    if template == "externo":
        return payload_externo()
    if template == "prc":
        return payload_prc()
    if template == "cumprimento":
        return payload_cumprimento()
    raise ValueError(f"Template inválido: {template}")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Testa /health e /incluir (Int_Sys_to_Mdy)")
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Base URL do servidor (ex.: http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Timeout em segundos para as requisições",
    )
    parser.add_argument(
        "--sem-pretty",
        action="store_true",
        help="Saída JSON sem indentação",
    )
    parser.add_argument(
        "--somente",
        choices=["health", "incluir"],
        default=None,
        help="Executa apenas um dos checks",
    )
    parser.add_argument(
        "--template",
        choices=["externo", "prc", "cumprimento"],
        default="externo",
        help="Template usado no POST /incluir",
    )

    args = parser.parse_args(argv)
    pretty = not args.sem_pretty

    health_url = f"{args.base_url.rstrip('/')}/health"
    incluir_url = f"{args.base_url.rstrip('/')}/incluir"

    ok = True
    if args.somente in (None, "health"):
        ok = _get_health(health_url, timeout_s=args.timeout, pretty=pretty) and ok
        print()

    if args.somente in (None, "incluir"):
        body = _resolver_payload(args.template)  # type: ignore[arg-type]
        ok = _post_incluir(incluir_url, body=body, timeout_s=args.timeout, pretty=pretty) and ok

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

