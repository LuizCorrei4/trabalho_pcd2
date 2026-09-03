"""Coletor e estruturador de preços de combustíveis (ANP).

Ingesta os dados brutos de combustíveis da ANP e gera a tabela padronizada
em nível UF × mês (data/interim/combustiveis_uf_mes.parquet).
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

import pandas as pd

from ... import config
from ...logging_config import (
    BackupManager,
    DownloadLogger,
    get_logger,
    prompt_confirmacao,
)
from ..base import ColetaResult

CAMINHO_RAW = config.DATA_RAW / "combustiveis" / "combustivel.csv"
DESTINO_INTERIM = config.DATA_INTERIM / "combustiveis_uf_mes.parquet"


def executar_coleta(
    overwrite: str = "skip",
    ano_inicio: int | None = None,
    ano_fim: int | None = None,
    logger: logging.Logger | None = None,
    download_logger: DownloadLogger | None = None,
    interativo: bool = False,
) -> ColetaResult:
    """Executa a ingestão e estruturação dos dados de combustíveis da ANP.

    Args:
        overwrite: Política de sobrescrita ('skip', 'force', 'update', 'backup').
        ano_inicio: Ano inicial opcional.
        ano_fim: Ano final opcional.
        logger: Logger configurado da sessão.
        download_logger: Logger transacional de downloads.
        interativo: Se True, pergunta confirmação antes de sobrescrever.

    Returns:
        ColetaResult com métricas e metadados da execução.
    """
    log = logger or get_logger("combustiveis")
    t_inicio = time.perf_counter()

    dl_logger = download_logger or DownloadLogger(config.DATA_RAW / "combustiveis")

    # Tratamento Interativo
    politica = overwrite.lower()
    if interativo and DESTINO_INTERIM.exists():
        escolha = prompt_confirmacao(DESTINO_INTERIM, log)
        if escolha == "cancel":
            return ColetaResult(
                fonte="combustiveis",
                status="PULADO",
                acao_executada="PULADO_PELO_USUARIO",
                duracao_segundos=round(time.perf_counter() - t_inicio, 2),
                arquivo_saida=str(DESTINO_INTERIM.relative_to(config.RAIZ)),
            )
        politica = escolha

    # Verificação de reutilização (skip)
    if politica == "skip" and DESTINO_INTERIM.exists():
        try:
            df_existente = pd.read_parquet(DESTINO_INTERIM)
            tamanho = DESTINO_INTERIM.stat().st_size
            log.info(
                f"Arquivo interim de combustíveis já existe ({len(df_existente):,} linhas). "
                "Pulando reprocessamento (skip)."
            )
            return ColetaResult(
                fonte="combustiveis",
                status="SUCESSO",
                acao_executada="REUTILIZADO",
                duracao_segundos=round(time.perf_counter() - t_inicio, 2),
                linhas=len(df_existente),
                colunas=df_existente.shape[1],
                arquivo_saida=str(DESTINO_INTERIM.relative_to(config.RAIZ)),
                tamanho_bytes=tamanho,
                chunks_totais=1,
                chunks_baixados=0,
                chunks_reaproveitados=1,
            )
        except Exception as e:
            log.warning(f"Arquivo existente ilegível ({e}). Reprocessando...")

    # Verifica se o arquivo bruto da ANP existe
    if not CAMINHO_RAW.exists():
        duracao = time.perf_counter() - t_inicio
        msg = f"Arquivo bruto não encontrado em: {CAMINHO_RAW}"
        log.error(msg)
        return ColetaResult(
            fonte="combustiveis",
            status="FALHA",
            acao_executada="ERRO_ARQUIVO_NAO_ENCONTRADO",
            duracao_segundos=round(duracao, 2),
            arquivo_saida=str(DESTINO_INTERIM.relative_to(config.RAIZ)),
            erros=[msg],
        )

    log.info(f"Iniciando estruturação de combustíveis ANP a partir de: {CAMINHO_RAW.name}")

    try:
        import importlib

        mod_comb = importlib.import_module("src.tratamento.25_combustiveis")
        prepara_combustiveis = mod_comb.prepara_combustiveis

        t_proc = time.perf_counter()
        df_comb = prepara_combustiveis()
        duracao_proc_ms = (time.perf_counter() - t_proc) * 1000

        # Filtro temporal opcional se solicitado
        if ano_inicio is not None or ano_fim is not None:
            if hasattr(df_comb["ano_mes"].dtype, "year"):
                anos = df_comb["ano_mes"].dt.year
            else:
                anos = pd.to_datetime(df_comb["ano_mes"].astype(str)).dt.year

            mascara = pd.Series(True, index=df_comb.index)
            if ano_inicio is not None:
                mascara &= anos >= ano_inicio
            if ano_fim is not None:
                mascara &= anos <= ano_fim
            df_comb = df_comb[mascara].reset_index(drop=True)

        # Gravação protegida com BackupManager
        usar_backup = politica == "backup"
        with BackupManager.gerenciar_com_seguranca(
            DESTINO_INTERIM, ativar_backup=usar_backup, logger=log
        ):
            DESTINO_INTERIM.parent.mkdir(parents=True, exist_ok=True)
            df_comb.to_parquet(DESTINO_INTERIM, index=False)

        tamanho = DESTINO_INTERIM.stat().st_size
        duracao_total = time.perf_counter() - t_inicio

        # Registro transacional CSV
        dl_logger.registrar(
            identificador_chunk="combustiveis_uf_mes",
            url=str(CAMINHO_RAW),
            status_http=200,
            tamanho_bytes=tamanho,
            duracao_ms=duracao_proc_ms,
            tentativas_retry=1,
            sucesso=True,
        )

        acao = "BACKUP_CRIADO" if usar_backup else ("ATUALIZADO" if politica == "force" else "BAIXADO_NOVO")
        log.info(
            f"Combustíveis estruturados com sucesso: {len(df_comb):,} linhas, "
            f"{df_comb.shape[1]} colunas ({tamanho / 1024:.1f} KB)."
        )

        return ColetaResult(
            fonte="combustiveis",
            status="SUCESSO",
            acao_executada=acao,
            duracao_segundos=round(duracao_total, 2),
            linhas=len(df_comb),
            colunas=df_comb.shape[1],
            arquivo_saida=str(DESTINO_INTERIM.relative_to(config.RAIZ)),
            tamanho_bytes=tamanho,
            chunks_totais=1,
            chunks_baixados=1,
            chunks_reaproveitados=0,
            detalhes={
                "produtos": ["diesel", "diesel_s10", "gasolina", "etanol", "glp_13kg"],
                "ufs": int(df_comb["sigla_uf"].nunique()),
                "meses": int(df_comb["ano_mes"].nunique()),
            },
        )

    except Exception as e:
        duracao = time.perf_counter() - t_inicio
        log.exception(f"Erro no processamento de combustíveis: {e}")
        return ColetaResult(
            fonte="combustiveis",
            status="FALHA",
            acao_executada="FALHA_PROCESSAMENTO",
            duracao_segundos=round(duracao, 2),
            arquivo_saida=str(DESTINO_INTERIM.relative_to(config.RAIZ)),
            erros=[str(e)],
        )
