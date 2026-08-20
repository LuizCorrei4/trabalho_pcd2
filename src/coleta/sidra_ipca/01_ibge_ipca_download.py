"""
Script de Coleta Oficial do IPCA de Alimentos via API do SIDRA / IBGE
Atualizado com Checkpoints e Sistema de Retry (Tolerância a Falhas)
"""

import sidrapy
import pandas as pd
import time
import os
import re

def gerar_trimestres(ano_inicio, ano_fim):
    periodos = []
    for ano in range(ano_inicio, ano_fim + 1):
        periodos.extend([
            f"{ano}01-{ano}03",
            f"{ano}04-{ano}06",
            f"{ano}07-{ano}09",
            f"{ano}10-{ano}12"
        ])
    return periodos

# Configurações de Tabelas e Períodos do SIDRA
TABELAS = {
    "2938": gerar_trimestres(2006, 2011), 
    "1419": gerar_trimestres(2012, 2019),
    "7060": gerar_trimestres(2020, 2026)
}

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

def fetch_ipca_completo():
    """Baixa os dados com sistema de retentativas e salva chunks para evitar perda de dados."""
    
    # Criar pasta para salvar as partes (chunks)
    pasta_chunks = "data/raw/sidra_ipca/chunks"
    os.makedirs(pasta_chunks, exist_ok=True)
    
    df_lista = [] # Lista para guardar os dataframes em memória e juntar no final
    total_requisicoes = sum(len(p) for p in TABELAS.values()) * len(NIVEIS_TERRITORIAIS)
    req_atual = 0

    print(f"Iniciando coleta de {total_requisicoes} blocos na API do SIDRA...")

    for tabela, periodos in TABELAS.items():
        for periodo in periodos:
            for nivel in NIVEIS_TERRITORIAIS:
                req_atual += 1
                tipo_str = "Municípios (N6)" if nivel == "6" else "RMs (N7)"
                
                # Nome do arquivo de checkpoint
                arquivo_chunk = f"{pasta_chunks}/ipca_tab{tabela}_{periodo}_N{nivel}.parquet"
                
                # 1. VERIFICA SE JÁ FOI BAIXADO
                if os.path.exists(arquivo_chunk):
                    print(f"[{req_atual:03d}/{total_requisicoes:03d}] Tabela {tabela} | {periodo} | {tipo_str} -> Já baixado (Pulando).")
                    df_lista.append(pd.read_parquet(arquivo_chunk))
                    continue
                
                print(f"[{req_atual:03d}/{total_requisicoes:03d}] Tabela {tabela} | {periodo} | {tipo_str} -> Baixando...")

                # 2. SISTEMA DE RETRY (TENTA ATÉ 5 VEZES)
                max_tentativas = 5
                sucesso = False
                
                for tentativa in range(max_tentativas):
                    try:
                        data = sidrapy.get_table(
                            table_code=tabela,
                            territorial_level=nivel,
                            ibge_territorial_code="all",
                            variable=VARIAVEIS,
                            period=periodo,
                            classification="315/all"
                        )

                        if not data.empty and len(data) > 1:
                            data.columns = data.iloc[0]
                            data = data[1:].copy()

                            col_localidade = next((c for c in data.columns if ('Região Metropolitana' in str(c) or 'Município' in str(c)) and 'Código' not in str(c)), None)
                            if col_localidade:
                                data['regiao_padronizada'] = data[col_localidade]
                            else:
                                data['regiao_padronizada'] = data.iloc[:, 6]

                            # SALVA O CHUNK NO DISCO LOGO APÓS BAIXAR E TRATAR
                            data.to_parquet(arquivo_chunk, index=False)
                            df_lista.append(data)

                        sucesso = True
                        time.sleep(0.5) # Respeitar limites do servidor
                        break # Se deu certo, sai do loop de tentativas

                    except Exception as e:
                        tempo_espera = 2 ** tentativa # Ex: 1s, 2s, 4s, 8s...
                        print(f"    ⚠️ Erro de conexão (Tentativa {tentativa+1}/{max_tentativas}). Esperando {tempo_espera}s para tentar de novo... Erro: {e}")
                        time.sleep(tempo_espera)

                if not sucesso:
                    print(f" ❌ FALHA CRÍTICA: Não foi possível baixar Tabela {tabela} | {periodo} | N{nivel} após {max_tentativas} tentativas.")

    # Juntar todas as partes
    if df_lista:
        return pd.concat(df_lista, ignore_index=True)
    else:
        return pd.DataFrame()

