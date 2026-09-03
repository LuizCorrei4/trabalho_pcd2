"""T-014 — Coletor de dados meteorológicos históricos do INMET.

O contrato compartilhado entre o download, o catálogo e a agregação fica aqui.
"""

from __future__ import annotations

# Código de ausência do INMET. Se sobreviver como número, contamina qualquer
# média em silêncio: a temperatura média de uma estação vira algo como -3000 °C.
# É tratado na LEITURA de cada CSV (`na_values`), nunca depois.
SENTINELA_AUSENTE = -9999

# Os CSVs de dentro do ZIP são latin-1, com `;` de separador e vírgula decimal.
# As 8 primeiras linhas são metadados da estação, não dados.
ENCODING_CSV = "latin-1"
SEPARADOR_CSV = ";"
LINHAS_METADADOS = 8

# Um dia com menos que isto de horas válidas é descartado em vez de virar média
# de meia dúzia de horas — o T-014 define o corte.
MINIMO_HORAS_VALIDAS = 18

# Faixas fisicamente plausíveis para o Brasil. Fora delas o valor é sentinela de
# erro disfarçado, não clima, e vira NaN.
FAIXA_CHUVA_DIA_MM = (0.0, 500.0)
FAIXA_TEMPERATURA_C = (-10.0, 50.0)
FAIXA_UMIDADE_PCT = (0.0, 100.0)
# Pressão medida ao nível da ESTAÇÃO, não reduzida ao nível do mar: a estação mais
# alta do país fica perto de 1.900 m, onde a pressão ronda 800 mb. A faixa é larga
# de propósito, para pegar só sentinela e não achatar estação de altitude.
FAIXA_PRESSAO_MB = (500.0, 1100.0)
FAIXA_VENTO_MS = (0.0, 75.0)

from .coletor import executar_coleta

__all__ = [
    "SENTINELA_AUSENTE",
    "ENCODING_CSV",
    "SEPARADOR_CSV",
    "LINHAS_METADADOS",
    "MINIMO_HORAS_VALIDAS",
    "FAIXA_CHUVA_DIA_MM",
    "FAIXA_TEMPERATURA_C",
    "FAIXA_UMIDADE_PCT",
    "FAIXA_PRESSAO_MB",
    "FAIXA_VENTO_MS",
    "executar_coleta",
]
