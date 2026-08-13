"""T-013 — Coletor BCB/SGS: variáveis macroeconômicas de controle.

Sem controlar inflação e câmbio, o modelo atribui ao clima o que é só perda de poder
de compra da moeda. O IPCA aqui tem dupla função: é controle **e** é o deflator que o
T-024 usa para gerar o alvo em termos reais.

Séries (API pública do Banco Central, sem cadastro):
    1   Dólar PTAX venda        diária       -> média do mês e último dia útil
    433 IPCA variação mensal    mensal       -> ipca_mm e ipca_indice_base
    432 Selic meta              diária       -> taxa vigente no fim do mês (% a.a.)
    11  Selic efetiva           dias úteis   -> acumulada no mês (% a.m.)
    189 IGP-M                   mensal

Saídas:
    data/interim/macro_br_mes.parquet + .csv   (uma linha por mês, Brasil)

Uso:
    python src/coleta/04_bcb_sgs.py
    python src/coleta/04_bcb_sgs.py --inicio 2010
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests

RAIZ = Path(__file__).resolve().parents[2]
DIR_INTERIM = RAIZ / "data" / "interim"
DIR_RAW = RAIZ / "data" / "raw" / "bcb"

URL_SGS = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"

SERIES = {
    "dolar_ptax": 1,
    "ipca_mm": 433,
    "selic_meta": 432,
    "selic_efetiva": 11,
    "igpm": 189,
}

# Base do índice de preços. O T-024 deflaciona o alvo por esta coluna.
BASE_IPCA = "2015-01"

# Pontos de conferência contra a fonte (critério de aceite "conferir alguns meses").
REFERENCIAS = {
    "dolar médio 2020-03 (pico da pandemia)": ("dolar_ptax_medio", "2020-03", 4.90, 0.10),
    "dólar fim de 2022-12": ("dolar_ptax_fim", "2022-12", 5.22, 0.10),
    "Selic meta em 2016-12": ("selic", "2016-12", 13.75, 0.01),
}
# IPCA acumulado no ano, valores divulgados pelo IBGE.
REFERENCIAS_IPCA_ANO = {2015: 10.67, 2016: 6.29, 2021: 10.06, 2022: 5.79}

PAUSA_S = 0.4


def log(msg: str) -> None:
    print(f"[T-013] {msg}", flush=True)


def _para_numero(serie: pd.Series) -> pd.Series:
    """Valores vêm como string; algumas séries usam vírgula decimal."""
    limpa = serie.astype("string").str.strip().str.replace(",", ".", regex=False)
    return pd.to_numeric(limpa, errors="coerce")


def _blocos(inicio: date, fim: date, anos: int = 10) -> list[tuple[date, date]]:
    """A API tem limite informal de ~10 anos por requisição e falha silenciosamente
    acima dele: devolve 200 com payload truncado, sem erro."""
    blocos = []
    ini = inicio
    while ini <= fim:
        prox = date(min(ini.year + anos, fim.year + 1), 1, 1)
        blocos.append((ini, min(fim, date(prox.year, 1, 1) - pd.Timedelta(days=1).to_pytimedelta())))
        ini = prox
    return blocos


def busca_serie(codigo: int, inicio: date, fim: date, tentativas: int = 4) -> pd.DataFrame:
    """Baixa uma série do SGS paginando em blocos de 10 anos.

    Devolve DataFrame com `data` (datetime64) e `valor` (float), ordenado e sem
    duplicatas. Valida o intervalo devolvido contra o pedido — truncamento silencioso
    é a armadilha principal desta API.
    """
    pedacos = []
    for bloco_ini, bloco_fim in _blocos(inicio, fim):
        params = {
            "formato": "json",
            "dataInicial": bloco_ini.strftime("%d/%m/%Y"),
            "dataFinal": bloco_fim.strftime("%d/%m/%Y"),
        }
        for tentativa in range(1, tentativas + 1):
            try:
                r = requests.get(URL_SGS.format(codigo=codigo), params=params, timeout=120)
                r.raise_for_status()
                dados = r.json()
                break
            except Exception as e:
                if tentativa == tentativas:
                    raise RuntimeError(f"série {codigo} [{bloco_ini}..{bloco_fim}]: {e}") from e
                espera = 2**tentativa
                log(f"  tentativa {tentativa} falhou ({e}); repetindo em {espera}s")
                time.sleep(espera)

        if not dados:
            log(f"  série {codigo}: bloco {bloco_ini}..{bloco_fim} veio vazio")
            continue

        df = pd.DataFrame(dados)
        # format explícito: sem ele "03/04" pode virar 4 de março em vez de 3 de abril.
        df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y")
        df["valor"] = _para_numero(df["valor"])

        # Truncamento silencioso: um bloco histórico tem que chegar perto do fim pedido.
        atraso = (pd.Timestamp(bloco_fim) - df["data"].max()).days
        if bloco_fim < date.today() and atraso > 45:
            raise RuntimeError(
                f"série {codigo}: pedi até {bloco_fim} e voltou só até "
                f"{df['data'].max():%Y-%m-%d} ({atraso} dias a menos) — payload truncado"
            )

        pedacos.append(df[["data", "valor"]])
        time.sleep(PAUSA_S)

    if not pedacos:
        raise RuntimeError(f"série {codigo}: nenhum dado devolvido")

    completa = pd.concat(pedacos, ignore_index=True).drop_duplicates("data")
    return completa.sort_values("data").reset_index(drop=True)


def _mensaliza(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["ano_mes"] = df["data"].dt.to_period("M").dt.to_timestamp()
    return df


def coleta(inicio: date, fim: date) -> pd.DataFrame:
    brutos = {}
    for nome, codigo in SERIES.items():
        serie = busca_serie(codigo, inicio, fim)
        brutos[nome] = serie
        log(f"série {codigo:>3} ({nome}): {len(serie):,} obs, "
            f"{serie['data'].min():%Y-%m-%d} → {serie['data'].max():%Y-%m-%d}")

    DIR_RAW.mkdir(parents=True, exist_ok=True)
    for nome, serie in brutos.items():
        serie.to_parquet(DIR_RAW / f"sgs_{SERIES[nome]}_{nome}.parquet", index=False)

    # Dólar: média do mês e último dia útil.
    dolar = _mensaliza(brutos["dolar_ptax"])
    macro = dolar.groupby("ano_mes", as_index=False).agg(
        dolar_ptax_medio=("valor", "mean"),
        dolar_ptax_fim=("valor", "last"),
    )

    # Selic meta: a taxa vigente no fim do mês (série 432 é diária, dias corridos).
    selic = _mensaliza(brutos["selic_meta"]).groupby("ano_mes", as_index=False).agg(
        selic=("valor", "last")
    )

    # Selic efetiva: a série 11 é % ao dia útil — compõe dentro do mês, não soma.
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

    return macro[
        [
            "ano_mes",
            "dolar_ptax_medio",
            "dolar_ptax_fim",
            "ipca_mm",
            "ipca_indice_base",
            "selic",
            "selic_efetiva_am",
            "igpm",
        ]
    ]


def _indice_base(variacao_pct: pd.Series, ano_mes: pd.Series) -> pd.Series:
    """Índice acumulado a partir da variação mensal, com base BASE_IPCA = 100."""
    fator = (1 + variacao_pct / 100).cumprod()
    base = fator[ano_mes.dt.to_period("M").astype(str) == BASE_IPCA]
    if base.empty:
        raise ValueError(f"mês-base {BASE_IPCA} fora do período coletado")
    return fator / base.iloc[0] * 100


def apara_incompletos(macro: pd.DataFrame) -> pd.DataFrame:
    """Corta os meses do fim que ainda não têm todas as séries publicadas.

    O IPCA do mês corrente só sai no meio do mês seguinte; sem isso o arquivo
    terminaria com NaN e quebraria o critério de aceite.
    """
    completos = macro.notna().all(axis=1)
    if completos.all():
        return macro

    ultimo = completos[completos].index.max()
    descartados = macro.loc[ultimo + 1 :, "ano_mes"].dt.strftime("%Y-%m").tolist()
    if descartados:
        log(f"meses ainda incompletos, descartados: {', '.join(descartados)}")

    aparado = macro.loc[:ultimo].copy()
    buracos = aparado[aparado.isna().any(axis=1)]
    if not buracos.empty:
        raise ValueError(
            "NaN no meio da série (não é só o fim):\n"
            + buracos.assign(m=buracos["ano_mes"].dt.strftime("%Y-%m")).to_string()
        )
    return aparado.reset_index(drop=True)


def valida(macro: pd.DataFrame, inicio: date) -> str:
    linhas = ["# QA — T-013 BCB/SGS", "", f"Gerado em {date.today().isoformat()}.", ""]

    def ok(c: bool) -> str:
        return "✅" if c else "❌"

    meses = macro["ano_mes"].dt.to_period("M")
    esperados = pd.period_range(f"{inicio.year}-{inicio.month:02d}", meses.max(), freq="M")
    buracos = sorted(set(esperados) - set(meses))
    linhas.append(
        f"{ok(not buracos)} **Cobertura mensal**: {meses.min()} → {meses.max()} "
        f"({len(meses)} meses; buracos: {[str(b) for b in buracos] or 'nenhum'})"
    )

    nulos = int(macro.isna().sum().sum())
    linhas.append(f"{ok(nulos == 0)} **Sem NaN**: {nulos} nulos em {macro.size:,} células")

    # O índice não é estritamente crescente — deflação mensal existe (2017-06, 2022-07..09).
    # O que denuncia erro de acumulação é queda *sustentada*.
    idx = macro["ipca_indice_base"].astype(float)
    quedas = (idx.diff().fillna(0.0) < 0).astype(int)
    # soma dentro de cada corrida de valores iguais: nas corridas de 1 dá o comprimento
    maior_seq = int(quedas.groupby((quedas != quedas.shift()).cumsum()).sum().max())
    recuo_max = float((idx / idx.cummax() - 1).min() * 100)
    linhas.append(
        f"{ok(idx.iloc[-1] > idx.iloc[0] and recuo_max > -3)} **ipca_indice_base**: "
        f"{idx.iloc[0]:.2f} → {idx.iloc[-1]:.2f} "
        f"(maior sequência de queda: {int(maior_seq)} meses; recuo máximo: {recuo_max:.2f}%)"
    )

    linhas += ["", "## Conferência contra a fonte", ""]
    for rotulo, (coluna, mes, esperado, tol) in REFERENCIAS.items():
        obtido = macro.loc[macro["ano_mes"].dt.to_period("M").astype(str) == mes, coluna]
        if obtido.empty:
            linhas.append(f"- ⚠️ {rotulo}: mês fora do período coletado")
            continue
        v = float(obtido.iloc[0])
        linhas.append(f"- {ok(abs(v - esperado) <= tol)} {rotulo}: {v:.4f} (esperado ~{esperado})")

    acum = (
        macro.assign(ano=macro["ano_mes"].dt.year, f=1 + macro["ipca_mm"] / 100)
        .groupby("ano")["f"]
        .prod()
        .sub(1)
        .mul(100)
    )
    for ano, esperado in REFERENCIAS_IPCA_ANO.items():
        if ano in acum.index:
            v = float(acum[ano])
            linhas.append(
                f"- {ok(abs(v - esperado) <= 0.05)} IPCA acumulado em {ano}: "
                f"{v:.2f}% (IBGE: {esperado}%)"
            )

    linhas += ["", "## Amostra", "", "```"]
    amostra = macro.iloc[[0, len(macro) // 2, -1]].copy()
    amostra["ano_mes"] = amostra["ano_mes"].dt.strftime("%Y-%m")
    linhas += [amostra.to_string(index=False), "```"]
    return "\n".join(linhas) + "\n"


def salva(df: pd.DataFrame, nome: str) -> None:
    DIR_INTERIM.mkdir(parents=True, exist_ok=True)
    pq = DIR_INTERIM / f"{nome}.parquet"
    csv = DIR_INTERIM / f"{nome}.csv"
    df.to_parquet(pq, index=False)
    df.to_csv(csv, index=False, encoding="utf-8")
    log(f"→ {pq.relative_to(RAIZ)} + {nome}.csv ({len(df):,} linhas)")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="T-013 — coletor BCB/SGS")
    p.add_argument("--inicio", type=int, default=2014, help="primeiro ano (padrão 2014)")
    args = p.parse_args(argv)

    inicio = date(args.inicio, 1, 1)
    macro = coleta(inicio, date.today())
    macro = apara_incompletos(macro)
    salva(macro, "macro_br_mes")

    relatorio = valida(macro, inicio)
    (DIR_INTERIM / "qa_T-013_bcb.md").write_text(relatorio, encoding="utf-8")
    print("\n" + relatorio)
    return 0


if __name__ == "__main__":
    sys.exit(main())
