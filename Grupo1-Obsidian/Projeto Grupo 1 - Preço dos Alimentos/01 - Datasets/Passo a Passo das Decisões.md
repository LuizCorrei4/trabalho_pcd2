
> **Projeto:** O que realmente move o preço da comida no Brasil? (SSC0957)  
> Esta nota conta, **em ordem**, como saímos de seis fontes soltas e chegamos a uma tabela única, e **por que** cada escolha foi feita quando havia mais de um caminho. Os caminhos que pesquisamos e **não** usamos estão reunidos em [[Alternativas descartadas]].  
> Visão geral das decisões: [[Decisões e Justificativas do Projeto]] · avaliação de cada fonte: [[Resumo]] · detalhes técnicos: [[Integração das Bases]].

**Como ler.** Cada decisão segue o mesmo formato: 🧭 a pergunta · 🔀 as opções · ✅ o que escolhemos · 💡 por quê · ⚠️ o cuidado que quem usa a tabela precisa ter.

**Roteiro**

1. [[#Parte 1 — Planejamento]] (decisões 1 a 6)
2. [[#Parte 2 — Coleta]] (decisões 7 a 17)
3. [[#Parte 3 — Padronização e junção]] (decisões 18 a 28)
4. [[#Parte 4 — Combustíveis]] (decisões 29 a 33)
5. [[#Parte 5 — Documentação do resultado]] (decisão 34)
6. [[#O que ainda falta]]

```
PLANEJAR         COLETAR                  PADRONIZAR            JUNTAR                      RESULTADO
tema             IBGE/SIDRA -> IPCA       mês num formato só    calendário 27 UFs x 138     1 tabela
alvo             INMET      -> clima      UF sempre em sigla    meses + LEFT JOINs          2.088 linhas
fontes           ANA        -> seca       cada fonte reduzida   + combustíveis (ANP)        108 colunas
período          IBGE/LSPA  -> safra      a UF x mês
                 BCB        -> macro
                 ANP        -> combustível
                 data/raw/ -------------> data/interim/ ------------------------------> data/processed/
```

---

# Parte 1 — Planejamento

Antes de baixar qualquer arquivo, precisamos decidir **o que perguntar**, **o que medir** e **com quais dados**.

### 🧭 Decisão 1 — Qual tema estudar?

- 🔀 **Opções:** ondas de calor na Europa · impactos do El Niño na economia · **clima e preço dos alimentos no Brasil**.
- **Critérios de comparação:** dados disponíveis, possibilidade de cruzar fontes diferentes e relevância do problema. Também queríamos evitar fontes com as quais o grupo já teve dificuldade (como o DataSUS).
- ✅ **Escolha:** como clima, safra, custo logístico e macroeconomia se relacionam com o preço dos alimentos no Brasil.
- 💡 **Por quê:** dados públicos e em tabela (sem mapas de satélite nem PDFs complicados), várias fontes cruzáveis, e o preço da comida afeta diretamente o orçamento das famílias.
- **Pergunta central:** _quais fatores ajudam a explicar a variação regional dos preços dos alimentos no Brasil?_ A tabela final precisa permitir testar H1 clima · H2 safra · H3 logística · H4 macroeconomia · H5 diferenças entre regiões.

### 🧭 Decisão 2 — Como medir o "preço da comida"? (variável-alvo)

- 🔀 **Opções:** cesta básica do DIEESE × **IPCA de alimentos (IBGE/SIDRA)**.

|DIEESE|**IPCA (SIDRA)**|
|---|---|---|
|O que é|valor da cesta em R$, por capital|variação % mensal, por área urbana|
|Formato|relatórios mensais em **PDF**, layout que muda entre anos|**API pública**, tabela pronta|
|Preço por produto|fechado ao público desde 2018|disponível (arroz, tomate, café, carnes...)|
|Cobertura|17 capitais|16 áreas urbanas|
|Tipo de número|valor em R$ (tem tendência, exigiria deflacionar)|variação % (comparável entre meses e regiões)|

- ✅ **Escolha:** IPCA do grupo _Alimentação e bebidas_ e de itens selecionados, por área urbana.
- 💡 **Por quê:** é o índice oficial de inflação, vem por API, traz preço por produto e já é variação percentual. **Ler os PDFs do DIEESE era a tarefa mais arriscada do projeto (ticket T-011) e foi abandonada.**
- ⚠️ O IPCA só existe para **16 UFs**. Ficam de fora MT (maior produtor de grãos), AL, PB, PI, RN, AM, AP, RO, RR, TO e SC. As UFs onde o clima afeta a produção nem sempre são as mesmas onde o preço é medido.

### 🧭 Decisão 3 — Com quais dados explicar o preço?

Para cada hipótese precisávamos de pelo menos uma fonte. Avaliamos por relevância, período, frequência (queremos **mensal**), detalhe regional (queremos **por UF**) e facilidade de cruzar.

|Hipótese|Fonte avaliada|O que traz|Decisão|Motivo|
|---|---|---|---|---|
|H1 Clima|**INMET** (BDMEP)|chuva e temperatura de ~700 estações|✅ usar|medição direta e diária, no país inteiro|
|H1 Clima|**ANA** (Monitor de Secas)|% do estado em seca e severidade|🟡 usar com ressalva|índice pronto e validado por especialistas, mas só cobre o país inteiro a partir de 2023|
|H2 Safra|**IBGE/LSPA** + PAM|estimativa mensal de safra por UF e produto|✅ usar|é mensal e por UF|
|H2 Safra|CONAB|safra, estoques e custos|❌ descartar|**anual por ano-safra** (ex.: 2024/25); virar mês exige suposições, e o LSPA já mede o mesmo mês a mês|
|H3 Logística|**ANP**|diesel, gasolina, etanol e gás de cozinha|✅ usar|único custo que muda **no tempo e entre estados**|
|H3 Logística|CEPEA/ESALQ|preços na origem e frete|⏸️ não coletada|estava na proposta, ficou para depois|
|H4 Macro|**BCB/SGS**|dólar, Selic, inflação geral, IGP-M|✅ usar|séries oficiais, sem nenhum valor faltando|

- ✅ **Escolha:** seis pesquisas de cinco instituições (IBGE/SIDRA, INMET, ANA, IBGE/LSPA, BCB e ANP). A disciplina pedia pelo menos três fontes.
- 💡 **Por que INMET _e_ ANA?** O INMET mede o clima de cada dia (pico de calor, chuva forte); a ANA resume a **seca prolongada** num índice pronto.

### 🧭 Decisão 4 — O que cada linha da tabela final representa?

Cada fonte chega com um **grão** diferente:

|Fonte|Uma linha é...|
|---|---|
|IPCA|um item (arroz, tomate...) numa área urbana, num mês|
|INMET|uma estação meteorológica numa hora|
|Safra|um produto numa UF, num mês|
|Seca|uma UF num mês|
|BCB|o Brasil inteiro num mês|
|ANP|um combustível numa UF, num mês|

- 🔀 **Opções:** município × mês · região metropolitana × mês · **UF × mês** · Brasil × mês; e formato **longo** ou **largo**.
- ✅ **Escolha:** **UF × mês, formato largo.** Chave `(sigla_uf, ano_mes)`.
- 💡 **Por quê:** UF e mês são as **únicas** dimensões que todas as fontes têm em comum. Município não existe no IPCA nem na seca; Brasil × mês jogaria fora a variação regional, que é a pergunta. O formato largo deixa "uma linha = um estado num mês", o que os modelos esperam.
- ⚠️ A área urbana do IPCA (ex.: RM de Belém) vira a UF (PA), pelos 2 primeiros dígitos do código IBGE. O preço é o da capital e arredores, não do estado inteiro.

### 🧭 Decisão 5 — Qual período analisar?

- ✅ **Escolha:** **2015-01 a 2026-06 (138 meses)**, fixado em `src/config.py`.
- 💡 **Por quê:** é o período em que **todas** as fontes existem ao mesmo tempo; junho de 2026 é o último mês que todas têm.
- **Baixamos mais, de propósito:** IPCA desde 2006-07 (acumulado em 12 meses de jan/2015 precisa de 2014); INMET, safra e BCB desde 2014-01 (variáveis defasadas); ANP desde 2004-05 (variação em 12 meses de jan/2015).
- ⚠️ Cálculos que olham para trás são feitos **na série inteira, antes do corte**. Cortando primeiro, os 12 primeiros meses ficariam vazios.

### 🧭 Decisão 6 — Como organizar os arquivos para 5 pessoas?

- 🔀 **Opções:** cada um com seus caminhos no próprio computador · estrutura fixa com os dados separados por etapa.
- ✅ **Escolha:** `data/raw/` (como veio, **nunca modificado**) → `data/interim/` (uma tabela por fonte, limpa) → `data/processed/` (tabela final e `dim_uf.csv`). `src/config.py` guarda todos os caminhos e o período. Dados fora do Git; quem clona gera tudo com `python -m src.coleta.runner --completo`.
- 💡 **Por quê:** se um erro aparece no tratamento, refaz-se a partir de `raw/` sem baixar tudo de novo. A Decisão 8 mostra o que acontece quando essa regra não é respeitada.

---

# Parte 2 — Coleta

|Fonte|Como foi baixada|O que chegou|
|---|---|---|
|IBGE/SIDRA: IPCA|API, 168 requisições em blocos de 3 meses|83.383 linhas, 2006-07 a 2026-07|
|INMET: clima|13 ZIPs anuais (~1,27 GB)|701 estações, dados **por hora**|
|ANA: seca|API REST, uma requisição por UF|27 UFs, série mensal|
|IBGE/LSPA: safra|API do SIDRA (tabela 6588) + PAM (1612 e 1613)|44.847 linhas, 11 produtos|
|BCB/SGS: macro|API do Banco Central, 5 séries|151 meses, nenhum valor faltando|
|ANP: combustíveis|extração da base de preços (CSV)|26.446 linhas, 8 produtos|

### 🧭 Decisão 7 — De qual tabela do SIDRA tirar o IPCA?

O IBGE troca a tabela sempre que revisa a estrutura do índice; nenhuma cobre o período todo.

- 🔀 **Opções:** só a 7060 (começa em jan/2020, perderíamos 2015–2019) · emendar com a 7062 (**não serve**: é o IPCA-15, outro índice) · **encadear 2938 → 1419 → 7060** (mesma pesquisa, mesmos códigos de item).
- ✅ **Escolha:** encadear **2938** (2006–2011), **1419** (2012–2019) e **7060** (2020–2026), buscando **N7** (10 regiões metropolitanas) e **N6** (6 municípios).
- 💡 **Por que os dois níveis:** o IPCA não tem nível "UF" (o N3 devolve erro 404). Só com N7 se perderiam Brasília, Goiânia, Campo Grande, São Luís, Aracaju e Rio Branco.

### 🧭 Decisão 8 — O que fazer com os marcadores de "sem dado" do SIDRA?

O SIDRA escreve `-` (ou `...`, `X`) quando um valor não foi publicado. A primeira versão do coletor limpava isso **apagando o caractere `-` de todo o texto**. Resultado: `-0,48` virou `0,48`; **toda queda de preço virou alta**, sem erro e sem aviso.

|Com o erro|Corrigido|
|---|---|---|
|valores negativos (deflação)|**0**|**32.696**|
|menor valor|0,00 %|−56,62 %|
|média por mês|3,14 % (≈ 45 % ao ano)|0,75 %|

- ✅ **Escolha:** anular só o texto que é, **inteiro**, um marcador, e **baixar tudo de novo**.
- 💡 **Por que baixar de novo:** o arquivo em `raw/` já tinha passado pela limpeza errada e não havia cópia intacta. Isso motivou a regra "nunca modificar `data/raw/`".
- ⚠️ A junção agora **falha de propósito** se o alvo não tiver nenhum mês de deflação (`src/tratamento/24_junta.py`): onze anos de inflação mensal sem valor negativo é impossível.

### 🧭 Decisão 9 — Identificar cada item pelo nome ou pelo código?

- ✅ **Escolha:** pelo **código** (ex.: `1101002`).
- 💡 **Por quê:** o IBGE **renomeia itens no meio da série** (40 códigos com 42 nomes; "Leite pasteurizado" virou "Leite longa vida"; "macassar" virou "macáçar"). Agrupar pelo nome quebraria as séries em duas.

### 🧭 Decisão 10 — Como ler 1,27 GB do INMET sem travar e sem ler lixo?

- ✅ **Escolhas:** um ano e um arquivo por vez, lidos direto do ZIP (descompactar tudo ocuparia vários GB); **colunas encontradas pelo nome, não pela posição** (o formato mudou em 2019: rótulos sem acento, data com `/`, "sem medição" deixou de ser `-9999` e virou campo vazio); `-9999` tratado como vazio já na leitura.
- 💡 **Por quê:** um `-9999` que chega a uma média vira uma "temperatura" de milhares de graus negativos, e o código não reclama.

### 🧭 Decisão 11 — Em que ordem transformar hora → dia → mês?

- 🔀 **Opções:** hora → mês direto (mais simples) · passando pelo dia.
- ✅ **Escolha:** **hora → dia → mês**, com regras por grandeza:
    - chuva do dia = **soma** das horas; temperatura = média, máxima e mínima;
    - um dia só vale com **≥ 18 horas medidas**, conferido por grandeza (é comum o pluviômetro parar e o termômetro continuar);
    - soma com `min_count=1` (senão um dia **sem medição** vira "0 mm");
    - índices de extremo (dias sem chuva, maior sequência seca, calor extremo) calculados **a partir dos dias**: depois de virar total mensal, não dá para saber como a chuva se distribuiu (90 mm espalhados ≠ 90 mm numa tempestade, que deixa 15 dias secos seguidos);
    - "calor extremo" = acima do **percentil 90 da própria estação naquele mês do ano** (32 °C é normal em Teresina e raro em Curitiba);
    - **direção do vento ficou de fora**: é um ângulo, e a média de 350° e 10° dá 180°, o lado oposto.

### 🧭 Decisão 12 — O que fazer onde as estações não mediram?

Critério de cobertura: pelo menos 90 % dos dias com alguma estação medindo. Dois problemas apareceram:

- **Roraima** tem praticamente uma estação; em 2021 e 2026 não mediu nada. Nenhum tratamento resolve: o dado não existe.
- **Buraco nacional em 2021–2022** (o RN cai de 100 % para 38 % em 2021), justamente o ano da crise hídrica do Centro-Sul.
- 🔀 **Opções:** preencher com a normal climatológica · usar outra fonte (**NASA POWER**, satélite em grade, sem falha de estação) · **manter vazio e documentar**.
- ✅ **Escolha (por enquanto):** manter vazio e guardar `clima_n_estacoes`.
- 💡 **Por quê:** preencher agora esconderia a incerteza justamente no período de maior interesse. Imputação e NASA POWER ficaram como pendência.
- ⚠️ A rede cresce (475 estações em 2014, 638 em 2026): um degrau na série que coincide com salto no número de estações é efeito da rede, não do clima.

### 🧭 Decisão 13 — Como obter os dados de seca?

- 🔀 **Opções:** baixar o CSV do site (**não existe**: a página monta a tabela no navegador) · baixar mapas e cruzar com municípios (exige geoprocessamento, shapefiles, `geopandas`) · **usar a API que o próprio site usa** (descoberta lendo o JavaScript da página).
- ✅ **Escolha:** API REST aberta da ANA, **uma requisição por UF** (27, menos de um minuto).
- 💡 **Por quê:** o campo `area` não é km², é o **% do território da UF** em seca; as categorias são **cumulativas** (S2 = "grave ou pior"). A própria ANA já agrega município → UF, então não foi preciso geoprocessamento.

### 🧭 Decisão 14 — A API devolve várias versões do mesmo mês. Qual usar?

Quando a ANA revisa um mês, a API devolve **todas as versões juntas**, sem dizer qual vale, e algumas versões antigas trazem valores absurdos (Bahia, abril/2015: `984700` em vez de `9847`, escala ×100; em junho/2016 um `123456`, claramente de teste).

- 🔀 **Opções:** a primeira · o maior valor · a média · **a mais recente (maior `id`)**.
- ✅ **Escolha:** a versão de **maior `id`** (vigente), gravando as divergências (49 UF-meses) em `outputs/tabelas/monitor_secas_revisoes_divergentes.csv` para auditoria.
- ⚠️ O que não dá para consertar, a gente marca: um mês do Maranhão (2014-11) viola a regra cumulativa (S3 = 0 com S4 = 13) e recebeu `inconsistente = True`. Não inventamos valor.

### 🧭 Decisão 15 — Quais produtos e quais cálculos para a safra?

(A escolha LSPA × CONAB está na Decisão 3.)

- ✅ **Escolhas:** tabela 6588 (LSPA, estimativa da safra do ano revista todo mês, por UF) complementada pela PAM (1612 e 1613); **11 produtos** (arroz, feijão, milho, soja, trigo, café, banana, batata-inglesa, tomate, mandioca, cana-de-açúcar); **somar as safras que o IBGE separa** (feijão 1ª/2ª/3ª, milho 1ª/2ª, café arábica/canéfora, batata das 3); **recalcular o rendimento** (produção total ÷ área total).
- 💡 **Por que recalcular:** a média de rendimentos dá o mesmo peso a uma safra de mil hectares e a uma de um milhão.
- ⚠️ Cada linha é a estimativa da safra do **ano inteiro** vigente no mês, não o colhido no mês. Somar 12 meses multiplica a produção por 12.

### 🧭 Decisão 16 — Quais séries do BCB e como torná-las mensais?

|Série (código SGS)|Original|Virou mensal como|
|---|---|---|
|Dólar PTAX (1)|diária|média do mês **e** valor do último dia|
|IPCA cheio (433)|mensal|direto|
|Selic meta (432)|diária|valor no fim do mês|
|Selic efetiva (11)|dias úteis|composta no mês|
|IGP-M (189)|mensal|direto|

- 💡 **Por quê:** sem controlar dólar e inflação geral, o modelo poderia atribuir ao clima o que é só perda de valor da moeda. O IPCA cheio também gera o alvo "inflação da comida acima da inflação geral" (Decisão 20).
- ⚠️ **Armadilha:** pedindo mais de 10 anos de uma vez, a API responde "OK" mas **devolve os dados cortados**. O coletor pede em blocos de 10 anos e confere o período devolvido. Valores conferidos com números oficiais (dólar médio de março/2020 = R$ 4,88).

### 🧭 Decisão 17 — Quais combustíveis e quais preços manter?

A extração da ANP tem 8 produtos e dois preços: o que o posto **paga** à distribuidora e o que **cobra** do consumidor.

|Item|Decisão|Motivo medido|
|---|---|---|
|Diesel, Diesel S10, Gasolina, Etanol|✅ manter|cobrem a janela inteira nas 16 UFs|
|GLP (13 kg)|✅ manter|é o gás de cozinha, parte da própria cesta do IPCA|
|Diesel S50|❌ descartar|só existe em 2012 (73 linhas)|
|Gasolina aditivada|❌ descartar|começa só em out/2020 e anda junto com a comum (correlação ~0,99)|
|GNV|❌ descartar|falta em 45 % da grade; combustível de carro urbano, não de frete|
|Preço de **compra** do posto|❌ descartar|a ANP parou de publicar em 2021: a coluna "morre" no meio da série|
|Preço de **venda** ao consumidor|✅ manter|é contínuo|

- 💡 **Por que combustível numa tabela sobre comida:** o diesel é o frete de toda a comida que sai da lavoura, o GLP é o custo de cozinhar, e, ao contrário de dólar e Selic, o preço **muda de um estado para outro**.
- ⚠️ **Pendência:** é a única fonte **sem script de download** no repositório (o CSV foi extraído à parte).

---

# Parte 3 — Padronização e junção

Com as seis tabelas baixadas, a pergunta passou a ser como colocar tudo na mesma linha. Apareceram três armadilhas, todas do tipo que **não dá erro nenhum**: só produzem um número errado.

### 🧭 Decisão 18 — Em que formato guardar o mês?

O mês chegou como texto `"2015-01"` (IPCA, clima, seca), data `2015-01-01` (safra, BCB) e período.

- 🔀 **Opções:** texto · data · **`Period[M]`**.
- ✅ **Escolha:** todo mês vira `Period[M]`; a UF é sempre sigla de 2 letras maiúsculas.
- 💡 **Por quê:** o jeito "óbvio" (tudo para texto) faz `"2015-01"` nunca encontrar `"2015-01-01"`, e a coluna da safra volta **inteira vazia** sem aviso (no dado real, **0 de 3.726** preenchidos). `Period[M]` não tem dia, então não há divergência possível.

### 🧭 Decisão 18b — Linhas que se multiplicam (pivotar antes de juntar)

A safra tem uma linha por produto em cada UF-mês. Juntando direto com 11 produtos, a tabela iria de **3.726 para 40.986 linhas**, e a taxa de preenchimento (79,6 %) ainda pareceria saudável.

- ✅ **Escolha:** toda fonte com mais de uma linha por UF-mês é **pivotada antes** de juntar, e um verificador roda depois de **cada** junção (`src/tratamento/chaves.py`): `padroniza_chaves`, `valida_chaves` e `checa_join` (compara linhas antes e depois e a taxa de preenchimento; **interrompe a execução** se as linhas mudaram ou nada casou).
- 💡 **Por quê:** transforma um erro silencioso num erro que aparece.

### 🧭 Decisão 19 — Quais itens do IPCA entram?

São 40 códigos, e nem todos existem no período inteiro em todas as UFs.

- ✅ **Escolha:** os **17 códigos com cobertura completa** (2.088 linhas cada; o 18º já cai para 92 %), cada um em duas colunas: `ipca_var_*` e `ipca_peso_*`. Grupo: Alimentação e bebidas (o alvo). Subgrupos: farinhas, açúcares, hortaliças, carnes, carnes industrializadas, aves e ovos, leites e derivados. Subitens: arroz, batata-inglesa, tomate, frango inteiro, frango em pedaços, leite longa vida, pão francês, óleo de soja, café moído.
- ⚠️ Os itens estão em **três níveis que se encaixam** (frango inteiro ⊂ aves e ovos ⊂ alimentação). **Não somar os pesos.**

### 🧭 Decisão 20 — Qual número usar como alvo?

- 🔀 **Opções:** variação do mês · acumulada em 12 meses · acima da inflação geral.
- ✅ **Escolha:** **as três**, em colunas separadas: `ipca_var_alimentacao` (alvo principal), `ipca_var_alimentacao_acum12` (suaviza a sazonalidade, que troca de sinal quase todo mês) e `ipca_var_alimentacao_relativa` (alimentos − IPCA cheio: quanto subiu **além** da inflação geral).
- ⚠️ O acumulado é **multiplicado, não somado** (12 altas de 1 % dão 12,68 %, não 12 %).

### 🧭 Decisão 21 — Como transformar ~700 estações num número por UF?

- 🔀 **Opções:** soma (sem sentido físico: ~100 estações do RS dariam ~50.000 mm) · média (um sensor quebrado puxa a UF toda) · **mediana** · média ponderada pela produção agrícola (mais fiel, mas é trabalho à parte: T-022).
- ✅ **Escolha:** **mediana**, descartando antes as estação-mês com **< 70 % dos dias medidos** (22,8 % das estação-mês). Tabela traz `clima_n_estacoes`.
- **Ficaram de fora** a máxima e a mínima **absolutas**: a mediana dos recordes de cada estação não descreve nem o extremo nem o típico.
- ⚠️ Em RR, AP e AC a mediana sai de 1 a 3 estações. A ponderação pela produção **ainda não foi feita**.

### 🧭 Decisão 22 — Quais medidas de safra levar?

O LSPA tem 5 medidas por produto: área plantada, área colhida, produção, rendimento e **revisão %**.

- ✅ **Escolha:** 2 × 11 = **22 colunas** (`safra_producao_t_*` e `safra_revisao_pct_*`). As outras três ficam em `data/interim/`.
- 💡 **Por quê:** a revisão é o que **se mexe quando a lavoura quebra**; o nível quase não muda dentro do ano. Levar 55 colunas traria mais ruído que informação.
- ⚠️ O maior valor bruto de revisão passava de **15 milhões %** (divisão por estimativa anterior quase zero). Limitado a **±50 %** (winsorização): 99,1 % dos valores intactos.

### 🧭 Decisão 23 — O que fazer com os vazios da safra?

- ✅ `safra_producao_t_*`: vazio vira **0** (a UF não planta o produto; zero tonelada é verdade, e a grade do LSPA é completa).
- ✅ `safra_revisao_pct_*`: **continua vazio** (zero diria "a estimativa não mudou", outra afirmação). Também é vazia em **todo janeiro**, sem mês anterior na mesma safra.

### 🧭 Decisão 24 — O que fazer com os meses em que a UF não era monitorada pela ANA?

O Monitor de Secas começou no Nordeste e chegou aos outros estados aos poucos. Dos 3.726 UF-meses, **1.358 (36 %)** são anteriores à entrada da UF. Cobertura de seca medida nas 16 UFs do alvo: 65,8 % (desde 2015-01), 77,9 % (2018-01), **90,5 % (2020-01)**, 100 % (2024-01).

- 🔀 **Opções:** preencher com 0 · apagar as linhas · **manter vazio e criar `seca_monitorado`**.
- ✅ **Escolha:** manter vazio + `seca_monitorado`.
- 💡 **Por quê:** o vazio significa "ninguém estava medindo", não "não houve seca". Com zero, o modelo aprenderia que o Sul não tinha seca antes de 2020 e confundiria "seca" com "ser do Nordeste" (até 2018 só o Nordeste tem dado).
- ⚠️ Quem usar seca deve **filtrar por `seca_monitorado`** ou **recortar a partir de 2020-01**.

### 🧭 Decisão 25 — Como colocar uma série nacional numa tabela por UF?

- ✅ **Escolha:** **repetir** o valor do Brasil em todas as UFs no mesmo mês (5 colunas: IPCA cheio, dólar médio, dólar no fim do mês, Selic e IGP-M).
- ⚠️ Essas colunas são idênticas entre UFs: explicam variação **no tempo**, nunca diferença **entre estados**.

### 🧭 Decisão 26 — Por qual tabela começar e que junção usar?

- 🔀 **Opções:** começar pelo IPCA com INNER JOIN (cada junção descarta linhas sem avisar; no fim não se sabe o que se perdeu) · **calendário completo + só LEFT JOIN**.
- ✅ **Escolha:** calendário-espinha de **27 UFs × 138 meses = 3.726 linhas** + 5 LEFT JOINs: IPCA preenche 56,0 % (alvo só em 16 UFs), clima 96,9 %, safra 100 %, seca 63,6 %, macro 100 %. `checa_join` após cada junção: as 3.726 linhas se mantêm. Filtro final: só onde há alvo.
- 💡 **Por quê:** nada some no meio; a perda acontece num único filtro, no fim, e é contada.

### 🧭 Decisão 27 — Como nomear as colunas para não haver conflito?

- 🔀 **Opções:** deixar o pandas criar `_x`/`_y` · **prefixo por fonte antes de juntar**.
- ✅ **Escolha:** `ipca_`, `clima_`, `safra_`, `seca_`, `macro_` (depois `comb_`). Colunas repetidas sem utilidade (`ano`, `mes`) foram **descartadas**, não renomeadas.
- 💡 **Por quê:** o nome da coluna já diz de onde ela veio; `temp_media_x` não diz nada.

### 🧭 Decisão 28 — Quais linhas ficam na tabela final?

- ✅ **Escolha:** só as com alvo: 16 UFs, nos meses em que o IPCA existe. Sem alvo, não há o que explicar.
- **A conta:** 16 × 138 = 2.208; AC, MA e SE só entram em 2018-05 (faltam 40 meses cada, 120 no total) → **2.088 linhas × 89 colunas**.
- ⚠️ Variáveis defasadas devem ser calculadas **no calendário completo, antes deste filtro** (`data/processed/calendario_uf_mes.parquet`), senão os primeiros meses de AC, MA e SE ficam sem passado.

---

# Parte 4 — Combustíveis

Entraram depois, **acrescentados à tabela que já estava pronta**, com decisões novas e uma armadilha que o verificador de junção não detecta.

### 🧭 Decisão 29 — O que fazer com linhas repetidas na fonte?

A ANP traz **182 casos** de mesma UF, mês e produto repetidos (quase todos em abril de 2026, duas rodadas de coleta; o resto são linhas soltas com um único posto).

- 🔀 **Opções:** apagar e ficar com uma (qual?) · média simples · **média ponderada pelo número de postos** (`quantidade_registros`).
- ✅ **Escolha:** média ponderada.
- 💡 **Por quê:** uma regra resolve os dois casos. Exemplo real, GLP no Pará em fev/2008: linha solta de 1 posto a R$ 3,00 e coleta normal de 674 postos a R$ 32,95. Média simples = R$ 17,98 (1 posto vale o mesmo que 674); ponderada = R$ 32,91. A média simples errava o mês em **45 %**.

### 🧭 Decisão 30 — Como calcular variação mensal numa série com meses faltando?

A ANP não tem coleta em alguns meses (33 dos 138 para líquidos). Ex.: gasolina em SP, 2018, sem abril a junho.

- ✅ **Escolha:** calcular variações **só depois de completar a grade de meses**. O mês ausente vira linha vazia, e a variação dele (e a do mês seguinte) nasce vazia.
- 💡 **Por quê:** com `shift(1)` sobre as linhas existentes, julho aparece com alta de ~7 % "no mês", mas é comparado com **março**. Não é erro de conta, é erro de rótulo, e nenhum verificador pega.

### 🧭 Decisão 31 — Preencher os meses sem coleta?

- 🔀 **Opções:** interpolar · repetir o último preço (_forward fill_) · zero · **manter vazio e marcar**.
- ✅ **Escolha:** vazio + **duas** marcas: `comb_observado_liquidos` (diesel, gasolina ou etanol) e `comb_observado` (qualquer produto, inclusive GLP).
- 💡 **Por quê:** interpolar inventaria preço em ~23 % das linhas e apagaria justamente os choques. São duas marcas porque a ANP faz duas pesquisas com falhas em meses diferentes: líquidos faltam em 33 meses, GLP em 15, e só 10 meses não têm nada.

### 🧭 Decisão 32 — Refazer a junção inteira ou acrescentar?

- ✅ **Escolha:** **acrescentar**, com um único LEFT JOIN sobre a tabela de 2.088 linhas e a mesma verificação.
- **Conferido:** 2.088 → 2.088 linhas; 89 → 108 colunas (19 novas); as 89 anteriores **idênticas**.

### 🧭 Decisão 33 — Como saber se os preços agregados da ANP estão certos?

Havia uma segunda extração da mesma base, mais detalhada (**96.049 coletas** posto a posto), mas cheia de buracos.

- 🔀 **Opções:** usar como fonte · ignorar · **usar como testemunha**.
- ✅ **Escolha:** testemunha. Para cada UF-mês com ≥ 20 coletas, comparou-se a média das coletas com o preço agregado: 1.149 UF-meses, correlação > 0,99 em todos os produtos, erro típico (mediana do erro absoluto) de **0,61 %**.
- 💡 **Por quê:** duas extrações dando o mesmo número é uma validação forte, e raramente existe uma segunda medição.

---

# Parte 5 — Documentação do resultado

**Arquivo final:** `data/processed/fato_alimentos_combustiveis_uf_mes.parquet` · 2.088 linhas · 108 colunas · 16 UFs · 2015-01 a 2026-06 · chave `(sigla_uf, ano_mes)` sem repetição.

### 🧭 Decisão 34 — Como documentar o que cada coluna significa?

- ✅ **Escolha:** **dicionário de variáveis gerado pelo próprio código**, uma linha por coluna (descrição, unidade, fonte, grão original, % de vazios e, para **toda** coluna com vazio, **o que o vazio significa**). O código falha se alguma coluna com mais de 40 % de vazios ficar sem justificativa.
- 108 colunas documentadas, 61 sem nenhum vazio. Colunas por família: identificação 6 · IPCA 36 · clima 11 · safra 22 · seca 9 · macro 5 · combustíveis 19.

**O que cada vazio significa**

|Família|% vazio|O vazio significa|Pode virar 0?|
|---|---|---|---|
|`seca_*`|34 a 38 %|a UF não era monitorada|**Não** (inventaria ausência de seca)|
|`comb_preco_*`|~23 % (GLP ~10 %)|mês sem pesquisa da ANP|**Não** (seria combustível de graça)|
|`comb_var_mm_*` / `comb_var12_*`|~30 % / ~39 %|falta o mês atual ou o de comparação|**Não**|
|`safra_revisao_pct_*`|9 a 53 %|é janeiro, ou a UF não planta|**Não** (0 = "não mudou")|
|`safra_producao_t_*`|0 %|(já virou 0: a UF não planta)|já virou|
|`clima_*`|0,3 %|nenhuma estação passou do corte de 70 %|Não|
|`ipca_var_alimentacao_acum12`|1,6 %|primeiros meses de AC, MA e SE, sem 12 meses de histórico|Não|

**Conferência com eventos históricos** (uma junção pode rodar e estar errada):

- Seca do Ceará (jan/2017): 100 % do estado em seca grave ou pior, severidade 4,52 de 5.
- Alimentos na pandemia: pico de 18,1 % em 12 meses (nov/2020).
- Estação chuvosa: chuva mediana de 226 mm em janeiro contra 13 mm em agosto (Norte e Centro-Oeste).
- Diesel após a invasão da Ucrânia: +62 % em 12 meses em jul/2022 e −34 % em jul/2023.

**Dois primeiros sinais (pontos de partida, não conclusões):** o diesel antecipa a comida (correlação 0,42 no mesmo mês, **0,49 com o diesel adiantado 4 meses**); o combustível varia entre estados, o dólar não (o Acre paga em média 20 % a mais pelo diesel que a mediana do país, o Paraná 5 % a menos). Correlação não é causa.

---

# O que ainda falta

Esta etapa **juntou** os dados; não fez exploração nem limpeza profunda.

1. **Exploração e limpeza profunda** (T-030): distribuições, extremos, sazonalidade, correlações.
2. **Variáveis defasadas** (T-023): chuva, seca e diesel de 1 a 6 meses antes, calculadas no calendário completo, antes do filtro.
3. **Clima ponderado pela produção** (T-022): o preço do feijão em SP depende da chuva onde o feijão é plantado.
4. **Pendências de coleta:** script de download da ANP no repositório; investigar os 33 meses sem coleta; avaliar o NASA POWER para os buracos do INMET; CEPEA/ESALQ.