"""T-015, etapa 3 — verifica os critérios de aceite do ticket.

Uso (a partir da raiz do repositório):

    python -m src.coleta.monitor_secas.validar

Sai com código 0 se todos os critérios passam, 1 se algum falha, para poder ser
usado em CI depois. Cada critério imprime o número que o sustenta, não só
"passou" — é o número que vai para o relatório do T-025.
"""

from __future__ import annotations

import argparse

import pandas as pd

from ... import config
from . import CATEGORIAS
from .agrega_uf_mes import SAIDA

UFS_NORDESTE = ["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"]
UFS_CENTRO_SUL = ["RS", "SC", "PR", "SP", "MS", "MG", "GO"]

# A grande seca do Nordeste e a crise hídrica do Centro-Sul, que o ticket manda
# conferir na série.
SECA_NORDESTE = ("2015-01", "2017-12")
ANO_SECA_CENTRO_SUL = 2021

COLUNAS_PCT = [f"pct_area_{c}plus" for c in CATEGORIAS]


class Relatorio:
    def __init__(self) -> None:
        self.falhas = 0

    def checar(self, nome: str, condicao: bool, detalhe: str = "") -> None:
        marca = "PASSA" if condicao else "FALHA"
        if not condicao:
            self.falhas += 1
        sufixo = f" — {detalhe}" if detalhe else ""
        print(f"  [{marca}] {nome}{sufixo}")


def validar(df: pd.DataFrame) -> int:
    rel = Relatorio()

    print("\nCritério 1 — percentuais entre 0 e 100 e categorias coerentes")
    for coluna in COLUNAS_PCT:
        valores = df[coluna].dropna()
        rel.checar(
            f"{coluna} dentro de [0, 100]",
            bool(((valores >= 0) & (valores <= 100)).all()),
            f"min={valores.min():.2f} max={valores.max():.2f}",
        )

    # As categorias são cumulativas, então precisam ser monotonicamente não
    # crescentes. Se isso quebrar, alguma faixa exclusiva é negativa e a
    # severidade média está errada.
    for mais_amplo, mais_grave in zip(COLUNAS_PCT, COLUNAS_PCT[1:]):
        comparaveis = df[[mais_amplo, mais_grave]].dropna()
        violacoes = int((comparaveis[mais_grave] > comparaveis[mais_amplo] + 1e-9).sum())
        rel.checar(f"{mais_grave} <= {mais_amplo}", violacoes == 0, f"{violacoes} violações")

    sev = df["severidade_media"].dropna()
    rel.checar(
        "severidade_media dentro de [0, 5]",
        bool(((sev >= 0) & (sev <= 5)).all()),
        f"min={sev.min():.3f} max={sev.max():.3f}",
    )

    print("\nCritério 2 — cobertura documentada e pré-monitoramento como NaN")
    rel.checar("as 27 UFs estão presentes", df["sigla_uf"].nunique() == 27, f"{df['sigla_uf'].nunique()} UFs")
    esperado = 27 * df["ano_mes"].nunique()
    rel.checar("grade UF × mês sem buraco de chave", len(df) == esperado, f"{len(df)} de {esperado} linhas")

    nao_monitorado = df[~df["monitorado"]]
    todas_nan = bool(nao_monitorado[COLUNAS_PCT + ["severidade_media"]].isna().all().all())
    rel.checar(
        "linha sem monitoramento tem NaN (não zero)",
        todas_nan,
        f"{len(nao_monitorado)} linhas sem monitoramento",
    )
    zeros_indevidos = int((nao_monitorado[COLUNAS_PCT] == 0).sum().sum())
    rel.checar("nenhum zero indevido no pré-monitoramento", zeros_indevidos == 0, f"{zeros_indevidos} zeros")

    from .agrega_uf_mes import DOC_COBERTURA

    rel.checar(
        "documento de cobertura por UF existe",
        DOC_COBERTURA.exists(),
        str(DOC_COBERTURA.relative_to(config.RAIZ)),
    )

    print("\nCritério 3 — sanidade histórica das secas conhecidas")
    ne = df[df["sigla_uf"].isin(UFS_NORDESTE)]
    na_seca = ne[ne["ano_mes"].between(*SECA_NORDESTE)]["pct_area_S2plus"].mean()
    fora = ne[~ne["ano_mes"].between(*SECA_NORDESTE)]["pct_area_S2plus"].mean()
    rel.checar(
        "Nordeste 2015-2017 aparece como seca severa",
        na_seca > 40 and na_seca > 2 * fora,
        f"S2+ médio {na_seca:.1f}% em 2015-2017 vs {fora:.1f}% no resto da série",
    )

    cs = df[df["sigla_uf"].isin(UFS_CENTRO_SUL) & df["monitorado"]]
    por_ano = cs.groupby("ano")["pct_area_S2plus"].mean().sort_values(ascending=False)
    posicao = list(por_ano.index).index(ANO_SECA_CENTRO_SUL) + 1
    rel.checar(
        f"Centro-Sul {ANO_SECA_CENTRO_SUL} destaca-se na série",
        posicao <= 2,
        f"{ANO_SECA_CENTRO_SUL} é o {posicao}º ano mais seco "
        f"({por_ano[ANO_SECA_CENTRO_SUL]:.1f}% de S2+); topo: "
        + ", ".join(f"{ano}={v:.1f}%" for ano, v in por_ano.head(3).items()),
    )

    print("\nCritério 4 — memória da seca (meses consecutivos)")
    mc = df["meses_consecutivos_S2plus"].dropna()
    rel.checar("meses_consecutivos_S2plus não negativo", bool((mc >= 0).all()), f"máx={mc.max():.0f} meses")
    pior = df.loc[df["meses_consecutivos_S2plus"].idxmax()]
    print(
        f"         maior sequência de seca grave+: {pior['sigla_uf']} "
        f"terminando em {pior['ano_mes']} com {pior['meses_consecutivos_S2plus']:.0f} meses"
    )

    return rel.falhas


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="T-015 — critérios de aceite do Monitor de Secas")
    parser.parse_args(argv)

    if not SAIDA.exists():
        print(f"ERRO: {SAIDA} não existe. Rode: python -m src.coleta.monitor_secas.agrega_uf_mes")
        return 1

    df = pd.read_parquet(SAIDA)
    print(f"T-015 — validando {SAIDA.relative_to(config.RAIZ)} ({len(df)} linhas)")

    falhas = validar(df)

    print()
    if falhas:
        print(f"RESULTADO: {falhas} critério(s) falharam.")
        return 1
    print("RESULTADO: todos os critérios de aceite do T-015 passaram.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
