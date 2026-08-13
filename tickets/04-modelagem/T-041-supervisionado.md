# T-041 — Modelo supervisionado com validação temporal

| Campo | Valor |
|---|---|
| **Etapa** | 4 Modelagem |
| **Prioridade** | P0 |
| **Estimativa** | 6h |
| **Depende de** | T-023, T-024, T-031 |
| **Bloqueia** | T-042, T-050 |
| **Responsável** | — |
| **Status** | 🔲 A fazer |

## Contexto
O modelo principal do trabalho: prever a variação mensal do custo da cesta a partir de clima, safra e macro.

**O ponto mais crítico deste ticket não é o algoritmo — é a validação.** Usar `train_test_split` aleatório numa série temporal coloca o futuro no treino, infla a métrica e invalida o resultado inteiro. É o erro que mais derruba nota em trabalho de série temporal, e é fácil de cometer sem perceber.

## Entregável
`notebooks/04_modelagem.ipynb`
`outputs/tabelas/resultados_modelos.csv`
`outputs/figuras/predito_vs_real.png`, `outputs/figuras/residuos.png`

## Alvo
`var_pct_cesta_mm` — variação percentual mês a mês. É estacionária, o que evita que o modelo aprenda só tendência.

Se sobrar tempo, comparar com o alvo `valor_cesta_real` em nível.

## Protocolo de validação
```
Treino:    2015-01 → 2023-12
Validação: 2024-01 → 2024-12   (ajuste de hiperparâmetros)
Teste:     2025-01 → 2026-06   (tocado UMA única vez, no fim)
```
Mais `TimeSeriesSplit(n_splits=5)` dentro do treino para a validação cruzada.

## Tarefas
- [ ] Baseline ingênuo: prever a média histórica, e prever o valor do mês anterior (*persistence*). **Todo modelo tem que bater isso** — se não bater, não tem valor
- [ ] Baseline linear: `Ridge` e `Lasso` (o Lasso já faz seleção de features)
- [ ] `RandomForestRegressor`
- [ ] `XGBoost` / `LightGBM` com ajuste de hiperparâmetros
- [ ] Seleção de features guiada pelos `lags_otimos.csv` do T-031 — não jogar as 180 colunas de uma vez
- [ ] Métricas: RMSE, MAE, R², MAPE. Reportar **todas** para todos os modelos
- [ ] Gráfico predito vs. real na janela de teste
- [ ] Análise de resíduos: distribuição, autocorrelação (Ljung-Box), resíduo por UF e por período
- [ ] Verificar se o modelo usa a dimensão geográfica ou só a temporal (ver Armadilhas)
- [ ] Tabela comparativa final de todos os modelos

## Critérios de aceite
- [ ] **Zero uso de `train_test_split` aleatório** — verificado explicitamente no código
- [ ] O conjunto de teste foi avaliado uma única vez, depois de todas as decisões tomadas
- [ ] O melhor modelo supera os dois baselines ingênuos em RMSE no teste
- [ ] Nenhuma feature contemporânea de clima entrou no conjunto de treino
- [ ] Resíduos sem autocorrelação forte (se houver, há estrutura temporal não capturada — discutir)
- [ ] A tabela comparativa cobre todos os modelos com todas as métricas
- [ ] R² do teste está reportado **honestamente**, mesmo que baixo

## Armadilhas
- **Vazamento temporal** é o risco número um. Além do split: qualquer `StandardScaler` ou imputação deve ser ajustado **só no treino** e aplicado no teste. Usar `Pipeline` do sklearn resolve isso de forma estrutural.
- **Vazamento pelo painel:** as variáveis macro e de clima ponderado são idênticas entre UFs no mesmo mês. Se o split for por UF (e não por tempo), o modelo vê o mesmo mês nos dois lados. Split **sempre por data**.
- ~2.300 linhas e ~180 features favorecem overfitting. Priorizar modelos regularizados e seleção agressiva de features. Um Ridge bem especificado batendo o XGBoost é resultado normal aqui — e vale mais que um XGBoost superajustado.
- **R² baixo é esperado e não é fracasso.** Preço de alimento depende de margem de varejo, política comercial, expectativa de mercado — coisas que não estão na base. Um R² de 0,3 bem discutido vale mais que um R² de 0,9 obtido com vazamento.
- Testar se o modelo consegue algo além de sazonalidade: rodar uma versão só com dummies de mês e comparar. Se o ganho das features climáticas sobre isso for nulo, o clima não está agregando — e isso precisa ser dito.
