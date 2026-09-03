"""Sistema de logging em múltiplos níveis e gestão de backups (Orquestrador de Coleta).

Estruturado em 4 camadas complementares:
1. Console / Terminal (StreamHandler - INFO / Formatado com cores)
2. Arquivo de Log em Disco (FileHandler - DEBUG, logs/execucoes/coleta_*.log)
3. Manifesto Estruturado JSON (logs/execucoes/coleta_*_manifest.json)
4. Log Transacional por Chunk/Arquivo (_download_log.csv nas pastas de dados)
"""

from __future__ import annotations

import csv
import json
import logging
import os
import platform
import shutil
import sys
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator

from . import config

# --------------------------------------------------------------------------- #
# Cores e Formatação de Console (Camada 1)                                    #
# --------------------------------------------------------------------------- #

class CoresANSI:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    VERMELHO = "\033[91m"
    VERDE = "\033[92m"
    AMARELO = "\033[93m"
    AZUL = "\033[94m"
    CIANO = "\033[96m"
    CINZA = "\033[90m"

    @classmethod
    def ativo(cls) -> bool:
        """Verifica se o terminal suporta cores ANSI."""
        if os.getenv("NO_COLOR"):
            return False
        if not sys.stdout.isatty():
            return False
        return True


class ConsoleFormatter(logging.Formatter):
    """Formatador customizado para terminal com marcadores limpos e legíveis."""

    NIVEL_LABELS = {
        logging.DEBUG: ("[DEBUG]", CoresANSI.CINZA),
        logging.INFO: ("[INFO]", CoresANSI.AZUL),
        logging.WARNING: ("[AVISO]", CoresANSI.AMARELO),
        logging.ERROR: ("[ERRO]", CoresANSI.VERMELHO),
        logging.CRITICAL: ("[CRÍTICO]", CoresANSI.VERMELHO + CoresANSI.BOLD),
    }

    def format(self, record: logging.LogRecord) -> str:
        usa_cor = CoresANSI.ativo()
        label, cor = self.NIVEL_LABELS.get(record.levelno, (f"[{record.levelname}]", ""))
        
        # Marcador de Sucesso customizado via atributo extra
        if getattr(record, "sucesso", False):
            label = "[SUCESSO]"
            cor = CoresANSI.VERDE

        if usa_cor and cor:
            prefixo = f"{cor}{CoresANSI.BOLD}{label}{CoresANSI.RESET}"
        else:
            prefixo = label

        mensagem = record.getMessage()
        if record.levelno == logging.DEBUG:
            return f"  {prefixo} ({record.name}:{record.lineno}) {mensagem}"
        return f"  {prefixo} {mensagem}"


class FileFormatter(logging.Formatter):
    """Formatador detalhado para arquivo em disco (Camada 2 - Nível DEBUG)."""

    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        ct = datetime.fromtimestamp(record.created)
        return ct.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    def format(self, record: logging.LogRecord) -> str:
        ts = self.formatTime(record)
        nivel = record.levelname.ljust(7)
        logger_name = record.name
        origem = f"{record.funcName}:{record.lineno}"
        msg = record.getMessage()

        linha = f"[{ts}] [{nivel}] [{logger_name}] [{origem}] -> {msg}"
        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
            linha += f"\n{record.exc_text}"
        return linha


# --------------------------------------------------------------------------- #
# Configuração Central de Loggers                                            #
# --------------------------------------------------------------------------- #

_SESSAO_LOG_DIR: Path | None = None
_SESSAO_LOG_FILE: Path | None = None
_SESSAO_ID: str | None = None


def obter_pasta_logs() -> Path:
    """Garante e devolve o diretório de logs de execuções."""
    pasta = config.RAIZ / "logs" / "execucoes"
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def inicializar_sessao_logging(
    sessao_id: str | None = None,
    nivel_console: int = logging.INFO,
    nivel_arquivo: int = logging.DEBUG,
) -> tuple[str, Path, logging.Logger]:
    """Inicializa a sessão de logging criando arquivo de log e configurando handlers.

    Returns:
        (sessao_id, caminho_arquivo_log, logger_raiz)
    """
    global _SESSAO_ID, _SESSAO_LOG_DIR, _SESSAO_LOG_FILE

    if sessao_id is None:
        ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        sessao_id = f"coleta_{ts_str}"

    _SESSAO_ID = sessao_id
    pasta_logs = obter_pasta_logs()
    _SESSAO_LOG_DIR = pasta_logs
    _SESSAO_LOG_FILE = pasta_logs / f"{sessao_id}.log"

    logger_principal = logging.getLogger("coleta")
    logger_principal.setLevel(logging.DEBUG)
    logger_principal.propagate = False

    # Limpar handlers existentes para não duplicar
    for handler in list(logger_principal.handlers):
        logger_principal.removeHandler(handler)
        handler.close()

    # Handler 1: Console
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(nivel_console)
    ch.setFormatter(ConsoleFormatter())
    logger_principal.addHandler(ch)

    # Handler 2: Arquivo detalhado
    fh = logging.FileHandler(_SESSAO_LOG_FILE, encoding="utf-8")
    fh.setLevel(nivel_arquivo)
    fh.setFormatter(FileFormatter())
    logger_principal.addHandler(fh)

    logger_principal.debug(f"Sessão de logging inicializada: {sessao_id} -> {_SESSAO_LOG_FILE}")
    return sessao_id, _SESSAO_LOG_FILE, logger_principal


