# Análise: como juntar as 4 bases de `data/interim/` numa tabela UF × mês

> Documento de desenho da junção. Cobre os tickets [T-020](../../tickets/02-tratamento/T-020-padronizacao.md),
> [T-021](../../tickets/02-tratamento/T-021-clima-uf-mes.md) e [T-024](../../tickets/02-tratamento/T-024-juncao-final.md).
> Todos os números aqui foram medidos nos arquivos reais, não estimados.

## Contexto

O trabalho precisa cruzar 3+ fontes heterogêneas por uma variável comum. Hoje existem quatro
tabelas em `data/interim/`, cada uma num **grão diferente**, com **tipo de data diferente** e
**unidade geográfica diferente**. Nenhum notebook consegue analisá-las juntas.

| Tabela | Grão real | Linhas | Unidade espacial | tipo de `ano_mes` | Cobertura |
|---|---|---|---|---|---|
| `ipca_alimentos_rm.parquet` | `ano_mes × sigla_uf × item` | 83.383 | 16 áreas urbanas IBGE | `str "YYYY-MM"` | 2006-07 → 2026-07 |
| `safra_uf_mes.parquet` | `sigla_uf × produto × ano_mes` | 44.847 | 27 UF | **`datetime64[us]`** | 2014-01 → 2026-07 |
| `seca_uf_mes.parquet` | `sigla_uf × ano_mes` | 3.726 | 27 UF | `str "YYYY-MM"` | 2015-01 → 2026-06 |
| `clima_estacao_mes.parquet` | `codigo_estacao × ano_mes` | 83.814 | **701 estações INMET** | `str "YYYY-MM"` | 2014-01 → 2026-07 |

**Só duas coisas são compartilhadas: `sigla_uf` e o mês.** Todo o resto precisa ser reduzido a esse
denominador comum.

Nota: o T-024 foi escrito para o DIEESE (T-011, abandonado — não existe `data/raw/dieese/`). O alvo
agora é o IPCA de alimentos, então alguns números do ticket original ficam obsoletos.

**Resultado pretendido:** `data/processed/fato_alimentos_uf_mes.parquet`, chave única
`(sigla_uf, ano_mes)`, **2.088 linhas**, com alvo de inflação alimentar + clima + seca + safra +
macro. Depois disso nenhum notebook lê `interim/`.

---

## Decisões tomadas

| Decisão | Escolha | Motivo |
|---|---|---|
| Grão final | **UF × mês (largo)** | É o que T-024 especifica e o que os modelos de T-041 esperam |
| Recorte temporal | **2015-01 → 2026-06** (138 meses) | Interseção das 4 bases; bate com `PERIODO_INICIO/FIM` de [`src/config.py`](../../src/config.py) |
| Recorte espacial | **16 UFs** (as do IPCA) | O alvo só existe para elas; são subconjunto estrito das 27 das outras três |
| Clima estação → UF | **Mediana entre estações** (T-021) | Robusta a estação com defeito; cobertura 100 % das linhas |
| Bug do sinal do IPCA | **Corrigir e re-coletar antes de juntar** | Sem isso o alvo está corrompido |

---

## Passo 0 — BLOQUEADOR: corrigir o sinal do IPCA

Verificado no arquivo atual: `IPCA - Variação mensal` tem **mínimo 0,0, zero valores negativos e
média 3,14 %/mês** (≈45 %/ano composto). Toda deflação virou inflação.

A causa está em [`src/coleta/sidra_ipca/01_ibge_ipca_download.py`](../../src/coleta/sidra_ipca/01_ibge_ipca_download.py),
linhas 159-162: o `.str.replace('-', '')` foi escrito para remover o marcador `-` ("não publicado")
do SIDRA, mas apaga **o sinal de menos de todo valor negativo**.

```python
# hoje — apaga o menos de qualquer número negativo
df_clean['valor'] = pd.to_numeric(
    df_clean['valor'].astype(str).str.replace('...', '', regex=False)
                                 .str.replace('-', '', regex=False),
    errors='coerce')

# corrigido — só anula os marcadores do SIDRA, preserva o sinal
MARCADORES = {'-': None, '...': None, '..': None, 'X': None, '': None}
df_clean['valor'] = pd.to_numeric(
    df_clean['valor'].astype(str).str.strip().replace(MARCADORES),
    errors='coerce')
```

`data/raw/sidra_ipca/ipca_alimentos_rm.parquet` é **byte-idêntico** ao de `interim/` — não há bruto
intacto guardado, então a correção exige re-executar o coletor contra a API do SIDRA:

```bash
python -m src.coleta.sidra_ipca.01_ibge_ipca_download
```

**Critério de aceite:** após o re-coleta, `(df['IPCA - Variação mensal'] < 0).sum() > 0` e a média
cai para a ordem de 0,4–0,6 %/mês.

> Consequência lateral: o relatório `data/raw/sidra_ipca/RELATORIO_METADADOS_E_ANALISE_SEMANTICA.md`
> e o notebook `02_exploration_data-raw_sidra_ipca.ipynb` narram mínimos negativos ("Tomate −48,5 %")
> que **não existem no arquivo** — a prosa foi escrita a partir de outra versão do dado. Devem ser
> re-executados depois da correção.

---

## Passo 1 — Contrato de chaves (T-020)

Já existe [`src/tratamento/T-012_T-013/chaves.py`](../../src/tratamento/T-012_T-013/chaves.py) com
`normaliza_nome()`, `mapear_para_uf()` e `carrega_dim_uf()` — **reusar, não recriar**. Note que o
docstring do próprio módulo importa de `src.tratamento.chaves` (sem a subpasta): mover o arquivo
para `src/tratamento/chaves.py` resolve a inconsistência e é o caminho que o T-020 pede.

Acrescentar as três funções do contrato:

```python
def padroniza_chaves(df: pd.DataFrame) -> pd.DataFrame:
    """sigla_uf -> str 2 maiúsculas; ano_mes -> pd.Period[M].

    Aceita as três formas que chegam de interim/: str "YYYY-MM" (ipca, seca,
    clima), datetime64 (safra) e Period. Sem isto o merge entre str e Timestamp
    não dá erro — devolve tudo NaN em silêncio.
    """

def valida_chaves(df: pd.DataFrame, nome: str) -> None:
    """Levanta erro se sigla_uf/ano_mes violarem o contrato ou a chave duplicar."""

def checa_join(antes: pd.DataFrame, depois: pd.DataFrame, nome: str, chave: list[str]) -> None:
    """Loga linhas antes/depois e taxa de match; alerta se o nº de linhas mudou."""
```

Rodar `checa_join()` **após cada merge** — não é opcional. O merge silencioso entre tipos
incompatíveis é a armadilha central deste ticket, e `safra_uf_mes` é justamente a tabela com o
`ano_mes` divergente.

---

## Passo 2 — Calendário-espinha

`data/processed/calendario_uf_mes.parquet` = produto cartesiano
`dim_uf × period_range(2015-01, 2026-06)` = **27 × 138 = 3.726 linhas** (entregável do T-020, usa
[`data/processed/dim_uf.csv`](../../data/processed/dim_uf.csv)).

A junção parte dele com **LEFT JOIN sempre, nunca INNER**. As 11 UFs sem IPCA e os meses sem alvo
caem só no filtro final — assim a perda é contabilizada, não silenciosa.

---

## Passo 3 — Normalizar cada fonte para UF × mês

### 3a. IPCA → alvo

O `item` mistura níveis hierárquicos e traz o código embutido (`"1101002.Arroz"`). Separar em
`cod_item` + `nome_item`.

Há duas colisões código↔nome, ambas **renomeações do IBGE em datas disjuntas** e ambas irrelevantes
para a janela: `1111004` (Leite pasteurizado até 2011-12 → Leite longa vida) é inteiramente
pré-janela, e `1101053` (Feijão macassar → macáçar em 2020-01) só aparece em 5 UFs e não entra na
seleção. **Chavear por `cod_item` é seguro dentro da janela.**

Selecionar os **17 códigos com cobertura máxima** (2.088 linhas = 16 UF × 138 meses menos os 120
meses em que AC/MA/SE ainda não existiam):

```
1        Alimentação e bebidas          <- ALVO PRINCIPAL
1101002  Arroz              1102  Farinhas, féculas e massas
1103003  Batata-inglesa     1104  Açúcares e derivados
1103028  Tomate             1105  Hortaliças e verduras
1110009  Frango inteiro     1107  Carnes
1110010  Frango em pedaços  1109  Carnes e peixes industrializados
1111004  Leite longa vida   1110  Aves e ovos
1112015  Pão francês        1111  Leites e derivados
1113013  Óleo de soja
1114022  Café moído
```

Pivotar para largo: `ipca_var_<slug>` e `ipca_peso_<slug>`.

> ⚠️ Documentar no dicionário: os 17 misturam **grupo** (`1`), **subgrupos** (`1102`, `1104`,
> `1105`, `1107`, `1109`, `1110`, `1111`) e **subitens** (7 dígitos). Somar `ipca_peso_*` entre
> colunas dupla-conta. São colunas para usar lado a lado, nunca agregadas.

