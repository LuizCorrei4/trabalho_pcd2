"""Módulo de coleta de variáveis macroeconômicas via API do Banco Central (SGS)."""

from .coletor import executar_coleta

__all__ = ["executar_coleta"]
