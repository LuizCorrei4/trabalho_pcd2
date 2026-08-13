# T-015 — Coletor do Monitor de Secas (ANA)

Ticket: [`tickets/01-coleta/T-015-monitor-secas.md`](../../../tickets/01-coleta/T-015-monitor-secas.md)

## Como rodar

A partir da **raiz do repositório**, com o ambiente `pcd2` ativo:

```bash
python -m src.coleta.monitor_secas.download        # 1. baixa 27 JSONs -> data/raw/ana/
python -m src.coleta.monitor_secas.agrega_uf_mes   # 2. gera data/interim/seca_uf_mes.parquet
python -m src.coleta.monitor_secas.validar         # 3. confere os critérios de aceite
```

O download é idempotente: rodar de novo reaproveita o que já está em `data/raw/`.
Use `--forcar` para rebaixar e `--ufs CE BA` para trabalhar com um subconjunto.

Roda inteiro em menos de um minuto.

## A fonte: uma API, não a página de downloads

O ticket aponta para <https://monitordesecas.ana.gov.br/dados-tabulares>, mas
aquela página é uma aplicação Angular que monta o CSV no navegador — não há
arquivo para baixar. Os dados vêm de uma **API REST aberta**, encontrada no
bundle JavaScript do site:

```
GET https://apimsbr.ana.gov.br/rpc/v1/dados-tabulares-monitor?tipo_area=1&area={geocod_uf}
```

* `tipo_area=1` é o nível Unidade da Federação; `area` é o geocódigo IBGE de 2
  dígitos (23 = CE, 35 = SP...). Confirmado no código do site, que filtra por
  `tipo_area == 1 && area == uf.geocod`.
* Uma requisição devolve a **série mensal completa** daquela UF. 27 requisições
  no total.
* Não exige autenticação. O bundle do site também expõe credenciais OAuth de um
  usuário administrativo; elas **não são usadas aqui** — os endpoints `rpc/v1`
  respondem sem token.

## A descoberta que muda o ticket: a ANA já agregou por área

O campo `area` **não é km²**, apesar do nome. É o percentual do território da UF
em **pontos-base**: `10000` = 100,00%. E as categorias são **cumulativas** —
`S2` significa "área em seca grave *ou pior*".

Evidência (550 meses, 8 UFs conferidas):

* o valor satura em exatamente `10000`, com uma nuvem de valores logo abaixo
  (9998, 9995, 9986...), que é a assinatura de um teto em 100,00%;
* `S0 >= S1 >= S2 >= S3 >= S4` em **todos** os registros, zero exceções, que só
  faz sentido sob leitura cumulativa;
* o Ceará em 2015-01 dá `S0=10000` (100% do estado em seca fraca ou pior) e em
  2017-01 dá `S4=6364` (63,64% em seca excepcional) — exatamente a grande seca do
  Nordeste, na intensidade que ela realmente teve.

**Consequência prática:** a tarefa do ticket de "agregar município → UF
ponderando pela área do município" **já vem feita pela ANA**. Não há municípios
para agregar, não é preciso `geopandas`, e a área territorial das UFs não entra
na conta. O ticket estimava 3h; a coleta em si é bem mais rápida que isso — o
trabalho real foi descobrir o formato e limpar a fonte.

## As três sujeiras da fonte

Nenhuma é documentada pela ANA, e todas produzem número errado em silêncio:

| Problema | Onde | Tratamento |
|---|---|---|
| **Revisões empilhadas.** A API devolve todas as versões de um mês na mesma lista, sem dizer qual vale. 66 dos 2.422 meses têm a categoria repetida 2 a 4 vezes. | generalizado | O `id` maior é o vigente. Divergências gravadas em `outputs/tabelas/monitor_secas_revisoes_divergentes.csv` |
| **Categorias em minúsculas** (`s0`..`s4`) convivendo com as maiúsculas | AL e CE em 2020-03 | Normaliza a caixa antes de agrupar |
| **Monotonia cumulativa violada** (`S3=0` com `S4=13`, impossível), sem revisão que corrija | MA em 2014-11 | Sinaliza na coluna `inconsistente`; não inventa valor. Fica fora da janela-alvo |

