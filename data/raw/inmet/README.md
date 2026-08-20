# `data/raw/inmet/` — dados meteorológicos históricos do INMET

**Ticket:** [T-014](../../../tickets/01-coleta/T-014-inmet.md) ·
**Coletor:** [`src/coleta/inmet/`](../../../src/coleta/inmet/) ·
**Coletado em:** 2026-08-13

## O que está aqui

13 arquivos ZIP, um por ano, exatamente como vieram do portal. **Nunca editar.**

| Arquivo | Tamanho | Estações | Dias-estação gerados | Chuva presente |
|---|---|---|---|---|
| `2014.zip` | 98,9 MB | 475 | 172.793 | 86,7% |
| `2015.zip` | 98,0 MB | 484 | 174.662 | 84,1% |
| `2016.zip` | 102,4 MB | 529 | 182.172 | 84,9% |
| `2017.zip` | 109,7 MB | 563 | 198.981 | 83,1% |
| `2018.zip` | 117,9 MB | 596 | 213.684 | 84,5% |
| `2019.zip` | 117,6 MB | 589 | 213.259 | 85,1% |
| `2020.zip` | 103,7 MB | 589 | 215.574 | 67,7% |
| `2021.zip` | 80,6 MB | 588 | 214.620 | **47,1%** |
| `2022.zip` | 90,4 MB | 567 | 206.205 | 62,0% |
| `2023.zip` | 107,1 MB | 567 | 206.955 | 77,0% |
| `2024.zip` | 102,8 MB | 565 | 206.790 | 72,9% |
| `2025.zip` | 90,9 MB | 594 | 209.177 | 59,4% |
| `2026.zip` | 55,1 MB | 638 | 133.027 | 56,8% |

**Total: 1,27 GB · 7.344 arquivos CSV de estação · 2.547.899 linhas estação×dia.**

2026 é parcial (vai até julho). 2014 está aqui por causa dos lags do T-023 — a
janela-alvo do projeto começa em 2015-01.

## De onde veio

```
https://portal.inmet.gov.br/uploads/dadoshistoricos/{ANO}.zip
```

Regenerar (idempotente — reaproveita o que já está completo):

```bash
python -m src.coleta.inmet.download
python -m src.coleta.inmet.download --verificar   # só checa integridade
```

## O que deu certo

- **URL previsível, sem scraping.** Um ZIP por ano, nome do arquivo é o ano.
- **Todos os 13 ZIPs baixaram íntegros** e abrem sem erro. Verificado lendo o
  índice central de cada um (`verificar_zip`).
- **Os metadados de estação vêm no cabeçalho de cada CSV** (8 primeiras linhas:
  região, UF, nome, código WMO, lat, lon, altitude, data de fundação). Bem mais
  confiável que raspar a página de catálogo, e é de lá que sai o
  `catalogo_estacoes.csv` — **701 estações, todas as 27 UFs, zero sem UF**.
- **Nenhum CSV ilegível** entre os 7.344 processados.
- **Sazonalidade fisicamente correta** no resultado: Amazonas com pico jan-abr,
  Ceará com 3-4 mm em set-out, Rio Grande do Sul distribuído o ano todo.

## O que deu errado / exigiu cuidado

### O portal recusa cliente "não-navegador"
Sem `User-Agent` de navegador o servidor responde `Connection reset by peer` —
não é 403, é a conexão caindo, o que confunde o diagnóstico. E **`HEAD` também é
recusado**: para descobrir o tamanho remoto é preciso `GET` com
`Range: bytes=0-0`. Ambos tratados em [`src/rede.py`](../../../src/rede.py).

### O formato muda ao longo dos anos, com quebra em 2019

| | 2014-2018 | 2019-2026 |
|---|---|---|
| Caminho no ZIP | `2014/INMET_...CSV` (subpasta) | `INMET_...CSV` (raiz) |
| Metadados | `REGIÃO:`, `ESTAÇÃO:` | `REGIAO:`, `ESTACAO:` |
| Data de fundação | `2000-05-07` | `07/05/00` |
| Cabeçalho data/hora | `DATA (YYYY-MM-DD)`, `HORA (UTC)` | `Data`, `Hora UTC` |
| Valor data/hora | `2014-01-01`, `00:00` | `2019/01/01`, `0000 UTC` |
| **Código de ausência** | `-9999` | **campo vazio** |

**São dois códigos de ausência diferentes.** Um coletor que trate só `-9999`
funciona até 2018 e falha em silêncio depois; um que trate só vazio faz o
inverso. Os dois entram em `na_values`.

Outros detalhes do arquivo: encoding `latin-1` (não UTF-8), separador `;`,
vírgula decimal, 8 linhas de metadados antes do cabeçalho, e um `;` sobrando no
fim de cada linha que cria uma coluna anônima.

### Duas falhas de cobertura que são da fonte, não do coletor

**1. Roraima.** 3 estações no catálogo, efetivamente 1 ativa. Em **2021 e 2026
não produziu nenhum dia válido**; em 2025, 24,7% do ano. Cobertura de 69,8% no
período — abaixo do critério de 90% do T-014. Amapá tem o mesmo problema, mais
brando (89,8%).

**2. Há um buraco nacional em 2021-2022.** Não é limitação de UF pequena: o Rio
Grande do Norte, com 9 estações e 100% de cobertura em todos os outros anos, cai
para **38,1% em 2021** e 68,2% em 2022. Veja a coluna "chuva presente" na tabela
acima despencar de 85,1% (2019) para 47,1% (2021).

E **2021 é justamente o ano da crise hídrica do Centro-Sul**, que o Monitor de
Secas (T-015) aponta como o episódio mais severo da série. O período de maior
interesse analítico é o de pior cobertura climática. Detalhe por UF × ano em
[`docs/cobertura_inmet.md`](../../../docs/cobertura_inmet.md).

### Volume
Os ZIPs de 2020 (103 MB) e 2024 (102 MB) passam do **limite rígido de 100 MB por
arquivo do GitHub**. Esta pasta nunca pode ir para o Git — o `.gitignore` já
cobre, e foi preciso corrigi-lo, porque as regras de `data/raw/` estavam
comentadas.

## O que foi gerado a partir daqui

- `data/interim/catalogo_estacoes.csv` — 701 estações
- `data/interim/clima_estacao_mes.parquet` — **a entrega final**: 83.814 linhas
  estação × mês × 28 colunas, num **arquivo único** de 4,7 MB
- `data/interim/clima_estacao_dia.parquet/` — etapa **intermediária** (2.547.899
  linhas, um arquivo por ano). Existe porque os índices de extremo
  (`dias_sem_chuva`, `max_dias_secos_seguidos`, `dias_calor_extremo`) **precisam**
  ser calculados no dia, antes da agregação mensal — depois são impossíveis de
  recuperar. Pode ser apagada sem perda: é reproduzível a partir destes ZIPs com
  `python -m src.coleta.inmet.agrega_dia`

**As 19 colunas de dados do CSV são todas mapeadas**, mas a tabela diária resume
17 delas em 11 grandezas (chuva, três temperaturas, três de umidade, radiação,
pressão, e duas de vento). Ficaram de fora, de propósito: os extremos horários de
pressão e de ponto de orvalho, que não acrescentam nada sobre a média diária, e
`VENTO, DIREÇÃO` — que é grandeza **circular** e não pode ser agregada com
`mean()` sem produzir número errado (a média de 350° e 10° dá 180°, o sentido
oposto). O detalhe horário em si continua só dentro dos ZIPs.

Próximo consumidor: **T-021** (agregação estação×dia → UF×mês).
