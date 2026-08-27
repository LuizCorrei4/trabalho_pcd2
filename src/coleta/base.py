"""Contrato comum e classes de suporte para todos os módulos de coleta."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


@dataclass
class ColetaResult:
    """Resultado padronizado retornado pela execução de qualquer coletor."""

    fonte: str
    status: str  # SUCESSO | AVISO | FALHA | PULADO
    acao_executada: str  # BAIXADO_NOVO | REUTILIZADO | ATUALIZADO | BACKUP_CRIADO | PULADO_EXISTENTE
    duracao_segundos: float = 0.0
    linhas: int = 0
    colunas: int = 0
    arquivo_saida: str = ""
    tamanho_bytes: int = 0
    chunks_totais: int = 0
    chunks_baixados: int = 0
    chunks_reaproveitados: int = 0
    erros: list[str] = field(default_factory=list)
    detalhes: dict[str, Any] = field(default_factory=dict)

    def para_dicionario(self) -> dict[str, Any]:
        return {
            "fonte": self.fonte,
            "status": self.status,
            "acao_executada": self.acao_executada,
            "duracao_segundos": round(self.duracao_segundos, 2),
            "linhas": self.linhas,
            "colunas": self.colunas,
            "arquivo_saida": self.arquivo_saida,
            "tamanho_bytes": self.tamanho_bytes,
            "chunks_totais": self.chunks_totais,
            "chunks_baixados": self.chunks_baixados,
            "chunks_reaproveitados": self.chunks_reaproveitados,
            "erros": self.erros,
            "detalhes": self.detalhes,
        }


def calcular_tamanho_caminho(caminho: Path) -> int:
    """Calcula tamanho em bytes de um arquivo ou de uma pasta inteira."""
    if not caminho.exists():
        return 0
    if caminho.is_file():
        return caminho.stat().st_size
    return sum(f.stat().st_size for f in caminho.rglob("*") if f.is_file())
