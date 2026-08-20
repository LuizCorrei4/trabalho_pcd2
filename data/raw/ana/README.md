# `data/raw/ana/` — Monitor de Secas da ANA

**Ticket:** [T-015](../../../tickets/01-coleta/T-015-monitor-secas.md) ·
**Coletor:** [`src/coleta/monitor_secas/`](../../../src/coleta/monitor_secas/) ·
**Coletado em:** 2026-08-13

## O que está aqui

27 arquivos JSON, um por UF, exatamente como vieram da API. **Nunca editar.**
Total: **6,6 MB · 2.422 registros mensais.**

Cada arquivo tem a série mensal **completa** daquela UF. O número de meses varia
muito, porque o Monitor nasceu no Nordeste em 2014 e foi expandindo pelo país:

| Meses na fonte | UFs |
|---|---|
| 144 (série cheia, desde 2014-07) | AL, BA, CE, MA, PB, PE, PI, RN |
| 143 | SE — **tem 1 mês faltando no meio** |
| 92, 87, 79, 74, 73, 72, 72, 71, 71, 71, 68 | MG, ES, TO, RJ, GO, DF, MS, PR, RS, SC, SP |
| 61, 47, 44, 43, 39, 32, 31 | MT, RO, AC, AM, PA, RR, AP |

Roraima (32) e Amapá (31) só entraram em 2023.

## De onde veio

```
GET https://apimsbr.ana.gov.br/rpc/v1/dados-tabulares-monitor?tipo_area=1&area={geocod_uf}
```

`tipo_area=1` é o nível UF; `area` é o geocódigo IBGE de 2 dígitos (23 = CE,
35 = SP). Uma requisição por UF, sem autenticação.

Regenerar (idempotente):

```bash
python -m src.coleta.monitor_secas.download
python -m src.coleta.monitor_secas.download --ufs CE BA --forcar
```

## O que deu certo

- **O dado vem pronto no nível que o projeto precisa:** mensal, por UF,
  classificado por especialistas. Nada de reconstruir severidade de seca a partir
  de precipitação bruta.
- **Uma requisição por UF traz a série inteira** — 27 chamadas, roda em segundos.
- **A ponderação por área de município já vem feita pela ANA.** Isso elimina a
  parte mais trabalhosa do ticket e **dispensa `geopandas`** por completo.
- **Sanidade histórica confirmada:** o Ceará aparece com 100% do território em
  seca (S0+) em 2015-01 e 63,64% em seca excepcional (S4) em 2017-01 — a grande
  seca do Nordeste, na intensidade que ela realmente teve. E 2021 sai como o ano
  mais seco do Centro-Sul.

## O que deu errado / exigiu cuidado

### A página de "dados tabulares" não tem arquivo para baixar
<https://monitordesecas.ana.gov.br/dados-tabulares> é uma aplicação Angular que
monta o CSV no navegador. Não existe CSV no servidor. A API acima foi encontrada
lendo o bundle JavaScript do site.

*(O bundle também expõe credenciais OAuth de um usuário administrativo. Elas
**não são usadas** — os endpoints `rpc/v1` respondem sem token.)*

### O campo `area` não é km², apesar do nome
É o percentual do território da UF em **pontos-base**: `10000` = 100,00%. E as
categorias são **cumulativas** — `S2` significa "área em seca grave *ou pior*",
não "área exatamente em S2".

Tratar como km² produz percentuais silenciosamente absurdos. A evidência de que é
pontos-base: o valor satura em exatamente `10000`, com uma nuvem de valores logo
abaixo (9998, 9995, 9986...), e `S0 >= S1 >= S2 >= S3 >= S4` vale em **todos** os
2.422 registros, sem uma exceção.

Consequência para a média ponderada: é preciso **desfazer o acúmulo** antes de
aplicar os pesos S0=1…S4=5, senão a área em seca extrema é contada cinco vezes.

### A API empilha todas as revisões do mês sem dizer qual vale
**66 dos 2.422 meses** vêm com a categoria repetida 2 a 4 vezes, e entre as
revisões antigas há erros já corrigidos:

| Caso | Valores por `id` | Correto |
|---|---|---|
| BA 2016-06 `S4` | 1570→`0`, **1575→`123456`**, 1580→`0` | `0` (placeholder digitado à mão) |
| BA 2015-04 `S0` | 711→`9847`, **796→`984700`**, 801→`9847` | `9847` (escala 100× errada) |

A regra é **maior `id` vence**. Pegar o máximo, o mínimo ou a média entre
revisões importa o lixo sem reclamar — foi o que aconteceu na primeira versão do
coletor, e só o validador pegou. As 127 divergências ficam registradas em
`outputs/tabelas/monitor_secas_revisoes_divergentes.csv`.

