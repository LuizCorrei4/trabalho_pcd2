"""Orquestrador do Pipeline de Tratamento e Junção Final dos Dados.

Coordena a execução ordenada dos scripts da pasta src/tratamento:
  1. T-021: 21_clima_uf_mes.py (agregação espacial estações -> UF × mês)
  2. T-024: 24_junta.py (LEFT JOIN das 5 fontes -> fato_alimentos_uf_mes)
  3. T-025: 25_combustiveis.py (LEFT JOIN dos combustíveis ANP -> fato_alimentos_combustiveis_uf_mes)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .. import config
from ..coleta.base import ColetaResult
from ..logging_config import BackupManager, get_logger


@dataclass
class EtapaTratamentoMeta:
    etapa: str
    descricao: str
    status: str
    duracao_segundos: float
    arquivo_saida: str
    linhas: int = 0
    colunas: int = 0
    tamanho_bytes: int = 0
    erros: list[str] | None = None


def executar_pipeline_tratamento(
    overwrite: str = "skip",
    logger: logging.Logger | None = None,
) -> list[ColetaResult]:
    """Executa a sequência completa de tratamento e junção de dados.

    Args:
        overwrite: Política de sobrescrita ('skip', 'force', 'update', 'backup').
        logger: Logger configurado da sessão.

    Returns:
        Lista de ColetaResult contendo os metadados de cada etapa.
    """
    log = logger or get_logger("tratamento")
    resultados: list[ColetaResult] = []

    # ----------------------------------------------------------------------- #
    # Etapa 1: Clima UF x Mês (T-021)                                          #
    # ----------------------------------------------------------------------- #
    t0 = time.perf_counter()
    origem_clima = config.DATA_INTERIM / "clima_estacao_mes.parquet"
    saida_clima = config.DATA_INTERIM / "clima_uf_mes.parquet"

    log.info("\n--- [Tratamento 1/3] Agregação Climática: Estações -> UF × Mês (T-021) ---")
    if overwrite == "skip" and saida_clima.exists():
        df_c = pd.read_parquet(saida_clima)
        dur = round(time.perf_counter() - t0, 2)
        log.info(f"Arquivo já existe ({len(df_c):,} linhas). Pulando etapa (skip).")
        resultados.append(
            ColetaResult(
                fonte="clima_uf_mes",
                status="SUCESSO",
                acao_executada="REUTILIZADO",
                duracao_segundos=dur,
                linhas=len(df_c),
                colunas=df_c.shape[1],
                arquivo_saida=str(saida_clima.relative_to(config.RAIZ)),
                tamanho_bytes=saida_clima.stat().st_size,
            )
        )
    else:
        try:
            if not origem_clima.exists():
                raise FileNotFoundError(f"Arquivo de entrada não encontrado: {origem_clima}")

            import importlib
            mod_clima = importlib.import_module("src.tratamento.21_clima_uf_mes")
            
            estacoes = pd.read_parquet(origem_clima)
            df_uf_mes = mod_clima.agrega_uf_mes(estacoes)
            mod_clima.valida_chaves(df_uf_mes, "clima_uf_mes")
            
            saida_clima.parent.mkdir(parents=True, exist_ok=True)
            df_uf_mes.to_parquet(saida_clima, index=False)
            
            dur = round(time.perf_counter() - t0, 2)
            log.info(f"Clima agregado por UF concluído: {len(df_uf_mes):,} linhas, {df_uf_mes.shape[1]} colunas ({dur}s).")
            resultados.append(
                ColetaResult(
                    fonte="clima_uf_mes",
                    status="SUCESSO",
                    acao_executada="ATUALIZADO" if saida_clima.exists() else "BAIXADO_NOVO",
                    duracao_segundos=dur,
                    linhas=len(df_uf_mes),
                    colunas=df_uf_mes.shape[1],
                    arquivo_saida=str(saida_clima.relative_to(config.RAIZ)),
                    tamanho_bytes=saida_clima.stat().st_size,
                )
            )
        except Exception as e:
            dur = round(time.perf_counter() - t0, 2)
            log.exception(f"Erro na agregação climática: {e}")
            resultados.append(
                ColetaResult(
                    fonte="clima_uf_mes",
                    status="FALHA",
                    acao_executada="FALHA_PROCESSAMENTO",
                    duracao_segundos=dur,
                    arquivo_saida=str(saida_clima.relative_to(config.RAIZ)),
                    erros=[str(e)],
                )
            )

    # ----------------------------------------------------------------------- #
    # Etapa 2: Junção Final das 5 Fontes (T-024)                              #
    # ----------------------------------------------------------------------- #
    t0 = time.perf_counter()
    saida_fato = config.DATA_PROCESSED / "fato_alimentos_uf_mes.parquet"
    log.info("\n--- [Tratamento 2/3] Junção Central: fato_alimentos_uf_mes (T-024) ---")

    if overwrite == "skip" and saida_fato.exists():
        df_f = pd.read_parquet(saida_fato)
        dur = round(time.perf_counter() - t0, 2)
        log.info(f"Tabela fato já existe ({len(df_f):,} linhas). Pulando junção (skip).")
        resultados.append(
            ColetaResult(
                fonte="fato_alimentos",
                status="SUCESSO",
                acao_executada="REUTILIZADO",
                duracao_segundos=dur,
                linhas=len(df_f),
                colunas=df_f.shape[1],
                arquivo_saida=str(saida_fato.relative_to(config.RAIZ)),
                tamanho_bytes=saida_fato.stat().st_size,
            )
        )
    else:
        try:
            import importlib
            mod_junta = importlib.import_module("src.tratamento.24_junta")
            
            # Executa a junção completa
            fato = mod_junta.junta()
            saida_fato.parent.mkdir(parents=True, exist_ok=True)
            fato.to_parquet(saida_fato, index=False)
            
            # Gera o dicionário de variáveis
            dicionario = mod_junta.monta_dicionario(fato)
            (config.OUTPUTS / "tabelas").mkdir(parents=True, exist_ok=True)
            dicionario.to_csv(config.OUTPUTS / "tabelas" / "dicionario_variaveis.csv", index=False, encoding="utf-8")
            
            dur = round(time.perf_counter() - t0, 2)
            log.info(f"Tabela fato gerada com sucesso: {len(fato):,} linhas, {fato.shape[1]} colunas ({dur}s).")
            resultados.append(
                ColetaResult(
                    fonte="fato_alimentos",
                    status="SUCESSO",
                    acao_executada="ATUALIZADO" if saida_fato.exists() else "BAIXADO_NOVO",
                    duracao_segundos=dur,
                    linhas=len(fato),
                    colunas=fato.shape[1],
                    arquivo_saida=str(saida_fato.relative_to(config.RAIZ)),
                    tamanho_bytes=saida_fato.stat().st_size,
                )
            )
        except Exception as e:
            dur = round(time.perf_counter() - t0, 2)
            log.exception(f"Erro na junção da tabela fato: {e}")
            resultados.append(
                ColetaResult(
                    fonte="fato_alimentos",
                    status="FALHA",
                    acao_executada="FALHA_PROCESSAMENTO",
                    duracao_segundos=dur,
                    arquivo_saida=str(saida_fato.relative_to(config.RAIZ)),
                    erros=[str(e)],
                )
            )

    # ----------------------------------------------------------------------- #
    # Etapa 3: Integração de Combustíveis ANP (T-025)                          #
    # ----------------------------------------------------------------------- #
    t0 = time.perf_counter()
    saida_comb = config.DATA_PROCESSED / "fato_alimentos_combustiveis_uf_mes.parquet"
    log.info("\n--- [Tratamento 3/3] Integração de Combustíveis ANP (T-025) ---")

    if overwrite == "skip" and saida_comb.exists():
        df_fc = pd.read_parquet(saida_comb)
        dur = round(time.perf_counter() - t0, 2)
        log.info(f"Tabela fato com combustíveis já existe ({len(df_fc):,} linhas). Pulando etapa (skip).")
        resultados.append(
            ColetaResult(
                fonte="fato_combustiveis",
                status="SUCESSO",
                acao_executada="REUTILIZADO",
                duracao_segundos=dur,
                linhas=len(df_fc),
                colunas=df_fc.shape[1],
                arquivo_saida=str(saida_comb.relative_to(config.RAIZ)),
                tamanho_bytes=saida_comb.stat().st_size,
            )
        )
    else:
        try:
            import importlib
            mod_comb = importlib.import_module("src.tratamento.25_combustiveis")
            
            fato_comb = mod_comb.junta()
            saida_comb.parent.mkdir(parents=True, exist_ok=True)
            fato_comb.to_parquet(saida_comb, index=False)
            
            dic_comb = mod_comb.monta_dicionario(fato_comb)
            dic_comb.to_csv(
                config.OUTPUTS / "tabelas" / "dicionario_variaveis_combustiveis.csv",
                index=False,
                encoding="utf-8",
            )
            
            dur = round(time.perf_counter() - t0, 2)
            log.info(
                f"Tabela fato com combustíveis gerada: {len(fato_comb):,} linhas, "
                f"{fato_comb.shape[1]} colunas ({dur}s)."
            )
            resultados.append(
                ColetaResult(
                    fonte="fato_combustiveis",
                    status="SUCESSO",
                    acao_executada="ATUALIZADO" if saida_comb.exists() else "BAIXADO_NOVO",
                    duracao_segundos=dur,
                    linhas=len(fato_comb),
                    colunas=fato_comb.shape[1],
                    arquivo_saida=str(saida_comb.relative_to(config.RAIZ)),
                    tamanho_bytes=saida_comb.stat().st_size,
                )
            )
        except Exception as e:
            dur = round(time.perf_counter() - t0, 2)
            log.exception(f"Erro na integração de combustíveis ao fato: {e}")
            resultados.append(
                ColetaResult(
                    fonte="fato_combustiveis",
                    status="FALHA",
                    acao_executada="FALHA_PROCESSAMENTO",
                    duracao_segundos=dur,
                    arquivo_saida=str(saida_comb.relative_to(config.RAIZ)),
                    erros=[str(e)],
                )
            )

    return resultados
