# Roteiro de apresentação (versão simplificada) — Da coleta bruta à tabela final

> Versão enxuta do `roteiro_apresentacao_dados.md`. Mesma narrativa, sem os números de detalhe:
> cada bloco `## Slide N` é um slide, os bullets são o conteúdo visível e **Notas** é a fala do
> apresentador. Os detalhes finos (contagens por fonte, tabelas de sujeira, comandos de reprodução)
> ficam no roteiro completo, para perguntas da banca.

> 📚 **Material de Aprofundamento para o Palestrante:** Cada slide deste roteiro está conectado aos guias técnicos da pasta [`docs/preparacao_palestrante/`](preparacao_palestrante/README.md), contendo referências de código (`src/`), justificativas matemáticas, decisões de engenharia e respostas para perguntas difíceis da banca.

---

## Slide 1 — Capa

**O que realmente move o preço da comida no Brasil?**
Clima, safra, macroeconomia e custo de frete na inflação alimentar regional

- SSC0957 — Prática em Ciência de Dados II
- Entrega: uma tabela única `UF × mês`, pronta para modelar
- **6 fontes · 5 instituições · 16 UFs · 11 anos e meio de série**

**Notas:** a narrativa pública simplifica — "a culpa é da seca" ou "a culpa é do dólar". A realidade é
multifatorial e varia por região. Para responder isso é preciso colocar clima, oferta agrícola,
macroeconomia e custo logístico na *mesma linha da mesma tabela*. Esta apresentação é sobre como essa
linha foi construída.

