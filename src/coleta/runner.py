"""Orquestrador Central e Unificado de Coleta de Dados.

Ponto de entrada único (CLI) para execução, atualização, auditoria e controle
de políticas de sobrescrita de todas as fontes de dados do projeto.

Uso:
    python -m src.coleta.runner --all
    python -m src.coleta.runner --fonte ipca
    python -m src.coleta.runner --fontes ipca,bcb --overwrite force
    python -m src.coleta.runner --status
    python -m src.coleta.runner --all --interactive
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Callable

import pandas as pd

from .. import config
from ..logging_config import (
    CoresANSI,
    DownloadLogger,
    ModuloExecucaoMeta,
    SessionManifest,
    inicializar_sessao_logging,
    obter_pasta_logs,
)
from . import bcb, inmet, monitor_secas, safra, sidra_ipca
from .base import ColetaResult, calcular_tamanho_caminho

# --------------------------------------------------------------------------- #
# Registro de Coletores Disponíveis                                           #
# --------------------------------------------------------------------------- #

COLETORES: dict[str, dict[str, Any]] = {
    "ipca": {
        "nome_exibicao": "IPCA Alimentos (IBGE/SIDRA)",
        "modulo": sidra_ipca,
        "funcao": sidra_ipca.executar_coleta,
        "arquivo_principal": config.DATA_RAW / "sidra_ipca" / "ipca_alimentos_rm.parquet",
        "aliases": ["sidra_ipca", "ibge_ipca", "inflacao"],
        "pasta_raw": config.DATA_RAW / "sidra_ipca",
    },
    "inmet": {
        "nome_exibicao": "Clima BDMEP (INMET)",
        "modulo": inmet,
        "funcao": inmet.executar_coleta,
        "arquivo_principal": config.DATA_INTERIM / "clima_estacao_mes.parquet",
        "aliases": ["clima", "bdmep", "meteorologia"],
        "pasta_raw": config.RAW_INMET,
    },
    "seca": {
        "nome_exibicao": "Monitor de Secas (ANA)",
        "modulo": monitor_secas,
        "funcao": monitor_secas.executar_coleta,
        "arquivo_principal": config.DATA_INTERIM / "seca_uf_mes.parquet",
        "aliases": ["monitor_secas", "ana", "secas"],
        "pasta_raw": config.RAW_ANA,
    },
    "safra": {
        "nome_exibicao": "Estimativas de Safra (LSPA/PAM)",
        "modulo": safra,
        "funcao": safra.executar_coleta,
        "arquivo_principal": config.DATA_INTERIM / "safra_uf_mes.parquet",
        "aliases": ["lspa", "pam", "ibge_safra", "safras"],
        "pasta_raw": config.DATA_RAW / "estimativas_safra_UF",
    },
    "bcb": {
        "nome_exibicao": "Variáveis Macroeconômicas (BCB/SGS)",
        "modulo": bcb,
        "funcao": bcb.executar_coleta,
        "arquivo_principal": config.DATA_INTERIM / "macro_br_mes.parquet",
        "aliases": ["sgs", "macro", "banco_central", "dolar", "selic"],
        "pasta_raw": config.DATA_RAW / "bcb_var_macroeconômicas",
    },
}

ORDEM_EXECUCAO_PADRAO = ["ipca", "inmet", "seca", "safra", "bcb"]


def resolver_nome_fonte(termo: str) -> str | None:
    """Normaliza o nome da fonte ou alias informado pelo usuário."""
    termo_norm = termo.strip().lower().replace("-", "_")
    if termo_norm in COLETORES:
        return termo_norm
    for chave, info in COLETORES.items():
        if termo_norm in info["aliases"]:
            return chave
    return None


# --------------------------------------------------------------------------- #
# Formatação de Tabelas ASCII para Terminal                                   #
# --------------------------------------------------------------------------- #

def formatar_tabela_resumo(resultados: list[ColetaResult]) -> str:
    """Gera uma tabela ASCII formatada com resumo visual da sessão."""
    usa_cor = CoresANSI.ativo()
    
    cabecalhos = ["Fonte", "Status", "Ação Executada", "Linhas", "Cols", "Tamanho", "Tempo (s)", "Arquivo de Saída"]
    linhas_tabela = []

    for r in resultados:
        # Status formatado
        status_str = r.status
        if usa_cor:
            if r.status == "SUCESSO":
                status_str = f"{CoresANSI.VERDE}{CoresANSI.BOLD}SUCESSO{CoresANSI.RESET}"
            elif r.status == "AVISO":
                status_str = f"{CoresANSI.AMARELO}{CoresANSI.BOLD}AVISO{CoresANSI.RESET}"
            elif r.status == "PULADO":
                status_str = f"{CoresANSI.CINZA}PULADO{CoresANSI.RESET}"
            else:
                status_str = f"{CoresANSI.VERMELHO}{CoresANSI.BOLD}FALHA{CoresANSI.RESET}"

        # Tamanho legível
        if r.tamanho_bytes >= 1e9:
            tam_str = f"{r.tamanho_bytes / 1e9:.2f} GB"
        elif r.tamanho_bytes >= 1e6:
            tam_str = f"{r.tamanho_bytes / 1e6:.2f} MB"
        elif r.tamanho_bytes >= 1e3:
            tam_str = f"{r.tamanho_bytes / 1e3:.1f} KB"
        elif r.tamanho_bytes > 0:
            tam_str = f"{r.tamanho_bytes} B"
        else:
            tam_str = "-"

        linhas_tabela.append([
            r.fonte,
            status_str,
            r.acao_executada,
            f"{r.linhas:,}" if r.linhas > 0 else "-",
            str(r.colunas) if r.colunas > 0 else "-",
            tam_str,
            f"{r.duracao_segundos:.2f}s",
            r.arquivo_saida or "-",
        ])

    # Cálculo das larguras das colunas (sem códigos ANSI)
    def comprimento_real(texto: str) -> int:
        sem_ansi = (
            texto.replace(CoresANSI.RESET, "")
            .replace(CoresANSI.BOLD, "")
            .replace(CoresANSI.VERDE, "")
            .replace(CoresANSI.AMARELO, "")
            .replace(CoresANSI.VERMELHO, "")
            .replace(CoresANSI.CINZA, "")
            .replace(CoresANSI.AZUL, "")
            .replace(CoresANSI.CIANO, "")
        )
        return len(sem_ansi)

    larguras = [len(c) for c in cabecalhos]
    for linha in linhas_tabela:
        for i, celula in enumerate(linha):
            larguras[i] = max(larguras[i], comprimento_real(celula))

    sep = "+" + "+".join("-" * (w + 2) for w in larguras) + "+"
    cab = "| " + " | ".join(c.ljust(larguras[i]) for i, c in enumerate(cabecalhos)) + " |"

    linhas_saida = [sep, cab, sep]
    for linha in linhas_tabela:
        itens_fmt = []
        for i, celula in enumerate(linha):
            espacos = larguras[i] - comprimento_real(celula)
            itens_fmt.append(celula + (" " * espacos))
        linhas_saida.append("| " + " | ".join(itens_fmt) + " |")
    linhas_saida.append(sep)

    return "\n".join(linhas_saida)


# --------------------------------------------------------------------------- #
# Inspeção de Status do Disco (--status / --dry-run)                         #
# --------------------------------------------------------------------------- #

def inspecionar_status_disco() -> int:
    """Verifica e exibe o estado de integridade e preenchimento de todos os dados locais."""
    usa_cor = CoresANSI.ativo()
    config.garantir_pastas()

    print("\n" + "=" * 90)
    print("🔍 AUDITORIA DO ESTADO DAS BASES DE DADOS EM DISCO (DRY-RUN / STATUS)")
    print("=" * 90)

    fontes_auditadas = [
        ("Inflação IPCA (Alimentos)", config.DATA_RAW / "sidra_ipca" / "ipca_alimentos_rm.parquet"),
        ("Clima INMET (Mensal)", config.DATA_INTERIM / "clima_estacao_mes.parquet"),
        ("Clima INMET (Diário)", config.DATA_INTERIM / "clima_estacao_dia.parquet"),
        ("Clima INMET (Catálogo)", config.DATA_INTERIM / "catalogo_estacoes.csv"),
        ("Monitor de Secas (ANA)", config.DATA_INTERIM / "seca_uf_mes.parquet"),
        ("Estimativas Safra (LSPA)", config.DATA_INTERIM / "safra_uf_mes.parquet"),
        ("Produção Safra (PAM)", config.DATA_INTERIM / "producao_uf_ano.parquet"),
        ("Variáveis Macro (BCB)", config.DATA_INTERIM / "macro_br_mes.parquet"),
        ("Dimensão Territorial (UF)", config.DATA_PROCESSED / "dim_uf.csv"),
        ("CONAB Série Histórica", config.DATA_RAW / "conab" / "SerieHistoricaGraos.txt"),
    ]

    tabela_linhas = []

    for rotulo, caminho in fontes_auditadas:
        if not caminho.exists():
            status_txt = f"{CoresANSI.VERMELHO}AUSENTE{CoresANSI.RESET}" if usa_cor else "AUSENTE"
            tabela_linhas.append((rotulo, status_txt, "-", "-", "-", "-", str(caminho.relative_to(config.RAIZ))))
            continue

        tamanho_b = calcular_tamanho_caminho(caminho)
        mtime = datetime.fromtimestamp(caminho.stat().st_mtime).strftime("%Y-%m-%d %H:%M")

        if tamanho_b >= 1e9:
            tam_str = f"{tamanho_b / 1e9:.2f} GB"
        elif tamanho_b >= 1e6:
            tam_str = f"{tamanho_b / 1e6:.2f} MB"
        else:
            tam_str = f"{tamanho_b / 1e3:.1f} KB"

        linhas_str = "-"
        cols_str = "-"
        status_txt = f"{CoresANSI.VERDE}OK{CoresANSI.RESET}" if usa_cor else "OK"

        try:
            if caminho.suffix == ".parquet" and caminho.is_file():
                df = pd.read_parquet(caminho)
                linhas_str = f"{len(df):,}"
                cols_str = str(len(df.columns))
            elif caminho.suffix == ".csv" and caminho.is_file():
                df = pd.read_csv(caminho)
                linhas_str = f"{len(df):,}"
                cols_str = str(len(df.columns))
            elif caminho.is_dir():
                parquets = list(caminho.glob("*.parquet"))
                if parquets:
                    df = pd.read_parquet(caminho)
                    linhas_str = f"{len(df):,} ({len(parquets)} partes)"
                    cols_str = str(len(df.columns))
                else:
                    linhas_str = f"{len(list(caminho.iterdir()))} arquivos"
            elif caminho.suffix == ".txt" and caminho.is_file():
                with caminho.open(encoding="latin-1", errors="ignore") as f:
                    linhas_str = f"{sum(1 for _ in f):,}"
        except Exception as e:
            status_txt = f"{CoresANSI.AMARELO}ERRO_LEITURA{CoresANSI.RESET}" if usa_cor else "ERRO_LEITURA"

        tabela_linhas.append((rotulo, status_txt, linhas_str, cols_str, tam_str, mtime, str(caminho.relative_to(config.RAIZ))))

    cabecalhos = ["Base de Dados", "Status", "Linhas", "Cols", "Tamanho", "Modificado", "Caminho Relativo"]
    
    def c_len(t: str) -> int:
        return len(
            t.replace(CoresANSI.RESET, "")
            .replace(CoresANSI.VERDE, "")
            .replace(CoresANSI.AMARELO, "")
            .replace(CoresANSI.VERMELHO, "")
        )

    w = [len(c) for c in cabecalhos]
    for r in tabela_linhas:
        for i, val in enumerate(r):
            w[i] = max(w[i], c_len(val))

    sep = "+" + "+".join("-" * (width + 2) for width in w) + "+"
    cab = "| " + " | ".join(c.ljust(w[i]) for i, c in enumerate(cabecalhos)) + " |"

    print(sep)
    print(cab)
    print(sep)
    for r in tabela_linhas:
        row_fmt = []
        for i, val in enumerate(r):
            pad = w[i] - c_len(val)
            row_fmt.append(val + (" " * pad))
        print("| " + " | ".join(row_fmt) + " |")
    print(sep)
    print("💡 Para atualizar ou coletar qualquer base, use: python -m src.coleta.runner --all\n")
    return 0


# --------------------------------------------------------------------------- #
# Execução Principal do Orquestrador                                          #
# --------------------------------------------------------------------------- #

def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.coleta.runner",
        description="Orquestrador Central e Unificado de Coleta de Dados do Projeto.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  python -m src.coleta.runner --all                       # Executa todos os coletores no modo seguro
  python -m src.coleta.runner --fonte ipca                # Executa apenas a coleta do IPCA
  python -m src.coleta.runner --fontes inmet,seca         # Executa apenas INMET e Monitor de Secas
  python -m src.coleta.runner --all --overwrite force     # Força nova coleta descartando checkpoints
  python -m src.coleta.runner --fonte bcb --backup        # Coleta BCB mantendo backup de segurança
  python -m src.coleta.runner --all --interactive         # Confirmação interativa antes de sobrescrever
  python -m src.coleta.runner --status                    # Diagnóstico dos arquivos presentes em disco
        """
    )

    # Grupo de Seleção de Escopo
    escopo = parser.add_argument_group("Seleção de Escopo")
    escopo.add_argument("--all", "-a", action="store_true", help="executa TODOS os coletores na ordem correta")
    escopo.add_argument("--fonte", type=str, metavar="NOME", help="executa uma única fonte (ipca, inmet, seca, safra, bcb)")
    escopo.add_argument("--fontes", type=str, metavar="N1,N2", help="executa uma lista separada por vírgulas (ex: ipca,bcb)")
    escopo.add_argument("--status", "--dry-run", action="store_true", help="exibe o estado dos dados em disco sem fazer requisições")

    # Grupo de Políticas de Sobrescrita
    sobrescrita = parser.add_argument_group("Políticas de Sobrescrita (--overwrite)")
    sobrescrita.add_argument(
        "--overwrite",
        choices=["skip", "force", "update", "backup"],
        default="skip",
        help="política de sobrescrita de arquivos existentes (padrão: skip)"
    )
    sobrescrita.add_argument("--force", "-f", action="store_true", help="atalho para --overwrite force (substituição total)")
    sobrescrita.add_argument("--update", "-u", action="store_true", help="atalho para --overwrite update (atualização incremental)")
    sobrescrita.add_argument("--backup", "-b", action="store_true", help="atalho para --overwrite backup (com cópia de segurança)")
    sobrescrita.add_argument("--interactive", "-i", action="store_true", help="pergunta antes de sobrescrever arquivos existentes")

    # Grupo de Recorte Temporal e Verbosidade
    opcoes = parser.add_argument_group("Recorte Temporal e Logging")
    opcoes.add_argument("--ano-inicio", type=int, metavar="ANO", help="ano inicial para coleta (ex: 2020)")
    opcoes.add_argument("--ano-fim", type=int, metavar="ANO", help="ano final para coleta (ex: 2026)")
    opcoes.add_argument("--verbose", "-v", action="store_true", help="mostra mensagens detalhadas de DEBUG no terminal")
    opcoes.add_argument("--quiet", "-q", action="store_true", help="mostra apenas avisos e erros no terminal")
    opcoes.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=None,
        help="define explicitamente o nível de log do console"
    )

    return parser


