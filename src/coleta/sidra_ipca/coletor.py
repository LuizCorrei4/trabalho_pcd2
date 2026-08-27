"""Coletor oficial do IPCA de Alimentos via API do SIDRA / IBGE.

Suporta controle granular de sobrescrita (skip, force, update, backup),
checkpoints em formato parquet, sistema de retentativas com espera exponencial,
logging transacional em CSV e interface padronizada com o Orquestrador.
"""

from __future__ import annotations

import logging
import os
import re
import time
from pathlib import Path
from typing import Any

import pandas as pd
import sidrapy

from ... import config
from ...logging_config import BackupManager, DownloadLogger, get_logger, prompt_confirmacao
from ..base import ColetaResult, calcular_tamanho_caminho

DESTINO_FINAL = config.DATA_RAW / "sidra_ipca" / "ipca_alimentos_rm.parquet"
DESTINO_INTERIM = config.DATA_INTERIM / "ipca_alimentos_rm.parquet"
DIR_CHUNKS = config.DATA_RAW / "sidra_ipca" / "chunks"

NIVEIS_TERRITORIAIS = ["6", "7"]
VARIAVEIS = "63,66"

ALIMENTOS_ALVO = [
    "Alimentação e bebidas", "Arroz", "Feijão", "Tomate", "Carnes",
    "Batata", "Óleo de soja", "Hortaliças", "Café", "Açúcar",
    "Farinha", "Leite", "Pão francês", "Frango", "Ovos"
]

MAPEAMENTO_REGIOES = {
    'Brasília - DF': {'capital': 'Brasília', 'sigla_uf': 'DF', 'tipo_cobertura': 'Município'},
    'Goiânia - GO': {'capital': 'Goiânia', 'sigla_uf': 'GO', 'tipo_cobertura': 'Município'},
    'Campo Grande - MS': {'capital': 'Campo Grande', 'sigla_uf': 'MS', 'tipo_cobertura': 'Município'},
    'Rio Branco - AC': {'capital': 'Rio Branco', 'sigla_uf': 'AC', 'tipo_cobertura': 'Município'},
    'São Luís - MA': {'capital': 'São Luís', 'sigla_uf': 'MA', 'tipo_cobertura': 'Município'},
    'Aracaju - SE': {'capital': 'Aracaju', 'sigla_uf': 'SE', 'tipo_cobertura': 'Município'},
    'São Paulo - SP': {'capital': 'São Paulo', 'sigla_uf': 'SP', 'tipo_cobertura': 'Região Metropolitana'},
    'Rio de Janeiro - RJ': {'capital': 'Rio de Janeiro', 'sigla_uf': 'RJ', 'tipo_cobertura': 'Região Metropolitana'},
    'Belo Horizonte - MG': {'capital': 'Belo Horizonte', 'sigla_uf': 'MG', 'tipo_cobertura': 'Região Metropolitana'},
    'Curitiba - PR': {'capital': 'Curitiba', 'sigla_uf': 'PR', 'tipo_cobertura': 'Região Metropolitana'},
    'Porto Alegre - RS': {'capital': 'Porto Alegre', 'sigla_uf': 'RS', 'tipo_cobertura': 'Região Metropolitana'},
    'Salvador - BA': {'capital': 'Salvador', 'sigla_uf': 'BA', 'tipo_cobertura': 'Região Metropolitana'},
    'Recife - PE': {'capital': 'Recife', 'sigla_uf': 'PE', 'tipo_cobertura': 'Região Metropolitana'},
    'Fortaleza - CE': {'capital': 'Fortaleza', 'sigla_uf': 'CE', 'tipo_cobertura': 'Região Metropolitana'},
    'Belém - PA': {'capital': 'Belém', 'sigla_uf': 'PA', 'tipo_cobertura': 'Região Metropolitana'},
    'Grande Vitória - ES': {'capital': 'Vitória', 'sigla_uf': 'ES', 'tipo_cobertura': 'Região Metropolitana'}
}


