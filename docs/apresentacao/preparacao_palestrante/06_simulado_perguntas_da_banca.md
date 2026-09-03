# 🎯 Módulo 6: Simulado de Alta Tensão — Perguntas Profundas da Banca

Este documento reúne **15 perguntas extremamente desafiadoras, técnicas e conceituais** formuladas no padrão de arguição do Prof. Alexandre Delbem e de bancas de Ciência de Dados do ICMC-USP, acompanhadas das **respostas exatas, fundamentadas e memorizáveis** para o palestrante.

---

### Pergunta 1: Representatividade Espacial Urbana vs. Rural
> **Banca:** *"O alvo de vocês é a inflação ao consumidor, medida em supermercados e feiras de 16 capitais e regiões metropolitanas. No entanto, o clima e as lavouras de soja e milho ocorrem no interior dos estados. Como vocês justificam metodologicamente cruzar o clima do interior com o preço da capital sem cometer uma falácia ecológica de representatividade espacial?"*

**Resposta do Palestrante:**  
"A pergunta toca no ponto metodológico central do projeto. Reconhecemos integralmente essa assimetria: o grão da observação do IPCA é urbano, enquanto o grão da produção agrícola é rural.  
Nós defendemos essa agregação em dois níveis:
1. **Nível Institucional e de Mercado Integrado:** A Unidade da Federação (UF) é a menor unidade político-econômica comum no Brasil que compartilha a mesma malha tributária (ICMS de combustíveis e alimentos), os mesmos entrepostos atacadistas reguladores (CEASAs estaduais) e a mesma rede primária de rodovias estaduais de escoamento. O preço na capital reflete o custo logístico e de safra do estado como um todo.
2. **Evolução Técnica Planejada (Ticket T-022):** Para a etapa de engenharia de features finas, já deixamos arquitetada e documentada a ponderação espacial das 701 estações do INMET pela produção agrícola municipal apurada pela PAM (Pesquisa Agrícola Municipal). Em vez de uma mediana territorial pura da UF, o choque climático será calculado como a média das estações ponderada pela área colhida de cada cultura nos municípios do entorno.  
Assim, mantemos a comparabilidade em `UF × mês` sem ignorar a geografia econômica do campo."

---

### Pergunta 2: Descoberta e Mitigação do Bug do Sinal do IPCA
> **Banca:** *"No slide 5 vocês afirmam que uma limpeza de dados inverteu o sinal de todas as deflações do IPCA, mas que nenhum erro foi disparado. Como vocês descobriram essa falha se o código executava normalmente com código 0 e como garantiram que ela nunca mais se repetirá?"*

