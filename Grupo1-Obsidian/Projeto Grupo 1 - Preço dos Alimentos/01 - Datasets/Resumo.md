# Avaliação detalhada das fontes

> Anexo das seções 3 a 6 de [[Decisões e Justificativas do Projeto]]. Cada fonte traz a avaliação feita antes da coleta e um bloco **📌 Na tabela final** com o que de fato chegou à tabela `fato_alimentos_combustiveis_uf_mes` (2.088 linhas × 108 colunas). Detalhes técnicos da junção em [[Integração das Bases]].

## 3. Avaliação das fontes

### 3.1 `bcb_var_macroeconomicas`

- **Fonte:** [[Banco Central do Brasil]] (BCB / SGS)
- **Papel no Projeto:** Investigar a relação de variáveis macroeconômicas (câmbio, juros, inflação geral) com a volatilidade dos preços dos alimentos.

**Perguntas a responder durante a avaliação:**

- **Quais variáveis estão disponíveis?**
    - Câmbio PTAX comercial diário consolidado em métricas mensais (`dolar_ptax_medio`, `dolar_ptax_fim`);
    - Inflação geral do país via IPCA (`ipca_mm` de variação mensal e `ipca_indice_base`);
    - Taxa de juros básica da economia (`selic` anualizada e `selic_efetiva_am` ao mês);
    - Índice Geral de Preços do Mercado (`igpm`), relevante para contratos de insumos e logística.
- **Qual é a periodicidade?** Mensal contínua (`ano_mes`), com agregação consistente das cotações diárias (dólar: média do mês e valor do último dia).
- **Existe cobertura para todo o período escolhido?** Cobertura de **2014-01-01 a 2026-07-01** (151 meses completos), atendendo 100% da janela do projeto (2015-01 → 2026-06) com **0% de valores ausentes** em todas as colunas.
- **Essas variáveis possuem relação plausível com o preço dos alimentos?**
    - O **Câmbio (PTAX)** dita o custo de insumos importados (fertilizantes, defensivos) e a paridade de exportação de commodities agrícolas (soja, milho, carne, trigo);
    - O **IPCA Geral e IGP-M** capturam a inércia inflacionária, custos de atacado e repasse geral de preços;
    - A **Selic** reflete o aperto monetário, custo de estocagem e crédito para custeio de safras.
- **É possível integrá-las aos dados regionais?** Via **broadcast nacional** pela chave `ano_mes`: as variáveis se replicam para todas as UFs em cada mês, como features de contexto exógeno.

> [!check] Decisão: ✅ Utilizar (fonte primária de features macroeconômicas) **Justificativa:** 100% de completude (zero nulos) nos 151 meses, sem necessidade de imputação. Fornecem o contexto exógeno para isolar choques cambiais e inerciais de choques climáticos/locais.

> [!example] 📌 Na tabela final
> 
> - **5 colunas** `macro_*`: IPCA cheio, dólar médio, dólar no fim do mês, Selic e IGP-M. _(Conferir no dicionário se `selic_efetiva_am` e `ipca_indice_base`, citadas acima, chegaram à tabela.)_
> - **Armadilha da API:** pedindo mais de 10 anos de uma vez, ela responde "OK" mas devolve dados cortados. O coletor pede em blocos de 10 anos e confere o período devolvido.
> - ⚠️ As colunas são **idênticas em todas as UFs** no mesmo mês: explicam variação **no tempo**, nunca diferença entre estados.

---

### 3.2 `conab`

- **Fonte:** Companhia Nacional de Abastecimento (CONAB)
- **Papel no Projeto:** Fornecer informações de produção agrícola e balanço de oferta/estoque de produtos agrícolas.

**Perguntas avaliadas:**

- **Quais produtos estão disponíveis?** Grãos e principais commodities agrícolas em séries históricas e balanço de oferta e demanda.
- **Existe informação por estado ou região?** Apenas para safra/área (`UF × safra`); estoques e oferta/demanda são agregados para o Brasil.
- **Qual é a periodicidade?** Anual por ano-safra (ex.: 2024/25), sem frequência mensal nativa no histórico longo.
- **Qual é a cobertura temporal?** De 1976/77 até 2025/26 (abrange a janela 2015–2026).
- **Os dados podem ser relacionados aos preços observados?** Não diretamente em frequência mensal sem gerar degraus e autocorrelação espúria; viável apenas em base anual ou como nível estático.
- **Há sobreposição com `estimativas_safra_UF`?** Sim, com as estimativas do [[LSPA]]/IBGE. O estoque nacional é o único diferencial relevante.

