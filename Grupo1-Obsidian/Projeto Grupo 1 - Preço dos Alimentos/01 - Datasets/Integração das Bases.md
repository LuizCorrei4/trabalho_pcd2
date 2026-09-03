Modelo de Preços de Alimentos (T-024)

## 1. Objetivo do Módulo

O script `24_junta.py` é o motor central de consolidação de dados do projeto. Seu objetivo é integrar cinco fontes de dados multimodais (preços, clima, agricultura e macroeconomia) em uma única tabela analítica (Fato) na granularidade de **Unidade Federativa (UF) × Mês**, cobrindo o período de **Janeiro de 2015 a Junho de 2026**.

Esta tabela final servirá como base para modelar como choques climáticos, agrícolas e custos de transporte/cocção afetam a inflação de alimentos nas diferentes regiões do país.

## 2. Decisões Arquiteturais de Engenharia de Dados

O código foi desenhado para garantir rastreabilidade, evitar perda silenciosa de dados e prevenir a explosão de dimensionalidade (produto cartesiano indevido).

- **A Espinha Dorsal (Calendário Completo):** A junção não parte de uma base aleatória, mas da função `monta_calendario()`. Ela cria um produto cartesiano perfeito de 27 UFs × 138 meses (3.726 linhas).      
    - _Justificativa:_ Ao usar a espinha como base para operações de `LEFT JOIN`, garantimos que perdas de dados por chaves ausentes sejam mapeadas. As 11 UFs que não possuem cobertura do IPCA são descartadas apenas no filtro final, permitindo contabilizar a perda com transparência. A integração de combustíveis não altera a espinha, utilizando um LEFT JOIN estrito.
- **Transformação Longa para Larga (Pivotamento):** Bases nativamente "longas" (como IPCA, que varia por item, Safra, que varia por produto) e Combustíveis são pivotadas (`pivot_table`) antes do merge.    
    - _Justificativa:_ Se a base de safra (11 produtos) fosse cruzada no formato longo, a espinha seria multiplicada por 11, gerando mais de 40 mil duplicatas geográficas/temporais. O pivotamento achata a estrutura mantendo a granularidade UF × Mês estrita.
- **Agregação Ponderada:** Os registros de combustíveis sofreram agregação por média ponderada pelo volume de postos (`quantidade_registros`). Isso elimina vieses de até 45% causados por coletas isoladas super-representadas em médias simples.
- **Linhagem Clara (Prefixos vs. Sufixos):** O uso de sufixos automáticos do Pandas (`_x`, `_y`) foi proibido. Todas as colunas ganham o prefixo de sua fonte de origem antes do join (`ipca_`, `safra_`, `clima_`, `seca_`, `macro_`).
- **Validação Contínua (`checa_join`):** Como merges entre tipos diferentes (ex: `str` e `Timestamp`) no Pandas retornam nulos silenciosamente em vez de erro, o código impõe um teste de sanidade coluna a coluna após cada operação de junção.
- **Controle da Armadilha Temporal:** As variações mensais e anuais de preço dos combustíveis só foram calculadas após a reindexação na grade de meses completa. O uso de `shift(1)` em dados com lacunas geraria falsas variações entre meses distantes.
## 3. Justificativa das Fontes e Regras de Negócio Aplicadas

As decisões de inclusão, exclusão e transformação de variáveis foram baseadas na avaliação de qualidade e aderência estatística das fontes:
### 3.1. Variável-Alvo: Inflação de Alimentos (IPCA - IBGE/SIDRA)

- **Por que foi escolhida:** Preferida em relação ao DIEESE por ser uma métrica estacionária (variação percentual), ter pesos orçamentários robustos e cobrir 16 praças urbanas em uma série histórica ininterrupta.    
- **Tratamento no código:**
    - **Filtro de Itens:** Selecionamos propositalmente 17 itens em três níveis hierárquicos (grupo, subgrupo e subitem) para focar na cesta básica.
    - **Alvos Criados:** Além da variação mensal, o código calcula o **acumulado de 12 meses** (via produtório móvel) e a **inflação relativa** (`ipca_var_alimentacao_relativa`), que subtrai a inflação geral da inflação de alimentos. Isso isola o "excesso" de alta da comida, eliminando o efeito inercial geral da economia.
### 3.2. Choques de Oferta: Safra (IBGE/LSPA)

