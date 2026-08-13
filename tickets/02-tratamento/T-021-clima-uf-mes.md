# T-021 — Agregação climática: estação × dia → UF × mês

| Campo | Valor |
|---|---|
| **Etapa** | 2 Tratamento |
| **Prioridade** | P0 |
| **Estimativa** | 4h |
| **Depende de** | T-014 |
| **Bloqueia** | T-022, T-023 |
| **Responsável** | — |
| **Status** | 🔲 A fazer |

## Contexto
O INMET entrega ~400 estações × ~4.000 dias. O alvo é 27 UFs × 138 meses. Esta redução de escala é onde se decide se a feature climática vai ter sinal ou virar ruído — e é onde os índices de extremo (que são o que realmente afeta safra) precisam ser calculados, porque **depois da agregação mensal eles são impossíveis de recuperar**.

## Entregável
`data/interim/clima_uf_mes.parquet`

## Schema de saída
| Coluna | Descrição |
|---|---|
| `sigla_uf`, `ano_mes` | chave |
| `chuva_mm_mes` | soma da chuva no mês |
| `temp_media`, `temp_max_media`, `temp_min_media` | temperaturas |
| `umidade_media` | % |
| `dias_sem_chuva` | nº de dias com chuva < 1 mm ⭐ |
| `dias_chuva_forte` | nº de dias com chuva > 50 mm ⭐ |
| `dias_calor_extremo` | nº de dias com `temp_max` > p90 histórico daquela UF/mês ⭐ |
| `amplitude_termica` | média de (`temp_max` − `temp_min`) diária |
| `n_estacoes` | estações que contribuíram (indicador de qualidade) |
| `pct_dias_validos` | cobertura do mês |

## Tarefas
- [ ] **Calcular os índices de extremo no nível diário, antes de agregar para o mês** — esta é a ordem correta e não é negociável
- [ ] Calcular o percentil 90 de `temp_max` por `(sigla_uf, mês-do-ano)` usando toda a série histórica, como referência para `dias_calor_extremo`
- [ ] Agregar dia → mês por **estação** primeiro
- [ ] Agregar estação → UF: **mediana** entre estações (robusta a estação com defeito), guardando `n_estacoes`
- [ ] Marcar como `NaN` o mês com `pct_dias_validos < 70%` — não inventar dado
- [ ] Imputar os buracos remanescentes com a **normal climatológica** daquela UF/mês (média histórica), sinalizando com flag `clima_imputado`
- [ ] Plotar chuva mensal de 4 UFs de regiões diferentes e conferir se a sazonalidade faz sentido

## Critérios de aceite
- [ ] 27 UFs × todos os meses do período, sem buraco de chave
- [ ] `chuva_mm_mes` entre 0 e 1.200 mm; `temp_media` entre 10 °C e 35 °C
- [ ] Sazonalidade correta e visível: Manaus com pico de chuva no 1º trimestre; Nordeste seco no 2º semestre; Sul com chuva distribuída o ano todo
- [ ] Chuva média anual por UF dentro de ±25% da normal climatológica publicada pelo INMET
- [ ] `n_estacoes ≥ 1` em 100% das linhas; a coluna `clima_imputado` existe e está documentada

## Armadilhas
- **Não dá para calcular `dias_sem_chuva` a partir da chuva mensal.** Se agregar para mês primeiro, esses índices se perdem para sempre e é preciso reprocessar tudo. Calcular no diário.
- Chuva agrega por **soma**; temperatura por **média**. Somar temperatura ou tirar média de chuva são erros que passam despercebidos numa revisão rápida.
- **Média entre estações é enganosa em UF grande.** A média de uma estação no litoral e outra no sertão do Piauí não descreve nenhum dos dois lugares. Usar mediana ajuda, mas a limitação é real e deve constar no relatório — é justamente o que o T-022 vem resolver.
- Estação nova entrando no meio da série cria degrau artificial na média da UF. Por isso guardar `n_estacoes`: se ela salta de 3 para 9, qualquer quebra de nível naquele ponto é artefato, não clima.