> [!failure] Decisão: ❌ Descartar **Justificativa:** a CONAB não disponibiliza dados mensais por UF para o período do projeto, só registros anuais por safra. Expandir artificialmente para mensal inflaria o $n$ e geraria autocorrelação espúria (CCF), e o LSPA já mede o mesmo fenômeno mês a mês. A relação _estoque/consumo_ nacional (via _broadcast_ defasado) fica registrada apenas como **ideia futura**, não adotada.

---

### 3.3 `estimativas_safra_UF`

- **Fonte:** [[IBGE]] / [[LSPA]] (Levantamento Sistemático da Produção Agrícola) e [[PAM]] (Produção Agrícola Municipal)
- **Papel no Projeto:** Fornecer dados conjunturais de oferta e estimativas de safra em nível estadual, permitindo quantificar choques de produtividade e revisões mensais de produção por cultura.

**Perguntas a responder durante a avaliação:**

- **Quais culturas estão disponíveis?**
    - 11 culturas ligadas à cesta de alimentos: arroz, feijão, milho, soja, trigo, café, banana, batata-inglesa, tomate, mandioca e cana-de-açúcar (lavouras temporárias 82% e permanentes 18%). As safras que o IBGE separa são somadas (feijão 1ª/2ª/3ª, milho 1ª/2ª, café arábica/canéfora, batata das 3 safras).
- **Como as estimativas são calculadas?**
    - Estimativas mensais de campo e comissões técnicas (GCEA/IBGE) que consolidam `area_plantada_ha`, `area_colhida_ha`, `producao_t`, `rendimento_kg_ha` e a taxa de revisão da produção em relação ao relatório anterior (`revisao_pct_prod`). O rendimento é **recalculado** como produção total ÷ área total (a média de rendimentos daria o mesmo peso a safras de tamanhos muito diferentes).
- **Qual é a periodicidade?**
    - Mensal contínua no LSPA (tabela 6588, `ano_mes`), referente à safra anual (`ano_safra`), complementada pelo consolidado anual do PAM (tabelas 1612 e 1613).
- **Qual é a cobertura temporal?**
    - **2014-01-01 a 2026-07-01** (151 meses no LSPA e 11 anos completos no PAM), cobrindo 100% da janela do projeto.
- **Como as UFs estão identificadas?**
    - `sigla_uf`, `cod_ibge_uf` (11 a 53) e `nome_uf`, sem nulos, cobrindo as **27 UFs**.
- **Há dados suficientes para todo o período?**
    - Sim. Os ~21% de ausentes em métricas de produção na base bruta referem-se à ausência natural do plantio (ex.: trigo no Norte), e não a falha de coleta.
- **Essa base acrescenta informação em relação à CONAB?**
    - **Sim:** granularidade **mensal real** por UF (capturando revisões de expectativa) e consistência metodológica direta com o IBGE/SIDRA, a mesma raiz territorial do alvo.

> [!check] Decisão: ✅ Utilizar (fonte primária de choques de oferta) **Justificativa:** o LSPA resolve o gargalo de frequência da CONAB ao entregar acompanhamento mensal por UF para 11 culturas. A revisão percentual da estimativa funciona como regressor direto de quebra de safra.

> [!example] 📌 Na tabela final
> 
> - **22 colunas** (2 medidas × 11 produtos): `safra_producao_t_*` (o nível) e `safra_revisao_pct_*` (a revisão). **Área plantada, área colhida e rendimento NÃO entram na tabela final**; ficam em `data/interim/` para uso futuro. Levou-se a revisão porque é ela que "se mexe" quando a lavoura quebra.
> - **Vazios:** `safra_producao_t_*` vazio vira **0** (a UF não planta o produto), então a coluna final tem 0% de vazios. `safra_revisao_pct_*` **continua vazia** (zero diria "a estimativa não mudou") e fica vazia em todo janeiro.
> - **Outliers:** a revisão sofreu _clipping_ em **±50%** (o bruto passava de 15 milhões %); 99,1% dos valores ficaram intactos.
> - ⚠️ Cada linha é a estimativa da safra do **ano inteiro** vigente no mês, não o colhido no mês: somar 12 meses multiplica a produção por 12.

