"""Testes unitários e de integração para o Runner CLI e orquestrador."""

import unittest
from src.coleta.runner import (
    construir_parser,
    formatar_tabela_resumo,
    inspecionar_status_disco,
    resolver_fontes_selecionadas,
    resolver_nome_fonte,
    resolver_politica_sobrescrita,
)
from src.coleta.base import ColetaResult


class TestRunnerCLI(unittest.TestCase):

    def setUp(self):
        self.parser = construir_parser()

    def test_resolver_nome_fonte_e_aliases(self):
        self.assertEqual(resolver_nome_fonte("ipca"), "ipca")
        self.assertEqual(resolver_nome_fonte("sidra_ipca"), "ipca")
        self.assertEqual(resolver_nome_fonte("inflacao"), "ipca")
        self.assertEqual(resolver_nome_fonte("inmet"), "inmet")
        self.assertEqual(resolver_nome_fonte("clima"), "inmet")
        self.assertEqual(resolver_nome_fonte("bdmep"), "inmet")
        self.assertEqual(resolver_nome_fonte("seca"), "seca")
        self.assertEqual(resolver_nome_fonte("monitor_secas"), "seca")
        self.assertEqual(resolver_nome_fonte("safra"), "safra")
        self.assertEqual(resolver_nome_fonte("lspa"), "safra")
        self.assertEqual(resolver_nome_fonte("bcb"), "bcb")
        self.assertEqual(resolver_nome_fonte("sgs"), "bcb")
        self.assertEqual(resolver_nome_fonte("macro"), "bcb")
        self.assertEqual(resolver_nome_fonte("combustiveis"), "combustiveis")
        self.assertEqual(resolver_nome_fonte("anp"), "combustiveis")
        self.assertEqual(resolver_nome_fonte("diesel"), "combustiveis")
        self.assertIsNone(resolver_nome_fonte("fonte_inexistente"))

    def test_parser_escopo_all(self):
        args = self.parser.parse_args(["--all"])
        fontes = resolver_fontes_selecionadas(args)
        self.assertEqual(fontes, ["ipca", "inmet", "seca", "safra", "bcb", "combustiveis"])

    def test_parser_escopo_completo(self):
        args = self.parser.parse_args(["--completo"])
        self.assertTrue(args.completo)
        fontes = resolver_fontes_selecionadas(args)
        self.assertEqual(fontes, ["ipca", "inmet", "seca", "safra", "bcb", "combustiveis"])

    def test_parser_escopo_tratamento(self):
        args = self.parser.parse_args(["--tratamento"])
        self.assertTrue(args.tratamento)
        fontes = resolver_fontes_selecionadas(args)
        self.assertEqual(fontes, [])

    def test_parser_escopo_individual(self):
        args = self.parser.parse_args(["--fonte", "ipca"])
        fontes = resolver_fontes_selecionadas(args)
        self.assertEqual(fontes, ["ipca"])

    def test_parser_escopo_subconjunto(self):
        args = self.parser.parse_args(["--fontes", "ipca,bcb,combustiveis"])
        fontes = resolver_fontes_selecionadas(args)
        self.assertEqual(fontes, ["ipca", "bcb", "combustiveis"])

    def test_parser_politica_sobrescrita(self):
        args_padrao = self.parser.parse_args(["--all"])
        self.assertEqual(resolver_politica_sobrescrita(args_padrao), "skip")

        args_force = self.parser.parse_args(["--all", "--force"])
        self.assertEqual(resolver_politica_sobrescrita(args_force), "force")

        args_update = self.parser.parse_args(["--all", "--update"])
        self.assertEqual(resolver_politica_sobrescrita(args_update), "update")

        args_backup = self.parser.parse_args(["--all", "--backup"])
        self.assertEqual(resolver_politica_sobrescrita(args_backup), "backup")

        args_explicit = self.parser.parse_args(["--all", "--overwrite", "force"])
        self.assertEqual(resolver_politica_sobrescrita(args_explicit), "force")

    def test_formatar_tabela_resumo(self):
        resultados = [
            ColetaResult(
                fonte="ipca",
                status="SUCESSO",
                acao_executada="REUTILIZADO",
                linhas=83383,
                colunas=8,
                arquivo_saida="data/raw/sidra_ipca/ipca_alimentos_rm.parquet",
                tamanho_bytes=422682,
                duracao_segundos=0.05,
            ),
            ColetaResult(
                fonte="bcb",
                status="AVISO",
                acao_executada="ATUALIZADO",
                linhas=151,
                colunas=8,
                arquivo_saida="data/interim/macro_br_mes.parquet",
                tamanho_bytes=13500,
                duracao_segundos=1.20,
            ),
        ]

        tabela_str = formatar_tabela_resumo(resultados)
        self.assertIn("Fonte", tabela_str)
        self.assertIn("ipca", tabela_str)
        self.assertIn("83,383", tabela_str)
        self.assertIn("bcb", tabela_str)
        self.assertIn("151", tabela_str)

    def test_inspecionar_status_disco(self):
        ret = inspecionar_status_disco()
        self.assertEqual(ret, 0)


if __name__ == "__main__":
    unittest.main()
