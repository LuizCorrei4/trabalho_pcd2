# Roteiro de apresentação — Da coleta bruta à tabela `fato_alimentos_combustiveis_uf_mes.parquet`

> Texto-fonte para gerar os slides. Cada bloco `## Slide N` é um slide; os bullets são o
> conteúdo visível e a seção **Notas** é a fala do apresentador. Todos os números foram medidos
> nos arquivos reais do repositório, não estimados.

---

## Slide 1 — Capa

**O que realmente move o preço da comida no Brasil?**
Clima, safra, macroeconomia e custo de frete na inflação alimentar regional

- SSC0957 — Prática em Ciência de Dados II
- Entrega: `data/processed/fato_alimentos_combustiveis_uf_mes.parquet`
- **2.088 linhas × 108 colunas · 16 UFs × 138 meses (2015-01 → 2026-06) · 6 fontes · 5 instituições**

**Notas:** a narrativa pública simplifica — "a culpa é da seca" ou "a culpa é do dólar". A realidade é
multifatorial e varia por região. Para responder isso é preciso colocar clima, oferta agrícola,
macroeconomia e custo logístico na *mesma linha da mesma tabela*. Esta apresentação é sobre como
essa linha foi construída.

---

## Slide 2 — A pergunta e o desenho da tabela

- **Alvo:** IPCA do grupo *Alimentação e bebidas*, variação mensal por área urbana
- **Explicativas:** clima local, seca, estimativa de safra, macro nacional, preço de combustível
- **Denominador comum:** só duas coisas são compartilhadas por todas as fontes — `sigla_uf` e o mês
- **Grão final:** `UF × mês`, formato largo, chave única `(sigla_uf, ano_mes)`

**Notas:** essa é a decisão estruturante do projeto. Cada fonte chega num grão diferente — estação
meteorológica, produto agrícola, item de IPCA, país inteiro — e nenhuma delas conversa com as outras
como vem. Tudo teve de ser reduzido a `UF × mês` antes de qualquer merge.

---

## Slide 3 — O pipeline em três camadas

```
data/raw/          →  data/interim/        →  data/processed/
dado como baixado     tabela por fonte,       tabela única,
NUNCA modificado      já em UF × mês          pronta para modelar
```

| Camada | Conteúdo | Versionado? |
|---|---|---|
| `raw/` | ZIPs do INMET (1,27 GB), JSONs da ANA, chunks do SIDRA, CSVs da ANP | Não (só a estrutura) |
| `interim/` | uma tabela por fonte, já padronizada | Parcial |
| `processed/` | `calendario_uf_mes` · `fato_alimentos_uf_mes` · **`fato_alimentos_combustiveis_uf_mes`** | Sim |

- Código modular em `src/coleta/<fonte>/` e `src/tratamento/`
- Todo caminho sai de `src/config.py` — nenhum caminho absoluto espalhado pelo código
- Cada coletor tem um `validar.py` que confere os critérios de aceite e sai com código 0 ou 1

**Notas:** a separação raw/interim/processed é o que torna o trabalho reprodutível. Um erro
descoberto no tratamento nunca exige rebaixar 1,27 GB — o bruto está intacto no disco. A única
exceção dolorosa aparece no slide do IPCA.

---

## Slide 4 — As seis fontes, em uma tela

| # | Fonte | Instituição | O que traz | Granularidade nativa | Período coletado |
|---|---|---|---|---|---|
| 1 | SIDRA / IPCA-SNIPC | IBGE | **o alvo** — inflação de alimentos | mês × área urbana × item | 2006-07 → 2026-07 |
| 2 | BDMEP | INMET | chuva, temperatura, extremos | estação × dia (→ mês) | 2014 → 2026 |
| 3 | Monitor de Secas | ANA | severidade e área em seca | UF × mês | 2014-07 → 2026-06 |
| 4 | SIDRA / LSPA + PAM | IBGE | estimativa de safra e sua revisão | UF × produto × mês | 2014-01 → 2026-07 |
| 5 | SGS | BCB | dólar, Selic, IPCA cheio, IGP-M | Brasil × mês | 2014-01 → 2026-07 |
| 6 | Levantamento de Preços | ANP | diesel, gasolina, etanol, GLP | UF × mês × produto | 2004-05 → 2026-07 |

- Requisito da disciplina: ≥ 3 fontes heterogêneas. **Entregamos 6 pesquisas, de 5 instituições.**
- Nenhuma fonte compartilha grão com outra, e o `ano_mes` chegou do disco em três tipos diferentes.

**Notas:** vale marcar que "IBGE" aparece duas vezes mas são *pesquisas diferentes* — o IPCA é
pesquisa de preço ao consumidor em área urbana; o LSPA é estimativa de safra por UF. Metodologia,
grão e periodicidade não têm nada em comum.

---

## Slide 5 — Fonte 1: IBGE/SIDRA — o IPCA de alimentos (o alvo)

**Como foi coletado**
- Biblioteca `sidrapy` contra a **API pública do SIDRA**, sem chave
- **Três tabelas encadeadas**, porque o IBGE troca a tabela a cada revisão da estrutura do índice:
  `2938` (2006-2011) · `1419` (2012-2019) · `7060` (2020-2026)
- Níveis territoriais **N6 (município)** e **N7 (região metropolitana)**; variáveis **63** (variação
  mensal) e **66** (peso mensal); classificação `315/all` (todos os itens e subitens)
- **168 requisições** em blocos trimestrais, com *checkpoint* em Parquet por bloco, retry até 5×
  e pausa de 0,5 s — rodar de novo reaproveita o que já baixou

