"""T-014, etapa 3 — agrega os dados horários do INMET para estação × dia.

Uso (a partir da raiz do repositório):

    python -m src.coleta.inmet.agrega_dia
    python -m src.coleta.inmet.agrega_dia --anos 2015 2016

Entrada:  `data/raw/inmet/*.zip`
Saída:    `data/interim/clima_estacao_dia.parquet/` (um arquivo por ano)

## Memória

Os ZIPs somam 1,27 GB comprimidos e ~7.300 arquivos de estação. Descomprimir
tudo de uma vez, ou empilhar todos os anos num DataFrame só, come vários GB e
derruba a máquina. Aqui o processamento é **um ano por vez, um CSV por vez**: o
CSV é lido de dentro do ZIP direto para memória (nunca para o disco), agregado
na hora para ~365 linhas diárias, e o horário é descartado. O pico de memória
fica na casa de dezenas de MB.

## Ausência de dado

`-9999` é o código de ausência do INMET (até 2018; de 2019 em diante o campo vem
vazio). Os dois são declarados em `na_values`, ou seja, tratados **na leitura**,
antes de qualquer média — que é a única ordem segura. Se um `-9999` escapar como
número, a temperatura média da estação vira algo como -3.000 °C e contamina tudo
sem levantar exceção. Há ainda uma varredura defensiva depois da leitura, que
conta o que tenha escapado, para o caso de o INMET inventar outra grafia.
"""

from __future__ import annotations

import argparse
import io
import shutil
import zipfile
from collections import Counter
from pathlib import Path

import pandas as pd

from ... import config
from . import (
    ENCODING_CSV,
    FAIXA_CHUVA_DIA_MM,
    FAIXA_TEMPERATURA_C,
    FAIXA_UMIDADE_PCT,
    LINHAS_METADADOS,
    MINIMO_HORAS_VALIDAS,
    SENTINELA_AUSENTE,
    SEPARADOR_CSV,
)
from .colunas import mapear_colunas_dados, parsear_metadados
from .download import anos_padrao, caminho_zip, csvs_do_zip

SAIDA = config.DATA_INTERIM / "clima_estacao_dia.parquet"

# Todas as grafias do sentinela que já apareceram nos arquivos, mais as variantes
# plausíveis. Strings vazias já viram NaN pelo padrão do pandas.
VALORES_AUSENTES = ["-9999", "-9999.0", "-9999,0", "-9999.00", "-9999,00"]

COLUNAS_NUMERICAS = ("chuva_mm", "temp_c", "temp_max_c", "temp_min_c", "umidade_pct", "radiacao_kjm2")

COLUNAS_SAIDA = [
    "codigo_estacao",
    "sigla_uf",
    "data",
    "ano",
    "mes",
    "chuva_mm",
    "temp_media",
    "temp_max",
    "temp_min",
    "umidade_media",
    "radiacao_total",
    "horas_validas",
    "horas_validas_chuva",
    "horas_registradas",
]


def _ler_horario(dados: bytes) -> tuple[pd.DataFrame, dict[str, str]]:
    """Lê um CSV de estação-ano de dentro do ZIP e devolve o horário canônico."""
    meta = parsear_metadados(dados[:4096].decode(ENCODING_CSV, errors="replace").splitlines()[:LINHAS_METADADOS])

    df = pd.read_csv(
        io.BytesIO(dados),
        sep=SEPARADOR_CSV,
        decimal=",",
        encoding=ENCODING_CSV,
        skiprows=LINHAS_METADADOS,
        na_values=VALORES_AUSENTES,
        dtype=str,
    )

    mapa = mapear_colunas_dados(list(df.columns))
    df = df[list(mapa)].rename(columns=mapa)

    # A conversão numérica é feita aqui, e não pelo `read_csv`, porque a vírgula
    # decimal combinada com colunas que às vezes vêm totalmente vazias faz o
    # pandas inferir tipos diferentes de arquivo para arquivo.
    for coluna in COLUNAS_NUMERICAS:
        if coluna in df.columns:
            df[coluna] = pd.to_numeric(df[coluna].str.replace(",", ".", regex=False), errors="coerce")

    # 2014-2018: `2014-01-01`. 2019-2026: `2019/01/01`. Uniformizar o separador
    # deixa um único formato para o parser, em vez de inferência por linha.
    df["data"] = pd.to_datetime(
        df["data"].str.strip().str.replace("/", "-", regex=False),
        format="%Y-%m-%d",
        errors="coerce",
    )

    return df, meta


def _agregar_dia(horario: pd.DataFrame) -> pd.DataFrame:
    """Hora -> dia. Chuva e radiação somam; temperatura e umidade não."""
    grupos = horario.groupby("data", sort=True)

    diario = pd.DataFrame(
        {
            # min_count=1 impede que um dia inteiro de NaN vire 0 mm de chuva,
            # que seria indistinguível de um dia genuinamente seco.
            "chuva_mm": grupos["chuva_mm"].sum(min_count=1),
            "temp_media": grupos["temp_c"].mean(),
            "temp_max": grupos["temp_max_c"].max(),
            "temp_min": grupos["temp_min_c"].min(),
            "umidade_media": grupos["umidade_pct"].mean(),
            "radiacao_total": grupos["radiacao_kjm2"].sum(min_count=1),
            "horas_validas": grupos["temp_c"].count(),
            "horas_validas_chuva": grupos["chuva_mm"].count(),
            "horas_registradas": grupos.size(),
        }
    )

    # O corte de horas válidas é aplicado por grandeza, não em bloco: chuva e
    # temperatura falham de forma independente no INMET (é comum o pluviômetro
    # parar e o termômetro seguir), e zerar as duas juntas jogaria fora dado bom.
    poucas_temp = diario["horas_validas"] < MINIMO_HORAS_VALIDAS
    diario.loc[poucas_temp, ["temp_media", "temp_max", "temp_min", "umidade_media"]] = pd.NA

    poucas_chuva = diario["horas_validas_chuva"] < MINIMO_HORAS_VALIDAS
    diario.loc[poucas_chuva, "chuva_mm"] = pd.NA

    # A radiação é nula à noite por natureza, então não faz sentido exigir 18
    # horas válidas dela; o que se exige é que o dia tenha registro suficiente.
    diario.loc[diario["horas_registradas"] < MINIMO_HORAS_VALIDAS, "radiacao_total"] = pd.NA

    return diario.reset_index()


