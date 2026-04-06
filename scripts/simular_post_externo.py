"""
Simula uma requisição POST externa para POST /incluir (FastAPI).

Campos enviados (exemplo):
  ID, agente, nome, usuário, email, tipo, status

Uso:
  1) Subir a API:  uvicorn main:app --reload
  2) Executar:     python scripts/simular_post_externo.py

Opções:
  --url URL completa (default: http://127.0.0.1:8000/incluir).
  Na cloud Ubuntu use:  python scripts/simular_post_externo.py --url http://IP_DA_VM:8000/incluir
  --sem-pretty     saída JSON numa linha
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict

try:
    import requests
except ImportError:
    print("Instale requests: pip install requests", file=sys.stderr)
    sys.exit(1)


def payload_exemplo() -> Dict[str, Any]:
    """
    Valores de demonstração. Ajuste `tipo` e `status` para bater com os
    labels das colunas status da Monday (RPV/PRC e Status Compras).
    """
    return {
        "ID": "0022451-54.2023.8.26.0053",
        "agente": "TESTE RED",
        "nome": "PEDRO LUIZ GALRAO DE FRANCA",
        "usuário": "pgalrao",
        "email": "pedro.exemplo@empresa.com.br",
        "tipo": "PRC-TJSP",
        "status": "Incluir na carteira",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Simula POST externo para /incluir")
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8000/incluir",
        help="URL do endpoint POST /incluir",
    )
    parser.add_argument(
        "--sem-pretty",
        action="store_true",
        help="Resposta JSON sem indentação",
    )
    args = parser.parse_args()

    body = payload_exemplo()

    print("Enviando POST para:", args.url)
    print("Corpo (JSON):\n", json.dumps(body, ensure_ascii=False, indent=2))
    print()

    try:
        r = requests.post(
            args.url,
            json=body,
            headers={"Content-Type": "application/json"},
            timeout=60,
        )
    except requests.RequestException as e:
        print("Erro de rede:", e, file=sys.stderr)
        sys.exit(1)

    print("HTTP", r.status_code)
    try:
        data = r.json()
        indent = None if args.sem_pretty else 2
        print(json.dumps(data, ensure_ascii=False, indent=indent))
    except Exception:
        print(r.text)

    sys.exit(0 if r.ok else 1)


if __name__ == "__main__":
    main()
