# Modelo de Preços de Alimentos (T-024)

> Notas técnicas da junção. Decisões gerais em [[Decisões e Justificativas do Projeto]]; avaliação das fontes em [[Resumo]]. Passo a passo com exemplos: notebook `08_decisoes_e_resultado_da_juncao.ipynb`.

## 1. Objetivo do módulo

Os scripts `24_junta.py` (junção principal) e `25_combustiveis.py` (segunda junção) são o motor de consolidação do projeto. Integram **seis fontes** (IPCA, clima, safra, seca, macroeconomia e combustíveis) em uma única tabela analítica (Fato) na granularidade **Unidade Federativa (UF) × Mês**, de **janeiro de 2015 a junho de 2026**.

- `24_junta.py` integra **cinco** fontes: IPCA, clima, safra, seca e macro (resultado: 2.088 linhas × 89 colunas);
- `25_combustiveis.py` **acrescenta** a ANP à tabela já pronta (resultado: 2.088 linhas × 108 colunas).

A tabela final servirá de base para modelar como choques climáticos, agrícolas e custos de transporte/cocção afetam a inflação de alimentos nas diferentes regiões do país.

## 2. Decisões arquiteturais de engenharia de dados

O código foi desenhado para garantir rastreabilidade, evitar perda silenciosa de dados e prevenir a explosão de linhas (produto cartesiano indevido). As armadilhas encontradas são do tipo que **não dá erro nenhum**: só produzem um número errado.

- **A espinha dorsal (calendário completo):** a junção parte de `monta_calendario()`, um produto cartesiano de **27 UFs × 138 meses = 3.726 linhas**.
    - _Justificativa:_ com a espinha como base de `LEFT JOIN`, nenhuma linha some no meio do caminho. A perda acontece em **um único filtro, no fim**, e é contada. As 11 UFs sem IPCA são descartadas só nesse filtro. Começar pelo IPCA com `INNER JOIN` descartaria linhas sem aviso a cada passo.
    - Cada junção preenche: IPCA 56,0 % (o alvo só existe em 16 UFs), clima 96,9 %, safra 100 %, seca 63,6 %, macro 100 %.
- **Formato do mês: `Period[M]`.** O mês chega como texto (`"2015-01"`), data (`2015-01-01`) ou período. Converter tudo para texto parece o caminho óbvio, mas `"2015-01"` nunca encontra `"2015-01-01"`: no dado real, a safra voltou com **0 de 3.726** valores preenchidos, sem erro. Com `Period[M]` (sem dia) isso não acontece. A UF é sempre sigla de 2 letras maiúsculas.
- **Transformação longa para larga (pivotamento):** fontes com mais de uma linha por UF-mês (IPCA por item, safra por produto, combustíveis por produto) são pivotadas (`pivot_table`) antes do merge.
    - _Justificativa:_ juntando a safra (11 produtos) no formato longo, a tabela iria de **3.726 para 40.986 linhas**, e a taxa de preenchimento (79,6 %) ainda pareceria saudável.
- **Linhagem clara (prefixos em vez de sufixos):** os sufixos automáticos do Pandas (`_x`, `_y`) foram proibidos. Toda coluna ganha o prefixo da fonte antes do join (`ipca_`, `safra_`, `clima_`, `seca_`, `macro_`, `comb_`). Colunas repetidas sem utilidade (`ano`, `mes`) foram descartadas, não renomeadas.
- **Validação contínua (`checa_join`, em `src/tratamento/chaves.py`):** roda depois de **cada** junção. Compara o número de linhas antes e depois e a taxa de preenchimento, e **interrompe a execução** se as linhas mudaram ou se nada casou. Funções irmãs: `padroniza_chaves` (converte UF e mês para o formato combinado) e `valida_chaves` (recusa UF fora do padrão, mês que não seja `Period[M]` e chave repetida).
- **Agregação ponderada (combustíveis):** a ANP traz 182 casos de UF-mês-produto repetidos (quase todos em abril de 2026, duas rodadas de coleta). Usa-se média ponderada por `quantidade_registros` (número de postos). A média simples errava um mês em até **45 %** (exemplo: GLP no Pará em fev/2008, R$ 17,98 contra R$ 32,91 corretos).
- **Controle da armadilha temporal:** variações mensais e anuais dos combustíveis só são calculadas **após** reindexar para a grade completa de meses. Com `shift(1)` sobre dados com lacunas, a "variação de julho" seria calculada contra março (alta falsa de ~7 % no exemplo de São Paulo, 2018).
- **Acréscimo, não refação:** os combustíveis entraram com **um único `LEFT JOIN`** sobre a tabela pronta, com a mesma verificação. Resultado: 2.088 → 2.088 linhas, 89 → 108 colunas, e as 89 colunas anteriores **idênticas** às de antes.
- **Linhas da tabela final:** 16 UFs × 138 meses = 2.208, menos 120 meses (AC, MA e SE só entram no IPCA em **2018-05**, 40 meses cada) = **2.088 linhas**.