**O que a base tem**
- `data/interim/ipca_alimentos_rm.parquet` — **83.383 linhas × 8 colunas**
- Grão: `ano_mes × sigla_uf × item` · **241 meses (2006-07 → 2026-07)**
- **16 áreas urbanas**: 10 regiões metropolitanas (SP, RJ, MG, PR, RS, BA, PE, CE, PA, ES) +
  6 municípios (DF, GO, MS, AC, MA, SE)
- Variáveis: `IPCA - Variação mensal` (%) e `IPCA - Peso mensal` (% do orçamento familiar)
- **40 códigos de item distintos, sob 42 nomes** — o IBGE renomeia item no meio da série

**Notas:** o campo `item` traz o código embutido no nome (`"1101002.Arroz"`). Chavear pelo **código**
e não pelo nome foi decisão consciente: `1111004` era "Leite pasteurizado" até 2011-12 e virou
"Leite longa vida"; agrupar por nome quebraria a série em duas.

---

## Slide 6 — O bloqueador: o sinal do IPCA estava invertido

```python
# ERRADO — apaga o menos de todo valor negativo
df['valor'].astype(str).str.replace('...', '').str.replace('-', '')
```

| | Antes (com o bug) | Depois da correção |
|---|---|---|
| linhas | 83.383 | 83.383 |
| **valores negativos** | **0** | **32.696** |
| mínimo | 0,00 | **−56,62 %** |
| média %/mês | **3,14 %** (≈45 % a.a.) | **0,75 %** |

- O `-` sozinho é o marcador do SIDRA para "não publicado" — a intenção era removê-lo
- Efeito colateral: **toda deflação virou inflação**, e o alvo do projeto estava corrompido
- `data/raw/` era byte-idêntico ao `interim/` → não havia bruto intacto → **re-coleta completa**
  das 168 requisições
- No grupo `1.Alimentação e bebidas` a média caiu para **0,59 %/mês**, a ordem de grandeza correta
- Virou um teste permanente no código: `assert (df.ipca_var_alimentacao < 0).sum() > 0`

**Notas:** este é o slide que mais impressiona porque o erro não levantava exceção nenhuma. Uma
série com zero valores negativos em 83 mil linhas é impossível para inflação mensal — e passou
despercebida até alguém olhar o mínimo da distribuição. É também a razão de a regra "nunca modifique
`data/raw/`" existir: sem bruto intacto, a correção custou uma re-coleta inteira.

---

## Slide 7 — Fonte 2: INMET — 1,27 GB de clima horário

**Como foi coletado**
- ZIPs anuais em URL previsível: `portal.inmet.gov.br/uploads/dadoshistoricos/{ANO}.zip`
- **13 anos (2014-2026), ~1,27 GB comprimidos, 7.344 arquivos de estação**
- Duas exigências descobertas na prática: **User-Agent de navegador é obrigatório** (sem ele o
  portal responde `Connection reset by peer`) e **`HEAD` é recusado** — para saber o tamanho remoto
  é preciso `GET` com `Range: bytes=0-0`
- Download **idempotente e atômico**: um arquivo interrompido nunca fica com o nome final
- O catálogo de estações sai do **cabeçalho de cada CSV dentro do ZIP**, não da página web — é a
  mesma fonte do dado e não depende de a página estar no ar

**A armadilha do formato: uma quebra limpa em 2019**

| | 2014-2018 | 2019-2026 |
|---|---|---|
| Caminho no ZIP | `2014/INMET_...CSV` | `INMET_...CSV` (raiz) |
| Rótulos | `REGIÃO:`, `ESTAÇÃO:` | `REGIAO:`, `ESTACAO:` |
| Data | `2014-01-01` | `2019/01/01` |
| **Código de ausência** | **`-9999`** | **campo vazio** |

- As colunas são casadas **por padrão de texto, não por posição** — e o mapeamento confere que cada
  destino casou exatamente uma vez, para uma mudança futura de layout virar erro alto e não coluna
  silenciosamente vazia
- `-9999` tratado na leitura (`na_values`) **e** numa varredura defensiva depois: um `-9999` que
  sobrevive até uma média vira temperatura de −3.000 °C sem levantar exceção nenhuma

**Notas:** o processamento é **um ano por vez, um CSV por vez**, lido do ZIP direto para memória.
Descomprimir tudo consome vários GB e derruba máquina de 8 GB; assim o pico fica em dezenas de MB.

---

## Slide 8 — INMET: hora → dia → mês, e por que nessa ordem

**Hora → dia** (2.547.899 linhas diárias)
- `chuva_mm` = **soma** das 24 horas com `min_count=1` — sem isso um dia inteiro de `NaN` soma 0, e
  "não mediu" fica indistinguível de "não choveu"
- Corte de 18 horas válidas **aplicado por grandeza, não em bloco** — é comum o pluviômetro parar e
  o termômetro continuar
- Faixas físicas viram `NaN` fora do limite (chuva em [0, 500) mm, temperatura em [−10, 50] °C)
- `vento_direcao_gr` foi **deliberadamente deixada de fora**: direção é grandeza circular e a média
  de 350° com 10° dá 180°, exatamente o lado oposto do correto

**Dia → mês** (`clima_estacao_mes.parquet` — **83.814 linhas, 701 estações, 151 meses, 4,7 MB**)
- **Não é um `resample('M')`**: os índices de extremo têm de sair do nível diário, senão são
  impossíveis de recuperar. 90 mm num mês podem ser 3 mm em 30 dias ou 90 mm num dia só — e para
  uma safra a diferença é tudo
- `dias_sem_chuva` · `dias_chuva_forte` · **`max_dias_secos_seguidos`** (o veranico, que é o que de
  fato mata lavoura) · `dias_calor_extremo`
- `dias_calor_extremo` usa limiar **por estação e por mês do calendário** (p90 da própria série):
  32 °C é banal em Teresina em novembro e excepcional em Curitiba em julho
- `max_dias_secos_seguidos` **não atravessa a virada do mês**, e um dia sem medição **quebra** a
  sequência — não se pode afirmar que não choveu num dia em que ninguém olhou

