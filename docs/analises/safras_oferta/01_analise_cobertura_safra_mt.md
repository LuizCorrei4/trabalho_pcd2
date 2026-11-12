# 🌾 Análise Técnica: Cobertura das 11 UFs sem IPCA e o Destino da Safra do Mato Grosso (MT)

**Projeto:** SSC0957 — Prática em Ciência de Dados II (2026)  
**Documento:** `docs/analises/safras_oferta/01_analise_cobertura_safra_mt.md`  
**Data:** Setembro de 2026  
**Status:** Diagnóstico de cobertura e alternativas metodológicas propostas; ganho analítico ainda não validado.  
**Revisão metodológica e referências:** 12/11/2026. As seções 7 e 8 distinguem evidência publicada, construção proposta e condições de validação.  

---

## 1. Contexto e Motivação da Investigação

Ao auditar a tabela primária de preços ao consumidor ([`data/interim/ipca_alimentos_rm.parquet`](../../../data/interim/ipca_alimentos_rm.parquet)), constatou-se que o alvo do projeto (`ipca_var_alimentacao`) cobre exclusivamente **16 Unidades da Federação**. Consequentemente, **11 UFs brasileiras não possuem dados de IPCA**.

Dentre as 11 UFs ausentes, destaca-se o estado de **Mato Grosso (MT)** — o maior polo agropecuário e produtor de grãos (soja e milho) do Brasil e do mundo.

Esta análise responde a quatro questões críticas:
1. *A esteira de dados desconsiderou os dados de safra do Mato Grosso?*
2. *Qual é o tamanho real do Mato Grosso na produção agrícola nacional?*
3. *Onde e como o filtro aconteceu no código-fonte?*
4. *Qual é o impacto econométrico para os estados consumidores e como solucionar essa lacuna nas próximas etapas?*

---

## 2. Auditoria da Cobertura Territorial das UFs

Cruzando [`data/interim/ipca_alimentos_rm.parquet`](../../../data/interim/ipca_alimentos_rm.parquet) com a dimensão canônica [`data/processed/dim_uf.csv`](../../../data/processed/dim_uf.csv):

| Grupo | Total | UFs Incluídas | Justificativa Institucional (IBGE (Instituto Brasileiro de Geografia e Estatística)) |
|---|:---:|---|---|
| **UFs com IPCA (Presentes)** | **16** | `AC`, `BA`, `CE`, `DF`, `ES`, `GO`, `MA`, `MG`, `MS`, `PA`, `PE`, `PR`, `RJ`, `RS`, `SE`, `SP` | O SNIPC/IBGE (Instituto Brasileiro de Geografia e Estatística) coleta preços em 10 Regiões Metropolitanas e 6 capitais/municípios isolados. |
| **UFs sem IPCA (Ausentes)** | **11** | `AL`, `AM`, `AP`, **`MT`**, `PB`, `PI`, `RN`, `RO`, `RR`, `SC`, `TO` | Estados onde o IBGE (Instituto Brasileiro de Geografia e Estatística) não realiza a pesquisa domiciliar contínua de preços ao consumidor do IPCA. |

> [!IMPORTANT]
> A ausência de MT não é um erro de raspagem de dados; é uma restrição amostral metodológica do próprio IBGE (Instituto Brasileiro de Geografia e Estatística)/SNIPC.

---

## 3. O Peso Agrícola do Mato Grosso: Dados Reais Auditados

Auditamos a base de safras em [`data/interim/safra_uf_mes.parquet`](../../../data/interim/safra_uf_mes.parquet) no fechamento oficial anual de 2023 (safra consolidada em dezembro/2023):

### 3.1. Soja em Grão (2023)
- **Produção Nacional Total:** 151.963.045 toneladas
- **Produção de Mato Grosso (MT):** **44.462.908 toneladas**
- **Participação de MT no Brasil:** **29,26 % de toda a soja brasileira!**

#### Ranking dos 5 Maiores Produtores de Soja:
| Posição | UF | Produção Anual (t) | % da Safra Nacional | Presente no IPCA / Tabela Fato? |
|:---:|:---:|:---:|:---:|:---:|
| **1º** | **MT** | **44.462.908** | **29,26 %** | ❌ **NÃO (Descartado)** |
| 2º | PR | 22.455.000 | 14,78 % | ✅ SIM |
| 3º | GO | 16.749.192 | 11,02 % | ✅ SIM |
| 4º | MS | 14.193.250 | 9,34 % | ✅ SIM |
| 5º | RS | 12.693.487 | 8,35 % | ✅ SIM |

