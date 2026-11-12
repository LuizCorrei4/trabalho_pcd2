# Cobertura do Monitor de Secas por UF (T-015)

Gerado por `python -m src.coleta.monitor_secas.agrega_uf_mes`. Não editar à mão.

Janela-alvo do projeto: **2015-01 a 2026-06** (138 meses).

O Monitor de Secas nasceu no Nordeste em 2014 e foi expandindo para o resto do
país ao longo dos anos. Os meses anteriores à entrada de cada UF estão como
`NaN` na tabela `seca_uf_mes.parquet` — **não como zero**. Ausência de
monitoramento não é ausência de seca, e tratar como zero criaria um viés
regional grave nos primeiros anos da série.

| UF | Primeiro mês | Último mês | Meses com dado | % da janela | Buracos internos |
|---|---|---|---|---|---|
| AL | 2015-01 | 2026-06 | 138 | 100.0% | 0 |
| BA | 2015-01 | 2026-06 | 138 | 100.0% | 0 |
| CE | 2015-01 | 2026-06 | 138 | 100.0% | 0 |
| MA | 2015-01 | 2026-06 | 138 | 100.0% | 0 |
| PB | 2015-01 | 2026-06 | 138 | 100.0% | 0 |
| PE | 2015-01 | 2026-06 | 138 | 100.0% | 0 |
| PI | 2015-01 | 2026-06 | 138 | 100.0% | 0 |
| RN | 2015-01 | 2026-06 | 138 | 100.0% | 0 |
| SE | 2015-01 | 2026-06 | 137 | 99.3% | 1 |
| MG | 2018-11 | 2026-06 | 92 | 66.7% | 0 |
| ES | 2019-04 | 2026-06 | 87 | 63.0% | 0 |
| TO | 2019-12 | 2026-06 | 79 | 57.2% | 0 |
| RJ | 2020-05 | 2026-06 | 74 | 53.6% | 0 |
| GO | 2020-06 | 2026-06 | 73 | 52.9% | 0 |
| DF | 2020-07 | 2026-06 | 72 | 52.2% | 0 |
| MS | 2020-07 | 2026-06 | 72 | 52.2% | 0 |
| PR | 2020-08 | 2026-06 | 71 | 51.4% | 0 |
| RS | 2020-08 | 2026-06 | 71 | 51.4% | 0 |
| SC | 2020-08 | 2026-06 | 71 | 51.4% | 0 |
| SP | 2020-11 | 2026-06 | 68 | 49.3% | 0 |
| MT | 2021-06 | 2026-06 | 61 | 44.2% | 0 |
| RO | 2022-08 | 2026-06 | 47 | 34.1% | 0 |
| AC | 2022-11 | 2026-06 | 44 | 31.9% | 0 |
| AM | 2022-12 | 2026-06 | 43 | 31.2% | 0 |
| PA | 2023-04 | 2026-06 | 39 | 28.3% | 0 |
| RR | 2023-11 | 2026-06 | 32 | 23.2% | 0 |
| AP | 2023-12 | 2026-06 | 31 | 22.5% | 0 |

**Buracos internos** são meses sem dado *dentro* do intervalo em que a UF já
era monitorada — falha da série, não expansão pendente. Também ficam `NaN`.
