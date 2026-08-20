"""T-014, etapa 4 — agrega estação × dia para estação × mês, num arquivo só.

Uso (a partir da raiz do repositório):

    python -m src.coleta.inmet.agrega_mes

Entrada:  `data/interim/clima_estacao_dia.parquet/` (um arquivo por ano)
Saída:    `data/interim/clima_estacao_mes.parquet`  (arquivo único, todos os anos)

## Por que os índices de extremo são calculados aqui

O T-021 é categórico: **os índices de extremo têm de sair do nível diário, antes
da agregação mensal** — depois eles são impossíveis de recuperar. `dias_sem_chuva`
não se deduz de `chuva_mm_mes`: 90 mm num mês podem ser 3 mm em 30 dias ou 90 mm
num dia só, e a diferença é tudo para uma safra.

Por isso esta etapa não é só um `resample('M')`. Ela varre o diário e guarda, como
colunas do mensal, tudo o que só existe no dia: contagem de dias secos, de dias de
chuva forte, de dias de calor extremo, e a **maior sequência de dias secos
seguidos** — que é o indicador de veranico, o que de fato mata lavoura.

Com isso a tabela mensal passa a conter tudo o que a diária dizia sobre extremos,
e a diária vira intermediária descartável (e sempre reproduzível a partir dos
ZIPs em `data/raw/inmet/`).

## Granularidade

A saída continua sendo por **estação**, não por UF. Reduzir estação → UF envolve
decisões de modelagem que são do T-021 (mediana entre estações, contagem de
estações contribuintes, tratamento de UF grande com clima heterogêneo), e não
cabem num coletor.
"""

from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from ... import config
from .agrega_dia import SAIDA as ENTRADA_DIARIA

SAIDA = config.DATA_INTERIM / "clima_estacao_mes.parquet"

# Limiares dos índices de extremo, explícitos para o T-023 poder experimentar.
LIMIAR_DIA_SECO_MM = 1.0       # dia com menos que isto conta como "sem chuva"
LIMIAR_CHUVA_FORTE_MM = 50.0   # dia acima disto conta como chuva forte
PERCENTIL_CALOR = 0.90         # p90 da máxima, por estação e mês-do-ano

# Mês com menos que esta fração de dias válidos vira NaN em vez de virar média de
# meia dúzia de dias. Mesmo espírito do corte de 18 horas do diário.
MINIMO_FRACAO_DIAS_VALIDOS = 0.70


def _maior_sequencia_seca(df: pd.DataFrame, chave: pd.Series) -> pd.Series:
    """Maior nº de dias secos consecutivos dentro de cada estação × mês.

    Vetorizado: marca o início de cada sequência (dia seco cujo anterior não era
    seco, ou primeiro dia de uma chave nova), numera as sequências com um
    `cumsum`, e conta o comprimento de cada uma. Dia sem medição **quebra** a
    sequência — não se pode afirmar que não choveu num dia em que ninguém olhou.
    """
    seco = (df["chuva_mm"] < LIMIAR_DIA_SECO_MM).fillna(False)
    nova_chave = chave != chave.shift()
    inicio = seco & (~seco.shift(fill_value=False) | nova_chave)
    id_sequencia = inicio.cumsum()
    comprimento = seco.groupby(id_sequencia).cumsum()
    return comprimento.where(seco, 0).groupby(chave, sort=False).max()


