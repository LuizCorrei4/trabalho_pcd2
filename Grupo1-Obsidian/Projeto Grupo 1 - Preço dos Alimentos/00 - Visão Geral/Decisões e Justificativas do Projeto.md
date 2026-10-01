
> **Projeto:** O que realmente move o preço da comida no Brasil?  
> **Subtítulo:** Anomalias climáticas, custo logístico e macroeconomia na volatilidade regional da cesta básica  
> **Disciplina:** SSC0957 — Prática em Ciência de Dados II  
> **Referência técnica:** notebook `08_decisoes_e_resultado_da_juncao.ipynb` (34 decisões, em ordem)

Esta nota registra as principais decisões tomadas ao longo do desenvolvimento do projeto e as justificativas para cada uma delas. O objetivo é manter um histórico das escolhas metodológicas, facilitando a compreensão, reprodução e apresentação do projeto.

> [!info] Status atual **Concluído:** planejamento, coleta das 6 fontes, padronização e junção em uma tabela única (`UF × mês`).  
> **Ainda não feito:** exploração, limpeza profunda, seleção de features e modelagem (seções 9 a 13).  
> Detalhe das fontes: [[Resumo]]. Detalhe técnico da junção: [[Integração das Bases]].

---

## 1. Escolha do tema

### Contexto

O projeto surgiu a partir de uma discussão sobre possíveis relações entre fenômenos climáticos e impactos econômicos. Inicialmente, foram consideradas diferentes possibilidades, como:

- Ondas de calor na Europa;
- Impactos do El Niño na economia;
- Relações entre eventos climáticos e preços de alimentos.

As opções foram comparadas por três critérios: **dados disponíveis**, **possibilidade de cruzar fontes diferentes** e **relevância do problema**. Também se quis evitar fontes com as quais o grupo já teve dificuldade em trabalhos anteriores (como o DataSUS). Após essa discussão, decidimos investigar a relação entre **anomalias climáticas, custos logísticos, fatores macroeconômicos e preços de alimentos no Brasil**.

### Por que escolhemos este tema?

- **Relevância econômica:** alimentos possuem impacto direto no orçamento das famílias e na inflação;
- **Relevância regional:** os preços podem variar significativamente entre diferentes regiões do Brasil;
- **Possível influência climática:** eventos extremos e alterações nas condições climáticas podem afetar produção e oferta de alimentos;
- **Influência logística:** custos de transporte e distribuição podem contribuir para diferenças regionais nos preços;
- **Influência macroeconômica:** inflação, câmbio, juros e outras variáveis econômicas podem afetar os preços dos alimentos;
- **Viabilidade dos dados:** são públicos e em formato de tabela (sem mapas de satélite nem PDFs complicados), e permitem combinar dados climáticos, agrícolas, econômicos e de preços.

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

| Hipótese                   | Enunciado                                                                                                                               | Fonte(s) que a sustentam na tabela |
| -------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------- |
| **H1 — Clima**             | Anomalias climáticas podem estar associadas a alterações na produção agrícola e, consequentemente, à variação dos preços dos alimentos. | `inmet_clima`, `monitor_secas_ana` |
| **H2 — Produção agrícola** | Variações na produção ou nas estimativas de safra podem ajudar a explicar movimentos nos preços dos alimentos.                          | `estimativas_safra_UF` (LSPA/PAM)  |
| **H3 — Logística**         | Diferenças nos custos e condições logísticas podem contribuir para a maior volatilidade dos preços em determinadas regiões.             | `anp_combustiveis`                 |
| **H4 — Macroeconomia**     | Variáveis macroeconômicas podem influenciar os preços dos alimentos independentemente de fatores climáticos e produtivos.               | `bcb_var_macroeconomicas`          |
| **H5 — Efeito regional**   | A magnitude desses efeitos pode variar entre estados ou regiões brasileiras.                                                            | estrutura `UF × mês` da tabela     |

> **Observação:** As hipóteses ainda não foram validadas. Elas serão testadas durante a exploração e modelagem dos dados.

---

## 3. Levantamento e avaliação das fontes de dados

Foram levantadas e avaliadas sete fontes candidatas (mais uma, CEPEA/ESALQ, prevista e não coletada). A avaliação considerou:

- relevância para o problema de pesquisa;
- disponibilidade de variáveis relacionadas às hipóteses;
- cobertura temporal e geográfica;
- periodicidade (queremos **mensal**) e granularidade por UF;
- qualidade e completude dos dados;
- possibilidade de integração com as demais fontes.

