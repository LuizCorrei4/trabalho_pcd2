# T-014 — Coletor INMET: dados meteorológicos históricos

| Campo | Valor |
|---|---|
| **Etapa** | 1 Coleta |
| **Prioridade** | P0 |
| **Estimativa** | 6h |
| **Depende de** | T-002 |
| **Bloqueia** | T-021 |
| **Responsável** | Arthur |
| **Status** | 🔄 Em andamento |

## Contexto
Fonte primária de clima. O volume é grande (dado horário de centenas de estações) e a qualidade é irregular — estações abrem, fecham e falham. Este ticket só **baixa e consolida em dado diário por estação**; a agregação para UF×mês é o T-021.

## Entregável
`data/raw/inmet/{ANO}.zip` — arquivos brutos
`data/interim/clima_estacao_dia.parquet` — estação × dia
`data/interim/catalogo_estacoes.csv` — estação → UF, lat, lon, altitude

## Fonte
- ZIPs anuais ✅ verificado: `https://portal.inmet.gov.br/uploads/dadoshistoricos/{ANO}.zip` (2000→2026)
- Catálogo de estações automáticas: https://portal.inmet.gov.br/paginas/catalogoaut

## Tarefas
- [x] ~~`src/coleta/05_inmet_download.py`~~ → [`src/coleta/inmet/download.py`](../../src/coleta/inmet/download.py): baixa os ZIPs de 2014 a 2026 (1 ano a mais que o alvo, para lags). **1,27 GB, 13 anos, 7.344 arquivos de estação**
- [x] Montar `catalogo_estacoes.csv` a partir do cabeçalho de cada CSV dentro do ZIP → [`catalogo.py`](../../src/coleta/inmet/catalogo.py). **701 estações**
- [x] ~~`src/coleta/06_inmet_agrega_dia.py`~~ → [`agrega_dia.py`](../../src/coleta/inmet/agrega_dia.py): lê os CSVs de dentro do ZIP **sem extrair nada pro disco** (`zipfile` + `io.BytesIO`), um ano por vez, um CSV por vez
- [x] Agregar hora → dia por estação: `chuva_mm` (soma), `temp_min`/`temp_media`/`temp_max`, `umidade_media`, `radiacao_total`, `horas_validas`
- [x] **Extra ao ticket:** aproveitar as demais colunas do CSV, que já estavam sendo lidas e descartadas — `pressao_media_mb`, `temp_orvalho_media_c`, `umidade_min`/`umidade_max`, `vento_velocidade_media_ms`, `vento_rajada_max_ms`. São exatamente as grandezas que faltam para calcular **evapotranspiração**, e com ela o *índice de aridez simplificado* previsto na `docs/Proposta.md`. Sem isso, aquela variável exigiria reprocessar 1,27 GB de novo
- [x] Marcar como nulo o dia com `horas_validas < 18` — **aplicado por grandeza, não em bloco**, ver "Decisões" abaixo
- [x] Salvar em Parquet particionado por ano *(etapa intermediária)*
- [x] **Extra ao ticket:** `agrega_mes.py` reduz o diário a **estação × mês num arquivo único** (`data/interim/clima_estacao_mes.parquet`, 83.814 linhas, 4,7 MB). Junto vão os índices de extremo calculados **no nível diário** — `dias_sem_chuva`, `dias_chuva_forte`, `max_dias_secos_seguidos` e `dias_calor_extremo` (p90 por estação e mês-do-ano) — que é a exigência não negociável do T-021 e o que torna a tabela diária descartável

> **Nota sobre a organização dos arquivos:** o ticket sugeria
> `src/coleta/05_inmet_download.py` e `06_inmet_agrega_dia.py`. Ficou um
> **subpacote por fonte** (`src/coleta/inmet/`, `src/coleta/monitor_secas/`), com a
> ordem do pipeline documentada no README de cada pasta. Motivo prático: nome de
> módulo começando com dígito não é importável em Python (`import 01_download`
> é erro de sintaxe), o que obrigaria a gambiarras de `sys.path` para compartilhar
> `config.py` entre os scripts. Com subpacote, roda-se `python -m src.coleta.inmet.download`
> e os imports funcionam sem truque.