**Notas:** a sazonalidade dos extremos confere com a física do país — MT em julho dá 30 dias sem
chuva e 29 dias secos seguidos; RS dá 23 e 11, porque lá a chuva é distribuída o ano todo.

---

## Slide 9 — INMET: a cobertura que não passou no critério

- Critério do ticket: "≥ 90 % dos dias com ao menos 1 estação válida por UF" → **25 das 27 UFs**
  (média 98,0 %, mediana 100,0 %)
- **Roraima 69,8 %** — 3 estações no catálogo, 1 efetivamente ativa; em 2021 e 2026 ela não produziu
  nenhum dia válido. Não há tratamento de dados que resolva: a medição não existe
- **Um buraco nacional em 2021-2022** — o Rio Grande do Norte, com 100 % em todos os outros anos,
  cai para **38,1 % em 2021**. O preenchimento da chuva no país vai de **85,1 % (2019) para 47,1 %
  (2021)**
- A rede **cresce** ao longo da série: **475 estações em 2014 → 638 em 2026**

> ⚠️ 2021 é exatamente o ano da crise hídrica do Centro-Sul — **o período de maior interesse
> analítico é o de pior cobertura climática**. A incerteza tem de constar no relatório.

**Notas:** é por isso que `clima_n_estacoes` entrou na tabela final apesar de não ser uma medida de
clima. Um degrau de nível numa série climática que coincide com um salto na contagem de estações é
artefato da rede, não do clima.

---

## Slide 10 — Fonte 3: ANA — Monitor de Secas

**Como foi coletado**
- A página oficial (`monitordesecas.ana.gov.br/dados-tabulares`) é uma aplicação Angular que monta
  o CSV **no navegador** — não há arquivo para baixar
- A **API REST aberta** foi encontrada lendo o bundle JavaScript do site:
  `apimsbr.ana.gov.br/rpc/v1/dados-tabulares-monitor?tipo_area=1&area={geocod_uf}`
- `tipo_area=1` = nível UF; `area` = geocódigo IBGE (23 = CE, 35 = SP)
- **27 requisições**, uma por UF, cada uma devolvendo a série mensal completa. Sem autenticação.
  Roda inteiro em menos de um minuto

**A descoberta que encurtou o ticket**
- O campo `area` **não é km²**: é o % do território da UF em pontos-base (`10000` = 100,00 %)
- E as categorias são **cumulativas**: `S2` significa "seca grave **ou pior**"
- Consequência: **a ANA já agregou município → UF**. Não foi preciso `geopandas` nem área
  territorial dos municípios

**Notas:** a evidência do formato: o valor satura em exatamente 10000 com uma nuvem logo abaixo
(9998, 9995...), assinatura de teto em 100 %; e `S0 ≥ S1 ≥ S2 ≥ S3 ≥ S4` vale em **todos** os
registros, zero exceções, o que só faz sentido sob leitura cumulativa.

---

## Slide 11 — ANA: três sujeiras que produziriam número errado em silêncio

| Problema | Onde | Tratamento |
|---|---|---|
| **Revisões empilhadas** — a API devolve todas as versões do mês na mesma lista, sem dizer qual vale. 66 dos 2.422 meses vêm repetidos 2 a 4× | generalizado | o `id` maior é o vigente; divergências gravadas em `outputs/tabelas/` |
| **Categorias em minúscula** (`s0`..`s4`) convivendo com maiúsculas | AL e CE em 2020-03 | normaliza a caixa antes de agrupar |
| **Monotonia cumulativa violada** (`S3=0` com `S4=13`) | MA em 2014-11 | sinaliza em `inconsistente`; não inventa valor |

- A Bahia em 2015-04 tem uma revisão antiga com a escala **multiplicada por 100** (`984700` no lugar
  de `9847`), e em 2016-06 tem um **`123456` de placeholder**
- Pegar o máximo entre revisões — ou simplesmente o primeiro que aparece — importaria esses valores
  como se fossem reais

**Saída:** `seca_uf_mes.parquet` — **27 UFs × 138 meses = 3.726 linhas**
`pct_area_S0plus..S4plus` · `severidade_media` (0 a 5) · `severidade_media_area_seca` ·
`meses_consecutivos_S2plus` · `monitorado` · `inconsistente`

**Notas:** `severidade_media` primeiro desfaz o acúmulo para obter as faixas exclusivas, aplica os
pesos S0=1…S4=5 e divide pela área **total** da UF — assim a área sem seca entra com peso 0 e o
índice fica comparável entre UFs e entre meses.

---

## Slide 12 — ANA: o vazio mais perigoso da tabela

- O Monitor **nasceu no Nordeste em 2014** e foi se expandindo estado a estado
- Das 3.726 linhas, **2.368 têm dado e 1.358 são pré-monitoramento**

| Entrada no programa | UFs |
|---|---|
| 2015-01 | BA, CE, MA, PE, SE (e o restante do NE) |
| 2018-11 · 2019-04 | MG · ES |
| ao longo de 2020 | RJ, GO, DF, MS, RS, PR, SP |
| 2022-11 · 2023-04 · 2023-11 | AC · PA · RR |

| Recorte (16 UFs do alvo) | Linhas | % monitorado |
|---|---|---|
| 2015-01 → 2026-06 | 2.208 | **65,8 %** |
| 2020-01 → 2026-06 | 1.248 | **90,5 %** |
| 2024-01 → 2026-06 | 480 | 100,0 % |

> ⚠️ **`NaN` = "a UF não era monitorada", NÃO "não houve seca".** Preencher com 0 ensinaria ao
> modelo que não havia seca no Sul antes de 2020 — o que é falso: ninguém estava medindo.

