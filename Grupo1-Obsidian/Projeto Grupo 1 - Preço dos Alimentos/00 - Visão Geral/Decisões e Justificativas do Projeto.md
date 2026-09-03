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

| **Base**                  | **Fonte / Instituição**       | **Papel / Contribuição no Projeto**                                                                                                                                                                                   | **Status** | **Decisão**              |
| ------------------------- | ----------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ------------------------ |
| `sidra_ipca`              | [[IBGE]] / [[SIDRA]]          | **Variável-alvo (target):** Taxa de variação percentual mensal e pesos orçamentários de alimentos em 16 áreas urbanas.                                                                                                | Avaliada   | ✅ Utilizar               |
| `bcb_var_macroeconomicas` | [[Banco Central do Brasil]]   | **Contexto macroeconômico:** Câmbio (PTAX), Selic, IPCA geral e IGP-M via _broadcast_ nacional contínuo (2014–2026).                                                                                                  | Avaliada   | ✅ Utilizar               |
| `inmet_clima`             | [[INMET]]                     | **Choques climáticos:** Precipitação mensal acumulada, temperaturas extremas, mínimas absolutas (geadas) e umidade (701 estações).                                                                                    | Avaliada   | ✅ Utilizar               |
| `estimativas_safra_UF`    | [[IBGE]] ([[LSPA]] / [[PAM]]) | **Choques de oferta agrícola:** Variação mensal de rendimento ($kg/ha$), área colhida e revisões de produção por cultura e UF.                                                                                        | Avaliada   | ✅ Utilizar               |
| `monitor_secas_ana`       | [[ANA]]                       | **Persistência de secas:** Índices consolidados de severidade territorial e duração contínua de estiagem grave ($S2+$) por UF.                                                                                        | Avaliada   | 🟡 Utilizar parcialmente |
| `conab`                   | CONAB                         | Informações de safra e balanço de oferta/demanda com baixa frequência temporal (anual).                                                                                                                               | Avaliada   | ❌ Descartar              |
| `anp_combustiveis`        | ANP                           | Integrar os custos logísticos de frete rodoviário (Diesel) e de cocção doméstica (GLP) à modelagem. Adiciona a dimensão espacial e regional de custos que variáveis macroeconômicas nacionais não conseguem capturar. | Avaliada   | ✅ Utilizar               |


>[!note] Diretriz de Uso no Modelo 
>
>As bases marcadas com **✅ Utilizar** compõem a estrutura principal do pipeline analítico (inflação de alimentos, macroeconomia, meteorologia de superfície, combustíveis e acompanhamento conjuntural de safras pelo LSPA). A base `monitor_secas_ana` entra como complemento com controle estrito de valores nulos para o período pré-monitoramento. A base `conab` foi **descartada** por limitações de frequência (dados anuais por safra que violam o rigor da análise mensal) e redundância frente ao LSPA/IBGE.


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



