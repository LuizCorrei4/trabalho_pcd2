"""T-012 — Coletor SIDRA/LSPA: estimativas de safra por UF.

Baixa da API SIDRA (IBGE, sem chave):

  * tabela 6588 (LSPA) — estimativa da safra do ano corrente, revista *mensalmente*,
    por UF e produto. É daqui que sai o sinal de choque de oferta (`revisao_pct_prod`).
  * tabelas 1612 (lavouras temporárias) e 1613 (lavouras permanentes) da PAM —
    produção anual realizada por UF, usada para os pesos de produção do T-022.

Saídas:
  data/interim/safra_uf_mes.parquet     (longo: sigla_uf x produto x ano_mes)
  data/interim/producao_uf_ano.parquet  (longo: sigla_uf x produto x ano)
  data/raw/sidra/*.parquet              (retorno bruto, para auditoria)
  data/interim/qa_T-012_sidra.md        (relatório dos critérios de aceite)

Uso:
    python src/coleta/03_sidra_lspa.py                  # tudo, 2014 -> hoje
    python src/coleta/03_sidra_lspa.py --inicio 2010
    python src/coleta/03_sidra_lspa.py --apenas lspa

ATENÇÃO (armadilha da 6588): cada mês é uma *fotografia da expectativa* para a safra
daquele ano, não a produção do mês. Nunca somar os 12 meses.
"""

from __future__ import annotations

import argparse
import sys
import time
import unicodedata
from datetime import date
from pathlib import Path

import pandas as pd
import requests

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

from src.tratamento.chaves import carrega_dim_uf as _le_dim_uf  # noqa: E402

DIR_RAW = RAIZ / "data" / "raw" / "sidra"
DIR_INTERIM = RAIZ / "data" / "interim"
CAMINHO_DIM_UF = RAIZ / "data" / "processed" / "dim_uf.csv"

URL_VALORES = "https://apisidra.ibge.gov.br/values"
URL_METADADOS = "https://servicodados.ibge.gov.br/api/v3/agregados/{tabela}/metadados"
URL_ESTADOS = "https://servicodados.ibge.gov.br/api/v1/localidades/estados"

# n1=Brasil, n2=Grande Região, n3=UF, n6=Município
NIVEIS = {"BR": "n1", "REGIAO": "n2", "UF": "n3", "MUNICIPIO": "n6"}

# Marcadores de dado ausente/não divulgado da SIDRA. Sem isso a coluna vira object.
AUSENTES = {"...", "..", ".", "-", "x", "X", "..-", ""}

PAUSA_S = 0.4  # cortesia com a API entre requisições

# --------------------------------------------------------------------------- #
# Produtos                                                                     #
# --------------------------------------------------------------------------- #
# Nome canônico -> categorias da SIDRA. Quando há mais de uma (safras), as áreas e
# a produção são somadas e o rendimento é recalculado (média ponderada real).

PRODUTOS_LSPA = {  # tabela 6588, classificação C48
    "arroz": ["39432"],
    "feijao": ["39436", "39437", "39438"],          # 1ª, 2ª e 3ª safra
    # A categoria "9/10 Café total" (40527) existe nos metadados mas volta "-" na 6588;
    # o café só é publicado desagregado, então somamos arábica + canephora.
    "cafe": ["39454", "39455"],
    "banana": ["39449"],
    "batata_inglesa": ["39450", "39451", "39452"],
    "tomate": ["39470"],
    "trigo": ["39445"],
    "mandioca": ["39467"],
    "cana_de_acucar": ["39456"],
    "soja": ["39443"],
    "milho": ["39441", "39442"],                     # 1ª e 2ª safra
}

PRODUTOS_PAM_TEMPORARIAS = {  # tabela 1612, classificação C81
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

PRODUTOS_PAM_PERMANENTES = {  # tabela 1613, classificação C82 (café e banana são permanentes!)
    "cafe": ["2723"],
    "banana": ["2720"],
}

# Variáveis por tabela -> nome legível de saída
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
    "2313": "area_plantada_ha",  # "área destinada à colheita" nas permanentes
    "216": "area_colhida_ha",
    "214": "producao_t",
    "112": "rendimento_kg_ha",
    "215": "valor_producao_mil_brl",
}


def log(msg: str) -> None:
    print(f"[T-012] {msg}", flush=True)


def normaliza_texto(s: str) -> str:
    """minúscula, sem acento, sem espaço nas pontas."""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode("ascii")
    return s.lower().strip()