As duas primeiras esconderiam erros graves: a Bahia em 2015-04 tem uma revisão
antiga com a escala multiplicada por 100 (`984700` no lugar de `9847`), e em
2016-06 tem um `123456` de placeholder em S4. Pegar o máximo entre revisões — ou
o primeiro que aparecer — importa esses valores como se fossem reais.

## Saída

`data/interim/seca_uf_mes.parquet` — 27 UFs × 138 meses = **3.726 linhas**.

Schema pedido pelo ticket:

| Coluna | Descrição |
|---|---|
| `sigla_uf`, `ano_mes` | chave (`ano_mes` no formato `YYYY-MM`) |
| `pct_area_S0plus` | % da área da UF em seca fraca ou pior |
| `pct_area_S2plus` | % em seca grave ou pior |
| `pct_area_S3plus` | % em seca extrema ou pior |
| `severidade_media` | índice de 0 a 5 sobre a UF inteira |
| `meses_consecutivos_S2plus` | meses seguidos com seca grave ou pior |

Colunas extras, que saem do mesmo cálculo:

| Coluna | Descrição |
|---|---|
| `ano`, `mes` | conveniência para agrupar |
| `pct_area_S1plus`, `pct_area_S4plus` | as duas faixas cumulativas restantes |
| `severidade_media_area_seca` | severidade média *dentro* da área seca; `NaN` no mês sem seca |
| `monitorado` | `False` quando a UF ainda não era monitorada |
| `inconsistente` | `True` no mês que falha a monotonia cumulativa |

### Como `severidade_media` é calculada

As categorias vêm cumulativas, então primeiro é preciso desfazer o acúmulo para
obter as faixas exclusivas (`S1_só = S1 − S2`, e assim por diante). Depois aplica
os pesos do ticket (S0=1 … S4=5) e divide pela área **total** da UF, de modo que
a área sem seca entre com peso 0:

```
severidade_media = Σ(peso_i × faixa_exclusiva_i) / área_total_da_UF
```

Resultado de 0 (nenhuma seca) a 5 (todo o território em seca excepcional), e
comparável entre UFs e entre meses. `severidade_media_area_seca` usa o mesmo
numerador dividido pela área seca, respondendo "quando dá seca aqui, ela é
forte?" — mas é indefinida no mês sem seca alguma, por isso não é a principal.

## Cobertura: `NaN`, nunca zero

O Monitor nasceu no Nordeste em 2014 e foi expandindo. Na janela do projeto:

* **9 UFs do Nordeste** cobrem os 138 meses (desde 2015-01, e a fonte começa em 2014-07);
* **MG** entra em 2018-11, **ES** em 2019-04, o **Sul e SP** em 2020-08/11, e **RR** só em 2023-11;
* das 3.726 linhas, **2.368 têm dado** e **1.358 são pré-monitoramento**.

Essas 1.358 linhas são `NaN`. Preenchê-las com zero ensinaria ao modelo que "não
havia seca no Sul antes de 2020", o que é falso — ninguém estava medindo. A
tabela completa está em [`docs/cobertura_monitor_secas.md`](../../../docs/cobertura_monitor_secas.md),
gerada automaticamente.

Há também **1 buraco interno** (SE, um mês faltando dentro do intervalo já
monitorado), tratado do mesmo jeito.

### Cuidado ao usar no modelo (T-023/T-041)

A série é **desbalanceada entre regiões nos primeiros anos**: até 2018 só existe
Nordeste. Um modelo treinado sem cuidado vai confundir "seca" com "ser do
Nordeste". Duas saídas razoáveis: restringir o uso desta feature a 2020+, ou
manter a janela toda e deixar o modelo tratar `NaN` explicitamente — mas nunca
imputar zero.

`meses_consecutivos_S2plus` tem uma limitação análoga: a contagem zera num buraco
da série e começa do 1 quando a UF entra no monitoramento. A UF que já estava em
seca ao entrar tem a duração **subestimada** — é subestimativa honesta, preferível
a um número inventado.
