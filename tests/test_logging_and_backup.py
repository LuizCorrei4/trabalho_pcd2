"""Testes unitários do sistema de logging e gestão de backups."""

import json
import logging
import shutil
import tempfile
import unittest
from pathlib import Path

from src.logging_config import (
    BackupManager,
    ConsoleFormatter,
    DownloadLogger,
    FileFormatter,
    ModuloExecucaoMeta,
    SessionManifest,
)


class TestLoggingAndBackup(unittest.TestCase):

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_console_and_file_formatters(self):
        record = logging.LogRecord(
            name="coleta.teste",
            level=logging.INFO,
            pathname="teste.py",
            lineno=42,
            msg="Mensagem de teste",
            args=(),
            exc_info=None,
        )

        c_fmt = ConsoleFormatter()
        f_fmt = FileFormatter()

        texto_console = c_fmt.format(record)
        self.assertIn("[INFO]", texto_console)
        self.assertIn("Mensagem de teste", texto_console)

        texto_arquivo = f_fmt.format(record)
        self.assertIn("[INFO", texto_arquivo)
        self.assertIn("[coleta.teste]", texto_arquivo)
        self.assertIn("Mensagem de teste", texto_arquivo)

    def test_download_logger_transacional(self):
        dl = DownloadLogger(self.temp_dir)
        csv_file = self.temp_dir / "_download_log.csv"
        self.assertTrue(csv_file.exists())

        dl.registrar(
            identificador_chunk="chunk_1.parquet",
            url="https://api.gov.br/data/1",
            status_http=200,
            tamanho_bytes=1024,
            duracao_ms=150.5,
            tentativas_retry=1,
            sucesso=True,
        )

        dl.registrar(
            identificador_chunk="chunk_2.parquet",
            url="https://api.gov.br/data/2",
            status_http=500,
            tamanho_bytes=0,
            duracao_ms=3000.0,
            tentativas_retry=4,
            sucesso=False,
            mensagem_erro="Timeout 504",
        )

        conteudo = csv_file.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(conteudo), 3)  # Cabeçalho + 2 linhas
        self.assertIn("chunk_1.parquet", conteudo[1])
        self.assertIn("chunk_2.parquet", conteudo[2])
        self.assertIn("Timeout 504", conteudo[2])

    def test_session_manifest_json(self):
        manifesto = SessionManifest(
            sessao_id="coleta_teste_001",
            comando_executado="python -m src.coleta.runner --all",
            politica_sobrescrita="skip",
            usuario="teste_user",
        )

        manifesto.adicionar_modulo(
            ModuloExecucaoMeta(
                fonte="sidra_ipca",
                status="SUCESSO",
                acao_executada="REUTILIZADO",
                duracao_segundos=0.5,
                linhas_geradas=83383,
                colunas_geradas=8,
                arquivo_saida="data/raw/sidra_ipca/ipca_alimentos_rm.parquet",
                tamanho_bytes=422000,
            )
        )

        caminho_json = manifesto.finalizar(self.temp_dir)
        self.assertTrue(caminho_json.exists())

        dados = json.loads(caminho_json.read_text(encoding="utf-8"))
        self.assertEqual(dados["sessao_id"], "coleta_teste_001")
        self.assertEqual(dados["status_geral"], "SUCESSO")
        self.assertEqual(dados["resumo"]["total_modulos"], 1)
        self.assertEqual(dados["resumo"]["sucessos"], 1)
        self.assertEqual(dados["modulos"][0]["linhas_geradas"], 83383)

    def test_backup_manager_criacao_e_restauracao(self):
        arquivo = self.temp_dir / "teste.parquet"
        arquivo.write_text("conteudo original")

        backup = BackupManager.criar_backup(arquivo)
        self.assertIsNotNone(backup)
        self.assertTrue(backup.exists())

        arquivo.write_text("conteudo modificado")
        self.assertEqual(arquivo.read_text(), "conteudo modificado")

        BackupManager.restaurar_backup(backup, arquivo)
        self.assertEqual(arquivo.read_text(), "conteudo original")

    def test_backup_manager_rollback_automatico_em_excecao(self):
        arquivo = self.temp_dir / "dado_critico.parquet"
        arquivo.write_text("versao 1.0 estavel")

        with self.assertRaises(RuntimeError):
            with BackupManager.gerenciar_com_seguranca(arquivo, ativar_backup=True):
                arquivo.write_text("versao 2.0 corrompida no meio")
                raise RuntimeError("Falha simulada de rede durante o processamento!")

        # Verifica se o arquivo foi restaurado automaticamente para a versão estável
        self.assertEqual(arquivo.read_text(), "versao 1.0 estavel")


if __name__ == "__main__":
    unittest.main()