## 3. Justificativa das fontes e regras de negócio aplicadas

### 3.1. Variável-alvo: inflação de alimentos (IPCA — IBGE/SIDRA)

- **Por que foi escolhida:** preferida ao DIEESE (cesta básica em PDF, com layout que muda entre anos, preço por produto fechado desde 2018 e valor em R$ com tendência). O IPCA é variação percentual (estacionária), vem por API, tem pesos orçamentários e traz o preço por produto, em 16 áreas urbanas.
- **Tratamento no código:**
    - **Tabelas encadeadas:** nenhuma tabela do SIDRA cobre o período todo. Encadeia-se **2938** (2006–2011) → **1419** (2012–2019) → **7060** (2020–2026), mesma pesquisa e mesmos códigos de item. A 7062 foi rejeitada: é o IPCA-15, outro índice.
    - **Dois níveis territoriais:** N7 (10 regiões metropolitanas) + N6 (6 municípios). O IPCA não tem nível "UF" (o N3 devolve erro 404); só com N7 se perderiam Brasília, Goiânia, Campo Grande, São Luís, Aracaju e Rio Branco. A conversão para UF usa os 2 primeiros dígitos do código IBGE.
    - **Itens identificados pelo código, não pelo nome:** o IBGE renomeia itens no meio da série (40 códigos com 42 nomes).
    - **Limpeza dos marcadores "sem dado":** o SIDRA escreve `-`, `...` ou `X` quando o valor não foi publicado. A primeira versão apagava o caractere `-` de todo o texto, e **toda queda de preço virou alta** (valores negativos: 0 no arquivo errado contra 32.696 no corrigido; média mensal de 3,14 % contra 0,75 %). A correção anula só o texto que é, inteiro, um marcador, e os dados foram baixados de novo. A junção agora **falha de propósito** se o alvo não tiver nenhum mês de deflação.
    - **Filtro de itens:** 17 códigos com cobertura completa na janela (o 18º já cai para 92 %), em três níveis hierárquicos (grupo, subgrupo, subitem). Cada um gera `ipca_var_*` e `ipca_peso_*`. **Não somar os pesos** (o frango seria contado duas vezes).
    - **Alvos criados:** variação mensal, **acumulado de 12 meses** (produtório móvel: composto, não somado) e **inflação relativa** (`ipca_var_alimentacao_relativa`), que subtrai a inflação geral da de alimentos e isola o "excesso" de alta da comida.

### 3.2. Choques de oferta: safra (IBGE/LSPA + PAM)

- **Por que foi escolhida:** priorizada sobre a CONAB, que só tem granularidade **anual por ano-safra**. O LSPA oferece estimativas **mensais** por UF.
- **Tratamento no código:**
    - Tabela 6588 (LSPA) + PAM (1612 e 1613); **11 produtos** (arroz, feijão, milho, soja, trigo, café, banana, batata-inglesa, tomate, mandioca, cana-de-açúcar). Safras que o IBGE separa são somadas (feijão 1ª/2ª/3ª, milho 1ª/2ª, café arábica/canéfora, batata das 3 safras). O rendimento (kg/ha) é **recalculado** como produção total ÷ área total.
    - **Medidas levadas à tabela final:** apenas `safra_producao_t_*` e `safra_revisao_pct_*` (2 × 11 = **22 colunas**). Área plantada, área colhida e rendimento ficam em `data/interim/`.
    - **Controle de outliers:** a revisão percentual sofre _clipping_ em **±50 %** (winsorização). Sem isso, divisões por estimativas anteriores quase nulas geravam valores de até 15 milhões %. 99,1 % dos valores ficaram intactos.
    - Cada linha é a estimativa da safra do **ano inteiro** vigente naquele mês, não o colhido no mês: somar 12 meses multiplicaria a produção por 12.

### 3.3. Choques climáticos: clima (INMET) e seca (ANA)

