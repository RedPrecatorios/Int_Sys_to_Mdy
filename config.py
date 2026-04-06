import os
from dotenv import load_dotenv

load_dotenv()

MONDAY_API_TOKEN = os.getenv("MONDAY_API_TOKEN")
MONDAY_BOARD_ID = int(os.getenv("MONDAY_BOARD_ID", "7345244366"))
MONDAY_API_URL = os.getenv("MONDAY_API_URL", "https://api.monday.com/v2")

CAMPOS_FIXOS = {
    "subelementos": "",
    "etapa": "Aguardando Atualização",
    "permissao": os.getenv("PERMISSAO", "aline.chaves@redprecatorios.com.br"),
}
