"""T-024 — Junta as cinco fontes numa única tabela UF × mês.

Entrada (grãos e tipos de `ano_mes` todos diferentes):

    data/interim/ipca_alimentos_rm.parquet   ano_mes × sigla_uf × item   str
    data/interim/clima_uf_mes.parquet        sigla_uf × ano_mes          Period  (T-021)
    data/interim/safra_uf_mes.parquet        sigla_uf × produto × ano_mes datetime64
    data/interim/seca_uf_mes.parquet         sigla_uf × ano_mes          str
    data/interim/parquet/macro_br_mes.parquet ano_mes                    datetime64

Saída:

    data/processed/calendario_uf_mes.parquet    27 UF × 138 meses = 3.726
    data/processed/fato_alimentos_uf_mes.parquet 16 UF × meses com alvo = 2.088
    outputs/tabelas/dicionario_variaveis.csv     uma linha por coluna

O desenho está em `docs/analise_juncao_uf_mes.md`. Três regras que a estrutura
deste arquivo existe para garantir:

* **A espinha é o calendário completo e todo merge é LEFT.** As 11 UFs sem IPCA
  e os meses sem alvo caem só no filtro final, então a perda é contada, não
  silenciosa.
* **Prefixo antes do merge, nunca `suffixes`.** `_x`/`_y` deixam a tabela
  ilegível, e `ano`/`mes` existem em seca e clima — são descartadas, não
  desambiguadas.
* **`checa_join()` depois de cada merge.** O merge entre `str` e `Timestamp` não
  levanta erro: devolve tudo NaN. E a safra não pivotada multiplica a espinha
  por 11.

Uso:
    python src/tratamento/24_junta.py
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

INTERIM = RAIZ / "data" / "interim"
PROCESSED = RAIZ / "data" / "processed"
OUT_TABELAS = RAIZ / "outputs" / "tabelas"

PERIODO_INICIO = "2015-01"
PERIODO_FIM = "2026-06"

# ------------------------------------------------------------------- IPCA ---
# Os 17 códigos com cobertura máxima na janela (2.088 linhas cada). Misturam de
# propósito três níveis da hierarquia do IBGE — grupo (1), subgrupo (4 dígitos)
# e subitem (7 dígitos). São colunas para ler lado a lado; SOMAR os pesos entre
# elas dupla-conta, porque o subitem já está dentro do subgrupo.
ITENS_IPCA = {
    "1": ("alimentacao", "grupo"),
    "1102": ("farinhas", "subgrupo"),
    "1104": ("acucares", "subgrupo"),
    "1105": ("hortalicas", "subgrupo"),
    "1107": ("carnes", "subgrupo"),
    "1109": ("carnes_industrializadas", "subgrupo"),
    "1110": ("aves_ovos", "subgrupo"),
    "1111": ("leites_derivados", "subgrupo"),
    "1101002": ("arroz", "subitem"),
    "1103003": ("batata_inglesa", "subitem"),
    "1103028": ("tomate", "subitem"),
    "1110009": ("frango_inteiro", "subitem"),
    "1110010": ("frango_pedacos", "subitem"),
    "1111004": ("leite_longa_vida", "subitem"),
    "1112015": ("pao_frances", "subitem"),
    "1113013": ("oleo_soja", "subitem"),
    "1114022": ("cafe_moido", "subitem"),
}

# ------------------------------------------------------------------ safra ---
# 11 produtos × 2 medidas = 22 colunas. As outras três medidas do LSPA
# (area_plantada_ha, area_colhida_ha, rendimento_kg_ha) continuam em interim/ e
# podem entrar depois; 55 colunas de saída seriam ruído.
MEDIDAS_SAFRA = ["producao_t", "revisao_pct_prod"]

# A revisão % tem cauda explosiva (máximo acima de 15 milhões %, de divisão por
# base minúscula) enquanto 91,8 % dos valores cabem em ±20 %. Sem corte, uma
# linha domina qualquer regressão.
LIMITE_REVISAO = 50.0

# ------------------------------------------------------------------- seca ---
COLUNAS_SECA = [
    "severidade_media",
    "severidade_media_area_seca",
    "pct_area_S0plus",
    "pct_area_S1plus",
    "pct_area_S2plus",
    "pct_area_S3plus",
    "pct_area_S4plus",
    "meses_consecutivos_S2plus",
    "monitorado",
]

# ------------------------------------------------------------------ macro ---
COLUNAS_MACRO = ["ipca_mm", "dolar_ptax_medio", "dolar_ptax_fim", "selic", "igpm"]


# ============================================================================
# Passo 2 — calendário-espinha
# ============================================================================
def monta_calendario() -> pd.DataFrame:
    """Produto cartesiano dim_uf × meses da janela: 27 × 138 = 3.726 linhas."""
    ufs = carrega_dim_uf()[["sigla_uf", "nome_uf", "regiao"]]
    meses = pd.period_range(PERIODO_INICIO, PERIODO_FIM, freq="M")

    cal = (
        ufs.merge(pd.DataFrame({"ano_mes": meses}), how="cross")
        .sort_values(["sigla_uf", "ano_mes"])
        .reset_index(drop=True)
    )
    cal["ano"] = cal["ano_mes"].dt.year
    cal["mes"] = cal["ano_mes"].dt.month
    return cal[["sigla_uf", "nome_uf", "regiao", "ano_mes", "ano", "mes"]]


# ============================================================================
# Passo 3a — IPCA longo -> largo, e os três alvos
# ============================================================================
def prepara_ipca() -> pd.DataFrame:
    """`ano_mes × uf × item` -> `uf × mês` largo, com variação e peso de 17 itens.

    Roda sobre a série inteira (desde 2006-07), não sobre a janela: o acumulado
    em 12 meses de 2015-01 precisa de 2014, que o recorte jogaria fora.
    """
    df = pd.read_parquet(INTERIM / "ipca_alimentos_rm.parquet")
    col_var = next(c for c in df.columns if "Varia" in c)
    col_peso = next(c for c in df.columns if "Peso" in c)

    # O item traz o código embutido: "1101002.Arroz". Chavear pelo código é
    # seguro — as duas colisões código<->nome do IBGE são renomeações em datas
    # disjuntas e nenhuma delas está entre os 17 selecionados.
    df["cod_item"] = df["item"].str.split(".", n=1).str[0]
    df = df[df["cod_item"].isin(ITENS_IPCA)].copy()
    df = padroniza_chaves(df)

    largo = df.pivot_table(
        index=["sigla_uf", "ano_mes"],
        columns="cod_item",
        values=[col_var, col_peso],
        aggfunc="first",
    )
    largo.columns = [
        f"ipca_{'var' if medida == col_var else 'peso'}_{ITENS_IPCA[cod][0]}"
        for medida, cod in largo.columns
    ]
    largo = largo.reset_index().sort_values(["sigla_uf", "ano_mes"])

    # Alvo 2: acumulado em 12 meses, composto — (1+r) multiplicados, não somados.
    fator = 1 + largo["ipca_var_alimentacao"] / 100
    largo["ipca_var_alimentacao_acum12"] = (
        fator.groupby(largo["sigla_uf"])
        .apply(lambda s: s.rolling(12).apply(lambda w: w.prod(), raw=True))
        .reset_index(level=0, drop=True)
        .sub(1)
        .mul(100)
    )

    return largo.reset_index(drop=True)


# ============================================================================
# Passo 3c — safra longa -> larga
# ============================================================================
def prepara_safra() -> pd.DataFrame:
    """`uf × produto × mês` -> `uf × mês` com 11 produtos × 2 medidas.

    Sem este pivô o merge multiplica a espinha por 11: a tabela tem 40.770
    duplicatas em (sigla_uf, ano_mes) porque o grão nativo inclui `produto`.
    """
    df = padroniza_chaves(pd.read_parquet(INTERIM / "safra_uf_mes.parquet"))
    valida_chaves(df, "safra_uf_mes (longa)", unica=False)

    df["revisao_pct_prod"] = df["revisao_pct_prod"].astype("float64").clip(
        -LIMITE_REVISAO, LIMITE_REVISAO
    )
    df["producao_t"] = df["producao_t"].astype("float64")

    largo = df.pivot_table(
        index=["sigla_uf", "ano_mes"], columns="produto", values=MEDIDAS_SAFRA, aggfunc="first"
    )
    largo.columns = [
        f"safra_{'producao_t' if medida == 'producao_t' else 'revisao_pct'}_{produto}"
        for medida, produto in largo.columns
    ]

    # NaN em producao_t é "a UF não planta esse produto", não medida faltante —
    # a grade UF × produto × mês é perfeita (27 × 11 × 151). Zero tonelada é
    # literalmente verdade, então preenche. Em revisao_pct a revisão é
    # *indefinida* (não há base anterior), e zero seria "a estimativa não mudou":
    # essa fica NaN.
    prod = [c for c in largo.columns if c.startswith("safra_producao_t_")]
    largo[prod] = largo[prod].fillna(0.0)

    return largo.reset_index()


# ============================================================================
# Passo 3d/3e — seca e macro
# ============================================================================
def prepara_seca() -> pd.DataFrame:
    """Já está em UF × mês: padroniza a chave, descarta derivadas, prefixa."""
    df = padroniza_chaves(pd.read_parquet(INTERIM / "seca_uf_mes.parquet"))
    df = df[["sigla_uf", "ano_mes", *COLUNAS_SECA]]
    return df.rename(columns={c: f"seca_{c}" for c in COLUNAS_SECA})


def prepara_macro() -> pd.DataFrame:
    """Série nacional: junta só por `ano_mes` e se repete em todas as UFs."""
    df = padroniza_chaves(pd.read_parquet(INTERIM / "parquet" / "macro_br_mes.parquet"))
    df = df[["ano_mes", *COLUNAS_MACRO]].astype({c: "float64" for c in COLUNAS_MACRO})
    return df.rename(columns={c: f"macro_{c}" for c in COLUNAS_MACRO})


# ============================================================================
# Passo 4 — a junção
# ============================================================================
def junta() -> pd.DataFrame:
    print("\n[1] Espinha")
    fato = monta_calendario()
    valida_chaves(fato, "calendario_uf_mes")
    PROCESSED.mkdir(parents=True, exist_ok=True)
    fato.to_parquet(PROCESSED / "calendario_uf_mes.parquet", index=False)

    fontes = [
        ("ipca", prepara_ipca(), ["sigla_uf", "ano_mes"], "ipca_var_alimentacao"),
        (
            "clima",
            padroniza_chaves(pd.read_parquet(INTERIM / "clima_uf_mes.parquet")),
            ["sigla_uf", "ano_mes"],
            "clima_chuva_mm_mes",
        ),
        ("safra", prepara_safra(), ["sigla_uf", "ano_mes"], "safra_producao_t_milho"),
        ("seca", prepara_seca(), ["sigla_uf", "ano_mes"], "seca_severidade_media"),
        ("macro", prepara_macro(), ["ano_mes"], "macro_ipca_mm"),
    ]

    print("\n[2] LEFT JOINs")
    for nome, direita, chave, teste in fontes:
        valida_chaves(direita, nome)
        antes = fato
        fato = antes.merge(direita, on=chave, how="left", validate="m:1")
        checa_join(antes, fato, nome, chave, coluna_teste=teste)

    # Alvo 3: o quanto a comida subiu ALÉM da inflação geral. A variação já é um
    # %, então subtrair o IPCA cheio é o análogo correto de "deflacionar" aqui.
    fato["ipca_var_alimentacao_relativa"] = (
        fato["ipca_var_alimentacao"] - fato["macro_ipca_mm"]
    )

    print("\n[3] Filtro final")
    print(f"  grade completa       : {len(fato):,} linhas ({fato.sigla_uf.nunique()} UFs)")
    fato = fato[fato["ipca_var_alimentacao"].notna()].reset_index(drop=True)
    print(f"  com alvo não-nulo    : {len(fato):,} linhas ({fato.sigla_uf.nunique()} UFs)")

    return fato


# ============================================================================
# Dicionário de variáveis
# ============================================================================
def _descreve(coluna: str) -> tuple[str, str, str, str]:
    """(unidade, fonte, granularidade nativa, descrição) de uma coluna."""
    if coluna in ("sigla_uf", "nome_uf", "regiao", "ano_mes", "ano", "mes"):
        rotulos = {
            "sigla_uf": ("—", "chave (UF)", "UF, uma das 16 áreas urbanas do IPCA"),
            "nome_uf": ("—", "descritiva", "nome por extenso da UF"),
            "regiao": ("—", "descritiva", "macrorregião do IBGE"),
            "ano_mes": ("mês", "chave (tempo)", "mês de referência, Period[M]"),
            "ano": ("ano", "derivada", "componente de ano_mes"),
            "mes": ("1-12", "derivada", "componente de ano_mes — útil como sazonal"),
        }
        unidade, granularidade, desc = rotulos[coluna]
        return unidade, "IBGE (dim_uf)", granularidade, desc

    if coluna.startswith("ipca_"):
        if coluna == "ipca_var_alimentacao_acum12":
            return ("%", "IBGE/SIDRA", "UF × mês",
                    "variação acumulada em 12 meses do grupo Alimentação e bebidas, composta")
        if coluna == "ipca_var_alimentacao_relativa":
            return ("p.p.", "IBGE/SIDRA + BCB", "UF × mês",
                    "ipca_var_alimentacao menos o IPCA cheio nacional: o excesso "
                    "da comida sobre a inflação geral")
        medida, slug = coluna.removeprefix("ipca_").split("_", 1)
        cod, (_, nivel) = next((c, v) for c, v in ITENS_IPCA.items() if v[0] == slug)
        if medida == "var":
            return ("%", "IBGE/SIDRA", "UF × mês",
                    f"variação % no mês do {nivel} {cod} ({slug.replace('_', ' ')})")
        return ("% do orçamento", "IBGE/SIDRA", "UF × mês",
                f"peso do {nivel} {cod} na cesta do IPCA da UF — NÃO somar entre colunas")

    if coluna.startswith("clima_"):
        if coluna == "clima_n_estacoes":
            return ("estações", "INMET", "estação × mês",
                    "quantas estações da UF mediram chuva no mês — controle do "
                    "crescimento da rede, não uma medida de clima")
        rotulos = {
            "clima_chuva_mm_mes": ("mm", "acumulado de chuva do mês (mediana entre estações)"),
            "clima_temp_media": ("°C", "temperatura média do mês"),
            "clima_temp_max_media": ("°C", "média das máximas diárias"),
            "clima_temp_min_media": ("°C", "média das mínimas diárias"),
            "clima_umidade_media": ("%", "umidade relativa média"),
            "clima_amplitude_termica_media": ("°C", "média de (máx - mín) diária"),
            "clima_dias_sem_chuva": ("dias", "dias do mês com chuva < 1 mm"),
            "clima_dias_chuva_forte": ("dias", "dias do mês com chuva > 50 mm"),
            "clima_dias_calor_extremo": ("dias", "dias com máxima acima do limiar de calor"),
            "clima_max_dias_secos_seguidos": ("dias", "maior sequência de dias secos do mês"),
        }
        unidade, desc = rotulos[coluna]
        return (unidade, "INMET", "estação × mês", f"{desc}; mediana das estações da UF")

    if coluna.startswith("safra_"):
        produto = coluna.split("_", 2)[2] if coluna.startswith("safra_producao_t_") else None
        if produto is not None:
            return ("toneladas", "IBGE/LSPA", "UF × produto × mês",
                    f"estimativa vigente da safra ANUAL de {produto.replace('_', ' ')} — "
                    "é estoque/previsão, não produção do mês; 0 = a UF não planta")
        produto = coluna.removeprefix("safra_revisao_pct_")
        return ("%", "IBGE/LSPA", "UF × produto × mês",
                f"revisão % da estimativa de {produto.replace('_', ' ')} vs. o mês anterior "
                f"da mesma safra (sinal de choque de oferta); winsorizada em ±{LIMITE_REVISAO:.0f} %; "
                "NaN em todo janeiro por construção")

    if coluna.startswith("seca_"):
        rotulos = {
            "seca_severidade_media": ("0-5", "severidade média sobre a UF inteira; 0 = sem seca"),
            "seca_severidade_media_area_seca": ("1-5", "severidade só dentro da área em seca"),
            "seca_pct_area_S0plus": ("%", "área em seca fraca ou pior (cumulativa)"),
            "seca_pct_area_S1plus": ("%", "área em seca moderada ou pior (cumulativa)"),
            "seca_pct_area_S2plus": ("%", "área em seca grave ou pior — corte usual de dano"),
            "seca_pct_area_S3plus": ("%", "área em seca extrema ou pior (cumulativa)"),
            "seca_pct_area_S4plus": ("%", "área em seca excepcional (cumulativa)"),
            "seca_meses_consecutivos_S2plus": ("meses", "duração da seca grave em curso"),
            "seca_monitorado": ("bool", "a UF estava no programa da ANA naquele mês — "
                                "False significa SEM MEDIÇÃO, não ausência de seca"),
        }
        unidade, desc = rotulos[coluna]
        return unidade, "ANA (Monitor de Secas)", "UF × mês", desc

    rotulos_macro = {
        "macro_ipca_mm": ("%", "IPCA cheio nacional, variação no mês (SGS 433)"),
        "macro_dolar_ptax_medio": ("BRL/USD", "dólar PTAX médio do mês (SGS 1)"),
        "macro_dolar_ptax_fim": ("BRL/USD", "dólar PTAX no fim do mês (SGS 1)"),
        "macro_selic": ("% a.a.", "meta Selic (SGS 432)"),
        "macro_igpm": ("%", "IGP-M no mês (SGS 189)"),
    }
    unidade, desc = rotulos_macro[coluna]
    return (unidade, "BCB/SGS", "Brasil × mês (broadcast: idêntico em todas as UFs)", desc)


# O que significa o vazio em cada família. Vai para o dicionário em TODA coluna
# que tenha algum nulo, não só nas que passam de 40 %: a leitura errada de um
# NaN de seca (34 % das linhas) faz tanto estrago quanto a de um de 52 %.
JUSTIFICATIVAS = {
    "seca": "O Monitor de Secas da ANA cobria só o Nordeste em 2015 e foi se expandindo "
            "até fechar o país em 2023. NaN = a UF não era monitorada, NÃO 'não houve seca'. "
            "Use seca_monitorado como filtro, ou recorte em 2020-01 (90,5 % de cobertura).",
    "safra": "NaN em safra_revisao_pct_* é indefinição, não falta: janeiro não tem mês "
             "anterior dentro da mesma safra, e a UF que não planta o produto não tem "
             "estimativa para revisar. As colunas safra_producao_t_* não têm nulo porque a "
             "ausência estrutural virou 0 tonelada.",
    "clima": "Estação-mês com menos de 70 % de dias válidos foi mascarada antes de agregar "
             "(T-021) — preferimos o vazio a inventar a média de um mês com 5 dias medidos.",
    "ipca": "Os 12 primeiros meses de cada UF não têm acumulado em 12 meses; AC, MA e SE só "
            "entram na amostra do IPCA em 2018-05.",
}


def monta_dicionario(fato: pd.DataFrame) -> pd.DataFrame:
    linhas = []
    for coluna in fato.columns:
        unidade, fonte, granularidade, descricao = _descreve(coluna)
        pct_nulos = float(fato[coluna].isna().mean()) * 100
        obs = JUSTIFICATIVAS.get(coluna.split("_")[0], "") if pct_nulos > 0 else ""
        linhas.append(
            {
                "coluna": coluna,
                "descricao": descricao,
                "unidade": unidade,
                "fonte": fonte,
                "granularidade_nativa": granularidade,
                "pct_nulos": round(pct_nulos, 2),
                "observacao": obs,
            }
        )
    return pd.DataFrame(linhas)


def main() -> None:
    fato = junta()

    print("\n[4] Validações")
    assert fato.duplicated(["sigla_uf", "ano_mes"]).sum() == 0, "chave duplicada"
    assert isinstance(fato["ano_mes"].dtype, pd.PeriodDtype), "ano_mes não é Period[M]"
    n_neg = int((fato["ipca_var_alimentacao"] < 0).sum())
    assert n_neg > 0, "nenhuma deflação no alvo — o bug do sinal do IPCA voltou"
    print(f"  chave única, ano_mes Period[M], {n_neg:,} meses de deflação no alvo")
    print(
        f"  {len(fato):,} linhas | {fato.sigla_uf.nunique()} UFs | "
        f"{fato.ano_mes.nunique()} meses | {fato.shape[1]} colunas"
    )

    PROCESSED.mkdir(parents=True, exist_ok=True)
    OUT_TABELAS.mkdir(parents=True, exist_ok=True)
    destino = PROCESSED / "fato_alimentos_uf_mes.parquet"
    fato.to_parquet(destino, index=False)

    dic = monta_dicionario(fato)
    dic.to_csv(OUT_TABELAS / "dicionario_variaveis.csv", index=False, encoding="utf-8")

    sem_justificativa = dic[(dic.pct_nulos > 40) & (dic.observacao == "")]
    assert sem_justificativa.empty, f"colunas > 40 % nulas sem justificativa:\n{sem_justificativa}"

    print(f"\n[ok] {destino.relative_to(RAIZ)}")
    print(f"[ok] outputs/tabelas/dicionario_variaveis.csv — {len(dic)} colunas documentadas")


if __name__ == "__main__":
    main()