### Categorias em minúsculas
AL e CE em 2020-03 trazem `s0`..`s4` **junto** das maiúsculas (10 chaves no mesmo
mês). Sem normalizar a caixa, viram categorias distintas.

### Um mês logicamente impossível
MA em 2014-11 tem `S3=0` com `S4=13` — impossível sob categorias cumulativas
(S4 ⊆ S3), e sem revisão posterior que corrija. Fica sinalizado na coluna
`inconsistente` em vez de ter um valor inventado. Cai fora da janela-alvo
(2015-01+), então não contamina a entrega.

### A cobertura desbalanceada é uma armadilha de modelagem
Até 2018 a série tem **apenas Nordeste**. Um modelo treinado sem cuidado vai
confundir "seca" com "ser do Nordeste". Os meses pré-monitoramento são `NaN`,
**nunca zero** — 1.358 das 3.726 linhas da saída. Tabela completa em
[`docs/cobertura_monitor_secas.md`](../../../docs/cobertura_monitor_secas.md).

## O que foi gerado a partir daqui

`data/interim/seca_uf_mes.parquet` — 27 UFs × 138 meses = **3.726 linhas × 14
colunas**. Todos os critérios de aceite do T-015 passam
(`python -m src.coleta.monitor_secas.validar`).

---

# Dicionário de colunas de `seca_uf_mes.parquet`

## Chave

| Coluna | Tipo | O que é |
|---|---|---|
| `sigla_uf` | `str` | UF, sempre preenchida. Toda junção do projeto passa por aqui, nunca por nome de cidade |
| `ano_mes` | `str` | Mês no formato `YYYY-MM` (ex. `2017-01`). Escolhido por ser seguro em junção e ordenável como texto |
| `ano`, `mes` | `int` | Os mesmos dois campos separados, por conveniência para agrupar |

## Percentuais de área — e a pegadinha do sufixo `plus`

As cinco colunas `pct_area_*plus` são **percentuais da área do estado**, de 0 a
100, e são **cumulativas**. O sufixo `plus` é literal:

| Coluna | Significa |
|---|---|
| `pct_area_S0plus` | % da UF em seca **fraca ou pior** (ou seja, qualquer seca) |
| `pct_area_S1plus` | % em seca **moderada ou pior** |
| `pct_area_S2plus` | % em seca **grave ou pior** |
| `pct_area_S3plus` | % em seca **extrema ou pior** |
| `pct_area_S4plus` | % em seca **excepcional** (é a última categoria, não há "ou pior") |

Por serem cumulativas, vale sempre
`S0plus >= S1plus >= S2plus >= S3plus >= S4plus`. O validador confere isso em
todas as linhas.

> **O erro fácil aqui é somar essas colunas.** Elas se contêm umas às outras, e
> somar dá muito mais que 100%. Para obter a faixa **exclusiva** (a área que está
> em S2 e não pior), use subtração: `pct_area_S2plus - pct_area_S3plus`.

Exemplo real — o Ceará em 2017-01, auge da seca do Nordeste:

```
pct_area_S0plus  100.00   <- o estado inteiro em alguma seca
pct_area_S1plus  100.00
pct_area_S2plus  100.00   <- o estado inteiro em seca grave ou pior
pct_area_S3plus   88.78
pct_area_S4plus   63.64   <- 63,64% do Ceará em seca excepcional
```

## Colunas derivadas

### `severidade_media` — índice de 0 a 5 para a UF inteira

Toma a faixa **exclusiva** de cada categoria (desfazendo o acúmulo), aplica os
pesos do ticket (S0=1, S1=2, S2=3, S3=4, S4=5) e divide pela área **total** da UF,
de modo que a área sem seca entra com peso 0:

```
severidade_media = Σ(peso_i × faixa_exclusiva_i) / área_total_da_UF
```

* `0` = nenhuma seca em lugar nenhum
* `5` = todo o território em seca excepcional
* Ceará em 2017-01: **4,52**. Máximo observado na série: **4,96**

É a coluna mais útil para modelagem: resume extensão e intensidade num número só e
é comparável entre UFs e entre meses.

### `severidade_media_area_seca` — severidade *dentro* da área seca

Mesmo numerador, dividido só pela área seca em vez da UF inteira. Responde outra
pergunta: *"quando dá seca aqui, ela costuma ser forte?"*. Varia de 1 a 5.

**É indefinida no mês sem seca alguma** — por isso tem 1.487 nulos, 129 a mais que
as demais colunas.