---

### 3.4 `sidra_ipca`

- **Fonte:** [[IBGE]] / [[SIDRA]]
- **Papel no Projeto:** Fornecer a variável-alvo (target): variação percentual mensal de preços de alimentos e pesos orçamentários das famílias.

**Perguntas avaliadas:**

- **Quais subitens de alimentação estão disponíveis?** Grupo _Alimentação e bebidas_, subgrupo _Alimentação no Domicílio_ e subitens desagregados (arroz, feijão, carnes, leite, hortifrútis, etc.): 40 códigos de item ao todo, mas nem todos existem no período inteiro em todas as UFs.
- **Qual é a granularidade regional?** 16 áreas urbanas oficiais (10 Regiões Metropolitanas, nível N7, e 6 municípios, nível N6). O IPCA **não tem nível "UF"**; cada área urbana é convertida para a UF pelos 2 primeiros dígitos do código IBGE.
- **Qual é o período disponível?** Série de 2006-07 a 2026-07, obtida **encadeando** as tabelas 2938 (2006–2011), 1419 (2012–2019) e 7060 (2020–2026). A 7062 foi rejeitada (é o IPCA-15, outro índice).
- **Como os pesos são utilizados?** Cada item tem peso no orçamento das famílias (`ipca_peso_*`). Os itens estão em três níveis que se encaixam, então os pesos **não devem ser somados**.
- **É possível construir uma medida adequada de variação de preços?** Sim: a taxa mensal percentual é padronizada, estacionária e comparável entre meses e regiões.
- **Como integrar às demais variáveis?** Cruzamento por `[ano_mes × sigla_uf]` com clima ([[INMET]]), seca ([[ANA]]), safra, combustíveis ([[ANP]]) e macro.

> [!check] Decisão: ✅ Utilizar (fonte primária da variável-alvo) **Justificativa:** qualidade estatística superior e histórico longo para 16 áreas urbanas, superando as limitações do DIEESE. A base bruta tem 83.383 registros.

> [!example] 📌 Na tabela final
> 
> - **17 itens** com cobertura completa na janela (o 18º já cai para 92%): 1 grupo (Alimentação e bebidas), 7 subgrupos (farinhas, açúcares, hortaliças, carnes, carnes industrializadas, aves e ovos, leites e derivados) e 9 subitens (arroz, batata-inglesa, tomate, frango inteiro, frango em pedaços, leite longa vida, pão francês, óleo de soja, café moído). Cada item gera `ipca_var_*` e `ipca_peso_*`. **O feijão não está entre os 17.**
> - **Três alvos:** variação no mês, acumulado de 12 meses (composto) e inflação relativa (alimentos − IPCA cheio).
> - ⚠️ **Cobertura não é 100% em todas as UFs:** AC, MA e SE só entram no IPCA em **2018-05** (painel desbalanceado). Por isso a tabela tem 2.088 linhas, e não 16 × 138 = 2.208.
> - ⚠️ **Erro corrigido:** a primeira limpeza apagava o sinal de menos dos valores e transformava deflação em inflação (0 valores negativos contra 32.696 corretos). Os dados foram baixados de novo, e a junção falha se o alvo não tiver deflação.
> - O preço é o da **capital e arredores**, não do estado inteiro.

---

### 3.5 `monitor_secas_ana`

- **Fonte:** Agência Nacional de Águas e Saneamento Básico ([[ANA]]), _Monitor de Secas_
- **Papel no Projeto:** Fornecer indicadores de severidade, extensão territorial e persistência de eventos de seca por UF para modelar choques climáticos sobre a oferta de alimentos.

**Perguntas avaliadas:**

