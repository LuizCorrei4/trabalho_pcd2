# T-014 — Coletor INMET (dados meteorológicos históricos)

Ticket: [`tickets/01-coleta/T-014-inmet.md`](../../../tickets/01-coleta/T-014-inmet.md)

## Como rodar

A partir da **raiz do repositório**, com o ambiente `pcd2` ativo:

```bash
python -m src.coleta.inmet.download      # 1. baixa 13 ZIPs (~1,27 GB) -> data/raw/inmet/
python -m src.coleta.inmet.catalogo      # 2. gera data/interim/catalogo_estacoes.csv
python -m src.coleta.inmet.agrega_dia    # 3. hora -> dia  (intermediário, 13 arquivos)
python -m src.coleta.inmet.agrega_mes    # 4. dia -> mês   (ENTREGA: 1 arquivo só)
python -m src.coleta.inmet.validar       # 5. confere os critérios de aceite
```

A entrega final é o **arquivo único** `data/interim/clima_estacao_mes.parquet`
(4,7 MB). A tabela diária é etapa intermediária: ela existe porque os índices de
extremo **precisam** ser calculados no dia, e é sempre reproduzível a partir dos
ZIPs.

Opções úteis:

| Comando | Efeito |
|---|---|
| `download --anos 2015 2016` | trabalha só nesses anos |
| `download --forcar` | rebaixa mesmo o que já está completo |
| `download --verificar` | não baixa nada, só checa a integridade dos ZIPs presentes |
| `agrega_dia --limpar` | apaga a saída antes de reprocessar |

Tempo aproximado: o download depende da rede (~10 min numa conexão razoável), a
agregação leva cerca de 1 minuto por ano.

O download é **idempotente e atômico**: rodar de novo reaproveita o que já está
completo, e um arquivo interrompido nunca fica com o nome final. Com 1,27 GB em
13 arquivos, retomar de onde parou importa.

## Não é scraping

O INMET publica ZIPs anuais em URL previsível, então não há HTML para raspar:

```
https://portal.inmet.gov.br/uploads/dadoshistoricos/{ANO}.zip
```

Duas exigências do servidor, descobertas na prática:

* **User-Agent de navegador é obrigatório.** Sem ele o portal responde
  `Connection reset by peer` e o download simplesmente falha. Tratado em
  [`src/rede.py`](../../rede.py).
* **`HEAD` é recusado.** Para descobrir o tamanho do arquivo remoto (e saber se o
  download local está completo) é preciso usar `GET` com `Range: bytes=0-0`.

O catálogo de estações também **não** vem da página
<https://portal.inmet.gov.br/paginas/catalogoaut>: os metadados saem do cabeçalho
de cada CSV dentro do ZIP, como o próprio ticket recomenda. É a mesma fonte do
dado, vem sempre junto, e não depende de a página estar no ar nem de manter o
layout.

## O formato muda ao longo dos anos — muito mais do que só os acentos

Esta é a maior fonte de armadilha do ticket. Há uma quebra limpa em **2019**:

| | 2014-2018 | 2019-2026 |
|---|---|---|
| Caminho dentro do ZIP | `2014/INMET_...CSV` (subpasta) | `INMET_...CSV` (raiz) |
| Rótulos de metadado | `REGIÃO:`, `ESTAÇÃO:` (com acento) | `REGIAO:`, `ESTACAO:` (sem) |
| Data de fundação | `2000-05-07` | `07/05/00` |
| Cabeçalho de data / hora | `DATA (YYYY-MM-DD)`, `HORA (UTC)` | `Data`, `Hora UTC` |
| Valor de data / hora | `2014-01-01`, `00:00` | `2019/01/01`, `0000 UTC` |
| **Código de ausência** | `-9999` | **campo vazio** |

Consequências no código:

* **`colunas.py` casa por padrão de texto, não por posição.** Tira acento, sobe
  para maiúscula e procura trecho característico. A ordem das colunas é estável
  nos 13 anos, então casar por posição funcionaria *hoje* — e quebraria calado no
  dia em que o INMET inserir uma coluna no meio. O mapeamento ainda **confere que
  cada destino casou exatamente uma vez**: mudança futura de formato vira erro
  alto, não coluna silenciosamente vazia.
