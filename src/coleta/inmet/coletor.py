"""Orquestrador do pipeline de dados climáticos do INMET (T-014).

Executa as etapas na sequência:
1. Download de ZIPs anuais (com tolerância a falhas e retentativas)
2. Construção do catálogo de estações
3. Agregação horária -> diária (com corte de horas válidas e filtros físicos)
4. Agregação diária -> mensal (com cálculo de extremos e veranicos)
5. Validação de critérios de aceite e exportação de relatórios
"""

from __future__ import annotations

import logging
import shutil
import time
from collections import Counter
from pathlib import Path

import pandas as pd

from ... import config
from ...logging_config import BackupManager, DownloadLogger, get_logger, prompt_confirmacao
from ..base import ColetaResult, calcular_tamanho_caminho
from . import agrega_dia, agrega_mes, catalogo, download, validar

SAIDA_FINAL = config.DATA_INTERIM / "clima_estacao_mes.parquet"
SAIDA_DIARIA = config.DATA_INTERIM / "clima_estacao_dia.parquet"
SAIDA_RAW_DIARIA = config.RAW_INMET / "clima_estacao_dia.parquet"
SAIDA_CATALOGO = config.DATA_INTERIM / "catalogo_estacoes.csv"
SAIDA_RAW_CATALOGO = config.DATA_RAW / "catalogo_estacoes.csv"


def _garantir_compatibilidade_arquivos() -> None:
    """Garante que catalogo e diaria estejam acessíveis tanto em interim quanto em raw."""
    if SAIDA_RAW_CATALOGO.exists() and not SAIDA_CATALOGO.exists():
        SAIDA_CATALOGO.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(SAIDA_RAW_CATALOGO, SAIDA_CATALOGO)
    elif SAIDA_CATALOGO.exists() and not SAIDA_RAW_CATALOGO.exists():
        shutil.copy2(SAIDA_CATALOGO, SAIDA_RAW_CATALOGO)

    if SAIDA_RAW_DIARIA.exists() and not SAIDA_DIARIA.exists():
        SAIDA_DIARIA.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(SAIDA_RAW_DIARIA, SAIDA_DIARIA)


