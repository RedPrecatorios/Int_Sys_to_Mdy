"""
Gera a aba com Telefone (sem 55), Nome completo e Número de processo.

Layouts detectados automaticamente na primeira aba compatível:
  - PRC FINAL: colunas TELEFONE_1, TELEFONE_2, … (ex.: Sheet1)
  - Lemitti: DDD em U, telefone em V, POSSUI-WHATSAPP em Z

Se não houver colunas POSSUI_WHATSAPP_n, usa o primeiro TELEFONE_k preenchido
(use --exige-whatsapp para exigir flag e ignorar linhas sem ela).

Uso:
    python utils/criar_aba_whatsapp_final.py "FINAL.xlsx"
    python utils/criar_aba_whatsapp_final.py "FINAL.xlsx" --enriquecimento "Lemitti.xlsx"
    python utils/criar_aba_whatsapp_final.py arquivo.xlsx --aba-fonte Sheet1
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from Modulos.excel_whatsapp_aba import WhatsAppAbaConfig, aplicar_aba_whatsapp_final


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Cria aba WhatsApp no Excel FINAL (auto: PRC TELEFONE_* ou Lemitti U/V/Z)"
    )
    parser.add_argument("arquivo", help="Caminho do arquivo .xlsx (FINAL)")
    parser.add_argument(
        "--enriquecimento",
        dest="enriquecimento",
        default=None,
        help="Excel separado Lemitti: U=DD, V=telefone, Z=POSSUI-WHATSAPP. Cruza com o FINAL pelo nº processo.",
    )
    parser.add_argument(
        "--aba-enriquecimento",
        default=None,
        help="Aba no ficheiro Lemitti (omitir = detetar por cabeçalho na coluna Z ou 1.ª aba)",
    )
    parser.add_argument(
        "--col-processo-lemitti",
        default=None,
        help="Letra da coluna do número de processo no ficheiro Lemitti (se não detetar pelo cabeçalho)",
    )
    parser.add_argument(
        "--linha-cabecalho-lemitti",
        type=int,
        default=1,
        help="Linha de cabeçalhos no ficheiro Lemitti",
    )
    parser.add_argument(
        "--linha-dados-inicio-lemitti",
        type=int,
        default=2,
        help="Primeira linha de dados no ficheiro Lemitti",
    )
    parser.add_argument(
        "--aba-fonte",
        "--aba-lemiti",
        dest="aba_fonte",
        default=None,
        help="Nome da aba de origem (omitir = detectar automaticamente)",
    )
    parser.add_argument(
        "--aba-destino",
        default="WhatsApp_FINAL",
        help="Nome da nova aba a criar (substitui se já existir)",
    )
    parser.add_argument("--col-nome", default=None, help="Letra da coluna do nome (se não detectar)")
    parser.add_argument("--col-processo", default=None, help="Letra da coluna do processo (se não detectar)")
    parser.add_argument("--linha-cabecalho", type=int, default=1)
    parser.add_argument("--linha-dados-inicio", type=int, default=2)
    parser.add_argument(
        "--exige-whatsapp",
        action="store_true",
        help="Só aceita telefone se existir coluna POSSUI_WHATSAPP_n=1 para o mesmo índice",
    )
    args = parser.parse_args()

    if not os.path.isfile(args.arquivo):
        print(f"Arquivo não encontrado: {args.arquivo}", file=sys.stderr)
        sys.exit(1)
    if args.enriquecimento and not os.path.isfile(args.enriquecimento):
        print(f"Enriquecimento não encontrado: {args.enriquecimento}", file=sys.stderr)
        sys.exit(1)

    cfg = WhatsAppAbaConfig(
        caminho_arquivo=os.path.abspath(args.arquivo),
        nome_aba_fonte=args.aba_fonte,
        nome_aba_destino=args.aba_destino,
        linha_cabecalho=args.linha_cabecalho,
        linha_dados_inicio=args.linha_dados_inicio,
        col_nome=args.col_nome,
        col_processo=args.col_processo,
        exige_flag_whatsapp=args.exige_whatsapp,
        caminho_enriquecimento_lemitti=(
            os.path.abspath(args.enriquecimento) if args.enriquecimento else None
        ),
        nome_aba_enriquecimento=args.aba_enriquecimento,
        linha_cabecalho_lemitti=args.linha_cabecalho_lemitti,
        linha_dados_inicio_lemitti=args.linha_dados_inicio_lemitti,
        col_processo_lemitti=args.col_processo_lemitti,
    )

    stats = aplicar_aba_whatsapp_final(cfg)
    print(
        f"OK — aba '{args.aba_destino}': {stats['linhas_escritas']} linha(s), "
        f"{stats['processos_unicos']} processo(s) único(s)."
    )
    print(f"    Layout: {stats['layout']} | Aba fonte FINAL: {stats['aba_fonte']!r}")
    if stats.get("aba_lemitti"):
        print(f"    Aba Lemitti: {stats['aba_lemitti']!r} | Mapa WhatsApp: {stats.get('processos_com_whatsapp_lemitti')} processo(s)")
    if stats.get("aviso"):
        print(f"    Aviso: {stats['aviso']}")


if __name__ == "__main__":
    main()