Resultado: **seis pesquisas de cinco instituições** (IBGE/SIDRA como alvo, mais INMET, ANA, IBGE/LSPA, BCB e ANP). A disciplina pedia pelo menos três fontes. A avaliação detalhada de cada uma está em [[Resumo]].

| **Base**                  | **Fonte / Instituição**       | **Papel / Contribuição no Projeto**                                                                                                                                                                                 | **Decisão**                                                                       |
| ------------------------- | ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| `sidra_ipca`              | [[IBGE]] / [[SIDRA]]          | **Variável-alvo (target):** variação percentual mensal e pesos orçamentários de itens de alimentação, em 16 áreas urbanas (convertidas para UF).                                                                    | ✅ Utilizar                                                                        |
| `bcb_var_macroeconomicas` | [[Banco Central do Brasil]]   | **Contexto macroeconômico:** câmbio (PTAX), Selic, IPCA geral e IGP-M, com _broadcast_ nacional (mesmo valor em todas as UFs no mês).                                                                               | ✅ Utilizar                                                                        |
| `inmet_clima`             | [[INMET]]                     | **Choques climáticos:** chuva mensal, temperaturas médias, índices de extremo (dias sem chuva, maior sequência seca, calor extremo) e umidade, agregados por UF pela **mediana** das estações (701 estações).       | ✅ Utilizar                                                                        |
| `estimativas_safra_UF`    | [[IBGE]] ([[LSPA]] / [[PAM]]) | **Choques de oferta agrícola:** produção estimada e **revisão % mensal** da estimativa, para 11 culturas por UF.                                                                                                    | ✅ Utilizar                                                                        |
| `monitor_secas_ana`       | [[ANA]]                       | **Persistência de secas:** severidade e duração contínua de seca grave (S2+) por UF. Só cobre o país inteiro a partir de 2023.                                                                                      | 🟡 Utilizar com ressalva (usar `seca_monitorado` ou recortar a partir de 2020-01) |
| `conab`                   | CONAB                         | Safra, estoques e balanço de oferta/demanda. Dados **anuais por ano-safra**.                                                                                                                                        | ❌ Descartar                                                                       |
| `anp_combustiveis`        | ANP                           | **Custos logísticos e de cocção:** diesel (frete agrícola) e GLP 13 kg (cocção doméstica), além de diesel S10, gasolina e etanol. Traz a dimensão **espacial** de custo que variáveis macro nacionais não capturam. | ✅ Utilizar                                                                        |


> [!note] Diretriz de uso no modelo As bases ✅ compõem a estrutura principal do pipeline. A `monitor_secas_ana` entra como complemento, **com controle estrito de nulos** no período pré-monitoramento (coluna `seca_monitorado`). A `conab` foi **descartada**: a frequência é anual por ano-safra (ex.: 2024/25), virar mês exigiria suposições, e o LSPA já mede o mesmo fenômeno mês a mês.
> 
> **Por que INMET _e_ ANA?** Elas se complementam: o INMET mede o clima de cada dia (um pico de calor, uma chuva forte); a ANA resume a **seca prolongada** em um índice pronto.

---

## 4. Escolha da variável de preço (alvo)

|Cesta básica do DIEESE|**IPCA de alimentos (IBGE/SIDRA)**|
|---|---|---|
|O que é|valor da cesta em R$, por capital|variação % mensal dos preços, por área urbana|
|Formato|relatórios mensais em **PDF**, com layout que muda entre anos|**API pública**, tabela pronta|
|Preço por produto|fechado ao público desde 2018|disponível (arroz, tomate, café, carnes...)|
|Cobertura|17 capitais|16 áreas urbanas|
|Tipo de número|valor em R$ (tem tendência, exigiria deflacionar)|variação % (comparável entre meses e regiões)|

✅ **Escolha:** IPCA do grupo _Alimentação e bebidas_ e de itens selecionados. Ler os PDFs do DIEESE era a tarefa mais arriscada do projeto (ticket T-011) e foi abandonada.

**Três alvos, em colunas separadas** (cada um responde a uma pergunta diferente):

|Coluna|Cálculo|Serve para|
|---|---|---|
|`ipca_var_alimentacao`|variação % no mês|**alvo principal**|
|`ipca_var_alimentacao_acum12`|12 meses **compostos** (multiplicados, não somados)|suavizar a sazonalidade|
|`ipca_var_alimentacao_relativa`|alimentos − IPCA cheio|quanto a comida subiu **além** da inflação geral|

---

## 5. Escolha do período analisado

✅ **Período:** `2015-01 → 2026-06` (**138 meses**), fixado em `src/config.py`.

