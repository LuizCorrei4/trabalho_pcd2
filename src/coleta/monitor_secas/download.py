"""T-015, etapa 1 — baixa a série tabular do Monitor de Secas, por UF.

Uso (a partir da raiz do repositório):

    python -m src.coleta.monitor_secas.download
    python -m src.coleta.monitor_secas.download --ufs CE BA --forcar

Salva um JSON bruto por UF em `data/raw/ana/`. Cada arquivo já contém a série
mensal **completa** daquela UF — uma requisição por UF, 27 no total.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from ... import config, rede, ufs as mod_ufs

URL_TABULAR = "https://apimsbr.ana.gov.br/rpc/v1/dados-tabulares-monitor"

# `tipo_area=1` é o nível Unidade da Federação, e `area` é o geocódigo do IBGE
# (2 dígitos). Confirmado no código-fonte do site do Monitor, que filtra por
# `tipo_area == 1 && area == uf.geocod`.
TIPO_AREA_UF = 1

PAUSA_ENTRE_REQUISICOES = 0.5  # segundos, para não martelar a API da ANA


def caminho_bruto(sigla_uf: str) -> Path:
    return config.RAW_ANA / f"dados_tabulares_uf_{sigla_uf}.json"


def baixar_uf(sigla_uf: str, cod_ibge_uf: int, forcar: bool = False) -> int:
    """Baixa a série de uma UF e devolve quantos meses vieram."""
    url = f"{URL_TABULAR}?tipo_area={TIPO_AREA_UF}&area={cod_ibge_uf}"
    destino = caminho_bruto(sigla_uf)
    reaproveitado = destino.exists() and not forcar

    bruto = rede.get_texto(url, cache=destino, forcar=forcar)
    conteudo = json.loads(bruto)

    lista = conteudo.get("data", {}).get("list")
    if lista is None:
        destino.unlink(missing_ok=True)
        raise RuntimeError(f"resposta da API sem 'data.list' para {sigla_uf} (cod {cod_ibge_uf})")

    marca = "=" if reaproveitado else "+"
    print(f"    {marca} {sigla_uf} (cod {cod_ibge_uf}): {len(lista)} meses")
    return len(lista)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="T-015 — download do Monitor de Secas (ANA)")
    parser.add_argument("--ufs", nargs="*", metavar="SIGLA", help="siglas a baixar (padrão: todas as 27)")
    parser.add_argument("--forcar", action="store_true", help="rebaixar mesmo se o JSON já existir")
    args = parser.parse_args(argv)

    config.garantir_pastas()

    print("T-015 — Monitor de Secas (ANA): download dos dados tabulares")
    tabela = mod_ufs.carregar_ufs()
    if args.ufs:
        pedidas = {s.upper() for s in args.ufs}
        desconhecidas = pedidas - set(tabela["sigla_uf"])
        if desconhecidas:
            parser.error(f"siglas de UF desconhecidas: {sorted(desconhecidas)}")
        tabela = tabela[tabela["sigla_uf"].isin(pedidas)]

    print(f"  baixando {len(tabela)} UFs para {config.RAW_ANA.relative_to(config.RAIZ)}/")
    total_meses = 0
    for i, linha in enumerate(tabela.itertuples(index=False)):
        total_meses += baixar_uf(linha.sigla_uf, int(linha.cod_ibge_uf), forcar=args.forcar)
        if i < len(tabela) - 1:
            time.sleep(PAUSA_ENTRE_REQUISICOES)

    print(f"\n  OK: {len(tabela)} UFs, {total_meses} registros mensais no total")
    print("  próximo passo: python -m src.coleta.monitor_secas.agrega_uf_mes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