---

### 3.2. Milho em Grão (2023)
- **Produção Nacional Total:** 131.085.011 toneladas
- **Produção de Mato Grosso (MT):** **50.543.494 toneladas**
- **Participação de MT no Brasil:** **38,56 % de todo o milho brasileiro!** (Quase 40% do milho do país).

#### Ranking dos 5 Maiores Produtores de Milho:
| Posição | UF | Produção Anual (t) | % da Safra Nacional | Presente no IPCA / Tabela Fato? |
|:---:|:---:|:---:|:---:|:---:|
| **1º** | **MT** | **50.543.494** | **38,56 %** | ❌ **NÃO (Descartado)** |
| 2º | PR | 17.958.800 | 13,70 % | ✅ SIM |
| 3º | GO | 14.048.839 | 10,72 % | ✅ SIM |
| 4º | MS | 13.468.542 | 10,27 % | ✅ SIM |
| 5º | MG | 8.296.982 | 6,33 % | ✅ SIM |

---

## 4. Onde e Como o Descarte Ocorreu no Pipeline

Rastreando a execução em [`src/tratamento/24_junta.py`](../../../src/tratamento/24_junta.py):

1. **A Espinha Dorsal Preserva MT:**
   A função `monta_calendario()` gera o produto cartesiano das 27 UFs com os 138 meses ($27 \times 138 = 3.726$ linhas). O arquivo [`data/processed/calendario_uf_mes.parquet`](../../../data/processed/calendario_uf_mes.parquet) **CONTÉM o Mato Grosso**.
2. **Os 5 LEFT JOINs Preservam MT:**
   - Durante os merges com `clima`, `safra`, `seca` e `macro`, a chave `(sigla_uf, ano_mes)` casa perfeitamente para MT.
   - O DataFrame intermediário atinge 3.726 linhas contendo todas as variáveis de produção física de MT (`safra_producao_t_soja = 44,4` milhões de t e `safra_producao_t_milho = 50,5` milhões de t).
