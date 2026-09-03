## 1. Avaliação das Fontes

### 1.1 `bcb_var_macroeconomicas`
* **Fonte:** [[Banco Central do Brasil]] (BCB / SGS)
* **Papel no Projeto:** Investigar a relação de variáveis macroeconômicas (câmbio, juros, inflação geral) com a volatilidade dos preços dos alimentos.

**Perguntas a responder durante a avaliação:**
* **Quais variáveis estão disponíveis?**
	  - Câmbio PTAX comercial diário consolidado em métricas mensais (`dolar_ptax_medio`, `dolar_ptax_fim`);
	- Inflação geral do país via IPCA (`ipca_mm` de variação mensal e `ipca_indice_base`);
	- Taxa de juros básica da economia (`selic` anualizada e `selic_efetiva_am` ao mês);
	- Índice Geral de Preços do Mercado (`igpm`), relevante para contratos de insumos e logística.
* **Qual é a periodicidade?** Mensal contínua (`ano_mes`), com agregação consistente das cotações diárias.
* **Existe cobertura para todo o período escolhido?** Cobertura de **2014-01-01 a 2026-07-01** (151 meses completos), atendendo 100% da janela do projeto (2015-01 → 2026-06) com **0% de valores ausentes (nulos)** em todas as colunas.
* **Essas variáveis possuem relação plausível com o preço dos alimentos?**
	- O **Câmbio (PTAX)** dita o custo de insumos importados (fertilizantes, defensivos) e a paridade de exportação de commodities agrícolas (soja, milho, carne, trigo);
	- O **IPCA Geral e IGP-M** capturam a inércia inflacionária, custos de atacado e repasse geral de preços na economia;
	- A **Selic** reflete o aperto monetário, custo de estocagem e crédito para custeio de safras.
* **É possível integrá-las aos dados regionais?** *Via **broadcast nacional** utilizando a chave temporal `ano_mes`. As variáveis replicam-se igualmente para todas as 16 áreas urbanas/UFs em cada mês, servindo como features de contexto macroeconômico exógeno.

> [!check] Decisão: ✅ Utilizar (Fonte primária de features macroeconômicas)
> **Justificativa:** O dataset apresenta **100% de completude (zero nulos)** para os 151 meses analisados (2014 a 2026), sem necessidade de imputação. As variáveis fornecem o contexto econômico exógeno fundamental para isolar choques cambiais e inerciais de choques puramente climáticos/locais no preço dos alimentos.

---

### 3.2 `conab`
* **Fonte:** Companhia Nacional de Abastecimento (CONAB)
* **Papel no Projeto:** Fornecer informações de produção agrícola e balanço de oferta/estoque de produtos agrícolas.

**Perguntas avaliadas:**
* **Quais produtos estão disponíveis?** Grãos e principais commodities agrícolas em séries históricas e balanço de oferta e demanda.
* **Existe informação por estado ou região?** Apenas para safra/área (`UF × safra`); estoques e oferta/demanda são estritamente agregados para o Brasil.
* **Qual é a periodicidade?** Anual por safra (sem frequência mensal nativa no histórico longo).
* **Qual é a cobertura temporal?** Cobre desde 1976/77 até 2025/26 (abrange a janela 2015–2026).
* **Os dados podem ser relacionados aos preços observados?** Não diretamente em frequência mensal sem gerar degraus e autocorrelação espúria; viável apenas em base anual ou como nível estático.
* **Há sobreposição com `estimativas_safra_UF`?** Sim, com as estimativas do [[LSPA]]/IBGE. O estoque nacional é o único diferencial relevante.

> [!warning] Decisão: 🟡 Utilizar parcialmente / Rejeitar para séries mensais por UF
> **Justificativa:** A CONAB não disponibiliza dados mensais por UF para o período completo do projeto (2015–2026), limitando-se a registros anuais por safra. A expansão artificial para base mensal inflaciona o $n$ e gera autocorrelação espúria nas análises de correlação cruzada (CCF). Mantém-se apenas o uso opcional da relação *estoque/consumo* nacional via broadcast defasado.

---

