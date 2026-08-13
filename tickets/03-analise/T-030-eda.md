# T-030 — Análise exploratória descritiva

| Campo | Valor |
|---|---|
| **Etapa** | 3 Análise |
| **Prioridade** | P1 |
| **Estimativa** | 4h |
| **Depende de** | T-024 |
| **Bloqueia** | T-050 |
| **Responsável** | — |
| **Status** | 🔲 A fazer |

## Contexto
Entender a base antes de modelar, e produzir os gráficos que sustentam a narrativa do relatório. A maior parte das figuras da apresentação final sai daqui — não do modelo.

## Entregável
`notebooks/01_eda.ipynb` + figuras em `outputs/figuras/`

## Análises a produzir
- [ ] **Série temporal do alvo**: cesta nominal vs. real, com 4-6 capitais destacadas. Mostra visualmente por que deflacionar importa
- [ ] **Ranking de capitais** por custo médio da cesta, e como esse ranking mudou entre 2015 e 2026
- [ ] **Heatmap capital × mês** do valor real — revela padrões regionais e sazonais de uma vez
- [ ] **Decomposição sazonal** (`statsmodels.seasonal_decompose`) do alvo para 2-3 capitais: tendência, sazonalidade, resíduo
- [ ] **Dispersão geográfica**: desvio-padrão entre capitais ao longo do tempo — as capitais estão convergindo ou divergindo em preço?
- [ ] **Sazonalidade climática vs. sazonalidade de preço** sobrepostas no mesmo eixo temporal — o gráfico que introduz visualmente a hipótese do trabalho
- [ ] **Distribuição de `var_pct_cesta_mm`**: histograma, teste de normalidade, identificação dos meses de choque
- [ ] Eventos conhecidos anotados no gráfico: pandemia (2020), seca 2021, alta do café (2024-25)

## Critérios de aceite
- [ ] Todas as figuras salvas em `outputs/figuras/` com DPI ≥ 150, legíveis quando projetadas
- [ ] Todo gráfico tem título, eixos rotulados **com unidade** e fonte citada
- [ ] Cada análise fecha com uma frase escrita de interpretação — não deixar gráfico órfão sem leitura
- [ ] As 3 figuras mais fortes estão marcadas como candidatas à apresentação
- [ ] Nenhum gráfico usa o valor **nominal** para comparar anos distantes sem dizer que é nominal

## Armadilhas
- Comparar R$ de 2015 com R$ de 2026 sem deflacionar produz a conclusão trivial "tudo subiu". Usar sempre o valor real nas comparações de longo prazo.
- Evitar o gráfico de 27 linhas coloridas — ilegível. Destacar 4-6 capitais e deixar as demais em cinza claro ao fundo.
- Escala do eixo Y: começar em zero em gráfico de barras, mas não necessariamente em série temporal (esconde variação relevante).
- Antes de escrever o código dos gráficos, considerar carregar a skill `dataviz` para calibrar paleta e formato — as figuras vão para a apresentação e valem nota.
