"""T-002 / T-020 — Chaves canônicas do projeto: `sigla_uf` e `ano_mes`.

Toda junção geográfica deve passar por `sigla_uf`, nunca por nome de cidade direto.
Este módulo é o único lugar onde nome de lugar vira chave.

    from src.tratamento.chaves import normaliza_nome, mapear_para_uf

    df["sigla_uf"] = mapear_para_uf(df["capital"])

O T-020 acrescentou o contrato temporal. As quatro tabelas de `data/interim/`
chegam com três tipos diferentes de `ano_mes` (str "YYYY-MM", datetime64 e
Period), e um merge entre str e Timestamp **não levanta erro** — devolve tudo
NaN em silêncio. `padroniza_chaves` converge os três para `Period[M]`,
`valida_chaves` recusa o que não cumprir o contrato e `checa_join` mede a taxa
de match depois de cada merge.
"""

from __future__ import annotations

import unicodedata
from functools import lru_cache
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
CAMINHO_DIM_UF = RAIZ / "data" / "processed" / "dim_uf.csv"

# Tipos fixos na leitura: sem isso o pandas lê cod_ibge_uf como int mas
# um CSV com "07" viraria string — e o merge com a SIDRA falha silenciosamente.
DTYPES_DIM_UF = {
    "sigla_uf": "string",
    "nome_uf": "string",
    "capital": "string",
    "capital_norm": "string",
    "cod_ibge_uf": int,
    "cod_ibge_capital": int,
    "regiao": "string",
}

# Formas que as fontes usam e que não saem de dim_uf sozinhas.
# O DIEESE escreve "Brasília"; o IBGE, "Distrito Federal".
APELIDOS = {
    "distrito federal": "DF",
    "brasilia df": "DF",
    "df": "DF",
    "rio de janeiro rj": "RJ",
    "sao paulo sp": "SP",
    "florianopolis sc": "SC",
    "vitoria es": "ES",
}


def normaliza_nome(s: str) -> str:
    """Minúscula, sem acento, sem pontuação, espaços colapsados.

    >>> normaliza_nome("SÃO PAULO")
    'sao paulo'
    >>> normaliza_nome(" Brasília/DF ")
    'brasilia df'
    """
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    texto = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode("ascii")
    texto = "".join(c if c.isalnum() else " " for c in texto.lower())
    return " ".join(texto.split())


@lru_cache(maxsize=1)
def carrega_dim_uf(caminho: str | None = None) -> pd.DataFrame:
    """Lê `data/processed/dim_uf.csv` com os tipos fixos."""
    alvo = Path(caminho) if caminho else CAMINHO_DIM_UF
    if not alvo.exists():
        raise FileNotFoundError(
            f"{alvo} não existe. Rode `python src/tratamento/00_dim_uf.py` (T-002) antes."
        )
    return pd.read_csv(alvo, dtype=DTYPES_DIM_UF, encoding="utf-8")


@lru_cache(maxsize=1)
def _tabela_busca() -> dict[str, str]:
    """nome normalizado -> sigla_uf, cobrindo capital, nome da UF e a própria sigla."""
    dim = carrega_dim_uf()
    busca: dict[str, str] = {}
    for _, linha in dim.iterrows():
        sigla = str(linha["sigla_uf"])
        for chave in (linha["capital"], linha["nome_uf"], sigla):
            busca[normaliza_nome(chave)] = sigla
    busca.update(APELIDOS)
    return busca


def mapear_para_uf(nomes: pd.Series) -> pd.Series:
    """Nome de cidade/UF -> `sigla_uf`. Devolve <NA> no que não reconhecer.

    Aceita acento, sem acento e CAIXA ALTA, e tolera sufixo de UF colado
    ("Belém/PA", "Belo Horizonte - MG").
    """
    busca = _tabela_busca()
    normalizados = pd.Series(nomes, dtype="object").map(normaliza_nome)

    resultado = normalizados.map(busca)

    # 2ª passada: tira um sufixo de 2 letras que seja sigla de UF ("belem pa")
    siglas = set(carrega_dim_uf()["sigla_uf"].str.lower())
    faltantes = resultado.isna()
    if faltantes.any():
        sem_sufixo = normalizados[faltantes].map(
            lambda s: " ".join(s.split()[:-1]) if s.split() and s.split()[-1] in siglas else s
        )
        resultado.loc[faltantes] = sem_sufixo.map(busca)

    return pd.Series(resultado, index=pd.Series(nomes).index, dtype="string").rename("sigla_uf")


