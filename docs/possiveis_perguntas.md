# ⭐ Proposta 1 (RECOMENDADA): O que realmente move o preço da comida no Brasil? Anomalias climáticas, custo logístico e macroeconomia na volatilidade regional da cesta básica

### Motivação
O brasileiro sente no bolso quando a comida encarece, mas a narrativa pública simplifica: "a culpa é da seca" ou "a culpa é do dólar". A realidade é multifatorial e varia regionalmente. **Esta proposta investiga qual fator — clima na origem, custo de transporte ou pressão macroeconômica — domina a formação de preço em cada região do país, e em que momentos.**

### Por que esta é a proposta recomendada
- **Dados predominantemente tabulares**, disponíveis via APIs públicas bem documentadas. Não exige processamento raster, shapefiles complexos ou parsing de arquivos proprietários.
- **ETL estimado em 2–3 semanas**, liberando mais tempo para a parte que o professor mais valoriza (exploração e interpretação).
- **O grupo já teve dificuldades sérias com DataSUS** (esquistossomose). Esta proposta evita completamente essa fonte.
- **Impacto comunicacional altíssimo**: "O que pesa mais no preço da comida — a seca ou o diesel?" é uma pergunta que qualquer pessoa entende.

### Fontes de Dados Detalhadas (5 fontes heterogêneas)

| # | Fonte | Tipo | Granularidade | Formato | Acesso |
|---|---|---|---|---|---|
| 1 | **IBGE — SIDRA (IPCA/SNIPC)** | Preços ao consumidor | Mensal, por RM (16 regiões metropolitanas) | API REST → JSON/CSV | `https://sidra.ibge.gov.br/` — Tabelas 7060, 1419 |
| 2 | **IBGE — SIDRA (PAM)** | Produção Agrícola Municipal | Anual, por município | API REST → JSON/CSV | `https://sidra.ibge.gov.br/` — Tabela 5457 |
| 3 | **INMET (BDMEP)** | Estações meteorológicas | Diária/Horária, por estação | API REST → JSON / CSV | `https://portal.inmet.gov.br/` — API pública |
| 4 | **ANP** | Preço de combustíveis | Semanal/Mensal, por estado/município | CSV direto | `https://www.gov.br/anp/` — Série histórica de preços |
| 5 | **ESALQ/CEPEA (USP)** | Indicadores agropecuários e frete | Diário/Semanal | Planilhas XLS/CSV | `https://www.cepea.esalq.usp.br/` |

**Fonte auxiliar (LLM):**
- **Atas do COPOM** (Banco Central) — PDFs textuais, ~8 por ano
- **Relatórios de Safra da CONAB** — PDFs mensais com análise qualitativa

### Justificativa Qualitativa das Fontes

1. **IPCA/SNIPC** é o indicador oficial de inflação do Brasil, coletado metodologicamente pelo IBGE com amostragem representativa. É a variável dependente natural.
2. **PAM** complementa ao fornecer o lado da oferta: quanto se produziu e com que rendimento. Permite diferenciar alta de preço por escassez real vs. especulação.
3. **INMET** fornece a dimensão climática: precipitação acumulada, temperatura máxima e número de dias sem chuva, que são os *drivers* físicos da produtividade agrícola.
4. **ANP** captura o custo logístico — o diesel é o sangue do transporte rodoviário brasileiro, responsável por >60% do frete de alimentos.
5. **CEPEA** traz os preços na origem (porteira da fazenda), permitindo medir a "margem de intermediação": quanto do preço final é produção vs. logística vs. tributação.

### Variáveis Esperadas Após Agregação (~40–60 variáveis)

**Variáveis climáticas (por região produtora, com lags de 1/3/6/12 meses):**
- Precipitação acumulada mensal (mm)
- Anomalia de precipitação (desvio da média histórica 30 anos)
- Temperatura máxima média mensal (°C)
- Número de dias consecutivos sem chuva (dias de seca)
- Índice de aridez simplificado (precipitação / evapotranspiração)
- ENSO Index (El Niño / La Niña — proxy da NOAA)

**Variáveis de produção agrícola (anuais, interpoladas para mensal):**
- Área plantada por cultura (hectares)
- Área colhida / Área plantada (razão de perda)
- Rendimento médio por hectare (kg/ha)
- Produção total (toneladas)
- Variação interanual da produtividade (%)

**Variáveis de custo logístico (mensais, por estado):**
- Preço médio do diesel (R$/litro)
- Variação mensal do diesel (%)
- Índice de frete rodoviário (CEPEA, R$/tonelada/km)
- Distância média ponderada do polo produtor à região metropolitana consumidora

**Variáveis macroeconômicas (mensais, nacionais):**
- Taxa de câmbio USD/BRL (média mensal)
- Taxa SELIC (meta)
- Índice de confiança do consumidor (FGV)
- Preço internacional de commodities (soja, milho — CBOT/CME)