- **Quais variáveis estão disponíveis?**
    - Percentuais **cumulativos** de área sob seca por classe: `pct_area_S0plus` (fraca ou pior) até `pct_area_S4plus` (excepcional);
    - `severidade_media` (ponderada pela área total da UF, escala 0 a 5) e `severidade_media_area_seca` (escala 1 a 5);
    - Memória do choque: `meses_consecutivos_S2plus` (duração contínua de seca grave ou pior);
    - Flags de auditoria: `monitorado` e `inconsistente`.
- **Como foi obtida?** Não há CSV: usa-se a **API REST que o próprio site usa** (encontrada lendo o JavaScript da página), uma requisição por UF. O campo `area` é o **% do território da UF** em seca; a própria ANA já agrega município → UF, sem necessidade de geoprocessamento.
- **Qual é a granularidade regional?** 27 UFs.
- **Qual é a periodicidade?** Mensal (`ano_mes`, `YYYY-MM`).
- **Qual é a cobertura temporal?** Janela tratada de `2015-01` a `2026-06` (138 meses × 27 UFs = 3.726 registros). A entrada das UFs no programa foi gradual: o Nordeste tem série completa (desde 2014), o Centro-Sul entrou por volta de 2020/2021 e RR e AP só em 2023. O país inteiro só é coberto a partir de 2023.
- **Os dados podem ser relacionados aos preços?** Sim: severidade e meses consecutivos de seca grave correlacionam-se com quebras de safra locais e pressão sobre hortifrútis e grãos, permitindo estudar defasagens (_lags_) no IPCA regional.
- **Quais cuidados metodológicos são exigidos?**
    - **Nulos:** 1.358 registros (36%) são do período pré-monitoramento e ficam como `NaN` (`monitorado == False`). Imputar zero falsearia "ausência de seca" no Centro-Sul antes de 2020.
    - **Natureza cumulativa:** S0 ≥ S1 ≥ S2 ≥ S3 ≥ S4; não somar sem desacumular.
    - **Versões duplicadas:** quando a ANA revisa um mês, a API devolve todas as versões juntas (algumas com escala ×100 ou valores de teste). Usa-se a de **maior `id`** (vigente) e 49 UF-meses divergentes são gravados para auditoria.

> [!warning] Decisão: 🟡 Utilizar com ressalva (features estaduais com filtro temporal) **Justificativa:** métricas consolidadas e validadas por especialistas, sem reconstrução geoespacial. Devido à entrada assimétrica das regiões, o uso deve ser condicionado ao tratamento explícito de `NaN` ou a recortes consistentes.

> [!example] 📌 Na tabela final
> 
> - **9 colunas** `seca_*`, com 34 a 38% de vazios e a coluna `seca_monitorado`.
> - Cobertura de seca medida nas 16 UFs do alvo, por recorte: 65,8% (desde 2015-01), 77,9% (2018-01), **90,5% (2020-01)** e 100% (2024-01).
> - ⚠️ **Recomendação:** filtrar por `seca_monitorado` ou recortar a partir de **2020-01**. Um mês do Maranhão (2014-11) viola a regra cumulativa e recebeu `inconsistente = True`.

---

### 3.6 `inmet_clima`

- **Fonte:** Instituto Nacional de Meteorologia ([[INMET]])
- **Papel no Projeto:** Fornecer dados climáticos observacionais de superfície para construir indicadores e anomalias meteorológicas e quantificar choques de clima nos polos produtores.

**Perguntas avaliadas:**

- **Quais variáveis estão disponíveis?**
    - Chuva acumulada mensal (`chuva_mm_mes`);
    - Médias térmicas: `temp_media`, `temp_max_media`, `temp_min_media` e `amplitude_termica_media`;
    - Extremos térmicos mensais: `temp_max_abs` e `temp_min_abs` (risco de geada);
    - Umidade relativa do ar média (`umidade_media`).
