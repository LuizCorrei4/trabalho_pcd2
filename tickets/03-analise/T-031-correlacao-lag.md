# T-031 — Correlação e cross-correlation com defasagem

| Campo | Valor |
|---|---|
| **Etapa** | 3 Análise |
| **Prioridade** | P0 |
| **Estimativa** | 4h |
| **Depende de** | T-024 |
| **Bloqueia** | T-041, T-050 |
| **Responsável** | — |
| **Status** | 🔲 A fazer |

## Contexto
O enunciado do trabalho pede explicitamente **"entender a correlação entre os dados"**. Este ticket é a resposta direta a esse requisito — e não é só uma matriz de correlação: o resultado mais interessante aqui é *em qual defasagem* o clima se conecta ao preço.

A saída deste ticket também alimenta a seleção de features do T-041: em vez de jogar 180 colunas no modelo, entram os lags que a análise mostrou serem relevantes.

## Entregável
`notebooks/02_correlacao.ipynb`
`outputs/figuras/matriz_correlacao.png`, `outputs/figuras/ccf_*.png`
`outputs/tabelas/lags_otimos.csv`

## Análises a produzir
- [ ] **Matriz de correlação** (Pearson e Spearman) entre alvo e features principais. Spearman importa: a relação clima→preço tem toda razão para ser não linear
- [ ] **Cross-correlation function (CCF)** entre cada variável climática e o alvo, para lags de 0 a 18 meses ⭐ — o resultado central do ticket
- [ ] **Tabela de lags ótimos**: para cada feature, o lag de maior correlação absoluta e o valor
- [ ] Correlação **por grupo**: separar por região e por período — a relação clima-preço no Nordeste não é a mesma do Sul
- [ ] **Teste de Granger** (`statsmodels.grangercausalitytests`): chuva ponderada → preço. Verificar estacionariedade (ADF) antes
- [ ] Comparar explicitamente **clima local vs. clima ponderado pela produção** — validação empírica da hipótese do T-022
- [ ] Correlação parcial controlando por IPCA — separa efeito climático de inflação geral

## Critérios de aceite
- [ ] A CCF está calculada para pelo menos 6 variáveis climáticas e plotada com banda de significância
- [ ] `lags_otimos.csv` gerado e usado como insumo declarado do T-041
- [ ] O teste de Granger foi precedido de teste de estacionariedade, e o resultado (positivo ou negativo) está interpretado
- [ ] A comparação clima local vs. ponderado tem conclusão escrita — qual funciona melhor e por quê
- [ ] Toda correlação relatada vem acompanhada de p-valor e tamanho da amostra
- [ ] Há pelo menos uma frase honesta sobre o que **não** correlacionou

## Armadilhas
- **Correlação espúria por tendência comum.** Duas séries que sobem ao longo do tempo correlacionam com qualquer coisa que também suba. Trabalhar com séries diferenciadas (`var_pct`) ou deflacionadas, nunca com o nominal em nível.
- **Correlação não é causalidade** — e Granger também não é causalidade, apesar do nome. É precedência temporal preditiva. Escrever isso com clareza no relatório; é o tipo de nuance que professor cobra.
- Testar 180 features contra o alvo significa que ~9 vão dar p < 0,05 por puro acaso. Mencionar o problema de múltiplas comparações e, se possível, aplicar correção (Bonferroni ou FDR).
- Correlação fraca no agregado pode esconder correlação forte num subgrupo (uma região, um produto). Vale investigar antes de concluir que não há relação.
- Se a correlação clima→preço vier fraca em tudo: **isso é um resultado, não um fracasso.** Significa que outros fatores (câmbio, margem de varejo, política de estoque) dominam. Reportar honestamente e explorar por quê rende um trabalho melhor que forçar um resultado.
