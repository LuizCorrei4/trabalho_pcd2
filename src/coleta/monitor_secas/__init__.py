"""T-015 — Coletor do Monitor de Secas da ANA.

A escala de severidade e o formato numérico da fonte ficam aqui porque são o
contrato entre o download e a agregação.
"""

from __future__ import annotations

# Escala oficial do Monitor de Secas.
CATEGORIAS = ("S0", "S1", "S2", "S3", "S4")

SIGNIFICADO = {
    "S0": "seca fraca",
    "S1": "seca moderada",
    "S2": "seca grave",
    "S3": "seca extrema",
    "S4": "seca excepcional",
}

# Pesos para a severidade média, conforme o T-015: S0=1 … S4=5.
PESOS = {"S0": 1, "S1": 2, "S2": 3, "S3": 4, "S4": 5}

# A API devolve a área em PONTOS-BASE do território da UF: 10000 = 100,00%.
# Isto foi determinado empiricamente e não está documentado pela ANA — ver o
# README deste pacote para a evidência. Errar isto (tratar como km²) produz
# percentuais silenciosamente absurdos.
PONTOS_BASE = 100.0

# As categorias vêm CUMULATIVAS ("S2" = área em seca grave *ou pior*), então
# S0 >= S1 >= S2 >= S3 >= S4 sempre. Para a média ponderada é preciso desfazer o
# acúmulo e obter as faixas exclusivas.