**Justificativa:** é o período em que **todas** as fontes existem ao mesmo tempo; junho de 2026 é o último mês que todas têm. Cobre ciclos agrícolas completos e eventos relevantes (ex.: crise hídrica de 2021, choque do diesel de 2022).

Algumas fontes foram baixadas **desde antes**, de propósito:

| Fonte             | Baixada desde | Por que a folga                                                       |
| ----------------- | ------------- | --------------------------------------------------------------------- |
| IPCA              | 2006-07       | o acumulado em 12 meses de jan/2015 precisa de 2014                   |
| INMET, safra, BCB | 2014-01       | variáveis defasadas (ex.: chuva de 6 meses antes) sem perder o início |
| ANP               | 2004-05       | a variação em 12 meses de jan/2015 precisa de jan/2014                |

> [!warning] Cuidado Cálculos que olham para trás (acumulados, variações anuais, defasagens) devem ser feitos **na série inteira, antes do corte**.

---

## 6. Granularidade (o que uma linha representa)

Cada fonte chega com um grão diferente (IPCA: item × área urbana × mês; INMET: estação × hora; safra: produto × UF × mês; seca: UF × mês; BCB: Brasil × mês; ANP: combustível × UF × mês).

✅ **Escolha:** **UF × mês, formato largo** (uma linha por estado por mês). A chave é `(sigla_uf, ano_mes)`.

**Justificativa:** UF e mês são as **únicas** dimensões que todas as fontes têm em comum. Município não existe no IPCA nem na seca; Brasil × mês jogaria fora a variação regional, que é a pergunta do projeto.

> [!warning] Cuidados
> 
> - A área urbana do IPCA (ex.: Região Metropolitana de Belém) vira a UF (PA), usando os 2 primeiros dígitos do código IBGE. O preço é o da **capital e arredores**, não do estado inteiro.
> - O IPCA só existe em **16 UFs**. Ficam de fora MT (maior produtor de grãos), AL, PB, PI, RN, AM, AP, RO, RR, TO e SC. O preço é medido, em parte, longe de onde a comida é produzida.

A padronização das UFs é feita pelo arquivo `dim_uf.csv` (sigla, nome, código IBGE, capital, região).

---

## 7. Organização do repositório

✅ **Escolha:** três camadas de dados e um lugar único para caminhos e referências.

- `data/raw/`: dado exatamente como veio da fonte, **nunca modificado**;
- `data/interim/`: uma tabela por fonte, já limpa e com chaves padronizadas;
- `data/processed/`: tabela final, calendário e `dim_uf.csv`;
- `src/config.py`: todos os caminhos e o período (sem caminho absoluto no código).

**Justificativa:** permite refazer qualquer etapa sem baixar tudo de novo. A regra "nunca modificar `raw/`" nasceu de um erro real: a primeira limpeza do IPCA apagava o sinal de menos e transformava deflação em inflação, e como o arquivo `raw/` já estava alterado foi preciso baixar tudo de novo (ver [[Integração das Bases]]). Os dados não vão para o Git (são pesados).

---

## 8. Junção das bases

Resumo das decisões (detalhe e justificativas em [[Integração das Bases]]):

- **Espinha:** calendário completo de 27 UFs × 138 meses (3.726 linhas) + apenas `LEFT JOIN`;
- **Mês** sempre como `Period[M]`; **UF** sempre como sigla de 2 letras;
- **Pivotar** toda fonte com mais de uma linha por UF-mês antes de juntar;
- **Prefixo por fonte** nas colunas (`ipca_`, `clima_`, `safra_`, `seca_`, `macro_`, `comb_`);
- **Filtro final:** só linhas com alvo (16 UFs) → **2.088 linhas** (16 × 138 = 2.208, menos 120 meses de AC, MA e SE, que só entram no IPCA em 2018-05);
- **Combustíveis** acrescentados depois, com um único `LEFT JOIN` sobre a tabela pronta: 2.088 linhas, de 89 para **108 colunas**.

---

# Decisões metodológicas futuras

As próximas decisões deverão ser registradas nesta nota conforme forem tomadas.

## 9. Seleção de features

**Já registrado:** a tabela final tem 108 colunas, distribuídas assim:

|Família|Colunas|Fonte|
|---|---|---|
|Identificação (UF, mês, região)|6|IBGE (`dim_uf`)|
|`ipca_*` (alvo e itens)|36|IBGE/SIDRA (+ BCB, para a variação relativa)|
|`clima_*`|11|INMET|
|`safra_*`|22|IBGE/LSPA|
|`seca_*`|9|ANA|
|`macro_*`|5|BCB|
|`comb_*`|19|ANP|

