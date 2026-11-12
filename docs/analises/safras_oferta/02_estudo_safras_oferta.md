# Safras e oferta: interpretação crítica da EDA 13

**Data:** 05/11/2026. **Status:** estudo para orientar decisões; recomendações ainda não implementadas.

Este estudo confronta o [notebook 13](../../../notebooks/13_eda_safras_oferta.ipynb) com as bases locais, a [proposta](../../planejamento/Proposta.md), o [plano da EDA](../../planejamento/plano_execucao_eda_grupo.md) e as notas metodológicas em `docs/`. O objetivo é decidir quais achados sustentar, quais formulações revisar e quais análises executar antes de ampliar a modelagem.

Leia em conjunto a [auditoria das evidências](03_auditoria_eda_safras_oferta.md) e o [plano de decisões](04_plano_decisoes_safras_oferta.md). A auditoria identifica precisamente o que foi recalculado e o que foi apenas lido nos resultados gravados do notebook.

## 1. Decisão central

A principal melhoria é representar a oferta nos polos produtores e confrontá-la com preços de subitens nas regiões consumidoras. Isso deve vir acompanhado de uma revisão da força das conclusões: os resultados atuais justificam investigar transmissão espacial e tendências na composição da agricultura; ainda não demonstram que a expansão da soja causou a retração do feijão ou que as revisões de safra explicam grande parte da inflação.

A hipótese H2 da proposta contém uma cadeia de mecanismos:

```mermaid
flowchart LR
    A[Expansão da soja] --> B[Realocação de área antes dedicada ao feijão]
    B --> C[Redução da oferta disponível de feijão]
    C --> D[Aumento do preço do feijão]
```

O notebook compara áreas nacionais e produção agregada. Ele não acompanha a conversão da mesma terra entre culturas, a disponibilidade interna de feijão nem a resposta do preço do feijão nessa cadeia. Cada seta exige evidência adicional. A identificação de tendências opostas em áreas nacionais é uma contribuição descritiva relevante, mas não completa o teste da H2 original.

## 2. O que os achados permitem dizer

| Achado | Leitura sustentada | Decisão recomendada |
|---|---|---|
| Revisões locais e preços de subitens têm correlações próximas de zero | O pareamento local simples oferece pouco sinal na especificação avaliada | Preservar o resultado negativo e comparar com oferta de polos/nacional |
| Revisão do arroz no RS e preços em UFs consumidoras apresentam sinais predominantemente negativos | Há associações fracas compatíveis com o mecanismo de oferta | Investigar incerteza, sazonalidade e estabilidade; evitar atribuir causalidade |
| A produção é geograficamente concentrada | A geografia do produtor importa para construir variáveis de exposição | Calcular concentração sobre as 27 UFs, com denominador e ano explícitos |
| Janeiro não tem revisão dentro do novo ano-safra | A ausência decorre da regra de cálculo do repositório | Preservar `NaN`; não interpretar como estabilidade |
| Muitas revisões são zero | A estimativa publicada permaneceu igual | Separar frequência de atualização e magnitude da revisão; zero não prova ausência de choque físico |
| Revisões de soja e milho no RS caem fortemente entre janeiro e março de 2022 | O episódio merece estudo de caso | Mostrar os números, procurar evidência climática e controlar explicações concorrentes |
| Área de soja/milho cresce e de arroz/feijão cai entre 2014 e 2025 | Existem tendências nacionais divergentes | Tratar H2 como parcialmente investigada; estudar produtividade e mudanças por UF |
| MT não tem alvo na fato, mas existe na camada de safra | O recorte supervisionado não representa toda a geografia produtiva | Construir oferta nacional antes do filtro de disponibilidade do alvo |

As tabelas gravadas na seção 0 do notebook mostram correlações locais entre aproximadamente −0,039 e +0,049. Na análise RS → consumidores, há, por exemplo, −0,148 no próprio RS no contemporâneo e −0,163 em PE no lag 2. Esses valores não sustentam chamar a correlação de alta nem estabelecer os lags de transmissão como conhecidos. A correlação do RS já é tão negativa no contemporâneo quanto no lag 1.

O código dessa seção usa `Series.corr()` sem `method`, portanto calcula **Pearson**. A comparação com o Spearman do notebook 09 também troca o estimador; diferenças entre resultados não podem ser atribuídas exclusivamente ao desenho espacial.

## 3. H2: tendências, produção e mecanismo

A conferência local reproduziu as variações de 2014 a 2025, usando estimativas de dezembro e somando UFs para cada cultura:

| Cultura | Área plantada | Produção |
|---|---:|---:|
| Soja | +57,88% | +92,10% |
| Milho | +44,18% | +79,97% |
| Arroz | −25,50% | +4,12% |
| Feijão | −19,60% | −6,40% |

