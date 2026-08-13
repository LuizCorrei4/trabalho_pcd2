# Dicionário de Dados: IPCA de Alimentos (SIDRA)

## Sobre o Arquivo
O arquivo `ipca_alimentos_rm.parquet` contém a série histórica da inflação alimentar oficial do Brasil, medida pelo IBGE. Ele foi projetado para medir a **volatilidade** (choques) nos preços dos alimentos devido a fatores climáticos e macroeconômicos.

Diferente do valor de uma "cesta básica", este dataset traz a variação percentual, permitindo uma correlação muito mais científica com os choques de temperatura e precipitação das regiões produtoras.

## Como os Dados Foram Gerados?
Os dados não foram raspados ou baixados de PDFs. Eles foram extraídos da API oficial do IBGE (SIDRA) através do script [`01_ibge_ipca_download.py`](../../src/coleta/sidra_ipca/01_ibge_ipca_download.py).

**Processo de Extração:**
1. **Unificação Histórica:** Como o IBGE revisa os pesos da inflação (POF) periodicamente, a série oficial está dividida em 3 tabelas diferentes na base deles. O script puxa e unifica as tabelas **2938** (2006-2011), **1419** (2012-2019) e **7060** (2020+).
2. **Paginação Inteligente:** A API do IBGE bloqueia requisições maiores que 50.000 valores. Para contornar isso, a requisição foi desenhada para buscar os dados em blocos trimestrais para cada ano.
3. **Limpeza Automática:** O script usa regex para buscar apenas palavras-chave relevantes (`Arroz`, `Feijão`, `Tomate`, `Carnes`, `Alimentação e bebidas`, etc.), converte as colunas para o tipo Float e transforma datas para o formato ISO `YYYY-MM`.

## Dicionário de Variáveis (Schema do Parquet)

Ao carregar o arquivo (`pd.read_parquet`), você encontrará as seguintes colunas principais:

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `ano_mes` | `string` | Data no formato `YYYY-MM` (mês de referência da inflação). |
| `regiao` | `string` | Nome da Região Metropolitana ou Município (ex: "São Paulo", "Fortaleza") onde o IBGE monitora os preços. |
| `item` | `string` | Categoria geral (ex: "1. Alimentação e bebidas") ou produto individual ("Arroz", "Tomate"). |
| `IPCA - Variação mensal (%)` * | `float64` | O percentual de alta ou queda do item naquele mês exato. É o principal termômetro do choque de preço. |
| `IPCA - Peso mensal (%)` * | `float64` | Qual fatia do orçamento da família brasileira esse item ocupou naquele mês. Mostra o impacto real no custo de vida. |

*\*Nota: Os nomes exatos das colunas de métrica podem variar ligeiramente dependendo da string textual retornada pela API do IBGE durante o ano, mas sempre representarão "Variação" e "Peso".*

## Como Usar no Python
```python
import pandas as pd

# Carregar os dados
df = pd.read_parquet("data/raw/sidra_ipca/ipca_alimentos_rm.parquet")

# Exemplo de Análise: Qual mês o Tomate mais subiu em SP?
df_tomate = df[(df['item'].str.contains("Tomate")) & (df['regiao'].str.contains("São Paulo"))]
print(df_tomate.sort_values(by="IPCA - Variação mensal (%)", ascending=False).head())
```