- Risco adicional: até 2018 só existe Nordeste na série. Um modelo descuidado confunde **"seca" com
  "ser do Nordeste"**
- Recomendação registrada no dicionário: recortar em **2020-01** ou filtrar por `seca_monitorado`

---

## Slide 13 — Fonte 4: IBGE/LSPA — estimativa de safra e o sinal de choque de oferta

**Como foi coletado**
- API SIDRA (`apisidra.ibge.gov.br/values`), sem chave, nível `n3` (UF)
- **Tabela 6588 (LSPA)** — estimativa da safra do ano corrente, **revista mensalmente**
- **Tabelas 1612 e 1613 (PAM)** — produção anual realizada (lavouras temporárias e permanentes),
  usada para os pesos de produção
- **11 produtos canônicos**, somando as safras que a SIDRA separa: feijão (1ª/2ª/3ª), milho (1ª/2ª),
  café (arábica + canephora), batata-inglesa (3 safras) — com o rendimento **recalculado** como
  média ponderada real, não média de médias

**O que a base tem**
- `safra_uf_mes.parquet` — **44.847 linhas = 27 UF × 11 produtos × 151 meses**, grade perfeita
  (2014-01 → 2026-07)
- Produtos: arroz · feijão · milho · soja · trigo · café · banana · batata-inglesa · tomate ·
  mandioca · cana-de-açúcar
- Variáveis: `area_plantada_ha` · `area_colhida_ha` · `producao_t` · `rendimento_kg_ha` ·
  `revisao_pct_prod` · `ano_safra`
- QA: soma UF vs. Brasil bate em **100 % dos pares** (produto × mês) com diferença ≤ 1 %

> ⚠️ **Cada linha é a estimativa vigente da safra do ANO INTEIRO, não a produção daquele mês.**
> `producao_t` é estoque/previsão, não fluxo — somar 12 meses infla ~12×.

**Notas:** a coluna que realmente interessa é `revisao_pct_prod` — quanto a estimativa mudou contra
o mês anterior da mesma safra. É ela que se move quando a lavoura quebra; o nível de produção é
quase constante dentro do ano.

---

## Slide 14 — Fonte 5: BCB/SGS — o controle macroeconômico

**Como foi coletado**
- API pública do Banco Central, sem cadastro:
  `api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados`
- Cinco séries: **1** (dólar PTAX venda, diária) · **433** (IPCA variação mensal) · **432** (Selic
  meta, diária) · **11** (Selic efetiva, dias úteis) · **189** (IGP-M)
- **Paginação obrigatória em blocos de 10 anos**: acima disso a API devolve `200 OK` com payload
  **truncado, sem erro** — o coletor valida o intervalo devolvido contra o intervalo pedido

**O que a base tem**
- `macro_br_mes.parquet` — **151 linhas × 8 colunas**, 2014-01 → 2026-07, **zero nulos** em 1.208
  células
- `dolar_ptax_medio` · `dolar_ptax_fim` · `ipca_mm` · `ipca_indice_base` · `selic` ·
  `selic_efetiva_am` · `igpm`

**Conferido contra a fonte oficial**
- Dólar médio em 2020-03 (pico da pandemia): **4,8839** ✓
- Dólar no fim de 2022-12: **5,2177** ✓ · Selic meta em 2016-12: **13,75 %** ✓
- IPCA acumulado: 2015 **10,67 %** · 2016 **6,29 %** · 2021 **10,06 %** · 2022 **5,78 %** ✓ (IBGE)

**Notas:** sem controlar inflação e câmbio, o modelo atribui ao clima o que é só perda de poder de
compra da moeda. O `ipca_mm` tem dupla função: é controle **e** é o que gera o alvo relativo.

---

## Slide 15 — Fonte 6: ANP — o custo de frete que faltava

**Por que combustível entra numa tabela sobre inflação de alimentos**
- **O diesel é o custo de frete de toda a comida.** Nada sai da lavoura sem caminhão, e o Brasil move
  a maior parte da sua carga por rodovia
- **O GLP é item da própria cesta do IPCA** — é o preço de *cozinhar* o alimento
- Razão estrutural: as colunas `macro_*` são **idênticas em todas as UFs**; preço de combustível tem
  as duas dimensões, tempo **e** espaço

**Como foi coletado**
- Extração da base do **Levantamento de Preços de Combustíveis da ANP**, entregue como dois CSVs
  (`results-20260827-153515.csv` tem o padrão de nome de exportação de console de consulta SQL)
- ⚠️ **É a única fonte sem script de coleta versionado no repositório** — pendência de
  reprodutibilidade que vale declarar

**O que as bases têm**

| Arquivo | Grão | Linhas | Período |
|---|---|---|---|
| `combustivel.csv` | UF × mês × produto, 8 produtos, 27 UFs | **26.446** | 2004-05 → 2026-07 |
| `results-*.csv` (testemunha) | **coleta individual** (posto × dia), 551 municípios | **96.049** | 11 anos salteados |

Colunas: `ano_mes` · `sigla_uf` · `produto` · `unidade_medida` · `preco_compra_medio` ·
`preco_venda_medio` · `quantidade_registros`

---

## Slide 16 — ANP: o que foi descartado, e por quê

| Descarte | Motivo medido |
|---|---|
| `preco_compra_medio` | **47,9 % nula no total e 100 % nula de 2021 em diante** — a ANP parou de publicar o preço de aquisição. Não é uma coluna com nulos, são duas séries coladas |
| `Diesel S50` | só existe em **2012** — 73 linhas na série inteira |
| `Gasolina Aditivada` | começa em **2020-10** (48 % da grade) e tem **~0,99 de correlação** com a comum: não acrescenta sinal |
| `GNV` | 55 % da grade, ausente em 1 UF, e é combustível de frota urbana leve — não move frete agrícola nem cesta |