def resolver_politica_sobrescrita(args: argparse.Namespace) -> str:
    """Resolve a política final de sobrescrita considerando atalhos de flags."""
    if args.force:
        return "force"
    if args.update:
        return "update"
    if args.backup:
        return "backup"
    return args.overwrite.lower()


def resolver_fontes_selecionadas(args: argparse.Namespace) -> list[str]:
    """Determina a lista ordenada de fontes a serem executadas."""
    if args.all:
        return list(ORDEM_EXECUCAO_PADRAO)

    if args.fonte:
        nome_resolvido = resolver_nome_fonte(args.fonte)
        if not nome_resolvido:
            print(f"❌ Erro: Fonte '{args.fonte}' não reconhecida. Opções válidas: {list(COLETORES.keys())}")
            sys.exit(1)
        return [nome_resolvido]

    if args.fontes:
        lista_bruta = [f.strip() for f in args.fontes.split(",") if f.strip()]
        selecionadas = []
        for item in lista_bruta:
            resolvido = resolver_nome_fonte(item)
            if not resolvido:
                print(f"❌ Erro: Fonte '{item}' não reconhecida. Opções válidas: {list(COLETORES.keys())}")
                sys.exit(1)
            if resolvido not in selecionadas:
                selecionadas.append(resolvido)
        return [f for f in ORDEM_EXECUCAO_PADRAO if f in selecionadas]

    # Se nenhum argumento de escopo foi passado
    return []


