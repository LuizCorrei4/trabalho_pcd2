"""T-002 — Constrói `data/processed/dim_uf.csv`, a tabela-dimensão canônica das UFs.

Cada fonte do projeto identifica o mesmo lugar de um jeito diferente (o DIEESE escreve
"Belém", o SIDRA usa o código IBGE 15, a CONAB usa "PA"). Esta tabela amarra tudo em
`sigla_uf`, que é a única chave geográfica que as junções podem usar.

Sigla, nome e região vêm da API de localidades do IBGE; o código IBGE da capital é
resolvido contra a lista de municípios da própria UF. As coordenadas da sede são
constantes (são 27 pares), mas cada uma é validada contra o bounding box da malha
municipal do IBGE — isso pega dígito trocado.

Uso:
    python src/tratamento/00_dim_uf.py
    python src/tratamento/00_dim_uf.py --sem-validar-malha   # offline/rápido
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import requests

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

from src.tratamento.chaves import normaliza_nome  # noqa: E402

DESTINO = RAIZ / "data" / "processed" / "dim_uf.csv"

URL_ESTADOS = "https://servicodados.ibge.gov.br/api/v1/localidades/estados"
URL_MUNICIPIOS = "https://servicodados.ibge.gov.br/api/v1/localidades/estados/{uf}/municipios"
URL_MALHA = (
    "https://servicodados.ibge.gov.br/api/v3/malhas/municipios/{cod}"
    "?formato=application/vnd.geo+json&qualidade=minima"
)

# sigla -> (capital, lat, lon) da sede municipal.
CAPITAIS = {
    "AC": ("Rio Branco", -9.9754, -67.8249),
    "AL": ("Maceió", -9.6658, -35.7353),
    "AP": ("Macapá", 0.0389, -51.0664),
    "AM": ("Manaus", -3.1190, -60.0217),
    "BA": ("Salvador", -12.9777, -38.5016),
    "CE": ("Fortaleza", -3.7319, -38.5267),
    "DF": ("Brasília", -15.7939, -47.8828),
    "ES": ("Vitória", -20.3155, -40.3128),
    "GO": ("Goiânia", -16.6869, -49.2648),
    "MA": ("São Luís", -2.5387, -44.2825),
    "MT": ("Cuiabá", -15.6014, -56.0979),
    "MS": ("Campo Grande", -20.4697, -54.6201),
    "MG": ("Belo Horizonte", -19.9167, -43.9345),
    "PA": ("Belém", -1.4558, -48.5039),
    "PB": ("João Pessoa", -7.1195, -34.8450),
    "PR": ("Curitiba", -25.4284, -49.2733),
    "PE": ("Recife", -8.0476, -34.8770),
    "PI": ("Teresina", -5.0892, -42.8019),
    "RJ": ("Rio de Janeiro", -22.9068, -43.1729),
    "RN": ("Natal", -5.7945, -35.2110),
    "RS": ("Porto Alegre", -30.0346, -51.2177),
    "RO": ("Porto Velho", -8.7612, -63.9004),
    "RR": ("Boa Vista", 2.8235, -60.6758),
    "SC": ("Florianópolis", -27.5954, -48.5480),
    "SP": ("São Paulo", -23.5505, -46.6333),
    "SE": ("Aracaju", -10.9472, -37.0731),
    "TO": ("Palmas", -10.1689, -48.3317),
}

# As 17 capitais da série longa da Pesquisa Nacional da Cesta Básica do DIEESE.
# Conferido na Tabela 1 do relatório de março/2025 ("Custo e variação da cesta
# básica em 17 capitais"). A pesquisa só passou a cobrir as 27 em agosto/2025.
UFS_DIEESE = {
    "SP", "RJ", "SC", "RS", "MS", "DF", "PR", "ES", "GO",
    "MG", "CE", "PA", "RN", "BA", "PE", "PB", "SE",
}


def log(msg: str) -> None:
    print(f"[T-002] {msg}", flush=True)


def busca_estados() -> pd.DataFrame:
    r = requests.get(URL_ESTADOS, timeout=60)
    r.raise_for_status()
    return pd.DataFrame(
        [
            {
                "sigla_uf": e["sigla"],
                "nome_uf": e["nome"],
                "cod_ibge_uf": int(e["id"]),
                "regiao": e["regiao"]["nome"],
            }
            for e in r.json()
        ]
    )


def busca_cod_capital(sigla: str, capital: str) -> int:
    """Resolve o código IBGE de 7 dígitos da capital na lista de municípios da UF."""
    r = requests.get(URL_MUNICIPIOS.format(uf=sigla), timeout=60)
    r.raise_for_status()
    alvo = normaliza_nome(capital)
    for m in r.json():
        if normaliza_nome(m["nome"]) == alvo:
            return int(m["id"])
    raise ValueError(f"capital {capital!r} não encontrada entre os municípios de {sigla}")


def bbox_municipio(cod: int) -> tuple[float, float, float, float]:
    """(lon_min, lon_max, lat_min, lat_max) da malha municipal."""
    r = requests.get(URL_MALHA.format(cod=cod), timeout=90)
    r.raise_for_status()

    def pontos(obj):
        if isinstance(obj[0], (int, float)):
            yield obj
        else:
            for item in obj:
                yield from pontos(item)

    coords = list(pontos(r.json()["features"][0]["geometry"]["coordinates"]))
    lons = [p[0] for p in coords]
    lats = [p[1] for p in coords]
    return min(lons), max(lons), min(lats), max(lats)


def constroi(validar_malha: bool = True) -> pd.DataFrame:
    dim = busca_estados()
    log(f"{len(dim)} UFs vindas da API de localidades")

    faltando = set(dim["sigla_uf"]) ^ set(CAPITAIS)
    if faltando:
        raise ValueError(f"divergência entre a API e a tabela CAPITAIS: {sorted(faltando)}")

    dim["capital"] = dim["sigla_uf"].map(lambda s: CAPITAIS[s][0])
    dim["lat"] = dim["sigla_uf"].map(lambda s: CAPITAIS[s][1])
    dim["lon"] = dim["sigla_uf"].map(lambda s: CAPITAIS[s][2])
    dim["capital_norm"] = dim["capital"].map(normaliza_nome)
    dim["no_dieese"] = dim["sigla_uf"].isin(UFS_DIEESE)

    log("resolvendo o código IBGE de cada capital...")
    dim["cod_ibge_capital"] = [
        busca_cod_capital(linha["sigla_uf"], linha["capital"]) for _, linha in dim.iterrows()
    ]

    if validar_malha:
        log("validando lat/lon contra o bounding box da malha municipal...")
        fora = []
        for _, l in dim.iterrows():
            lon_min, lon_max, lat_min, lat_max = bbox_municipio(l["cod_ibge_capital"])
            if not (lon_min <= l["lon"] <= lon_max and lat_min <= l["lat"] <= lat_max):
                fora.append(f"{l['sigla_uf']} ({l['capital']}): ({l['lat']}, {l['lon']})")
        if fora:
            raise ValueError("coordenadas fora da malha da capital:\n  " + "\n  ".join(fora))
        log("  27/27 dentro da malha da própria capital")

    colunas = [
        "sigla_uf", "nome_uf", "capital", "capital_norm",
        "cod_ibge_uf", "cod_ibge_capital", "lat", "lon", "regiao", "no_dieese",
    ]
    return dim[colunas].sort_values("sigla_uf").reset_index(drop=True)


def valida(dim: pd.DataFrame) -> None:
    """Critérios de aceite do T-002. Falha alto — dim_uf errada contamina tudo."""
    assert len(dim) == 27, f"esperava 27 linhas, veio {len(dim)}"
    assert dim["sigla_uf"].is_unique, "sigla_uf duplicada"
    nulos = dim.isna().sum()
    assert nulos.sum() == 0, f"colunas com nulo:\n{nulos[nulos > 0]}"

    codigos = dim["cod_ibge_capital"].astype(str)
    assert (codigos.str.len() == 7).all(), "cod_ibge_capital sem 7 dígitos"
    prefixo_ok = codigos.str[:2] == dim["cod_ibge_uf"].astype(str)
    assert prefixo_ok.all(), f"prefixo não bate: {dim.loc[~prefixo_ok, 'sigla_uf'].tolist()}"

    assert dim["no_dieese"].sum() == 17, f"no_dieese marcou {int(dim['no_dieese'].sum())}, esperava 17"
    log("critérios estruturais: OK (27 linhas, sem nulo, códigos consistentes, 17 no DIEESE)")


def valida_mapeamento(dim: pd.DataFrame) -> None:
    """mapear_para_uf() tem que acertar 27/27 com acento, sem acento e em CAIXA ALTA."""
    from src.tratamento import chaves

    chaves.carrega_dim_uf.cache_clear()
    chaves._tabela_busca.cache_clear()

    variantes = {
        "com acento": dim["capital"],
        "sem acento": dim["capital"].map(normaliza_nome),
        "CAIXA ALTA": dim["capital"].str.upper(),
        "com sufixo de UF": dim["capital"] + "/" + dim["sigla_uf"],
        "nome da UF": dim["nome_uf"],
    }
    esperado = dim["sigla_uf"].to_numpy(dtype=object)
    for rotulo, serie in variantes.items():
        obtido = chaves.mapear_para_uf(serie).to_numpy(dtype=object)
        acertou = obtido == esperado
        erradas = [
            f"{cap} -> {got!r}"
            for cap, got, ok in zip(dim["capital"], obtido, acertou)
            if not ok
        ]
        assert acertou.all(), f"{rotulo}: {int(acertou.sum())}/27 (falhou em {erradas})"
        log(f"mapear_para_uf [{rotulo}]: 27/27")

    # Armadilha do DIEESE: às vezes "Brasília", às vezes "Distrito Federal".
    df_variantes = pd.Series(["Brasília", "Distrito Federal", "BRASILIA", "brasilia/df"])
    obtido = chaves.mapear_para_uf(df_variantes)
    assert (obtido == "DF").all(), f"Brasília/DF: {obtido.tolist()}"
    log("mapear_para_uf [Brasília ~ Distrito Federal]: OK")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="T-002 — constrói dim_uf.csv")
    p.add_argument("--sem-validar-malha", action="store_true", help="pula a checagem de lat/lon")
    args = p.parse_args(argv)

    dim = constroi(validar_malha=not args.sem_validar_malha)
    valida(dim)

    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    dim.to_csv(DESTINO, index=False, encoding="utf-8")
    log(f"→ {DESTINO.relative_to(RAIZ)} ({len(dim)} linhas)")

    valida_mapeamento(dim)
    print()
    print(dim.to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
