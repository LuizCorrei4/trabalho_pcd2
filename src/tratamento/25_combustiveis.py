"""T-025 — Acrescenta a família `comb_*` (preços de combustível, ANP) à tabela fato.

Entrada:

    data/raw/combustiveis/combustivel.csv          sigla_uf × ano_mes × produto   str
    data/processed/fato_alimentos_uf_mes.parquet   sigla_uf × ano_mes  (89 colunas)

Saída:

    data/interim/combustiveis_uf_mes.parquet                    27 UF × mês, largo
    data/processed/fato_alimentos_combustiveis_uf_mes.parquet   2.088 × 107
    outputs/tabelas/dicionario_variaveis_combustiveis.csv       uma linha por coluna

Por que combustível entra numa tabela sobre inflação de alimentos: o diesel é o
custo de frete de toda a comida que sai da lavoura, e o GLP é item da própria
cesta do IPCA (é o gás de cozinha). São as duas pontas — o choque de custo que
chega antes e o preço que já está dentro do alvo.

Quatro decisões que a estrutura deste arquivo existe para garantir:

* **O grão nativo inclui `produto`.** Sem pivotar, o merge multiplica a espinha
  por 5. Mesmo problema da safra no T-024.
* **A média de preço é ponderada por `quantidade_registros`.** Um UF-mês com 1
  posto pesquisado não pode pesar o mesmo que um com 5.681 — e é assim que as
  182 linhas duplicadas da fonte se consolidam sem escolher arbitrariamente uma.
* **A variação % é calculada sobre a grade completa de meses, antes do merge.**
  Um `shift(1)` sobre a tabela com buracos compararia 2015-02 com 2015-07 sem
  avisar. Sobre a grade, o buraco vira `NaN` e a variação some junto.
* **O buraco não é preenchido.** A fonte não tem coleta de líquido em 33 dos 138
  meses da janela (e de GLP em 15 — são duas pesquisas com falhas diferentes);
  interpolar inventaria preço em 23 % das linhas.

Uso:
    python src/tratamento/25_combustiveis.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

from src.tratamento.chaves import (  # noqa: E402
    carrega_dim_uf,
    checa_join,
    padroniza_chaves,
    valida_chaves,
)

RAW_CSV = RAIZ / "data" / "raw" / "combustiveis" / "combustivel.csv"
AMOSTRA_CSV = (
    RAIZ / "data" / "raw" / "combustiveis"
    / "results-20260827-153515 - results-20260827-153515.csv"
)
INTERIM = RAIZ / "data" / "interim"
PROCESSED = RAIZ / "data" / "processed"
OUT_TABELAS = RAIZ / "outputs" / "tabelas"

FATO_ENTRADA = PROCESSED / "fato_alimentos_uf_mes.parquet"
FATO_SAIDA = PROCESSED / "fato_alimentos_combustiveis_uf_mes.parquet"

# Os cinco produtos que cobrem a janela inteira (2015-01 a 2026-06) nas 16 UFs
# do alvo. Ficaram de fora, e por quê:
#   Diesel S50          — só existe em 2012, fora da janela (73 linhas no total)
#   Gasolina Aditivada  — começa em 2020-10; 48 % da grade e ~0,99 de correlação
#                         com a gasolina comum, então não acrescenta sinal
#   Gnv                 — 55 % da grade, ausente em 1 UF, e é combustível de
#                         frota urbana leve: não move frete agrícola nem cesta
PRODUTOS = {
    "Diesel": "diesel",
    "Diesel S10": "diesel_s10",
    "Gasolina": "gasolina",
    "Etanol": "etanol",
    "Glp": "glp_13kg",
}

# Unidade de cada coluna de preço. O GLP é vendido por botijão de 13 kg, não por
# litro — está no nome da coluna para que ninguém compare o nível com os outros.
UNIDADES = {
    "diesel": "R$/litro",
    "diesel_s10": "R$/litro",
    "gasolina": "R$/litro",
    "etanol": "R$/litro",
    "glp_13kg": "R$/botijão 13 kg",
}


# ============================================================================
# Passo 1 — bruto -> UF × mês × produto, sem duplicata
# ============================================================================
def carrega_bruto() -> pd.DataFrame:
    """Lê o CSV da ANP e devolve com as chaves no contrato do projeto.

    `preco_compra_medio` é descartada aqui: é 100 % nula de 2021 em diante (a ANP
    parou de publicar o preço de aquisição do revendedor) e 48 % nula no total.
    Uma coluna que morre no meio da série vira degrau artificial em qualquer
    modelo que a use.
    """
    df = pd.read_csv(RAW_CSV, dtype={"sigla_uf": "string", "produto": "string"})
    df = padroniza_chaves(df)
    df["preco_venda_medio"] = df["preco_venda_medio"].astype("float64")
    df["quantidade_registros"] = df["quantidade_registros"].astype("int64")
    return df[["sigla_uf", "ano_mes", "produto", "preco_venda_medio", "quantidade_registros"]]


def consolida(df: pd.DataFrame) -> pd.DataFrame:
    """UF × mês × produto único, com preço ponderado pelo nº de postos.

    A fonte traz 182 linhas duplicadas em (ano_mes, sigla_uf, produto) — quase
    todas em 2026-04, que veio em duas levas de coleta, e o resto são linhas
    soltas com `unidade_medida` nula e 1 posto. A média ponderada por
    `quantidade_registros` resolve os dois casos com a mesma regra: a leva de 38
    postos domina a de 13, e o posto solto de 2010 vale 1/162 do mês.
    """
    df = df[df["produto"].isin(PRODUTOS)].copy()
    df["produto"] = df["produto"].map(PRODUTOS)

    df["_soma_precos"] = df["preco_venda_medio"] * df["quantidade_registros"]
    g = df.groupby(["sigla_uf", "ano_mes", "produto"], as_index=False).agg(
        _soma_precos=("_soma_precos", "sum"),
        n_registros=("quantidade_registros", "sum"),
    )
    g["preco"] = g["_soma_precos"] / g["n_registros"]
    return g.drop(columns="_soma_precos")


# ============================================================================
# Passo 2 — longo -> largo sobre a grade completa de meses
# ============================================================================
def monta_grade(meses: pd.PeriodIndex) -> pd.DataFrame:
    """27 UFs × todos os meses entre o primeiro e o último da fonte.

    Existe por causa do `shift`: a fonte pula meses inteiros (33 deles só na
    janela do fato), e um `pct_change` sobre a tabela como ela vem compararia
    2018-03 com 2018-07 chamando o resultado de "variação mensal". Sobre a
    grade, o mês ausente é uma linha `NaN` e a variação nasce `NaN` junto — que
    é a verdade.
    """
    ufs = carrega_dim_uf()[["sigla_uf"]]
    return ufs.merge(pd.DataFrame({"ano_mes": meses}), how="cross")


def prepara_combustiveis() -> pd.DataFrame:
    """`UF × mês × produto` -> `UF × mês` largo, com nível e variações.

    Roda sobre a série inteira (desde 2004-05), não sobre a janela do fato: a
    variação em 12 meses de 2015-01 precisa de 2014, que o recorte jogaria fora.
    """
    consolidado = consolida(carrega_bruto())
    valida_chaves(consolidado, "combustivel (longo)", unica=False)

    largo = consolidado.pivot_table(
        index=["sigla_uf", "ano_mes"], columns="produto", values="preco", aggfunc="first"
    )
    largo.columns = [f"comb_preco_{p}" for p in largo.columns]
    largo = largo.reset_index()

    # Quantos postos-coleta sustentam a linha inteira. É o análogo de
    # `clima_n_estacoes`: não é uma medida de preço, é o controle de quanta
    # medição existe por trás dele.
    postos = consolidado.groupby(["sigla_uf", "ano_mes"], as_index=False)["n_registros"].sum()
    largo = largo.merge(postos, on=["sigla_uf", "ano_mes"], how="left")
    largo = largo.rename(columns={"n_registros": "comb_n_registros"})

    meses = pd.period_range(largo["ano_mes"].min(), largo["ano_mes"].max(), freq="M")
    largo = (
        monta_grade(meses)
        .merge(largo, on=["sigla_uf", "ano_mes"], how="left")
        .sort_values(["sigla_uf", "ano_mes"])
        .reset_index(drop=True)
    )

    colunas_preco = [f"comb_preco_{p}" for p in PRODUTOS.values()]
    for coluna in colunas_preco:
        base = largo.groupby("sigla_uf")[coluna]
        sufixo = coluna.removeprefix("comb_preco_")
        largo[f"comb_var_mm_{sufixo}"] = (largo[coluna] / base.shift(1) - 1) * 100
        largo[f"comb_var12_{sufixo}"] = (largo[coluna] / base.shift(12) - 1) * 100

    # Dispersão espacial: o diesel da UF contra a mediana nacional DAQUELE mês.
    # As colunas macro_* são idênticas em todas as UFs e por isso não explicam
    # diferença entre capitais; esta explica — é o custo de frete relativo.
    mediana_br = largo.groupby("ano_mes")["comb_preco_diesel"].transform("median")
    largo["comb_diesel_vs_br_pct"] = (largo["comb_preco_diesel"] / mediana_br - 1) * 100

    # Os flags que separam "sem coleta" de "coleta com preço zero" (que não
    # existe). São DOIS porque a ANP roda duas pesquisas com falhas diferentes:
    # os líquidos perdem 33 meses da janela e o GLP perde 15, sendo 10 em comum.
    # Um flag só chamaria de "observado" um mês que tem GLP e não tem diesel.
    liquidos = [c for c in colunas_preco if c != "comb_preco_glp_13kg"]
    largo["comb_observado"] = largo[colunas_preco].notna().any(axis=1)
    largo["comb_observado_liquidos"] = largo[liquidos].notna().any(axis=1)

    return largo


# ============================================================================
# Passo 3 — o merge no fato
# ============================================================================
def junta() -> pd.DataFrame:
    if not FATO_ENTRADA.exists():
        raise FileNotFoundError(
            f"{FATO_ENTRADA} não existe. Rode `python src/tratamento/24_junta.py` (T-024) antes."
        )

    print("\n[1] Espinha — o fato do T-024")
    fato = padroniza_chaves(pd.read_parquet(FATO_ENTRADA))
    valida_chaves(fato, "fato_alimentos_uf_mes")

    print("\n[2] Combustíveis")
    comb = prepara_combustiveis()
    valida_chaves(comb, "combustiveis_uf_mes")
    INTERIM.mkdir(parents=True, exist_ok=True)
    comb.to_parquet(INTERIM / "combustiveis_uf_mes.parquet", index=False)

    print("\n[3] LEFT JOIN")
    antes = fato
    fato = antes.merge(comb, on=["sigla_uf", "ano_mes"], how="left", validate="m:1")
    checa_join(antes, fato, "combustiveis", ["sigla_uf", "ano_mes"],
               coluna_teste="comb_preco_diesel")

    return fato.reset_index(drop=True)


# ============================================================================
# Dicionário de variáveis
# ============================================================================
NOMES_LEGIVEIS = {
    "diesel": "diesel comum",
    "diesel_s10": "diesel S10",
    "gasolina": "gasolina comum",
    "etanol": "etanol hidratado",
    "glp_13kg": "GLP (gás de cozinha, botijão de 13 kg)",
}

JUSTIFICATIVA_COMB = (
    "A extração da ANP não tem coleta de combustível líquido em 33 dos 138 meses da janela, e de "
    "GLP em 15 (10 meses não têm nada) — a falha é simultânea nas 27 UFs, então é lacuna da "
    "série, não de uma UF. NaN = MÊS SEM PESQUISA, nunca preço zero ou produto indisponível. "
    "Filtre por comb_observado_liquidos (ou comb_observado, para o GLP) antes de usar; não "
    "interpole sem dizer que interpolou. As colunas de variação herdam o buraco de propósito: "
    "sem o mês anterior não existe variação mensal."
)


def _descreve_comb(coluna: str) -> tuple[str, str, str, str]:
    """(unidade, fonte, granularidade nativa, descrição) de uma coluna comb_*."""
    fonte = "ANP (Levantamento de Preços de Combustíveis)"
    grao = "UF × mês × produto"

    if coluna == "comb_n_registros":
        return ("postos-coleta", fonte, grao,
                "quantas coletas de preço sustentam a linha, somadas sobre os 5 produtos — "
                "controle do tamanho da amostra, não uma medida de preço")
    if coluna == "comb_observado":
        return ("bool", fonte, "UF × mês",
                "houve alguma coleta da ANP nessa UF nesse mês, de qualquer um dos 5 produtos — "
                "False significa SEM PESQUISA, não preço ausente")
    if coluna == "comb_observado_liquidos":
        return ("bool", fonte, "UF × mês",
                "houve coleta de combustível líquido (diesel, S10, gasolina ou etanol) — é este "
                "o filtro para as colunas de líquido; o GLP tem pesquisa própria, com outras faltas")
    if coluna == "comb_diesel_vs_br_pct":
        return ("%", fonte, "UF × mês",
                "desvio % do diesel da UF em relação à mediana nacional do mesmo mês — "
                "custo de frete relativo, a dimensão espacial que as colunas macro_* não têm")

    if coluna.startswith("comb_preco_"):
        slug = coluna.removeprefix("comb_preco_")
        return (UNIDADES[slug], fonte, grao,
                f"preço médio de venda ao consumidor de {NOMES_LEGIVEIS[slug]}, "
                "média ponderada pelo nº de postos pesquisados na UF")
    if coluna.startswith("comb_var_mm_"):
        slug = coluna.removeprefix("comb_var_mm_")
        return ("%", fonte, grao,
                f"variação % do preço de {NOMES_LEGIVEIS[slug]} contra o mês imediatamente "
                "anterior; NaN quando falta um dos dois meses")
    slug = coluna.removeprefix("comb_var12_")
    return ("%", fonte, grao,
            f"variação % do preço de {NOMES_LEGIVEIS[slug]} contra o mesmo mês do ano "
            "anterior; NaN quando falta um dos dois meses")


def monta_dicionario(fato: pd.DataFrame) -> pd.DataFrame:
    """Dicionário da tabela final: as 89 linhas do T-024 mais as novas comb_*.

    As descrições antigas vêm do CSV do T-024 em vez de serem reescritas — uma
    fonte só para cada coluna. O `pct_nulos` é recalculado sobre a tabela nova
    (o LEFT JOIN preserva as linhas, então não muda, mas o número tem de sair da
    tabela que o arquivo descreve).
    """
    anterior = pd.read_csv(OUT_TABELAS / "dicionario_variaveis.csv").set_index("coluna")

    linhas = []
    for coluna in fato.columns:
        if coluna.startswith("comb_"):
            unidade, fonte, granularidade, descricao = _descreve_comb(coluna)
        else:
            reg = anterior.loc[coluna]
            unidade, fonte = reg["unidade"], reg["fonte"]
            granularidade, descricao = reg["granularidade_nativa"], reg["descricao"]

        pct_nulos = float(fato[coluna].isna().mean()) * 100
        if pct_nulos == 0:
            obs = ""
        elif coluna.startswith("comb_"):
            obs = JUSTIFICATIVA_COMB
        else:
            obs = anterior.loc[coluna, "observacao"]
            obs = "" if pd.isna(obs) else obs

        linhas.append({
            "coluna": coluna,
            "descricao": descricao,
            "unidade": unidade,
            "fonte": fonte,
            "granularidade_nativa": granularidade,
            "pct_nulos": round(pct_nulos, 2),
            "observacao": obs,
        })
    return pd.DataFrame(linhas)


# ============================================================================
# Validação independente — a amostra de coletas individuais
# ============================================================================
def confere_com_amostra(consolidado: pd.DataFrame) -> pd.DataFrame:
    """Compara o agregado com a média crua do arquivo de coletas individuais.

    `results-*.csv` é outra extração da mesma base: 96.049 coletas posto a posto,
    com data e município, espalhadas por 11 anos. Não serve de fonte (a cobertura
    é esburacada), mas serve de testemunha: se a média simples das coletas de um
    UF-mês bate com o `preco_venda_medio` agregado, a agregação da fonte é o que
    diz ser. Só compara UF-meses com pelo menos 20 coletas na amostra.
    """
    amostra = pd.read_csv(AMOSTRA_CSV, decimal=",")
    amostra["ano_mes"] = pd.to_datetime(amostra["data_coleta"]).dt.to_period("M")
    amostra = amostra[amostra["produto"].isin(PRODUTOS)].copy()
    amostra["produto"] = amostra["produto"].map(PRODUTOS)

    por_mes = amostra.groupby(["sigla_uf", "ano_mes", "produto"], as_index=False).agg(
        preco_amostra=("preco_venda", "mean"), n_coletas=("preco_venda", "size")
    )
    comparavel = por_mes[por_mes["n_coletas"] >= 20].merge(
        consolidado, on=["sigla_uf", "ano_mes", "produto"], how="inner"
    )
    comparavel["erro_pct"] = (comparavel["preco_amostra"] / comparavel["preco"] - 1) * 100
    return comparavel


# ============================================================================
def main() -> None:
    fato = junta()

    print("\n[4] Validações")
    assert fato.duplicated(["sigla_uf", "ano_mes"]).sum() == 0, "chave duplicada"
    assert isinstance(fato["ano_mes"].dtype, pd.PeriodDtype), "ano_mes não é Period[M]"
    assert len(fato) == 2088, f"o merge mexeu no nº de linhas: {len(fato):,}"

    precos = [f"comb_preco_{p}" for p in PRODUTOS.values()]
    combustivel_liquido = [c for c in precos if c != "comb_preco_glp_13kg"]
    liquidos = fato[combustivel_liquido].stack().dropna()
    assert liquidos.between(1, 15).all(), "preço de líquido fora de 1-15 R$/l"
    assert fato["comb_preco_glp_13kg"].dropna().between(20, 200).all(), "GLP fora de 20-200 R$"
    assert (
        fato.loc[~fato["comb_observado_liquidos"], combustivel_liquido].isna().all().all()
    ), "comb_observado_liquidos == False com preço de líquido preenchido"

    # O sinal que justifica a família existir: o diesel sobe antes da comida.
    correl = fato[["comb_var12_diesel", "ipca_var_alimentacao_acum12"]].corr().iloc[0, 1]
    assert correl > 0.2, f"diesel e alimentos sem relação (corr={correl:.2f})"
    print(f"  chave única, 2.088 linhas, preços em faixa plausível")
    print(f"  corr(comb_var12_diesel, ipca_var_alimentacao_acum12) = {correl:.3f}")

    conferencia = confere_com_amostra(consolida(carrega_bruto()))
    erro_mediano = conferencia["erro_pct"].abs().median()
    assert erro_mediano < 2, f"agregado diverge da amostra de coletas ({erro_mediano:.2f} %)"
    print(f"  {len(conferencia):,} UF-meses conferidos contra as coletas individuais: "
          f"erro absoluto mediano {erro_mediano:.2f} %")

    print(
        f"  {len(fato):,} linhas | {fato.sigla_uf.nunique()} UFs | "
        f"{fato.ano_mes.nunique()} meses | {fato.shape[1]} colunas"
    )

    PROCESSED.mkdir(parents=True, exist_ok=True)
    OUT_TABELAS.mkdir(parents=True, exist_ok=True)
    fato.to_parquet(FATO_SAIDA, index=False)

    dic = monta_dicionario(fato)
    dic.to_csv(OUT_TABELAS / "dicionario_variaveis_combustiveis.csv", index=False, encoding="utf-8")

    sem_justificativa = dic[(dic.pct_nulos > 40) & (dic.observacao == "")]
    assert sem_justificativa.empty, f"colunas > 40 % nulas sem justificativa:\n{sem_justificativa}"

    print(f"\n[ok] data/interim/combustiveis_uf_mes.parquet")
    print(f"[ok] {FATO_SAIDA.relative_to(RAIZ)}")
    print(f"[ok] outputs/tabelas/dicionario_variaveis_combustiveis.csv — "
          f"{len(dic)} colunas documentadas")


if __name__ == "__main__":
    main()
