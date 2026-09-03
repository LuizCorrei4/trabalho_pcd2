"""Coletor oficial do Banco Central (SGS - Séries Macroeconômicas - T-013).

Baixa e consolida as séries:
- 1: Dólar PTAX venda (média mensal e último dia útil)
- 433: IPCA variação mensal (ipca_mm e cálculo de índice base)
- 432: Selic meta (% a.a. no fim do mês)
- 11: Selic efetiva (% a.d.u. composta mensalmente)
- 189: IGP-M mensal
"""

from __future__ import annotations

import logging
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests

from ... import config
from ...logging_config import BackupManager, DownloadLogger, get_logger, prompt_confirmacao
from ..base import ColetaResult

DIR_RAW = config.DATA_RAW / "bcb_var_macroeconômicas"
DIR_RAW_BCB = config.DATA_RAW / "bcb"
DIR_INTERIM = config.DATA_INTERIM

SAIDA_MACRO = DIR_INTERIM / "macro_br_mes.parquet"
SAIDA_MACRO_CSV = DIR_INTERIM / "macro_br_mes.csv"
SAIDA_PARQUET_DIR = DIR_INTERIM / "parquet" / "macro_br_mes.parquet"
SAIDA_QA = DIR_INTERIM / "qa_T-013_bcb.md"

URL_SGS = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"

SERIES = {
    "dolar_ptax": 1,
    "ipca_mm": 433,
    "selic_meta": 432,
    "selic_efetiva": 11,
    "igpm": 189,
}

BASE_IPCA = "2015-01"
REFERENCIAS = {
    "dolar médio 2020-03 (pico da pandemia)": ("dolar_ptax_medio", "2020-03", 4.90, 0.10),
    "dólar fim de 2022-12": ("dolar_ptax_fim", "2022-12", 5.22, 0.10),
    "Selic meta em 2016-12": ("selic", "2016-12", 13.75, 0.01),
}
REFERENCIAS_IPCA_ANO = {2015: 10.67, 2016: 6.29, 2021: 10.06, 2022: 5.79}
PAUSA_S = 0.3


def _para_numero(serie: pd.Series) -> pd.Series:
    limpa = serie.astype("string").str.strip().str.replace(",", ".", regex=False)
    return pd.to_numeric(limpa, errors="coerce")


def _blocos(inicio: date, fim: date, anos: int = 10) -> list[tuple[date, date]]:
    blocos = []
    ini = inicio
    while ini <= fim:
        prox = date(min(ini.year + anos, fim.year + 1), 1, 1)
        blocos.append((ini, min(fim, date(prox.year, 1, 1) - pd.Timedelta(days=1).to_pytimedelta())))
        ini = prox
    return blocos


def busca_serie(
    codigo: int,
    inicio: date,
    fim: date,
    tentativas: int = 4,
    download_logger: DownloadLogger | None = None,
    logger: logging.Logger | None = None,
) -> pd.DataFrame:
    pedacos = []
    t0 = time.perf_counter()

    for bloco_ini, bloco_fim in _blocos(inicio, fim):
        params = {
            "formato": "json",
            "dataInicial": bloco_ini.strftime("%d/%m/%Y"),
            "dataFinal": bloco_fim.strftime("%d/%m/%Y"),
        }
        url = URL_SGS.format(codigo=codigo)
        dados = None

        for tentativa in range(1, tentativas + 1):
            try:
                r = requests.get(url, params=params, timeout=120)
                r.raise_for_status()
                dados = r.json()
                duracao_ms = (time.perf_counter() - t0) * 1000
                if download_logger:
                    download_logger.registrar(
                        identificador_chunk=f"sgs_{codigo}_{bloco_ini}_{bloco_fim}",
                        url=url,
                        status_http=200,
                        tamanho_bytes=len(r.content),
                        duracao_ms=duracao_ms,
                        tentativas_retry=tentativa,
                        sucesso=True,
                    )
                break
            except Exception as e:
                if tentativa == tentativas:
                    duracao_ms = (time.perf_counter() - t0) * 1000
                    if download_logger:
                        download_logger.registrar(
                            identificador_chunk=f"sgs_{codigo}_{bloco_ini}_{bloco_fim}",
                            url=url,
                            status_http=500,
                            tamanho_bytes=0,
                            duracao_ms=duracao_ms,
                            tentativas_retry=tentativa,
                            sucesso=False,
                            mensagem_erro=str(e),
                        )
                    raise RuntimeError(f"série {codigo} [{bloco_ini}..{bloco_fim}]: {e}") from e
                espera = 2**tentativa
                time.sleep(espera)

        if not dados:
            continue

        df = pd.DataFrame(dados)
        df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y")
        df["valor"] = _para_numero(df["valor"])

        pedacos.append(df[["data", "valor"]])
        time.sleep(PAUSA_S)

    if not pedacos:
        return pd.DataFrame()

    completa = pd.concat(pedacos, ignore_index=True).drop_duplicates("data")
    return completa.sort_values("data").reset_index(drop=True)