def _slug(rotulo: str) -> str:
    """'Unidade da Federação (Código)' -> 'unidade_da_federacao_codigo'."""
    s = normaliza_texto(rotulo).replace("(", " ").replace(")", " ")
    return "_".join(s.split())


def _para_numero(serie: pd.Series) -> pd.Series:
    """Converte a coluna de valores da SIDRA para float, tratando os marcadores."""
    limpa = serie.astype("string").str.strip()
    limpa = limpa.mask(limpa.isin(AUSENTES))
    return pd.to_numeric(limpa, errors="coerce")


# --------------------------------------------------------------------------- #
# Acesso à API                                                                 #
# --------------------------------------------------------------------------- #
def periodo_final(tabela: str, padrao: str) -> str:
    """Último período publicado da tabela, direto dos metadados."""
    try:
        r = requests.get(URL_METADADOS.format(tabela=tabela), timeout=60)
        r.raise_for_status()
        return str(r.json()["periodicidade"]["fim"])
    except Exception as e:  # rede fora do ar / mudança de contrato: cai no padrão
        log(f"aviso: não obtive metadados da tabela {tabela} ({e}); usando fim={padrao}")
        return padrao


def busca_tabela(
    tabela: str,
    variaveis: list[str],
    periodos: str,
    nivel: str = "UF",
    classificacao: str | None = None,
    categorias: list[str] | None = None,
    tentativas: int = 4,
) -> pd.DataFrame:
    """Consulta /values da SIDRA e devolve um DataFrame longo com nomes legíveis.

    Args:
        tabela: código do agregado, ex. "6588".
        variaveis: códigos de variável, ex. ["35", "36"].
        periodos: string de período da SIDRA, ex. "201401-202412" ou "2014-2024".
        nivel: "BR", "REGIAO", "UF" ou "MUNICIPIO".
        classificacao: código da classificação, ex. "48" (produto das lavouras).
        categorias: códigos das categorias dentro da classificação.

    Devolve uma linha por (localidade, período, categoria, variável) com a coluna
    `valor` já numérica — marcadores de ausência viram NaN.
    """
    if nivel not in NIVEIS:
        raise ValueError(f"nível inválido: {nivel!r}; use um de {sorted(NIVEIS)}")

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

    for tentativa in range(1, tentativas + 1):
        try:
            r = requests.get(url, params={"formato": "json"}, timeout=180)
            r.raise_for_status()
            dados = r.json()
        except Exception as e:
            if tentativa == tentativas:
                raise RuntimeError(f"falha ao consultar {url}: {e}") from e
            espera = 2**tentativa
            log(f"  tentativa {tentativa} falhou ({e}); repetindo em {espera}s")
            time.sleep(espera)
            continue

        # A SIDRA devolve o cabeçalho legível como primeiro elemento da lista.
        if not isinstance(dados, list) or len(dados) < 2:
            return pd.DataFrame()

        cabecalho, corpo = dados[0], dados[1:]
        df = pd.DataFrame(corpo).rename(columns={k: _slug(v) for k, v in cabecalho.items()})
        df["valor"] = _para_numero(df.pop("valor"))
        time.sleep(PAUSA_S)
        return df

    return pd.DataFrame()


def salva(df: pd.DataFrame, nome: str) -> None:
    """Grava parquet (tipos preservados) + csv (legível/versionável no git)."""
    caminho_pq = DIR_INTERIM / f"{nome}.parquet"
    caminho_csv = DIR_INTERIM / f"{nome}.csv"
    df.to_parquet(caminho_pq, index=False)
    df.to_csv(caminho_csv, index=False, encoding="utf-8")
    mb = caminho_csv.stat().st_size / 1e6
    log(f"→ {caminho_pq.relative_to(RAIZ)} + {nome}.csv ({len(df):,} linhas, csv {mb:.1f} MB)")


def blocos_de_periodo(inicio: int, fim: int, passo: int = 4) -> list[tuple[int, int]]:
    """Quebra o intervalo de anos em blocos — requisição gigante volta erro obscuro."""
    return [(a, min(a + passo - 1, fim)) for a in range(inicio, fim + 1, passo)]