**Resposta do Palestrante:**  
"Descobrimos através de uma rotina de análise exploratória de distribuição univariada. Ao inspecionar os momentos estatísticos da série preliminar do IPCA, calculamos o valor mínimo (`df['valor'].min()`) e identificamos que ele era rigorosamente `0.00%`. Em 83.383 observações históricas de inflação mensal brasileira entre 2006 e 2026, a contagem de meses com deflação era exatamente zero.  
Isso é empiricamente impossível na economia brasileira, onde choques de supersafra de hortaliças e cortes de tributos produzem deflações sazonais frequentes no atacado e varejo.  
Rastreando o código em [`src/coleta/sidra_ipca/01_ibge_ipca_download.py`](../../src/coleta/sidra_ipca/01_ibge_ipca_download.py), encontramos a linha onde `.str.replace('-', '')` havia sido usado para apagar o marcador textual de não-publicado do SIDRA, levando junto o sinal negativo dos números.  
Para garantir que o bug nunca mais retorne, introduzimos uma asserção de regressão permanente no pipeline de tratamento ([`24_junta.py:411`](../../src/tratamento/24_junta.py#L411)):  
`assert (fato['ipca_var_alimentacao'] < 0).sum() > 0`  
Se qualquer alteração futura apagar o sinal de menos, o pipeline aborta a execução instantaneamente."

---

### Pergunta 3: Agregação Climática — Mediana vs. Média
> **Banca:** *"Por que vocês utilizaram a mediana para agregar as estações meteorológicas de uma mesma UF no mês em vez da média aritmética tradicional ou de uma interpolação por Krigagem?"*

**Resposta do Palestrante:**  
"Por duas razões fundamentais: robustez a falhas de sensores e assimetria de distribuição.  
Primeiro, estações meteorológicas automáticas em campo sofrem frequentes falhas eletromecânicas: sensores de temperatura travam temporariamente em fundos de escala anômalos (ex: 45 °C) ou pluviômetros acumulam sujeira e marcam 0 mm em dias de tempestade. A média aritmética tem um ponto de quebra (*breakdown point*) de $0\%$: basta um único sensor avariado para deslocar a média de todo o estado. A mediana possui ponto de quebra de $50\%$, sendo imune a falhas pontuais.  
Segundo, a precipitação pluviométrica não segue uma distribuição normal gaussiana; ela possui distribuição assimétrica positiva, frequentemente modelada por distribuições Gama ou Tweedie. Nesses cenários, a mediana é a medida de tendência central mais representativa do clima típico enfrentado pelo estado no mês."

---

### Pergunta 4: Winsorização da Revisão da Safra em ±50%
> **Banca:** *"No slide 8 vocês mencionam que winsorizaram a revisão da safra em ±50%. Por que truncar os dados em vez de aplicar uma transformação de escala padrão como Logaritmo ou Box-Cox?"*

**Resposta do Palestrante:**  
"A revisão de safra é uma taxa percentual de variação entre duas estimativas sucessivas: ela pode ser tanto positiva quanto negativa. Uma quebra de colheita por seca severa gera revisões de $-30\%$ ou $-40\%$.  
Transformações logarítmicas ou de Box-Cox são estritamente definidas apenas para valores estritamente positivos ($x > 0$). Tentar aplicar logaritmo exigiria adicionar uma constante arbitrária ($\log(x + c)$), o que distorceria a interpretabilidade econômica do zero (que significa 'estimativa mantida').  
Além disso, a patologia dos dados brutos era extrema: em culturas secundárias com produção próxima de zero, a revisão percentual atingia **15 milhões %** decorrente de divisão por quase-zero.  
Ao analisar a distribuição empírica, constatamos que **96,6% das revisões reais de safra cabem no intervalo $[-20\%, +20\%]$**. A winsorização em $\pm 50\%$ preservou **99,1% dos dados originais intactos**, atuando exclusivamente nas caudas numéricas anômalas e mantendo o sinal e a direção dos choques agrícolas perfeitamente interpretáveis."

---

### Pergunta 5: Semântica dos Nulos e Recusa de Imputação Cega
> **Banca:** *"Vocês têm mais de 34% de valores ausentes no Monitor de Secas da ANA e 23% nos combustíveis da ANP. Por que vocês não utilizaram algoritmos de imputação multivariada consagrados como MICE, MissForest ou KNN Imputer para entregar uma matriz 100% densa?"*

**Resposta do Palestrante:**  
"Porque em Ciência de Dados aplicada a políticas públicas e causalidade, **imputação estatística cega sobre dados estruturalmente ausentes inventa uma realidade que não existiu**.  
O caso do Monitor de Secas é o exemplo mais didático: o programa da ANA foi criado em 2014 no semiárido nordestino e foi expandido progressivamente até alcançar o Sul e Sudeste em 2020. Os valores `NaN` no Paraná ou em São Paulo em 2016 não representam falha aleatória (*Missing Completely at Random - MCAR*); eles significam que **o estado simplesmente não era monitorado pelo órgão**.  
Se aplicássemos KNN ou MissForest, o algoritmo atribuiria valores sintéticos ao Sul pré-2020 baseando-se no comportamento dos estados monitorados (o Nordeste!), ensinando aos modelos estatísticos que secas no Sul são correlacionadas com a dinâmica do semiárido.  
Para preservar a integridade científica, mantivemos os `NaN` ontológicos, documentamos a justificativa de 100% das colunas no dicionário de dados e fornecemos flags booleanas explícitas (`seca_monitorado` e `comb_observado_liquidos`) para que o cientista de dados recorte o período denso ($\ge$ 2020) ou controle a incerteza analítica."

---

### Pergunta 6: Topologia dos Joins — Por que não INNER JOIN?
> **Banca:** *"Por que criar uma espinha cartesiana de 3.726 linhas com 5 LEFT JOINs para depois filtrar para 2.088 linhas, em vez de fazer INNER JOIN diretamente entre as bases?"*

**Resposta do Palestrante:**  
"Porque o `INNER JOIN` é o mecanismo clássico de **perda silenciosa de dados**.  
Se fizéssemos `INNER JOIN` sucessivo entre as 6 fontes e uma delas tivesse uma falha de coleta de 3 meses em determinado ano, o `INNER JOIN` descartaria silenciosamente aqueles meses de todas as outras fontes sem emitir nenhum aviso ou log.  
Ao utilizarmos a espinha dorsal de calendário (`calendario_uf_mes.parquet`, $27 \times 138 = 3.726$ linhas) combinada com `LEFT JOIN`, nós garantimos três salvaguardas:
1. A contagem de 3.726 linhas atua como um invariante relacional estrito testado por `checa_join()` após cada etapa.
2. Monitoramos a taxa de match exata de cada instituição de forma desacoplada (ex: Clima 96,9%, Safra 100%, Seca 63,6%).
3. O descarte das 11 UFs sem IPCA e dos períodos preliminares ocorre em um único filtro final tardio, onde a perda amostral é matematicamente contabilizada e justificada."

---

### Pergunta 7: Lacunas da ANP (33 Meses sem Líquidos)
> **Banca:** *"A base de combustíveis da ANP tem 33 meses sem coleta de líquidos ao longo dos 138 meses da janela. Isso não invalida a utilização dessa fonte para explicar séries temporais contínuas?"*

**Resposta do Palestrante:**  
"Não invalida, pois trata-se de uma lacuna temporal homogênea e identificável.  
Primeiro, diagnosticamos que a falta de dados nos 33 meses ocorreu simultaneamente em todas as 27 UFs do país: isso comprova que não foi uma perda aleatória de dados de certos estados, mas sim uma interrupção nas publicações de relatórios tabulares de derivados de petróleo pela ANP em determinados períodos históricos.  
Segundo, nos 105 meses em que a pesquisa de campo foi realizada, a cobertura nas 16 UFs do nosso alvo é de **95,8% de dados válidos**.  
Terceiro, nós criamos a flag de observabilidade `comb_observado_liquidos`. Ao treinar modelos de defasagem (como demonstrado no Slide 14), o algoritmo filtra estritamente os períodos observados, garantindo que o sinal de repasse de frete seja estimado com máxima precisão."

---

### Pergunta 8: Independência e Robustez da Base Testemunha
> **Banca:** *"No slide 10 vocês apresentam uma validação com 96.049 coletas individuais de postos com erro mediano de 0,61%. Como vocês garantem que essa base testemunha é verdadeiramente independente e não possui o mesmo viés da base agregada?"*

**Resposta do Palestrante:**  
"Elas são independentes na camada de processamento e extração.  
O arquivo oficial `combustivel.csv` foi obtido a partir de séries agregadas mensais consolidadas pela diretoria técnica da ANP. Já o arquivo `results-*.csv` foi extraído diretamente de um log bruto de coletas em nível de transação de posto de combustível, contendo data exata de coleta, CNPJ do posto revendedor e preço unitário na bomba em 551 municípios.  
O cálculo que realizamos não foi ler um valor pré-calculado: nós escrevemos em Python a média ponderada do zero sobre as 96 mil transações atômicas ([`25_combustiveis.py:331-353`](../../src/tratamento/25_combustiveis.py#L331-L353)) e a confrontamos contra o valor consolidado.  
Obter correlação de Pearson superior a $0,993$ em todos os cinco combustíveis e viés médio quase nulo de $-0,07\%$ comprova que o dado consolidado que alimenta a tabela analítica é matematicamente fidedigno ao que o consumidor brasileiro pagou nas bombas."

---

### Pergunta 9: Escolha Técnica do `pd.Period[M]` vs. `Timestamp`
> **Banca:** *"Por que vocês insistiram tanto no uso do tipo `pd.Period[M]` do Pandas no módulo de chaves em vez de simplesmente padronizar as datas como `Timestamp` com o dia 01?"*

**Resposta do Palestrante:**  
"Porque `Timestamp` é ontologicamente um ponto discreto no tempo com precisão de nanosegundos (carrega ano, mês, dia, hora, minuto e fuso horário).  
Se uma tabela de entrada registrar o mês como o primeiro dia (`2020-01-01`), outra registrar como o último dia útil (`2020-01-31`) e outra como string (`2020-01`), um merge baseado em `Timestamp` falhará silenciosamente ou exigirá manipulações contínuas de normalização de dias e timezones.  
O `pd.Period[M]` representa um intervalo fechado que abrange a totalidade do mês civil (`Period('2020-01', 'M')`). Nele, o conceito de 'dia' não existe. Isso fecha permanentemente a porta para qualquer incompatibilidade de formato e impede discrepâncias de junção no Pandas."

---

### Pergunta 10: Causalidade vs. Correlação na Defasagem de 4 Meses
> **Banca:** *"No slide 14 vocês mostram que o diesel com defasagem de 4 meses tem a maior correlação com a inflação de alimentos. Mas correlação não é causalidade. Como provar que essa defasagem não é um mero reflexo do ciclo econômico ou da desvalorização do dólar?"*

**Resposta do Palestrante:**  
"Essa é uma questão crucial de econometria aplicada. Nós endereçamos isso através de três defesas metodológicas:
1. **Estrutura Temporal Precedente:** Ao adiantar o diesel em 4 meses em relação ao alimento, eliminamos a possibilidade de causalidade reversa contemporânea: a variação do preço da alface em maio de 2024 não tem como causar a cotação do óleo diesel em janeiro de 2024.
2. **Isolamento do Componente Específico via Alvo Relativo:** Nós construímos a métrica `ipca_var_alimentacao_relativa`, que subtrai a inflação geral do país (`macro_ipca_mm`) da inflação alimentar local. O pico de correlação aos 4 meses persiste mesmo contra a inflação alimentar relativa, provando que o diesel move o preço da comida além e acima do efeito monetário geral.
3. **Mecanismo Físico de Transmissão:** O intervalo de um quadrimestre é amplamente documentado na literatura de economia de transportes no Brasil (ex: estudos do CEPEA/USP e IPEA) como o tempo necessário para o reajuste das tarifas de frete rodoviário de safra ser transferido dos contratos de frete atacadista para as tabelas de preços do varejo urbano."

---

### Pergunta 11: Heterogeneidade das Duas Pesquisas do IBGE
> **Banca:** *"A disciplina exige três ou mais fontes heterogêneas. Vocês usaram IPCA e LSPA, ambas do IBGE. Isso não desqualifica uma das fontes como sendo da mesma instituição?"*

**Resposta do Palestrante:**  
"Não, de forma alguma. A exigência acadêmica visa assegurar heterogeneidade de coleta, metodologia e natureza dos dados.  
Mesmo ambas pertencendo institucionalmente ao IBGE, o IPCA e o LSPA são pesquisas inteiramente independentes:
- O **IPCA** é conduzido pela Coordenação de Índices de Preços (COINP/DPE), com amostragem domiciliar urbana e coleta de preços no comércio varejista via computadores de mão.
- O **LSPA** é coordenado pela Gerência de Agricultura (COAGRO/DPE) junto a comissões técnicas estaduais e municipais que reúnem extensionistas rurais da EMATER, agrônomos e cooperativas agrícolas no campo.
A metodologia de amostragem, o grão nativo, a equipe técnica e a natureza do fenômeno mensurado não compartilham absolutamente nada entre si.  
Além disso, mesmo que contássemos o IBGE como uma única instituição, nosso trabalho entregou **6 pesquisas de 5 instituições governamentais distintas** (IBGE, INMET, ANA, BCB e ANP), superando com ampla folga o requisito mínimo de 3 fontes."

---

### Pergunta 12: Tolerância a Falhas e Recuperação em Disco
> **Banca:** *"O que acontece com o repositório e com os dados em disco se o processo for interrompido por um SIGKILL ou falta de energia durante a geração da tabela final?"*

**Resposta do Palestrante:**  
"O pipeline é totalmente protegido contra corrupção de arquivos em disco através da classe `BackupManager` implementada em [`src/logging_config.py`](../../src/logging_config.py#L170-L245).  
Toda escrita de arquivo crítico em `data/interim/` e `data/processed/` é executada dentro de um context manager com salvaguarda atômica:
1. Antes de iniciar a gravação, o `BackupManager` cria uma cópia idêntica do arquivo anterior com sufixo `.bak_YYYYMMDD_HHMMSS`.
2. O novo arquivo Parquet é processado e escrito em disco.
3. Se qualquer exceção, erro de I/O ou cancelamento abrupto ocorrer durante a escrita, o bloco `finally` captura o evento e executa o **rollback automático**, restaurando a versão de backup anterior íntegra e excluindo resquícios corrompidos de 0 bytes.
Dessa forma, o estado do repositório é sempre consistente e determinístico."

---

### Pergunta 13: Por que Incluir `clima_n_estacoes` na Tabela?
> **Banca:** *"A coluna `clima_n_estacoes` representa quantas estações meteorológicas estavam ativas na UF no mês. Por que manter uma variável de infraestrutura de rede em uma tabela analítica de crises climáticas?"*

**Resposta do Palestrante:**  
"Para proteger os futuros modelos preditivos contra **artefatos instrumentais de mensuração**.  
A rede de estações meteorológicas automáticas do INMET não é constante: ela expandiu significativamente ao longo do período analisado, passando de 475 estações ativas em 2014 para 638 em 2026. Além disso, em anos críticos como a crise hídrica de 2021, a cobertura de dados no Nordeste sofreu quedas abruptas de estações ativas.  
Se um modelo observar um aumento de temperatura média ou queda na precipitação acumulada em uma UF que coincide exatamente com a desativação ou quebra de 5 estações locais, o modelo poderia interpretar essa variação como uma seca real quando se trata meramente de uma quebra amostral da rede.  
Incluir `clima_n_estacoes` permite ao pesquisador utilizar essa coluna como regressor de controle instrumental ou como filtro de sensibilidade estatística."

---

### Pergunta 14: Risco de Dupla Contagem nos Pesos do IPCA
> **Banca:** *"Por que no slide 15 vocês proíbem explicitamente somar as colunas `ipca_peso_*` entre si?"*

**Resposta do Palestrante:**  
"Porque a estrutura de ponderação do IPCA-SNIPC do IBGE é rigorosamente hierárquica e nós selecionamos variáveis de múltiplos níveis propositalmente para permitir análises transversais:
- O nível de **Grupo** (código `1` - Alimentação e bebidas) contém 100% do orçamento alimentar.
- O nível de **Subgrupo** (ex: código `1110` - Aves e ovos) representa uma fração do grupo.
- O nível de **Subitem** (ex: código `1110009` - Frango inteiro) representa uma fração do subgrupo de aves.
Se um analista somar a coluna de peso de `alimentacao`, com a de `aves_ovos` e a de `frango_inteiro`, ele estará somando três vezes a mesma despesa familiar com frango, resultando em um peso de orçamento superior a 100%.  
Essas colunas existem para serem avaliadas lado a lado em comparações isoladas, e nunca agregadas entre si."

---

### Pergunta 15: Estoque vs. Fluxo nas Estimativas do LSPA
> **Banca:** *"Por que somar os valores de `safra_producao_t_*` ao longo dos 12 meses do ano é um erro grave?"*

**Resposta do Palestrante:**  
"Porque a variável `producao_t` do LSPA é uma variável de **estoque/previsão anual**, e **não uma variável de fluxo mensal**.  
Em cada mês $t$, os agrônomos do IBGE divulgam a sua melhor estimativa para a colheita acumulada de todo aquele **ano civil**.  
Se a previsão da safra de soja do Mato Grosso for de 40 milhões de toneladas em janeiro, 40 milhões em fevereiro e 40 milhões em março, a safra real do estado é de 40 milhões de toneladas, e não a soma de 120 milhões.  
Somar as estimativas mensais ao longo do ano multiplicaria artificialmente a produção agrícola por 12 vezes. A variável legítima que mede a dinâmica mensal da safra é a **`safra_revisao_pct_*`**, que apura quanto a estimativa anual variou contra o mês anterior em função de eventos climáticos recentes."
