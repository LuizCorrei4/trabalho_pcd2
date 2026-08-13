# T-015 — Coletor Monitor de Secas (ANA)

| Campo | Valor |
|---|---|
| **Etapa** | 1 Coleta |
| **Prioridade** | P2 (opcional — **melhor custo/benefício dos opcionais**) |
| **Estimativa** | 3h |
| **Depende de** | T-002 |
| **Bloqueia** | — |
| **Responsável** | Arthur |
| **Status** | ✅ Feito |

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
- [x] Baixar os dados tabulares do período
- [x] Agregar município → UF: **% da área da UF** em cada categoria — **já vem feito pela ANA**, ver "Como foi feito"
- [x] Criar `severidade_media` = média ponderada com pesos S0=1 … S4=5
- [x] Criar `meses_consecutivos_S2plus` — seca é acumulativa; 6 meses seguidos de S2 machucam muito mais que 1
- [x] Documentar a partir de que ano cada UF entrou no monitoramento → [`docs/cobertura_monitor_secas.md`](../../docs/cobertura_monitor_secas.md)

## Critérios de aceite
- [x] Percentuais entre 0 e 100, e as categorias não se sobrepõem de forma inconsistente (`S3plus ≤ S2plus ≤ S0plus`)
- [x] Cobertura por UF documentada, com os anos pré-monitoramento marcados como `NaN` — **não como zero**
- [x] Sanidade histórica: a seca do Nordeste 2015-2017 e a do Centro-Sul em 2021 aparecem claramente na série

Reverificável a qualquer momento com `python -m src.coleta.monitor_secas.validar`
(sai com código 0 e imprime o número que sustenta cada critério). Última execução:
**todos passaram** — Nordeste com S2+ médio de 65,8% em 2015-2017 contra 16,3% no
resto da série, e 2021 como o ano mais seco do Centro-Sul.

## Como foi feito
Código em [`src/coleta/monitor_secas/`](../../src/coleta/monitor_secas/) —
detalhes completos no [README do coletor](../../src/coleta/monitor_secas/README.md).

```bash
python -m src.coleta.monitor_secas.download        # 27 JSONs -> data/raw/ana/
python -m src.coleta.monitor_secas.agrega_uf_mes   # -> data/interim/seca_uf_mes.parquet
python -m src.coleta.monitor_secas.validar         # critérios de aceite
```

Três descobertas que mudam o entendimento do ticket:

1. **A página de dados tabulares não tem arquivo para baixar** — é uma aplicação
   Angular que monta o CSV no navegador. Os dados vêm de uma API REST aberta,
   encontrada no bundle JavaScript do site:
   `GET https://apimsbr.ana.gov.br/rpc/v1/dados-tabulares-monitor?tipo_area=1&area={geocod_uf}`.
   Uma requisição devolve a série mensal completa de uma UF.

2. **A ponderação por área de município já vem feita pela ANA.** O campo `area`
   da API não é km², apesar do nome: é o percentual do território da UF em
   pontos-base (`10000` = 100,00%), e as categorias são **cumulativas** (`S2` =
   "seca grave ou pior"). Logo não há municípios para agregar e **`geopandas` não
   é necessário** — resolve a última armadilha listada abaixo.

3. **A fonte tem sujeira não documentada que produz erro silencioso.** A API
   devolve todas as revisões de um mês empilhadas, sem dizer qual vale — 66 dos
   2.422 meses têm categoria repetida. Entre as revisões antigas há valores com a
   escala multiplicada por 100 e um `123456` de placeholder. O desempate é pelo
   maior `id`, e as divergências ficam registradas em
   `outputs/tabelas/monitor_secas_revisoes_divergentes.csv`.

**Dependência do T-002:** o coletor usa `data/processed/dim_uf.csv` quando ele
existe e cai para a API do IBGE (a mesma fonte que o T-002 usa) enquanto não
existe — ver `src/ufs.py`. Passa a validar contra a tabela canônica
automaticamente, sem mexer em código, no dia em que o T-002 entregar.

## Saída
`data/interim/seca_uf_mes.parquet` — 27 UFs × 138 meses = **3.726 linhas**, das
quais 2.368 com dado e **1.358 pré-monitoramento (`NaN`, não zero)**.

## Armadilhas
- **Ausência de monitoramento ≠ ausência de seca.** Preencher com `0` os anos em que a UF ainda não era monitorada cria um viés grave: o modelo aprenderia que "antes de 2019 não havia seca no Sul". Usar `NaN`.
- A cobertura começou pelo Nordeste — a série é desbalanceada entre regiões nos primeiros anos.
- ~~Se só houver shapefile e não tabela para algum período, será preciso `geopandas`~~ — **não se aplica**: a API entrega percentual de área já calculado para toda a série. Nenhum shapefile foi necessário.

### Confirmadas na prática (para o T-023/T-041)
- **A armadilha do `NaN` é maior do que o ticket sugeria.** Não é "antes de 2019 no Sul": até 2018 a série tem **apenas Nordeste**. Um modelo treinado sem cuidado vai confundir "seca" com "ser do Nordeste". Duas saídas razoáveis: restringir esta feature a 2020+, ou manter a janela toda e tratar `NaN` explicitamente — nunca imputar zero.
- **`meses_consecutivos_S2plus` subestima a duração no início da série de cada UF.** A contagem zera num buraco e começa do 1 quando a UF entra no monitoramento, então a UF que já estava em seca ao entrar aparece com duração menor que a real. É subestimativa honesta, preferível a número inventado — mas precisa constar no relatório.
- Há **1 buraco interno** na série (SE, um mês faltando dentro do intervalo já monitorado) e **1 mês com categorias cumulativas inconsistentes** (MA 2014-11, fora da janela-alvo), sinalizado na coluna `inconsistente`.
