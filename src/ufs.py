"""Tabela das 27 UFs: código IBGE, sigla, nome e região.

**Ponte temporária até o T-002.** O ticket T-002 entrega
`data/processed/dim_uf.csv` como tabela canônica, e os coletores T-014/T-015
dependem formalmente dele. Como o T-002 ainda não estava pronto, esta função usa o
`dim_uf.csv` **quando ele existe** e cai para a API de localidades do IBGE — que é
a mesma fonte que o T-002 usa — quando não existe. Assim os coletores não ficam
bloqueados e passam a validar contra a tabela canônica automaticamente, no dia em
que ela aparecer, sem precisar mexer em código.

Por que os coletores precisam disto:

* **T-015** não funciona sem o geocódigo: a API do Monitor de Secas é consultada
  por `area={cod_ibge_uf}` (23 = CE, 35 = SP), então sem o mapeamento
  código ↔ sigla não há como baixar nem rotular.
* **T-014** tem como critério de aceite que a `sigla_uf` das estações bata com
  `dim_uf` e que todas as 27 UFs apareçam — o que exige a lista canônica.
"""

from __future__ import annotations

import json

import pandas as pd

from . import config, rede

URL_UFS_IBGE = "https://servicodados.ibge.gov.br/api/v1/localidades/estados?orderBy=nome"

N_UFS = 27


def _ufs_ibge(forcar: bool = False) -> pd.DataFrame:
    bruto = rede.get_texto(URL_UFS_IBGE, cache=config.RAW_IBGE / "localidades_estados.json", forcar=forcar)
    registros = json.loads(bruto)
    return pd.DataFrame(
        {
            "cod_ibge_uf": [int(uf["id"]) for uf in registros],
            "sigla_uf": [uf["sigla"] for uf in registros],
            "nome_uf": [uf["nome"] for uf in registros],
            "regiao": [uf["regiao"]["nome"] for uf in registros],
        }
    )


def carregar_ufs(forcar: bool = False) -> pd.DataFrame:
    """Devolve as 27 UFs com `cod_ibge_uf`, `sigla_uf`, `nome_uf` e `regiao`."""
    if config.DIM_UF.exists():
        dim = pd.read_csv(config.DIM_UF, dtype={"cod_ibge_uf": int})
        faltando = {"cod_ibge_uf", "sigla_uf"} - set(dim.columns)
        if faltando:
            raise ValueError(f"{config.DIM_UF} existe mas não tem as colunas {sorted(faltando)}")
        colunas = [c for c in ("cod_ibge_uf", "sigla_uf", "nome_uf", "regiao") if c in dim.columns]
        ufs = dim[colunas].copy()
        print(f"  UFs: usando a tabela canônica {config.DIM_UF.relative_to(config.RAIZ)} (T-002)")
    else:
        ufs = _ufs_ibge(forcar=forcar)
        print(
            "  UFs: dim_uf.csv (T-002) ainda não existe — usando a API do IBGE direto.\n"
            "       Quando o T-002 entregar a tabela, este coletor passa a validar contra ela sozinho."
        )

    if len(ufs) != N_UFS:
        raise ValueError(f"esperava {N_UFS} UFs, encontrei {len(ufs)}")

    return ufs.sort_values("sigla_uf", ignore_index=True)