def agregar(diario: pd.DataFrame) -> pd.DataFrame:
    diario = diario.sort_values(["codigo_estacao", "data"], ignore_index=True)
    diario["ano_mes"] = diario["data"].dt.strftime("%Y-%m")
    chave = diario["codigo_estacao"] + "|" + diario["ano_mes"]

    # p90 da temperatura máxima por estação e mês-do-ano, sobre a série inteira.
    # É a referência de "calor extremo para este lugar nesta época do ano" — um dia
    # de 32 °C é banal em Teresina em novembro e excepcional em Curitiba em julho.
    limiar_calor = diario.groupby(["codigo_estacao", "mes"])["temp_max"].transform(
        lambda s: s.quantile(PERCENTIL_CALOR)
    )
    diario["_calor_extremo"] = diario["temp_max"] > limiar_calor
    diario["_dia_seco"] = diario["chuva_mm"] < LIMIAR_DIA_SECO_MM
    diario["_chuva_forte"] = diario["chuva_mm"] > LIMIAR_CHUVA_FORTE_MM
    diario["_amplitude"] = diario["temp_max"] - diario["temp_min"]

    grupos = diario.groupby(chave, sort=False)

    mensal = pd.DataFrame(
        {
            "codigo_estacao": grupos["codigo_estacao"].first(),
            "sigla_uf": grupos["sigla_uf"].first(),
            "ano_mes": grupos["ano_mes"].first(),
            "ano": grupos["ano"].first(),
            "mes": grupos["mes"].first(),
            # --- acumulados e médias ---
            "chuva_mm_mes": grupos["chuva_mm"].sum(min_count=1),
            "temp_media": grupos["temp_media"].mean(),
            "temp_max_media": grupos["temp_max"].mean(),
            "temp_min_media": grupos["temp_min"].mean(),
            "temp_max_abs": grupos["temp_max"].max(),
            "temp_min_abs": grupos["temp_min"].min(),
            "amplitude_termica_media": grupos["_amplitude"].mean(),
            "umidade_media": grupos["umidade_media"].mean(),
            "umidade_min_abs": grupos["umidade_min"].min(),
            "radiacao_total_mes": grupos["radiacao_total"].sum(min_count=1),
            "pressao_media_mb": grupos["pressao_media_mb"].mean(),
            "temp_orvalho_media_c": grupos["temp_orvalho_media_c"].mean(),
            "vento_velocidade_media_ms": grupos["vento_velocidade_media_ms"].mean(),
            "vento_rajada_max_ms": grupos["vento_rajada_max_ms"].max(),
            # --- índices de extremo: só existem porque vieram do diário ---
            "dias_sem_chuva": grupos["_dia_seco"].sum(),
            "dias_chuva_forte": grupos["_chuva_forte"].sum(),
            "dias_calor_extremo": grupos["_calor_extremo"].sum(),
            # --- qualidade ---
            "dias_com_registro": grupos.size(),
            "dias_validos_chuva": grupos["chuva_mm"].count(),
            "dias_validos_temp": grupos["temp_media"].count(),
        }
    )

    mensal["max_dias_secos_seguidos"] = _maior_sequencia_seca(diario, chave)

    # Dias do calendário no mês, para medir cobertura de verdade: uma estação que
    # só reportou 5 dias tem 5 "dias com registro", não um mês.
    periodo = pd.PeriodIndex(mensal["ano_mes"], freq="M")
    mensal["dias_no_mes"] = periodo.days_in_month
    mensal["pct_dias_validos"] = (100 * mensal["dias_validos_temp"] / mensal["dias_no_mes"]).round(1)

    # Mês com cobertura insuficiente não vira média de meia dúzia de dias.
    ruim_temp = mensal["dias_validos_temp"] < MINIMO_FRACAO_DIAS_VALIDOS * mensal["dias_no_mes"]
    mensal.loc[ruim_temp, [
        "temp_media", "temp_max_media", "temp_min_media", "temp_max_abs", "temp_min_abs",
        "amplitude_termica_media", "umidade_media", "umidade_min_abs",
        "pressao_media_mb", "temp_orvalho_media_c",
        "vento_velocidade_media_ms", "vento_rajada_max_ms",
        "dias_calor_extremo",
    ]] = np.nan

    ruim_chuva = mensal["dias_validos_chuva"] < MINIMO_FRACAO_DIAS_VALIDOS * mensal["dias_no_mes"]
    mensal.loc[ruim_chuva, [
        "chuva_mm_mes", "dias_sem_chuva", "dias_chuva_forte", "max_dias_secos_seguidos",
    ]] = np.nan

    return mensal.sort_values(["codigo_estacao", "ano_mes"], ignore_index=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="T-014 — agrega o INMET de dia para mês, num arquivo só")
    parser.parse_args(argv)

    if not ENTRADA_DIARIA.exists() or not any(ENTRADA_DIARIA.glob("*.parquet")):
        print(f"ERRO: {ENTRADA_DIARIA} vazio. Rode antes: python -m src.coleta.inmet.agrega_dia")
        return 1

    config.garantir_pastas()
    print("T-014 — INMET: agregação dia -> mês")

    diario = pd.read_parquet(ENTRADA_DIARIA)
    print(f"  lidas {len(diario):,} linhas estação×dia de {len(list(ENTRADA_DIARIA.glob('*.parquet')))} arquivos anuais")

    mensal = agregar(diario)
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    mensal.to_parquet(SAIDA, index=False)

    tamanho = SAIDA.stat().st_size / 1e6
    print(f"\n  {len(mensal):,} linhas estação×mês × {len(mensal.columns)} colunas")
    print(f"  {mensal['codigo_estacao'].nunique()} estações | {mensal['ano_mes'].nunique()} meses "
          f"({mensal['ano_mes'].min()} a {mensal['ano_mes'].max()})")
    print(f"  + {SAIDA.relative_to(config.RAIZ)} ({tamanho:.1f} MB, arquivo único)")

    print("\n  preenchimento:")
    for coluna in ("chuva_mm_mes", "temp_media", "dias_sem_chuva", "max_dias_secos_seguidos", "dias_calor_extremo"):
        print(f"    {coluna:26s} {100 * mensal[coluna].notna().mean():5.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