> Use com cuidado: um mês com apenas 1% do estado em seca excepcional dá
> severidade **5** nesta coluna e **0,05** na `severidade_media`. Ela mede
> intensidade, não impacto.

### `meses_consecutivos_S2plus` — a memória da seca

Há quantos meses seguidos existe alguma área da UF em seca grave ou pior. Seca é
acumulativa: 6 meses seguidos machucam a safra muito mais que 1 mês isolado, e
essa memória se perde numa coluna mensal solta. Vai de 0 a **89** (a Bahia,
terminando em 2021-11).

Duas limitações honestas, que precisam constar no relatório:

* a contagem **zera num buraco da série** — não dá para afirmar continuidade
  através de um mês sem dado;
* a contagem **começa do 1 quando a UF entra no monitoramento**. A UF que já
  estava em seca ao ser incluída tem a duração **subestimada**. O Ceará em 2017-01
  marca 31 meses, contados desde que entrou no Monitor, não desde que a seca de
  fato começou.

É subestimativa honesta, preferível a um número inventado.

## As duas flags

### `monitorado` (`bool`) — a coluna mais importante para não errar a análise

`False` quando a UF ainda não fazia parte do Monitor naquele mês. Das 3.726
linhas, **1.358 são pré-monitoramento**, e nelas todos os percentuais são `NaN` —
**nunca zero**.

Exemplo — São Paulo em 2016-05 (o estado só entrou no Monitor em 2020-11):

```
pct_area_S0plus              NaN
pct_area_S2plus              NaN
severidade_media             NaN
meses_consecutivos_S2plus   <NA>
monitorado                 False
```

Preencher isso com zero ensinaria ao modelo que "não havia seca no Sul antes de
2020", o que é falso: ninguém estava medindo. E como **até 2018 a série só tem
Nordeste**, um modelo descuidado vai confundir "seca" com "ser do Nordeste".

Duas saídas razoáveis para o T-023/T-041: restringir esta feature a 2020+, ou
manter a janela toda e tratar `NaN` explicitamente. Nunca imputar zero.

### `inconsistente` (`bool`)

Marca mês que viola a monotonia cumulativa (por exemplo `S3=0` com `S4>0`, que é
impossível, já que S4 está contido em S3). Na janela entregue está **tudo
`False`**: o único caso encontrado na fonte (Maranhão, 2014-11) cai fora do
período. A coluna existe para que o mesmo defeito, se aparecer em dados futuros,
seja sinalizado em vez de silenciosamente agregado.

## Resumo de tipos e preenchimento

| Coluna | Tipo | Preenchidas | Nulas | Faixa observada |
|---|---|---|---|---|
| `sigla_uf` | `str` | 3.726 | 0 | — |
| `ano_mes` | `str` | 3.726 | 0 | `2015-01` a `2026-06` |
| `ano` | `int64` | 3.726 | 0 | 2015 – 2026 |
| `mes` | `int64` | 3.726 | 0 | 1 – 12 |
| `pct_area_S0plus` | `float64` | 2.368 | 1.358 | 0,00 – 100,00 |
| `pct_area_S1plus` | `float64` | 2.368 | 1.358 | 0,00 – 100,00 |
| `pct_area_S2plus` | `float64` | 2.368 | 1.358 | 0,00 – 100,00 |
| `pct_area_S3plus` | `float64` | 2.368 | 1.358 | 0,00 – 100,00 |
| `pct_area_S4plus` | `float64` | 2.368 | 1.358 | 0,00 – 96,13 |
| `severidade_media` | `float64` | 2.368 | 1.358 | 0,00 – 4,96 |
| `severidade_media_area_seca` | `float64` | 2.239 | 1.487 | 1,00 – 4,96 |
| `meses_consecutivos_S2plus` | `Float64` | 2.368 | 1.358 | 0 – 89 |
| `monitorado` | `bool` | 3.726 | 0 | — |
| `inconsistente` | `bool` | 3.726 | 0 | — |

> **Detalhe de tipo que pode morder:** `meses_consecutivos_S2plus` é `Float64`
> (o nullable do pandas, com N maiúsculo) e usa `<NA>`, não `NaN`. Foi necessário
> para representar "não monitorado" numa coluna que é conceitualmente inteira. Em
> comparações prefira `.isna()` a `== np.nan`.

## Como ler

```python
import pandas as pd
from src import config

seca = pd.read_parquet(config.DATA_INTERIM / "seca_uf_mes.parquet")

# só o que foi de fato medido
medido = seca[seca["monitorado"]]

# faixa exclusiva: área em seca grave, mas não extrema
seca["pct_area_apenas_S2"] = seca["pct_area_S2plus"] - seca["pct_area_S3plus"]
```