### 3.3 `estimativas_safra_UF`
* **Fonte:** [[IBGE]] / [[LSPA]] (Levantamento Sistemático da Produção Agrícola) e [[PAM]] (Produção Agrícola Municipal)
* **Papel no Projeto:** Fornecer dados conjunturais de oferta e estimativas de safra em nível estadual, permitindo quantificar choques de produtividade, revisões mensais de produção e área colhida por cultura agrícola.

**Perguntas a responder durante a avaliação:**
* **Quais culturas estão disponíveis?**
	* 11 culturas principais diretamente alinhadas à cesta básica e ao IPCA (arroz, banana, batata-inglesa, café, feijão, milho, soja, tomate, trigo, etc.), abrangendo tanto lavouras temporárias (82%) quanto permanentes (18%).
* **Como as estimativas são calculadas?**
	* Estimativas mensais de campo e comissões técnicas (GCEA/IBGE) que consolidam `area_plantada_ha`, `area_colhida_ha`, `producao_t`, `rendimento_kg_ha` e a taxa de revisão da produção em relação ao relatório anterior (`revisao_pct_prod`).
* **Qual é a periodicidade?**
	* Mensal contínua no LSPA (`ano_mes`), com referência à safra anual (`ano_safra`), complementada pelo consolidado anual do PAM (`ano`).
* **Qual é a cobertura temporal?**
	* Histórico de **2014-01-01 a 2026-07-01** (151 meses no LSPA e 11 anos completos no PAM), cobrindo 100% da janela do projeto (2015–2026).
* **Como as UFs estão identificadas?**
	* Padronização completa e sem nulos pelas chaves `sigla_uf`, `cod_ibge_uf` (códigos 11 a 53) e `nome_uf`, cobrindo todas as **27 UFs**.
* **Há dados suficientes para todo o período analisado?**
	* Sim. O histórico cobre o período integral. Os ~21% de valores ausentes em métricas de produção referem-se à ausência natural do plantio de determinadas culturas em estados específicos (ex.: trigo no Norte ou arroz irrigado em áreas não produtoras), e não a falha de coleta.
* **Essa base acrescenta informação em relação à CONAB?**
	* **Sim (superior no recorte temporal do projeto):**
	1. Fornece granularidade **mensal real** por UF (capturando revisões de expectativa safra a safra), enquanto a CONAB para o período longo é puramente anual;
	2. Mantém consistência metodológica direta com o IBGE/SIDRA (mesma raiz territorial da variável-alvo).

> [!check] Decisão: ✅ Utilizar (Fonte primária de choques de oferta e capacidade agrícola)
> **Justificativa:** O LSPA/IBGE soluciona o gargalo de frequência da CONAB ao entregar acompanhamento mensal e contínuo (2014–2026) por UF para as 11 principais culturas agrícolas. A métrica de revisão percentual (`revisao_pct_prod`) e as variações de rendimento médio (`rendimento_kg_ha`) servem como regressores diretos para capturar quebras de safra e choques de oferta nas correlações com a inflação do IPCA.

---

### 3.4 `sidra_ipca`
* **Fonte:** [[IBGE]] / [[SIDRA]]
* **Papel no Projeto:** Fornecer a variável-alvo (target) do projeto: variação percentual mensal de preços de alimentos e pesos orçamentários das famílias.

**Perguntas avaliadas:**
* **Quais subitens de alimentação estão disponíveis?** Grupo *Alimentação e Bebidas*, subgrupo *Alimentação no Domicílio* e subitens desagregados (arroz, feijão, carnes, leite, hortifrútis, etc.).
* **Qual é a granularidade regional?** 16 áreas urbanas oficiais (10 Regiões Metropolitanas e 6 Capitais/Municípios Isolados).
* **Qual é o período disponível?** Série histórica contínua de 2006 a 2026 (100% de cobertura no período do projeto).
* **Como os pesos são utilizados?** Mapeamento do comprometimento da renda familiar regional e ponderação de perdas e cestas compostas.
* **É possível construir uma medida adequada de variação de preços?** Sim, a taxa mensal percentual (`var_pct_mes`) é padronizada, estacionária e robusta contra distorções de escala.
* **Como integrar às demais variáveis?** Cruzamento por `[ano_mes × UF/Localidade]` com dados meteorológicos do [[INMET]], custos logísticos da [[ANP]] e contexto agrícola/macroeconômico.

