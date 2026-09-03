"""Módulo de ingestão e estruturação de preços de combustíveis (ANP)."""

from .coletor import executar_coleta

__all__ = ["executar_coleta"]
