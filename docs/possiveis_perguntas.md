# Possíveis Perguntas e Escopo do Projeto

> **Disciplina:** SSC0957 — Prática em Ciência de Dados II  
> **Tema Central:** Crises Climáticas e Alimentares no Cenário Brasileiro  
> **Duração:** 4 meses (~16 semanas)  
> **Equipe:** 5 pessoas

## Requisitos da Disciplina (checklist obrigatório)

Toda proposta abaixo foi desenhada para atender integralmente aos requisitos do professor:

- [x] **Assunto motivador** com relevância social clara
- [x] **3+ fontes de dados heterogêneas** (formatos, granularidades e origens distintas)
- [x] **Dezenas de variáveis** após agregação e cruzamento espaço-temporal
- [x] **Confronto de fontes com LLM** — usar LLM para questionar/validar narrativas contra os dados
- [x] **Justificativa qualitativa** de por que cada fonte foi escolhida
- [x] **Estatística Descritiva** como pilar central (qualidade, representatividade, erros grosseiros)
- [x] **Verificação de hipóteses** com base em dados
- [x] **Descoberta de relações não-óbvias**
- [x] **Modelagem como etapa final** ("cereja do bolo"), não como objetivo único

## Hierarquia de Prioridades (conforme ênfase do professor)

```
Prioridade MÁXIMA:
  ├── 1. Agregação e exploração de múltiplas fontes heterogêneas
  ├── 2. Interpretação visual + representatividade por propósito
  └── 3. Estatística descritiva + qualidade dos dados

Prioridade ALTA:
  ├── 4. Confronto de narrativas com LLM
  └── 5. Hipóteses e relações não-óbvias

Prioridade COMPLEMENTAR:
  └── 6. Construção de modelos (a cereja do bolo)
```

---

## ⭐ Proposta 1 (RECOMENDADA): O que realmente move o preço da comida no Brasil? Anomalias climáticas, custo logístico e macroeconomia na volatilidade regional da cesta básica

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

---

## Proposta 2: O avanço da fronteira agrícola destrói o próprio microclima? Uso do solo, desmatamento e resiliência hídrica no MATOPIBA

### Motivação
O MATOPIBA (Maranhão, Tocantins, Piauí, Bahia) é a última grande fronteira de expansão do agronegócio brasileiro. A hipótese é que o desmatamento acelerado para plantio de soja está retroalimentando um ciclo de degradação: menos vegetação → menos evapotranspiração → menos chuva → menor produtividade → pressão para expandir mais → mais desmatamento.

### Fontes de Dados Detalhadas (5 fontes)

| # | Fonte | Tipo | Granularidade | Formato | Acesso |
|---|---|---|---|---|---|
| 1 | **MapBiomas (Coleção 8+)** | Transição uso do solo | Anual, por município | GeoTIFF / Shapefile / CSV agregado | `https://mapbiomas.org/` |
| 2 | **INPE — PRODES** | Desmatamento consolidado | Anual, por município | Shapefile / CSV | `http://terrabrasilis.dpi.inpe.br/` |
| 3 | **INPE — DETER** | Alertas de desmatamento | Diário/Semanal | Shapefile / CSV | `http://terrabrasilis.dpi.inpe.br/` |
| 4 | **INMET (BDMEP)** | Dados meteorológicos | Diária, por estação | API REST → JSON/CSV | `https://portal.inmet.gov.br/` |
| 5 | **CONAB (Séries Históricas)** | Produção de grãos | Anual, safra, por UF/município | XLS/CSV | `https://www.conab.gov.br/` |

**Fonte auxiliar:** ANA — Hidroweb (vazão de rios), papers acadêmicos sobre reciclagem de precipitação.

### Justificativa Qualitativa
1. **MapBiomas** é o dataset mais completo e granular de uso do solo do Brasil, reconstruído retroativamente desde 1985 com sensoriamento remoto.
2. **PRODES/DETER** são os sistemas oficiais de monitoramento de desmatamento do governo. PRODES (anual, consolidado) dá a tendência; DETER (quase-tempo-real) captura a dinâmica.
3. **INMET** é a rede oficial de estações do Brasil. Embora com lacunas no interior do MATOPIBA, permite análise de tendência climática.
4. **CONAB** é a referência oficial de oferta agrícola, usada pelo próprio mercado financeiro.

### Variáveis Esperadas (~35–50 variáveis)
- % de área do município convertida de vegetação nativa para agricultura/pastagem (MapBiomas)
- Taxa anual de desmatamento (km²) por município (PRODES)
- Variação na precipitação acumulada anual vs. média histórica (INMET)
- Duração da estação chuvosa (dias entre primeiro e último evento > 20mm)
- Número de veranicos (períodos secos > 10 dias dentro da estação chuvosa)
- Produtividade de soja/milho/algodão (kg/ha) por município (CONAB)
- Razão área_colhida / área_plantada (proxy de perda)
- Distância do município ao fragmento florestal mais próximo (derivada de MapBiomas)
- Lags temporais: desmatamento acumulado em t-1, t-3, t-5 anos vs. precipitação em t

### Metodologia
1. **Agregação:** Todas as fontes alinhadas em resolução municipal/anual (foco: 2000–2024, ~337 municípios do MATOPIBA).
2. **Exploração visual:** Mapas choropleth animados mostrando a "onda" de conversão do solo ao longo dos anos. Scatter plots de desmatamento acumulado × tendência de precipitação por município.
3. **Autocorrelação espacial (PySal):** Análise de Moran Local (LISA) para identificar *clusters* de desmatamento-seca.
4. **LLM:** Pipeline Langchain para extrair e classificar trechos de relatórios da Embrapa e secretarias de agricultura estaduais sobre sustentabilidade no MATOPIBA, confrontando com dados de satélite.
5. **Hipóteses:** (a) Municípios com >70% de conversão do solo apresentam tendência de queda na precipitação superior a municípios vizinhos preservados. (b) O efeito aparece com lag de 3–5 anos.
6. **Modelagem:** Clustering espacial (K-Means / DBSCAN) para criar uma tipologia de municípios: "produtivos e sustentáveis" vs. "produtivos e em colapso hídrico" vs. "degradados e improdutivos".