> [!check] Decisão: ✅ Utilizar (Fonte primária da variável-alvo)
> **Justificativa:** Apresenta qualidade estatística superior e histórico contínuo (2006–2026) para as 16 principais áreas urbanas do país, superando as limitações regionais e metodológicas do DIEESE. A base conta com 83.383 registros integráveis diretamente ao pipeline multimodal.

---
### 3.5 `monitor_secas_ana`
- **Fonte:** Agência Nacional de Águas e Saneamento Básico ([[ANA]]) — _Monitor de Secas_
- **Papel no Projeto:** Fornecer indicadores objetivos de severidade, extensão territorial e persistência temporal de eventos de seca em nível estadual para modelar choques climáticos sobre a oferta de alimentos.
    
**Perguntas avaliadas:**
- **Quais variáveis estão disponíveis?**
    - Percentuais cumulativos de área sob seca por classe: `pct_area_S0plus` (fraca ou pior) até `pct_area_S4plus` (excepcional);
    - Índices consolidados de intensidade: `severidade_media` (ponderada pela área total da UF, escala 0 a 5) e `severidade_media_area_seca` (escala 1 a 5);
    - Memória do choque climático: `meses_consecutivos_S2plus` (duração contínua de seca grave ou pior);
    - Flags de auditoria: `monitorado` (booleano de vigência) e `inconsistente`.
- **Qual é a granularidade regional?**
    - Unidades Federativas (27 UFs). A ponderação por área municipal já é realizada nativamente pela metodologia da ANA.
- **Qual é a periodicidade?**
    - Mensal (`ano_mes` no formato `YYYY-MM`).
- **Qual é a cobertura temporal?**
    - Janela tratada cobre `2015-01` a `2026-06` (138 meses $\times$ 27 UFs = 3.726 registros). Contudo, a entrada das UFs no programa foi gradual: o Nordeste possui série completa (desde 2014), Centro-Sul entrou por volta de 2020/2021, e estados do Norte (RR, AP) apenas em 2023.
- **Os dados podem ser relacionados aos preços observados?**
    - Sim. A `severidade_media` e os `meses_consecutivos_S2plus` correlacionam-se diretamente com quebras de safra locais e pressão sobre hortifrútis e grãos, permitindo identificar defasagens temporais (_lags_) de impacto no IPCA regional.
- **Quais cuidados metodológicos são exigidos?**
    - **Tratamento de nulos:** 1.358 registros (36,4%) correspondem ao período pré-monitoramento de determinadas UFs e são mantidos estritamente como `NaN` (`monitorado == False`). Imputar zero falsearia ausência de seca no Centro-Sul antes de 2020.
    - **Natureza cumulativa:** Os percentuais brutos são cumulativos ($S0 \ge S1 \ge S2 \ge S3 \ge S4$) e não devem ser somados diretamente sem desacumulação.        

> [!check] Decisão: 🟡 Utilizar parcialmente (Features climáticas estaduais com filtro temporal)
> 
> **Justificativa:** O dataset entrega métricas consolidadas e validadas por especialistas sem a necessidade de reconstrução raster/geoespacial complexa. Devido à expansão histórica assimétrica entre as regiões, o uso deve ser condicionado ao tratamento explícito de `NaN` ou restrito a recortes espaciais/temporais consistentes (ex.: foco no Nordeste para a janela completa ou corte nacional pós-2020), evitando vieses de seleção geográfica nos modelos.

---

### 3.6 `inmet_clima`
- **Fonte:** Instituto Nacional de Meteorologia ([[INMET]])
- **Papel no Projeto:** Fornecer dados climáticos observacionais de superfície (precipitação, temperaturas extremas, amplitude térmica e umidade) para construir anomalias meteorológicas e quantificar choques de clima nos polos produtores agrícolas e cinturões verdes.
    
