"""Coletor oficial de Estimativas de Safra (LSPA e PAM - IBGE / SIDRA - T-012).

Baixa e consolida:
1. Tabela 6588 (LSPA) - Expectativas e revisões mensais de safra por UF e produto
2. Tabelas 1612 e 1613 (PAM) - Produção agrícola anual realizada por UF
"""

from __future__ import annotations

import logging
import time
import unicodedata
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from ... import config, ufs as mod_ufs
from ...logging_config import BackupManager, DownloadLogger, get_logger, prompt_confirmacao
from ..base import ColetaResult

DIR_RAW = config.DATA_RAW / "estimativas_safra_UF"
DIR_RAW_SIDRA = config.DATA_RAW / "sidra"
DIR_INTERIM = config.DATA_INTERIM
CAMINHO_DIM_UF = config.DIM_UF

SAIDA_SAFRA = DIR_INTERIM / "safra_uf_mes.parquet"
SAIDA_PRODUCAO = DIR_INTERIM / "producao_uf_ano.parquet"
SAIDA_QA = DIR_INTERIM / "qa_T-012_sidra.md"

URL_VALORES = "https://apisidra.ibge.gov.br/values"
URL_METADADOS = "https://servicodados.ibge.gov.br/api/v3/agregados/{tabela}/metadados"

NIVEIS = {"BR": "n1", "REGIAO": "n2", "UF": "n3", "MUNICIPIO": "n6"}
AUSENTES = {"...", "..", ".", "-", "x", "X", "..-", ""}
PAUSA_S = 0.3

PRODUTOS_LSPA = {
    "arroz": ["39432"],
    "feijao": ["39436", "39437", "39438"],
    "cafe": ["39454", "39455"],
    "banana": ["39449"],
    "batata_inglesa": ["39450", "39451", "39452"],
    "tomate": ["39470"],
    "trigo": ["39445"],
    "mandioca": ["39467"],
    "cana_de_acucar": ["39456"],
    "soja": ["39443"],
    "milho": ["39441", "39442"],
}

PRODUTOS_PAM_TEMPORARIAS = {
    "arroz": ["2692"],
    "feijao": ["2702"],
    "batata_inglesa": ["2695"],
    "tomate": ["2715"],
    "trigo": ["2716"],
    "mandioca": ["2708"],
    "cana_de_acucar": ["2696"],
    "soja": ["2713"],
    "milho": ["2711"],
}

PRODUTOS_PAM_PERMANENTES = {
    "cafe": ["2723"],
    "banana": ["2720"],
}

VARIAVEIS_LSPA = {
    "109": "area_plantada_ha",
    "216": "area_colhida_ha",
    "35": "producao_t",
    "36": "rendimento_kg_ha",
}

VARIAVEIS_PAM_TEMP = {
    "109": "area_plantada_ha",
    "216": "area_colhida_ha",
    "214": "producao_t",
    "112": "rendimento_kg_ha",
    "215": "valor_producao_mil_brl",
}

VARIAVEIS_PAM_PERM = {
    "2313": "area_plantada_ha",
    "216": "area_colhida_ha",
    "214": "producao_t",
    "112": "rendimento_kg_ha",
    "215": "valor_producao_mil_brl",
}