def _aplicar_faixas(diario: pd.DataFrame, contador: Counter) -> pd.DataFrame:
    """Zera para NaN o que está fora do fisicamente possível.

    Chuva de 900 mm num dia ou temperatura de -300 °C não é clima extremo: é
    sentinela de erro disfarçada de número, e o T-014 manda tratar como ausente.
    """
    limites = {
        "chuva_mm": FAIXA_CHUVA_DIA_MM,
        "temp_media": FAIXA_TEMPERATURA_C,
        "temp_max": FAIXA_TEMPERATURA_C,
        "temp_min": FAIXA_TEMPERATURA_C,
        "umidade_media": FAIXA_UMIDADE_PCT,
    }
    for coluna, (minimo, maximo) in limites.items():
        valores = diario[coluna]
        fora = valores.notna() & ((valores < minimo) | (valores > maximo))
        n_fora = int(fora.sum())
        if n_fora:
            contador[f"fora_de_faixa_{coluna}"] += n_fora
            diario.loc[fora, coluna] = pd.NA
    return diario


def processar_ano(ano: int, contador: Counter) -> pd.DataFrame:
    caminho = caminho_zip(ano)
    if not caminho.exists():
        raise FileNotFoundError(f"{caminho} não existe. Rode: python -m src.coleta.inmet.download --anos {ano}")

    diarios: list[pd.DataFrame] = []

    with zipfile.ZipFile(caminho) as arquivo:
        nomes = csvs_do_zip(arquivo)
        for nome in nomes:
            try:
                horario, meta = _ler_horario(arquivo.read(nome))
            except (ValueError, pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeError) as erro:
                contador["csv_ilegivel"] += 1
                print(f"      ! {Path(nome).name}: {type(erro).__name__}: {erro}")
                continue

            codigo = meta.get("codigo_estacao", "").strip().upper()
            sigla = meta.get("sigla_uf", "").strip().upper()
            if not codigo or not sigla:
                contador["sem_codigo_ou_uf"] += 1
                continue

            # Varredura defensiva: se o sentinela escapou do `na_values`, é aqui
            # que ele morre — e fica contado, para o problema aparecer no relatório
            # em vez de virar média envenenada.
            for coluna in COLUNAS_NUMERICAS:
                if coluna in horario.columns:
                    escapou = horario[coluna] == SENTINELA_AUSENTE
                    n_escapou = int(escapou.sum())
                    if n_escapou:
                        contador["sentinela_escapou"] += n_escapou
                        horario.loc[escapou, coluna] = pd.NA

            sem_data = int(horario["data"].isna().sum())
            if sem_data:
                contador["linhas_sem_data"] += sem_data
                horario = horario[horario["data"].notna()]
            if horario.empty:
                contador["csv_sem_linha_valida"] += 1
                continue

            diario = _agregar_dia(horario)
            diario.insert(0, "sigla_uf", sigla)
            diario.insert(0, "codigo_estacao", codigo)
            diarios.append(diario)
            contador["estacoes"] += 1

    if not diarios:
        raise RuntimeError(f"nenhuma estação utilizável em {ano}.zip")

    df = pd.concat(diarios, ignore_index=True)
    df["ano"] = df["data"].dt.year
    df["mes"] = df["data"].dt.month
    df = _aplicar_faixas(df, contador)

    # O arquivo de um ano pode conter dias que caem no ano vizinho (uma estação
    # com janela quebrada). Mantém-se o dado, mas particiona pelo ano do ZIP para
    # a releitura ser previsível.
    return df[COLUNAS_SAIDA]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="T-014 — agrega o INMET de hora para dia")
    parser.add_argument("--anos", nargs="*", type=int, metavar="ANO")
    parser.add_argument("--limpar", action="store_true", help="apaga a saída antes de começar")
    args = parser.parse_args(argv)

    anos = sorted(set(args.anos)) if args.anos else anos_padrao()
    config.garantir_pastas()

    if args.limpar and SAIDA.exists():
        shutil.rmtree(SAIDA)
    SAIDA.mkdir(parents=True, exist_ok=True)

    print(f"T-014 — INMET: agregação hora -> dia ({anos[0]}-{anos[-1]})")
    contador: Counter = Counter()
    total_linhas = 0

    for ano in anos:
        df = processar_ano(ano, contador)
        destino = SAIDA / f"clima_estacao_dia_{ano}.parquet"
        df.to_parquet(destino, index=False)
        total_linhas += len(df)
        cobertura = 100 * df["chuva_mm"].notna().mean()
        print(
            f"    {ano}: {df['codigo_estacao'].nunique()} estações, {len(df)} dias-estação, "
            f"chuva presente em {cobertura:.1f}% -> {destino.name}"
        )

    print(f"\n  {total_linhas} linhas estação×dia em {SAIDA.relative_to(config.RAIZ)}/")
    print("  ocorrências registradas na limpeza:")
    if not contador:
        print("    (nenhuma)")
    for chave, valor in sorted(contador.items()):
        print(f"    {chave}: {valor}")
    print("\n  próximo passo: python -m src.coleta.inmet.validar")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
