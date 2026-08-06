Para um projeto de 4 meses (um semestre letivo), o segredo da viabilidade é **delimitar o escopo geográfico ou temporal** e focar em variáveis dependentes claras. Tentar abraçar o Brasil inteiro desde 1980 vai esgotar o tempo apenas na etapa de ETL.

Aqui estão 5 perguntas norteadoras viáveis, que exigem a integração de fontes heterogêneas e permitem aplicar desde estatística descritiva espacial até algoritmos de *Machine Learning*:

### 1. Qual o peso das anomalias climáticas locais versus variáveis macroeconômicas na inflação da cesta básica?

* **O Problema:** O preço da comida sobe por causa da seca ou por causa do dólar e do preço do diesel?
* **Como fazer:** Construir um modelo de regressão para prever o índice de preços de alimentos do IPCA (IBGE) usando variáveis macroeconômicas (câmbio, IPCA geral) e anomalias de precipitação/temperatura (INMET) em regiões produtoras chaves ao longo dos últimos 10 anos.
* **Desafio Técnico:** Utilizar métodos baseados em árvores (como Random Forest ou XGBoost) para extrair a *feature importance* e quantificar qual conjunto de variáveis explica melhor a variação de preços.

### 2. É possível prever o risco de quebra de safra municipal combinando dados de transição de uso do solo e déficit hídrico?

* **O Problema:** Antecipar crises de abastecimento antes que elas reflitam no mercado.
* **Como fazer:** Cruzar o histórico de rendimento por hectare de uma cultura sensível (ex: feijão ou milho, via PAM/IBGE) com os dados anuais de transição de cobertura do solo (MapBiomas) e ocorrência de secas extremas (CEMADEN).
* **Desafio Técnico:** Modelar o problema como uma tarefa de classificação (ex: safra normal vs. quebra de safra) e criar um pipeline no Pandas que harmonize dados espaciais (municípios) com séries temporais anuais.

### 3. Como o fenômeno El Niño afeta desproporcionalmente a agricultura familiar em comparação com as *commodities* de exportação?

* **O Problema:** Crises climáticas costumam atingir com mais força quem tem menos tecnologia (irrigação).
* **Como fazer:** Selecionar dois estados contrastantes (ex: Rio Grande do Sul e Ceará) e comparar a variância da produção de culturas de subsistência (mandioca/feijão) versus culturas de exportação (soja) durante anos de El Niño forte (dados climáticos do INPE/NOAA vs. produção da CONAB/IBGE).
* **Desafio Técnico:** Análise de variância, testes de hipótese rigorosos e regressão de dados em painel para isolar o "efeito El Niño" por tipo de cultura.

### 4. Quais microrregiões brasileiras formam *clusters* de vulnerabilidade máxima à insegurança alimentar induzida pelo clima?

* **O Problema:** Identificar onde o governo deveria atuar preventivamente antes de uma seca ou enchente.
* **Como fazer:** Criar um índice composto cruzando dados de internações por desnutrição (DataSUS), concentração de agricultura dependente de chuva (IBGE) e alertas de desastres naturais (CEMADEN).
* **Desafio Técnico:** Utilizar algoritmos de aprendizado não supervisionado (como K-Means ou DBSCAN) para agrupar municípios com perfis de risco semelhantes, gerando visualizações geoespaciais impactantes das zonas de risco.

### 5. Qual o impacto do desmatamento acumulado no microclima local e na produtividade agrícola da região do MATOPIBA?

* **O Problema:** O avanço da fronteira agrícola destrói a própria chuva da qual a agricultura depende?
* **Como fazer:** Focar exclusivamente no MATOPIBA (Maranhão, Tocantins, Piauí, Bahia). Cruzar alertas de desmatamento (DETER/INPE) com a diminuição histórica da precipitação (INMET) e tentar correlacionar isso com a estabilidade da produção de grãos na mesma região (CONAB).
* **Desafio Técnico:** Lidar com defasagem temporal (o desmatamento de hoje afeta o clima em $t+x$ anos). Exige um desenho experimental cuidadoso para evitar correlações espúrias e bom domínio da manipulação de dados contínuos versus eventos pontuais.

---

Qual dessas abordagens — previsão de preços, classificação de risco de safra ou agrupamento de vulnerabilidades regionais — parece se alinhar melhor com a arquitetura e as técnicas de dados que você tem interesse em explorar nesse semestre?