## Critérios de aceite
- [x] ≥ 400 estações no catálogo, todas com `sigla_uf` preenchida e batendo com `dim_uf` — **701 estações**, 0 sem UF, 0 sigla estranha
- [x] Todas as 27 UFs têm ao menos 1 estação — mínimo 3 (RR)
- [x] Chuva diária sempre ≥ 0 e < 500 mm; temperatura entre -10 °C e 50 °C — chuva máx **414,6 mm**; temperaturas dentro da faixa; 908 valores fora de faixa convertidos para `NaN`
- [x] Nenhum valor `-9999` sobrevivendo como número na tabela final — **0 ocorrências**, e 0 valores < -1000
- [ ] **Cobertura temporal: ≥ 90% dos dias do período têm ao menos 1 estação válida por UF** — **25/27 UFs atendem**. Falham **RR (69,8%)** e **AP (89,8%)**. Média 98,0%, mediana 100,0%

Reverificável com `python -m src.coleta.inmet.validar`, que imprime o número de
cada critério e sai com código 1 enquanto o quinto não passar.

### Sobre o critério que não passa
**Não é corrigível por código — é limitação da fonte**, e há dois problemas
distintos, documentados em [`docs/analises/cobertura_inmet.md`](../../docs/analises/cobertura_inmet.md)
com a tabela por UF × ano em `outputs/tabelas/inmet_cobertura_uf_ano.csv`:

1. **Roraima tem 3 estações no catálogo e efetivamente 1 ativa.** Em 2021 e 2026
   ela não produziu **nenhum** dia válido; em 2025, 24,7% do ano. A medição não
   existe. Amapá tem o mesmo problema, mais brando (89,8%, quase no corte).

2. **Há um buraco nacional em 2021-2022**, que não tem a ver com UF pequena: o Rio
   Grande do Norte, com 9 estações e 100% de cobertura em todos os outros anos, cai
   para **38,1% em 2021** e 68,2% em 2022. O preenchimento da coluna de chuva no
   país cai de 85,1% (2019) para **47,1% (2021)**.

   Isso é especialmente inconveniente aqui: **2021 é justamente o ano da crise
   hídrica do Centro-Sul**, que o T-015 aponta como o episódio mais severo da série.
   A análise desse período vai depender de imputação, e a incerteza precisa constar
   no relatório do T-050.

**O que falta é decisão do grupo, não mais código.** Duas saídas:
* aceitar a limitação e ajustar o critério (documentando RR/AP como UFs de
  cobertura insuficiente), ou