**Perguntas avaliadas:**
- **Quais variáveis estão disponíveis?**
    - Pluviosidade acumulada mensal (`chuva_mm_mes`);
    - Médias térmicas: `temp_media`, `temp_max_media`, `temp_min_media` e `amplitude_termica_media`;
    - Extremos térmicos mensais: `temp_max_abs` (máxima absoluta) e `temp_min_abs` (mínima absoluta / risco de geada);
    - Umidade relativa do ar média (`umidade_media`).
- **Qual é a granularidade regional?**
    - Estação meteorológica pontual (`codigo_estacao`, com 701 estações distintas distribuídas pelas 27 UFs) agregável para nível estadual (`sigla_uf`) ou bacias agrícolas específicas. MG (12%), RS (8%) e BA (8%) concentram o maior número de estações ativas.
- **Qual é a periodicidade?**
    - Mensal consolidada (`ano_mes`), cobrindo os meses de 1 a 12.
- **Qual é a cobertura temporal?**
    - Histórico de **2014-01-01 a 2026-07-01** (151 meses completos), atendendo 100% da janela temporal do projeto (2015–2026).
- **Os dados podem ser relacionados aos preços observados?**
    - Sim. Permite calcular **anomalias climáticas** (desvios em relação à média histórica local) nas regiões produtoras e correlacioná-las via _lags_ com a inflação de alimentos sensíveis (ex.: chuvas extremas no RS vs. arroz; secas/calor em MG/GO vs. feijão; geadas no Sul/Sudeste vs. hortifrútis e café).
- **Quais cuidados metodológicos são exigidos?**
    - **Tratamento de nulos/falhas instrumentais:** Cerca de 21% a 28% de valores ausentes nas colunas climáticas devido a desativações temporárias ou falhas de sensores em estações automáticas/convencionais. A agregação espacial para a UF (via mediana/média ponderada de estações ativas) é necessária para mitigar lacunas individuais.
        

> [!check] Decisão: ✅ Utilizar (Fonte primária de variáveis meteorológicas e anomalias climáticas) 
> **Justificativa:** O dataset fornece uma malha densa de 701 estações com cobertura completa do período analisado (2014–2026). Ele complementa o Monitor de Secas da ANA ao trazer métricas contínuas de precipitação, picos térmicos absolutos e amplitude térmica, fundamentais para capturar choques climáticos pontuais e agudos sobre a oferta agrícola.
---

### 3.7 `anp_combustiveis`

- **Fonte:** Agência Nacional do Petróleo, Gás Natural e Biocombustíveis ([[ANP]])
- **Papel no Projeto:** Integrar os custos logísticos de transporte rodoviário (diesel) e de preparo doméstico (GLP) à modelagem. Explica a variabilidade regional de preços que variáveis macroeconômicas nacionais (como Dólar e Selic) não conseguem capturar.
**Perguntas avaliadas:**  

- **Quais variáveis estão disponíveis?**
    - Preço ao consumidor final (`comb_preco_*`) de 5 produtos essenciais: Diesel, Diesel S10, Gasolina, Etanol e GLP 13kg. _(Gasolina Aditivada, GNV e preços de compra/distribuidora foram descartados por baixa cobertura ou interrupção na série)_.
    - Variações percentuais de preço: mensal (`comb_var_mm_*`) e anual (`comb_var12_*`).        
    - Desvio espacial: `comb_diesel_vs_br_pct` (distância percentual do preço da UF contra a mediana nacional).
    - Metadados e auditoria: Número de postos pesquisados (`comb_n_registros`) e flags booleanos indicando meses com pesquisa ativa (`comb_observado`, `comb_observado_liquidos`).
- **Qual é a granularidade regional?**
    - Agregado por Estado (`sigla_uf`). O valor consolidado da ANP foi validado contra uma amostra testemunha de mais de 96 mil coletas individuais de postos, confirmando altíssima fidelidade (erro absoluto mediano de apenas 0,6%).
- **Qual é a periodicidade?**
    - Mensal (`ano_mes`).        
- **Qual é a cobertura temporal?**
    - Histórico original de 2004-05 a 2026-07. Para a janela do projeto (2015 a 2026), a cobertura espacial nas 16 UFs é perfeita nos meses em que a pesquisa ocorreu, mas há **lacunas temporais sistêmicas** (33 meses sem coleta de líquidos e 15 meses sem GLP).