def gerar_trimestres(ano_inicio: int, ano_fim: int) -> list[str]:
    """Gera códigos trimestrais no formato AAAAMM-AAAAMM para consulta na API."""
    periodos = []
    for ano in range(ano_inicio, ano_fim + 1):
        periodos.extend([
            f"{ano}01-{ano}03",
            f"{ano}04-{ano}06",
            f"{ano}07-{ano}09",
            f"{ano}10-{ano}12"
        ])
    return periodos


def obter_tabelas_por_periodo(ano_inicio: int = 2006, ano_fim: int = 2026) -> dict[str, list[str]]:
    """Gera mapa de tabela -> períodos ajustado para o recorte de anos solicitado."""
    tabelas_def = {
        "2938": (2006, 2011),
        "1419": (2012, 2019),
        "7060": (2020, 2026),
    }
    resultado = {}
    for cod_tab, (ini_tab, fim_tab) in tabelas_def.items():
        ini = max(ano_inicio, ini_tab)
        fim = min(ano_fim, fim_tab)
        if ini <= fim:
            resultado[cod_tab] = gerar_trimestres(ini, fim)
    return resultado


def baixar_chunk_sidra(
    tabela: str,
    periodo: str,
    nivel: str,
    arquivo_chunk: Path,
    download_logger: DownloadLogger | None = None,
    logger: logging.Logger | None = None,
    max_tentativas: int = 5,
) -> tuple[pd.DataFrame | None, str]:
    """Baixa um chunk específico da API do SIDRA com retentativas e registro transacional."""
    url_simulada = f"https://apisidra.ibge.gov.br/values/t/{tabela}/n{nivel}/all/v/{VARIAVEIS}/p/{periodo}/c315/all"
    t0 = time.perf_counter()
    ultimo_erro = ""

    for tentativa in range(1, max_tentativas + 1):
        try:
            data = sidrapy.get_table(
                table_code=tabela,
                territorial_level=nivel,
                ibge_territorial_code="all",
                variable=VARIAVEIS,
                period=periodo,
                classification="315/all"
            )

            duracao_ms = (time.perf_counter() - t0) * 1000

            if not data.empty and len(data) > 1:
                data.columns = data.iloc[0]
                data = data[1:].copy()

                col_localidade = next(
                    (c for c in data.columns if ('Região Metropolitana' in str(c) or 'Município' in str(c)) and 'Código' not in str(c)),
                    None
                )
                if col_localidade:
                    data['regiao_padronizada'] = data[col_localidade]
                else:
                    data['regiao_padronizada'] = data.iloc[:, 6]

                arquivo_chunk.parent.mkdir(parents=True, exist_ok=True)
                data.to_parquet(arquivo_chunk, index=False)
                tamanho_bytes = arquivo_chunk.stat().st_size

                if download_logger:
                    download_logger.registrar(
                        identificador_chunk=arquivo_chunk.name,
                        url=url_simulada,
                        status_http=200,
                        tamanho_bytes=tamanho_bytes,
                        duracao_ms=duracao_ms,
                        tentativas_retry=tentativa,
                        sucesso=True,
                    )
                time.sleep(0.3)
                return data, ""

            # Se veio vazio mas sem erro
            if download_logger:
                download_logger.registrar(
                    identificador_chunk=arquivo_chunk.name,
                    url=url_simulada,
                    status_http=200,
                    tamanho_bytes=0,
                    duracao_ms=duracao_ms,
                    tentativas_retry=tentativa,
                    sucesso=True,
                    mensagem_erro="retorno vazio da API",
                )
            return None, "retorno vazio"

        except Exception as e:
            ultimo_erro = str(e)
            duracao_ms = (time.perf_counter() - t0) * 1000
            if tentativa == max_tentativas:
                if download_logger:
                    download_logger.registrar(
                        identificador_chunk=arquivo_chunk.name,
                        url=url_simulada,
                        status_http=500,
                        tamanho_bytes=0,
                        duracao_ms=duracao_ms,
                        tentativas_retry=tentativa,
                        sucesso=False,
                        mensagem_erro=ultimo_erro,
                    )
                if logger:
                    logger.error(
                        f"Falha crítica ao baixar chunk {arquivo_chunk.name} "
                        f"após {max_tentativas} tentativas: {e}"
                    )
                return None, ultimo_erro

            espera = 2 ** tentativa
            if logger:
                logger.warning(
                    f"Erro de conexão no chunk {arquivo_chunk.name} "
                    f"(Tentativa {tentativa}/{max_tentativas}). Esperando {espera}s... Erro: {e}"
                )
            time.sleep(espera)

    return None, ultimo_erro