**Os 5 produtos que ficaram** (cobrem a janela inteira nas 16 UFs do alvo):
`Diesel` · `Diesel S10` · `Gasolina` · `Etanol` · `GLP (botijão 13 kg)`

> `Diesel` e `Diesel S10` são produtos **diferentes** e ambos ficam: o S10 é o de baixo enxofre,
> obrigatório em veículos novos; o comum ainda é vendido para frota antiga. A transição entre eles
> é gradual ao longo da série.

**Notas:** uma coluna que morre no meio da série vira degrau artificial em qualquer modelo que a
use — e o modelo vai aprender o degrau, não o fenômeno.

---

## Slide 17 — ANP: 182 duplicatas e a média que mente

- A fonte traz **364 linhas duplicadas em 182 grupos** de `(UF, mês, produto)` — quase todas em
  **2026-04**, que veio em duas levas de coleta; o resto são linhas soltas com um único posto
- `drop_duplicates()` escolheria uma leva ao acaso; média simples daria o mesmo peso a 1 posto e a
  5.681
- **Regra única que resolve os dois casos: média ponderada por `quantidade_registros`**

| UF | mês | produto | média simples | **ponderada** | erro | postos |
|---|---|---|---|---|---|---|
| PA | 2008-02 | GLP | R$ 17,98 | **R$ 32,91** | **−45,4 %** | [1, 674] |
| SP | 2017-02 | GLP | R$ 48,79 | R$ 52,57 | −7,2 % | [3297, 1] |
| RN | 2018-07 | Diesel | R$ 3,21 | R$ 3,41 | −5,9 % | [1, 134] |

**Notas:** o pior caso é brutal — um posto solto com R$ 3,00 pesa o mesmo que 674 postos com
R$ 32,95. E o viés é sempre no mesmo sentido: **o registro solto puxa o mês inteiro**. Onde as duas
levas são grandes (2026-04), as duas médias praticamente coincidem, que é como tem de ser.

---

## Slide 18 — As três armadilhas de junção (o coração técnico do projeto)

### 1. O merge que devolve tudo vazio **sem levantar erro**
```python
esquerda["ano_mes"].astype(str)   # "2015-01"
direita ["ano_mes"].astype(str)   # "2015-01-01"   ← a safra guarda o dia 1
```
- São duas strings, o pandas aceita, e o resultado é **0 de 3.726 valores não-nulos**
- Nenhuma exceção, nenhum aviso: uma tabela inteira de vazio disfarçada de junção

### 2. O merge que multiplica a espinha por 11
- `safra_uf_mes` tem **40.770 duplicatas** em `(sigla_uf, ano_mes)` — uma por produto
- Merge direto: **3.726 → 40.986 linhas**, com taxa de match de **79,6 %** — um número que
  *parece saudável*. Em combustíveis o fator é 5 (2.088 → 8.471)

### 3. `shift(1)` sobre uma tabela com buracos inventa variação mensal
```
gasolina em SP, as linhas que a fonte tem:
2018-01  4,04        2018-03  4,03
2018-02  4,05        2018-07  4,30  →  "+6,86 % no mês"   ← são QUATRO meses
```
- Não é erro de cálculo, é **erro de rótulo** — e vai calado para dentro de qualquer regressão

**Notas:** a terceira é a mais traiçoeira porque nenhum `checa_join` a detecta: o merge está certo,
o número é que é mentira.

---

## Slide 19 — O contrato de chaves que fecha as três portas

`src/tratamento/chaves.py`

| Função | O que garante |
|---|---|
| `padroniza_chaves(df)` | `sigla_uf` → str de 2 maiúsculas; `ano_mes` → **`Period[M]`**. Aceita str, `datetime64` e `Period` na entrada |
| `valida_chaves(df, nome)` | recusa sigla fora do padrão, `ano_mes` que não seja `Period[M]`, e chave duplicada |
| `checa_join(antes, depois, ...)` | loga linhas antes/depois e taxa de match; **levanta erro** se o nº de linhas mudou ou se o match foi 0 % |

- **`Period[M]` é o tipo certo porque é o único que não tem dia** — não existe um "2015-01-01" para
  divergir de um "2015-01"
- `checa_join()` roda **depois de cada merge**. Não é opcional
- Contra a armadilha nº 3: toda variação é calculada **sobre a grade completa de meses**, antes do
  merge — o mês ausente vira linha `NaN` e a variação nasce `NaN` junto, que é a verdade

**Notas:** as três funções foram escritas *depois* de as armadilhas terem sido demonstradas em
notebook, célula por célula. Elas existem para transformar um erro silencioso em erro alto.

---

## Slide 20 — Passo a passo: cada fonte reduzida a UF × mês

| Fonte | De | Para | Regra |
|---|---|---|---|
| **IPCA** | 83.383 linhas × 40 códigos de item | 34 colunas largas | pivô sobre os **17 códigos com cobertura máxima** (2.088 linhas cada) → `ipca_var_*` e `ipca_peso_*` |
| **Clima** | 83.814 estação-mês, 701 estações | 4.077 UF-mês | **mediana** entre estações (robusta a sensor defeituoso) + `n_estacoes` |
| **Safra** | 44.847 linhas × 11 produtos | 22 colunas | pivô de 11 produtos × 2 medidas (`producao_t`, `revisao_pct`) |
| **Seca** | já em UF × mês | 9 colunas | só padroniza a chave, descarta derivadas e prefixa |
| **Macro** | 151 linhas nacionais | 5 colunas | *broadcast* por `ano_mes` — idêntico em todas as UFs |
| **Combustível** | 26.446 linhas × 8 produtos | 19 colunas | consolida ponderado → pivô de 5 produtos → derivadas sobre a grade |

**Três decisões que não são óbvias**
- **Estação-mês com < 70 % de dias válidos vira `NaN` ANTES de agregar** — 22,8 % das 83.814 linhas.
  Um mês com 5 dias medidos não é uma medida do mês
