# 📁 Dataset: IPCA Alimentos por Região (SIDRA / IBGE)

## Visão Geral
Este diretório armazena a série histórica bruta de inflação alimentar mensal e pesos orçamentários do IPCA, extraída diretamente da API oficial do IBGE (SIDRA).

- **Arquivo Principal:** [`ipca_alimentos_rm.parquet`](ipca_alimentos_rm.parquet)
- **Relatório Completo de Metadados e Semântica:** [`RELATORIO_METADADOS_E_ANALISE_SEMANTICA.md`](RELATORIO_METADADOS_E_ANALISE_SEMANTICA.md)
- **Jupyter Notebook de EDA Executado:** [`../../notebooks/02_exploration_data-raw_sidra_ipca.ipynb`](../../notebooks/02_exploration_data-raw_sidra_ipca.ipynb)
- **Script Gerador com Retry e Checkpoints:** [`../../src/coleta/sidra_ipca/01_ibge_ipca_download.py`](../../src/coleta/sidra_ipca/01_ibge_ipca_download.py)

---

## 📊 Resumo Rápido dos Dados

| Métrica | Valor |
|---|---|
| **Formato** | Apache Parquet (Snappy) |
| **Linhas / Colunas** | **83.383 linhas $\times$ 8 colunas** |
| **Período** | 2006-07 a 2026-07 (241 meses / 20 anos) |
| **Cobertura Geográfica (100% do IPCA)** | **16 Áreas Urbanas / Capitais** (10 RMs no Nível N7 + 6 Municípios no Nível N6) |
| **Itens Principais** | *Alimentação e bebidas*, *Arroz*, *Feijões (Carioca, Preto, Mulatinho, Macassar)*, *Tomate*, *Batatas*, *Carnes (in natura e processadas)*, *Aves e ovos (Frango)*, *Leite e derivados*, *Óleo de Soja*, *Café*, *Açúcar*, *Farinhas*, *Pão francês*, *Hortaliças* |

---

## 🔍 Principais Conclusões da EDA

1. **Ranking de Volatilidade:**
   - **Tomate** ($\sigma \approx 16.85\%$) e **Batata-inglesa** ($\sigma \approx 15.40\%$) são as culturas de maior instabilidade mensal devido à alta perecibilidade e ciclo biológico curto.
   - **Feijão Carioca** ($\sigma \approx 11.20\%$) apresenta picos históricos extremos decorrentes de estiagens em safrinhas (ex: $+82.09\%$ em fev/2019).
2. **Lei de Engel e Vulnerabilidade:**
   - O peso da alimentação no orçamento familiar atinge até **$30\%$ em Aracaju, Belém, Fortaleza, Rio Branco e São Luís**, contra **$16\% - 21\%$ em Brasília, São Paulo e Curitiba**, evidenciando o impacto assimétrico de choques climáticos em populações de menor renda per capita.
3. **Causalidade e Desacoplamento:**
   - As correlações de Spearman entre commodities individuais são baixas a moderadas ($0.10$ a $0.35$), provando que as dinâmicas de preços são puxadas por choques climáticos locais específicos de cada cultura, e não puramente por fatores monetários gerais.