3. **O Filtro Final Elimina MT ([`24_junta.py:268`](../../../src/tratamento/24_junta.py#L268)):**
   ```python
   # Como ipca_var_alimentacao é NaN para MT:
   fato = fato[fato["ipca_var_alimentacao"].notna()].reset_index(drop=True)
   ```
   Como o objetivo da tabela final é servir de matriz de design $X \to y$ para aprendizado supervisionado da inflação local, **todas as 138 linhas do Mato Grosso foram filtradas e excluídas da tabela final** ([`data/processed/fato_alimentos_combustiveis_uf_mes.parquet`](../../../data/processed/fato_alimentos_combustiveis_uf_mes.parquet), que possui exatamente 2.088 linhas).

---

## 5. A Consequência Econométrica: O "Ponto Cego" dos Estados Consumidores

No desenho tabular largo (*wide*) atual, cada linha representa uma entidade espaço-temporal observada `(sigla_uf, ano_mes)`:

$$\begin{bmatrix}
\text{UF} & \text{ano\_mes} & \text{IPCA Alimentos (Alvo)} & \text{Safra Soja} & \text{Safra Milho} \\
\text{SP} & \text{2021-03} & +1,85\% & 4.500.000\text{ t} & 3.200.000\text{ t} \\
\text{RJ} & \text{2021-03} & +2,10\% & 0\text{ t} & 80.000\text{ t} \\
\end{bmatrix}$$

### O Mecanismo da Falha de Transmissão:
- São Paulo e Rio de Janeiro são gigantescos centros urbanos consumidores de alimentos processados (óleo de soja, farelo de soja para ração de frango e ovos, farinha de milho, carnes suínas).
- A produção própria de soja do estado de São Paulo (~4,5 milhões de t) atende a uma fração mínima de sua demanda industrial; o Rio de Janeiro tem produção zero.
- A produção em outras UFs pode influenciar mercados consumidores por comércio e formação de preços. Os dados atuais não identificam quais frações do abastecimento de SP ou RJ vêm de cada produtor.
- **O problema de representação:** uma queda da estimativa de safra em MT não aparece diretamente nas colunas de safra local das linhas de SP e RJ. Isso motiva testar variáveis que representem produtores externos à UF consumidora.
- Não é possível concluir, apenas com esse diagnóstico, quanto os preços responderiam nem se o modelo atribuiria a variação a outros fatores. Estoques, comércio exterior, demanda, custos e transmissão entre mercados podem alterar a resposta. A seção 7 apresenta fundamentos e limites dessas hipóteses.

---

## 6. Onde os Dados Estão Salvos Intactos no Repositório?

Nenhum dado do Mato Grosso foi perdido ou deletado do projeto:
- ✅ [`data/interim/safra_uf_mes.parquet`](../../../data/interim/safra_uf_mes.parquet): Contém a série histórica completa de todas as 27 UFs para os 11 produtos agrícolas em 151 meses (44.847 linhas).
- ✅ [`data/interim/producao_uf_ano.parquet`](../../../data/interim/producao_uf_ano.parquet): Contém a produção anual e área colhida de todas as 27 UFs apuradas pela PAM (Produção Agrícola Municipal).
- ✅ [`data/processed/calendario_uf_mes.parquet`](../../../data/processed/calendario_uf_mes.parquet): A grade cartesiana de 27 UFs × 138 meses (3.726 linhas) está intacta em disco.

---

## 7. Alternativas metodológicas: fundamentos e aplicação

As alternativas abaixo respondem a perguntas diferentes e podem ser avaliadas gradualmente. **Não são três melhorias já comprovadas na tabela fato.** A literatura fundamenta mecanismos e métodos; sua aplicação ao IPCA das regiões observadas precisa ser testada. A produção local continua disponível para comparação.

| Alternativa | Pergunta respondida | Informação que falta para adotá-la |
|---|---|---|
| Safra nacional por cultura | Como evolui a estimativa de produção brasileira relevante para este alimento? | Validar se acrescenta informação às variáveis locais |
| Clima ponderado pela produção | Como está o clima nas UFs que concentram esta cultura? | Escolher pesos históricos, calendário agrícola e tratamento da cobertura climática |
| Exposição por origem e destino | Quanto cada consumidor está exposto aos diferentes produtores? | Construir uma matriz justificável de abastecimento ou exposição |

### 7.1. Solução 1: safra nacional por cultura nas linhas consumidoras

**Fundamento acadêmico e evidência.** González-Rivera e Helfand (2001) estudam a integração espacial do mercado brasileiro de arroz por meio de um sistema multivariado com restrições de cointegração. O trabalho trata explicitamente da extensão, do padrão e do grau de integração entre mercados ([R1](#r1)). Chiodi (2006) investiga preços do milho em nove estados brasileiros e encontra relações de integração que diferem entre mercados ([R2](#r2)). Essas pesquisas justificam investigar conexões além da UF local. Não demonstram que a soma nacional de produção seja o melhor preditor do IPCA nem identificam os fluxos atuais de abastecimento.

**Adaptação proposta para o repositório.** Construir uma medida simples da produção estimada de **cada cultura**, somando as UFs produtoras antes de filtrar as linhas com alvo disponível:

$$
P^{BR}_{c,t}=\sum_{j=1}^{27}P_{j,c,t}
$$

Aqui, $c$ é a cultura, $j$ a UF produtora e $t$ o mês de referência. Não somar culturas diferentes em uma coluna: toneladas de cana, arroz e soja não representam o mesmo produto ou mecanismo de formação de preço.

Exemplos de colunas propostas:

- `safra_br_producao_t_soja` e `safra_br_revisao_pct_soja`;
- `safra_br_producao_t_milho` e `safra_br_revisao_pct_milho`;
- equivalentes para arroz, feijão e outras culturas selecionadas conforme o subitem estudado.

Para a revisão nacional, calcular a mudança do total, dentro do mesmo ano-safra:

$$
R^{BR}_{c,t}=100\left(\frac{P^{BR}_{c,t}}{P^{BR}_{c,t-1}}-1\right).
$$

Exigir base anterior positiva e cobertura comparável. Não usar média simples das taxas estaduais: uma UF com produção pequena não deve ter a mesma influência de um grande produtor. Janeiro permanece indefinido para essa comparação intrassafra.

O BCB (2022) analisa as mudanças das projeções do LSPA (Levantamento Sistemático da Produção Agrícola) ao longo do ano e esclarece que são **estimativas mensais da safra anual** ([R3](#r3)). Portanto, `producao_t` não é colheita realizada no mês e não deve ser somada ao longo dos doze meses. Uma revisão publicada também não equivale necessariamente a uma surpresa para os agentes de mercado.

**Como entra na fato.** Criar uma tabela auxiliar com uma linha por mês e colunas por cultura; fazer um `LEFT JOIN` por `ano_mes`. No mesmo mês, SP e RJ recebem o mesmo valor nacional, mantendo seus preços, clima e produção local específicos. MT participa da soma sem precisar ter uma linha com IPCA observado.

**Coluna específica de MT.** É justificável testar `safra_mt_revisao_pct_soja` ou `safra_mt_revisao_pct_milho` por sua importância produtiva documentada em 2023. Essa escolha é uma hipótese do projeto, não uma prescrição das referências. Como MT já faz parte do Brasil, comparar alternativas como Brasil apenas, Brasil + MT ou MT + restante do Brasil. Não presumir ganho nem interpretar coeficientes redundantes como contribuições independentes.

**Limites e critério de decisão.** O total perde a localização das perdas: uma queda em MT compensada por aumento em outra UF pode desaparecer no agregado. Produção nacional também não equivale à oferta disponível para consumo, que depende de estoques e comércio. Comparar variáveis locais e nacionais para subitens compatíveis, na mesma amostra, com avaliação temporal e controle de sazonalidade. Em previsão, respeitar a data de divulgação do LSPA (Levantamento Sistemático da Produção Agrícola), além do mês de referência.

Um indicador nacional replicado varia apenas no tempo e é absorvido por efeitos fixos completos de ano-mês. Essa é uma propriedade algébrica do desenho: escolher a especificação antes de tentar estimar sua contribuição. Ganho preditivo, associação e causalidade são conclusões distintas.

### 7.2. Solução 2: clima nos produtores ponderado pela PAM (Produção Agrícola Municipal)

**Origem dos dados e dos pesos.** A PAM (Produção Agrícola Municipal), do IBGE (Instituto Brasileiro de Geografia e Estatística), fornece informações anuais sobre culturas agrícolas. O coletor do projeto consulta as tabelas SIDRA 1612, de lavouras temporárias, e 1613, de permanentes, no nível de UF ([R4](#r4)). O nome “Municipal” da pesquisa não significa que o arquivo local contenha observações municipais.

Em [`coleta_pam()`](../../../src/coleta/safra/coletor.py), o código calcula:

$$
w_{j,c,a}=\frac{P^{PAM}_{j,c,a}}{\sum_k P^{PAM}_{k,c,a}},
$$

onde $a$ é o ano. O resultado é `peso_producao_uf`, armazenado junto da produção em [`producao_uf_ano.parquet`](../../../data/interim/producao_uf_ano.parquet), pois ambos têm o grão **UF × cultura × ano**. Na conferência local, o arquivo cobre 2014–2024 e contém 3.267 linhas. O peso é uma participação produtiva calculada pelo projeto, não um peso de amostragem fornecido pelo IBGE (Instituto Brasileiro de Geografia e Estatística) nem um parâmetro estimado pelo modelo.

**Fundamento acadêmico e alcance.** Schlenker e Roberts (2009) relacionam produtividade agrícola a exposições meteorológicas nos locais de cultivo e mostram a importância de considerar respostas não lineares e exposição a extremos ([R5](#r5)). O estudo fundamenta alinhar o clima à geografia agrícola e alerta para perdas de informação por médias. Ele não testa pesos estaduais da PAM (Produção Agrícola Municipal) nem preços ao consumidor no Brasil. Usar participações produtivas estaduais é uma **aproximação proposta neste projeto**, a ser comparada com outras formas de agregação.

O [T-022](../../../tickets/02-tratamento/T-022-clima-ponderado.md) traduz essa ideia em um índice por cultura:

$$
C^{pond}_{c,t}=\sum_j \bar w_{j,c} C_{j,t},
$$

com pesos históricos $\bar w$ definidos antes do período avaliado. Se uma UF responde por 30% da produção histórica de soja, seu indicador climático recebe peso 0,30 no índice da soja. O peso do arroz nessa mesma UF pode ser diferente.

**Como entra na fato.** Combinar os pesos com clima mensal por UF; agregar por cultura e mês; transformar culturas em colunas; integrar à fato por `ano_mes`. Colunas candidatas incluem `clima_chuva_anomalia_pond_soja` e `clima_dias_calor_pond_milho`, mantendo também os indicadores locais. São nomes propostos, não colunas já presentes na fato.

**Condições de validade.**

- Usar pesos de período anterior ou atualizações baseadas em dados já publicados; o ano da produção não é a data de disponibilidade da PAM (Produção Agrícola Municipal). A janela de cinco anos do ticket é uma escolha operacional a justificar.
- Documentar se o peso é por produção ou área. Produção dá maior participação às regiões com maior volume; área responde a uma exposição territorial diferente. Compará-los pode ser uma análise de sensibilidade.
- Alinhar as variáveis ao calendário da cultura. Uma média anual de chuva pode esconder um extremo em fase crítica; anomalias locais e contagens de extremos são candidatos a investigar.
- Registrar a fração dos pesos com clima observado. Ausência em produtor importante não pode virar clima zero. Renormalizar pesos entre UFs observadas muda o universo e deve ser sinalizado.
- Não interpretar esses pesos como frações de compra de cada consumidor. O índice será nacional por cultura, repetido nas UFs consumidoras.

**Critério de decisão.** Comparar clima local, média simples e clima ponderado, com pesos fixados sem informação futura e os mesmos subitens/períodos. Um resultado fraco continua válido; não ajustar pesos até obter a correlação desejada. A evidência sobre clima e produtividade não substitui o teste da transmissão de produtividade/oferta até os preços.

### 7.3. Solução 3: exposição específica entre produtores e consumidores

**Fundamento acadêmico.** Halleck Vega e Elhorst (2015) discutem modelos de transbordamento espacial e propõem o modelo SLX como ponto de partida quando não há teoria suficiente para escolher uma estrutura mais complexa. O SLX inclui variáveis explicativas de outras unidades, ponderadas por uma matriz de relações. Os autores também discutem identificação e endogeneidade das variáveis e dos pesos ([R6](#r6)).

**Adaptação proposta.** Para uma cultura $c$, construir uma matriz de exposição $A_c$ com consumidores nas linhas e produtores nas colunas. O elemento $a_{i,j,c}$ indica a exposição do consumidor $i$ ao produtor $j$. Se representar participações de abastecimento, cada linha deve somar 1 e ter origem, cobertura e período documentados.

$$
E_{i,c,t}=\sum_{j=1}^{27}a_{i,j,c} R_{j,c,t-\ell}
$$

$R$ representa uma revisão de safra previamente auditada e $\ell$ a defasagem escolhida. O índice pode entrar em uma regressão:

$$
y_{i,t}=\alpha_i+\gamma_t+\theta_c E_{i,c,t}+X_{i,t}\beta+\epsilon_{i,t}.
$$

Aqui, $y$ é a taxa de variação do IPCA ou subitem, não uma segunda diferença dessa taxa. Os controles e efeitos fixos dependem da pergunta; se todas as linhas de $A_c$ forem iguais, $E$ será nacional e colinear com efeitos completos de ano-mês.

Com 16 consumidores e 27 produtores, $A_c$ é **retangular**. Essa construção de exposição se inspira no mecanismo de variáveis explicativas ponderadas do SLX; não corresponde automaticamente ao SLX convencional com matriz quadrada sobre as mesmas unidades. Pode ser calculada antes da regressão. MT entra como produtor mesmo sem preço observado. Pode-se incluir a própria UF como fornecedora, evitando excluir produção local sem justificativa.

Isso difere de um modelo que inclui preços de outras regiões, $Wy$: a proposta inicial pondera **variáveis de oferta**, não exige estimar simultaneamente a transmissão entre todos os preços. PySAL pode auxiliar em modelos espaciais, mas não fornece por si só os fluxos econômicos necessários à matriz.

**Viabilidade e base dos pesos.**

| Base candidata | Interpretação possível | Limitação |
|---|---|---|
| Fluxos observados de produto entre origem e destino | Participação no abastecimento registrado | Confirmar produto, direção, unidade, período e cobertura |
| Produção histórica combinada com distância ou custo | Exposição potencial sob hipótese de acesso aos produtores | Não equivale a fluxo observado; testar sensibilidade da hipótese |
| Contiguidade entre estados | Proximidade territorial | Vizinhança pode representar mal cadeias com transporte de longa distância |

As fontes de transporte citadas na versão anterior, como ANTT/SIFRECA, são possibilidades de investigação; **a existência de uma matriz utilizável por cultura não foi verificada aqui**. Série de frete e fluxo físico origem–destino são informações diferentes. Usar fluxos contemporâneos também exige cautela: eles podem responder aos próprios choques de produção e preços.

**Critério de decisão.** Antes de estimar, documentar o mecanismo e a origem dos pesos. Comparar o indicador regional com o agregado nacional; avaliar estabilidade temporal e sensibilidade às matrizes. Priorizar esta alternativa somente se houver dados ou hipóteses defensáveis que distingam as exposições dos consumidores. Uma matriz construída não identifica causalidade por si só.

---

## 8. Encaminhamento da auditoria

1. **Manter o recorte do alvo observado**, preservando as informações dos demais produtores em tabelas auxiliares e variáveis explicativas.
2. **Começar pela solução 1**, separando culturas e comparando representação local, nacional e polos específicos. É a alternativa mais simples com as bases já disponíveis; sua utilidade ainda precisa ser medida.
3. **Avaliar a solução 2 com o T-022**, documentando disponibilidade histórica dos pesos, calendário e cobertura climática.
4. **Condicionar a solução 3 à construção de uma matriz justificável**, começando por um produto e um conjunto limitado de consumidores.
5. **Não tratar as alternativas como ganhos comprovados.** Os estudos citados sustentam mecanismos e métodos; não validam automaticamente o desenho proposto para o IPCA deste projeto.

Aprofundamento: [interpretação crítica da EDA](02_estudo_safras_oferta.md), [auditoria quantitativa](03_auditoria_eda_safras_oferta.md) e [plano de decisões](04_plano_decisoes_safras_oferta.md).

## 9. Referências e alcance da consulta

As referências foram consultadas em 12/11/2026. As adaptações e critérios de decisão da seção 7 são propostas do projeto, não resultados apresentados pelos autores para nossa tabela fato.

<a id="r1"></a>
**R1. GONZÁLEZ-RIVERA, Gloria; HELFAND, Steven M. (2001).** *The Extent, Pattern, and Degree of Market Integration: A Multivariate Approach for the Brazilian Rice Market*. American Journal of Agricultural Economics, 83(3), 576–592. [DOI e resumo editorial](https://doi.org/10.1111/0002-9092.00179). Consulta ao resumo editorial; fundamenta a investigação de integração espacial, não a escolha de um indicador nacional específico.

<a id="r2"></a>
**R2. CHIODI, Luciane (2006).** *Integração espacial no mercado brasileiro de milho*. Dissertação de mestrado, ESALQ/USP. [Registro e resumo no repositório da USP](https://teses.usp.br/teses/disponiveis/11/11132/tde-13112006-082158/pt-br.html). Consulta ao resumo institucional. Resultados históricos não estabelecem a integração atual nem o repasse ao varejo.

<a id="r3"></a>
**R3. BANCO CENTRAL DO BRASIL (2022).** *Variações das estimativas do LSPA (Levantamento Sistemático da Produção Agrícola) ao longo do ano: período de 2007 a 2022*. Boletim Regional, novembro, p. 58–60. [Texto integral](https://www.bcb.gov.br/content/publicacoes/boletimregional/202211/br202211b3p.pdf). Fonte institucional para a natureza das estimativas e suas revisões; a comparação com dezembro usada nessa nota difere da revisão mês a mês proposta aqui.

<a id="r4"></a>
**R4. IBGE (Instituto Brasileiro de Geografia e Estatística).** *Produção Agrícola Municipal — tabelas SIDRA [1612](https://sidra.ibge.gov.br/tabela/1612) e [1613](https://sidra.ibge.gov.br/tabela/1613)*. Fontes originais identificadas no coletor local; os endereços retornaram restrição de acesso na consulta automatizada. A descrição da extração e dos pesos foi conferida em [`coleta_pam()`](../../../src/coleta/safra/coletor.py) e no Parquet local, sem nova coleta ao SIDRA.

<a id="r5"></a>
**R5. SCHLENKER, Wolfram; ROBERTS, Michael J. (2009).** *Nonlinear temperature effects indicate severe damages to U.S. crop yields under climate change*. Proceedings of the National Academy of Sciences, 106(37), 15594–15598. [Texto e DOI](https://doi.org/10.1073/pnas.0906865106). Estudo de produtividade nos EUA; fundamenta o alinhamento da exposição climática aos cultivos e a atenção a extremos. Não valida o índice PAM (Produção Agrícola Municipal) estadual proposto para o Brasil.

<a id="r6"></a>
**R6. HALLECK VEGA, Solmaria; ELHORST, J. Paul (2015).** *The SLX Model*. Journal of Regional Science, 55(3), 339–363. [DOI](https://doi.org/10.1111/jors.12188) e [texto integral no repositório da Universidade de Groningen](https://pure.rug.nl/ws/portalfiles/portal/99108393/THE_SLX_MODEL.pdf). Referência metodológica para variáveis explicativas espacialmente ponderadas e cautelas de identificação; a matriz retangular produtor–consumidor é uma adaptação do projeto.
