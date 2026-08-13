"""T-002 — Chaves geográficas canônicas do projeto.

Toda junção geográfica deve passar por `sigla_uf`, nunca por nome de cidade direto.
Este módulo é o único lugar onde nome de lugar vira chave.

    from src.tratamento.chaves import normaliza_nome, mapear_para_uf

    df["sigla_uf"] = mapear_para_uf(df["capital"])
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