- **A chuva agrega por mediana neste passo, não por soma.** "Chuva soma" vale para dia → mês; somar
  o acumulado mensal das ~100 estações do RS daria **~50.000 mm**, número sem sentido físico
- **`revisao_pct_prod` é winsorizada em ±50 %**: o máximo bruto passa de **15 milhões %** (divisão
  por base minúscula) enquanto 96,6 % dos valores cabem em ±20 %. O corte deixa **99,1 % dos valores
  intactos** e mexe só na cauda

---

## Slide 21 — Os 17 itens do IPCA e os três alvos

- Dos 40 códigos, **17 têm as 2.088 linhas da janela** (cobertura máxima); o 18º cai para 92 % e
  nunca mais sobe
- Eles misturam **três níveis da hierarquia do IBGE de propósito**:
  - **grupo**: `1` Alimentação e bebidas
  - **subgrupos**: farinhas, açúcares, hortaliças, carnes, carnes industrializadas, aves e ovos,
    leites e derivados
  - **subitens**: arroz, batata-inglesa, tomate, frango inteiro, frango em pedaços, leite longa vida,
    pão francês, óleo de soja, café moído

> ⚠️ `1110009` (Frango inteiro) está **dentro de** `1110` (Aves e ovos), que está **dentro de** `1`.
> **Somar as colunas `ipca_peso_*` dupla-conta.** São colunas para ler lado a lado — "o frango subiu
> mais que o grupo?" —, nunca para agregar.

| Alvo | Cálculo | Para que serve |
|---|---|---|
| `ipca_var_alimentacao` | variação % no mês do grupo `1` | **alvo principal** |
| `ipca_var_alimentacao_acum12` | produto de `(1+r)` em 12 meses, por UF | remove a sazonalidade mensal |
| `ipca_var_alimentacao_relativa` | `ipca_var_alimentacao − macro_ipca_mm` | o quanto a comida subiu **além** da inflação geral |

- O acumulado é **composto, não somado** — 12 altas de 1 % dão 12,7 %, não 12 %
- E é calculado sobre a **série inteira desde 2006**, antes do recorte: senão os 12 primeiros meses
  da janela ficariam vazios por falta de passado

---

## Slide 22 — A junção (T-024): espinha de calendário, cinco LEFT JOINs

```
calendario_uf_mes  (27 UF × 138 meses = 3.726)          ← a espinha
  └─ LEFT JOIN ipca   on (sigla_uf, ano_mes)   match  56,0 %   (94,6 % nas 16 UFs)
  └─ LEFT JOIN clima  on (sigla_uf, ano_mes)   match  96,9 %
  └─ LEFT JOIN safra  on (sigla_uf, ano_mes)   match 100,0 %
  └─ LEFT JOIN seca   on (sigla_uf, ano_mes)   match  63,6 %
  └─ LEFT JOIN macro  on (ano_mes)             match 100,0 %   ← broadcast nacional
  → checa_join() após CADA merge
  → filtro final pelo alvo: 3.726 → 2.088 linhas
```

- **A espinha é o calendário completo, não o IPCA**, e todo merge é `LEFT`, nunca `INNER`. As 11 UFs
  sem alvo e os meses sem alvo caem num **único filtro no fim**, onde a perda é contada, em vez de
  sumirem aos poucos dentro dos merges
- **As 3.726 linhas se mantêm nos cinco merges** — é isso que prova que nenhum fan-out aconteceu
- **Prefixo antes do merge, nunca `suffixes`** — `_x`/`_y` deixam a tabela ilegível, e `ano`/`mes`
  existem em seca e clima: são descartadas, não desambiguadas

**A conta do filtro final fecha exatamente:**
16 UF × 138 meses = 2.208, menos AC, MA e SE (que só entram na amostra do IPCA em **2018-05**)
× 40 meses = 120 → **2.088**

---

## Slide 23 — A segunda junção (T-025): combustíveis entram sem mexer em nada

- Aqui a espinha **não é o calendário**: é a tabela fato do T-024, já filtrada nas 16 UFs com alvo
- A direção mudou — o T-024 montou a espinha e pendurou fontes nela; o T-025 pendura **uma** fonte
  numa espinha que já existe. Nenhuma linha pode entrar, sair ou mudar de valor

```
[3] LEFT JOIN  validate="m:1"
  [join] combustiveis  on sigla_uf+ano_mes   2.088 → 2.088 linhas | match 77,1 %
  89 colunas → 108 colunas (19 novas)
  as 89 colunas do T-024 saíram intactas: True
```

**A taxa de 77,1 % se decompõe inteira:** dos 138 meses da janela, **105 têm coleta de líquido** →
105 × 16 UFs = 1.680 linhas possíveis, das quais **1.610 vêm preenchidas = 95,8 % do que era
possível casar**. O resto é lacuna temporal da fonte, não uma UF descoberta.

**As 19 colunas novas**

| Bloco | Colunas |
|---|---|
| nível | `comb_preco_{diesel, diesel_s10, gasolina, etanol, glp_13kg}` |
| variação mensal / anual | `comb_var_mm_*` · `comb_var12_*` |
| **espacial** | `comb_diesel_vs_br_pct` — desvio % contra a mediana nacional do mês |
| medição | `comb_n_registros` · `comb_observado` · `comb_observado_liquidos` |

> **São dois flags de observação, não um**, porque a ANP roda **duas pesquisas** com falhas
> diferentes: os líquidos perdem 33 meses da janela e o GLP perde 15 — só 10 meses não têm nada.
> Um flag único chamaria de "observado" um mês em que o diesel não existe.

---

## Slide 24 — A testemunha: 96.049 coletas individuais validam o agregado

