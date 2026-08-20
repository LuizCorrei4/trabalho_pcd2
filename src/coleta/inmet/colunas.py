"""Normalização dos nomes de coluna e metadados dos CSVs do INMET.

Os nomes mudaram ao longo dos anos — e não só nos acentos. Entre 2014 e 2026 o
mesmo campo aparece como `DATA (YYYY-MM-DD)` e como `Data`; `HORA (UTC)` e
`Hora UTC`; `REGIÃO:` e `REGIAO:`. O ticket T-014 é explícito: mapear **por
padrão de texto, não por posição**. Casar por posição funcionaria hoje (a ordem
das colunas é estável nos 13 anos) e quebraria em silêncio no dia em que o INMET
inserir uma coluna no meio.

A estratégia: tirar acento, subir para maiúscula, e casar por trecho
característico. Depois **conferir que cada destino casou exatamente uma vez** —
é essa conferência que transforma uma mudança futura de formato em erro alto em
vez de coluna silenciosamente vazia.
"""

from __future__ import annotations

import re
import unicodedata

# As 19 colunas de dados do CSV do INMET. Ordem importa: o primeiro padrão que
# casar vence, então o mais específico vem antes do mais genérico.
REGRAS_DADOS: tuple[tuple[str, str], ...] = (
    (r"^DATA\b", "data"),
    (r"^HORA\b", "hora"),
    (r"PRECIPITACAO TOTAL", "chuva_mm"),
    (r"RADIACAO GLOBAL", "radiacao_kjm2"),
    # Pressão: as variantes "MAX./MIN. NA HORA ANT." vêm antes da horária, senão
    # um padrão genérico de pressão engoliria as três.
    (r"PRESSAO ATMOSFERICA MAX", "pressao_max_mb"),
    (r"PRESSAO ATMOSFERICA MIN", "pressao_min_mb"),
    (r"PRESSAO ATMOSFERICA AO NIVEL", "pressao_mb"),
    # Orvalho antes das temperaturas do ar: "TEMPERATURA ORVALHO MAX." não pode
    # ser confundida com "TEMPERATURA MÁXIMA" — são grandezas diferentes, e casar
    # errado importaria ponto de orvalho como temperatura do ar.
    (r"TEMPERATURA ORVALHO MAX", "temp_orvalho_max_c"),
    (r"TEMPERATURA ORVALHO MIN", "temp_orvalho_min_c"),
    (r"TEMPERATURA DO PONTO DE ORVALHO", "temp_orvalho_c"),
    # "DO AR ... BULBO SECO" separa a temperatura do ar das de orvalho.
    (r"TEMPERATURA DO AR.*BULBO SECO", "temp_c"),
    (r"TEMPERATURA MAXIMA", "temp_max_c"),
    (r"TEMPERATURA MINIMA", "temp_min_c"),
    # Idem para umidade: as extremas da hora anterior antes da horária.
    (r"UMIDADE REL\.? MAX", "umidade_max_pct"),
    (r"UMIDADE REL\.? MIN", "umidade_min_pct"),
    (r"UMIDADE RELATIVA DO AR", "umidade_pct"),
    (r"VENTO, DIRECAO", "vento_direcao_gr"),
    (r"VENTO, RAJADA", "vento_rajada_ms"),
    (r"VENTO, VELOCIDADE", "vento_velocidade_ms"),
)

# Todas as colunas numéricas do arquivo horário.
COLUNAS_NUMERICAS_TODAS = tuple(
    destino for _, destino in REGRAS_DADOS if destino not in ("data", "hora")
)

# Sem estas o dia não é utilizável.
COLUNAS_OBRIGATORIAS = ("data", "hora", "chuva_mm", "temp_c", "temp_max_c", "temp_min_c", "umidade_pct")

REGRAS_METADADOS: tuple[tuple[str, str], ...] = (
    (r"^REGIAO", "regiao"),
    (r"^UF", "sigla_uf"),
    (r"^ESTACAO", "nome_estacao"),
    (r"^CODIGO", "codigo_estacao"),
    (r"^LATITUDE", "lat"),
    (r"^LONGITUDE", "lon"),
    (r"^ALTITUDE", "altitude"),
    (r"^DATA DE FUNDACAO", "data_fundacao"),
)


def normaliza(texto: str) -> str:
    """Tira acento, sobe para maiúscula e colapsa espaço."""
    sem_acento = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", sem_acento).strip().upper()


def _aplicar(regras: tuple[tuple[str, str], ...], nome: str) -> str | None:
    alvo = normaliza(nome)
    for padrao, destino in regras:
        if re.search(padrao, alvo):
            return destino
    return None


def mapear_colunas_dados(nomes: list[str]) -> dict[str, str]:
    """Mapeia nomes originais de coluna -> nomes canônicos do projeto.

    Levanta erro se um destino casar com duas colunas diferentes (ambiguidade) ou
    se faltar coluna obrigatória — os dois sintomas de mudança de formato.
    """
    mapa: dict[str, str] = {}
    for nome in nomes:
        destino = _aplicar(REGRAS_DADOS, nome)
        if destino is not None:
            mapa[nome] = destino

    contagem: dict[str, list[str]] = {}
    for origem, destino in mapa.items():
        contagem.setdefault(destino, []).append(origem)

    ambiguos = {d: o for d, o in contagem.items() if len(o) > 1}
    if ambiguos:
        raise ValueError(f"colunas do INMET ambíguas — o mapeamento precisa ser revisto: {ambiguos}")

    faltando = [c for c in COLUNAS_OBRIGATORIAS if c not in contagem]
    if faltando:
        raise ValueError(f"colunas obrigatórias não encontradas no CSV do INMET: {faltando} (vistas: {nomes})")

    return mapa


def parsear_metadados(linhas: list[str]) -> dict[str, str]:
    """Converte as 8 linhas de cabeçalho (`RÓTULO:;valor`) em dicionário canônico."""
    metadados: dict[str, str] = {}
    for linha in linhas:
        if ";" not in linha:
            continue
        rotulo, _, valor = linha.partition(";")
        destino = _aplicar(REGRAS_METADADOS, rotulo.rstrip(":"))
        if destino is not None and destino not in metadados:
            metadados[destino] = valor.strip()
    return metadados


def para_float(texto: str | None) -> float | None:
    """Converte número em formato brasileiro (vírgula decimal) para float."""
    if texto is None:
        return None
    limpo = str(texto).strip().replace(",", ".")
    if not limpo:
        return None
    try:
        return float(limpo)
    except ValueError:
        return None
