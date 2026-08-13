"""T-015, etapa 2 — agrega o Monitor de Secas para `seca_uf_mes.parquet`.

Uso (a partir da raiz do repositório):

    python -m src.coleta.monitor_secas.agrega_uf_mes

Entrada:  `data/raw/ana/dados_tabulares_uf_*.json` (etapa 1)
Saída:    `data/interim/seca_uf_mes.parquet`
          `docs/cobertura_monitor_secas.md` (quando cada UF entrou no monitoramento)

Duas decisões de modelagem que valem ser lidas antes de usar a tabela:

* **A fonte já vem em percentual da área da UF, cumulativo.** A API entrega
  pontos-base (10000 = 100,00%) e a categoria `S2` significa "área em seca grave
  *ou pior*". Logo a ponderação por área de município que o T-015 pedia já foi
  feita pela ANA — não há municípios para agregar, nem `geopandas` envolvido.
* **Mês sem monitoramento é `NaN`, nunca zero.** É a armadilha central do
  ticket: preencher com zero ensinaria ao modelo que "antes de 2020 não havia
  seca no Sul", quando na verdade ninguém estava olhando.
"""

from __future__ import annotations

import argparse
import json

import pandas as pd

from ... import config, ufs as mod_ufs
from . import CATEGORIAS, PESOS, PONTOS_BASE
from .download import caminho_bruto

SAIDA = config.DATA_INTERIM / "seca_uf_mes.parquet"
DOC_COBERTURA = config.DOCS / "cobertura_monitor_secas.md"
TABELA_COBERTURA = config.OUT_TABELAS / "cobertura_monitor_secas.csv"
TABELA_QUALIDADE = config.OUT_TABELAS / "monitor_secas_revisoes_divergentes.csv"

# Um mês conta para `meses_consecutivos_S2plus` quando há qualquer área da UF em
# seca grave ou pior. Constante explícita para o T-023 poder experimentar outro
# limiar (ex.: 10% da área) sem caçar número mágico no meio do código.
LIMIAR_S2PLUS_PCT = 0.0

# Ordem final das colunas: primeiro exatamente o schema pedido pelo T-015,
# depois as colunas extras que saem de graça do mesmo cálculo.
COLUNAS_TICKET = [
    "sigla_uf",
    "ano_mes",
    "pct_area_S0plus",
    "pct_area_S2plus",
    "pct_area_S3plus",
    "severidade_media",
    "meses_consecutivos_S2plus",
]
COLUNAS_EXTRA = [
    "ano",
    "mes",
    "pct_area_S1plus",
    "pct_area_S4plus",
    "severidade_media_area_seca",
    "monitorado",
    "inconsistente",
]


def _carregar_bruto(siglas: list[str]) -> pd.DataFrame:
    """Lê os JSONs brutos e devolve uma linha por UF × mês × categoria.

    A API entrega **todas as revisões** de um mês empilhadas na mesma lista
    `areas`, sem sinalizar qual é a vigente: 66 dos 2.422 meses vêm com a
    categoria repetida 2 a 4 vezes. As revisões antigas incluem erros que já
    foram corrigidos — a Bahia em 2015-04 aparece com a escala multiplicada por
    100 (`984700` em vez de `9847`), e em 2016-06 tem um `123456` de placeholder
    em S4. **Só o `id` maior é o dado vigente**; em ambos os casos a revisão
    seguinte já traz o valor certo.

    Pegar o máximo, o mínimo ou a média entre revisões produz número errado sem
    reclamar. Por isso o desempate é explícito e as divergências são gravadas em
    `outputs/tabelas/` para auditoria.
    """
    registros: list[dict] = []
    ausentes: list[str] = []

    for sigla in siglas:
        caminho = caminho_bruto(sigla)
        if not caminho.exists():
            ausentes.append(sigla)
            continue
        conteudo = json.loads(caminho.read_text(encoding="utf-8"))
        for item in conteudo["data"]["list"]:
            mapa = item["mapa"]
            for area in item["areas"]:
                registros.append(
                    {
                        "sigla_uf": sigla,
                        "ano": int(mapa["ano"]),
                        "mes": int(mapa["mes"]),
                        # AL e CE em 2020-03 trazem as categorias em minúsculas
                        # (`s0`..`s4`) junto das maiúsculas. Sem normalizar a
                        # caixa, viram categorias distintas e o mês fica com 10.
                        "categoria": str(area["categoria"]).upper(),
                        "pontos": float(area["area"]),
                        "id_registro": int(area["id"]),
                    }
                )

    if ausentes:
        raise FileNotFoundError(
            f"faltam os JSONs brutos de {ausentes}. "
            "Rode primeiro: python -m src.coleta.monitor_secas.download"
        )

    longo = pd.DataFrame(registros)
    chave = ["sigla_uf", "ano", "mes", "categoria"]

    grupos = longo.groupby(chave)["pontos"]
    longo["n_revisoes"] = grupos.transform("size")
    longo["n_valores_distintos"] = grupos.transform("nunique")

    _registrar_divergencias(longo, chave)

    longo = longo.sort_values("id_registro").drop_duplicates(subset=chave, keep="last")
    return longo.drop(columns=["n_valores_distintos"])


