"""T-014, etapa 1 — baixa os ZIPs anuais de dados históricos do INMET.

Uso (a partir da raiz do repositório):

    python -m src.coleta.inmet.download                 # 2014 a 2026
    python -m src.coleta.inmet.download --anos 2014 2015
    python -m src.coleta.inmet.download --verificar      # só checa o que já existe

Salva em `data/raw/inmet/{ANO}.zip`. São ~100 MB por ano, **~1,25 GB no total** —
por isso `data/raw/` não é versionado (ver `.gitignore`).

Dois detalhes que fazem a diferença entre funcionar e não funcionar:

* O portal do INMET **derruba a conexão de cliente sem User-Agent de navegador**
  ("Connection reset by peer") e também recusa `HEAD`. Tratado no `src/rede.py`.
* O download é **atômico e idempotente**: o arquivo só aparece com o nome final
  quando terminou, e rodar de novo reaproveita o que já está completo. Com 1,25 GB
  em 13 arquivos, retomar de onde parou não é luxo.
"""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

from ... import config, rede

URL_MODELO = "https://portal.inmet.gov.br/uploads/dadoshistoricos/{ano}.zip"


def caminho_zip(ano: int) -> Path:
    return config.RAW_INMET / f"{ano}.zip"


def csvs_do_zip(arquivo: zipfile.ZipFile) -> list[str]:
    """Nomes dos CSVs de estação dentro do ZIP.

    Em 2014 os arquivos vêm dentro de uma subpasta (`2014/INMET_...CSV`) e de 2019
    em diante na raiz do ZIP; por isso a busca é por sufixo, nunca por caminho.
    """
    return [n for n in arquivo.namelist() if n.upper().endswith(".CSV")]


def verificar_zip(caminho: Path) -> int:
    """Confere se o ZIP abre e devolve quantos CSVs ele contém.

    Um ZIP truncado costuma ter tamanho "parecido" com o certo e só explode na
    leitura, muito depois. Ler o índice central agora é barato e falha cedo.
    """
    try:
        with zipfile.ZipFile(caminho) as z:
            return len(csvs_do_zip(z))
    except (zipfile.BadZipFile, OSError) as erro:
        raise RuntimeError(f"{caminho.name} está corrompido ({type(erro).__name__}): baixe de novo com --forcar") from erro


def anos_padrao() -> list[int]:
    return list(range(config.ANO_INICIO_CLIMA, config.ANO_FIM_CLIMA + 1))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="T-014 — download dos ZIPs históricos do INMET")
    parser.add_argument("--anos", nargs="*", type=int, metavar="ANO", help=f"padrão: {config.ANO_INICIO_CLIMA}-{config.ANO_FIM_CLIMA}")
    parser.add_argument("--forcar", action="store_true", help="rebaixar mesmo se o ZIP já estiver completo")
    parser.add_argument("--verificar", action="store_true", help="não baixa nada, só valida os ZIPs já presentes")
    args = parser.parse_args(argv)

    anos = sorted(set(args.anos)) if args.anos else anos_padrao()
    config.garantir_pastas()

    print(f"T-014 — INMET: {'verificação' if args.verificar else 'download'} de {len(anos)} anos ({anos[0]}-{anos[-1]})")
    print(f"  destino: {config.RAW_INMET.relative_to(config.RAIZ)}/")

    falhas: list[int] = []
    total_bytes = 0
    total_csvs = 0

    for ano in anos:
        destino = caminho_zip(ano)
        try:
            if args.verificar:
                if not destino.exists():
                    print(f"    - {ano}.zip ausente")
                    falhas.append(ano)
                    continue
            else:
                rede.baixar_arquivo(URL_MODELO.format(ano=ano), destino, forcar=args.forcar)

            n_csvs = verificar_zip(destino)
            tamanho = destino.stat().st_size
            total_bytes += tamanho
            total_csvs += n_csvs
            print(f"      {ano}: {n_csvs} estações, {tamanho / 1e6:.1f} MB, ZIP íntegro")
        except (RuntimeError, OSError) as erro:
            print(f"    ! {ano}: {erro}")
            falhas.append(ano)

    print(f"\n  total: {total_bytes / 1e9:.2f} GB em {len(anos) - len(falhas)} anos, {total_csvs} arquivos de estação")
    if falhas:
        print(f"  FALHARAM: {falhas} — rode de novo para retomar (o que já baixou é reaproveitado)")
        return 1
    print("  próximo passo: python -m src.coleta.inmet.catalogo")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