* Os padrões precisam distinguir `TEMPERATURA MÁXIMA NA HORA ANT.` de
  `TEMPERATURA ORVALHO MAX. NA HORA ANT.` — são grandezas diferentes e a segunda
  não pode entrar como temperatura do ar.
* **Os dois códigos de ausência são declarados juntos** em `na_values`, porque a
  série cobre os dois regimes.
* Há um `;` sobrando no fim de cada linha de dados, que cria uma coluna anônima.
  Ela é descartada por não casar com nenhum padrão.

## `-9999`: tratado na leitura, não depois

É a armadilha que o ticket destaca, e com razão: se um `-9999` sobrevive como
número até uma média, a temperatura da estação vira algo como -3.000 °C e
**contamina tudo sem levantar exceção nenhuma**. O tratamento é em duas camadas:

1. `na_values` no `read_csv` — todas as grafias já vistas do sentinela, mais
   variantes plausíveis (`-9999,0`, `-9999.00`...);
2. uma varredura defensiva depois da leitura que compara com `-9999` e **conta**
   o que tenha escapado, para o problema aparecer no relatório final em vez de
   virar média envenenada.

O validador fecha o ciclo checando que nenhum `-9999` — e nenhum valor abaixo de
-1000 — sobrou na tabela final.

## Memória: um ano por vez, um CSV por vez

Os ZIPs somam 1,27 GB comprimidos, com **7.344 arquivos de estação**.
Descomprimir tudo para o disco, ou empilhar os 13 anos num DataFrame só, consome
vários GB e derruba máquina de 8 GB.

O `agrega_dia.py` processa **um ano por vez, um CSV por vez**: cada CSV é lido de
dentro do ZIP direto para memória (`zipfile` + `io.BytesIO`, nunca para o disco),
agregado na hora para ~365 linhas diárias, e o horário é descartado. O pico de
memória fica em dezenas de MB, e cada ano é gravado em seu próprio Parquet antes
do ano seguinte começar.

## Agregação hora → dia

| Coluna | Como sai |
|---|---|
| `chuva_mm` | **soma** das 24 horas (`min_count=1`) |
| `temp_media` | média da temperatura horária do ar |
| `temp_max` / `temp_min` | máx / mín das colunas horárias de máxima e mínima |
| `umidade_media` | média da umidade relativa horária |
| `radiacao_total` | soma da radiação global (`min_count=1`) |
| `pressao_media_mb` | média da pressão ao nível da **estação** (não reduzida ao nível do mar) |
| `temp_orvalho_media_c` | média do ponto de orvalho |
| `umidade_min` / `umidade_max` | mín / máx das colunas horárias de extremo de umidade |
| `vento_velocidade_media_ms` | média da velocidade horária |
| `vento_rajada_max_ms` | **pico** de rajada do dia |
| `horas_validas` | horas com temperatura não nula |
| `horas_validas_chuva` | horas com precipitação não nula |
| `horas_registradas` | quantidade de linhas horárias no dia |

As seis grandezas do meio (pressão, orvalho, extremos de umidade e vento) foram
acrescentadas depois das cinco originais. São exatamente o que falta para calcular
**evapotranspiração** e, com ela, o *índice de aridez simplificado* previsto na
[`docs/Proposta.md`](../../../docs/Proposta.md) — que precisa de temperatura,
umidade, radiação, vento e pressão juntos. Sem elas, aquela variável não sairia
sem reprocessar 1,27 GB de ZIP de novo.

**`vento_direcao_gr` foi deliberadamente deixada de fora.** Direção é grandeza
circular: a média aritmética de 350° e 10° dá 180°, que aponta exatamente para o
lado oposto do correto. Agregar direção exige média vetorial (e um comprimento
resultante junto, para dizer se a média significa alguma coisa). Como direção do
vento tem uso marginal neste projeto, ficou fora — em vez de entrar como uma
coluna silenciosamente errada. Se o T-021 precisar dela, é o cálculo certo que
tem de ser implementado, não um `mean()`.

Detalhes que não são óbvios:

