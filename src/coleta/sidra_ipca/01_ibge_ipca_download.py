import sidrapy
import pandas as pd
import time
import os

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

# Configurações do IPCA no SIDRA
# Fatiando os períodos em trimestres para não ultrapassar o limite de 50.000 valores da API
TABELAS = {
    "2938": gerar_trimestres(2006, 2011), 
    "1419": gerar_trimestres(2012, 2019),
    "7060": gerar_trimestres(2020, 2026)
}

VARIAVEIS = "63,66"
TERRITORIO = "6" 

ALIMENTOS_ALVO = [
    "Alimentação e bebidas",
    "Arroz",
    "Feijão",
    "Tomate",
    "Carnes",
    "Batata",
    "Óleo de soja",
    "Hortaliças"
]

def fetch_ipca():
    df_final = pd.DataFrame()
    
    for tabela, periodos in TABELAS.items():
        for periodo in periodos:
            print(f"Buscando Tabela {tabela} | Período {periodo}...")
            
            try:
                data = sidrapy.get_table(
                    table_code=tabela,
                    territorial_level=TERRITORIO,
                    ibge_territorial_code="all",
                    variable=VARIAVEIS,
                    period=periodo,
                    classification="315/all"
                )
                
                if not data.empty:
                    # A primeira linha contém os nomes das colunas
                    data.columns = data.iloc[0]
                    data = data[1:]
                    
                    df_final = pd.concat([df_final, data], ignore_index=True)
                
                time.sleep(0.5)
                
            except Exception as e:
                print(f"Erro ao buscar {tabela} - {periodo}: {e}")
                
    return df_final

def processar_dados(df):
    print("Processando dados e filtrando os itens de interesse...")
    
    # A API retornou colunas específicas, vamos mapeá-las corretamente
    col_mes = 'Mês (Código)'
    col_regiao = 'Município' if 'Município' in df.columns else 'Região Metropolitana'
    col_variavel = 'Variável'
    col_valor = 'Valor'
    col_item = 'Geral, grupo, subgrupo, item e subitem'
    
    if not all([c in df.columns for c in [col_mes, col_regiao, col_variavel, col_valor, col_item]]):
        print("Erro: Colunas esperadas não encontradas no retorno da API.")
        print("Colunas disponíveis:", df.columns.tolist())
        return pd.DataFrame()
        
    df_clean = df.rename(columns={
        col_mes: 'ano_mes',
        col_regiao: 'regiao',
        col_variavel: 'metrica',
        col_valor: 'valor',
        col_item: 'item'
    })
    
    # Filtrar apenas os itens de interesse usando Regex
    pattern = '|'.join(ALIMENTOS_ALVO)
    df_clean = df_clean[df_clean['item'].str.contains(pattern, case=False, na=False)]
    
    # Manter apenas as colunas essenciais
    cols_essenciais = ['ano_mes', 'regiao', 'metrica', 'item', 'valor']
    df_clean = df_clean[cols_essenciais]
    
    # Conversão de tipos
    df_clean['valor'] = pd.to_numeric(df_clean['valor'].replace('...', pd.NA).replace('-', pd.NA), errors='coerce')
    
    # Formatação de data (de 200601 para 2006-01)
    df_clean['ano_mes'] = df_clean['ano_mes'].astype(str).str[:4] + "-" + df_clean['ano_mes'].astype(str).str[4:6]
    
    # Pivotar a métrica para que Variação e Peso sejam colunas separadas
    df_pivot = df_clean.pivot_table(
        index=['ano_mes', 'regiao', 'item'], 
        columns='metrica', 
        values='valor',
        aggfunc='first'
    ).reset_index()
    
    return df_pivot

if __name__ == "__main__":
    print("Iniciando pipeline de extração do IPCA (SIDRA/IBGE)...")
    
    df_bruto = fetch_ipca()
    
    if not df_bruto.empty:
        df_final = processar_dados(df_bruto)
        
        if not df_final.empty:
            os.makedirs("data/raw/sidra_ipca", exist_ok=True)
            caminho_saida = "data/raw/sidra_ipca/ipca_alimentos_rm.parquet"
            
            df_final.to_parquet(caminho_saida, index=False)
            print(f"Sucesso! Dados salvos em: {caminho_saida}")
            print(f"Linhas geradas: {len(df_final)}")
        else:
            print("Erro no processamento. DataFrame final vazio.")
    else:
        print("Erro: Nenhum dado foi retornado pela API.")