def processar_e_estruturar_dados(df: pd.DataFrame, logger: logging.Logger | None = None) -> pd.DataFrame:
    """Padroniza, limpa e enriquece os dados brutos com metadados geográficos."""
    if df.empty:
        return pd.DataFrame()

    col_mes = next((c for c in df.columns if 'Mês' in str(c) and 'Código' in str(c)), None)
    col_variavel = next((c for c in df.columns if 'Variável' in str(c) and 'Código' not in str(c)), None)
    col_valor = next((c for c in df.columns if 'Valor' in str(c)), None)
    col_item = next((c for c in df.columns if 'Geral, grupo, subgrupo, item e subitem' in str(c) and 'Código' not in str(c)), None)
    col_regiao = 'regiao_padronizada'

    if not all([col_mes, col_variavel, col_valor, col_item, col_regiao]):
        if logger:
            logger.error("Colunas essenciais não identificadas na estruturação do IPCA.")
        return pd.DataFrame()

    df_clean = df.rename(columns={
        col_mes: 'ano_mes', col_regiao: 'regiao', col_variavel: 'metrica',
        col_valor: 'valor', col_item: 'item'
    })

    pattern = '|'.join(ALIMENTOS_ALVO)
    df_clean = df_clean[df_clean['item'].str.contains(pattern, case=False, na=False)].copy()
    df_clean['item'] = df_clean['item'].str.replace('))', ')', regex=False).str.strip()

    MARCADORES = ['-', '...', '..', 'X', '']
    valor_texto = df_clean['valor'].astype(str).str.strip()
    df_clean['valor'] = pd.to_numeric(
        valor_texto.where(~valor_texto.isin(MARCADORES)),
        errors='coerce'
    )

    df_clean['ano_mes'] = df_clean['ano_mes'].astype(str).str[:4] + "-" + df_clean['ano_mes'].astype(str).str[4:6]

    df_pivot = df_clean.pivot_table(
        index=['ano_mes', 'regiao', 'item'], columns='metrica', values='valor', aggfunc='first'
    ).reset_index()

    cols_rename_metricas = {}
    for col in df_pivot.columns:
        if 'Variação mensal' in str(col):
            cols_rename_metricas[col] = 'IPCA - Variação mensal'
        elif 'Peso mensal' in str(col):
            cols_rename_metricas[col] = 'IPCA - Peso mensal'

    df_pivot = df_pivot.rename(columns=cols_rename_metricas)

    df_pivot['capital'] = df_pivot['regiao'].apply(lambda x: MAPEAMENTO_REGIOES.get(x, {}).get('capital', str(x).split(' - ')[0]))
    df_pivot['sigla_uf'] = df_pivot['regiao'].apply(lambda x: MAPEAMENTO_REGIOES.get(x, {}).get('sigla_uf', str(x).split(' - ')[-1] if ' - ' in str(x) else ''))
    df_pivot['tipo_cobertura'] = df_pivot['regiao'].apply(lambda x: MAPEAMENTO_REGIOES.get(x, {}).get('tipo_cobertura', 'Outro'))

    cols_ordenadas = ['ano_mes', 'regiao', 'capital', 'sigla_uf', 'tipo_cobertura', 'item', 'IPCA - Peso mensal', 'IPCA - Variação mensal']
    cols_finais = [c for c in cols_ordenadas if c in df_pivot.columns]
    df_final = df_pivot[cols_finais].sort_values(by=['ano_mes', 'sigla_uf', 'item']).reset_index(drop=True)

    return df_final