**Variável dependente:**
- IPCA — Grupo Alimentação e Bebidas (variação mensal, por RM)
- Preço médio de itens-chave: arroz, feijão, carne bovina, leite, tomate (SNIPC)

### Metodologia Detalhada (Passo a Passo)

#### Fase 1 — Coleta e Ingestão (Semanas 1–3)
1. Escrever scripts em `src/` para download automatizado via APIs (SIDRA, INMET, ANP).
2. Armazenar dados brutos em `data/raw/` com nomeação padronizada: `{fonte}_{variavel}_{periodo}.csv`.
3. Documentar cada fonte em `docs/fontes_de_dados.md` com: URL, método de coleta, licença, período coberto, limitações conhecidas.

#### Fase 2 — Limpeza e Qualidade (Semanas 3–5)
1. **Inventário de dados faltantes** por variável e por período: tabelas de completude.
2. **Detecção de erros grosseiros**: Z-scores extremos, valores fisicamente impossíveis (temperatura negativa no Nordeste, precipitação > 500mm/dia).
3. **Harmonização espaço-temporal**: todas as fontes alinhadas na mesma resolução (mensal) e na mesma unidade geográfica (região metropolitana / estado / polo produtor).
4. Criação de um **dicionário de variáveis** (`docs/dicionario_variaveis.md`) com nome, unidade, fonte, fórmula de derivação.

#### Fase 3 — Estatística Descritiva e Exploração Visual (Semanas 5–9) ⬅️ FOCO PRINCIPAL
1. **Distribuições univariadas** de todas as variáveis: histogramas, boxplots, testes de normalidade.
2. **Matriz de correlação de Pearson e Spearman** (heatmap grande) entre todas as variáveis — busca por padrões inesperados.
3. **Análise de sazonalidade**: decomposição STL (Seasonal-Trend-Loess) das séries de preço e clima.
4. **Mapas bivariados** (choropleth): sobreposição visual de anomalia climática × inflação alimentar por região.
5. **Análise de defasagem temporal (cross-correlation)**: qual é o *lag* ótimo entre uma seca e seu reflexo no preço?
6. **Representatividade por propósito**: As 16 RMs do IPCA representam bem a realidade do interior? Confrontar com dados PAM municipais.

#### Fase 4 — Confronto com LLM (Semanas 8–11)
1. Coletar PDFs das Atas do COPOM (~80 documentos em 10 anos) e relatórios da CONAB.
2. Usar **Langchain + OpenAI** para extrair trechos que mencionam "alimentos", "clima", "seca", "safra", "combustível".
3. Estruturar as narrativas em uma tabela: `{data, fonte, causa_alegada, magnitude_alegada}`.
4. **Confrontar sistematicamente**: quando o COPOM diz "a alta de alimentos foi causada pela seca no Sul", os dados do INMET confirmam anomalia de precipitação naquele período e região? Ou o diesel subiu 15% no mesmo trimestre?
5. Gerar um "Índice de Aderência Narrativa" — percentual das vezes que a justificativa oficial é sustentada pelos dados.

#### Fase 5 — Hipóteses e Relações Não-Óbvias (Semanas 10–13)
1. **H1:** Em estados distantes dos polos produtores (ex: AM, AP), o diesel explica >50% da variância do preço de alimentos, tornando o clima irrelevante localmente.
2. **H2:** Existe um "efeito paradoxo de safra recorde" — quando a produção nacional bate recorde, o preço do feijão pode subir por realocação de área (produtores migram para soja, reduzindo área de feijão).
3. **H3:** O lag entre seca e inflação alimentar é assimétrico: a alta de preço é rápida (~2 meses), mas a queda após a normalização do clima é lenta (~6+ meses) — histerese de preço.
4. **H4:** Em anos de El Niño, a correlação entre preço do tomate e precipitação no Sudeste inverte de sinal comparada a anos neutros.
5. Validação formal via testes estatísticos (Mann-Whitney, Granger Causality, Kruskal-Wallis para grupos).

#### Fase 6 — Modelagem: A Cereja do Bolo (Semanas 12–15)
1. **Random Forest / XGBoost** para regressão do IPCA-Alimentação com *todas* as variáveis integradas.
2. Objetivo primário: **feature importance** (SHAP values) — não prever o futuro, mas explicar o passado.
3. Modelos separados por região para comparar quais fatores dominam em cada canto do país.
4. Análise de resíduos: onde o modelo erra sistematicamente? Esses casos especiais podem revelar variáveis ocultas não capturadas.

#### Fase 7 — Relatório e Apresentação (Semanas 15–16)
1. Consolidar figuras em `figures/`, relatório final em `reports/`.
2. Preparar apresentação com as 3 entregas da disciplina em mente.