A produção de arroz cresceu apesar da retração de área. Isso torna indispensável decompor produção em área colhida e rendimento. A retração da área, isoladamente, não demonstra redução de oferta física nem escassez no varejo.

**O que significa Spearman?** A correlação de Spearman mede se duas variáveis tendem a subir ou descer juntas de forma consistente. Primeiro, ela substitui os valores por suas posições em uma ordenação: o ano com maior área de soja recebe uma posição alta, por exemplo. Depois, compara as posições das duas culturas. O coeficiente vai de −1 a +1: valores negativos indicam que, quando uma cultura ocupa posições mais altas, a outra tende a ocupar posições mais baixas; valores próximos de zero indicam pouca associação ordenada. Spearman não exige uma relação em linha reta, mas continua sendo uma medida de associação, não de causa.

“Em níveis anuais” quer dizer que comparamos as áreas observadas em cada ano: soja de 2014 com arroz de 2014, soja de 2015 com arroz de 2015, e assim por diante. Nessa comparação, os coeficientes soja–arroz (−0,832) e soja–feijão (−0,881) mostram que anos com mais área de soja tendem também a ser anos com menos área de arroz ou feijão.

**O que são primeiras diferenças anuais?** Em vez de comparar o tamanho das áreas, calculamos quanto cada área mudou de um ano para o seguinte. Por exemplo, a diferença da soja em 2015 é `área_soja_2015 − área_soja_2014`; fazemos o mesmo para arroz ou feijão e comparamos as mudanças ocorridas no mesmo intervalo. Assim, a pergunta deixa de ser “anos com mais soja têm menos arroz?” e passa a ser “nos intervalos em que a área de soja aumentou mais, a área de arroz ou feijão diminuiu?”.

Com essas mudanças anuais, os coeficientes passam a +0,191 para soja–arroz e +0,173 para soja–feijão: ambos são fracos e positivos nesta amostra. A diferença em relação aos valores negativos fortes em nível mostra **sensibilidade à tendência**. Em outras palavras, o padrão negativo aparece ao comparar os tamanhos das áreas ao longo dos anos, mas não aparece ao comparar os aumentos e reduções de um ano para o seguinte. Uma tendência prolongada — por exemplo, soja crescendo ao longo do período e arroz diminuindo — pode gerar correlação negativa entre os níveis mesmo quando as mudanças anuais não se compensam sistematicamente. Isso é um alerta para não interpretar a correlação em níveis, sozinha, como evidência de que uma cultura substituiu a outra.

Há apenas 12 observações anuais em nível (2014–2025) e 11 mudanças anuais. Com séries tão curtas, cada ano pode influenciar bastante o resultado. A comparação em diferenças é um diagnóstico útil, mas não prova ausência de substituição: ela não controla todos os fatores, não acompanha a mesma terra e também não resolve a dependência entre anos consecutivos.

**Como ler o teste de Mann–Whitney?** O notebook separa os valores anuais em dois grupos: 2014–2018 e 2019–2025. O teste compara as posições ordenadas dos valores dos dois grupos para avaliar se suas distribuições parecem iguais ou se um grupo tende a apresentar valores maiores ou menores. Aqui foi usada a alternativa unilateral de que a área no primeiro período (2014–2018) é maior que no segundo (2019–2025), para arroz e feijão.

O resultado reproduzido, p nominal ≈ 0,00126, significa que, **sob a hipótese de distribuições iguais e as premissas do teste**, resultados tão incompatíveis com essa hipótese seriam incomuns. O p-valor não é a probabilidade de a hipótese ser verdadeira, não mede o tamanho da queda e não demonstra que algo especial ocorreu exatamente em 2019. A documentação do SciPy descreve o Mann–Whitney como um teste para duas amostras independentes ([documentação do SciPy](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.mannwhitneyu.html)). Como os grupos aqui são trechos da mesma série anual e podem compartilhar tendência ou dependência temporal, essa premissa precisa ser justificada. Mesmo que o teste detecte diferença entre os períodos, isso não identifica uma “ruptura estrutural” nem sua causa; seria necessário um método de série temporal adequado e uma justificativa para a data da ruptura.

**Formulação recomendada:** “Entre 2014 e 2025, soja e milho ampliaram área enquanto arroz e feijão a reduziram. As associações entre níveis são fortes, mas sensíveis à remoção da tendência. A substituição direta de culturas e seu efeito sobre preços permanecem hipóteses a investigar.”

Para avançar, usar o painel anual UF × cultura: verificar se a expansão e a retração ocorrem nas mesmas UFs e anos, examinar área colhida e rendimento e reconhecer que múltiplas safras/sucessão de culturas impedem interpretar hectares agregados como área física exclusiva. Uma demonstração de conversão da mesma terra exigiria dados adicionais de uso do solo.

## 4. Oferta, produção prevista e disponibilidade interna