* trazer o [NASA POWER](https://power.larc.nasa.gov/) como fonte de imputação no
  T-021 — que este ticket já recomendava de qualquer forma, e que resolveria tanto
  Roraima quanto o buraco de 2021-2022.

O T-021 não está bloqueado por isso: a tabela `clima_estacao_dia.parquet` está
completa e válida, e a imputação por normal climatológica já é tarefa dele.

## Como foi feito
Código em [`src/coleta/inmet/`](../../src/coleta/inmet/) — detalhes completos no
[README do coletor](../../src/coleta/inmet/README.md).

```bash
python -m src.coleta.inmet.download      # 13 ZIPs (~1,27 GB) -> data/raw/inmet/
python -m src.coleta.inmet.catalogo      # -> data/interim/catalogo_estacoes.csv
python -m src.coleta.inmet.agrega_dia    # -> data/interim/clima_estacao_dia.parquet/
python -m src.coleta.inmet.validar       # critérios de aceite
```

**Não precisou de scraping.** Os ZIPs estão em URL previsível, mas o servidor
impõe duas condições descobertas na prática: exige **User-Agent de navegador**
(sem ele responde `Connection reset by peer`) e **recusa `HEAD`** — para saber o
tamanho remoto é preciso `GET` com `Range: bytes=0-0`. Ambas tratadas em
`src/rede.py`. O catálogo saiu dos cabeçalhos dos CSVs, como o ticket recomendava,
sem tocar na página de catálogo do INMET.

### Decisões que valem registro
- **O corte de 18 horas válidas é por grandeza, não em bloco.** Chuva e temperatura
  falham de forma independente no INMET (é comum o pluviômetro parar e o termômetro
  seguir), então há `horas_validas` e `horas_validas_chuva` separados. Invalidar a
  chuva de um dia não joga fora a temperatura boa do mesmo dia.
- **A radiação não é cortada pelas 18 horas de temperatura**, porque é nula à noite
  por natureza — o critério dela é o dia ter registro suficiente.
- **`min_count=1` na soma da chuva.** Sem isso um dia inteiro de `NaN` soma `0`, e
  "não mediu" fica indistinguível de "não choveu" — erro que sobrevive a revisão
  rápida e enviesaria `dias_sem_chuva` no T-021.

## Armadilhas
- **`-9999` é o código de ausência do INMET.** Se não for convertido para `NaN` antes de qualquer média, a temperatura média da estação vira um número absurdamente negativo e contamina tudo silenciosamente. Tratar isso na leitura, não depois.
- Encoding dos CSVs é **`latin-1`**, não UTF-8. E o separador é `;`, com vírgula decimal (`decimal=","`).
- As 8 primeiras linhas de cada CSV são cabeçalho de metadados, não dados. `skiprows=8`.
- Os nomes das colunas mudaram ao longo dos anos (`PRECIPITAÇÃO TOTAL, HORÁRIO (mm)` vs variações). Normalizar os nomes com um mapeamento explícito por padrão de texto, não por posição.
- Volume: os ZIPs somados passam de 1 GB. Não versionar no git (já coberto pelo `.gitignore` do T-001).

### Confirmadas na prática, e o que o ticket não previa
- **A deriva de formato é muito maior que só os acentos, e quebra em 2019:**

  | | 2014-2018 | 2019-2026 |
  |---|---|---|
  | Caminho no ZIP | `2014/INMET_...CSV` (subpasta) | `INMET_...CSV` (raiz) |
  | Metadados | `REGIÃO:`, `ESTAÇÃO:` | `REGIAO:`, `ESTACAO:` |
  | Data de fundação | `2000-05-07` | `07/05/00` |
  | Cabeçalho data/hora | `DATA (YYYY-MM-DD)`, `HORA (UTC)` | `Data`, `Hora UTC` |
  | Valor data/hora | `2014-01-01`, `00:00` | `2019/01/01`, `0000 UTC` |
  | **Código de ausência** | `-9999` | **campo vazio** |

  Ou seja: **há dois códigos de ausência**, e os dois precisam entrar em
  `na_values`. Um coletor que só trate `-9999` funciona em 2014-2018 e falha em
  silêncio depois; um que só trate vazio faz o inverso.
- **O mapeamento por texto precisa distinguir `TEMPERATURA MÁXIMA NA HORA ANT.` de
  `TEMPERATURA ORVALHO MAX. NA HORA ANT.`** — são grandezas diferentes e casar
  errado importa temperatura de ponto de orvalho como temperatura do ar.
- **`.gitignore` do T-001 estava com as regras de `data/raw/` comentadas** e sem
  `*.zip`. Corrigido: os ZIPs de 2020 (103 MB) e 2024 (102 MB) passam do **limite
  rígido de 100 MB por arquivo do GitHub** e teriam quebrado o push do grupo todo.
- **A rede de estações cresce ~35% no período** (475 em 2014 → 638 em 2026). Por
  isso o catálogo traz `ano_primeiro`/`ano_ultimo`: é o que permite ao T-021
  distinguir quebra de nível causada por estação nova de mudança real de clima.
- Há um `;` sobrando no fim de cada linha de dados, criando uma coluna anônima.

## Saídas
`data/interim/catalogo_estacoes.csv` — 701 estações, 27 UFs, zero sem `sigla_uf`.

`data/interim/clima_estacao_mes.parquet` — **entrega final**, arquivo único com
83.814 linhas estação × mês e 28 colunas, incluindo os índices de extremo.

`data/interim/clima_estacao_dia.parquet/` — intermediária, um arquivo por ano.
Descartável: reproduzível a partir dos ZIPs.

**Dependência do T-002:** o coletor usa `data/processed/dim_uf.csv` quando existe e
cai para a API do IBGE enquanto não existe (`src/ufs.py`), então não ficou
bloqueado. A validação contra a tabela canônica passa a valer sozinha quando o
T-002 entregar.

**Plano B não foi necessário:** o [NASA POWER](https://power.larc.nasa.gov/) segue
registrado como fonte de imputação para os buracos de cobertura no T-021, que é o
uso que o próprio ticket já recomendava de qualquer forma.
- **Alternativa se este ticket virar um pântano:** [NASA POWER](https://power.larc.nasa.gov/) entrega série **mensal** direto por lat/lon, em grade, sem falhas de estação e sem cadastro. Basta pedir o ponto de cada capital ou de cada centroide de UF. Perde-se granularidade diária (adeus `dias_sem_chuva`), mas resolve o clima básico em 1h em vez de 6h. Vale usar de qualquer forma como fonte de imputação para os buracos do INMET.