- **Por que foram escolhidas:** complementam-se. O INMET traz variáveis contínuas e agudas (picos de calor, chuvas extremas); a ANA traz um índice validado por especialistas sobre a extensão e a memória de secas severas.
- **Tratamento — INMET:**
    - Leitura de ~1,27 GB (13 ZIPs anuais, dados **por hora**) um ano e um arquivo por vez; colunas encontradas **pelo nome** (o formato mudou em 2019); `-9999` tratado como vazio.
    - Ordem **hora → dia → mês**. Um dia só vale com ≥ 18 horas medidas, grandeza por grandeza. Soma com `min_count=1` (dia sem medição não vira "0 mm"). Índices de extremo (dias sem chuva, maior sequência seca, calor extremo = acima do percentil 90 da própria estação naquele mês) são calculados **a partir dos dias**.
    - **Agregação por UF: mediana** entre estações (somar não tem sentido físico; a média é puxada por sensor com defeito). Estação-mês com menos de 70 % dos dias medidos vira vazio (22,8 % das estação-mês).
    - **Ficaram de fora:** direção do vento (é um ângulo) e as máximas/mínimas **absolutas** (a mediana dos recordes de cada estação não descreve nem o extremo nem o típico).
    - A tabela traz `clima_n_estacoes` (quantas estações entraram na mediana).
- **Tratamento — ANA:**
    - Não há CSV: usa-se a **API REST que o próprio site usa**, uma requisição por UF. O campo `area` é o **% do território da UF** em seca, e as categorias são **cumulativas** (S2 = "grave ou pior"). A própria ANA já agrega município → UF.
    - Quando um mês é revisado, a API devolve todas as versões juntas (algumas com escala ×100 ou valores de teste, como `123456`). Usa-se a **versão de maior `id`** (vigente) e as divergências (49 UF-meses) são gravadas em `outputs/tabelas/monitor_secas_revisoes_divergentes.csv`. Um mês do Maranhão que viola a regra cumulativa recebe `inconsistente = True`, sem inventar valor.
- Ambas mantidas em UF × mês. A interpretação dos nulos está na seção 4.

### 3.4. Contexto exógeno: macroeconomia (BCB)

- **Por que foi escolhida:** essencial para separar o que é choque climático do que é impacto do dólar (insumos/fertilizantes) ou dos juros.
- **Tratamento no código:**
    - Cinco séries SGS (dólar PTAX, IPCA cheio, Selic meta, Selic efetiva, IGP-M). Dólar vira **média do mês** e **valor do último dia**; Selic meta, valor do fim do mês; Selic efetiva, composta no mês.
    - **Armadilha da API:** pedindo mais de 10 anos de uma vez, ela responde "OK" mas **devolve dados cortados**. O coletor pede em blocos de 10 anos e confere o período devolvido. Valores conferidos com números oficiais (dólar médio de março/2020 = R$ 4,88).
    - **Broadcast:** o `LEFT JOIN` por `ano_mes` repete os mesmos valores em todas as UFs. Essas colunas explicam variação **no tempo**, nunca diferença entre estados.
    - Na tabela final entram 5 colunas `macro_*`.

### 3.5. Custos logísticos e cocção (ANP)

O diesel dita o frete agrícola e o GLP é essencial na cesta domiciliar. Eles inserem a dimensão **espacial** de custo, ignorada pelas métricas macro (Selic, dólar), que são iguais no país inteiro.

- **Mantidos:** Diesel, Diesel S10, Gasolina, Etanol e GLP 13 kg, só **preço de venda ao consumidor**.
- **Descartados:** Diesel S50 (só existe em 2012, 73 linhas), gasolina aditivada (começa em out/2020; correlação ~0,99 com a comum), GNV (falta em 45 % da grade), e o preço de **compra/distribuidora** (a ANP parou de publicar em 2021).
- **Validação:** o agregado foi comparado com uma segunda extração, mais detalhada (96.049 coletas posto a posto), usada como **testemunha**: 1.149 UF-meses comparados, correlação > 0,99 em todos os produtos, erro típico (mediana do erro absoluto) de **0,61 %**.
- **Pendência:** é a única fonte **sem script de download** no repositório (o CSV foi extraído à parte).

## 4. Estratégia de tratamento de dados ausentes (NaNs)

O rigor analítico se destaca na diferenciação semântica dos nulos, documentada na função `_descreve` e enviada ao dicionário de variáveis. **Cada vazio é uma afirmação diferente sobre o mundo.**

1. **Safra (ausência vs. indefinição):**
    - `safra_producao_t_*`: vazio significa que a UF **não planta** o produto. Imputa-se **zero (0,0)** (zero tonelada é verdade; a grade do LSPA é completa, então o vazio nunca é falha de medição). Resultado: 0 % de vazios.
    - `safra_revisao_pct_*`: **permanece NaN**. Zero diria "a estimativa não mudou", que é outra afirmação. Também é vazia em **todo janeiro** (não há mês anterior na mesma safra). Vazios de 9 a 53 %.