- **Por que foi escolhida:** Foi priorizada sobre a CONAB porque a CONAB possui apenas granularidade anual para o período antigo. O LSPA oferece expectativas de safra _mensais_ por UF.
- **Tratamento no código:**
    - **Controle de Outliers:** A variável de revisão percentual (`revisao_pct_prod`) sofre um _clipping_ (corte) em ±50%. Sem isso, divisões por bases minúsculas geravam caudas explosivas de até 15 milhões %, o que destruiria qualquer regressão linear.
### 3.3. Choques Climáticos: Clima (INMET) e Seca (ANA)

- **Por que foram escolhidas:** Complementam-se. O INMET traz variáveis contínuas e agudas (picos de calor, chuvas extremas), enquanto a ANA traz um índice validado por especialistas sobre a extensão e memória de secas severas.
- **Tratamento no código:**
    - Mantidas na granularidade de UF × Mês. A integração direta exige cuidado na interpretação dos nulos (ver seção 4).        
### 3.4. Contexto Exógeno: Macroeconomia (BCB)

- **Por que foi escolhida:** Essencial para separar o que é choque climático do que é impacto do dólar (insumos/fertilizantes) ou dos juros.    
- **Tratamento no código:**    
    - Como as variáveis são nacionais (Série SGS), sofrem _broadcast_: o `LEFT JOIN` via `ano_mes` repete os mesmos valores de câmbio, juros e IGP-M para todas as UFs naquele mês específico.
### 3.5. **Custos Logísticos e Cocção (ANP)**
O Diesel dita o frete agrícola e o GLP é essencial na cesta domiciliar. Eles inserem a dimensão espacial de custo ignorada pelas métricas macroeconômicas (como Selic e Dólar). Apenas Diesel, Diesel S10, Gasolina, Etanol e GLP 13kg foram mantidos. O preço de compra/distribuidora foi descartado devido à interrupção permanente da série pela ANP em 2021.
## 4. Estratégia de Tratamento de Dados Ausentes (NaNs)

O rigor analítico deste script se destaca na diferenciação semântica dos dados nulos (NaN), documentada ativamente na função `_descreve` e enviada ao `dicionario_variaveis.csv`:
1. **Safra (Ausência vs. Indefinição):** Se a `producao_t` é NaN, significa que aquele Estado não planta aquele produto (ausência estrutural). O código imputa **zero (0.0)**. Porém, a `revisao_pct` permanece NaN, pois não há o que revisar se a cultura não existe ali (ou se é o mês de janeiro, início do ciclo).
2. **Monitor de Secas ANA (Ausência de Medição vs. Sem Seca):** Um NaN na seca não significa "não houve seca", mas sim que a UF **não era monitorada** naquele ano (o programa começou no Nordeste em 2014 e chegou ao Norte/Sul apenas em 2023). O código cria o flag `seca_monitorado` para evitar que um modelo de machine learning entenda o NaN como "clima normal".
3. **Clima (Qualidade Instrumental):** Nulos mantidos representam meses em que as estações tiveram falhas instrumentais severas (menos de 70% de dias válidos), preferindo-se o vazio a imputar uma média mascarada por falta de coleta.
4. **Combustíveis (Lacunas Sistêmicas):** `NaN` indica estritamente a interrupção nacional da pesquisa pela ANP (33 meses sem líquidos, 15 sem GLP). É proibida a imputação por zeros. O controle de dados válidos é garantido em modelagem pelos booleanos `comb_observado` e `comb_observado_liquidos`.

## 5. Saídas (Deliverables)

A execução deste pipeline entrega:
1. `calendario_uf_mes.parquet`: Grade completa (3.726 linhas) para auditoria.    
2. `fato_alimentos_uf_mes.parquet`: A tabela final de modelagem, com **2.088 linhas** (apenas as 16 UFs com medição de inflação ativa) e dezenas de features integradas (alvos, clima, safra e macro).
3. `dicionario_variaveis.csv`: Um dicionário de dados automatizado contendo metadados (unidade, origem, % de nulos e justificativas de negócio), garantindo que os cientistas de dados que assumirão a próxima etapa compreendam as premissas geográficas e de preenchimento de cada coluna.
4. **fato_alimentos_combustiveis_uf_mes.parquet:** Tabela final com 2.088 linhas rastreáveis (16 UFs) e expansão estrutural para 108 colunas.
5. **dicionario_variaveis_combustiveis.csv:** Metadados catalogados das 19 novas variáveis, assegurando transparência na interpretação dos nulos.