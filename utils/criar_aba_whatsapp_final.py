"""
Gera a aba com Telefone (sem 55), Nome completo e Número de processo
a partir da planilha de enriquecimento Lemitti (colunas U, V, Z).

Execute ANTES de limpar a planilha Lemitti, para não perder o flag WhatsApp.

Uso:
    python utils/criar_aba_whatsapp_final.py "C:\\caminho\\FINAL.xlsx"
    python utils/criar_aba_whatsapp_final.py arquivo.xlsx --aba-lemiti "Nome da aba"
    python utils/criar_aba_whatsapp_final.py arquivo.xlsx --col-nome B --col-processo A
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from Modulos.excel_whatsapp_aba import WhatsAppAbaConfig, aplicar_aba_whatsapp_final


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Cria aba WhatsApp no Excel FINAL (Lemitti: U=DDD, V=Tel, Z=POSSUI-WHATSAPP)"
    )
    parser.add_argument("arquivo", help="Caminho do arquivo .xlsx (FINAL)")
    parser.add_argument(
        "--aba-lemiti",
        default="Planilha de enriquecimento da Lemitti",
        help="Nome exato da aba Lemitti no workbook",
    )
    parser.add_argument(
        "--aba-destino",
        default="WhatsApp_FINAL",
        help="Nome da nova aba a criar (substitui se já existir)",
    )
    parser.add_argument(
        "--col-nome",
        default=None,
        help="Letra da coluna do nome completo (ex: B), se não houver cabeçalho detectável",
    )
    parser.add_argument(
        "--col-processo",
        default=None,
        help="Letra da coluna do número de processo (ex: A)",
    )
    parser.add_argument(
        "--linha-cabecalho",
        type=int,
        default=1,
        help="Linha onde estão os títulos (para localizar Nome e Processo)",
    )
    parser.add_argument(
        "--linha-dados-inicio",
        type=int,
        default=2,
        help="Primeira linha de dados (após o cabeçalho)",
    )
    args = parser.parse_args()

    if not os.path.isfile(args.arquivo):
        print(f"Arquivo não encontrado: {args.arquivo}", file=sys.stderr)
        sys.exit(1)

    cfg = WhatsAppAbaConfig(
        caminho_arquivo=os.path.abspath(args.arquivo),
        nome_aba_lemitti=args.aba_lemiti,
        nome_aba_destino=args.aba_destino,
        linha_cabecalho=args.linha_cabecalho,
        linha_dados_inicio=args.linha_dados_inicio,
        col_nome=args.col_nome,
        col_processo=args.col_processo,
    )

    stats = aplicar_aba_whatsapp_final(cfg)
    print(
        f"OK — aba '{args.aba_destino}' criada com {stats['linhas_escritas']} linha(s) "
        f"({stats['processos_unicos']} processo(s) único(s))."
    )


if __name__ == "__main__":
    main()
