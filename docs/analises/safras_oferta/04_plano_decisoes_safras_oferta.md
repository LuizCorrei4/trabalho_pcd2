# Plano de decisões após a EDA de safras

**Data:** 05/11/2026. **Status:** proposta para execução pelo grupo. As tarefas abaixo não constituem alterações já feitas no notebook ou nos dados.

Fundamentos: [estudo interpretativo](02_estudo_safras_oferta.md), [auditoria quantitativa](03_auditoria_eda_safras_oferta.md), [plano da EDA](../../planejamento/plano_execucao_eda_grupo.md) e [análise da cobertura de MT](01_analise_cobertura_safra_mt.md).

## 1. Ordem recomendada

| Prioridade | Decisão proposta | Entrega verificável | Condição para avançar |
|---|---|---|---|
| P0 | Revisar o alcance das conclusões e a consistência das figuras | Notebook 13 com linguagem revisada, números dinâmicos e janela explícita | Cada conclusão aponta para tabela/figura correspondente |
| P0 | Auditar revisões brutas e calendário | Tabela de casos cortados/não finitos e cobertura UF × mês | Cada ausência e extremo tem classificação ou pendência registrada |
| P1 | Representar oferta nacional e polos produtores | Tabela mensal por cultura, derivada das 27 UFs antes do filtro de alvo | Agregados conciliados; mês de referência e disponibilidade diferenciados |
| P1 | Reavaliar a transmissão até os subitens | Tabela de associações com amostra, lag, estimador e incerteza | Comparação na mesma janela e sem selecionar lag no período de avaliação |
| P1 | Reformular o teste de H2 | Painel anual UF × cultura e decomposição da produção | Tendência, produtividade e escala geográfica discutidas |
| P2 | Avaliar se vale adicionar fontes | Quadro de lacunas e custo de coleta/manutenção | Nova fonte responde a um mecanismo ainda não observado |
| P2 | Comparar modelos simples e ampliados | Avaliação temporal com e sem oferta nacional/polos | Ganho e estabilidade medidos no período reservado |

Começar por P0 e pelo arroz RS → preços de arroz nas UFs consumidoras como um experimento delimitado. Manter soja/feijão como trilha anual de H2. Não expandir simultaneamente para todos os pares cultura–produto, todas as fontes e todos os modelos.

## 2. P0 — Revisão do notebook e da documentação

- [ ] Trocar “H2 confirmada categoricamente” por evidência descritiva compatível com parte da hipótese.
- [ ] Trocar “transmissão comprovada” por associação exploratória e reportar a pequena magnitude observada.
- [ ] Nomear Pearson/Spearman corretamente e comparar ambos na mesma amostra.
- [ ] Corrigir painel desbalanceado, UFs e contagem de janeiros; alinhar a lista de UFs da nota de MT com a base atual.
- [ ] Gerar percentuais, anotações de eventos, volatilidade e rótulos a partir do mesmo subconjunto usado nos gráficos.
- [ ] Rotular a média simples entre UFs como tal; distinguir população do painel de população nacional.
- [ ] Substituir “zero significa ausência de choque” por “estimativa publicada inalterada”.
- [ ] Registrar que a frequência de valores cortados não demonstra que todos sejam anomalias ou que os choques relevantes tenham sido preservados.

**Aceite:** não há afirmação quantitativa fixa divergente da tabela que a originou; cada seção explicita período, geografia, unidade, denominador e número de observações. Registrar conclusões negativas junto das positivas.

## 3. P0 — Auditoria do corte e do calendário

Construir uma tabela de revisão bruta por `(sigla_uf, produto, ano_mes)` com produção anterior/atual, taxa original, taxa limitada e flags de base zero, base pequena, não finito e corte. Separar uma taxa indefinida de uma taxa realmente igual a zero. Nenhum infinito deve entrar silenciosamente como um choque válido de ±50%.

