"""T-014, etapa 2 — monta o catálogo de estações a partir dos ZIPs.

Uso (a partir da raiz do repositório):

    python -m src.coleta.inmet.catalogo

Entrada:  `data/raw/inmet/*.zip`
Saída:    `data/interim/catalogo_estacoes.csv`

Os metadados saem do **cabeçalho de cada CSV dentro do ZIP** (as 8 primeiras
linhas), como o ticket recomenda, e não de raspagem da página de catálogo do
INMET: o cabeçalho é a mesma fonte do dado, vem sempre junto e não depende de a
página estar no ar ou manter o layout.

Uma estação aparece em vários anos, com metadados que às vezes mudam (a altitude
de Brasília vai de 1159,54 em 2014 para 1160,96 em 2026 — recalibração). Vale o
registro do **ano mais recente**, e as colunas `ano_primeiro`/`ano_ultimo`
guardam a vida útil da estação, que o T-021 precisa para explicar degrau na
média de uma UF quando uma estação entra ou sai.
"""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

import pandas as pd

from ... import config, ufs as mod_ufs
from . import LINHAS_METADADOS
from .colunas import para_float, parsear_metadados
from .download import caminho_zip, csvs_do_zip

SAIDA = config.DATA_INTERIM / "catalogo_estacoes.csv"

MINIMO_ESTACOES = 400  # critério de aceite do T-014


def _ler_metadados(arquivo: zipfile.ZipFile, nome: str) -> dict[str, str]:
    with arquivo.open(nome) as fluxo:
        # Ler só o começo: o cabeçalho está nos primeiros bytes e o arquivo
        # inteiro tem ~8.760 linhas de dado que aqui não interessam.
        bruto = fluxo.read(4096).decode("latin-1", errors="replace")
    return parsear_metadados(bruto.splitlines()[:LINHAS_METADADOS])


def coletar(anos: list[int]) -> pd.DataFrame:
    registros: list[dict] = []

    for ano in anos:
        caminho = caminho_zip(ano)
        if not caminho.exists():
            print(f"    - {ano}.zip ausente, pulando")
            continue
        with zipfile.ZipFile(caminho) as arquivo:
            nomes = csvs_do_zip(arquivo)
            for nome in nomes:
                meta = _ler_metadados(arquivo, nome)
                registros.append(
                    {
                        "codigo_estacao": meta.get("codigo_estacao", "").strip().upper(),
                        "nome": meta.get("nome_estacao", "").strip(),
                        "sigla_uf": meta.get("sigla_uf", "").strip().upper(),
                        "regiao_inmet": meta.get("regiao", "").strip().upper(),
                        "lat": para_float(meta.get("lat")),
                        "lon": para_float(meta.get("lon")),
                        "altitude": para_float(meta.get("altitude")),
                        "data_fundacao_bruta": meta.get("data_fundacao", "").strip(),
                        "ano": ano,
                        "arquivo": Path(nome).name,
                    }
                )
        print(f"    {ano}: {len(nomes)} estações lidas")

    if not registros:
        raise FileNotFoundError(
            "nenhum ZIP do INMET encontrado. Rode primeiro: python -m src.coleta.inmet.download"
        )
    return pd.DataFrame(registros)


def consolidar(bruto: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por estação, com os metadados do ano mais recente."""
    presenca = (
        bruto.groupby("codigo_estacao")["ano"]
        .agg(ano_primeiro="min", ano_ultimo="max", n_anos="nunique")
        .reset_index()
    )

    recente = bruto.sort_values("ano").drop_duplicates(subset="codigo_estacao", keep="last")
    catalogo = recente.drop(columns=["ano", "arquivo"]).merge(presenca, on="codigo_estacao", how="left")

    # As duas formas em que a data de fundação aparece: `2000-05-07` (até ~2020)
    # e `07/05/00` (nos anos recentes). Cada uma precisa do seu parser; misturar
    # deixaria metade como NaT.
    iso = pd.to_datetime(catalogo["data_fundacao_bruta"], format="%Y-%m-%d", errors="coerce")
    brasileira = pd.to_datetime(catalogo["data_fundacao_bruta"], format="%d/%m/%y", errors="coerce")
    catalogo["data_fundacao"] = iso.fillna(brasileira)
    catalogo = catalogo.drop(columns=["data_fundacao_bruta"])

    return catalogo.sort_values(["sigla_uf", "codigo_estacao"], ignore_index=True)


def _relatar(catalogo: pd.DataFrame) -> None:
    tabela_ufs = mod_ufs.carregar_ufs()
    siglas_validas = set(tabela_ufs["sigla_uf"])

    sem_uf = int(catalogo["sigla_uf"].eq("").sum() + catalogo["sigla_uf"].isna().sum())
    fora = sorted(set(catalogo["sigla_uf"]) - siglas_validas - {""})
    por_uf = catalogo.groupby("sigla_uf").size()
    ufs_sem_estacao = sorted(siglas_validas - set(por_uf.index))

    print(f"\n  {len(catalogo)} estações únicas")
    print(f"  sem sigla_uf: {sem_uf} | siglas fora de dim_uf: {fora or 'nenhuma'}")
    print(f"  UFs sem nenhuma estação: {ufs_sem_estacao or 'nenhuma'}")
    print(f"  estações por UF: mín {por_uf.min()} ({por_uf.idxmin()}), máx {por_uf.max()} ({por_uf.idxmax()})")
    faltam_coord = int(catalogo[["lat", "lon"]].isna().any(axis=1).sum())
    print(f"  sem lat/lon: {faltam_coord} | sem altitude: {int(catalogo['altitude'].isna().sum())}")
    print(f"  sem data de fundação legível: {int(catalogo['data_fundacao'].isna().sum())}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="T-014 — catálogo de estações do INMET")
    parser.add_argument("--anos", nargs="*", type=int, metavar="ANO")
    args = parser.parse_args(argv)

    from .download import anos_padrao

    anos = sorted(set(args.anos)) if args.anos else anos_padrao()
    config.garantir_pastas()

    print(f"T-014 — INMET: catálogo de estações ({anos[0]}-{anos[-1]})")
    bruto = coletar(anos)
    catalogo = consolidar(bruto)

    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    catalogo.to_csv(SAIDA, index=False, encoding="utf-8")

    _relatar(catalogo)
    print(f"\n  + {SAIDA.relative_to(config.RAIZ)}")
    if len(catalogo) < MINIMO_ESTACOES:
        print(f"  ATENÇÃO: menos de {MINIMO_ESTACOES} estações — critério de aceite do T-014 não atendido")
        return 1
    print("  próximo passo: python -m src.coleta.inmet.agrega_dia")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