# ------------------------------------------------------- contrato de chaves ---
def padroniza_chaves(df: pd.DataFrame) -> pd.DataFrame:
    """`sigla_uf` -> str de 2 maiúsculas; `ano_mes` -> `pd.Period[M]`.

    Aceita as três formas que chegam de `data/interim/`: str "YYYY-MM" (ipca,
    seca, clima), datetime64 (safra, macro) e Period. Devolve uma cópia — não
    altera o df de entrada.

    >>> padroniza_chaves(pd.DataFrame({"ano_mes": ["2015-01"]}))["ano_mes"][0]
    Period('2015-01', 'M')
    """
    out = df.copy()

    if "sigla_uf" in out.columns:
        out["sigla_uf"] = out["sigla_uf"].astype("string").str.strip().str.upper()

    if "ano_mes" in out.columns:
        col = out["ano_mes"]
        if isinstance(col.dtype, pd.PeriodDtype):
            out["ano_mes"] = col.dt.asfreq("M")
        elif pd.api.types.is_datetime64_any_dtype(col):
            out["ano_mes"] = col.dt.to_period("M")
        else:
            out["ano_mes"] = pd.PeriodIndex(col.astype(str).str.strip(), freq="M")

    return out


def valida_chaves(df: pd.DataFrame, nome: str, *, unica: bool = True) -> None:
    """Levanta `ValueError` se `sigla_uf`/`ano_mes` violarem o contrato.

    `unica=False` para tabelas cujo grão nativo é mais fino que UF × mês
    (safra em formato longo, clima por estação) — ali a duplicata é esperada.
    """
    faltando = [c for c in ("sigla_uf", "ano_mes") if c not in df.columns]
    if faltando and faltando != ["sigla_uf"]:  # macro é nacional: só tem ano_mes
        raise ValueError(f"[{nome}] faltam colunas de chave: {faltando}")

    if "ano_mes" in df.columns and not isinstance(df["ano_mes"].dtype, pd.PeriodDtype):
        raise ValueError(f"[{nome}] ano_mes é {df['ano_mes'].dtype}, esperado Period[M]")

    if "sigla_uf" in df.columns:
        sigla = df["sigla_uf"].astype("string")
        if sigla.isna().any():
            raise ValueError(f"[{nome}] {int(sigla.isna().sum())} linhas com sigla_uf nula")
        ruins = sigla[~sigla.str.fullmatch(r"[A-Z]{2}")].unique()
        if len(ruins):
            raise ValueError(f"[{nome}] sigla_uf fora do padrão de 2 maiúsculas: {list(ruins)[:5]}")

    if unica:
        chave = [c for c in ("sigla_uf", "ano_mes") if c in df.columns]
        n_dup = int(df.duplicated(chave).sum())
        if n_dup:
            raise ValueError(f"[{nome}] chave {chave} duplica em {n_dup:,} linhas")

    print(f"  [ok] {nome}: {len(df):,} linhas, chave válida")


def checa_join(
    antes: pd.DataFrame,
    depois: pd.DataFrame,
    nome: str,
    chave: list[str],
    *,
    coluna_teste: str | None = None,
) -> None:
    """Loga linhas antes/depois e a taxa de match; alerta se o nº de linhas mudou.

    Um LEFT JOIN correto preserva a contagem de linhas da esquerda. Se cresceu,
    o lado direito tinha a chave duplicada (o fan-out ×11 da safra não pivotada);
    se encolheu, alguém usou INNER sem querer. Taxa de match 0 % com chave
    aparentemente certa é o sintoma do merge entre `str` e `Timestamp`.
    """
    if coluna_teste is None:
        novas = [c for c in depois.columns if c not in antes.columns]
        coluna_teste = novas[0] if novas else depois.columns[-1]

    taxa = float(depois[coluna_teste].notna().mean()) * 100
    print(
        f"  [join] {nome:<22} on {'+'.join(chave):<20} "
        f"{len(antes):>6,} -> {len(depois):>6,} linhas | match {taxa:5.1f}% ({coluna_teste})"
    )

    if len(depois) > len(antes):
        raise ValueError(
            f"[{nome}] o merge inflou {len(antes):,} -> {len(depois):,} linhas: "
            f"a tabela da direita duplica {chave}. Pivote antes de juntar."
        )
    if len(depois) < len(antes):
        raise ValueError(
            f"[{nome}] o merge perdeu linhas ({len(antes):,} -> {len(depois):,}). "
            "A espinha tem de ser preservada — use how='left'."
        )
    if taxa == 0:
        raise ValueError(
            f"[{nome}] taxa de match 0 %: as chaves não se encontraram. "
            "Confira se ano_mes é Period[M] dos dois lados."
        )
