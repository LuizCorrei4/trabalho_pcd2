# T-022 — Clima ponderado pela produção ⭐ DIFERENCIAL DO TRABALHO

| Campo | Valor |
|---|---|
| **Etapa** | 2 Tratamento |
| **Prioridade** | P1 |
| **Estimativa** | 5h |
| **Depende de** | T-012, T-021 |
| **Bloqueia** | T-023 |
| **Responsável** | — |
| **Status** | 🔲 A fazer |

## Contexto
**Este é o ticket que separa um trabalho mediano de um bom trabalho.**

O erro conceitual óbvio no tema é juntar o clima da capital com o preço da capital. Mas o preço do feijão em São Paulo não depende da chuva em São Paulo — depende da chuva na Bahia e no Paraná, que é onde o feijão nasce. Commodity é transportável; o preço se forma no mercado nacional, não no clima local.

A solução é construir, para cada produto, um índice climático **nacional** ponderado pela participação de cada UF na produção daquele produto.

## Formulação

Para cada produto *p* e mês *t*:

```
clima_ponderado[p][t] = Σ_uf ( peso[p][uf] × clima[uf][t] )

onde   peso[p][uf] = producao[p][uf] / Σ_uf producao[p][uf]
```

Os pesos vêm do PAM/LSPA (T-012). Resultado: variáveis como `chuva_pond_feijao_t`, `dias_calor_extremo_pond_cafe_t` — nacionais, replicadas para todas as capitais.

## Entregável
`data/interim/clima_ponderado_mes.parquet` (nacional × mês)
`data/processed/pesos_producao.csv` (produto × UF, documentado)

## Tarefas
- [ ] Calcular `peso[p][uf]` a partir da produção média dos últimos 5 anos (janela fixa, ver Armadilhas)
- [ ] Salvar a matriz de pesos como entregável próprio — ela é resultado de análise, vale uma tabela no relatório
- [ ] Aplicar a ponderação sobre as variáveis climáticas do T-021, para cada produto da lista do T-012
- [ ] Manter também as versões **locais** (clima da própria UF) — o modelo recebe as duas famílias e decide qual importa para quê
- [ ] Produzir um mapa ou gráfico de barras da concentração produtiva por produto (ótimo material para a apresentação)
- [ ] Documentar a fórmula e a justificativa no relatório

## Critérios de aceite
- [ ] Para cada produto, os pesos somam 1,00 (tolerância 0,001)
- [ ] Os pesos batem com o conhecimento do setor: café concentrado em MG/ES, arroz em RS/SC, feijão em PR/MG/BA, soja em MT/PR/RS
- [ ] Nenhuma UF com peso > 0 num produto que ela não produz
- [ ] Sanidade final: `chuva_pond_cafe` correlaciona mais forte com o preço do café (IPCA subitem, T-017) do que a chuva média simples do Brasil. **Se isso não acontecer, a hipótese central do trabalho precisa ser revista** — e esse resultado negativo também é uma conclusão legítima, desde que reportada.

## Armadilhas
- **Peso variável no tempo cria vazamento.** Usar a produção do próprio ano *t* para ponderar significa usar informação futura (a safra só é conhecida depois). Fixar os pesos numa janela histórica anterior ao período de treino, ou usar média móvel defasada.
- Alguns produtos da cesta **não são lavoura**: carne, leite, manteiga. Para eles, o caminho é ponderar pela produção de **milho e soja** (custo de ração) ou usar dados da Pesquisa Trimestral do Abate/Leite do IBGE. Documentar a escolha.
- Café e banana são lavoura permanente — a produção reage ao clima com defasagem muito maior (o cafeeiro é afetado na florada, ~6-9 meses antes da colheita). Isso reforça a necessidade de lags longos no T-023.
- Trigo e boa parte do óleo/trigo consumidos são **importados** (Argentina, principalmente). Para esses, clima brasileiro explica pouco e câmbio explica muito — esperar coeficiente fraco e não forçar interpretação.
