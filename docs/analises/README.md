# Análises do projeto

Este diretório reúne estudos metodológicos, auditorias de dados e recomendações de próximos passos. Os documentos estão agrupados por tema e numerados na ordem de leitura sugerida **dentro de cada pasta**. O prefixo indica a sequência de compreensão, não a data de criação ou a prioridade de execução.

## Por onde começar

Para uma leitura completa, siga **integração dos dados → cobertura climática → safras e oferta**:

1. Leia o desenho da junção para entender como as fontes se tornam um painel UF × mês.
2. Consulte a cobertura do INMET e do Monitor de Secas para compreender as limitações das observações.
3. Em safras, comece pela representatividade espacial de MT, avance para a interpretação da EDA, confira as evidências e termine com o plano de decisões.

Se o foco for apenas o notebook 13, siga os quatro documentos de `safras_oferta/` em ordem numérica.

| Pasta | Assunto | Quando consultar |
|---|---|---|
| [integracao_dados/](integracao_dados/) | Junção das fontes no painel UF × mês | Para entender chaves, granularidade, agregações e contratos da tabela fato |
| [clima_cobertura/](clima_cobertura/) | Disponibilidade dos dados meteorológicos e de seca | Para escolher janelas de análise e interpretar ausências de observação |
| [safras_oferta/](safras_oferta/) | Produção agrícola, oferta de alimentos e EDA de safras | Para interpretar o notebook 13, avaliar a hipótese H2 e decidir os próximos experimentos |

## Integração dos dados

| Ordem | Documento | O que você entende com esta leitura |
|---|---|---|
| 01 | [Desenho da junção UF × mês](integracao_dados/01_analise_juncao_uf_mes.md) | Contratos de chaves, calendário, conversão da safra para formato largo, semântica dos nulos e verificações de integridade das junções |

## Clima e cobertura

| Ordem | Documento | O que você entende com esta leitura |
|---|---|---|
| 01 | [Cobertura do INMET](clima_cobertura/01_cobertura_inmet.md) | Disponibilidade das observações meteorológicas por UF e atendimento ao critério de qualidade |
| 02 | [Cobertura do Monitor de Secas](clima_cobertura/02_cobertura_monitor_secas.md) | Entrada de cada UF no monitoramento, meses observados e lacunas; distingue ausência de monitoramento de ausência de seca |

Esses dois relatórios são gerados pelos módulos `src.coleta.inmet.validar` e `src.coleta.monitor_secas.agrega_uf_mes`. Atualize-os pelos geradores indicados no próprio documento, que já usam os nomes numerados.

## Safras e oferta

| Ordem | Documento | O que você entende com esta leitura |
|---|---|---|
| 01 | [Cobertura da safra de Mato Grosso](safras_oferta/01_analise_cobertura_safra_mt.md) | **Contexto espacial:** por que MT não aparece no alvo do IPCA, onde seus dados de produção estão preservados e quais alternativas foram propostas para representar os fornecedores |
| 02 | [Estudo dos achados da EDA](safras_oferta/02_estudo_safras_oferta.md) | **Interpretação crítica:** o que os resultados do notebook 13 sustentam sobre H2 e transmissão aos preços; inclui ressalvas à análise anterior de MT |
| 03 | [Auditoria das evidências](safras_oferta/03_auditoria_eda_safras_oferta.md) | **Conferência quantitativa:** números recalculados, inconsistências nas conclusões e figuras, revisões antes do corte e código de reprodução |
| 04 | [Plano de decisões](safras_oferta/04_plano_decisoes_safras_oferta.md) | **Próximas ações:** prioridades, experimentos propostos, critérios de aceite e registro de decisões para melhorar o estudo |

As recomendações do plano estão registradas como propostas; consulte seu status antes de tratá-las como implementadas. Leia o documento 01 como contexto da investigação e use os documentos 02 e 03 para acompanhar as revisões críticas posteriores.

## Como adicionar uma análise

Coloque o documento na pasta do tema correspondente com o padrão `NN_nome_descritivo.md` e acrescente aqui seu link e uma descrição curta. Escolha a posição conforme o conhecimento necessário para a leitura: contexto, interpretação, evidências e decisões. A numeração recomeça em `01` em cada tema; mantenha `README.md` sem prefixo como porta de entrada.

Se surgir um tema distinto, crie uma pasta com nome descritivo. Registre no documento as fontes, a data, o escopo e se ele contém diagnóstico, recomendação ou decisão já implementada. Ao renumerar documentos, ajuste as referências e os caminhos de saída de seus geradores.

Veja também o [índice geral da documentação](../README.md) e o [plano de execução da EDA](../planejamento/plano_execucao_eda_grupo.md).