Para cada variável incluída no modelo, registrar:

- Qual fenômeno ela representa?
- Qual é a hipótese relacionada?
- Por que ela pode explicar o preço dos alimentos?
- Qual é a fonte?
- Existe correlação com outras variáveis?
- Existem problemas de multicolinearidade?
- Existem valores faltantes?
- Por que ela foi mantida ou removida?

> [!warning] Atenção na seleção Os pesos `ipca_peso_*` estão em três níveis que se encaixam (ex.: frango inteiro dentro de aves e ovos, dentro de alimentação). **Não somar** essas colunas. As colunas `macro_*` são idênticas em todas as UFs no mesmo mês: explicam variação **no tempo**, nunca diferença **entre estados**.

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

**Já decidido na etapa de junção** (a limpeza profunda ainda não foi feita):

|Tema|Decisão|
|---|---|
|Valores faltantes|**nunca imputar zero ou repetir o último valor** quando o vazio tem significado; cada vazio é documentado no dicionário. Exceção: `safra_producao_t_*` vazio vira **0** (a UF não planta o produto).|
|Marcadores de ausência|`seca_monitorado`, `comb_observado`, `comb_observado_liquidos`, `clima_n_estacoes`|
|Outliers|`safra_revisao_pct_*` limitada a **±50 %** (winsorização; 99,1 % dos valores intactos; o bruto passava de 15 milhões %)|
|Agregações|clima: **mediana** entre estações; combustíveis: **média ponderada** pelo nº de postos|
|Periodicidade|tudo reduzido a `UF × mês`; macro por _broadcast_ nacional|
|Transformações|acumulado de 12 meses por **composição**; variações de combustível calculadas só **após** completar a grade de meses|

A documentar ainda:

- identificação de outliers e anomalias (exploração);
- normalização/padronização;
- transformações adicionais (defasagens, anomalias climáticas);
- tratamento dos buracos do INMET (2021–2022 e Roraima).

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

### Sinais preliminares da junção (não são conclusões)

- **O diesel parece antecipar a comida:** a correlação entre a variação anual do diesel e a dos alimentos é 0,42 no mesmo mês e sobe para **0,49 com o diesel adiantado em 4 meses**.
- **O combustível varia entre estados; o dólar não:** o Acre paga em média ~20 % a mais pelo diesel que a mediana do país; o Paraná, ~5 % a menos.
- **A tabela reproduz eventos conhecidos:** seca do Ceará em jan/2017, pico de 18,1 % nos alimentos em 12 meses (nov/2020), choque do diesel após a Ucrânia (+62 % em 12 meses em jul/2022).

> [!warning] Correlação não é causa. Esses sinais são pontos de partida para a análise.

---

## 14. Limitações

**Já conhecidas:**

|Limitação|Efeito|O que existe para lidar com ela|
|---|---|---|
|IPCA só em 16 UFs (MT fica de fora)|o preço é medido longe de onde a comida é produzida|clima ponderado pela produção (T-022)|
|AC, MA e SE só a partir de 2018-05|painel desbalanceado|a conta está documentada (2.088 linhas)|
|Seca só cobre o país inteiro a partir de 2023|34 a 38 % de vazios em `seca_*`|`seca_monitorado`; recorte em 2020-01|
|Buraco do INMET em 2021–2022 e em Roraima|clima incerto na crise hídrica de 2021; a rede de estações cresce (475 em 2014, 638 em 2026)|`clima_n_estacoes`; imputação/NASA POWER pendentes|
|ANP sem coleta em 33 meses (líquidos) e 15 (GLP)|~23 % de vazios nos preços|`comb_observado_liquidos`, `comb_observado`|
|Macro igual em todas as UFs|não explica diferenças regionais|`comb_diesel_vs_br_pct` traz a dimensão espacial|
|Clima por mediana simples (sem ponderar pela produção)|em RR, AP e AC a mediana vem de 1 a 3 estações|T-022|

**A registrar posteriormente:** causalidade, variáveis não observadas e possíveis vieses.

---

## Próximos passos

1. **Exploração e limpeza profunda** (T-030): distribuições, valores extremos, sazonalidade, correlações.
2. **Variáveis defasadas** (T-023): chuva, seca e diesel de 1 a 6 meses antes, calculadas no calendário completo, **antes** do filtro.
3. **Clima ponderado pela produção** (T-022).
4. **Pendências de coleta:** script de download da ANP no repositório; investigar os 33 meses sem coleta; avaliar NASA POWER para os buracos do INMET.