- **Os dados podem ser relacionados aos preços observados?**      
    - Sim. O Diesel compõe o frete que escoa a safra (impactando o IPCA com defasagem estimada de 4 a 5 meses). O GLP impacta simultaneamente a mesma cesta do IPCA medida pelo IBGE.
- **Quais cuidados metodológicos são exigidos?**
    - **Ponderação de Duplicatas:** Existência de levas duplas de pesquisa no mesmo mês (ex.: 2026-04). Foi aplicada média ponderada pela `quantidade_registros` (postos) para evitar vieses extremos que chegavam a distorcer o preço médio em 45%.         
    - **A Armadilha do _Shift_:** As variações (`var_mm` e `var12`) foram calculadas apenas **após** reindexar a série para a grade temporal completa. Sem isso, um buraco de coleta faria o Pandas calcular a variação de março diretamente contra julho, mascarando o choque real.
    - **Preservação Semântica dos Nulos (NaN):** Valores vazios indicam estritamente que a ANP não foi a campo naqueles meses (nacionalmente). Não é permitido o uso de _forward fill_ ou preenchimento com zeros, sob o risco de criar planícies ou degraus artificiais no modelo. O controle deve ser feito via flag `comb_observado`.
    
> [!check] Decisão: ✅ Utilizar (Fonte primária de custos logísticos e de cocção)
> 
> **Justificativa:** O dataset entrega a dimensão de custo de frete agrícola (Diesel) e despesa domiciliar (GLP) com as variações regionais necessárias para diferenciar o impacto inflacionário entre as capitais. A manobra de pivotamento e o tratamento rigoroso das lacunas da ANP garantem a integração das 19 novas features sem corromper a espinha ou multiplicar as linhas da tabela fato já consolidada.

---
### 3.7 Critérios de Decisão
* ✅ **Utilizar:** Apresenta informações relevantes, consistentes e adequadas ao escopo temporal/espacial.
* 🟡 **Utilizar parcialmente:** Variáveis específicas aproveitadas (ex.: features de contexto ou broadcast).
* ❌ **Descartar:** Não atende à granularidade, qualidade ou histórico necessário.
* 🔄 **Substituir:** Há outra fonte de maior frequência ou cobertura metodológica para o mesmo fenômeno.

---
## 5. Escolha da Variável de Preço

Avaliamos inicialmente o [[DIEESE]] para monitoramento da cesta básica, mas a opção final foi o **IPCA (SIDRA/IBGE)** pelos seguintes fatores:

* **Métrica Estacionária:** A variação percentual mensal e a estrutura de pesos orçamentários facilitam a modelagem sem os vieses de preços nominais absolutos.
* **Granularidade e Comparabilidade:** Cobertura de 16 praças urbanas representativas de diferentes realidades logísticas e de consumo.
* **Estrutura por Subitem:** Possibilidade de isolar choques em culturas específicas (ex.: feijão, arroz, hortifrútis) contra suas respectivas origens produtivas.

---

## 6. Escolha do Período Analisado

Critérios para a janela temporal:
* Disponibilidade simultânea das bases meteorológicas, logísticas, agrícolas e de preços.
* Observação de ciclos agrícolas completos e anomalias climáticas severas (ex.: secas, geadas, El Niño/La Niña).
* Volume amostral suficiente para estimação de modelos com defasagens (*lags*).

> [!todo] Período Escolhido: `2015-01 → 2026-06` (A confirmar com a equipe)
> **Justificativa:** `A preencher após validação final do pipeline de dados.`

---

## 7. Granularidade Espacial

A análise adota a escala regional como pilar central, permitindo mensurar disparidades entre capitais consumidoras e polos produtores.

* **Níveis de agregação:**
  * Brasil (agregado macroeconômico / broadcast);
  * Unidades Federativas (UFs);
  * Regiões Metropolitanas e Capitais isoladas do IPCA.

### Dimensão Geográfica
Padronização centralizada via arquivo `dim_uf.csv` para unificar códigos IBGE, siglas, nomes e macrorregiões entre todas as tabelas brutas.

---