Comparar resultados em três especificações documentadas: observações finitas sem corte; corte atual ±50%; tratamento de base pequena/zero com flag e análise separada dos episódios. Se houver estimativa de limiares a partir da distribuição, fazê-la apenas na amostra de treinamento. Não escolher o tratamento pela correlação mais favorável.

**Aceite:** justificar os casos afetados por UF/cultura e verificar a sensibilidade das conclusões ao tratamento. Se o resultado depender de poucos casos, classificá-lo como frágil. O limite atual pode ser mantido provisoriamente como regra operacional, com essa condição explícita.

Para defasagens, usar calendário mensal completo por entidade ou verificar diferenças consecutivas de exatamente um mês antes do `shift`. Produzir lags antes de filtrar por disponibilidade de outras fontes. A “janela balanceada” do utilitário atualmente filtra observabilidade de combustível e seca; seu nome não garante, por si só, um painel temporal balanceado.

## 4. P1 — Oferta nacional e exposição aos produtores

Construir a estimativa nacional para a cultura `c` e o mês `t` usando a camada interim:

```text
P_BR[c,t] = soma da produção estimada de todas as UFs com cobertura válida
R_BR[c,t] = 100 × (P_BR[c,t] / P_BR[c,t−1] − 1), dentro do mesmo ano-safra
```

Somar níveis antes de calcular a revisão. Não usar média simples das taxas estaduais. Se a cobertura mudar entre meses, o agregado pode mudar sem revisão real: registrar número de UFs cobertas, cobertura esperada e painel consistente. Não somar as estimativas dos doze meses como produção anual. Preservar janeiro indefinido para a revisão intrassafra.

Manter também a revisão de polos específicos, começando por RS/arroz e MT/soja/milho. A produção de MT entra como variável explicativa das regiões com preços observados; não é necessário criar ou imputar IPCA para MT.

**Dados propostos:** tabela por mês/cultura com produção nacional, revisão nacional, revisão do polo, flags de qualidade e identificação do universo. Fazer o broadcast somente depois de consolidar os agregados. Para previsão, adicionar data de divulgação/disponibilidade; enquanto ela não estiver disponível, classificar a análise como retrospectiva e evitar alegar desempenho em tempo real.

**Aceite:** uma linha por mês/cultura; conciliação com o total estadual em períodos de cobertura completa; sem multiplicação de linhas ao integrar à fato. A participação de cada polo deve informar ano e denominador. Pesos PAM do T-022 são pesos de produção por UF, não uma matriz observada de fluxos produtor–consumidor.

## 5. P1 — Experimento de transmissão aos preços

Pergunta inicial: “A revisão do arroz no RS ou no Brasil acrescenta informação à evolução do preço do arroz nas regiões observadas, além de sazonalidade e da própria história do preço?”

Comparar, na mesma janela e por UF consumidora:

1. Referência: sazonalidade mensal e defasagens do próprio preço.
2. Referência acrescida da revisão local de safra.
3. Referência acrescida da revisão nacional ou do polo produtor.

Definir previamente lags candidatos de 0–3 meses para a análise retrospectiva inicial; ampliar a janela apenas com justificativa e novo controle de seleção. Lag 0 representa associação contemporânea, não previsão ex ante. Usar arroz ↔ arroz; soja ↔ óleo de soja é uma relação de transformação industrial e deve ser rotulada como tal.

Registrar estimador, janela, n de pares válidos e de revisões não zero, cultura, UF de origem, destino e lag. Comparar Pearson/Spearman e associações após ajuste de sazonalidade. Na inferência, considerar dependência temporal com procedimentos adequados, como reamostragem em blocos, explicitando tamanho e sensibilidade dos blocos. Com poucos anos/blocos, a incerteza continua elevada. Controlar múltiplos testes dentro de famílias previamente definidas; reportar a seleção do maior módulo como seleção exploratória.