def processar_e_estruturar_dados(df):
    """Padroniza, limpa e enriquece os dados brutos com metadados geográficos."""
    print("\nProcessando e estruturando os dados coletados...")

    col_mes = next((c for c in df.columns if 'Mês' in str(c) and 'Código' in str(c)), None)
    col_variavel = next((c for c in df.columns if 'Variável' in str(c) and 'Código' not in str(c)), None)
    col_valor = next((c for c in df.columns if 'Valor' in str(c)), None)
    col_item = next((c for c in df.columns if 'Geral, grupo, subgrupo, item e subitem' in str(c) and 'Código' not in str(c)), None)
    col_regiao = 'regiao_padronizada'

    if not all([col_mes, col_variavel, col_valor, col_item, col_regiao]):
        print("❌ Erro: Colunas essenciais não identificadas.")
        print("Colunas disponíveis no DataFrame bruto:", df.columns.tolist())
        return pd.DataFrame()

    df_clean = df.rename(columns={
        col_mes: 'ano_mes', col_regiao: 'regiao', col_variavel: 'metrica',
        col_valor: 'valor', col_item: 'item'
    })

    pattern = '|'.join(ALIMENTOS_ALVO)
    df_clean = df_clean[df_clean['item'].str.contains(pattern, case=False, na=False)].copy()
    df_clean['item'] = df_clean['item'].str.replace('))', ')', regex=False).str.strip()

    df_clean['valor'] = pd.to_numeric(
        df_clean['valor'].astype(str).str.replace('...', '', regex=False).str.replace('-', '', regex=False),
        errors='coerce'
    )

    df_clean['ano_mes'] = df_clean['ano_mes'].astype(str).str[:4] + "-" + df_clean['ano_mes'].astype(str).str[4:6]

    df_pivot = df_clean.pivot_table(
        index=['ano_mes', 'regiao', 'item'], columns='metrica', values='valor', aggfunc='first'
    ).reset_index()

    cols_rename_metricas = {}
    for col in df_pivot.columns:
        if 'Variação mensal' in str(col): cols_rename_metricas[col] = 'IPCA - Variação mensal'
        elif 'Peso mensal' in str(col): cols_rename_metricas[col] = 'IPCA - Peso mensal'

    df_pivot = df_pivot.rename(columns=cols_rename_metricas)

    df_pivot['capital'] = df_pivot['regiao'].apply(lambda x: MAPEAMENTO_REGIOES.get(x, {}).get('capital', x.split(' - ')[0]))
    df_pivot['sigla_uf'] = df_pivot['regiao'].apply(lambda x: MAPEAMENTO_REGIOES.get(x, {}).get('sigla_uf', x.split(' - ')[-1] if ' - ' in x else ''))
    df_pivot['tipo_cobertura'] = df_pivot['regiao'].apply(lambda x: MAPEAMENTO_REGIOES.get(x, {}).get('tipo_cobertura', 'Outro'))

    cols_ordenadas = ['ano_mes', 'regiao', 'capital', 'sigla_uf', 'tipo_cobertura', 'item', 'IPCA - Peso mensal', 'IPCA - Variação mensal']
    cols_finais = [c for c in cols_ordenadas if c in df_pivot.columns]
    df_final = df_pivot[cols_finais].sort_values(by=['ano_mes', 'sigla_uf', 'item']).reset_index(drop=True)

    return df_final

if __name__ == "__main__":
    print("=" * 70)
    print("INICIANDO COLETA AMPLIADA DO IPCA ALIMENTOS (TODAS AS 16 ÁREAS URBANAS)")
    print("=" * 70)

    df_bruto = fetch_ipca_completo()

    if not df_bruto.empty:
        df_final = processar_e_estruturar_dados(df_bruto)

        if not df_final.empty:
            caminho_saida = "data/raw/sidra_ipca/ipca_alimentos_rm.parquet"
            df_final.to_parquet(caminho_saida, index=False)
            
            print("=" * 70)
            print(f"✅ SUCESSO! Dataset consolidado salvo em: {caminho_saida}")
            print(f"📊 Total de Linhas: {len(df_final):,}")
            print("=" * 70)
        else:
            print("❌ Erro no processamento: DataFrame final ficou vazio.")
    else:
        print("❌ Erro: Nenhum dado retornado pela API do SIDRA.")