def executar_coleta(
    overwrite: str = 'skip',  # 'skip' | 'force' | 'update' | 'backup'
    ano_inicio: int | None = None,
    ano_fim: int | None = None,
    logger: logging.Logger | None = None,
    download_logger: DownloadLogger | None = None,
    interativo: bool = False,
) -> ColetaResult:
    """Executa o pipeline completo do INMET conforme a política de sobrescrita."""
    log = logger or get_logger("inmet")
    t_inicio = time.perf_counter()

    config.garantir_pastas()
    _garantir_compatibilidade_arquivos()

    dl_logger = download_logger or DownloadLogger(config.RAW_INMET)

    ano_ini = ano_inicio or config.ANO_INICIO_CLIMA
    ano_f = ano_fim or config.ANO_FIM_CLIMA
    anos = list(range(ano_ini, ano_f + 1))

    politica = overwrite.lower()
    if interativo and SAIDA_FINAL.exists():
        escolha = prompt_confirmacao(SAIDA_FINAL, log)
        if escolha == "cancel":
            return ColetaResult(
                fonte="inmet",
                status="PULADO",
                acao_executada="PULADO_PELO_USUARIO",
                duracao_segundos=round(time.perf_counter() - t_inicio, 2),
                arquivo_saida=str(SAIDA_FINAL.relative_to(config.RAIZ)),
            )
        politica = escolha

    # Verificação rápida no modo skip
    if politica == "skip" and SAIDA_FINAL.exists() and ano_inicio is None and ano_fim is None:
        try:
            df_existente = pd.read_parquet(SAIDA_FINAL)
            tamanho = SAIDA_FINAL.stat().st_size
            log.info(
                f"Arquivo final INMET já existe ({len(df_existente):,} linhas mensais). "
                f"Pulando coleta (skip)."
            )
            return ColetaResult(
                fonte="inmet",
                status="SUCESSO",
                acao_executada="REUTILIZADO",
                duracao_segundos=round(time.perf_counter() - t_inicio, 2),
                linhas=len(df_existente),
                colunas=len(df_existente.columns),
                arquivo_saida=str(SAIDA_FINAL.relative_to(config.RAIZ)),
                tamanho_bytes=tamanho,
                chunks_totais=len(anos),
                chunks_baixados=0,
                chunks_reaproveitados=len(anos),
                detalhes={
                    "estacoes": int(df_existente["codigo_estacao"].nunique()),
                    "meses": int(df_existente["ano_mes"].nunique()),
                },
            )
        except Exception as e:
            log.warning(f"Arquivo final corrompido ({e}). Reexecutando pipeline...")

    log.info(f"Iniciando pipeline INMET ({ano_ini}-{ano_f}) com política: {politica}")

    erros: list[str] = []
    chunks_baixados = 0
    chunks_reaproveitados = 0

    # Etapa 1: Download de ZIPs anuais
    log.info("Etapa 1/4: Verificação / Download dos ZIPs anuais...")
    for ano in anos:
        destino_zip = download.caminho_zip(ano)
        url_zip = download.URL_MODELO.format(ano=ano)
        t0 = time.perf_counter()

        deve_baixar = (
            politica == "force"
            or not destino_zip.exists()
            or (politica == "update" and ano == anos[-1])
        )

        if not deve_baixar:
            try:
                download.verificar_zip(destino_zip)
                chunks_reaproveitados += 1
                log.debug(f"  {ano}.zip já existe e está íntegro (reaproveitado).")
                continue
            except Exception:
                log.warning(f"  {ano}.zip corrompido. Baixando novamente...")

        try:
            log.info(f"  Baixando {ano}.zip ({url_zip})...")
            baixou = download.rede.baixar_arquivo(url_zip, destino_zip, forcar=(politica == "force"))
            duracao_ms = (time.perf_counter() - t0) * 1000
            tamanho = destino_zip.stat().st_size if destino_zip.exists() else 0

            dl_logger.registrar(
                identificador_chunk=f"{ano}.zip",
                url=url_zip,
                status_http=200,
                tamanho_bytes=tamanho,
                duracao_ms=duracao_ms,
                tentativas_retry=1,
                sucesso=True,
            )
            if baixou:
                chunks_baixados += 1
            else:
                chunks_reaproveitados += 1
        except Exception as e:
            msg_erro = f"Falha no download de {ano}.zip: {e}"
            log.error(msg_erro)
            erros.append(msg_erro)
            duracao_ms = (time.perf_counter() - t0) * 1000
            dl_logger.registrar(
                identificador_chunk=f"{ano}.zip",
                url=url_zip,
                status_http=500,
                tamanho_bytes=0,
                duracao_ms=duracao_ms,
                tentativas_retry=config.HTTP_TENTATIVAS,
                sucesso=False,
                mensagem_erro=str(e),
            )

    # Etapa 2: Construção do Catálogo de Estações
    log.info("Etapa 2/4: Montagem do catálogo de estações meteorológicas...")
    try:
        bruto_cat = catalogo.coletar(anos)
        df_catalogo = catalogo.consolidar(bruto_cat)
        SAIDA_CATALOGO.parent.mkdir(parents=True, exist_ok=True)
        df_catalogo.to_csv(SAIDA_CATALOGO, index=False, encoding="utf-8")
        if SAIDA_RAW_CATALOGO.parent.exists():
            df_catalogo.to_csv(SAIDA_RAW_CATALOGO, index=False, encoding="utf-8")
        log.info(f"  Catálogo gerado: {len(df_catalogo)} estações ativas.")
    except Exception as e:
        msg = f"Falha na geração do catálogo de estações: {e}"
        log.warning(msg)
        erros.append(msg)

    # Etapa 3: Agregação Horária -> Diária
    log.info("Etapa 3/4: Agregação horária para diária por estação...")
    SAIDA_DIARIA.mkdir(parents=True, exist_ok=True)
    contador_limpeza = Counter()
    total_linhas_diarias = 0

    for ano in anos:
        destino_diario = SAIDA_DIARIA / f"clima_estacao_dia_{ano}.parquet"
        if politica in ("skip", "backup") and destino_diario.exists() and not politica == "force":
            try:
                df_dia = pd.read_parquet(destino_diario)
                total_linhas_diarias += len(df_dia)
                log.debug(f"  Diário {ano} já existe ({len(df_dia):,} linhas).")
                continue
            except Exception:
                pass

        try:
            df_dia = agrega_dia.processar_ano(ano, contador_limpeza)
            df_dia.to_parquet(destino_diario, index=False)
            total_linhas_diarias += len(df_dia)
            log.info(f"  Diário {ano}: {len(df_dia):,} dias-estação agregados.")
        except Exception as e:
            msg = f"Falha na agregação diária de {ano}: {e}"
            log.warning(msg)
            erros.append(msg)

    # Etapa 4: Agregação Diária -> Mensal
    log.info("Etapa 4/4: Agregação diária para mensal (cálculo de extremos e veranicos)...")
    usar_backup = politica == "backup"

    try:
        entrada_diaria_path = SAIDA_DIARIA if any(SAIDA_DIARIA.glob("*.parquet")) else SAIDA_RAW_DIARIA
        diario_completo = pd.read_parquet(entrada_diaria_path)
        log.info(f"  Lidas {len(diario_completo):,} linhas diárias para agregação mensal.")

        df_mensal = agrega_mes.agregar(diario_completo)

        with BackupManager.gerenciar_com_seguranca(SAIDA_FINAL, ativar_backup=usar_backup, logger=log):
            SAIDA_FINAL.parent.mkdir(parents=True, exist_ok=True)
            df_mensal.to_parquet(SAIDA_FINAL, index=False)

        tamanho_mensal = SAIDA_FINAL.stat().st_size
        log.info(
            f"  INMET mensal consolidado: {len(df_mensal):,} linhas, "
            f"{len(df_mensal.columns)} colunas ({tamanho_mensal / 1e6:.2f} MB)."
        )

        # Executar validação de qualidade
        log.info("Executando validação de consistência e exportando métricas de cobertura...")
        if SAIDA_CATALOGO.exists():
            df_cat = pd.read_csv(SAIDA_CATALOGO)
            falhas_val = validar.validar(df_cat, diario_completo)
            if falhas_val > 0:
                log.warning(f"Validação do INMET apontou {falhas_val} critério(s) com avisos/falhas.")
        
    except Exception as e:
        duracao = time.perf_counter() - t_inicio
        msg = f"Falha na consolidação mensal do INMET: {e}"
        log.error(msg)
        erros.append(msg)
        return ColetaResult(
            fonte="inmet",
            status="FALHA",
            acao_executada="FALHA_PROCESSAMENTO",
            duracao_segundos=round(duracao, 2),
            chunks_totais=len(anos),
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
        fonte="inmet",
        status="AVISO" if erros else "SUCESSO",
        acao_executada=acao,
        duracao_segundos=round(duracao, 2),
        linhas=len(df_mensal),
        colunas=len(df_mensal.columns),
        arquivo_saida=str(SAIDA_FINAL.relative_to(config.RAIZ)),
        tamanho_bytes=tamanho_mensal,
        chunks_totais=len(anos),
        chunks_baixados=chunks_baixados,
        chunks_reaproveitados=chunks_reaproveitados,
        erros=erros,
        detalhes={
            "estacoes": int(df_mensal["codigo_estacao"].nunique()),
            "meses": int(df_mensal["ano_mes"].nunique()),
            "linhas_diarias": total_linhas_diarias,
        }
    )
