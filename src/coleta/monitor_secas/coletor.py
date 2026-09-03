"""Orquestrador do coletor do Monitor de Secas (ANA - T-015).

Gerencia download, agregação mensal por UF, cálculo de severidade e validações.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import pandas as pd

from ... import config, rede, ufs as mod_ufs
from ...logging_config import BackupManager, DownloadLogger, get_logger, prompt_confirmacao
from ..base import ColetaResult
from . import agrega_uf_mes, download, validar

DESTINO_FINAL = config.DATA_INTERIM / "seca_uf_mes.parquet"
PASTA_RAW_ANA = config.RAW_ANA


def executar_coleta(
    overwrite: str = 'skip',  # 'skip' | 'force' | 'update' | 'backup'
    ano_inicio: int | None = None,
    ano_fim: int | None = None,
    logger: logging.Logger | None = None,
    download_logger: DownloadLogger | None = None,
    interativo: bool = False,
) -> ColetaResult:
    """Executa a coleta e estruturação dos dados do Monitor de Secas."""
    log = logger or get_logger("monitor_secas")
    t_inicio = time.perf_counter()

    config.garantir_pastas()
    PASTA_RAW_ANA.mkdir(parents=True, exist_ok=True)

    dl_logger = download_logger or DownloadLogger(PASTA_RAW_ANA)

    politica = overwrite.lower()
    if interativo and DESTINO_FINAL.exists():
        escolha = prompt_confirmacao(DESTINO_FINAL, log)
        if escolha == "cancel":
            return ColetaResult(
                fonte="monitor_secas",
                status="PULADO",
                acao_executada="PULADO_PELO_USUARIO",
                duracao_segundos=round(time.perf_counter() - t_inicio, 2),
                arquivo_saida=str(DESTINO_FINAL.relative_to(config.RAIZ)),
            )
        politica = escolha

    # Verificação rápida no modo skip
    if politica == "skip" and DESTINO_FINAL.exists() and ano_inicio is None and ano_fim is None:
        try:
            df_existente = pd.read_parquet(DESTINO_FINAL)
            tamanho = DESTINO_FINAL.stat().st_size
            log.info(
                f"Arquivo final Monitor de Secas já existe ({len(df_existente):,} linhas). "
                f"Pulando coleta (skip)."
            )
            return ColetaResult(
                fonte="monitor_secas",
                status="SUCESSO",
                acao_executada="REUTILIZADO",
                duracao_segundos=round(time.perf_counter() - t_inicio, 2),
                linhas=len(df_existente),
                colunas=len(df_existente.columns),
                arquivo_saida=str(DESTINO_FINAL.relative_to(config.RAIZ)),
                tamanho_bytes=tamanho,
                chunks_totais=27,
                chunks_baixados=0,
                chunks_reaproveitados=27,
                detalhes={
                    "ufs": int(df_existente["sigla_uf"].nunique()),
                    "meses": int(df_existente["ano_mes"].nunique()),
                },
            )
        except Exception as e:
            log.warning(f"Arquivo existente corrompido ({e}). Reprocessando...")

    log.info(f"Iniciando coleta Monitor de Secas (ANA) com política: {politica}")

    tabela_ufs = mod_ufs.carregar_ufs()
    erros: list[str] = []
    chunks_baixados = 0
    chunks_reaproveitados = 0

    # Etapa 1: Download de dados brutos por UF
    log.info("Etapa 1/3: Download dos dados tabulares das 27 UFs na API da ANA...")
    for i, linha in enumerate(tabela_ufs.itertuples(index=False)):
        sigla = linha.sigla_uf
        cod_ibge = int(linha.cod_ibge_uf)
        destino_json = download.caminho_bruto(sigla)
        url = f"{download.URL_TABULAR}?tipo_area={download.TIPO_AREA_UF}&area={cod_ibge}"
        t0 = time.perf_counter()

        deve_baixar = (
            politica in ("force", "update")
            or not destino_json.exists()
        )

        if not deve_baixar:
            try:
                conteudo = json.loads(destino_json.read_text(encoding="utf-8"))
                if "data" in conteudo and "list" in conteudo["data"]:
                    chunks_reaproveitados += 1
                    log.debug(f"  UF {sigla} (código {cod_ibge}) já existe em disco.")
                    continue
            except Exception:
                log.warning(f"  JSON de {sigla} corrompido. Baixando novamente...")

        try:
            log.debug(f"  Baixando {sigla} ({cod_ibge})...")
            n_meses = download.baixar_uf(sigla, cod_ibge, forcar=True)
            duracao_ms = (time.perf_counter() - t0) * 1000
            tamanho = destino_json.stat().st_size if destino_json.exists() else 0

            dl_logger.registrar(
                identificador_chunk=f"dados_tabulares_uf_{sigla}.json",
                url=url,
                status_http=200,
                tamanho_bytes=tamanho,
                duracao_ms=duracao_ms,
                tentativas_retry=1,
                sucesso=True,
            )
            chunks_baixados += 1
            if i < len(tabela_ufs) - 1:
                time.sleep(download.PAUSA_ENTRE_REQUISICOES)
        except Exception as e:
            msg_erro = f"Falha ao baixar UF {sigla} (código {cod_ibge}): {e}"
            log.error(msg_erro)
            erros.append(msg_erro)
            duracao_ms = (time.perf_counter() - t0) * 1000
            dl_logger.registrar(
                identificador_chunk=f"dados_tabulares_uf_{sigla}.json",
                url=url,
                status_http=500,
                tamanho_bytes=0,
                duracao_ms=duracao_ms,
                tentativas_retry=config.HTTP_TENTATIVAS,
                sucesso=False,
                mensagem_erro=str(e),
            )

    # Etapa 2: Agregação e cálculo de severidade
    log.info("Etapa 2/3: Agregação e cálculo de severidade por UF × Mês...")
    usar_backup = politica == "backup"

    try:
        df_agregado = agrega_uf_mes.agregar()

        if ano_inicio or ano_fim:
            ini_str = f"{ano_inicio or 2014}-01"
            fim_str = f"{ano_fim or 2026}-12"
            df_agregado = df_agregado[df_agregado["ano_mes"].between(ini_str, fim_str)].copy()

        with BackupManager.gerenciar_com_seguranca(DESTINO_FINAL, ativar_backup=usar_backup, logger=log):
            DESTINO_FINAL.parent.mkdir(parents=True, exist_ok=True)
            df_agregado.to_parquet(DESTINO_FINAL, index=False)

        agrega_uf_mes.escrever_cobertura(df_agregado)
        tamanho = DESTINO_FINAL.stat().st_size

        log.info(
            f"  Monitor de Secas consolidado: {len(df_agregado):,} linhas, "
            f"{len(df_agregado.columns)} colunas ({tamanho / 1e6:.2f} MB)."
        )

        # Etapa 3: Validação
        log.info("Etapa 3/3: Validação dos critérios de aceite do Monitor de Secas...")
        falhas_val = validar.validar(df_agregado)
        if falhas_val > 0:
            log.warning(f"Validação do Monitor de Secas apontou {falhas_val} critério(s) com ressalvas.")

    except Exception as e:
        duracao = time.perf_counter() - t_inicio
        msg = f"Falha na agregação do Monitor de Secas: {e}"
        log.error(msg)
        erros.append(msg)
        return ColetaResult(
            fonte="monitor_secas",
            status="FALHA",
            acao_executada="FALHA_PROCESSAMENTO",
            duracao_segundos=round(duracao, 2),
            chunks_totais=27,
            chunks_baixados=chunks_baixados,
            chunks_reaproveitados=chunks_reaproveitados,
            erros=erros,
        )

    duracao = time.perf_counter() - t_inicio
    acao = "BAIXADO_NOVO" if chunks_baixados > 0 and chunks_reaproveitados == 0 else (
        "ATUALIZADO" if chunks_baixados > 0 else (
            "BACKUP_CRIADO" if usar_backup else "REUTILIZADO"
        )
    )

    return ColetaResult(
        fonte="monitor_secas",
        status="AVISO" if erros else "SUCESSO",
        acao_executada=acao,
        duracao_segundos=round(duracao, 2),
        linhas=len(df_agregado),
        colunas=len(df_agregado.columns),
        arquivo_saida=str(DESTINO_FINAL.relative_to(config.RAIZ)),
        tamanho_bytes=tamanho,
        chunks_totais=27,
        chunks_baixados=chunks_baixados,
        chunks_reaproveitados=chunks_reaproveitados,
        erros=erros,
        detalhes={
            "ufs_monitoradas": int(df_agregado["sigla_uf"].nunique()),
            "meses_cobertos": int(df_agregado["ano_mes"].nunique()),
        }
    )