- **Qual é a granularidade regional?** Estação pontual (`codigo_estacao`, 701 estações nas 27 UFs), agregada para a UF. MG (12%), RS (8%) e BA (8%) concentram mais estações.
- **Qual é a periodicidade original?** Dados **por hora** (13 ZIPs anuais, ~1,27 GB), transformados em **hora → dia → mês**.
- **Qual é a cobertura temporal?** **2014-01 a 2026-07** (151 meses).
- **Os dados podem ser relacionados aos preços?** Sim. Permitem calcular anomalias (desvios em relação à média histórica local) e correlacioná-las via _lags_ com a inflação de alimentos sensíveis (ex.: chuvas extremas no RS vs. arroz; geadas no Sul/Sudeste vs. hortifrúti e café).
- **Quais cuidados metodológicos são exigidos?**
    - **Falhas instrumentais:** 22,8% das estação-mês têm menos de 70% dos dias medidos (faixa de 21% a 28% nas colunas) e viram vazio **antes** de agregar. A agregação por UF usa a **mediana** (resiste a sensor com defeito).
    - **Cobertura não é completa:** Roraima tem praticamente 1 estação (sem medição em 2021 e 2026) e há um **buraco nacional em 2021–2022** (ex.: RN cai de 100% para 38% de cobertura em 2021). A rede também cresce (475 estações em 2014, 638 em 2026).

> [!check] Decisão: ✅ Utilizar (fonte primária de variáveis meteorológicas) **Justificativa:** malha densa de 701 estações. Complementa o Monitor de Secas da ANA com métricas contínuas de precipitação e extremos, fundamentais para capturar choques pontuais sobre a oferta agrícola.

> [!example] 📌 Na tabela final
> 
> - **11 colunas** `clima_*`, incluindo `clima_n_estacoes` (quantas estações entraram na mediana). Vazios: 0,3% (nenhuma estação passou do corte de 70%).
> - Índices de extremo calculados **a partir dos dias**: dias sem chuva, maior sequência seca e calor extremo (acima do percentil 90 da própria estação naquele mês do ano).
> - **Ficaram de fora:** direção do vento e as máximas/mínimas **absolutas** (`temp_max_abs`, `temp_min_abs`). _(Conferir no dicionário se a umidade entrou.)_
> - ⚠️ Em RR, AP e AC a mediana sai de 1 a 3 estações. A ponderação pela produção (T-022) ainda **não foi feita**. Imputação (normal climatológica ou NASA POWER) é pendência.

---

### 3.7 `anp_combustiveis`

- **Fonte:** Agência Nacional do Petróleo, Gás Natural e Biocombustíveis ([[ANP]])
- **Papel no Projeto:** Integrar os custos logísticos de transporte rodoviário (diesel) e de preparo doméstico (GLP) à modelagem, explicando variabilidade regional que variáveis macro nacionais (dólar, Selic) não capturam.

**Perguntas avaliadas:**

- **Quais variáveis estão disponíveis?**
    - Preço ao consumidor final (`comb_preco_*`) de 5 produtos: Diesel, Diesel S10, Gasolina, Etanol e GLP 13 kg. _Descartados:_ Diesel S50 (só 2012), gasolina aditivada (começa em out/2020, correlação ~0,99 com a comum), GNV (falta em 45% da grade) e o preço de **compra/distribuidora** (série interrompida pela ANP em 2021).
    - Variações percentuais: mensal (`comb_var_mm_*`) e anual (`comb_var12_*`).
    - Desvio espacial: `comb_diesel_vs_br_pct` (distância do preço da UF à mediana nacional).
    - Auditoria: `comb_n_registros` (nº de postos) e os flags `comb_observado` e `comb_observado_liquidos`.
- **Qual é a granularidade regional?** Por UF. O agregado foi validado contra uma segunda extração (96.049 coletas posto a posto, usada como **testemunha**): 1.149 UF-meses comparados, correlação > 0,99 e erro típico de **0,61%**.
- **Qual é a periodicidade?** Mensal.
- **Qual é a cobertura temporal?** Original de 2004-05 a 2026-07. Na janela do projeto há **lacunas sistêmicas**: 33 meses sem coleta de líquidos, 15 sem GLP e 10 sem nada.
- **Os dados podem ser relacionados aos preços?** Sim. O diesel compõe o frete que escoa a safra; o GLP está na própria cesta do IPCA. **Sinal preliminar:** a correlação entre a variação anual do diesel e a dos alimentos é 0,42 no mesmo mês e 0,49 com o diesel adiantado **4 meses**. É ponto de partida, não conclusão.
- **Quais cuidados metodológicos são exigidos?**
    - **Duplicatas:** 182 casos de UF-mês-produto repetidos (quase todos em abril de 2026). Aplicou-se **média ponderada** pelo número de postos; a média simples errava um mês em até 45%.
    - **A armadilha do _shift_:** as variações só são calculadas **após** reindexar para a grade completa de meses; senão março seria comparado diretamente com julho.
    - **Nulos:** vazio significa que a ANP **não foi a campo** (nacionalmente). Proibidos _forward fill_, interpolação e zeros; usar `comb_observado`.

