
> Registro de tudo o que **pesquisamos, avaliamos e não usamos** (ou adiamos), com o motivo. Serve para mostrar que as escolhas foram comparadas, não aleatórias. A narrativa completa, em ordem, está em [[Passo a passo das decisões]]; o resumo das fontes em [[Decisões e Justificativas do Projeto]] e [[Resumo]].

**Legenda:** ❌ descartada · 🟡 usada com ressalva · ⏸️ adiada · 🔁 trocada após erro

---

## 1. Temas, fontes e variável-alvo

|Alternativa|O que era|Decisão|Motivo|Ref.|
|---|---|---|---|---|
|Ondas de calor na Europa|tema candidato|❌|menos dados cruzáveis e menos relevante para o grupo que o tema escolhido|Dec. 1|
|Impactos do El Niño na economia|tema candidato|❌|idem|Dec. 1|
|DataSUS (e fontes parecidas)|fonte com a qual o grupo já teve dificuldade|❌|evitada de propósito|Dec. 1|
|**Cesta básica DIEESE**|valor da cesta em R$, 17 capitais|❌|relatórios em **PDF** com layout que muda entre anos (ler era a tarefa mais arriscada, T-011); preço por produto fechado desde 2018; valor em R$ tem tendência e exigiria deflacionar|Dec. 2|
|**CONAB**|safra, estoques e custos|❌|**anual por ano-safra** (ex.: 2024/25); virar mês exige suposições, gera degraus e autocorrelação espúria; o LSPA já mede o mesmo mês a mês. Única ideia aproveitável (estoque/consumo nacional defasado) fica só como ideia futura|Dec. 3|
|**CEPEA/ESALQ**|preços na origem e frete|⏸️|estava na proposta; ficou para depois|Dec. 3|
|**ANA (Monitor de Secas)**|índice de seca por UF|🟡|cobre o país inteiro só a partir de 2023; usar com `seca_monitorado` ou recorte em 2020-01|Dec. 3, 24|

## 2. Coleta

|Alternativa|O que era|Decisão|Motivo|Ref.|
|---|---|---|---|---|
|Só a tabela 7060 do SIDRA|IPCA a partir de 2020|❌|perderíamos 2015–2019|Dec. 7|
|Tabela 7062 do SIDRA|emendar com outra tabela|❌|é o **IPCA-15**, outro índice|Dec. 7|
|Nível N7 apenas (ou N3 "UF")|só regiões metropolitanas|❌|N3 não existe (erro 404); só N7 perde Brasília, Goiânia, Campo Grande, São Luís, Aracaju e Rio Branco|Dec. 7|
|Limpar o SIDRA apagando o `-` do texto|primeira versão do coletor|🔁|transformou **deflação em inflação** (0 negativos contra 32.696); dados baixados de novo|Dec. 8|
|Agrupar itens do IPCA pelo nome|em vez do código|❌|o IBGE renomeia itens no meio da série (40 códigos, 42 nomes)|Dec. 9|
|Descompactar todo o INMET|1,27 GB|❌|ocuparia vários GB|Dec. 10|
|Ler colunas do INMET por posição|em vez do nome|❌|o formato mudou em 2019|Dec. 10|
|Agregar hora → mês direto|sem passar pelo dia|❌|perde sequência seca e calor extremo|Dec. 11|
|Direção do vento|variável do INMET|❌|é ângulo: média de 350° e 10° dá 180°|Dec. 11|
|Preencher INMET com normal climatológica|imputação|⏸️|esconderia a incerteza justamente em 2021|Dec. 12|
|NASA POWER|satélite em grade, sem falha de estação|⏸️|pendência para os buracos do INMET|Dec. 12|
|CSV do site da ANA|arquivo pronto|❌|não existe: a página monta a tabela no navegador|Dec. 13|
|Mapas da ANA + geoprocessamento|shapefiles, `geopandas`|❌|desnecessário: a ANA já agrega município → UF|Dec. 13|
|Primeira / maior / média das versões da ANA|quando o mês é revisado|❌|versões antigas têm escala ×100 e valores de teste (`123456`)|Dec. 14|
|Média dos rendimentos das safras|em vez de recalcular|❌|dá o mesmo peso a safra de mil e de um milhão de hectares|Dec. 15|
|BCB em uma única requisição|vários anos de uma vez|❌|a API devolve os dados cortados sem avisar; usam-se blocos de 10 anos|Dec. 16|
|Diesel S50|combustível da ANP|❌|só existe em 2012 (73 linhas)|Dec. 17|
|Gasolina aditivada|combustível da ANP|❌|começa em out/2020; correlação ~0,99 com a comum|Dec. 17|
|GNV|combustível da ANP|❌|falta em 45 % da grade; é de carro urbano, não de frete|Dec. 17|
|Preço de **compra** do posto|ANP|❌|a ANP parou de publicar em 2021|Dec. 17|