* **`min_count=1` na chuva.** Sem isso, um dia inteiro de `NaN` soma `0`, e "não
  mediu" fica indistinguível de "não choveu" — um erro que sobrevive a qualquer
  revisão rápida e enviesa `dias_sem_chuva` no T-021.
* **O corte de 18 horas válidas é aplicado por grandeza, não em bloco.** Chuva e
  temperatura falham de forma independente no INMET (é comum o pluviômetro parar
  e o termômetro continuar). Por isso há dois contadores, e invalidar a chuva não
  joga fora a temperatura boa do mesmo dia.
* **A radiação não é cortada pelas 18 horas de temperatura**, porque é nula à
  noite por natureza — exigir 18 horas válidas dela descartaria todos os dias. O
  critério dela é o dia ter registro suficiente (`horas_registradas`).
* **Faixas físicas** (`chuva` em [0, 500) mm, temperatura em [-10, 50] °C,
  umidade em [0, 100] %) viram `NaN` fora do limite, e cada descarte é contado.
  Chuva de 900 mm num dia não é clima extremo, é sentinela disfarçada.

## Saídas

### `data/interim/catalogo_estacoes.csv`

**701 estações únicas**, todas as 27 UFs cobertas, zero sem `sigla_uf`.

| Coluna | Descrição |
|---|---|
| `codigo_estacao` | código WMO (`A001`), a chave |
| `nome`, `sigla_uf`, `regiao_inmet` | identificação |
| `lat`, `lon`, `altitude` | localização |
| `data_fundacao` | os dois formatos da fonte, já normalizados |
| `ano_primeiro`, `ano_ultimo`, `n_anos` | vida útil da estação na série |

`ano_primeiro`/`ano_ultimo` existem porque **estações abrem e fecham**: são 475
em 2014 e 638 em 2026. O T-021 precisa disso para explicar degrau na média de uma
UF — se a contagem de estações salta de 3 para 9, qualquer quebra de nível ali é
artefato, não clima.

### `data/interim/clima_estacao_dia.parquet/`

Um arquivo por ano (`clima_estacao_dia_2014.parquet`, ...), como o ticket pede.
Ler o conjunto todo de uma vez:

```python
import pandas as pd
from src import config
clima = pd.read_parquet(config.DATA_INTERIM / "clima_estacao_dia.parquet")
```

Chave: `codigo_estacao` × `data`. Traz também `sigla_uf`, `ano` e `mes` para
facilitar o agrupamento do T-021.

## Cobertura: o critério de aceite que não passa

4 dos 5 critérios do ticket passam. O quinto — "≥ 90% dos dias do período com ao
menos 1 estação válida por UF" — é atendido por **25 das 27 UFs**. Média 98,0%,
mediana 100,0%. Detalhe completo em
[`docs/analises/cobertura_inmet.md`](../../../docs/analises/cobertura_inmet.md), gerado pelo
`validar.py`, com a tabela por UF × ano em
`outputs/tabelas/inmet_cobertura_uf_ano.csv`.

São dois problemas de natureza diferente, e nenhum é do coletor:

**1. Roraima (69,8%) e Amapá (89,8%).** RR tem 3 estações no catálogo e
efetivamente 1 ativa: em **2021 e 2026 ela não produziu nenhum dia válido**, e em
2025 cobriu 24,7% do ano. Não há tratamento de dados que resolva — a medição não
existe.

**2. Um buraco nacional em 2021-2022.** Este é o mais importante, e não aparece se
só se olhar as UFs pequenas: o **Rio Grande do Norte**, com 9 estações e 100% de
cobertura em todos os outros anos, cai para **38,1% em 2021** e 68,2% em 2022. O
preenchimento da coluna de chuva no país inteiro vai de 85,1% (2019) para **47,1%
(2021)**.

E 2021 é exatamente o ano da crise hídrica do Centro-Sul, que o T-015 aponta como
o episódio mais severo da série do Monitor de Secas. Ou seja: **o período de maior
interesse analítico é o de pior cobertura climática**. A análise desse episódio vai
depender de imputação, e a incerteza tem de constar no relatório.

## Agregação dia → mês (a entrega final)