Alvos derivados (equivalentes às três versões que o T-024 pede):

- `ipca_var_alimentacao` — variação % m/m do grupo 1 → **alvo principal**
- `ipca_var_alimentacao_acum12` — acumulado 12 meses, composto, por UF
- `ipca_var_alimentacao_relativa` = `ipca_var_alimentacao − macro.ipca_mm` → o quanto a comida
  subiu **além** da inflação geral. É a versão "real" que faz sentido aqui: a variação já é um %,
  não um nível em R$, então dividir pelo deflator não se aplica como se aplicava no DIEESE.

### 3b. Clima: 701 estações → UF × mês (T-021)

Saída: `data/interim/clima_uf_mes.parquet`, 27 × 151 = 4.077 linhas.

1. Mascarar como `NaN` as medidas onde `pct_dias_validos < 70` (não inventar dado).
2. Agregar estação → UF por **mediana**, com `n_estacoes = nunique(codigo_estacao)`.
3. Colunas a levar: `chuva_mm_mes`, `temp_media`, `temp_max_media`, `temp_min_media`,
   `umidade_media`, `amplitude_termica_media`, e os quatro índices de extremo já calculados no
   diário — `dias_sem_chuva`, `dias_chuva_forte`, `dias_calor_extremo`, `max_dias_secos_seguidos`.
4. Prefixar tudo com `clima_`.

> ⚠️ **Chuva agrega por mediana aqui, não por soma.** A regra "chuva soma" do T-021 vale para
> dia→mês (já feito em `agrega_mes.py`). Somar o acumulado mensal de 100 estações do RS daria
> ~50.000 mm — número sem sentido físico.

Ressalvas para o dicionário (verificadas):

- Cobertura na espinha: **100 %** das linhas têm ≥1 estação; `chuva` não-nula em 99,6 %.
- Desbalanceamento severo: `n_estacoes` vai de **3 (RR) a 98**, mediana 25. A mediana entre uma
  estação do litoral e outra do sertão não descreve nenhum dos dois lugares.
- A rede **cresce** ao longo da série (475 estações em 2014 → 638 em 2026). Um degrau de nível
  coincidente com salto de `n_estacoes` é artefato, não clima. Por isso `n_estacoes` fica na tabela.
- `data/raw/catalogo_estacoes.csv` (701 linhas, casamento perfeito por `codigo_estacao`) tem
  `lat`/`lon`/`altitude` e não é necessário para a mediana — mas é o insumo se depois se quiser o
  clima ponderado do T-022. Atenção ao outlier `lat = -84.0`, que não fica no Brasil.

### 3c. Safra: longo → largo

**Esta é a armadilha que mais dói.** `safra_uf_mes` tem 40.770 duplicatas em `(sigla_uf, ano_mes)`
— porque o grão é `sigla_uf × produto × ano_mes` (27 × 11 × 151 = 44.847, grade perfeita). Juntar
sem pivotar multiplica a espinha por 11.

Pivotar 11 produtos × **2 medidas**:

- `safra_producao_t_<produto>` — nível
- `safra_revisao_pct_<produto>` — a revisão % da estimativa vs. mês anterior dentro da mesma safra;
  **é o sinal de choque de oferta**, a coluna que realmente interessa

→ 22 colunas. As outras três medidas (`area_plantada_ha`, `area_colhida_ha`, `rendimento_kg_ha`)
ficam disponíveis em `interim/` e podem ser acrescentadas depois se a análise pedir; 55 colunas de
saída seriam ruído.

> ⚠️ **Cada linha é a estimativa vigente da safra do ANO INTEIRO, não a produção daquele mês.**
> `safra_producao_t_soja` é um estoque/previsão, não um fluxo. Somar 12 meses infla ~12×.
>
> ⚠️ `revisao_pct_prod` é `NaN` em **todo janeiro** por construção (não há mês anterior dentro da
> mesma safra) e tem cauda explosiva (máx > 15 milhões %, de divisão por base minúscula). 91,8 %
> dos valores não-nulos cabem em ±20 %. **Winsorizar em ±50 % ou usar log-diferença.**
>
> ⚠️ `NaN` = "a UF não planta esse produto", não "dado faltante". Nulos medidos na espinha de 16 UF:
> mandioca/milho/feijão 0 %, cana 0,8 %, banana 3,5 %, arroz 7 %, tomate 10,5 %, café 18,8 %,
> soja 27,1 %, batata-inglesa 47,7 %, trigo 51 %. **Preencher com 0 é defensável para
> `producao_t` (ausência estrutural) e errado para `revisao_pct` (indefinida).** Registrar a
> decisão no dicionário — não deixar acontecer por acidente.

