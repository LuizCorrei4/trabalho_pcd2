> **Projeto:** O que realmente move o preço da comida no Brasil?  
> **Subtítulo:** Anomalias climáticas, custo logístico e macroeconomia na volatilidade regional da cesta básica

Esta nota registra as principais decisões tomadas ao longo do desenvolvimento do projeto e as justificativas para cada uma delas. O objetivo é manter um histórico das escolhas metodológicas, facilitando a compreensão, reprodução e apresentação do projeto.

---

## 1. Escolha do tema

### Contexto

O projeto surgiu a partir de uma discussão sobre possíveis relações entre fenômenos climáticos e impactos econômicos. Inicialmente, foram consideradas diferentes possibilidades, como:

- Ondas de calor na Europa;
- Impactos do El Niño na economia;
- Relações entre eventos climáticos e preços de alimentos.

Após discutir a disponibilidade de dados, a possibilidade de integração entre diferentes fontes e a relevância do problema, decidimos investigar a relação entre **anomalias climáticas, custos logísticos, fatores macroeconômicos e preços de alimentos no Brasil**.

### Por que escolhemos este tema?

A escolha foi motivada principalmente por:

- **Relevância econômica:** alimentos possuem impacto direto no orçamento das famílias e na inflação;
- **Relevância regional:** os preços podem variar significativamente entre diferentes regiões do Brasil;
- **Possível influência climática:** eventos extremos e alterações nas condições climáticas podem afetar produção e oferta de alimentos;
- **Influência logística:** custos de transporte e distribuição podem contribuir para diferenças regionais nos preços;
- **Influência macroeconômica:** inflação, câmbio, juros e outras variáveis econômicas podem afetar os preços dos alimentos;
- **Integração de diferentes fontes:** o problema permite combinar dados climáticos, agrícolas, econômicos e de preços.

### Pergunta central

> **Quais fatores ajudam a explicar a volatilidade regional dos preços dos alimentos no Brasil?**

A partir dessa pergunta, buscamos investigar principalmente a contribuição de:

1. Anomalias climáticas;
2. Produção e estimativas de safra;
3. Custos logísticos;
4. Variáveis macroeconômicas;
5. Características regionais.

---

## 2. Hipóteses iniciais

Antes da análise dos dados, estabelecemos algumas hipóteses que serão investigadas ao longo do projeto.

### H1 — Clima

Anomalias climáticas podem estar associadas a alterações na produção agrícola e, consequentemente, à variação dos preços dos alimentos.

### H2 — Produção agrícola

Variações na produção ou nas estimativas de safra podem ajudar a explicar movimentos nos preços dos alimentos.

### H3 — Logística

Diferenças nos custos e condições logísticas podem contribuir para a maior volatilidade dos preços em determinadas regiões.

### H4 — Macroeconomia

Variáveis macroeconômicas podem influenciar os preços dos alimentos independentemente de fatores climáticos e produtivos.

### H5 — Efeito regional

A magnitude desses efeitos pode variar entre estados ou regiões brasileiras.

> **Observação:** As hipóteses ainda não foram validadas. Elas serão testadas durante a exploração e modelagem dos dados.

---

## 3. Levantamento e avaliação das fontes de dados

Nesta etapa do projeto, ainda não definimos quais bases serão utilizadas na análise final.

O objetivo inicial é **levantar, explorar e avaliar diferentes fontes de dados** que possam contribuir para responder à pergunta central do projeto:

> Quais fatores ajudam a explicar a volatilidade regional dos preços dos alimentos no Brasil?

As bases estão sendo avaliadas considerando principalmente:

- relevância para o problema de pesquisa;
- disponibilidade de variáveis relacionadas às nossas hipóteses;
- cobertura temporal;
- cobertura geográfica;
- periodicidade;
- granularidade por Unidade Federativa (UF);
- qualidade e completude dos dados;
- possibilidade de integração com as demais fontes;
- compatibilidade entre as diferentes bases.

### Bases atualmente em avaliação

| Base                      | Fonte/Instituição       | Possível contribuição                                                       | Status        |
| ------------------------- | ----------------------- | --------------------------------------------------------------------------- | ------------- |
| `bcb_var_macroeconômicas` | Banco Central do Brasil | Variáveis macroeconômicas que podem ajudar a explicar a variação dos preços | Em avaliação  |
| `conab`                   | CONAB                   | Informações relacionadas à produção/safra agrícola                          | Em avaliação  |
| `estimativas_safra_UF`    | A definir               | Estimativas de safra com granularidade por UF                               | Em avaliação  |
| `sidra_ipca`              | IBGE / SIDRA            | Variações de preços/IPCA de alimentos                                       |  Em avaliação |