`agrega_mes.py` reduz as 2.547.899 linhas diárias a **83.814 linhas
estação × mês**, num arquivo só de 4,7 MB, cobrindo 701 estações e 151 meses.

### Não é um `resample('M')`

O T-021 é categórico: **os índices de extremo têm de sair do nível diário, antes
da agregação mensal** — depois são impossíveis de recuperar. `dias_sem_chuva` não
se deduz de `chuva_mm_mes`: 90 mm num mês podem ser 3 mm em 30 dias ou 90 mm num
dia só, e para uma safra a diferença é tudo.

Por isso esta etapa varre o diário e guarda, como colunas do mensal, tudo o que
só existe no dia:

| Coluna | O que é |
|---|---|
| `dias_sem_chuva` | dias com menos de 1 mm |
| `dias_chuva_forte` | dias com mais de 50 mm |
| `max_dias_secos_seguidos` | **maior sequência de dias secos** — o veranico, que é o que de fato mata lavoura |
| `dias_calor_extremo` | dias com máxima acima do p90 daquela estação naquele mês-do-ano |

`dias_calor_extremo` usa um limiar **por estação e por mês do calendário**,
calculado sobre a série inteira: 32 °C é banal em Teresina em novembro e
excepcional em Curitiba em julho. Um limiar único para o país não mediria nada.

`max_dias_secos_seguidos` **não atravessa a virada do mês**, e um dia sem medição
**quebra** a sequência — não se pode afirmar que não choveu num dia em que ninguém
olhou. Essas duas regras estão cobertas por teste.

### Demais colunas

Acumulados e médias: `chuva_mm_mes`, `radiacao_total_mes` (somas);
`temp_media`, `temp_max_media`, `temp_min_media`, `amplitude_termica_media`,
`umidade_media`, `pressao_media_mb`, `temp_orvalho_media_c`,
`vento_velocidade_media_ms` (médias); `temp_max_abs`, `temp_min_abs`,
`umidade_min_abs`, `vento_rajada_max_ms` (extremos absolutos do mês).

Qualidade: `dias_com_registro`, `dias_validos_chuva`, `dias_validos_temp`,
`dias_no_mes`, `pct_dias_validos`.

Mês com menos de **70% de dias válidos** vira `NaN` em vez de virar média de meia
dúzia de dias — mesmo espírito do corte de 18 horas do diário, e aplicado
separadamente para chuva e para temperatura.

### Sanidade conferida

A sazonalidade dos extremos bate com a realidade física do país:

| UF | `dias_sem_chuva` em julho | `max_dias_secos_seguidos` em julho |
|---|---|---|
| MT (Cerrado) | 30 | **29** — seca total |
| CE (Sertão) | 28 | 20 |
| AM (Amazônia) | 23 | 12 — muitos dias secos, mas chuva dispersa |
| RS (Sul) | 23 | 11 — distribuído o ano todo |

E `dias_calor_extremo` dá em média 3,0 dias/mês, ou seja **10% dos dias**, que é
exatamente o que a definição por p90 tem de produzir.

## Para quem pegar o T-021

* Os **índices de extremo têm de ser calculados no nível diário**, antes de
  agregar para o mês. `dias_sem_chuva` e `dias_chuva_forte` são impossíveis de
  recuperar depois da agregação mensal. Esta tabela existe exatamente para isso.
* Guarde `n_estacoes` por UF×mês. A rede cresceu ~35% no período.
* `horas_validas` e `horas_validas_chuva` são o indicador de qualidade por dia —
  use para montar `pct_dias_validos`.
* A média entre estações de uma UF grande é enganosa (litoral e sertão do Piauí
  não descrevem nenhum dos dois). Mediana ajuda; ponderar pela produção é o T-022.

## Alternativa registrada, se o INMET virar um problema

O ticket sugere o [NASA POWER](https://power.larc.nasa.gov/) como plano B: série
**mensal** por lat/lon em grade, sem falha de estação e sem cadastro. **Não foi
necessário** — o INMET rodou inteiro e passou os critérios de aceite. Mas segue
valendo como fonte de imputação para buracos de cobertura no T-021, que é o uso
que o próprio ticket recomenda de qualquer forma.