def normaliza_texto(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode("ascii")
    return s.lower().strip()


def _slug(rotulo: str) -> str:
    s = normaliza_texto(rotulo).replace("(", " ").replace(")", " ")
    return "_".join(s.split())


def _para_numero(serie: pd.Series) -> pd.Series:
    limpa = serie.astype("string").str.strip()
    limpa = limpa.mask(limpa.isin(AUSENTES))
    return pd.to_numeric(limpa, errors="coerce")


def periodo_final(tabela: str, padrao: str) -> str:
    try:
        r = requests.get(URL_METADADOS.format(tabela=tabela), timeout=45)
        r.raise_for_status()
        return str(r.json()["periodicidade"]["fim"])
    except Exception:
        return padrao


def busca_tabela(
    tabela: str,
    variaveis: list[str],
    periodos: str,
    nivel: str = "UF",
    classificacao: str | None = None,
    categorias: list[str] | None = None,
    tentativas: int = 4,
    download_logger: DownloadLogger | None = None,
) -> pd.DataFrame:
    partes = [
        URL_VALORES,
        "t", tabela,
        NIVEIS[nivel], "all",
        "v", ",".join(variaveis),
        "p", periodos,
    ]
    if classificacao and categorias:
        partes += [f"c{classificacao}", ",".join(categorias)]
    url = "/".join(partes)

    t0 = time.perf_counter()

    for tentativa in range(1, tentativas + 1):
        try:
            r = requests.get(url, params={"formato": "json"}, timeout=180)
            r.raise_for_status()
            dados = r.json()
            duracao_ms = (time.perf_counter() - t0) * 1000

            if not isinstance(dados, list) or len(dados) < 2:
                if download_logger:
                    download_logger.registrar(
                        identificador_chunk=f"tab{tabela}_{periodos}_{nivel}",
                        url=url,
                        status_http=200,
                        tamanho_bytes=len(r.content),
                        duracao_ms=duracao_ms,
                        tentativas_retry=tentativa,
                        sucesso=True,
                        mensagem_erro="retorno vazio",
                    )
                return pd.DataFrame()

            cabecalho, corpo = dados[0], dados[1:]
            df = pd.DataFrame(corpo).rename(columns={k: _slug(v) for k, v in cabecalho.items()})
            df["valor"] = _para_numero(df.pop("valor"))

            if download_logger:
                download_logger.registrar(
                    identificador_chunk=f"tab{tabela}_{periodos}_{nivel}",
                    url=url,
                    status_http=200,
                    tamanho_bytes=len(r.content),
                    duracao_ms=duracao_ms,
                    tentativas_retry=tentativa,
                    sucesso=True,
                )

            time.sleep(PAUSA_S)
            return df
        except Exception as e:
            if tentativa == tentativas:
                duracao_ms = (time.perf_counter() - t0) * 1000
                if download_logger:
                    download_logger.registrar(
                        identificador_chunk=f"tab{tabela}_{periodos}_{nivel}",
                        url=url,
                        status_http=500,
                        tamanho_bytes=0,
                        duracao_ms=duracao_ms,
                        tentativas_retry=tentativa,
                        sucesso=False,
                        mensagem_erro=str(e),
                    )
                raise RuntimeError(f"Falha ao consultar SIDRA {url}: {e}") from e
            espera = 2**tentativa
            time.sleep(espera)

    return pd.DataFrame()


def blocos_de_periodo(inicio: int, fim: int, passo: int = 4) -> list[tuple[int, int]]:
    return [(a, min(a + passo - 1, fim)) for a in range(inicio, fim + 1, passo)]


def aplica_dim_uf(df: pd.DataFrame, dim_uf: pd.DataFrame, col_codigo: str) -> pd.DataFrame:
    df = df.copy()
    df["cod_ibge_uf"] = pd.to_numeric(df.pop(col_codigo), errors="coerce").astype("Int64")
    return df.merge(dim_uf, on="cod_ibge_uf", how="left")


def _empilha_produtos(
    tabela: str,
    classificacao: str,
    produtos: dict[str, list[str]],
    variaveis: dict[str, str],
    periodos: str,
    nivel: str,
    download_logger: DownloadLogger | None = None,
    logger: logging.Logger | None = None,
) -> pd.DataFrame:
    pedacos = []
    for canonico, categorias in produtos.items():
        bruto = busca_tabela(
            tabela=tabela,
            variaveis=list(variaveis),
            periodos=periodos,
            nivel=nivel,
            classificacao=classificacao,
            categorias=categorias,
            download_logger=download_logger,
        )
        if bruto.empty:
            continue
        bruto["produto"] = canonico
        pedacos.append(bruto)
        if logger:
            logger.debug(f"  {tabela}/{canonico}: {len(bruto):,} linhas")
    if not pedacos:
        return pd.DataFrame()
    return pd.concat(pedacos, ignore_index=True)


def _identifica_colunas(df: pd.DataFrame) -> tuple[str, str, str, str]:
    def acha(*chaves: str, obrigatorio: bool = True) -> str:
        for c in df.columns:
            if all(k in c for k in chaves):
                return c
        if obrigatorio:
            raise KeyError(f"coluna com {chaves} não encontrada em {list(df.columns)}")
        return ""

    col_local = acha("unidade_da_federacao", "codigo") if any(
        "unidade_da_federacao" in c for c in df.columns
    ) else acha("brasil", "codigo")
    col_periodo = acha("mes", "codigo", obrigatorio=False) or acha("ano", "codigo")
    col_variavel = acha("variavel", "codigo")
    col_categoria = acha("produto", "codigo")
    return col_local, col_periodo, col_variavel, col_categoria


def _pivota_variaveis(
    df: pd.DataFrame, variaveis: dict[str, str], chaves: list[str], col_variavel: str
) -> pd.DataFrame:
    df = df.copy()
    df["variavel"] = df[col_variavel].astype(str).map(variaveis)
    df = df.dropna(subset=["variavel"])
    largo = (
        df.groupby(chaves + ["variavel"], dropna=False)["valor"]
        .sum(min_count=1)
        .unstack("variavel")
        .reset_index()
        .rename_axis(columns=None)
    )
    for nome in variaveis.values():
        if nome not in largo.columns:
            largo[nome] = pd.NA
    return largo


def _agrega_safras(df: pd.DataFrame, chaves: list[str]) -> pd.DataFrame:
    colunas_soma = [
        c for c in ("area_plantada_ha", "area_colhida_ha", "producao_t", "valor_producao_mil_brl")
        if c in df.columns
    ]
    agregado = df.groupby(chaves, as_index=False, dropna=False)[colunas_soma].sum(min_count=1)

    rend_reportado = (
        df.groupby(chaves, as_index=False, dropna=False)
        .agg(n_categorias=("rendimento_kg_ha", "size"), rendimento_reportado=("rendimento_kg_ha", "mean"))
    )
    agregado = agregado.merge(rend_reportado, on=chaves, how="left")

    calculado = (agregado["producao_t"] * 1000) / agregado["area_colhida_ha"].where(
        agregado["area_colhida_ha"] > 0
    )
    agregado["rendimento_kg_ha"] = calculado.where(
        agregado["n_categorias"] > 1, agregado["rendimento_reportado"]
    ).fillna(calculado)
    return agregado.drop(columns=["n_categorias", "rendimento_reportado"])


def coleta_lspa(
    inicio: int,
    fim_periodo: str,
    dim_uf: pd.DataFrame,
    nivel: str = "UF",
    download_logger: DownloadLogger | None = None,
    logger: logging.Logger | None = None,
) -> pd.DataFrame:
    ano_fim = int(fim_periodo[:4])
    partes = []
    for a1, a2 in blocos_de_periodo(inicio, ano_fim):
        p_ini = f"{a1}01"
        p_fim = fim_periodo if a2 == ano_fim else f"{a2}12"
        if logger:
            logger.info(f"LSPA 6588 [{nivel}] período {p_ini}-{p_fim}")
        df_parte = _empilha_produtos(
            "6588", "48", PRODUTOS_LSPA, VARIAVEIS_LSPA, f"{p_ini}-{p_fim}", nivel,
            download_logger=download_logger, logger=logger
        )
        if not df_parte.empty:
            partes.append(df_parte)

    if not partes:
        return pd.DataFrame()

    bruto = pd.concat(partes, ignore_index=True)

    if nivel == "UF":
        DIR_RAW.mkdir(parents=True, exist_ok=True)
        DIR_RAW_SIDRA.mkdir(parents=True, exist_ok=True)
        bruto.to_parquet(DIR_RAW / "lspa_6588_bruto.parquet", index=False)
        bruto.to_parquet(DIR_RAW_SIDRA / "lspa_6588_bruto.parquet", index=False)

    col_local, col_periodo, col_variavel, col_categoria = _identifica_colunas(bruto)
    bruto["ano_mes"] = pd.to_datetime(bruto[col_periodo], format="%Y%m")

    chaves_cat = [col_local, "ano_mes", "produto", col_categoria]
    largo = _pivota_variaveis(bruto, VARIAVEIS_LSPA, chaves_cat, col_variavel)
    df = _agrega_safras(largo, [col_local, "ano_mes", "produto"])

    if nivel == "UF":
        df = aplica_dim_uf(df, dim_uf, col_local)
    else:
        df = df.rename(columns={col_local: "cod_local"})

    df["ano_safra"] = df["ano_mes"].dt.year
    df = df.sort_values(["produto", "ano_mes"] if nivel != "UF" else ["sigla_uf", "produto", "ano_mes"])
    grupo = ["sigla_uf", "produto", "ano_safra"] if nivel == "UF" else ["produto", "ano_safra"]
    df["revisao_pct_prod"] = df.groupby(grupo, dropna=False)["producao_t"].pct_change() * 100

    colunas = (
        ["sigla_uf", "cod_ibge_uf", "nome_uf"] if nivel == "UF" else ["cod_local"]
    ) + [
        "produto",
        "ano_mes",
        "ano_safra",
        "area_plantada_ha",
        "area_colhida_ha",
        "producao_t",
        "rendimento_kg_ha",
        "revisao_pct_prod",
    ]
    return df[[c for c in colunas if c in df.columns]].reset_index(drop=True)


def coleta_pam(
    inicio: int,
    fim: int,
    dim_uf: pd.DataFrame,
    download_logger: DownloadLogger | None = None,
    logger: logging.Logger | None = None,
) -> pd.DataFrame:
    especificacoes = [
        ("1612", "81", PRODUTOS_PAM_TEMPORARIAS, VARIAVEIS_PAM_TEMP, "temporaria"),
        ("1613", "82", PRODUTOS_PAM_PERMANENTES, VARIAVEIS_PAM_PERM, "permanente"),
    ]
    partes = []
    for tabela, classif, produtos, variaveis, lavoura in especificacoes:
        if logger:
            logger.info(f"PAM {tabela} ({lavoura}) período {inicio}-{fim}")
        bruto = _empilha_produtos(
            tabela, classif, produtos, variaveis, f"{inicio}-{fim}", "UF",
            download_logger=download_logger, logger=logger
        )
        if bruto.empty:
            continue

        DIR_RAW.mkdir(parents=True, exist_ok=True)
        DIR_RAW_SIDRA.mkdir(parents=True, exist_ok=True)
        bruto.to_parquet(DIR_RAW / f"pam_{tabela}_bruto.parquet", index=False)
        bruto.to_parquet(DIR_RAW_SIDRA / f"pam_{tabela}_bruto.parquet", index=False)

        col_local, col_periodo, col_variavel, col_categoria = _identifica_colunas(bruto)
        bruto["ano"] = pd.to_numeric(bruto[col_periodo], errors="coerce").astype("Int64")

        largo = _pivota_variaveis(
            bruto, variaveis, [col_local, "ano", "produto", col_categoria], col_variavel
        )
        df = _agrega_safras(largo, [col_local, "ano", "produto"])
        df = aplica_dim_uf(df, dim_uf, col_local)
        df["lavoura"] = lavoura
        partes.append(df)

    if not partes:
        return pd.DataFrame()

    df = pd.concat(partes, ignore_index=True)
    total_br = df.groupby(["produto", "ano"], dropna=False)["producao_t"].transform("sum")
    df["peso_producao_uf"] = df["producao_t"] / total_br.where(total_br > 0)

    colunas = [
        "sigla_uf",
        "cod_ibge_uf",
        "nome_uf",
        "produto",
        "ano",
        "lavoura",
        "area_plantada_ha",
        "area_colhida_ha",
        "producao_t",
        "rendimento_kg_ha",
        "valor_producao_mil_brl",
        "peso_producao_uf",
    ]
    return df[[c for c in colunas if c in df.columns]].sort_values(["produto", "ano", "sigla_uf"]).reset_index(drop=True)


def executar_coleta(
    overwrite: str = 'skip',  # 'skip' | 'force' | 'update' | 'backup'
    ano_inicio: int | None = None,
    ano_fim: int | None = None,
    logger: logging.Logger | None = None,
    download_logger: DownloadLogger | None = None,
    interativo: bool = False,
) -> ColetaResult:
    """Executa a coleta e estruturação das safras LSPA e PAM via SIDRA."""
    log = logger or get_logger("safra")
    t_inicio = time.perf_counter()

    config.garantir_pastas()
    DIR_RAW.mkdir(parents=True, exist_ok=True)
    DIR_RAW_SIDRA.mkdir(parents=True, exist_ok=True)
    DIR_INTERIM.mkdir(parents=True, exist_ok=True)

    dl_logger = download_logger or DownloadLogger(DIR_RAW)

    politica = overwrite.lower()
    if interativo and SAIDA_SAFRA.exists():
        escolha = prompt_confirmacao(SAIDA_SAFRA, log)
        if escolha == "cancel":
            return ColetaResult(
                fonte="safra",
                status="PULADO",
                acao_executada="PULADO_PELO_USUARIO",
                duracao_segundos=round(time.perf_counter() - t_inicio, 2),
                arquivo_saida=str(SAIDA_SAFRA.relative_to(config.RAIZ)),
            )
        politica = escolha

    # Verificação no modo skip
    if politica == "skip" and SAIDA_SAFRA.exists() and SAIDA_PRODUCAO.exists() and ano_inicio is None and ano_fim is None:
        try:
            df_safra = pd.read_parquet(SAIDA_SAFRA)
            df_pam = pd.read_parquet(SAIDA_PRODUCAO)
            tamanho = SAIDA_SAFRA.stat().st_size + SAIDA_PRODUCAO.stat().st_size
            log.info(
                f"Arquivos finais de Safra (LSPA + PAM) já existem ({len(df_safra):,} e {len(df_pam):,} linhas). "
                f"Pulando coleta (skip)."
            )
            return ColetaResult(
                fonte="safra",
                status="SUCESSO",
                acao_executada="REUTILIZADO",
                duracao_segundos=round(time.perf_counter() - t_inicio, 2),
                linhas=len(df_safra),
                colunas=len(df_safra.columns),
                arquivo_saida=str(SAIDA_SAFRA.relative_to(config.RAIZ)),
                tamanho_bytes=tamanho,
                chunks_totais=2,
                chunks_baixados=0,
                chunks_reaproveitados=2,
                detalhes={
                    "produtos": int(df_safra["produto"].nunique()),
                    "linhas_safra": len(df_safra),
                    "linhas_producao_pam": len(df_pam),
                },
            )
        except Exception as e:
            log.warning(f"Arquivos existentes corrompidos ({e}). Reprocessando...")

    log.info(f"Iniciando coleta de Estimativas de Safra (LSPA/PAM) com política: {politica}")

    dim_uf = mod_ufs.carregar_ufs()
    ini_ano = ano_inicio or 2014
    fim_lspa = f"{ano_fim}12" if ano_fim else periodo_final("6588", f"{date.today():%Y%m}")
    fim_pam = ano_fim or int(periodo_final("1612", str(date.today().year - 1))[:4])

    erros: list[str] = []
    usar_backup = politica == "backup"

    try:
        # Coleta LSPA
        log.info(f"Etapa 1/2: Coleta LSPA (tabela 6588) {ini_ano} até {fim_lspa}...")
        safra = coleta_lspa(ini_ano, fim_lspa, dim_uf, nivel="UF", download_logger=dl_logger, logger=log)

        with BackupManager.gerenciar_com_seguranca(SAIDA_SAFRA, ativar_backup=usar_backup, logger=log):
            SAIDA_SAFRA.parent.mkdir(parents=True, exist_ok=True)
            safra.to_parquet(SAIDA_SAFRA, index=False)

        # Coleta PAM
        log.info(f"Etapa 2/2: Coleta PAM (tabelas 1612 e 1613) {ini_ano} até {fim_pam}...")
        pam = coleta_pam(ini_ano, fim_pam, dim_uf, download_logger=dl_logger, logger=log)

        with BackupManager.gerenciar_com_seguranca(SAIDA_PRODUCAO, ativar_backup=usar_backup, logger=log):
            SAIDA_PRODUCAO.parent.mkdir(parents=True, exist_ok=True)
            pam.to_parquet(SAIDA_PRODUCAO, index=False)

        tamanho_total = SAIDA_SAFRA.stat().st_size + SAIDA_PRODUCAO.stat().st_size
        log.info(
            f"Safras consolidadas: {len(safra):,} linhas LSPA e {len(pam):,} linhas PAM "
            f"({tamanho_total / 1e6:.2f} MB)."
        )

    except Exception as e:
        duracao = time.perf_counter() - t_inicio
        msg = f"Falha na coleta de safras LSPA/PAM: {e}"
        log.error(msg)
        erros.append(msg)
        return ColetaResult(
            fonte="safra",
            status="FALHA",
            acao_executada="FALHA_PROCESSAMENTO",
            duracao_segundos=round(duracao, 2),
            erros=erros,
        )

    duracao = time.perf_counter() - t_inicio
    acao = "BACKUP_CRIADO" if usar_backup else ("BAIXADO_NOVO" if politica == "force" else "ATUALIZADO")

    return ColetaResult(
        fonte="safra",
        status="AVISO" if erros else "SUCESSO",
        acao_executada=acao,
        duracao_segundos=round(duracao, 2),
        linhas=len(safra),
        colunas=len(safra.columns),
        arquivo_saida=str(SAIDA_SAFRA.relative_to(config.RAIZ)),
        tamanho_bytes=tamanho_total,
        chunks_totais=len(PRODUTOS_LSPA) + len(PRODUTOS_PAM_TEMPORARIAS) + len(PRODUTOS_PAM_PERMANENTES),
        erros=erros,
        detalhes={
            "produtos": int(safra["produto"].nunique()),
            "linhas_safra": len(safra),
            "linhas_producao_pam": len(pam),
        }
    )
