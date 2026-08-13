# T-015 — Coletor Monitor de Secas (ANA)

| Campo | Valor |
|---|---|
| **Etapa** | 1 Coleta |
| **Prioridade** | P2 (opcional — **melhor custo/benefício dos opcionais**) |
| **Estimativa** | 3h |
| **Depende de** | T-002 |
| **Bloqueia** | — |
| **Responsável** | — |
| **Status** | 🔲 A fazer |

## Contexto
O Monitor de Secas entrega o que teríamos que construir na mão a partir do INMET: uma classificação de severidade de seca (S0 a S4), já mensal, já por município, já validada por especialistas. É uma feature de altíssimo sinal para o tema do projeto e custa 3h.

Se sobrar tempo para exatamente **um** opcional, é este.

## Entregável
`data/interim/seca_uf_mes.parquet`

## Fonte
- Dados tabulares: https://monitordesecas.ana.gov.br/dados-tabulares
- Dados SIG: https://monitordesecas.ana.gov.br/dados-sig
- Cobertura: 2014 → atual (começou pelo Nordeste e foi expandindo para o país)

## Escala de severidade
| Código | Significado |
|---|---|
| S0 | Seca fraca |
| S1 | Seca moderada |
| S2 | Seca grave |
| S3 | Seca extrema |
| S4 | Seca excepcional |

## Schema de saída
`sigla_uf`, `ano_mes`, `pct_area_S0plus`, `pct_area_S2plus`, `pct_area_S3plus`, `severidade_media`, `meses_consecutivos_S2plus`

## Tarefas
- [ ] Baixar os dados tabulares do período
- [ ] Agregar município → UF: **% da área da UF** em cada categoria (ponderar pela área do município, não contar municípios — municípios têm tamanhos muito diferentes)
- [ ] Criar `severidade_media` = média ponderada com pesos S0=1 … S4=5
- [ ] Criar `meses_consecutivos_S2plus` — seca é acumulativa; 6 meses seguidos de S2 machucam muito mais que 1
- [ ] Documentar a partir de que ano cada UF entrou no monitoramento

## Critérios de aceite
- [ ] Percentuais entre 0 e 100, e as categorias não se sobrepõem de forma inconsistente (`S3plus ≤ S2plus ≤ S0plus`)
- [ ] Cobertura por UF documentada, com os anos pré-monitoramento marcados como `NaN` — **não como zero**
- [ ] Sanidade histórica: a seca do Nordeste 2015-2017 e a do Centro-Sul em 2021 aparecem claramente na série

## Armadilhas
- **Ausência de monitoramento ≠ ausência de seca.** Preencher com `0` os anos em que a UF ainda não era monitorada cria um viés grave: o modelo aprenderia que "antes de 2019 não havia seca no Sul". Usar `NaN`.
- A cobertura começou pelo Nordeste — a série é desbalanceada entre regiões nos primeiros anos.
- Se só houver shapefile e não tabela para algum período, será preciso `geopandas` para calcular a área por categoria. Avaliar se compensa antes de entrar nesse caminho.
