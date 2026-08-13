# T-013 — Coletor BCB/SGS: variáveis macroeconômicas de controle

| Campo | Valor |
|---|---|
| **Etapa** | 1 Coleta |
| **Prioridade** | P0 |
| **Estimativa** | 2h |
| **Depende de** | T-001 |
| **Bloqueia** | T-024 |
| **Responsável** | — |
| **Status** | 🔲 A fazer |

## Contexto
Sem controlar inflação e câmbio, o modelo vai atribuir ao clima aquilo que é só perda de poder de compra da moeda. O IPCA aqui tem dupla função: é variável de controle **e** é o deflator que gera o alvo em termos reais.

É o ticket mais fácil da coleta — API JSON pública, sem cadastro. Bom para começar e ter um resultado rápido.

## Entregável
`data/interim/macro_br_mes.parquet` — uma linha por mês, Brasil.

## Fonte
`https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados?formato=json&dataInicial=01/01/2014&dataFinal=31/12/2026`

| Código | Série | Periodicidade |
|---|---|---|
| 1 | Dólar PTAX (venda) | diária |
| 433 | IPCA — variação mensal | mensal |
| 432 | Selic — meta | diária |
| 11 | Selic — efetiva | diária |
| 189 | IGP-M | mensal |

## Schema de saída
`ano_mes`, `dolar_ptax_medio`, `dolar_ptax_fim`, `ipca_mm`, `ipca_indice_base`, `selic`, `igpm`

## Tarefas
- [ ] `src/coleta/04_bcb_sgs.py` com `busca_serie(codigo, inicio, fim)`
- [ ] **Paginar em blocos de até 10 anos** — a API tem esse limite informal e falha silenciosamente acima dele
- [ ] Agregar séries diárias → mensal: média do mês (`dolar_ptax_medio`) e último dia útil (`dolar_ptax_fim`)
- [ ] Construir `ipca_indice_base`: índice acumulado a partir da variação mensal, com base fixa (sugestão: 2015-01 = 100). É o que o T-024 usa para deflacionar
- [ ] Conferir o valor de fechamento de alguns meses contra o site do BCB

## Critérios de aceite
- [ ] Série mensal contínua 2014-01 → fim do período, zero buracos
- [ ] `ipca_indice_base` é monotonicamente crescente (deflação mensal existe, mas não sustentada — queda longa indica erro de acumulação)
- [ ] Dólar médio de um mês conhecido bate com a fonte (ex.: conferir 2020-03, pico da pandemia, ~R$ 4,90)
- [ ] Sem `NaN` em nenhuma coluna

## Armadilhas
- Datas vêm como `"dd/MM/yyyy"` string. `pd.to_datetime(..., format="%d/%m/%Y")` explícito — sem o `format`, o pandas pode interpretar `03/04` como março/abril errado.
- Valores vêm como **string** (`"5,432"` com vírgula decimal em algumas séries). Converter explicitamente.
- Requisição de mais de 10 anos pode retornar 200 com payload truncado, sem erro. Sempre validar o intervalo de datas do resultado contra o pedido.
- Essas variáveis são **nacionais** — no T-024 elas são replicadas (broadcast) para todas as UFs do mesmo mês. Isso é intencional, mas significa que elas não explicam diferença *entre* capitais, só variação no tempo.
