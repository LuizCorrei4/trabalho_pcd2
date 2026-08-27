"""T-021 — Reduz o clima de 701 estações do INMET para a grade UF × mês.

`data/interim/clima_estacao_mes.parquet` está no grão `codigo_estacao × ano_mes`.
A tabela final do projeto é UF × mês, então as estações de uma mesma UF precisam
virar um número só. A regra é **mediana**, não média: uma estação com sensor
defeituoso puxa a média e não move a mediana.

Duas armadilhas ficam registradas aqui porque são fáceis de errar:

1. **Chuva agrega por mediana neste passo, não por soma.** A regra "chuva soma"
   vale para dia -> mês (feita em `src/coleta/inmet/agrega_mes.py`). Somar o
   acumulado mensal das ~100 estações do RS daria ~50.000 mm, número sem
   sentido físico.
2. **Estação-mês com menos de 70 % de dias válidos vira NaN antes de agregar.**
   Um mês com 5 dias medidos não é uma medida do mês; entrar na mediana como se
   fosse inventa dado.

`n_estacoes` fica na saída de propósito: a rede do INMET **cresce** ao longo da
série e é muito desbalanceada entre UFs — depois do corte de 70 %, a mediana de
estações válidas por UF-mês vai de 1 (RR) a 77, com mediana geral de 11. Um
degrau de nível que coincide com salto de `n_estacoes` é artefato da rede, não
clima.

Uso:
    python src/tratamento/21_clima_uf_mes.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

from src.tratamento.chaves import padroniza_chaves, valida_chaves  # noqa: E402

ORIGEM = RAIZ / "data" / "interim" / "clima_estacao_mes.parquet"
DESTINO = RAIZ / "data" / "interim" / "clima_uf_mes.parquet"

# Abaixo disto a estação-mês não é uma medida do mês (T-021).
MIN_PCT_DIAS_VALIDOS = 70.0

# Médias do mês e índices de extremo. Fora ficam os absolutos (temp_max_abs,
# umidade_min_abs, vento_rajada_max_ms): o máximo entre estações é o de uma
# estação só, e a mediana de máximos não descreve nem o extremo nem o típico.
MEDIDAS = [
    "chuva_mm_mes",
    "temp_media",
    "temp_max_media",
    "temp_min_media",
    "umidade_media",
    "amplitude_termica_media",
    "dias_sem_chuva",
    "dias_chuva_forte",
    "dias_calor_extremo",
    "max_dias_secos_seguidos",
]


def agrega_uf_mes(estacoes: pd.DataFrame) -> pd.DataFrame:
    """estação × mês -> UF × mês, por mediana, com a contagem de estações."""
    df = padroniza_chaves(estacoes)

    # 1. Mascarar o mês mal medido ANTES de agregar.
    ruim = df["pct_dias_validos"] < MIN_PCT_DIAS_VALIDOS
    print(
        f"  {int(ruim.sum()):,} de {len(df):,} estação-mês "
        f"({ruim.mean():.1%}) com < {MIN_PCT_DIAS_VALIDOS:.0f}% de dias válidos -> NaN"
    )
    df.loc[ruim, MEDIDAS] = pd.NA
    df[MEDIDAS] = df[MEDIDAS].astype("float64")

    # 2. Mediana entre as estações da UF; n_estacoes conta só quem mediu chuva.
    uf_mes = (
        df.groupby(["sigla_uf", "ano_mes"], as_index=False)[MEDIDAS]
        .median()
        .merge(
            df[df["chuva_mm_mes"].notna()]
            .groupby(["sigla_uf", "ano_mes"], as_index=False)["codigo_estacao"]
            .nunique()
            .rename(columns={"codigo_estacao": "n_estacoes"}),
            on=["sigla_uf", "ano_mes"],
            how="left",
        )
    )
    uf_mes["n_estacoes"] = uf_mes["n_estacoes"].fillna(0).astype("int64")

    # 3. Prefixar tudo menos as chaves.
    return uf_mes.rename(
        columns={c: f"clima_{c}" for c in uf_mes.columns if c not in ("sigla_uf", "ano_mes")}
    )


def main() -> None:
    print(f"Lendo {ORIGEM.relative_to(RAIZ)}")
    estacoes = pd.read_parquet(ORIGEM)
    print(f"  {len(estacoes):,} linhas, {estacoes['codigo_estacao'].nunique()} estações")

    uf_mes = agrega_uf_mes(estacoes)
    valida_chaves(uf_mes, "clima_uf_mes")

    print(
        f"  n_estacoes por UF-mês: min {uf_mes['clima_n_estacoes'].min()}, "
        f"mediana {uf_mes['clima_n_estacoes'].median():.0f}, "
        f"max {uf_mes['clima_n_estacoes'].max()}"
    )

    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    uf_mes.to_parquet(DESTINO, index=False)
    print(f"[ok] {DESTINO.relative_to(RAIZ)} — {len(uf_mes):,} linhas x {uf_mes.shape[1]} colunas")


if __name__ == "__main__":
    main()
