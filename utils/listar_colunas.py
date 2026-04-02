"""
Utilitário: lista as colunas do board Monday e exibe seus IDs.

Execução:
    python utils/listar_colunas.py           → board principal (Inclusões)
    python utils/listar_colunas.py --sms     → board SMS
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from Modulos.monday_api import buscar_colunas, _executar_query
from config import MONDAY_SMS_BOARD_ID


def listar(board_id: int, label: str) -> None:
    query = """
    query ($board_id: ID!) {
      boards(ids: [$board_id]) {
        columns { id title type }
      }
    }
    """
    data    = _executar_query(query, {"board_id": str(board_id)})
    boards  = data.get("boards", [])
    colunas = boards[0].get("columns", []) if boards else []

    if not colunas:
        print(f"Nenhuma coluna encontrada no board {label} (id={board_id}).")
        return

    print(f"\nBoard: {label} (id={board_id})\n")
    print(f"{'Título':<35} {'ID':<25} {'Tipo'}")
    print("-" * 75)
    for col in colunas:
        print(f"{col.get('title',''):<35} {col.get('id',''):<25} {col.get('type','')}")


if __name__ == "__main__":
    modo_sms = "--sms" in sys.argv

    if modo_sms:
        if not MONDAY_SMS_BOARD_ID:
            print("MONDAY_SMS_BOARD_ID não configurado no .env.")
            sys.exit(1)
        listar(MONDAY_SMS_BOARD_ID, "SMS")
    else:
        from config import MONDAY_BOARD_ID
        listar(MONDAY_BOARD_ID, "Inclusões")