2. **Monitor de Secas ANA (ausência de medição vs. sem seca):** NaN significa que a UF **não era monitorada** naquele mês. O programa começou no **Nordeste**; Centro-Sul entrou por volta de 2020/2021 e estados do Norte (RR, AP) só em 2023, com o país inteiro coberto apenas a partir de 2023. Dos 3.726 UF-meses, 1.358 (36 %) são anteriores à entrada da UF. O flag `seca_monitorado` impede que o modelo entenda NaN como "clima normal". Nas 16 UFs do alvo, a cobertura de seca medida é 65,8 % (2015-01 em diante), 77,9 % (2018), **90,5 % (2020-01 em diante)** e 100 % (2024).
    - _Recomendação:_ quem usar seca deve filtrar por `seca_monitorado` ou recortar a partir de **2020-01**. Preencher com 0 faria o modelo confundir "seca" com "ser do Nordeste".
3. **Clima (qualidade instrumental):** antes de agregar, estação-mês com menos de 70 % dos dias válidos vira vazio. Na tabela por UF, o vazio restante (0,3 %) indica que **nenhuma estação** passou do corte. Prefere-se o vazio a imputar uma média que mascare a falta de coleta. Há dois problemas estruturais: **Roraima** (1 estação, sem medição em 2021 e 2026) e um **buraco nacional em 2021–2022** (ex.: RN cai de 100 % para 38 % de cobertura em 2021, justamente o ano da crise hídrica). A rede de estações também cresce (475 em 2014, 638 em 2026): um degrau na série que coincide com salto no número de estações é efeito da rede, não do clima.
4. **Combustíveis (lacunas sistêmicas):** NaN indica estritamente que a ANP **não foi a campo** naquele mês (33 meses sem líquidos, 15 sem GLP, 10 sem nada). É **proibida** a imputação por zero, interpolação ou _forward fill_ (interpolar inventaria preço em ~23 % das linhas). O controle é feito por `comb_observado` (qualquer produto) e `comb_observado_liquidos` (diesel, gasolina, etanol). As variações `comb_var_mm_*` (~30 % vazias) e `comb_var12_*` (~39 %) ficam vazias quando falta o mês atual **ou** o de comparação.
5. **IPCA acumulado em 12 meses:** 1,6 % de vazios, nos primeiros meses de AC, MA e SE (ainda sem 12 meses de histórico).

## 5. Saídas (deliverables)

1. `calendario_uf_mes.parquet`: grade completa (3.726 linhas) para auditoria. Também serve para calcular **variáveis defasadas antes do filtro final**, senão os primeiros meses de AC, MA e SE ficam sem passado.
2. `fato_alimentos_uf_mes.parquet`: tabela da primeira junção, **2.088 linhas × 89 colunas** (16 UFs com IPCA).
3. `dicionario_variaveis.csv`: dicionário automatizado (unidade, origem, % de nulos e justificativa de cada vazio) para a primeira junção.
4. `fato_alimentos_combustiveis_uf_mes.parquet`: **tabela final**, 2.088 linhas rastreáveis e **108 colunas** (19 novas de combustíveis). Chave `(sigla_uf, ano_mes)`, sem repetição.
5. `dicionario_variaveis_combustiveis.csv`: dicionário da tabela final, com **uma linha por coluna (as 108)**, incluindo as 19 novas. O código falha se alguma coluna com mais de 40 % de vazios ficar sem justificativa. 61 das 108 colunas não têm nenhum vazio.

## 6. Como saber se a junção está certa

Uma junção pode **rodar** e mesmo assim estar **errada**. Além dos testes de estrutura (chave única, 2.088 linhas, mês no formato certo, preços em faixas possíveis, alvo com deflação), conferimos eventos históricos conhecidos:

|Evento conhecido|O que a tabela mostra|
|---|---|
|Seca histórica do Ceará (jan/2017)|100 % do estado em seca grave ou pior; severidade 4,52 de 5|
|Alta dos alimentos na pandemia|pico de 18,1 % em 12 meses em nov/2020|
|Estação chuvosa no Norte e Centro-Oeste|chuva mediana de 226 mm em janeiro, contra 13 mm em agosto|
|Choque do diesel após a invasão da Ucrânia|+62 % em 12 meses em jul/2022 e −34 % em jul/2023|