# --------------------------------------------------------------------------- #
# dim_uf (T-002)                                                               #
# --------------------------------------------------------------------------- #
def carrega_dim_uf() -> tuple[pd.DataFrame, bool]:
    """Devolve (dim_uf mínimo, veio_do_arquivo).

    Usa `data/processed/dim_uf.csv` quando o T-002 já foi entregue; senão monta um
    substituto com a API de localidades do IBGE para não travar a coleta.
    """
    if CAMINHO_DIM_UF.exists():
        dim = _le_dim_uf()
        return dim[["cod_ibge_uf", "sigla_uf", "nome_uf"]].astype({"sigla_uf": str, "nome_uf": str}), True

    log(f"aviso: {CAMINHO_DIM_UF.relative_to(RAIZ)} não existe (T-002 pendente).")
    log("       usando a API de localidades do IBGE como substituto temporário.")
    r = requests.get(URL_ESTADOS, timeout=60)
    r.raise_for_status()
    dim = pd.DataFrame(
        [{"cod_ibge_uf": int(e["id"]), "sigla_uf": e["sigla"], "nome_uf": e["nome"]} for e in r.json()]
    )
    return dim.sort_values("cod_ibge_uf").reset_index(drop=True), False


def aplica_dim_uf(df: pd.DataFrame, dim_uf: pd.DataFrame, col_codigo: str) -> pd.DataFrame:
    """Traduz código IBGE de UF -> sigla_uf. Aborta se aparecer código órfão."""
    df = df.copy()
    df["cod_ibge_uf"] = pd.to_numeric(df.pop(col_codigo), errors="coerce").astype("Int64")

    orfaos = sorted(set(df["cod_ibge_uf"].dropna().astype(int)) - set(dim_uf["cod_ibge_uf"]))
    if orfaos:
        raise ValueError(f"códigos de UF sem correspondência em dim_uf: {orfaos}")

    return df.merge(dim_uf, on="cod_ibge_uf", how="left", validate="many_to_one")


# --------------------------------------------------------------------------- #
# Montagem dos produtos                                                        #
# --------------------------------------------------------------------------- #
def _empilha_produtos(
    tabela: str,
    classificacao: str,
    produtos: dict[str, list[str]],
    variaveis: dict[str, str],
    periodos: str,
    nivel: str,
) -> pd.DataFrame:
    """Baixa produto a produto (limite de volume por requisição) e empilha."""
    pedacos = []
    for canonico, categorias in produtos.items():
        bruto = busca_tabela(
            tabela=tabela,
            variaveis=list(variaveis),
            periodos=periodos,
            nivel=nivel,
            classificacao=classificacao,
            categorias=categorias,
        )
        if bruto.empty:
            log(f"  ! {tabela}/{canonico}: retorno vazio")
            continue
        bruto["produto"] = canonico
        pedacos.append(bruto)
        log(f"  {tabela}/{canonico}: {len(bruto):,} linhas")
    if not pedacos:
        raise RuntimeError(f"tabela {tabela}: nenhum produto retornou dados")
    return pd.concat(pedacos, ignore_index=True)