O LSPA acompanha estimativas da safra anual em publicações mensais, como descreve a [nota do BCB sobre as estimativas do LSPA](https://www.bcb.gov.br/content/publicacoes/boletimregional/202211/br202211b3p.pdf). A variável do repositório é uma atualização dessas estimativas, não o volume colhido naquele mês e tampouco uma surpresa de mercado identificada.

Assim, uma revisão negativa pode representar informação nova ou reconhecimento tardio de perdas. Não devemos equiparar sua data à data do choque climático ou do primeiro ajuste de preços. Para estudo prospectivo, também é necessário conhecer a data em que a estimativa se tornou pública; o mês de referência, sozinho, não assegura que a informação estivesse disponível para prever o preço daquele mês.

Oferta disponível para consumo depende ainda de estoques, importações, exportações e usos industriais. A proposta de recorrer a CONAB e CEPEA é pertinente para testar mecanismos específicos, mas sua coleta deve responder a uma lacuna concreta. Estoques públicos, se obtidos, não representam automaticamente todos os estoques privados/comerciais.

## 5. O caso RS 2021–2022 e a volatilidade

Os dados locais confirmam a forte redução das estimativas entre janeiro e março de 2022: soja de 21,071 para 9,495 milhões de toneladas; milho de 5,527 para 3,025 milhões; arroz de 7,816 para 7,418 milhões. No RS, o IPCA do arroz passa de −3,31% em janeiro para +3,11% em março; o IPCA de alimentação em março é +3,18%.

Essa simultaneidade é adequada para descrição de um caso. Atribuir os preços à seca exige confronto com evidência climática e fatores concorrentes. A diferença entre arroz e grãos de sequeiro motiva investigar irrigação; a comparação isolada entre três culturas não identifica o efeito causal dessa tecnologia. Sem uma fonte de classificação e exposição hídrica, registrar o mecanismo como interpretação a confrontar.

O contraste entre preços de perecíveis e de produtos armazenáveis também permanece útil. Porém, o boxplot não mede estoques ou tecnologia de armazenamento. Além disso, a figura usa a fato inteira, enquanto a caixa de estatísticas contém números fixos e o rótulo 2018–2024. Primeiro corrigir janela e números; depois discutir mecanismos possíveis, incluindo calendário, perecibilidade e transmissão industrial.

## 6. Conexões com as decisões em docs e tickets

- A [auditoria de MT](01_analise_cobertura_safra_mt.md) já recomenda oferta nacional por broadcast. Esta recomendação deve preservar MT como produtor, sem inventar um alvo para MT. Sua lista de UFs contém uma inconsistência: os dados atuais incluem ES; isso deve ser conciliado antes de reutilizar a tabela desse documento.
- A [análise da junção](../integracao_dados/01_analise_juncao_uf_mes.md) distingue previsão anual de fluxo mensal e preserva revisões indefinidas. Manter esses contratos em qualquer nova tabela.
- O [T-022](../../../tickets/02-tratamento/T-022-clima-ponderado.md) propõe um índice climático nacional ponderado por produção **por UF**, com pesos anteriores ao período avaliado. Isso é diferente da descrição de ponderação municipal de estações feita nas notas de apresentação; essa extensão municipal não está demonstrada pelo ticket.
- O [T-031](../../../tickets/03-analise/T-031-correlacao-lag.md) pede Pearson/Spearman, tamanho amostral, tratamento de tendência e comparações múltiplas. Sua orientação de reportar resultados negativos é especialmente pertinente aqui. O título do ticket é correlação/CCF; a referência a “T-031 TWFE” na apresentação precisa ser conciliada.
- Os [critérios da disciplina](../../apresentacao/criterios_disciplina_delbem.md) priorizam representatividade por propósito e interpretação da informação integrada. Corrigir população, calendário e alcance da inferência atende diretamente a esses critérios.

## 7. Limite da modelagem proposta

Uma safra nacional replicada para todas as UFs varia apenas no tempo. Em um painel com efeitos fixos completos para cada ano-mês, sua contribuição isolada é absorvida por esses efeitos: não existe variação restante para identificar seu coeficiente. Essa é uma consequência algébrica do desenho, aplicável também aos controles macro nacionais.

Escolher a especificação conforme a pergunta: série temporal nacional para associação agregada; painel com exposições regionais previamente definidas para heterogeneidade; ou modelo de previsão avaliado em cortes temporais. Retirar efeitos de tempo apenas para obter um coeficiente pode reintroduzir confundimento. Interações com exposições regionais exigem justificativa e não tornam o resultado automaticamente causal.

SHAP, importância de variáveis e precedência preditiva podem ajudar a descrever um modelo; não devem ser apresentados como percentuais causais da inflação. A decisão de expandir para modelos complexos fica condicionada ao plano de comparação e às auditorias dos documentos seguintes.