### 3d. Seca — já está em UF × mês

Só padronizar `ano_mes` para `Period[M]` e prefixar com `seca_`. Levar `severidade_media`,
`pct_area_S0plus`, `pct_area_S1plus`, `pct_area_S2plus`, `pct_area_S3plus`, `pct_area_S4plus`,
`meses_consecutivos_S2plus`, `severidade_media_area_seca` e o flag `monitorado`.

Descartar `ano` e `mes` (derivados, e colidem com as mesmas colunas do clima).

> ⚠️ **O maior buraco da tabela final.** `monitorado == False` (36 % das linhas) significa "a UF
> não estava no programa da ANA naquele mês" — `NaN` **não** é "não houve seca". Preencher com 0
> inventaria ausência de seca onde não houve medição.

Cobertura medida na espinha de 16 UF, por recorte:

| Janela | Linhas | % monitorado |
|---|---|---|
| 2015-01 → 2026-06 | 2.208 | **65,8 %** |
| 2018-01 → 2026-06 | 1.632 | 77,9 % |
| **2020-01 → 2026-06** | 1.248 | **90,5 %** |
| 2021-01 → 2026-06 | 1.056 | 95,3 % |
| 2024-01 → 2026-06 | 480 | 100 % |

Início do monitoramento por UF: BA/CE/MA/PE/SE em 2015-01; MG 2018-11; ES 2019-04;
RJ/GO/DF/MS/RS/PR/SP ao longo de 2020; AC 2022-11; PA 2023-04.

**Recomendação:** manter a tabela cheia em 2015-01→2026-06 e documentar; qualquer análise que use
seca como regressor deve recortar em **2020-01** (90,5 % de cobertura) ou usar `seca_monitorado`
como filtro explícito. Isso vira a justificativa escrita no dicionário, satisfazendo o critério
"nenhuma coluna com > 40 % de nulos sem justificativa" do T-024.

### 3e. Macro (bônus, quase de graça)

`data/interim/parquet/macro_br_mes.parquet` (151 × 8) já está pronto e junta por `ano_mes` só —
broadcast nacional. Traz `ipca_mm` (necessário para o alvo relativo), `dolar_ptax_medio`, `selic`,
`igpm`. Prefixar `macro_`. Eleva o total para **4 fontes distintas** (IBGE/SIDRA, INMET, ANA, BCB),
com folga sobre o requisito de ≥3.

---

## Passo 4 — A junção

```
calendario_uf_mes                    (27 × 138 = 3.726)   espinha
  └─ LEFT JOIN ipca_uf_mes           on (sigla_uf, ano_mes)   → alvo        16 UF
  └─ LEFT JOIN clima_uf_mes          on (sigla_uf, ano_mes)   → clima local 27 UF
  └─ LEFT JOIN safra_uf_mes_largo    on (sigla_uf, ano_mes)   → safra       27 UF
  └─ LEFT JOIN seca_uf_mes           on (sigla_uf, ano_mes)   → seca        27 UF
  └─ LEFT JOIN macro_br_mes          on (ano_mes)             → broadcast nacional
  → checa_join() após CADA merge
  → filtrar linhas com alvo → 2.088 linhas
```

Regras:

- `checa_join()` obrigatório após cada merge, logando linhas antes/depois e taxa de match.
  Taxas esperadas (medidas): IPCA 94,6 %, clima 100 %, safra 100 %, seca 65,8 %.
- **Prefixar as colunas antes de cada merge** (`clima_`, `seca_`, `safra_`, `ipca_`, `macro_`).
  Não confiar em `suffixes` — `_x`/`_y` deixam a tabela ilegível. `ano`/`mes` existem em seca e
  clima e devem ser removidos, não desambiguados.
- **Calcular lags/janelas (T-023) na grade completa, ANTES do filtro final.** Filtrar primeiro
  quebraria o lag nas bordas de AC/MA/SE.
- O broadcast macro é intencional mas precisa ser consciente: essas colunas são idênticas para
  todas as UFs no mesmo mês, então explicam variação **no tempo**, nunca **entre capitais**.

Por que 2.088 e não 2.208: AC, MA e SE só entram no IPCA em 2018-05, faltando 40 meses × 3 UFs =
120 linhas. (O T-024 fala em "~2.350 para 17 capitais" — número do DIEESE, obsoleto.)

---

## Passo 5 — Notebook de análise (`notebooks/06_juncao_uf_mes.ipynb`)