def _mensaliza(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["ano_mes"] = df["data"].dt.to_period("M").dt.to_timestamp()
    return df


def _indice_base(variacao_pct: pd.Series, ano_mes: pd.Series) -> pd.Series:
    fator = (1 + variacao_pct / 100).cumprod()
    base = fator[ano_mes.dt.to_period("M").astype(str) == BASE_IPCA]
    if base.empty:
        # Se 2015-01 não estiver na série, usa o primeiro mês como base
        return fator / fator.iloc[0] * 100
    return fator / base.iloc[0] * 100


def apara_incompletos(macro: pd.DataFrame) -> pd.DataFrame:
    completos = macro.notna().all(axis=1)
    if completos.all():
        return macro
    ultimo = completos[completos].index.max()
    return macro.loc[:ultimo].reset_index(drop=True)


def executar_coleta(
    overwrite: str = 'skip',  # 'skip' | 'force' | 'update' | 'backup'
    ano_inicio: int | None = None,
    ano_fim: int | None = None,
    logger: logging.Logger | None = None,
    download_logger: DownloadLogger | None = None,
    interativo: bool = False,
) -> ColetaResult:
    """Executa a coleta das séries macroeconômicas do Banco Central."""
    log = logger or get_logger("bcb")
    t_inicio = time.perf_counter()

    config.garantir_pastas()
    DIR_RAW.mkdir(parents=True, exist_ok=True)
    DIR_RAW_BCB.mkdir(parents=True, exist_ok=True)
    DIR_INTERIM.mkdir(parents=True, exist_ok=True)

    dl_logger = download_logger or DownloadLogger(DIR_RAW)

    politica = overwrite.lower()
    if interativo and SAIDA_MACRO.exists():
        escolha = prompt_confirmacao(SAIDA_MACRO, log)
        if escolha == "cancel":
            return ColetaResult(
                fonte="bcb",
                status="PULADO",
                acao_executada="PULADO_PELO_USUARIO",
                duracao_segundos=round(time.perf_counter() - t_inicio, 2),
                arquivo_saida=str(SAIDA_MACRO.relative_to(config.RAIZ)),
            )
        politica = escolha

    # Verificação no modo skip
    if politica == "skip" and SAIDA_MACRO.exists() and ano_inicio is None and ano_fim is None:
        try:
            df_existente = pd.read_parquet(SAIDA_MACRO)
            tamanho = SAIDA_MACRO.stat().st_size
            log.info(
                f"Arquivo macroeconômico já existe ({len(df_existente):,} meses). "
                f"Pulando coleta (skip)."
            )
            return ColetaResult(
                fonte="bcb",
                status="SUCESSO",
                acao_executada="REUTILIZADO",
                duracao_segundos=round(time.perf_counter() - t_inicio, 2),
                linhas=len(df_existente),
                colunas=len(df_existente.columns),
                arquivo_saida=str(SAIDA_MACRO.relative_to(config.RAIZ)),
                tamanho_bytes=tamanho,
                chunks_totais=len(SERIES),
                chunks_baixados=0,
                chunks_reaproveitados=len(SERIES),
                detalhes={
                    "meses": len(df_existente),
                    "inicio": str(df_existente["ano_mes"].min()),
                    "fim": str(df_existente["ano_mes"].max()),
                },
            )
        except Exception as e:
            log.warning(f"Arquivo existente corrompido ({e}). Reprocessando...")

    log.info(f"Iniciando coleta de séries BCB/SGS com política: {politica}")

    dt_inicio = date(ano_inicio or 2014, 1, 1)
    dt_fim = date(ano_fim, 12, 31) if ano_fim else date.today()

    erros: list[str] = []
    brutos: dict[str, pd.DataFrame] = {}

    for nome, codigo in SERIES.items():
        log.info(f"  Coletando série {codigo} ({nome})...")
        try:
            serie = busca_serie(codigo, dt_inicio, dt_fim, download_logger=dl_logger, logger=log)
            if not serie.empty:
                brutos[nome] = serie
                serie.to_parquet(DIR_RAW / f"sgs_{codigo}_{nome}.parquet", index=False)
                serie.to_parquet(DIR_RAW_BCB / f"sgs_{codigo}_{nome}.parquet", index=False)
            else:
                erros.append(f"Série {codigo} ({nome}) retornou vazia")
        except Exception as e:
            msg = f"Falha na série {codigo} ({nome}): {e}"
            log.error(msg)
            erros.append(msg)

    if not brutos or len(brutos) < len(SERIES):
        duracao = time.perf_counter() - t_inicio
        return ColetaResult(
            fonte="bcb",
            status="FALHA" if not brutos else "AVISO",
            acao_executada="FALHA_DOWNLOAD",
            duracao_segundos=round(duracao, 2),
            erros=erros,
        )

    # Processamento e agregação macroeconômica
    dolar = _mensaliza(brutos["dolar_ptax"])
    macro = dolar.groupby("ano_mes", as_index=False).agg(
        dolar_ptax_medio=("valor", "mean"),
        dolar_ptax_fim=("valor", "last"),
    )

    selic = _mensaliza(brutos["selic_meta"]).groupby("ano_mes", as_index=False).agg(
        selic=("valor", "last")
    )

    efetiva = _mensaliza(brutos["selic_efetiva"])
    efetiva["fator"] = 1 + efetiva["valor"] / 100
    efetiva = efetiva.groupby("ano_mes", as_index=False).agg(fator=("fator", "prod"))
    efetiva["selic_efetiva_am"] = (efetiva["fator"] - 1) * 100

    ipca = _mensaliza(brutos["ipca_mm"]).rename(columns={"valor": "ipca_mm"})[["ano_mes", "ipca_mm"]]
    igpm = _mensaliza(brutos["igpm"]).rename(columns={"valor": "igpm"})[["ano_mes", "igpm"]]

    for outro in (selic, efetiva[["ano_mes", "selic_efetiva_am"]], ipca, igpm):
        macro = macro.merge(outro, on="ano_mes", how="outer")

    macro = macro.sort_values("ano_mes").reset_index(drop=True)
    macro["ipca_indice_base"] = _indice_base(macro["ipca_mm"], macro["ano_mes"])
    macro = apara_incompletos(macro)

    colunas_ordenadas = [
        "ano_mes",
        "dolar_ptax_medio",
        "dolar_ptax_fim",
        "ipca_mm",
        "ipca_indice_base",
        "selic",
        "selic_efetiva_am",
        "igpm",
    ]
    df_final = macro[[c for c in colunas_ordenadas if c in macro.columns]]

    usar_backup = politica == "backup"
    with BackupManager.gerenciar_com_seguranca(SAIDA_MACRO, ativar_backup=usar_backup, logger=log):
        SAIDA_MACRO.parent.mkdir(parents=True, exist_ok=True)
        df_final.to_parquet(SAIDA_MACRO, index=False)
        df_final.to_csv(SAIDA_MACRO_CSV, index=False, encoding="utf-8")

        # Compatibilidade com interim/parquet
        SAIDA_PARQUET_DIR.parent.mkdir(parents=True, exist_ok=True)
        df_final.to_parquet(SAIDA_PARQUET_DIR, index=False)

    tamanho = SAIDA_MACRO.stat().st_size
    duracao = time.perf_counter() - t_inicio
    acao = "BACKUP_CRIADO" if usar_backup else ("BAIXADO_NOVO" if politica == "force" else "ATUALIZADO")

    log.info(
        f"Dados macroeconômicos consolidados: {len(df_final):,} meses "
        f"({tamanho / 1e3:.1f} KB)."
    )

    return ColetaResult(
        fonte="bcb",
        status="AVISO" if erros else "SUCESSO",
        acao_executada=acao,
        duracao_segundos=round(duracao, 2),
        linhas=len(df_final),
        colunas=len(df_final.columns),
        arquivo_saida=str(SAIDA_MACRO.relative_to(config.RAIZ)),
        tamanho_bytes=tamanho,
        chunks_totais=len(SERIES),
        chunks_baixados=len(SERIES),
        erros=erros,
        detalhes={
            "meses": len(df_final),
            "inicio": str(df_final["ano_mes"].min()),
            "fim": str(df_final["ano_mes"].max()),
        }
    )