- `results-*.csv` é **outra extração da mesma base**, num grão totalmente diferente: uma linha por
  coleta, com posto, município e data
- A cobertura é esburacada, então **não serve de fonte — serve de testemunha**
- Teste: se a média simples das coletas de um UF-mês bate com o `preco_venda_medio` agregado, a
  agregação é o que diz ser. Só UF-meses com **≥ 20 coletas**

| produto | pares | correlação | erro absoluto mediano |
|---|---|---|---|
| glp_13kg | 512 | ~1,00 | 0,72 % |
| gasolina | 241 | ~1,00 | 0,52 % |
| diesel_s10 | 157 | ~1,00 | 0,55 % |
| etanol | 134 | ~1,00 | 0,68 % |
| diesel | 105 | ~1,00 | 0,53 % |

**Geral: 1.149 UF-meses · correlação > 0,993 em todos os produtos · erro absoluto mediano 0,61 % ·
viés médio −0,07 %**

**Notas:** duas extrações independentes, grãos diferentes, mesmo número. É um tipo de checagem que
raramente é possível — na maioria das fontes não existe uma segunda medição para confrontar.

---

## Slide 25 — A tabela final

### `data/processed/fato_alimentos_combustiveis_uf_mes.parquet`

- **2.088 linhas × 108 colunas** · 1,8 MB em memória
- Chave única `(sigla_uf, ano_mes)` · **16 UFs × 138 meses** · 2015-01 → 2026-06
- `ano_mes` é `Period[M]` em toda a tabela · zero duplicatas

| Família | Colunas | Fonte |
|---|---|---|
| `ipca_*` | **36** | IBGE/SIDRA |
| `safra_*` | **22** | IBGE/LSPA |
| `comb_*` | **19** | ANP |
| `clima_*` | **11** | INMET |
| `seca_*` | **9** | ANA |
| chave/descritiva | 6 | IBGE (`dim_uf`) |
| `macro_*` | 5 | BCB/SGS |

- **UFs:** AC, BA, CE, DF, ES, GO, MA, MG, MS, PA, PE, PR, RJ, RS, SE, SP
- **Dicionário de variáveis cobrindo 100 % das colunas**:
  `outputs/tabelas/dicionario_variaveis_combustiveis.csv` — nome, descrição, unidade, fonte,
  granularidade nativa, % de nulos e **o que o vazio significa**

**Notas:** o requisito da disciplina era "várias dezenas de variáveis após a agregação das bases".
108 colunas, de 6 pesquisas de 5 instituições, todas documentadas linha a linha.

---

## Slide 26 — O perfil de nulos: cada vazio tem um significado diferente

| Família | % de nulos | O `NaN` significa | Preencher com 0? |
|---|---|---|---|
| `seca_*` | 34-38 % | a UF **não era monitorada** pela ANA naquele mês | **Não** — inventaria ausência de seca onde não houve medição |
| `comb_preco_*` (líquidos) | ~23 % | **mês sem pesquisa** — 33 dos 138 meses | **Não** — criaria postos vendendo diesel de graça |
| `comb_var12_*` | ~39 % | precisa do mês **e** do mesmo mês do ano anterior: perde os dois buracos | **Não** |
| `safra_revisao_pct_*` | 9-53 % | revisão **indefinida**: é janeiro, ou a UF não planta o produto | **Não** — 0 significaria "a estimativa não mudou" |
| `safra_producao_t_*` | 0 % | — | **Já foi**: ausência estrutural virou 0 tonelada, que é literalmente verdade |
| `clima_*` | 0,3 % | nenhuma estação da UF passou do corte de 70 % de dias válidos | Não |
| `ipca_*_acum12` | 1,6 % | os 12 primeiros meses de AC, MA e SE na amostra | Não — é borda de janela |

- Regra do projeto: **nenhum `NaN` vira 0 por acidente**, e toda coluna com nulo ganha justificativa
  escrita no dicionário — não só as acima de 40 %
- A escada dos combustíveis é aritmética, não acidental: preço ~23 % → variação mensal ~30 %
  (precisa de dois meses seguidos) → variação anual ~39 % (precisa de dois buracos)

**Notas:** a leitura errada de um `NaN` de seca com 34 % de incidência faz tanto estrago quanto a de
um com 52 %. Por isso a justificativa vai em todas.

---

## Slide 27 — Validação: estrutural primeiro, histórica depois

**Estruturais (assertivas no código — falham a execução)**
- ✅ chave `(sigla_uf, ano_mes)` única · 2.088 linhas · 16 UFs · 138 meses
- ✅ `ano_mes` é `Period[M]`, não string, em toda tabela
- ✅ o alvo tem deflação — prova de que o bug do sinal não voltou
- ✅ ≥ 3 instituições de origem (temos 5) · dicionário cobre 100 % das colunas
- ✅ nenhuma coluna > 40 % nula sem justificativa escrita
- ✅ preço de líquido entre 1 e 15 R$/l · GLP entre 20 e 200 R$/botijão
- ✅ `comb_observado_liquidos == False` implica preço de líquido nulo

**Históricas — a tabela reconhece o que sabemos que aconteceu**
- **Seca do Ceará em 2017-01**: `S2plus = 100 %`, `S4plus = 63,64 %`, severidade **4,52**
- **Pico da inflação de alimentos**: 2020-11 com **18,1 % em 12 meses** (câmbio + pandemia); e a
  alta de 2016 (seca do NE + recessão)
- **Sazonalidade climática**: chuva mediana no Norte/CO — janeiro **226 mm** vs. agosto **13 mm**
- **Choque do diesel**: pico de **+62,1 % em 12 meses em 2022-07** (petróleo pós-invasão da Ucrânia)
  e vale de **−33,8 % em 2023-07** (corte de tributos federais + base de comparação alta)

