"""
Utilitário: lista as colunas do board Monday e exibe seus IDs.

Use os IDs retornados para preencher o MAPA_COLUNAS em main.py.

Execução:
    python utils/listar_colunas.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from Modulos.monday_api import buscar_colunas

if __name__ == "__main__":
    print("Buscando colunas do board...\n")
    colunas = buscar_colunas()

    if not colunas:
        print("Nenhuma coluna encontrada. Verifique o BOARD_ID e o token.")
        sys.exit(1)

    print(f"{'Título':<30} {'ID':<25} {'Tipo'}")
    print("-" * 70)
    for col in colunas:
        print(f"{col.get('title',''):<30} {col.get('id',''):<25} {col.get('type','')}")