👉 **Defesa Técnica da Implementação:** [Módulo 1 — Fundamentos e Escopo](preparacao_palestrante/01_slides_01_a_04_fundamentos_e_arquitetura.md#slide-1--capa-o-que-realmente-move-o-preço-da-comida-no-brasil)

---

## Slide 2 — A pergunta e o desenho da tabela

- **Alvo:** a inflação de alimentos medida pelo IPCA, mês a mês, por área urbana
- **Explicativas:** clima local, seca, safra, macroeconomia nacional e preço de combustível
- **O problema:** cada fonte chega num grão diferente — estação meteorológica, produto agrícola, item
  de índice de preço, país inteiro
- **Denominador comum:** só duas coisas são compartilhadas por todas elas — a **UF** e o **mês**
- **Grão final:** `UF × mês`, formato largo, uma linha por estado e mês

**Notas:** essa é a decisão estruturante do projeto. Nenhuma fonte conversa com as outras do jeito que
vem do disco. Tudo teve de ser reduzido a `UF × mês` antes de qualquer merge — e é essa redução que
consome a maior parte do trabalho.

👉 **Defesa Técnica da Implementação:** [Módulo 1 — Pergunta e Desenho da Tabela](preparacao_palestrante/01_slides_01_a_04_fundamentos_e_arquitetura.md#slide-2--a-pergunta-e-o-desenho-da-tabela)

---

## Slide 3 — As seis fontes

| Fonte | Instituição | O que traz |
|---|---|---|
| SIDRA / IPCA | IBGE | **o alvo** — inflação de alimentos por área urbana |
| BDMEP | INMET | chuva, temperatura e extremos climáticos |
| Monitor de Secas | ANA | severidade e área do estado em seca |
| SIDRA / LSPA | IBGE | estimativa de safra e sua revisão mensal |
| SGS | BCB | dólar, Selic, inflação geral, IGP-M |
| Levantamento de Preços | ANP | diesel, gasolina, etanol e gás de cozinha |

- Requisito da disciplina: ≥ 3 fontes heterogêneas. **Entregamos 6 pesquisas, de 5 instituições.**
- Todas públicas e sem chave de acesso — o pipeline inteiro é reprodutível por qualquer pessoa

**Notas:** vale marcar que "IBGE" aparece duas vezes, mas são *pesquisas diferentes*: o IPCA mede preço
ao consumidor em área urbana, o LSPA estima safra por estado. Metodologia, grão e periodicidade não têm
nada em comum.

👉 **Defesa Técnica da Implementação:** [Módulo 1 — As Seis Fontes Heterogêneas](preparacao_palestrante/01_slides_01_a_04_fundamentos_e_arquitetura.md#slide-3--as-seis-fontes-de-dados)

---

## Slide 4 — O pipeline em três camadas

```
data/raw/          →  data/interim/        →  data/processed/
dado como baixado     tabela por fonte,       tabela única,
NUNCA modificado      já em UF × mês          pronta para modelar
```

- **`raw/`** guarda o dado exatamente como veio da fonte e nunca é tocado
- **`interim/`** tem uma tabela por fonte, já padronizada no grão comum
- **`processed/`** tem a tabela final integrada
- Código modular por fonte, cada um com um validador próprio que passa ou falha a etapa

**Notas:** a separação raw/interim/processed é o que torna o trabalho reprodutível. Um erro descoberto
no tratamento nunca exige rebaixar o dado bruto — ele está intacto no disco. O próximo slide mostra o
que acontece quando essa regra é quebrada.

👉 **Defesa Técnica da Implementação:** [Módulo 1 — Pipeline em Três Camadas](preparacao_palestrante/01_slides_01_a_04_fundamentos_e_arquitetura.md#slide-4--o-pipeline-em-três-camadas)

---

## Slide 5 — Erros que não levantam exceção nenhuma

**O bloqueador do projeto: o sinal do IPCA estava invertido**
- Uma limpeza de texto removeu o hífen que marcava "não publicado" — e junto levou o **sinal de menos
  de todo valor negativo**
- Resultado: **toda deflação virou inflação**, e o alvo do projeto ficou corrompido
- Nenhum erro, nenhum aviso. Só aparece quando alguém pergunta *"quantos valores negativos essa série
  tem?"* — e a resposta é zero, o que é impossível para inflação mensal
- A correção exigiu **re-coletar tudo**, porque naquele momento o bruto não estava preservado
- Virou teste permanente: o código falha se o alvo não tiver deflação

**O mesmo padrão aparece nas outras fontes**
- **INMET:** o formato dos arquivos muda no meio da série, e o código de "sem medição" vira uma
  temperatura de milhares de graus negativos se passar batido
- **ANA:** a API devolve todas as revisões do mesmo mês empilhadas, sem dizer qual vale — e algumas
  revisões antigas trazem valor de placeholder
- **ANP:** meses com coleta duplicada, onde a média simples dá o mesmo peso a 1 posto e a milhares

**Notas:** o fio condutor da apresentação é este. Nenhum desses erros trava a execução — todos produzem
um número plausível e errado. O trabalho não foi rodar o código, foi descobrir onde ele mentia.

👉 **Defesa Técnica da Implementação:** [Módulo 2 — Erros Silenciosos e o Bloqueador](preparacao_palestrante/02_slides_05_a_07_erros_silenciosos_e_contrato_chaves.md#slide-5--erros-que-não-levantam-exceção-nenhuma)

---

## Slide 6 — As três armadilhas da junção

### 1. O merge que devolve tudo vazio
Uma tabela guarda o mês como `"2015-01"`, a outra como `"2015-01-01"`. São duas strings, o pandas
aceita, e o resultado é **uma coluna inteira de vazio disfarçada de junção** — sem exceção, sem aviso.

### 2. O merge que multiplica as linhas
A safra tem uma linha por **produto** dentro de cada `UF × mês`. Juntar direto **multiplica a tabela
por 11** — e a taxa de match ainda parece saudável, o que torna o erro convincente.

### 3. A variação mensal inventada
Calcular "variação contra o mês anterior" numa série com buracos compara janeiro com julho e rotula o
resultado como variação de um mês. **Não é erro de cálculo, é erro de rótulo** — e entra calado em
qualquer regressão.

**Notas:** a terceira é a mais traiçoeira, porque nenhuma verificação de merge a detecta: o merge está
certo, o número é que é mentira.

👉 **Defesa Técnica da Implementação:** [Módulo 2 — As Três Armadilhas da Junção](preparacao_palestrante/02_slides_05_a_07_erros_silenciosos_e_contrato_chaves.md#slide-6--as-três-armadilhas-da-junção)

---

## Slide 7 — O contrato de chaves que fecha as três portas

Um módulo único que toda fonte é obrigada a atravessar antes de entrar num merge:

| O que faz | O que garante |
|---|---|
| **padroniza** | `sigla_uf` e `ano_mes` sempre no mesmo tipo, venham como vierem |
| **valida** | recusa sigla fora do padrão, tipo errado de mês e chave duplicada |
| **checa o join** | compara linhas antes/depois e a taxa de match; **levanta erro** se a contagem mudou ou se nada casou |

- O mês é guardado num tipo **que não tem dia** — assim não existe um "2015-01-01" para divergir de um
  "2015-01" (fecha a armadilha 1)
- A verificação roda **depois de cada merge**, e não é opcional (fecha a armadilha 2)
- Toda variação temporal é calculada **sobre a grade completa de meses**, antes do merge: mês ausente
  vira linha vazia e a variação nasce vazia junto, que é a verdade (fecha a armadilha 3)

**Notas:** essas funções foram escritas *depois* de as armadilhas terem sido demonstradas em notebook,
célula por célula. Elas existem para transformar erro silencioso em erro alto.

👉 **Defesa Técnica da Implementação:** [Módulo 2 — O Contrato de Chaves (chaves.py)](preparacao_palestrante/02_slides_05_a_07_erros_silenciosos_e_contrato_chaves.md#slide-7--o-contrato-de-chaves-que-fecha-as-três-portas)

---

## Slide 8 — Cada fonte reduzida ao grão comum

| Fonte | A redução | A decisão não-óbvia |
|---|---|---|
| **IPCA** | itens viram colunas, uma por produto/grupo | chavear pelo **código**, não pelo nome — o IBGE renomeia item no meio da série |
| **Clima** | centenas de estações → um valor por UF | **mediana** entre estações, robusta a sensor defeituoso; mês de estação com poucos dias medidos é descartado antes de agregar |
| **Safra** | 11 produtos viram colunas | o que interessa é a **revisão** da estimativa, não o nível: é ela que se move quando a lavoura quebra |
| **Seca** | já vinha em UF × mês | a ANA já agregou município → estado; bastou padronizar a chave |
| **Macro** | série nacional replicada por mês | é **idêntica em todas as UFs** — por isso não explica diferença entre estados |
| **Combustível** | 5 produtos viram colunas | onde há coleta duplicada, **média ponderada pelo nº de postos**, nunca média simples |

- Regra transversal: **agregar só depois de garantir que o dado agregado significa alguma coisa.** Um
  mês com poucos dias medidos não é uma medida do mês
- E cada grandeza agrega do jeito dela: chuva soma no dia, mas nunca soma entre estações

**Notas:** o exemplo mais claro dessa regra é o clima. Os índices de extremo — quantos dias sem chuva,
qual a maior sequência seca — precisam sair do nível diário. Depois que o mês virou um total, eles são
impossíveis de recuperar: 90 mm podem ser 3 mm em 30 dias ou 90 mm num dia só, e para uma safra a
diferença é tudo.

👉 **Defesa Técnica da Implementação:** [Módulo 3 — Redução de Cada Fonte ao Grão Comum](preparacao_palestrante/03_slides_08_a_10_reducao_juncao_e_combustiveis.md#slide-8--cada-fonte-reduzida-ao-grão-comum)

---

## Slide 9 — A junção: uma espinha de calendário e cinco LEFT JOINs

```
calendario_uf_mes  (todas as UFs × todos os meses)      ← a espinha
  └─ LEFT JOIN  IPCA · clima · safra · seca · macro
  → verificação após CADA merge
  → um único filtro no fim, pelas UFs que têm alvo
```

- **A espinha é o calendário completo, não o IPCA** — e todo merge é `LEFT`, nunca `INNER`
- Assim as linhas sem alvo caem num **único filtro no fim, onde a perda é contada**, em vez de sumirem
  aos poucos dentro dos merges sem ninguém perceber
- **A contagem de linhas se mantém nos cinco merges** — é isso que prova que nenhuma multiplicação
  aconteceu
- Cada fonte recebe um **prefixo próprio antes do merge** (`clima_`, `safra_`, `seca_`…), o que mantém
  a tabela legível e evita colisão de nomes
- Os combustíveis entram numa **segunda junção**, pendurados na tabela já pronta: nenhuma linha pode
  entrar, sair ou mudar de valor

**Notas:** a ordem importa menos do que a disciplina: espinha primeiro, LEFT sempre, verificação depois
de cada passo, filtro só no fim. Com isso, a contagem de linhas da tabela final fecha exatamente com o
que era esperado.

👉 **Defesa Técnica da Implementação:** [Módulo 3 — A Junção e Espinha de Calendário](preparacao_palestrante/03_slides_08_a_10_reducao_juncao_e_combustiveis.md#slide-9--a-junção-uma-espinha-de-calendário-e-cinco-left-joins)

---

## Slide 10 — Por que combustível entra numa tabela sobre comida

- **O diesel é o custo de frete de toda a comida.** Nada sai da lavoura sem caminhão, e o Brasil move a
  maior parte da sua carga por rodovia
- **O gás de cozinha é item da própria cesta do IPCA** — é o preço de *cozinhar* o alimento
- Razão estrutural: as variáveis macroeconômicas são **idênticas em todas as UFs**. Preço de
  combustível tem as duas dimensões: **tempo e espaço**

**A validação que raramente é possível**
- A mesma base da ANP foi extraída num segundo formato, muito mais fino: uma linha por coleta de posto
- A cobertura desse formato é esburacada, então ele **não serve de fonte — serve de testemunha**
- Confrontadas as duas extrações, os preços batem quase perfeitamente, com erro típico abaixo de 1 %

**Notas:** duas extrações independentes, grãos diferentes, mesmo número. Na maioria das fontes não
existe uma segunda medição para confrontar; onde existe, é a checagem mais forte que se pode fazer.

👉 **Defesa Técnica da Implementação:** [Módulo 3 — Combustíveis e Validação por Testemunha](preparacao_palestrante/03_slides_08_a_10_reducao_juncao_e_combustiveis.md#slide-10--por-que-combustível-entra-numa-tabela-sobre-comida)

---

## Slide 11 — A tabela final

### `data/processed/fato_alimentos_combustiveis_uf_mes.parquet`

- **Uma linha por UF e mês**, chave única, sem duplicatas
- **16 UFs · 138 meses (2015 → meados de 2026) · ~2,1 mil linhas × 108 colunas**

| Família | Fonte |
|---|---|
| `ipca_*` — o alvo e os itens da cesta | IBGE/SIDRA |
| `safra_*` — produção e revisão por produto | IBGE/LSPA |
| `comb_*` — preço, variação e desvio regional | ANP |
| `clima_*` — chuva, temperatura e extremos | INMET |
| `seca_*` — área e severidade | ANA |
| `macro_*` — dólar, Selic, inflação geral | BCB/SGS |

- **Dicionário de variáveis cobrindo 100 % das colunas**: nome, descrição, unidade, fonte,
  granularidade de origem, % de nulos e **o que o vazio significa**

**Notas:** o requisito da disciplina era "várias dezenas de variáveis após a agregação das bases". São
108 colunas, de 6 pesquisas de 5 instituições, todas documentadas linha a linha.

👉 **Defesa Técnica da Implementação:** [Módulo 4 — A Tabela Final e suas 108 Colunas](preparacao_palestrante/04_slides_11_a_13_tabela_fato_nulos_e_validacoes.md#slide-11--a-tabela-final)

---

## Slide 12 — Cada vazio significa uma coisa diferente

| Família | O `NaN` significa | Preencher com 0? |
|---|---|---|
| `seca_*` | a UF **não era monitorada** naquele mês | **Não** — inventaria ausência de seca onde não houve medição |
| `comb_*` | **mês sem pesquisa** da ANP | **Não** — criaria postos vendendo diesel de graça |
| `safra_revisao_*` | a estimativa **não tem contra o que ser comparada** | **Não** — 0 significaria "a estimativa não mudou" |
| `clima_*` | nenhuma estação da UF teve medição suficiente no mês | **Não** |

> ⚠️ O caso da seca é o mais perigoso. O Monitor **nasceu no Nordeste e foi se expandindo** estado a
> estado ao longo dos anos. Preencher com 0 ensinaria ao modelo que não havia seca no Sul — o que é
> falso: **ninguém estava medindo.** E, pior, faria o modelo confundir *"seca"* com *"ser do Nordeste"*.

- Regra do projeto: **nenhum vazio vira 0 por acidente**, e toda coluna com nulo ganha justificativa
  escrita no dicionário
- Há um problema equivalente no clima: a rede de estações **cresce** ao longo da série, e um degrau na
  série climática pode ser artefato da rede, não do clima — por isso a contagem de estações é uma
  coluna da tabela

**Notas:** todo vazio desta base carrega uma afirmação sobre o mundo. A afirmação errada muda a
conclusão de qualquer regressão — por isso a justificativa vai em todas as colunas, não só nas piores.

👉 **Defesa Técnica da Implementação:** [Módulo 4 — Semântica dos Nulos e Perigo do Zero](preparacao_palestrante/04_slides_11_a_13_tabela_fato_nulos_e_validacoes.md#slide-12--cada-vazio-significa-uma-coisa-diferente)

---

## Slide 13 — Validação: estrutural primeiro, histórica depois

**Estruturais — assertivas no código, que falham a execução**
- ✅ chave única, contagem de linhas, UFs e meses conforme o esperado
- ✅ o mês é sempre do mesmo tipo em toda a tabela
- ✅ o alvo tem deflação — prova de que o bug do sinal não voltou
- ✅ preços dentro de faixas fisicamente possíveis
- ✅ nenhuma coluna muito vazia sem justificativa escrita

**Históricas — a tabela reconhece o que sabemos que aconteceu**
- A **seca do Ceará em 2017** aparece com o estado inteiro em seca severa
- O **pico da inflação de alimentos no fim de 2020** (câmbio + pandemia) está lá
- A **sazonalidade climática** bate com a física do país: chove no Norte em janeiro, não em agosto
- O **choque do diesel em 2022** (petróleo pós-invasão da Ucrânia) e a queda de 2023 aparecem inteiros

**Notas:** é isso que separa uma junção que **roda** de uma junção **correta**. Ninguém disse à tabela
que esses eventos existiram — ela os reconhece sozinha.

👉 **Defesa Técnica da Implementação:** [Módulo 4 — Validações Estruturais e Históricas](preparacao_palestrante/04_slides_11_a_13_tabela_fato_nulos_e_validacoes.md#slide-13--validação-estrutural-primeiro-histórica-depois)

---

## Slide 14 — O achado que justifica a última fonte existir

**A defasagem: o diesel de hoje explica a comida de quando?**
- A correlação entre a variação do diesel e a inflação de alimentos **sobe quando o diesel é adiantado
  em cerca de 4 meses**, e cai depois disso
- É a forma de um **repasse de custo**, não de uma coincidência — e a ordem de grandeza bate com o que
  a literatura de repasse de frete ao varejo alimentar registra

**A dimensão que a macroeconomia não tem: espaço**
- Comparando cada UF com a mediana nacional do mês, o **Acre paga cerca de 20 % a mais pelo diesel — em
  todo mês da série**. É distância de refinaria e custo de escoamento
- No outro extremo, o Paraná paga consistentemente abaixo da mediana
- **O dólar é idêntico nas 16 UFs e não consegue explicar isso.** O preço de combustível, sim

**Notas:** esse é o fechamento. A integração não só funcionou tecnicamente — ela produziu um sinal que
nenhuma das fontes isoladas continha.

👉 **Defesa Técnica da Implementação:** [Módulo 5 — Achados Empíricos: Lag e Espaço](preparacao_palestrante/05_slides_14_a_15_achados_limites_e_proximos_passos.md#slide-14--o-achado-que-justifica-a-última-fonte-existir)

---

## Slide 15 — Limites de uso e próximos passos

| ✅ Dá para | ❌ Não dá para |
|---|---|
| Usar o diesel defasado como preditor do alvo | Ler vazio em combustível como preço zero |
| Comparar a inflação de um item com a do grupo, na mesma UF | Somar os pesos dos itens entre si — os níveis se sobrepõem |
| Explicar diferença **entre estados** com o preço de combustível | Explicar diferença entre estados com variáveis macro |
| Ler a revisão da safra como choque de oferta | Somar a produção ao longo dos meses — é estimativa do ano, não fluxo mensal |
| Comparar clima entre meses da mesma UF | Comparar nível de clima entre UFs sem olhar a contagem de estações |

**O que fica para as próximas etapas**
- Agregar o clima **pesando pela produção agrícola** da região, não por mediana simples
- Criar **variáveis defasadas** de chuva e seca (1 a 6 meses) e médias móveis
- Modelagem e análise de importância de variáveis — alvo e regressores já estão na mesma linha
- Fechar a lacuna temporal da fonte de combustíveis e versionar o seu script de coleta

**A lição transversal do projeto**
> Dos seis merges desta tabela, **três falhariam em silêncio** se escritos do jeito óbvio: um devolve
> tudo vazio, um multiplica as linhas, e um inventa uma variação mensal que não existiu.
> Nenhum levanta exceção. O trabalho não foi juntar os dados — foi **construir as verificações que
> transformam erro silencioso em erro alto**.

👉 **Defesa Técnica da Implementação:** [Módulo 5 — Limites de Uso e Roadmap de Modelagem](preparacao_palestrante/05_slides_14_a_15_achados_limites_e_proximos_passos.md#slide-15--limites-de-uso-e-próximos-passos)

---

## 🎯 Simulação e Treinamento de Perguntas da Banca

Para treinar a resposta a perguntas agressivas e profundas de avaliação (como quebra de suporte espacial, escolha de mediana vs média, recusa de imputação por KNN/MICE e causalidade da defasagem), estude o:  
👉 [**Módulo 6: Simulado de Alta Tensão da Banca (15 Perguntas e Respostas)**](preparacao_palestrante/06_simulado_perguntas_da_banca.md)