## 3. Estrutura e junção

|Alternativa|O que era|Decisão|Motivo|Ref.|
|---|---|---|---|---|
|Município × mês|grão da tabela|❌|não existe no IPCA nem na seca|Dec. 4|
|Região metropolitana × mês|grão da tabela|❌|não é comum a todas as fontes|Dec. 4|
|Brasil × mês|grão da tabela|❌|joga fora a variação regional, que é a pergunta|Dec. 4|
|Formato longo|uma linha por item/produto|❌|modelos esperam "uma linha = um estado num mês"|Dec. 4|
|Cortar o período antes de calcular acumulados||❌|os 12 primeiros meses ficariam vazios|Dec. 5|
|Cada um com seus caminhos||❌|5 pessoas; difícil refazer etapas|Dec. 6|
|Mês como texto|`"2015-01"`|❌|não casa com `"2015-01-01"`; safra voltou vazia (0 de 3.726)|Dec. 18|
|Juntar safra no formato longo|sem pivotar|❌|3.726 → 40.986 linhas|Dec. 18b|
|Incluir todos os 40 itens do IPCA||❌|nem todos existem em todas as UFs e meses (o 18º já cai para 92 %); entraram 17|Dec. 19|
|Somar os pesos do IPCA||❌|itens em 3 níveis que se encaixam: contaria o mesmo item duas vezes|Dec. 19|
|Acumulado de 12 meses por soma||❌|12 altas de 1 % = 12,68 %, não 12 %|Dec. 20|
|Soma / média entre estações|agregação do clima|❌|soma sem sentido físico; média puxada por sensor com defeito|Dec. 21|
|Média ponderada pela produção|agregação do clima|⏸️|mais fiel, mas é trabalho à parte (T-022)|Dec. 21|
|Temperaturas máx./mín. **absolutas**|variáveis do INMET|❌|a mediana dos recordes não descreve nem o extremo nem o típico|Dec. 21|
|Levar as 5 medidas da safra (55 colunas)||❌|mais ruído que informação; só produção e revisão (22 colunas)|Dec. 22|
|Preencher produção ou revisão da safra só com 0 / só com vazio||❌|"não planta" = 0 t é verdade; revisão inexistente não é 0|Dec. 23|
|Preencher seca com 0 / apagar linhas|meses não monitorados|❌|o modelo confundiria "seca" com "ser do Nordeste"|Dec. 24|
|IPCA + INNER JOIN|começar pelo alvo|❌|cada junção descartaria linhas sem avisar|Dec. 26|
|Sufixos `_x` / `_y`|nomes do pandas|❌|não dizem de onde a coluna veio|Dec. 27|
|Manter as 27 UFs na tabela final||❌|sem alvo não há o que explicar|Dec. 28|

## 4. Combustíveis

|Alternativa|O que era|Decisão|Motivo|Ref.|
|---|---|---|---|---|
|Apagar linhas repetidas|ficar com uma|❌|não há critério para escolher qual|Dec. 29|
|Média simples das repetidas||❌|1 posto pesava o mesmo que 674; erro de até 45 %|Dec. 29|
|Variação sobre as linhas existentes|`shift(1)` direto|❌|compara março com julho e chama de "variação mensal"|Dec. 30|
|Interpolar / forward fill / zero|meses sem coleta|❌|inventaria preço em ~23 % das linhas|Dec. 31|
|Refazer a junção inteira||❌|acrescentar com um LEFT JOIN mantém as 89 colunas idênticas|Dec. 32|
|Usar a extração detalhada como fonte|96.049 coletas|❌|cheia de buracos; serve como **testemunha** (erro típico de 0,61 %)|Dec. 33|

---

> [!note] Como usar na apresentação Para cada fonte "não usada", a frase-modelo é: **o que era → por que parecia útil → o problema medido → o que usamos no lugar**. Exemplo (CONAB): _tem estoques e balanço de oferta, mas é anual por ano-safra; converter para mês criaria degraus artificiais; o LSPA entrega o mesmo fenômeno mês a mês por UF._