def _identifica_colunas(df: pd.DataFrame) -> tuple[str, str, str, str]:
    """Localiza as colunas de código de localidade, período, variável e categoria."""
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
    """Uma coluna por variável (área, produção, rendimento…), mantendo o formato longo
    em produto — o pivot de produto é do T-024."""
    df = df.copy()
    df["variavel"] = df[col_variavel].astype(str).map(variaveis)
    df = df.dropna(subset=["variavel"])
    # groupby+unstack em vez de pivot_table: `sum(min_count=1)` mantém NaN onde não há
    # nenhum dado. pivot_table somaria NaN para 0 e criaria buracos silenciosos.
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
    """Soma as safras de um mesmo produto (feijão 1ª/2ª/3ª, milho 1ª/2ª…).

    Rendimento não pode ser somado: é recalculado como produção/área colhida.
    """
    colunas_soma = [
        c
        for c in ("area_plantada_ha", "area_colhida_ha", "producao_t", "valor_producao_mil_brl")
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
    # produto com uma única categoria: mantém o rendimento publicado pelo IBGE
    agregado["rendimento_kg_ha"] = calculado.where(
        agregado["n_categorias"] > 1, agregado["rendimento_reportado"]
    ).fillna(calculado)
    return agregado.drop(columns=["n_categorias", "rendimento_reportado"])


# --------------------------------------------------------------------------- #
# LSPA 6588                                                                    #
# --------------------------------------------------------------------------- #
def coleta_lspa(inicio: int, fim_periodo: str, dim_uf: pd.DataFrame, nivel: str = "UF") -> pd.DataFrame:
    ano_fim = int(fim_periodo[:4])
    partes = []
    for a1, a2 in blocos_de_periodo(inicio, ano_fim):
        p_ini = f"{a1}01"
        p_fim = fim_periodo if a2 == ano_fim else f"{a2}12"
        log(f"LSPA 6588 [{nivel}] período {p_ini}-{p_fim}")
        partes.append(
            _empilha_produtos("6588", "48", PRODUTOS_LSPA, VARIAVEIS_LSPA, f"{p_ini}-{p_fim}", nivel)
        )
    bruto = pd.concat(partes, ignore_index=True)

    if nivel == "UF":
        DIR_RAW.mkdir(parents=True, exist_ok=True)
        bruto.to_parquet(DIR_RAW / "lspa_6588_bruto.parquet", index=False)

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

    # Revisão mês a mês DENTRO da mesma safra: dezembro/2015 e janeiro/2016 falam de
    # anos-safra diferentes, então a variação entre eles não é revisão de estimativa.
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
    return df[colunas].reset_index(drop=True)


# --------------------------------------------------------------------------- #
# PAM 1612 / 1613                                                              #
# --------------------------------------------------------------------------- #
def coleta_pam(inicio: int, fim: int, dim_uf: pd.DataFrame) -> pd.DataFrame:
    especificacoes = [
        ("1612", "81", PRODUTOS_PAM_TEMPORARIAS, VARIAVEIS_PAM_TEMP, "temporaria"),
        ("1613", "82", PRODUTOS_PAM_PERMANENTES, VARIAVEIS_PAM_PERM, "permanente"),
    ]
    partes = []
    for tabela, classif, produtos, variaveis, lavoura in especificacoes:
        log(f"PAM {tabela} ({lavoura}) período {inicio}-{fim}")
        bruto = _empilha_produtos(tabela, classif, produtos, variaveis, f"{inicio}-{fim}", "UF")
        DIR_RAW.mkdir(parents=True, exist_ok=True)
        bruto.to_parquet(DIR_RAW / f"pam_{tabela}_bruto.parquet", index=False)

        col_local, col_periodo, col_variavel, col_categoria = _identifica_colunas(bruto)
        bruto["ano"] = pd.to_numeric(bruto[col_periodo], errors="coerce").astype("Int64")

        largo = _pivota_variaveis(
            bruto, variaveis, [col_local, "ano", "produto", col_categoria], col_variavel
        )
        df = _agrega_safras(largo, [col_local, "ano", "produto"])
        df = aplica_dim_uf(df, dim_uf, col_local)
        df["lavoura"] = lavoura
        partes.append(df)

    df = pd.concat(partes, ignore_index=True)

    # Peso da UF na produção nacional do produto naquele ano (insumo do T-022).
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
    return df[colunas].sort_values(["produto", "ano", "sigla_uf"]).reset_index(drop=True)


# --------------------------------------------------------------------------- #
# Critérios de aceite                                                          #
# --------------------------------------------------------------------------- #
def valida(
    safra: pd.DataFrame,
    brasil: pd.DataFrame | None,
    pam: pd.DataFrame | None,
    dim_uf: pd.DataFrame,
    inicio: int,
) -> str:
    linhas: list[str] = ["# QA — T-012 SIDRA/LSPA", "", f"Gerado em {date.today().isoformat()}.", ""]

    def ok(condicao: bool) -> str:
        return "✅" if condicao else "❌"

    # 1. 11 produtos, >= 1 UF cada
    por_produto = safra.dropna(subset=["producao_t"]).groupby("produto")["sigla_uf"].nunique()
    faltando = sorted(set(PRODUTOS_LSPA) - set(por_produto.index))
    linhas += [
        f"{ok(not faltando and (por_produto >= 1).all())} **Produtos**: "
        f"{len(por_produto)}/{len(PRODUTOS_LSPA)} presentes, mínimo de "
        f"{int(por_produto.min())} UF por produto (faltando: {faltando or 'nenhum'})",
    ]

    # 2. cobertura mensal contínua
    meses = pd.PeriodIndex(safra["ano_mes"].dt.to_period("M").unique(), freq="M").sort_values()
    esperados = pd.period_range(f"{inicio}-01", meses.max(), freq="M")
    buracos = sorted(set(esperados) - set(meses))
    linhas += [
        f"{ok(not buracos)} **Cobertura mensal**: {meses.min()} → {meses.max()} "
        f"({len(meses)} meses; buracos: {[str(b) for b in buracos] or 'nenhum'})",
    ]

    # 3. sigla_uf x dim_uf
    orfaos = sorted(set(safra["sigla_uf"].dropna()) - set(dim_uf["sigla_uf"]))
    linhas += [
        f"{ok(not orfaos and safra['sigla_uf'].notna().all())} **Chave geográfica**: "
        f"{safra['sigla_uf'].nunique()} UFs, nulos={int(safra['sigla_uf'].isna().sum())}, "
        f"órfãos={orfaos or 'nenhum'}",
    ]

    # 4. soma das UFs ≈ Brasil
    if brasil is not None and not brasil.empty:
        soma_uf = safra.groupby(["produto", "ano_mes"], as_index=False)["producao_t"].sum(min_count=1)
        comp = soma_uf.merge(
            brasil[["produto", "ano_mes", "producao_t"]].rename(columns={"producao_t": "producao_br"}),
            on=["produto", "ano_mes"],
            how="inner",
        ).dropna()
        comp["dif_pct"] = (comp["producao_t"] - comp["producao_br"]).abs() / comp["producao_br"] * 100
        dentro = (comp["dif_pct"] <= 1).mean() * 100
        linhas += [
            f"{ok(dentro >= 99)} **Soma UF vs. Brasil**: {dentro:.2f}% dos pares "
            f"(produto × mês) com diferença ≤ 1% (máx. {comp['dif_pct'].max():.3f}%, n={len(comp):,})",
        ]
    else:
        linhas += ["⚠️ **Soma UF vs. Brasil**: não verificado (nível BR não coletado)"]

    # 5. plausibilidade da revisão
    rev = safra["revisao_pct_prod"].dropna()
    dentro_faixa = ((rev >= -20) & (rev <= 20)).mean() * 100
    linhas += [
        f"{ok(dentro_faixa >= 50)} **revisao_pct_prod**: {dentro_faixa:.1f}% entre -20% e +20% "
        f"(mediana {rev.median():.2f}%, p05 {rev.quantile(.05):.1f}%, p95 {rev.quantile(.95):.1f}%, "
        f"n={len(rev):,})",
    ]

    linhas += ["", "## Volumes", "", f"- `safra_uf_mes`: {len(safra):,} linhas"]
    if pam is not None:
        anos = f"{int(pam['ano'].min())}–{int(pam['ano'].max())}"
        linhas += [
            f"- `producao_uf_ano`: {len(pam):,} linhas, {anos}, "
            f"{pam['produto'].nunique()} produtos",
        ]

    linhas += ["", "## Produção estimada por produto (último mês)", ""]
    ultimo = safra[safra["ano_mes"] == safra["ano_mes"].max()]
    tot = ultimo.groupby("produto")["producao_t"].sum().sort_values(ascending=False)
    linhas += ["| produto | produção (t) | UFs |", "|---|---:|---:|"]
    for prod, valor in tot.items():
        n_uf = int(ultimo.loc[ultimo["produto"] == prod, "producao_t"].notna().sum())
        linhas.append(f"| {prod} | {valor:,.0f} | {n_uf} |")

    return "\n".join(linhas) + "\n"


# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="T-012 — coletor SIDRA/LSPA")
    p.add_argument("--inicio", type=int, default=2014, help="primeiro ano (padrão 2014)")
    p.add_argument("--fim", type=str, default=None, help="último período: AAAAMM (LSPA)")
    p.add_argument(
        "--apenas", choices=["lspa", "pam"], default=None, help="rodar só uma das coletas"
    )
    args = p.parse_args(argv)

    DIR_INTERIM.mkdir(parents=True, exist_ok=True)
    (DIR_INTERIM / ".gitkeep").touch()

    dim_uf, do_arquivo = carrega_dim_uf()
    log(f"dim_uf: {len(dim_uf)} UFs ({'data/processed/dim_uf.csv' if do_arquivo else 'API IBGE'})")

    safra = brasil = pam = None

    if args.apenas != "pam":
        fim = args.fim or periodo_final("6588", f"{date.today():%Y%m}")
        safra = coleta_lspa(args.inicio, fim, dim_uf, nivel="UF")
        brasil = coleta_lspa(args.inicio, fim, dim_uf, nivel="BR")
        salva(safra, "safra_uf_mes")

    if args.apenas != "lspa":
        fim_pam = int(periodo_final("1612", str(date.today().year - 1))[:4])
        pam = coleta_pam(args.inicio, fim_pam, dim_uf)
        salva(pam, "producao_uf_ano")

    if safra is not None:
        relatorio = valida(safra, brasil, pam, dim_uf, args.inicio)
        (DIR_INTERIM / "qa_T-012_sidra.md").write_text(relatorio, encoding="utf-8")
        print("\n" + relatorio)

    return 0


if __name__ == "__main__":
    sys.exit(main())
