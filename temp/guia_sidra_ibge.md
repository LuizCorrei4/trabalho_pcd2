# Guia de Coleta: Inflação Alimentar via SIDRA (IBGE)

Este guia documenta o processo de coleta de dados do IBGE para substituir a métrica absoluta da cesta básica por uma métrica científica de **Variação de Preços (Inflação)**.

## O Que é o IPCA no SIDRA?
O IPCA (Índice Nacional de Preços ao Consumidor Amplo) é o indicador oficial de inflação do Brasil. Em vez de medir o preço final na prateleira (ex: "R$ 20,00 o saco de arroz"), o IPCA mede a **variação mensal** (ex: "O arroz subiu 5% este mês"). 

Para cruzar com secas e chuvas, a **variação (%)** é muito melhor do que o preço absoluto, pois neutraliza diferenças de custo de vida fixo entre estados (ex: São Paulo sempre será mais caro que o Ceará em valores nominais, mas a variação nos mostra o efeito do choque climático).

## A Tabela de Ouro: Tabela 7060
No SIDRA, todos os dados do IPCA atualizados ficam na **Tabela 7060**.

Dentro dela, nós vamos filtrar:
1. **Período:** De 2015 a 2026 (ou conforme escopo).
2. **Território:** As 16 Regiões Metropolitanas e Municípios onde o IBGE coleta preços.
3. **Variável:** `63` (Variação Mensal em %) ou `2265` (Variação acumulada em 12 meses em %).
4. **Geral, Grupo, Subgrupo, Item e Subitem:** Aqui é onde a mágica acontece. Nós não pegamos a inflação geral do Brasil. Nós pegamos especificamente o grupo **"1. Alimentação e bebidas"** (Código `7169`). Se quisermos descer ao nível do produto, podemos puxar os códigos exatos do Arroz, Feijão, Tomate, etc.

## Como Coletar via Python (Sem PDFs!)

A comunidade Python tem um pacote maravilhoso chamado `sidrapy` que conversa com a API do IBGE perfeitamente.

```python
# Instalação: pip install sidrapy pandas
import sidrapy
import pandas as pd

# Exemplo: Puxando a inflação mensal (variável 63) do grupo "Alimentação" (7169)
# para todas as regiões metropolitanas (território 6) no ano de 2023.
dados_ibge = sidrapy.get_table(
    table_code="7060",
    territorial_level="6",
    ibge_territorial_code="all",
    variable="63",
    period="202301-202312",
    classification="315/7169" # 315 é a classificação de produtos, 7169 é Alimentação
)

# A primeira linha da resposta vem como cabeçalho da API
df = dados_ibge
df.columns = df.iloc[0]
df = df[1:]

# O dataframe agora tem colunas como:
# 'Mês' (ex: janeiro 2023), 'Região Metropolitana', 'Variação %'
print(df.head())
```

## Como isso se conecta com o resto do projeto?
Quando vocês forem construir os painéis, vocês terão a **Anomalia de Chuva do INMET (ex: -50mm)** e a **Variação do IPCA-Alimentação (ex: +3.2%)** para a mesma região no mesmo mês. Isso gera gráficos de dispersão perfeitos e os algoritmos (XGBoost/Random Forest) vão aprender exatamente qual *lag* temporal da seca causa o pico inflacionário.
