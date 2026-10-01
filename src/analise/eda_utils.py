"""Módulo utilitário compartilhado para Análise Exploratória de Dados (EDA).

Projeto: O que move o preço da comida no Brasil?
Disciplina: SSC0957 - Prática em Ciência de Dados II (USP)
Base: data/processed/fato_alimentos_combustiveis_uf_mes.parquet
"""

from __future__ import annotations

from pathlib import Path
import warnings
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

ROOT_DIR = Path(__file__).resolve().parents[2]
PATH_FATO = ROOT_DIR / "data" / "processed" / "fato_alimentos_combustiveis_uf_mes.parquet"
PASTA_FIGURAS = ROOT_DIR / "outputs" / "figuras" / "eda"


def carregar_fato_alimentos(caminho: Path | str | None = None) -> pd.DataFrame:
    """Carrega a tabela fato analítica e padroniza chaves de ordenação."""
    caminho = Path(caminho) if caminho else PATH_FATO
    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")

    df = pd.read_parquet(caminho)

    # Garante ordenação temporal estrita por estado
    df = df.sort_values(["sigla_uf", "ano_mes"]).reset_index(drop=True)
    return df


def adicionar_lags_painel(
    df: pd.DataFrame,
    colunas: list[str],
    lags: list[int] = [1, 2, 3, 6],
    sufixo_padrao: str = "lag",
) -> pd.DataFrame:
    """Gera variáveis defasadas (lags) agrupadas por UF.

    Garante que o shift ocorra estritamente dentro da mesma UF e não contamine
    estados adjacentes.
    """
    df_out = df.copy()

    # Valida que as colunas existem
    colunas_validas = [c for c in colunas if c in df_out.columns]
    colunas_faltantes = set(colunas) - set(colunas_validas)
    if colunas_faltantes:
        warnings.warn(f"Colunas não encontradas ignoradas: {colunas_faltantes}")

    # Agrupa por UF para shift seguro
    for col in colunas_validas:
        for lag in lags:
            nome_lag = f"{col}_{sufixo_padrao}{lag}"
            df_out[nome_lag] = df_out.groupby("sigla_uf")[col].shift(lag)

    return df_out


def obter_janela_analise(
    df: pd.DataFrame, modo: str = "ampla"
) -> pd.DataFrame:
    """Filtra o DataFrame de acordo com a estratégia de janela do projeto.

    - 'ampla': Retorna as 2.088 linhas históricas (2015-2026), preservando NaNs
    ontológicos.
    - 'balanceada': Retorna o subconjunto onde ANP combustíveis líquidos e
    Monitor de Secas estavam simultaneamente observados.
    """
    if modo == "ampla":
        return df.copy()
    elif modo == "balanceada":
        cond_comb = (
            df["comb_observado_liquidos"] == True
            if "comb_observado_liquidos" in df.columns
            else True
        )
        cond_seca = (
            df["seca_monitorado"] == True
            if "seca_monitorado" in df.columns
            else True
        )
        df_sub = df[cond_comb & cond_seca].copy()
        return df_sub.reset_index(drop=True)
    else:
        raise ValueError(
            f"Modo desconhecido: {modo}. Escolha 'ampla' ou 'balanceada'."
        )


def configurar_estilo_visual() -> None:
    """Configura o estilo padrão dos gráficos (Seaborn + Matplotlib) para relatórios."""
    sns.set_theme(style="whitegrid", palette="tab10")
    plt.rcParams["font.sans-serif"] = [
        "DejaVu Sans",
        "Arial",
        "Helvetica",
        "sans-serif",
    ]
    plt.rcParams["axes.titlesize"] = 13
    plt.rcParams["axes.titleweight"] = "bold"
    plt.rcParams["axes.labelsize"] = 11
    plt.rcParams["axes.labelweight"] = "bold"
    plt.rcParams["xtick.labelsize"] = 10
    plt.rcParams["ytick.labelsize"] = 10
    plt.rcParams["figure.titlesize"] = 14
    plt.rcParams["figure.titleweight"] = "bold"
    plt.rcParams["figure.dpi"] = 150


def salvar_figura(
    fig: plt.Figure,
    nome_arquivo: str,
    pasta: Path | str | None = None,
    dpi: int = 150,
) -> Path:
    """Salva a figura em alta resolução no diretório padrão de figuras."""
    pasta_destino = Path(pasta) if pasta else PASTA_FIGURAS
    pasta_destino.mkdir(parents=True, exist_ok=True)

    if not nome_arquivo.endswith(".png"):
        nome_arquivo += ".png"

    caminho_final = pasta_destino / nome_arquivo
    fig.savefig(caminho_final, dpi=dpi, bbox_inches="tight")
    print(f"✅ Figura salva com sucesso em: {caminho_final}")
    return caminho_final