def executar_coleta(
    overwrite: str = 'skip',  # 'skip' | 'force' | 'update' | 'backup'
    ano_inicio: int | None = None,
    ano_fim: int | None = None,
    logger: logging.Logger | None = None,
    download_logger: DownloadLogger | None = None,
    interativo: bool = False,
) -> ColetaResult:
    """Executa a coleta do IPCA Alimentos via API do SIDRA conforme o contrato unificado."""
    log = logger or get_logger("sidra_ipca")
    t_inicio = time.perf_counter()

    ano_ini = ano_inicio or 2006
    ano_f = ano_fim or 2026

    DIR_CHUNKS.mkdir(parents=True, exist_ok=True)
    DESTINO_FINAL.parent.mkdir(parents=True, exist_ok=True)

    dl_logger = download_logger or DownloadLogger(config.DATA_RAW / "sidra_ipca")

    # Tratamento Interativo
    politica = overwrite.lower()
    if interativo and DESTINO_FINAL.exists():
        escolha = prompt_confirmacao(DESTINO_FINAL, log)
        if escolha == "cancel":
            return ColetaResult(
                fonte="sidra_ipca",
                status="PULADO",
                acao_executada="PULADO_PELO_USUARIO",
                duracao_segundos=round(time.perf_counter() - t_inicio, 2),
                arquivo_saida=str(DESTINO_FINAL.relative_to(config.RAIZ)),
            )
        politica = escolha

    # Verificação rápida de skip (se o arquivo final já existe e cobre tudo)
    if politica == "skip" and DESTINO_FINAL.exists() and ano_inicio is None and ano_fim is None:
        try:
            df_existente = pd.read_parquet(DESTINO_FINAL)
            tamanho = DESTINO_FINAL.stat().st_size
            log.info(f"Arquivo final já existe ({len(df_existente):,} linhas). Pulando coleta (skip).")
            return ColetaResult(
                fonte="sidra_ipca",
                status="SUCESSO",
                acao_executada="REUTILIZADO",
                duracao_segundos=round(time.perf_counter() - t_inicio, 2),
                linhas=len(df_existente),
                colunas=len(df_existente.columns),
                arquivo_saida=str(DESTINO_FINAL.relative_to(config.RAIZ)),
                tamanho_bytes=tamanho,
                chunks_totais=len(list(DIR_CHUNKS.glob("*.parquet"))),
                chunks_reaproveitados=len(list(DIR_CHUNKS.glob("*.parquet"))),
            )
        except Exception as e:
            log.warning(f"Arquivo existente corrompido ({e}). Forçando reprocessamento...")

    tabelas_periodos = obter_tabelas_por_periodo(ano_ini, ano_f)
    total_requisicoes = sum(len(p) for p in tabelas_periodos.values()) * len(NIVEIS_TERRITORIAIS)

    log.info(
        f"Iniciando coleta IPCA Alimentos ({ano_ini}-{ano_f}): "
        f"{total_requisicoes} blocos planejados (política: {politica})."
    )

    df_lista: list[pd.DataFrame] = []
    chunks_baixados = 0
    chunks_reaproveitados = 0
    erros: list[str] = []
    req_atual = 0

    for tabela, periodos in tabelas_periodos.items():
        for periodo in periodos:
            for nivel in NIVEIS_TERRITORIAIS:
                req_atual += 1
                tipo_str = "N6 (Municípios)" if nivel == "6" else "N7 (RMs)"
                arquivo_chunk = DIR_CHUNKS / f"ipca_tab{tabela}_{periodo}_N{nivel}.parquet"

                deve_reaproveitar = (
                    arquivo_chunk.exists()
                    and politica in ("skip", "update", "backup")
                )

                if deve_reaproveitar:
                    try:
                        chunk_df = pd.read_parquet(arquivo_chunk)
                        df_lista.append(chunk_df)
                        chunks_reaproveitados += 1
                        log.debug(f"[{req_atual:03d}/{total_requisicoes:03d}] {arquivo_chunk.name} -> Reutilizado.")
                        continue
                    except Exception as e:
                        log.warning(f"Chunk {arquivo_chunk.name} corrompido ({e}). Baixando novamente...")

                # Caso force ou chunk ausente
                log.info(f"[{req_atual:03d}/{total_requisicoes:03d}] Tabela {tabela} | {periodo} | {tipo_str} -> Baixando...")
                chunk_df, erro = baixar_chunk_sidra(
                    tabela=tabela,
                    periodo=periodo,
                    nivel=nivel,
                    arquivo_chunk=arquivo_chunk,
                    download_logger=dl_logger,
                    logger=log,
                )

                if chunk_df is not None and not chunk_df.empty:
                    df_lista.append(chunk_df)
                    chunks_baixados += 1
                elif erro:
                    erros.append(f"Tabela {tabela} {periodo} N{nivel}: {erro}")

    if not df_lista:
        duracao = time.perf_counter() - t_inicio
        log.error("Nenhum dado retornado pela API do SIDRA para o IPCA.")
        return ColetaResult(
            fonte="sidra_ipca",
            status="FALHA",
            acao_executada="FALHA_DOWNLOAD",
            duracao_segundos=round(duracao, 2),
            chunks_totais=total_requisicoes,
            chunks_baixados=chunks_baixados,
            chunks_reaproveitados=chunks_reaproveitados,
            erros=erros or ["Nenhum dado coletado"],
        )

    log.info("Concatenando e estruturando os chunks coletados...")
    df_bruto = pd.concat(df_lista, ignore_index=True)
    df_final = processar_e_estruturar_dados(df_bruto, log)

    if df_final.empty:
        duracao = time.perf_counter() - t_inicio
        log.error("Falha na estruturação: DataFrame final do IPCA ficou vazio.")
        return ColetaResult(
            fonte="sidra_ipca",
            status="FALHA",
            acao_executada="FALHA_PROCESSAMENTO",
            duracao_segundos=round(duracao, 2),
            chunks_totais=total_requisicoes,
            chunks_baixados=chunks_baixados,
            chunks_reaproveitados=chunks_reaproveitados,
            erros=erros or ["DataFrame final vazio após estruturação"],
        )

    # Gravação com proteção de backup
    usar_backup = politica == "backup"
    with BackupManager.gerenciar_com_seguranca(DESTINO_FINAL, ativar_backup=usar_backup, logger=log):
        DESTINO_FINAL.parent.mkdir(parents=True, exist_ok=True)
        df_final.to_parquet(DESTINO_FINAL, index=False)
        # Espelha também para interim para compatibilidade
        DESTINO_INTERIM.parent.mkdir(parents=True, exist_ok=True)
        df_final.to_parquet(DESTINO_INTERIM, index=False)

    tamanho = DESTINO_FINAL.stat().st_size
    duracao = time.perf_counter() - t_inicio

    acao = "BAIXADO_NOVO" if chunks_baixados > 0 and chunks_reaproveitados == 0 else (
        "ATUALIZADO" if chunks_baixados > 0 else (
            "BACKUP_CRIADO" if usar_backup else "REUTILIZADO"
        )
    )

    status = "AVISO" if erros else "SUCESSO"
    log.info(
        f"IPCA consolidado com sucesso: {len(df_final):,} linhas, "
        f"{len(df_final.columns)} colunas ({tamanho / 1e6:.2f} MB)."
    )

    return ColetaResult(
        fonte="sidra_ipca",
        status=status,
        acao_executada=acao,
        duracao_segundos=round(duracao, 2),
        linhas=len(df_final),
        colunas=len(df_final.columns),
        arquivo_saida=str(DESTINO_FINAL.relative_to(config.RAIZ)),
        tamanho_bytes=tamanho,
        chunks_totais=total_requisicoes,
        chunks_baixados=chunks_baixados,
        chunks_reaproveitados=chunks_reaproveitados,
        erros=erros,
        detalhes={
            "periodo_min": str(df_final['ano_mes'].min()),
            "periodo_max": str(df_final['ano_mes'].max()),
            "areas_cobertas": int(df_final['regiao'].nunique()),
            "itens_cobertos": int(df_final['item'].nunique()),
        }
    )