> **Importante:** a presença de uma base no repositório não significa que ela será necessariamente utilizada no modelo final. A decisão será tomada após a exploração e avaliação dos dados.

---

### 3.1 `bcb_var_macroeconômicas`

**Fonte:** Banco Central do Brasil

**Possível papel no projeto:**  
Investigar se variáveis macroeconômicas apresentam relação com a volatilidade dos preços dos alimentos.

**Perguntas a responder durante a avaliação:**

- Quais variáveis estão disponíveis?
- Qual é a periodicidade?
- Existe cobertura para todo o período escolhido?
- Essas variáveis possuem relação plausível com o preço dos alimentos?
- É possível integrá-las aos dados regionais?

**Decisão:** `A definir`

**Justificativa:** `A preencher após exploração.`

---

### 3.2 `conab`

**Fonte:** Companhia Nacional de Abastecimento (CONAB)

**Possível papel no projeto:**  
Fornecer informações relacionadas à produção agrícola e às condições de oferta de produtos agrícolas.

**Perguntas a responder durante a avaliação:**

- Quais produtos estão disponíveis?
- Existe informação por estado ou região?
- Qual é a periodicidade?
- Qual é a cobertura temporal?
- Os dados podem ser relacionados aos preços observados?
- Há sobreposição ou complementaridade com `estimativas_safra_UF`?

**Decisão:** `A definir`

**Justificativa:** `A preencher após exploração.`

---

### 3.3 `estimativas_safra_UF`

**Fonte:** `A definir`

**Possível papel no projeto:**  
Representar variações nas estimativas de safra em nível estadual, permitindo investigar possíveis relações entre produção agrícola e preços regionais.

A existência da dimensão de UF pode facilitar a integração com outras fontes que também possuem granularidade estadual.

**Perguntas a responder durante a avaliação:**

- Quais culturas estão disponíveis?
- Como as estimativas são calculadas?
- Qual é a periodicidade?
- Qual é a cobertura temporal?
- Como as UFs estão identificadas?
- Há dados suficientes para todo o período analisado?
- Essa base acrescenta informação em relação à CONAB?

**Decisão:** `A definir`

**Justificativa:** `A preencher após exploração.`

---

### 3.4 `sidra_ipca`

**Fonte:** IBGE / SIDRA

**Possível papel no projeto:**  
Fornecer informações relacionadas à variação dos preços de alimentos ao longo do tempo.

Durante a exploração inicial, o SIDRA foi considerado uma alternativa ao uso direto dos dados de cesta básica do DIEESE, especialmente pela disponibilidade de informações de variação mensal do IPCA e de pesos dos itens.

Entretanto, a utilização definitiva dessa fonte ainda depende da avaliação de sua adequação à pergunta de pesquisa e da possibilidade de integração com as demais bases.

**Perguntas a responder durante a avaliação:**

- Quais subitens de alimentação estão disponíveis?
- Qual é a granularidade regional?
- Qual é o período disponível?
- Como os pesos são utilizados?
- É possível construir uma medida adequada de variação de preços para o projeto?
- Como essa variável poderá ser integrada às variáveis climáticas, agrícolas, logísticas e macroeconômicas?

**Decisão:** `A definir`

**Justificativa:** `A preencher após exploração.`

---

## 3.5 Critérios de decisão

Ao final da etapa de exploração, cada fonte deverá receber uma decisão:

- ✅ **Utilizar** — apresenta informações relevantes e adequadas ao projeto;
- 🟡 **Utilizar parcialmente** — apenas algumas variáveis serão aproveitadas;
- ❌ **Descartar** — não apresenta informação suficiente ou adequada;
- 🔄 **Substituir** — existe outra fonte mais adequada para representar a mesma variável.

A decisão deve ser acompanhada de uma justificativa.

### Exemplo

> **CONAB — Utilizar parcialmente**
>
> A base possui informações relevantes sobre produção agrícola, porém determinadas variáveis apresentam cobertura temporal/geográfica incompatível com o restante do projeto. Serão utilizadas apenas as variáveis que puderem ser integradas ao conjunto principal de dados.

---

## 3.6 Histórico de avaliação

| Data | Base | Ação | Resultado |
|---|---|---|---|
| 13/08/2026 | BCB | Exploração | Coletor macro construído |
| 13/08/2026 | CONAB | Exploração | Em avaliação |
| 13/08/2026 | Estimativas de safra por UF | Construção/exploração | Coletor criado |
| 13/08/2026 | SIDRA/IBGE | Exploração | Série histórica de inflação alimentar adicionada |

---

## 4. Critérios para escolha das bases

As bases não serão escolhidas apenas pela disponibilidade. Para cada fonte, devemos registrar:

- O que a base mede?
- Qual é a unidade de medida?
- Qual é a periodicidade?
- Qual é a cobertura geográfica?
- Qual é o intervalo temporal?
- Existe granularidade por UF?
- Os dados possuem valores faltantes?
- É possível relacionar os dados com as demais fontes?
- A variável realmente responde à nossa pergunta de pesquisa?

### Justificativa das bases escolhidas

> **A preencher após a confirmação da equipe.**

Para cada base utilizada, documentaremos:

**Base:**  
**Fonte:**  
**Variáveis utilizadas:**  
**Período:**  
**Granularidade:**  
**Por que foi escolhida:**  
**Por que outras fontes foram descartadas:**  
**Limitações:**

---

## 5. Escolha da variável de preço

Durante a exploração das fontes de preços, consideramos diferentes possibilidades.

O DIEESE foi avaliado como uma possível fonte para dados relacionados à cesta básica.

Entretanto, optamos por utilizar dados do **SIDRA/IBGE**, considerando a disponibilidade de variações mensais do IPCA e de informações relacionadas ao peso dos itens.

A escolha foi motivada pela necessidade de trabalhar com uma medida que permita analisar a **variação dos preços ao longo do tempo e entre diferentes regiões**, em vez de utilizar somente o preço absoluto de uma cesta básica.

> **A justificativa completa será revisada após definirmos exatamente quais tabelas e variáveis do SIDRA serão utilizadas.**

---

## 6. Escolha do período analisado

O intervalo temporal escolhido deve ser justificado considerando:

- disponibilidade simultânea das diferentes fontes;
- periodicidade dos dados;
- quantidade de observações;
- existência de eventos climáticos relevantes;
- disponibilidade de dados econômicos e agrícolas;
- possibilidade de observar períodos de normalidade e de anomalias.

**Período escolhido:** `A DEFINIR`

**Justificativa:**  
`A preencher após confirmação do período utilizado pela equipe.`

---

## 7. Granularidade espacial

Uma das decisões importantes do projeto é trabalhar com dados em nível regional.

A análise deverá considerar, quando possível:

- Brasil;
- Unidades Federativas (UFs);
- eventualmente regiões brasileiras.

A utilização da UF como unidade de análise permite investigar se os fatores associados à variação dos preços apresentam comportamentos diferentes entre regiões.

### Dimensão geográfica

Foi criada uma dimensão de UF (`dim_uf.csv`) para facilitar a integração das diferentes bases e padronizar as informações geográficas.

---

## 8. Integração das bases

O projeto depende da integração de diferentes fontes de dados.

A integração deverá considerar principalmente:

**Chaves de integração:**

- UF;
- período (ano/mês);
- eventualmente produto/categoria.

### Desafio

As diferentes fontes podem apresentar:

- periodicidades diferentes;
- nomenclaturas diferentes para estados;
- unidades de medida diferentes;
- períodos de cobertura diferentes;
- diferentes níveis de agregação.

Por isso, parte do trabalho consiste em realizar a padronização antes da análise.

---

# Decisões metodológicas futuras

As próximas decisões deverão ser registradas nesta nota conforme forem tomadas.

## 9. Seleção de features

Para cada variável incluída no modelo, registrar:

- Qual fenômeno ela representa?
- Qual é a hipótese relacionada?
- Por que ela pode explicar o preço dos alimentos?
- Qual é a fonte?
- Existe correlação com outras variáveis?
- Existem problemas de multicolinearidade?
- Existem valores faltantes?
- Por que ela foi mantida ou removida?

---

## 10. Métricas

Registrar posteriormente:

- quais métricas serão utilizadas;
- por que foram escolhidas;
- o que cada métrica representa;
- quais métricas serão utilizadas para avaliar os modelos;
- quais métricas serão utilizadas para analisar volatilidade.

---

## 11. Tratamento dos dados

Documentar:

- tratamento de valores faltantes;
- identificação de outliers;
- tratamento de anomalias;
- normalização/padronização;
- transformações;
- agregações;
- tratamento de diferenças de periodicidade.

---

## 12. Modelagem

Registrar:

- modelos testados;
- modelos descartados;
- hiperparâmetros;
- estratégia de validação;
- divisão temporal dos dados;
- critérios de comparação.

---

## 13. Resultados

### Principais descobertas

`A preencher`

### Hipóteses confirmadas

`A preencher`

### Hipóteses não confirmadas

`A preencher`

### Resultados inesperados

`A preencher`

---

## 14. Limitações

Registrar limitações relacionadas a:

- disponibilidade dos dados;
- qualidade dos dados;
- diferenças de periodicidade;
- cobertura regional;
- causalidade;
- variáveis não observadas;
- possíveis vieses.



