# T-042 — Interpretação do modelo com SHAP

| Campo | Valor |
|---|---|
| **Etapa** | 4 Modelagem |
| **Prioridade** | P1 |
| **Estimativa** | 3h |
| **Depende de** | T-041 |
| **Bloqueia** | T-050 |
| **Responsável** | — |
| **Status** | 🔲 A fazer |

## Contexto
A pergunta de pesquisa não é "qual o RMSE" — é **"quanto do preço da cesta é explicado por clima"**. Sem interpretação, o modelo responde a pergunta errada.

O SHAP é o que transforma um número de acurácia em uma conclusão substantiva: *quais* choques climáticos pesam, *com que defasagem*, e *em que direção*.

## Entregável
`notebooks/05_interpretacao.ipynb`
`outputs/figuras/shap_summary.png`, `shap_dependence_*.png`, `importancia_features.png`

## Tarefas
- [ ] `shap.TreeExplainer` no melhor modelo de árvore do T-041
- [ ] **Summary plot** (beeswarm) — a figura principal da interpretação
- [ ] **Bar plot** de importância média absoluta
- [ ] **Dependence plots** para as 4-5 features mais importantes — mostram a forma da relação, inclusive não linearidades
- [ ] Agrupar a importância por **família de variável**: clima local, clima ponderado, safra, macro, sazonalidade. Responde diretamente "quanto do preço é clima?" ⭐
- [ ] Comparar o SHAP com a importância por permutação (mais confiável que a importância nativa do modelo)
- [ ] Comparar a importância dos lags com os `lags_otimos.csv` do T-031 — as duas análises concordam?
- [ ] Um ou dois **waterfall plots** de meses específicos de choque (ex.: pico do café), explicando aquela previsão individual
- [ ] Escrever as conclusões substantivas em prosa

## Critérios de aceite
- [ ] Summary plot gerado e legível
- [ ] A importância agregada por família está calculada e apresentada como percentual
- [ ] Cada uma das 5 features mais importantes tem interpretação escrita, incluindo o **sinal** do efeito e se ele faz sentido agronômico
- [ ] Há comparação explícita entre clima local e clima ponderado — fecha o arco do T-022
- [ ] Existe pelo menos uma conclusão que **contraria** a expectativa inicial, ou uma declaração explícita de que tudo confirmou a hipótese
- [ ] As conclusões estão escritas em linguagem que um não-especialista entende

## Armadilhas
- **SHAP explica o modelo, não o mundo.** Se o modelo estiver mal especificado, o SHAP explicará bem um modelo errado. Só interpretar depois que o T-041 passar em todos os critérios de aceite.
- Features correlacionadas entre si (chuva em lag 3 e chuva acumulada em 3 meses medem quase a mesma coisa) **dividem** a importância entre si. Um efeito real pode parecer fraco por estar espalhado em 4 colunas. Por isso a agregação por família é mais confiável que a leitura coluna a coluna.
- `shap.TreeExplainer` só funciona em modelos de árvore. Se o melhor modelo for Ridge, usar os coeficientes padronizados — que aliás são mais fáceis de interpretar.
- Cuidado com narrativa causal: SHAP mostra associação dentro do modelo. Escrever "associado a" e não "causa".
- Se o clima aparecer com importância baixa, **essa é a conclusão do trabalho** e precisa ser defendida com honestidade, não escondida atrás de um gráfico bonito de outra variável.