No estilo dos notebooks 02–05 (português, `DICIONARIO` renderizado como DataFrame, matplotlib
`figsize=(11, 3.6)`, fecho com tabela "## O que fica para..."):

1. Diagnóstico lado a lado das 4 tabelas: grão, tipo de `ano_mes`, duplicatas, cobertura.
2. Demonstrar a armadilha: merge de `str` com `Timestamp` devolvendo tudo `NaN` sem erro; e o
   fan-out ×11 da safra não pivotada.
3. Cada merge com sua taxa de match e o log do `checa_join()`.
4. Perfil de nulos por coluna, com a justificativa de cada coluna acima de 40 %.
5. Validações de sanidade (abaixo).
6. Salvar o parquet e o dicionário.

---

## Verificação

```bash
python -m src.coleta.sidra_ipca.01_ibge_ipca_download   # após corrigir o sinal
python -m src.tratamento.21_clima_uf_mes
python -m src.tratamento.24_junta
```

Checagens que o script deve asseverar e o notebook exibir:

- [ ] `df.duplicated(['sigla_uf','ano_mes']).sum() == 0`
- [ ] `len(df) == 2088`; 16 UFs distintas; 138 meses distintos
- [ ] `ano_mes` é `Period[M]` em toda tabela de `interim/` (nenhuma string)
- [ ] `(df.ipca_var_alimentacao < 0).sum() > 0` — prova de que o bug do sinal foi corrigido
- [ ] Cada `LEFT JOIN` logado com linhas antes/depois e taxa de match
- [ ] Taxas batem com o medido: IPCA 94,6 %, clima 100 %, safra 100 %, seca 65,8 %
- [ ] Nenhuma coluna > 40 % de nulos sem justificativa escrita no dicionário
- [ ] Sazonalidade do clima correta: `clima_chuva_mm_mes` de janeiro ≫ agosto no Norte/Centro-Oeste
- [ ] Validação histórica da seca: CE em 2017-01 com `seca_pct_area_S2plus` ≈ 100 e
      `seca_severidade_media` ≈ 4,5
- [ ] Validação histórica do alvo: pico de `ipca_var_alimentacao` no 1º semestre de 2016 (seca do
      NE) e em 2020-2021 (câmbio + pandemia)
- [ ] `checa_join()` dispara alerta num teste proposital com chave desalinhada
- [ ] ≥ 3 fontes distintas — verificar explicitamente que há colunas de SIDRA/IBGE, INMET, ANA e BCB
- [ ] Dicionário cobre 100 % das colunas

---

## Arquivos

**Corrigir**

- [`src/coleta/sidra_ipca/01_ibge_ipca_download.py`](../src/coleta/sidra_ipca/01_ibge_ipca_download.py)
  linhas 159-162 — o sinal de menos

**Criar**

- `src/tratamento/chaves.py` — mover de `T-012_T-013/` e acrescentar `padroniza_chaves`,
  `valida_chaves`, `checa_join`
- `src/tratamento/21_clima_uf_mes.py`
- `src/tratamento/24_junta.py`
- `notebooks/06_juncao_uf_mes.ipynb`

**Gerar**

- `data/processed/calendario_uf_mes.parquet` (3.726)
- `data/interim/clima_uf_mes.parquet` (4.077)
- `data/processed/fato_alimentos_uf_mes.parquet` (2.088)
- `outputs/tabelas/dicionario_variaveis.csv` — nome, descrição, unidade, fonte, granularidade
  nativa, % de nulos, observação

**Consertos menores de caminho** (encontrados no caminho, corrigir junto)

- `notebooks/03_exploracao_safra_uf.ipynb` lê `data/interim/parquet/safra_uf_mes.parquet`; o
  arquivo está em `data/interim/safra_uf_mes.parquet`
- `src/coleta/inmet/catalogo.py` declara escrever em `data/interim/catalogo_estacoes.csv`; o
  arquivo está em `data/raw/catalogo_estacoes.csv`

---

## Fora de escopo (fica para depois)

- **T-022 — clima ponderado pela produção.** `data/interim/parquet/producao_uf_ano.parquet` já traz
  `peso_producao_uf` pronto. Captura o choque na região *produtora* em vez da *consumidora* — mais
  fiel ao mecanismo econômico, mas é um ticket próprio.
- **T-023 — features de lag.** O desenho acima deixa o gancho pronto (lags calculados na grade
  completa antes do filtro), mas as janelas em si são outro ticket.
- Tabela longa `UF × mês × item` para análise produto a produto — a larga cobre a modelagem.
