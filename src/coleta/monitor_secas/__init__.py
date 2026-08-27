"""T-015 — Coletor do Monitor de Secas da ANA.

A escala de severidade e o formato numérico da fonte ficam aqui porque são o
contrato entre o download e a agregação.
"""

from __future__ import annotations

CATEGORIAS = ("S0", "S1", "S2", "S3", "S4")

SIGNIFICADO = {
    "S0": "seca fraca",
    "S1": "seca moderada",
    "S2": "seca grave",
    "S3": "seca extrema",
    "S4": "seca excepcional",
}

PESOS = {"S0": 1, "S1": 2, "S2": 3, "S3": 4, "S4": 5}
PONTOS_BASE = 100.0

from .coletor import executar_coleta

__all__ = [
    "CATEGORIAS",
    "SIGNIFICADO",
    "PESOS",
    "PONTOS_BASE",
    "executar_coleta",
]
