# T-023 — Engenharia de features: lags, janelas e extremos

| Campo | Valor |
|---|---|
| **Etapa** | 2 Tratamento |
| **Prioridade** | P0 |
| **Estimativa** | 4h |
| **Depende de** | T-021, T-022 |
| **Bloqueia** | T-024, T-041 |
| **Responsável** | — |
| **Status** | 🔲 A fazer |

## Contexto
Uma seca em novembro não mexe no preço em novembro. Ela quebra a safra que seria colhida em março e o preço reage entre abril e agosto. **Nenhuma variável climática pode entrar no modelo de forma contemporânea** — se entrar, o modelo não encontra nada e a conclusão do trabalho vira "clima não afeta preço", que é falso e é só um erro de especificação.

## Entregável
`src/tratamento/features.py` + `data/interim/features_clima.parquet`

## Features a gerar

**Lags** — para cada variável climática (local e ponderada): `t-1, t-2, t-3, t-6, t-9, t-12`

**Janelas acumuladas** — sinal mais forte que o mês isolado, porque seca é um fenômeno acumulativo:
- `chuva_acum_3m`, `chuva_acum_6m`, `chuva_acum_12m`
- `temp_media_movel_3m`, `temp_media_movel_6m`
- `dias_sem_chuva_acum_3m`, `dias_sem_chuva_acum_6m`

**Anomalias** — desvio em relação à normal daquele mês do ano. Mais interpretável que o valor absoluto: "choveu 40% menos que o normal para um março" diz mais que "choveu 90 mm".
- `anomalia_chuva = (chuva - media_historica_mes) / desvio_padrao_mes`
- `anomalia_temp` idem

**Sazonalidade** — `mes` como dummies, ou `sin(2πm/12)` e `cos(2πm/12)` (2 colunas em vez de 11)

**Safra** — `revisao_pct_prod_{produto}` com lags de 1 a 6 meses

## Tarefas
- [ ] `gera_lags(df, colunas, lags, grupo="sigla_uf")` — sempre agrupando por UF, ver Armadilhas
- [ ] `gera_janelas(df, colunas, janelas)` usando `.rolling()`
- [ ] `gera_anomalias(df, colunas)` a partir da normal por `(sigla_uf, mês-do-ano)`
- [ ] Gerar as features de sazonalidade
- [ ] Descartar as linhas iniciais sem histórico suficiente (os primeiros 12 meses ficam incompletos — por isso os coletores pegam desde 2014)
- [ ] Documentar o dicionário completo de variáveis geradas

## Critérios de aceite
- [ ] Nenhuma feature climática contemporânea (lag 0) sobrevive no conjunto final destinado ao modelo
- [ ] `df.groupby("sigla_uf")` confirma que o lag de cada UF veio da própria UF — teste explícito com 2 UFs
- [ ] `anomalia_chuva` tem média ≈ 0 e desvio ≈ 1 por UF/mês
- [ ] Nulos concentrados apenas nos 12 primeiros meses da série, e essas linhas são descartadas
- [ ] O dicionário de variáveis está escrito e cada feature tem uma linha explicando o que é

## Armadilhas
- **`shift()` sem `groupby("sigla_uf")` puxa o valor da UF anterior no DataFrame.** O lag de janeiro do Acre vira dezembro do Amazonas. É silencioso, é devastador e é o erro mais comum deste ticket. Sempre `df.groupby("sigla_uf")[col].shift(k)`.
- Ordenar por `(sigla_uf, ano_mes)` **antes** de qualquer `shift` ou `rolling`. Ordem errada = lag errado.
- Explosão de dimensionalidade: 15 variáveis × 6 lags × 2 famílias (local/ponderada) = 180 colunas para ~2.300 linhas. Isso é mais colunas que o razoável — planejar seleção de features no T-041 (regularização L1, importância por permutação, ou seleção guiada pela cross-correlation do T-031).
- Não criar feature que use informação futura: `rolling()` centrado (`center=True`) usa dados posteriores e é vazamento. Sempre janela para trás.