Reservar meses futuros inteiros para avaliação, mantendo todas as UFs de um mês no mesmo bloco. Escolha de lag, pesos e transformações ocorre no treino; a documentação de [validação temporal do FPP3](https://otexts.com/fpp3/toolbox.html#time-series-cross-validation) fundamenta esse desenho.

**Aceite:** tabela de associações e comparação temporal de erro com e sem oferta. Um ganho pequeno ou instável não autoriza declarar dominância do fator. Se não houver ganho, registrar “sem evidência incremental nesta especificação e janela”, preservando o resultado.

## 6. P1 — Investigar H2 em partes

| Componente | Próxima análise | Como interpretar |
|---|---|---|
| Tendência de área nacional | Nível, primeira diferença e mudanças percentuais por cultura | Verificar quanto do padrão depende de tendências opostas |
| Produtividade | Produção, área colhida e rendimento por UF/ano | Distinguir retração de área de retração de produção |
| Substituição espacial | Crescimento da soja e retração de arroz/feijão nas mesmas UFs | Compatibilidade espacial ainda não comprova conversão da mesma terra |
| Oferta interna | Estoques, produção e comércio, se obtidos com cobertura adequada | Estoques públicos não equivalem a estoques totais |
| Formação de preços | Oferta específica do feijão e IPCA do feijão, com calendário compatível | Examinar a parte da H2 que o teste atual não cobre |

Não usar um corte em 2019 como ruptura conhecida sem justificativa prévia. Se explorar vários cortes, explicitar essa busca. O painel anual de 12 anos exige parcimônia: resultados instáveis devem permanecer descritivos. Não aprovar ou rejeitar toda a H2 por um único p-valor.

## 7. P2 — Dados adicionais e especificação dos modelos

| Fonte candidata | Lacuna que pode ajudar a preencher | Condição de investimento |
|---|---|---|
| PAM já coletada | Pesos de produção e composição anual | Confirmar granularidade, anos e disponibilidade; congelar pesos anteriores à avaliação |
| INMET já coletado + índice do T-022 | Clima nos produtores | Documentar cobertura e pesos; confrontar chuva local e ponderada |
| CONAB | Estoques e narrativas sobre safra | Verificar série específica, abrangência e calendário; não confundir texto narrativo com validação causal |
| CEPEA | Preço na origem | Confirmar cobertura, unidade, acesso e comparabilidade; IPCA é variação de índice, não preço em R$/kg |
| Dados de frete/fluxos | Exposição interestadual | Diesel é proxy de custo, não observação do corredor MT → SP; não inventar matriz de abastecimento |

Para um painel com efeitos fixos completos de ano-mês, o broadcast nacional é colinear com os efeitos temporais. Escolher outra especificação conforme a pergunta ou interações com exposições regionais justificadas e predeterminadas. Não chamar qualquer interação de solução causal. No ML, comparar primeiro com uma referência simples e usar avaliação temporal; SHAP descreve o modelo ajustado e não identifica parcelas causais do preço.

## 8. Registro de decisões do grupo

Use o quadro para registrar a execução. Todas as linhas começam como propostas, sem responsável ou prazo atribuído.

| Decisão | Status inicial | Responsável | Evidência para encerramento |
|---|---|---|---|
| D-SAF-01 — Revisar texto e figuras | Proposta | A definir | Notebook e documentação conciliados |
| D-SAF-02 — Auditar corte/calendário | Proposta | A definir | Casos e sensibilidade documentados |
| D-SAF-03 — Oferta nacional/polos | Proposta | A definir | Agregados e disponibilidade auditados |
| D-SAF-04 — Comparação de transmissão | Proposta | A definir | Resultado temporal com referência e incerteza |
| D-SAF-05 — H2 por mecanismos | Proposta | A definir | Área, rendimento, oferta e preço tratados separadamente |
| D-SAF-06 — Fontes/modelos adicionais | Condicionada a D-SAF-01 a 05 | A definir | Lacuna, benefício e custo justificados |

Ao concluir uma decisão, acrescentar data, arquivos produzidos, resultados favoráveis e desfavoráveis e limitações. O próximo passo recomendado é D-SAF-01, seguido de D-SAF-02; essas etapas tornam a comunicação e os experimentos seguintes mais confiáveis sem depender de novas coletas.
