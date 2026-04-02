"""
Cria (ou sobrescreve) uma aba no Excel FINAL com contatos WhatsApp válidos.

Regras (planilha de enriquecimento Lemitti):
  - DDD na coluna U, telefone na coluna V → telefone final = dígitos(U) + dígitos(V), sem prefixo 55
  - Coluna Z (POSSUI-WHATSAPP) = 1 → considera WhatsApp
  - Por número de processo, mantém apenas a primeira linha que atende (primeiro contato)

Nome e número de processo: detectados pelo cabeçalho na primeira linha de dados,
ou informados por letra de coluna.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Dict, Iterator, List, Optional, Tuple

from openpyxl import load_workbook
from openpyxl.utils import column_index_from_string
from openpyxl.worksheet.worksheet import Worksheet

# Colunas fixas (1-based), conforme especificação Lemitti
COL_DDD = column_index_from_string("U")
COL_TEL = column_index_from_string("V")
COL_WA = column_index_from_string("Z")

NOME_ABA_DESTINO_PADRAO = "WhatsApp_FINAL"


def _only_digits(s: object) -> str:
    if s is None:
        return ""
    return re.sub(r"\D", "", str(s).strip())


def _whatsapp_flag(val: object) -> bool:
    if val is None or val == "":
        return False
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return int(val) == 1
    t = str(val).strip().upper()
    return t in ("1", "SIM", "TRUE", "S", "YES")


def _norm_header(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _find_header_columns(
    ws: Worksheet,
    header_row: int,
) -> Tuple[Optional[int], Optional[int]]:
    """
    Localiza colunas de Nome e Número de processo pelo título da linha header_row.
    Retorna índices 1-based ou (None, None) se não achar.
    """
    nome_idx: Optional[int] = None
    proc_idx: Optional[int] = None

    nome_tokens = (
        "nome",
        "requerente",
        "nomecompleto",
        "nome_completo",
        "credor",
    )
    proc_tokens = (
        "processo",
        "numerodoprocesso",
        "numero_processo",
        "nrprocesso",
        "processoprincipal",
        "elemento",
    )

    for col in range(1, ws.max_column + 1):
        cell = ws.cell(row=header_row, column=col).value
        if cell is None:
            continue
        h = _norm_header(str(cell))
        if nome_idx is None and any(t in h for t in nome_tokens):
            nome_idx = col
        if proc_idx is None and any(t in h for t in proc_tokens):
            proc_idx = col

    return nome_idx, proc_idx


@dataclass
class WhatsAppAbaConfig:
    """Configuração para gerar a aba WhatsApp no workbook FINAL."""

    caminho_arquivo: str
    nome_aba_lemitti: str
    nome_aba_destino: str = NOME_ABA_DESTINO_PADRAO
    linha_cabecalho: int = 1
    linha_dados_inicio: int = 2
    col_nome: Optional[str] = None  # ex: "B" — sobrescreve detecção
    col_processo: Optional[str] = None


def _col_letter_to_idx(letter: Optional[str]) -> Optional[int]:
    if not letter or not str(letter).strip():
        return None
    return column_index_from_string(str(letter).strip().upper())


def iter_linhas_whatsapp(
    ws: Worksheet,
    header_row: int,
    data_start: int,
    col_nome: int,
    col_processo: int,
) -> Iterator[Tuple[str, str, str]]:
    """
    Gera tuplas (telefone_sem_55, nome_inteiro, numero_processo) já filtradas por Z=1,
    ordenadas por ordem de linha; deduplicação por processo fica para o chamador.
    """
    for row in range(data_start, ws.max_row + 1):
        ddd = _only_digits(ws.cell(row=row, column=COL_DDD).value)
        tel = _only_digits(ws.cell(row=row, column=COL_TEL).value)
        flag = ws.cell(row=row, column=COL_WA).value

        if not _whatsapp_flag(flag):
            continue
        if not ddd and not tel:
            continue

        telefone = f"{ddd}{tel}"
        if not telefone:
            continue

        nome = ws.cell(row=row, column=col_nome).value
        proc = ws.cell(row=row, column=col_processo).value
        nome_s = (str(nome).strip() if nome is not None else "")
        proc_s = (str(proc).strip() if proc is not None else "")

        yield telefone, nome_s, proc_s


def aplicar_aba_whatsapp_final(cfg: WhatsAppAbaConfig) -> Dict[str, int]:
    """
    Abre o workbook, lê a aba Lemitti e grava/atualiza a aba de destino.

    Returns:
        Estatísticas: total_linhas_escritas, processos_unicos
    """
    wb = load_workbook(cfg.caminho_arquivo, data_only=True)
    try:
        if cfg.nome_aba_lemitti not in wb.sheetnames:
            nomes = list(wb.sheetnames)
            raise ValueError(
                f"Aba '{cfg.nome_aba_lemitti}' não encontrada. Abas: {nomes}"
            )

        ws_src = wb[cfg.nome_aba_lemitti]

        col_nome = _col_letter_to_idx(cfg.col_nome)
        col_proc = _col_letter_to_idx(cfg.col_processo)

        if col_nome is None or col_proc is None:
            det_nome, det_proc = _find_header_columns(ws_src, cfg.linha_cabecalho)
            col_nome = col_nome or det_nome
            col_proc = col_proc or det_proc

        if col_nome is None or col_proc is None:
            raise ValueError(
                "Não foi possível localizar colunas de Nome e Número de processo. "
                "Defina col_nome e col_processo (letras Excel) ou ajuste o cabeçalho na linha 1."
            )

        vistos: set = set()
        saida: List[Tuple[str, str, str]] = []

        for telefone, nome, proc in iter_linhas_whatsapp(
            ws_src,
            cfg.linha_cabecalho,
            cfg.linha_dados_inicio,
            col_nome,
            col_proc,
        ):
            chave = _norm_processo_key(proc)
            if not chave:
                continue
            if chave in vistos:
                continue
            vistos.add(chave)
            saida.append((telefone, nome, proc))

        if cfg.nome_aba_destino in wb.sheetnames:
            wb.remove(wb[cfg.nome_aba_destino])
        ws_out = wb.create_sheet(cfg.nome_aba_destino)

        ws_out.append(["Telefone", "Nome", "Número de processo"])
        for telefone, nome, proc in saida:
            ws_out.append([telefone, nome, proc])

        wb.save(cfg.caminho_arquivo)

        return {
            "linhas_escritas": len(saida),
            "processos_unicos": len(vistos),
        }
    finally:
        wb.close()


def _norm_processo_key(proc: str) -> str:
    if not proc or not str(proc).strip():
        return ""
    return re.sub(r"\s+", "", str(proc).upper().strip())
