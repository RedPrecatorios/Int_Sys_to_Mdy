import os
from dotenv import load_dotenv

load_dotenv()

# None ou string vazia se não definido (útil para aviso no arranque em cloud)
_raw_token = os.getenv("MONDAY_API_TOKEN")
MONDAY_API_TOKEN = _raw_token if _raw_token and str(_raw_token).strip() else None
MONDAY_BOARD_ID = int(os.getenv("MONDAY_BOARD_ID", "7345244366"))
MONDAY_API_URL = os.getenv("MONDAY_API_URL", "https://api.monday.com/v2")

CAMPOS_FIXOS = {
    "subelementos": "",
    "etapa": "Aguardando Atualização",
    "permissao": os.getenv("PERMISSAO", "aline.chaves@redprecatorios.com.br"),
}