def _registrar_divergencias(longo: pd.DataFrame, chave: list[str]) -> None:
    """Grava as revisões que discordam entre si, para auditoria do T-025."""
    divergentes = longo[longo["n_valores_distintos"] > 1].copy()
    if divergentes.empty:
        print("  revisões: nenhuma divergência entre revisões do mesmo mês")
        return

    vigentes = divergentes.sort_values("id_registro").drop_duplicates(subset=chave, keep="last")
    vigentes = vigentes[chave + ["pontos"]].rename(columns={"pontos": "pontos_vigente"})
    relatorio = (
        divergentes.merge(vigentes, on=chave, how="left")
        .assign(descartado=lambda d: d["pontos"] != d["pontos_vigente"])
        .sort_values(chave + ["id_registro"])
    )

    TABELA_QUALIDADE.parent.mkdir(parents=True, exist_ok=True)
    relatorio.to_csv(TABELA_QUALIDADE, index=False, encoding="utf-8")

    n_chaves = len(vigentes)
    n_descartados = int(relatorio["descartado"].sum())
    print(
        f"  revisões: {n_chaves} combinações UF×mês×categoria com revisões divergentes; "
        f"{n_descartados} valores antigos descartados (maior id vence)"
    )
    print(f"            auditoria em {TABELA_QUALIDADE.relative_to(config.RAIZ)}")


