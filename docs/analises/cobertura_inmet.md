# Cobertura temporal do INMET por UF (T-014)

Gerado por `python -m src.coleta.inmet.validar`. Não editar à mão.

Janela-alvo: **2015-01 a 2026-06**. Um dia conta como
coberto quando ao menos uma estação da UF registrou chuva **ou** temperatura
válida naquele dia.

O critério de aceite do T-014 é **>= 90%** dos dias por UF.

## Cobertura no período, por UF

| UF | % dos dias cobertos | Atende o critério |
|---|---|---|
| RR | 69.8% | **NÃO** |
| AP | 89.8% | **NÃO** |
| RN | 91.8% | sim |
| RO | 96.9% | sim |
| SE | 97.9% | sim |
| AC | 99.6% | sim |
| AL | 100.0% | sim |
| AM | 100.0% | sim |
| GO | 100.0% | sim |
| MA | 100.0% | sim |
| MG | 100.0% | sim |
| MS | 100.0% | sim |
| BA | 100.0% | sim |
| CE | 100.0% | sim |
| DF | 100.0% | sim |
| ES | 100.0% | sim |
| PE | 100.0% | sim |
| PB | 100.0% | sim |
| PA | 100.0% | sim |
| MT | 100.0% | sim |
| RJ | 100.0% | sim |
| PR | 100.0% | sim |
| RS | 100.0% | sim |
| PI | 100.0% | sim |
| SC | 100.0% | sim |
| SP | 100.0% | sim |
| TO | 100.0% | sim |

## Cobertura média entre UFs, por ano

| Ano | Cobertura média |
|---|---|
| 2015 | 99.2% |
| 2016 | 99.6% |
| 2017 | 99.4% |
| 2018 | 99.9% |
| 2019 | 100.0% |
| 2020 | 98.9% |
| 2021 | 91.9% |
| 2022 | 96.1% |
| 2023 | 97.7% |
| 2024 | 98.8% |
| 2025 | 97.2% |
| 2026 | 96.0% |

A tabela completa por UF × ano está em
`outputs/tabelas/inmet_cobertura_uf_ano.csv`.

## Duas limitações reais da fonte

**1. Roraima.** São 3 estações no catálogo e efetivamente 1 ativa na maior
parte da série. Em 2021 e 2026 ela não produziu **nenhum** dia válido, e em
2025 cobriu 24,7% do ano. Nenhum tratamento de dados resolve isso — a medição
não existe. Amapá tem problema parecido, mais brando.

**2. Há um buraco nacional em 2021-2022.** Não é limitação de UF pequena: o Rio
Grande do Norte, com 9 estações e 100% de cobertura em todos os outros anos, cai
para 38,1% em 2021 e 68,2% em 2022. O preenchimento da coluna de chuva no país
inteiro cai de 85,1% em 2019 para 47,1% em 2021.

Isso é especialmente inconveniente para este projeto: **2021 é justamente o ano
da crise hídrica do Centro-Sul**, que o Monitor de Secas (T-015) aponta como o
mais severo da série. A análise desse episódio vai depender de imputação, e a
incerteza precisa constar no relatório.

## Encaminhamento

Este é um limite da fonte, não do coletor, e a decisão de como tratá-lo é do
T-021 (agregação para UF × mês), que já tem a imputação por normal
climatológica entre suas tarefas. O próprio T-014 registra o
[NASA POWER](https://power.larc.nasa.gov/) como fonte de imputação recomendada:
entrega série por lat/lon em grade, sem falha de estação, e resolveria tanto
Roraima quanto o buraco de 2021-2022.