def main(argv: list[str] | None = None) -> int:
    parser = construir_parser()
    args = parser.parse_args(argv)

    # Modo Status / Dry-Run
    if args.status:
        return inspecionar_status_disco()

    fontes_a_executar = resolver_fontes_selecionadas(args)
    if not fontes_a_executar:
        parser.print_help()
        print("\n💡 Especifique o escopo desejado: --all, --fonte <nome> ou --fontes <n1,n2>")
        return 1

    politica = resolver_politica_sobrescrita(args)

    # Configuração de Nível de Console
    nivel_console = logging.INFO
    if args.log_level:
        nivel_console = getattr(logging, args.log_level.upper(), logging.INFO)
    elif args.verbose:
        nivel_console = logging.DEBUG
    elif args.quiet:
        nivel_console = logging.WARNING

    # Inicializa Sessão de Logging (Camadas 1, 2 e 3)
    sessao_id, log_file, logger = inicializar_sessao_logging(nivel_console=nivel_console)

    comando_exec = "python -m src.coleta.runner " + " ".join(sys.argv[1:] if argv is None else argv)
    manifesto = SessionManifest(
        sessao_id=sessao_id,
        comando_executado=comando_exec,
        politica_sobrescrita=politica,
    )

    logger.info("=" * 75)
    logger.info(f"🚀 INICIANDO SESSÃO DE ORQUESTRAÇÃO DE COLETA [{sessao_id}]")
    logger.info(f"   Fontes Selecionadas ({len(fontes_a_executar)}): {', '.join(fontes_a_executar)}")
    logger.info(f"   Política de Sobrescrita: {politica.upper()} (Interativo: {args.interactive})")
    if args.ano_inicio or args.ano_fim:
        logger.info(f"   Filtro Temporal: {args.ano_inicio or 'início'} até {args.ano_fim or 'fim'}")
    logger.info(f"   Arquivo de Log (DEBUG): {log_file.relative_to(config.RAIZ)}")
    logger.info("=" * 75)

    resultados: list[ColetaResult] = []
    total_fontes = len(fontes_a_executar)

    for idx, chave_fonte in enumerate(fontes_a_executar, start=1):
        info_fonte = COLETORES[chave_fonte]
        nome_exib = info_fonte["nome_exibicao"]
        funcao_exec = info_fonte["funcao"]
        pasta_raw = info_fonte["pasta_raw"]

        logger.info(f"\n[{idx}/{total_fontes}] Executando coletor: {nome_exib} ({chave_fonte})...")
        dl_logger = DownloadLogger(pasta_raw)
        log_coletor = logging.getLogger(f"coleta.{chave_fonte}")

        t0_mod = time.perf_counter()
        try:
            resultado = funcao_exec(
                overwrite=politica,
                ano_inicio=args.ano_inicio,
                ano_fim=args.ano_fim,
                logger=log_coletor,
                download_logger=dl_logger,
                interativo=args.interactive,
            )
        except Exception as e:
            duracao_falha = round(time.perf_counter() - t0_mod, 2)
            logger.error(f"Erro não tratado no coletor '{chave_fonte}': {e}", exc_info=True)
            resultado = ColetaResult(
                fonte=chave_fonte,
                status="FALHA",
                acao_executada="EXCECAO_NAO_TRATADA",
                duracao_segundos=duracao_falha,
                erros=[str(e)],
            )

        resultados.append(resultado)

        # Adiciona ao Manifesto JSON
        manifesto.adicionar_modulo(
            ModuloExecucaoMeta(
                fonte=resultado.fonte,
                status=resultado.status,
                acao_executada=resultado.acao_executada,
                duracao_segundos=resultado.duracao_segundos,
                linhas_geradas=resultado.linhas,
                colunas_geradas=resultado.colunas,
                arquivo_saida=resultado.arquivo_saida,
                tamanho_bytes=resultado.tamanho_bytes,
                chunks_totais=resultado.chunks_totais,
                chunks_baixados=resultado.chunks_baixados,
                chunks_reaproveitados=resultado.chunks_reaproveitados,
                erros=resultado.erros,
                detalhes=resultado.detalhes,
            )
        )

    # Finaliza e grava o Manifesto JSON (Camada 3)
    caminho_manifesto = manifesto.finalizar()

    # Exibe Resumo Visual no Console (Camada 1)
    logger.info("\n" + "=" * 75)
    logger.info("📊 RESUMO FINAL DA EXECUÇÃO")
    logger.info("=" * 75)
    print(formatar_tabela_resumo(resultados))

    falhas = [r for r in resultados if r.status == "FALHA"]
    avisos = [r for r in resultados if r.status == "AVISO"]

    logger.info(f"\n📄 Log Detalhado (DEBUG): {log_file.relative_to(config.RAIZ)}")
    logger.info(f"📋 Manifesto JSON:       {caminho_manifesto.relative_to(config.RAIZ)}")

    if falhas:
        logger.error(f"\n❌ Sessão concluída com {len(falhas)} falha(s). Verifique o log para detalhes.")
        return 1
    elif avisos:
        logger.warning(f"\n⚠️ Sessão concluída com {len(avisos)} aviso(s).")
        return 0

    logger.info("\n✅ Todas as coletas foram concluídas com sucesso!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