def _para_largo(longo: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por UF × mês, com uma coluna de pontos-base por categoria."""
    chave = ["sigla_uf", "ano", "mes", "categoria"]
    duplicadas = int(longo.duplicated(subset=chave).sum())
    if duplicadas:
        raise ValueError(f"{duplicadas} chaves duplicadas sobraram depois do desempate por id")

    largo = (
        longo.pivot(index=["sigla_uf", "ano", "mes"], columns="categoria", values="pontos")
        .reset_index()
        .rename_axis(columns=None)
    )
    faltando = [c for c in CATEGORIAS if c not in largo.columns]
    if faltando:
        raise ValueError(f"categorias ausentes nos dados brutos: {faltando}")
    return largo


def _grade_completa(largo: pd.DataFrame, siglas: list[str]) -> pd.DataFrame:
    """Produto cartesiano UF × mês, cobrindo até o fim da janela-alvo.

    A grade começa no mês mais antigo disponível na fonte (2014-07, quando o
    Monitor nasceu no Nordeste) e não em `PERIODO_INICIO`, para que o contador de
    meses consecutivos de seca já chegue "aquecido" em 2015-01. Sem isso, o
    Ceará — que estava em seca contínua desde 2014 — apareceria zerado no
    primeiro mês da janela.
    """
    primeiro_fonte = pd.Period(f"{largo['ano'].min()}-{largo['mes'].min():02d}", freq="M")
    inicio = min(primeiro_fonte, pd.Period(config.PERIODO_INICIO, freq="M"))
    fim = pd.Period(config.PERIODO_FIM, freq="M")

    meses = pd.period_range(inicio, fim, freq="M")
    grade = pd.MultiIndex.from_product([siglas, meses], names=["sigla_uf", "periodo"]).to_frame(index=False)
    grade["ano"] = grade["periodo"].dt.year
    grade["mes"] = grade["periodo"].dt.month
    return grade


def agregar() -> pd.DataFrame:
    tabela_ufs = mod_ufs.carregar_ufs()
    siglas = sorted(tabela_ufs["sigla_uf"])

    longo = _carregar_bruto(siglas)
    largo = _para_largo(longo)
    print(f"  lidos {len(largo)} registros UF×mês de {largo['sigla_uf'].nunique()} UFs")

    df = _grade_completa(largo, siglas).merge(largo, on=["sigla_uf", "ano", "mes"], how="left")

    # `monitorado` distingue "não havia seca" de "ninguém estava medindo".
    df["monitorado"] = df[list(CATEGORIAS)].notna().any(axis=1)

    # Cumulativo, em pontos-base -> percentual da área da UF.
    for categoria in CATEGORIAS:
        df[f"pct_area_{categoria}plus"] = df[categoria] / PONTOS_BASE

    # Sob categorias cumulativas, S4 ⊆ S3 ⊆ ... ⊆ S0, então a série tem de ser
    # monotonicamente não crescente. O Maranhão em 2014-11 vem com S3=0 e S4=13,
    # o que é impossível, e não há revisão posterior que corrija. Em vez de
    # inventar um valor para S3, o mês fica sinalizado — quem for usar decide.
    inconsistente = pd.Series(False, index=df.index)
    for mais_amplo, mais_grave in zip(CATEGORIAS, CATEGORIAS[1:]):
        inconsistente |= df[mais_grave] > df[mais_amplo] + 1e-9
    df["inconsistente"] = inconsistente
    if inconsistente.any():
        quais = df.loc[inconsistente, ["sigla_uf", "ano", "mes"]]
        rotulos = [f"{r.sigla_uf} {r.ano}-{r.mes:02d}" for r in quais.itertuples(index=False)]
        print(f"  atenção: {len(rotulos)} mês(es) com categorias cumulativas inconsistentes: {', '.join(rotulos)}")

    # Desfaz o acúmulo para obter as faixas exclusivas, que é o que a média
    # ponderada exige. O clip(lower=0) é defensivo: sob dados consistentes as
    # faixas nunca são negativas, e o validar reporta se alguma for.
    faixas = {}
    for i, categoria in enumerate(CATEGORIAS):
        proxima = CATEGORIAS[i + 1] if i + 1 < len(CATEGORIAS) else None
        exclusiva = df[categoria] - (df[proxima] if proxima else 0.0)
        faixas[categoria] = exclusiva.clip(lower=0.0)

    numerador = sum(PESOS[categoria] * faixas[categoria] for categoria in CATEGORIAS)

    # Índice de severidade da UF inteira, de 0 (sem seca) a 5 (todo o território
    # em seca excepcional). Área sem seca entra com peso 0, o que mantém o índice
    # comparável entre UFs e entre meses.
    df["severidade_media"] = numerador / (PONTOS_BASE * 100.0)

    # Severidade média *dentro* da área seca: responde "quando dá seca aqui, ela
    # é forte?", mas é indefinida no mês sem seca alguma.
    area_seca = df["S0"]
    df["severidade_media_area_seca"] = (numerador / area_seca).where(area_seca > 0)

    df["meses_consecutivos_S2plus"] = _meses_consecutivos(df)

    df["ano_mes"] = df["periodo"].astype(str)
    df = df[df["ano_mes"] >= config.PERIODO_INICIO].copy()

    return df[COLUNAS_TICKET + COLUNAS_EXTRA].sort_values(["sigla_uf", "ano_mes"], ignore_index=True)


def _meses_consecutivos(df: pd.DataFrame) -> pd.Series:
    """Meses consecutivos com seca grave ou pior, por UF.

    Seca é acumulativa: 6 meses seguidos de S2 machucam a safra muito mais que 1
    mês isolado, e essa memória é justamente o que uma coluna mensal solta perde.

    Um mês sem monitoramento é `NaN` **e zera a contagem**: não é possível
    afirmar continuidade através de um buraco na série. Por isso a UF que entrou
    no monitoramento já em seca começa a contar do 1, não da duração real —
    subestimativa honesta, preferível a um número inventado.
    """
    resultado = pd.Series(pd.NA, index=df.index, dtype="Float64")

    for _, indices in df.groupby("sigla_uf", sort=False).groups.items():
        contador = 0
        for indice in indices:
            pct = df.at[indice, "pct_area_S2plus"]
            if pd.isna(pct):
                contador = 0
                continue  # deixa NaN
            if pct > LIMIAR_S2PLUS_PCT:
                contador += 1
            else:
                contador = 0
            resultado.at[indice] = contador

    return resultado


def escrever_cobertura(df: pd.DataFrame) -> pd.DataFrame:
    """Monta e grava a tabela de cobertura por UF (tarefa explícita do T-015)."""
    monitorado = df[df["monitorado"]]
    cobertura = (
        monitorado.groupby("sigla_uf")
        .agg(
            primeiro_mes=("ano_mes", "min"),
            ultimo_mes=("ano_mes", "max"),
            meses_com_dado=("ano_mes", "count"),
        )
        .reset_index()
    )

    total_meses = df["ano_mes"].nunique()
    cobertura["meses_na_janela"] = total_meses
    cobertura["pct_cobertura"] = (100 * cobertura["meses_com_dado"] / total_meses).round(1)
    # Buraco = mês sem dado DENTRO do intervalo já monitorado pela UF, que é
    # falha da série e não ausência de monitoramento.
    esperados = (
        pd.PeriodIndex(cobertura["ultimo_mes"], freq="M").astype("int64")
        - pd.PeriodIndex(cobertura["primeiro_mes"], freq="M").astype("int64")
        + 1
    )
    cobertura["buracos_internos"] = esperados - cobertura["meses_com_dado"]
    cobertura = cobertura.sort_values(["primeiro_mes", "sigla_uf"], ignore_index=True)

    TABELA_COBERTURA.parent.mkdir(parents=True, exist_ok=True)
    cobertura.to_csv(TABELA_COBERTURA, index=False, encoding="utf-8")

    linhas = [
        "# Cobertura do Monitor de Secas por UF (T-015)",
        "",
        "Gerado por `python -m src.coleta.monitor_secas.agrega_uf_mes`. Não editar à mão.",
        "",
        f"Janela-alvo do projeto: **{config.PERIODO_INICIO} a {config.PERIODO_FIM}** "
        f"({total_meses} meses).",
        "",
        "O Monitor de Secas nasceu no Nordeste em 2014 e foi expandindo para o resto do",
        "país ao longo dos anos. Os meses anteriores à entrada de cada UF estão como",
        "`NaN` na tabela `seca_uf_mes.parquet` — **não como zero**. Ausência de",
        "monitoramento não é ausência de seca, e tratar como zero criaria um viés",
        "regional grave nos primeiros anos da série.",
        "",
        "| UF | Primeiro mês | Último mês | Meses com dado | % da janela | Buracos internos |",
        "|---|---|---|---|---|---|",
    ]
    for linha in cobertura.itertuples(index=False):
        linhas.append(
            f"| {linha.sigla_uf} | {linha.primeiro_mes} | {linha.ultimo_mes} | "
            f"{linha.meses_com_dado} | {linha.pct_cobertura:.1f}% | {linha.buracos_internos} |"
        )
    linhas += [
        "",
        "**Buracos internos** são meses sem dado *dentro* do intervalo em que a UF já",
        "era monitorada — falha da série, não expansão pendente. Também ficam `NaN`.",
        "",
    ]
    DOC_COBERTURA.parent.mkdir(parents=True, exist_ok=True)
    DOC_COBERTURA.write_text("\n".join(linhas), encoding="utf-8")

    return cobertura


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="T-015 — agrega o Monitor de Secas para UF × mês")
    parser.parse_args(argv)

    config.garantir_pastas()
    print("T-015 — Monitor de Secas: agregação para UF × mês")

    df = agregar()

    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(SAIDA, index=False)

    cobertura = escrever_cobertura(df)

    print(f"\n  {len(df)} linhas ({df['sigla_uf'].nunique()} UFs × {df['ano_mes'].nunique()} meses)")
    print(f"  monitoradas: {int(df['monitorado'].sum())} linhas | sem monitoramento (NaN): {int((~df['monitorado']).sum())}")
    print(f"  + {SAIDA.relative_to(config.RAIZ)}")
    print(f"  + {DOC_COBERTURA.relative_to(config.RAIZ)}")
    print(f"  + {TABELA_COBERTURA.relative_to(config.RAIZ)}")
    print(f"\n  primeiras UFs a entrar no monitoramento:\n{cobertura.head(12).to_string(index=False)}")
    print("\n  próximo passo: python -m src.coleta.monitor_secas.validar")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