def get_logger(nome: str = "coleta") -> logging.Logger:
    """Devolve logger filho sob a hierarquia 'coleta'."""
    if nome == "coleta" or nome.startswith("coleta."):
        return logging.getLogger(nome)
    return logging.getLogger(f"coleta.{nome}")


# --------------------------------------------------------------------------- #
# Camada 4: Log Transacional Local (_download_log.csv)                        #
# --------------------------------------------------------------------------- #

COLUNAS_DOWNLOAD_LOG = [
    "timestamp",
    "identificador_chunk",
    "url",
    "status_http",
    "tamanho_bytes",
    "duracao_ms",
    "tentativas_retry",
    "sucesso",
    "mensagem_erro",
]


class DownloadLogger:
    """Registrador transacional por chunk/arquivo em CSV."""

    def __init__(self, pasta_destino: Path):
        self.pasta = Path(pasta_destino)
        self.arquivo_csv = self.pasta / "_download_log.csv"
        self._garantir_cabecalho()

    def _garantir_cabecalho(self) -> None:
        self.pasta.mkdir(parents=True, exist_ok=True)
        if not self.arquivo_csv.exists() or self.arquivo_csv.stat().st_size == 0:
            with self.arquivo_csv.open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(COLUNAS_DOWNLOAD_LOG)

    def registrar(
        self,
        identificador_chunk: str,
        url: str,
        status_http: int | None = 200,
        tamanho_bytes: int = 0,
        duracao_ms: float = 0.0,
        tentativas_retry: int = 1,
        sucesso: bool = True,
        mensagem_erro: str = "",
    ) -> None:
        """Registra atomicamente uma linha na tabela transacional."""
        ts = datetime.now(timezone.utc).isoformat()
        linha = [
            ts,
            str(identificador_chunk),
            str(url),
            str(status_http if status_http is not None else ""),
            str(tamanho_bytes),
            f"{duracao_ms:.2f}",
            str(tentativas_retry),
            str(bool(sucesso)),
            str(mensagem_erro or "").replace("\n", " "),
        ]
        with self.arquivo_csv.open("a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(linha)


# --------------------------------------------------------------------------- #
# Camada 3: Manifesto Estruturado JSON (_manifest.json)                       #
# --------------------------------------------------------------------------- #

@dataclass
class ModuloExecucaoMeta:
    fonte: str
    status: str  # SUCESSO, AVISO, FALHA, PULADO
    acao_executada: str  # BAIXADO_NOVO, REUTILIZADO, ATUALIZADO, BACKUP_CRIADO, PULADO_EXISTENTE
    duracao_segundos: float = 0.0
    linhas_geradas: int = 0
    colunas_geradas: int = 0
    arquivo_saida: str = ""
    tamanho_bytes: int = 0
    chunks_totais: int = 0
    chunks_baixados: int = 0
    chunks_reaproveitados: int = 0
    erros: list[str] = field(default_factory=list)
    detalhes: dict[str, Any] = field(default_factory=dict)


class SessionManifest:
    """Gerenciador do manifesto de execução estruturado em JSON."""

    def __init__(
        self,
        sessao_id: str,
        comando_executado: str,
        politica_sobrescrita: str,
        usuario: str | None = None,
    ):
        self.sessao_id = sessao_id
        self.timestamp_inicio = datetime.now(timezone.utc).isoformat()
        self.timestamp_fim: str | None = None
        self.duracao_total_segundos: float = 0.0
        self.usuario = usuario or os.getenv("USER") or os.getenv("USERNAME") or "desconhecido"
        self.comando_executado = comando_executado
        self.politica_sobrescrita = politica_sobrescrita
        self.status_geral = "EM_EXECUCAO"
        self.modulos: list[ModuloExecucaoMeta] = []
        self._inicio_time = time.perf_counter()

    def adicionar_modulo(self, meta: ModuloExecucaoMeta) -> None:
        self.modulos.append(meta)

    def finalizar(self, pasta_destino: Path | None = None) -> Path:
        self.timestamp_fim = datetime.now(timezone.utc).isoformat()
        self.duracao_total_segundos = round(time.perf_counter() - self._inicio_time, 2)

        total = len(self.modulos)
        sucessos = sum(1 for m in self.modulos if m.status == "SUCESSO")
        avisos = sum(1 for m in self.modulos if m.status == "AVISO")
        falhas = sum(1 for m in self.modulos if m.status == "FALHA")

        if falhas > 0:
            self.status_geral = "FALHA"
        elif avisos > 0:
            self.status_geral = "CONCLUIDO_COM_AVISOS"
        else:
            self.status_geral = "SUCESSO"

        payload = {
            "sessao_id": self.sessao_id,
            "timestamp_inicio": self.timestamp_inicio,
            "timestamp_fim": self.timestamp_fim,
            "duracao_total_segundos": self.duracao_total_segundos,
            "usuario": self.usuario,
            "sistema": f"{platform.system()} {platform.release()}",
            "comando_executado": self.comando_executado,
            "politica_sobrescrita": self.politica_sobrescrita,
            "status_geral": self.status_geral,
            "resumo": {
                "total_modulos": total,
                "sucessos": sucessos,
                "avisos": avisos,
                "falhas": falhas,
            },
            "modulos": [asdict(m) for m in self.modulos],
        }

        pasta = pasta_destino or obter_pasta_logs()
        arquivo_manifesto = pasta / f"{self.sessao_id}_manifest.json"
        pasta.mkdir(parents=True, exist_ok=True)
        with arquivo_manifesto.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        return arquivo_manifesto


# --------------------------------------------------------------------------- #
# Gestão de Backups e Rollback Automático                                     #
# --------------------------------------------------------------------------- #

class BackupManager:
    """Utilitário de backup atômico com rollback."""

    @staticmethod
    def criar_backup(caminho_arquivo: Path) -> Path | None:
        """Cria uma cópia de segurança com timestamp (ex: .parquet.bak_YYYYMMDD_HHMMSS)."""
        caminho = Path(caminho_arquivo)
        if not caminho.exists():
            return None

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_backup = f"{caminho.name}.bak_{ts}"
        caminho_backup = caminho.parent / nome_backup

        if caminho.is_dir():
            shutil.copytree(caminho, caminho_backup)
        else:
            shutil.copy2(caminho, caminho_backup)

        return caminho_backup

    @staticmethod
    def restaurar_backup(caminho_backup: Path, caminho_destino: Path) -> None:
        """Restaura o backup para o caminho original."""
        backup = Path(caminho_backup)
        destino = Path(caminho_destino)
        if not backup.exists():
            raise FileNotFoundError(f"Backup não encontrado: {backup}")

        if destino.exists():
            if destino.is_dir():
                shutil.rmtree(destino)
            else:
                destino.unlink()

        if backup.is_dir():
            shutil.copytree(backup, destino)
        else:
            shutil.copy2(backup, destino)

    @classmethod
    @contextmanager
    def gerenciar_com_seguranca(
        cls,
        caminho_arquivo: Path,
        ativar_backup: bool = True,
        logger: logging.Logger | None = None,
    ) -> Generator[Path | None, None, None]:
        """Context manager que cria backup e faz rollback automático em caso de exceção."""
        caminho = Path(caminho_arquivo)
        backup_path: Path | None = None

        if ativar_backup and caminho.exists():
            backup_path = cls.criar_backup(caminho)
            if logger:
                logger.info(f"Cópia de segurança criada: {backup_path.name}")

        try:
            yield backup_path
        except Exception as e:
            if backup_path and backup_path.exists():
                if logger:
                    logger.warning(
                        f"Falha detectada durante operação em {caminho.name}. "
                        f"Restaurando backup {backup_path.name}..."
                    )
                cls.restaurar_backup(backup_path, caminho)
                if logger:
                    logger.info("Backup restaurado com sucesso.")
            raise e


# --------------------------------------------------------------------------- #
# Modo Interativo de Confirmação                                              #
# --------------------------------------------------------------------------- #

def prompt_confirmacao(caminho_arquivo: Path, logger: logging.Logger | None = None) -> str:
    """Interroga o usuário quando o arquivo de destino já existe.

    Opções:
    - [S]obrescrever (force)
    - [P]ular (skip)
    - Criar [B]ackup e sobrescrever (backup)
    - [C]ancelar execução geral

    Returns: 'force' | 'skip' | 'backup' | 'cancel'
    """
    caminho = Path(caminho_arquivo)
    info_tamanho = ""
    if caminho.exists():
        if caminho.is_file():
            mb = caminho.stat().st_size / 1e6
            info_tamanho = f" ({mb:.2f} MB)"
        elif caminho.is_dir():
            info_tamanho = " (diretório)"

    prompt = (
        f"\n⚠️  Arquivo '{caminho.name}' já existe{info_tamanho}.\n"
        f"   [S]obrescrever, [P]ular, Criar [B]ackup ou [C]ancelar? [s/p/b/c]: "
    )

    while True:
        try:
            escolha = input(prompt).strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nOperação cancelada pelo usuário.")
            return "cancel"

        if escolha in ("s", "sobrescrever", "f", "force"):
            return "force"
        elif escolha in ("p", "pular", "skip"):
            return "skip"
        elif escolha in ("b", "backup"):
            return "backup"
        elif escolha in ("c", "cancelar", "cancel"):
            return "cancel"
        else:
            print("Opção inválida. Digite 's', 'p', 'b' ou 'c'.")