### ⚠️ Riscos Técnicos
- Processamento de dados raster (GeoTIFF) exige Rasterio e pode ser lento sem experiência prévia.
- Estações INMET são escassas no interior do MATOPIBA — pode haver gaps espaciais grandes.
- A hipótese de defasagem temporal exige desenho experimental cuidadoso para evitar correlações espúrias.

---

## Proposta 3: Vulnerabilidade à Insegurança Alimentar — Choques climáticos, perfil socioeconômico e efetividade de políticas públicas

### Motivação
Como os extremos climáticos (secas no Nordeste, enchentes no Sul) se traduzem em picos de internação por desnutrição, e a assistência social está sendo direcionada para quem mais precisa?

### Fontes de Dados Detalhadas (4 fontes)

| # | Fonte | Tipo | Granularidade | Formato | Acesso |
|---|---|---|---|---|---|
| 1 | **DataSUS — SIH/SUS** | Internações hospitalares | Mensal, por município | DBC (proprietário) → CSV | `https://datasus.saude.gov.br/` |
| 2 | **CEMADEN** | Alertas de desastres | Diário, por município | CSV / API | `http://www2.cemaden.gov.br/` |
| 3 | **IBGE — Censo / PNAD** | Perfil socioeconômico | Decenal / Anual | CSV / API SIDRA | `https://sidra.ibge.gov.br/` |
| 4 | **Vis Data (Min. Desenv. Social)** | Benefícios sociais | Mensal, por município | Portal web / CSV | `https://aplicacoes.mds.gov.br/` |

### Variáveis Esperadas (~40 variáveis)
- Taxa de internação por desnutrição (CID E40-E46) per capita
- Meses consecutivos sob seca (CEMADEN)
- Proporção de famílias em extrema pobreza (CadÚnico)
- Volume financeiro do Bolsa Família por município
- Razão beneficiários / famílias em pobreza (cobertura)

### Metodologia Resumida
1. Limpeza pesada dos arquivos `.dbc` do DataSUS (conversão via `read.dbc` ou `pysus`).
2. Painel municipal-mensal para estados do Semiárido (foco: ~1.200 municípios).
3. Cross-correlation entre pico de seca e pico de internação (qual o lag?).
4. LLM para analisar decretos de emergência vs. dados pluviométricos reais.
5. Classificador para identificar perfis de municípios vulneráveis.

### 🔴 ALERTA: Alto Risco Técnico
> **O grupo já enfrentou problemas sérios com dados do DataSUS** (esquistossomose). Os microdados do SIH/SUS são arquivos `.dbc` em formato proprietário, com codificação inconsistente, campos faltantes, e mudanças de schema entre anos. O CadÚnico possui acesso restrito na granularidade necessária. **O tempo de ETL pode facilmente consumir 5–6 semanas**, comprometendo as fases mais importantes do projeto.

---

## Proposta 4: A geografia da água e da proteína — Custo hídrico da pecuária e abastecimento humano

### Motivação
A expansão da pecuária bovina consome água de bacias que já operam no limite, criando um conflito invisível entre a produção de carne e o abastecimento de cidades e agricultura familiar.

### Fontes de Dados Detalhadas (4 fontes)

| # | Fonte | Tipo | Granularidade | Formato | Acesso |
|---|---|---|---|---|---|
| 1 | **IBGE — PPM** | Rebanho bovino | Anual, por município | API SIDRA → CSV | `https://sidra.ibge.gov.br/` |
| 2 | **ANA — SNIRH** | Outorgas e balanço hídrico | Variada, por bacia | Shapefile / CSV | `https://www.snirh.gov.br/` |
| 3 | **MapBiomas Água** | Superfície hídrica | Anual, por município | GeoTIFF / CSV | `https://mapbiomas.org/agua` |
| 4 | **IBGE — Censo Agro 2017** | Estrutura fundiária | Decenal | CSV / API | `https://censoagro2017.ibge.gov.br/` |

### Variáveis Esperadas (~30–40 variáveis)
- Carga bovina por km² por município
- Variação de superfície hídrica (km²/ano)
- Volume de outorgas para irrigação/dessedentação animal
- Disponibilidade hídrica per capita por bacia

### Metodologia Resumida
1. Integração de dados municipais com contornos de bacias hidrográficas (mudança de suporte geográfico).
2. Correlação entre crescimento do rebanho e diminuição de espelhos d'água.
3. LLM para analisar relatórios ESG de empresas pecuaristas vs. dados de satélite.
4. Modelagem econométrica espacial com PySal.

### ⚠️ Riscos Técnicos
- Dados de outorgas da ANA são notoriamente incompletos e inconsistentes.
- MapBiomas Água é um produto derivado com menos documentação que o MapBiomas padrão.
- A mudança de suporte geográfico (município → bacia) é tecnicamente complexa e pode consumir semanas.

---

## Decisão do Grupo

> **Sugestão forte: começar pela Proposta 1.** Ela permite que o grupo foque sua energia no que o professor realmente quer ver — agregação, visualização e interpretação — em vez de gastar semanas lutando contra formatos de dados e APIs quebradas. As outras propostas podem ser incorporadas como extensões caso sobre tempo.