> [!check] Decisão: ✅ Utilizar (fonte primária de custos logísticos e de cocção) **Justificativa:** entrega o custo de frete agrícola (diesel) e a despesa domiciliar (GLP), com variação **entre estados**. Foi acrescentada à tabela pronta por um único `LEFT JOIN`, sem alterar linhas nem as 89 colunas anteriores.

> [!example] 📌 Na tabela final
> 
> - **19 colunas** `comb_*` (17 com algum vazio). Preços vazios: ~23% (GLP ~10%); `comb_var_mm_*` ~30%; `comb_var12_*` ~39%.
> - ⚠️ **Pendência:** é a única fonte **sem script de download** no repositório (o CSV foi extraído à parte).

---

### 3.9 Critérios de decisão

- ✅ **Utilizar:** apresenta informações relevantes, consistentes e adequadas ao escopo temporal/espacial.
- 🟡 **Utilizar com ressalva:** aproveitada com restrições (ex.: filtro temporal ou flag de cobertura).
- ❌ **Descartar:** não atende à granularidade, qualidade ou histórico necessário.
- 🔄 **Substituir:** há outra fonte de maior frequência ou cobertura para o mesmo fenômeno.
- ⏸️ **Não coletada:** prevista, mas adiada.

---

## 4. Escolha da variável de preço

Avaliamos o [[DIEESE]] (cesta básica) e escolhemos o **IPCA (SIDRA/IBGE)**:

- **Formato:** o DIEESE publica **PDFs** mensais com layout que muda entre anos (tarefa abandonada, ticket T-011); o IPCA vem por **API** em tabela pronta.
- **Métrica estacionária:** variação percentual mensal, sem os vieses de preços nominais em R$ (que teriam tendência e exigiriam deflacionar).
- **Preço por produto:** fechado ao público no DIEESE desde 2018; disponível no IPCA (arroz, tomate, café, carnes...).
- **Cobertura:** DIEESE, 17 capitais; IPCA, 16 áreas urbanas.
- **Estrutura por subitem:** permite isolar choques em produtos específicos contra suas origens produtivas.

---

## 5. Escolha do período analisado

Critérios:

- Disponibilidade simultânea de todas as fontes;
- Ciclos agrícolas completos e anomalias climáticas severas (secas, geadas, El Niño/La Niña);
- Volume amostral suficiente para modelos com defasagens (_lags_).

> [!check] Período escolhido: `2015-01 → 2026-06` (138 meses) **Justificativa:** é o período em que **todas** as fontes existem ao mesmo tempo (junho de 2026 é o último mês que todas têm). Algumas fontes foram baixadas desde antes (IPCA 2006-07; INMET, safra e BCB 2014-01; ANP 2004-05) para permitir acumulados em 12 meses e variáveis defasadas sem perder o início da janela. Cálculos que olham para trás devem ser feitos na série inteira, **antes do corte**.

---

## 6. Granularidade espacial

A análise adota a escala regional como pilar central, permitindo mensurar disparidades entre capitais consumidoras e polos produtores.

✅ **Grão final: UF × mês, formato largo.** UF e mês são as únicas dimensões comuns a todas as fontes.

- **Como cada fonte chega:** IPCA (área urbana → UF), INMET (estação → UF, por mediana), seca e safra (já por UF), BCB (Brasil, repetido em todas as UFs), ANP (UF).
- **Limitações:** o IPCA cobre só 16 UFs (MT, maior produtor de grãos, fica de fora) e o preço é o da capital e arredores.

### Dimensão geográfica

Padronização centralizada via `dim_uf.csv` (códigos IBGE, siglas, nomes, capital e região) para unificar todas as tabelas brutas.