**Notas:** é isso que separa uma junção que **roda** de uma junção **correta**. Ninguém disse à
tabela que esses eventos existiram — ela os reconhece sozinha.

---

## Slide 28 — O achado que justifica a última fonte existir

**A defasagem: o diesel de hoje explica a comida de quando?**

- Correlação entre `comb_var12_diesel` defasado e `ipca_var_alimentacao_acum12`:
  **0,422 sem defasagem → 0,487 com o diesel adiantado 4 meses**, caindo monotonicamente depois
- É a forma de um **repasse de custo**, não de uma coincidência — e 4 a 5 meses é a ordem de
  grandeza que a literatura de repasse de frete ao varejo alimentar registra

**A dimensão que `macro_*` não tem: espaço**

`comb_diesel_vs_br_pct` — desvio médio contra a mediana nacional, por UF:

| **AC +20,3 %** | PA +7,1 % | CE +3,2 % | MS +2,2 % | … | ES −2,5 % | SP −2,7 % | **PR −4,7 %** |
|---|---|---|---|---|---|---|---|

- O Acre paga **20 % a mais** pelo diesel que a mediana do país, **todo mês da série**. É distância
  de refinaria e custo de escoamento
- `macro_dolar_ptax_medio` é idêntica nas 16 UFs e **não consegue explicar isso**

**Notas:** esse é o gráfico de fechamento. Ele mostra que a integração não só funcionou tecnicamente
— ela produziu um sinal que nenhuma das fontes isoladas continha.

---

## Slide 29 — O que dá e o que não dá para fazer com a tabela

| ✅ Dá para | ❌ Não dá para |
|---|---|
| Usar `comb_var12_diesel` defasado 4-5 meses como preditor do alvo | Ler `NaN` em `comb_*` como preço zero — é **mês sem pesquisa** |
| Comparar a inflação de um item com a do grupo na mesma UF | Somar `ipca_peso_*` entre colunas (dupla-contagem entre níveis) |
| Explicar diferença **entre capitais** com `comb_diesel_vs_br_pct` | Explicar diferença entre capitais com `macro_*` — são idênticas em todas |
| Ler `safra_revisao_pct_*` como choque de oferta | Somar `safra_producao_t_*` ao longo dos meses (é estoque, não fluxo) |
| Regredir o alvo contra clima e safra na série toda | Usar `seca_*` sem filtrar `seca_monitorado` ou recortar em 2020-01 |
| Comparar clima entre meses da mesma UF | Comparar nível de clima entre UFs sem olhar `clima_n_estacoes` |
| Filtrar por `comb_observado_liquidos` e usar a série limpa | Interpolar os 33 meses sem coleta **e não dizer que interpolou** |

**Notas:** essa tabela é, na prática, o resumo executivo do dicionário de variáveis. Ela existe
porque todo `NaN` desta base carrega uma afirmação sobre o mundo, e a afirmação errada muda a
conclusão de qualquer regressão.

---

## Slide 30 — O que fica para os próximos passos

| Etapa | O que falta | O gancho que já existe |
|---|---|---|
| **T-022** — clima ponderado pela produção | agregar estação → UF pesando pela produção agrícola, não por mediana simples | `producao_uf_ano.parquet` já traz `peso_producao_uf`; `catalogo_estacoes.csv` tem lat/lon das 701 estações |
| **T-023** — features de lag | chuva e seca defasadas 1-6 meses, médias móveis | `calendario_uf_mes.parquet` é a grade completa: calcular os lags **nele**, antes do filtro do alvo, para não quebrar a borda de AC/MA/SE |
| **T-031 / T-041 / T-042** — análise e modelagem | cross-correlation, Random Forest / XGBoost, SHAP | alvo e regressores já estão na mesma linha; `ipca_var_alimentacao_relativa` isola o efeito específico de alimentos |
| Pendências de coleta | fechar a lacuna de 33 meses da ANP; versionar o script de coleta de combustíveis | a falha é simultânea nas 27 UFs → é da **extração**, não da coleta da ANP |

**A lição transversal do projeto**
> Dos seis merges desta tabela, **três falhariam em silêncio** se escritos do jeito óbvio: um devolve
> tudo vazio, um multiplica as linhas por 11, e um inventa uma variação mensal de quatro meses.
> Nenhum levanta exceção. O trabalho não foi juntar os dados — foi **construir as verificações que
> transformam erro silencioso em erro alto**.

---

## Apêndice — Comandos para reproduzir o pipeline

```bash
# Coleta (sempre a partir da raiz do repositório)
python -m src.coleta.sidra_ipca.01_ibge_ipca_download   # IPCA — 168 requisições ao SIDRA
python -m src.coleta.inmet.download                      # 13 ZIPs, ~1,27 GB
python -m src.coleta.inmet.catalogo                      # 701 estações
python -m src.coleta.inmet.agrega_dia                    # hora → dia
python -m src.coleta.inmet.agrega_mes                    # dia → mês
python -m src.coleta.monitor_secas.download              # 27 JSONs da API da ANA
python -m src.coleta.monitor_secas.agrega_uf_mes
python  src/coleta/T-012_T-013/03_sidra_lspa.py          # safra (LSPA + PAM)
python  src/coleta/T-012_T-013/04_bcb_sgs.py             # macro

# Tratamento e junção
python src/tratamento/21_clima_uf_mes.py                 # 701 estações → UF × mês
python src/tratamento/24_junta.py                        # 5 fontes → fato (89 colunas)
python src/tratamento/25_combustiveis.py                 # + ANP → fato final (108 colunas)
```

**Notebooks que mostram o raciocínio:** `06_juncao_uf_mes.ipynb` (as duas armadilhas do merge,
célula a célula) e `07_juncao_combustiveis.ipynb` (a terceira armadilha e a validação por
testemunha). O desenho da junção está em `docs/analise_juncao_uf_mes.md`.
