# T-050 — Relatório final

| Campo | Valor |
|---|---|
| **Etapa** | 5 Entrega |
| **Prioridade** | P0 |
| **Estimativa** | 6h |
| **Depende de** | T-025, T-030, T-031, T-040, T-042 |
| **Bloqueia** | T-051 |
| **Responsável** | grupo todo |
| **Status** | 🔲 A fazer |

## Contexto
O documento que o professor vai ler. Boa parte do conteúdo já foi escrita ao longo dos tickets anteriores (seção de limitações no T-025, interpretações no T-031 e T-042) — este ticket costura tudo numa narrativa e preenche as lacunas.

⚠️ **Conferir o formato exigido pela disciplina antes de começar** (extensão, template, ABNT, formato de entrega). Ajustar a estrutura abaixo ao que for pedido.

## Entregável
`relatorio/relatorio_final.pdf` (ou o formato exigido)

## Estrutura sugerida

1. **Resumo** — problema, dados, método, principal achado. Escrever por último.
2. **Introdução** — por que o preço da cesta básica importa; pergunta de pesquisa.
3. **Fontes de dados** — tabela com as 3+ fontes: origem, granularidade nativa, período, variáveis. **Cumpre o requisito de 3+ fontes — deixar isso explícito.**
4. **Metodologia de integração** ⭐ — a chave `(sigla_uf, ano_mes)`; o diagrama do pipeline; e a justificativa do **clima ponderado pela produção** (T-022), que é o diferencial metodológico do trabalho.
5. **Tratamento e qualidade** — limpeza, imputação, limitações (vem do T-025).
6. **Análise exploratória** — figuras do T-030.
7. **Correlação** ⭐ — matriz, cross-correlation, lags ótimos, Granger (T-031). **Cumpre o requisito de investigar correlação.**
8. **Modelagem**
   - 8.1 Não supervisionado: clusters de capitais (T-040)
   - 8.2 Supervisionado: previsão da variação (T-041), com o protocolo de validação temporal descrito
   - 8.3 Interpretação (T-042)
9. **Discussão** — o que os resultados dizem sobre a pergunta; o que contrariou a expectativa.
10. **Limitações e trabalhos futuros**
11. **Conclusão**
12. **Referências** — links de todas as fontes, com data de acesso.

## Tarefas
- [ ] Confirmar formato e requisitos da disciplina
- [ ] Montar o esqueleto e distribuir seções entre o grupo
- [ ] Reaproveitar textos já escritos nos tickets anteriores
- [ ] Selecionar as figuras finais (qualidade > quantidade — 8 a 12 boas figuras)
- [ ] Revisão cruzada: cada pessoa revisa a seção de outra
- [ ] Verificar que todo número citado no texto bate com o output dos notebooks
- [ ] Revisar linguagem causal ("associado a", não "causa")

## Critérios de aceite
- [ ] Os requisitos do enunciado estão explicitamente atendidos e visíveis: **3+ fontes**, **integração por variável comum**, **análise de correlação**, **modelo supervisionado e/ou não supervisionado**
- [ ] Todo número no texto é rastreável a um notebook
- [ ] Toda figura é referenciada no texto e tem legenda
- [ ] A seção de limitações é honesta e específica, não genérica
- [ ] Referências completas com data de acesso
- [ ] Revisão ortográfica feita
- [ ] O relatório é compreensível por quem não acompanhou o projeto

## Armadilhas
- Não transformar o relatório num log de tudo que foi tentado. Contar a história do que foi feito e do que foi descoberto.
- Resultado negativo bem discutido vale mais que resultado positivo forçado. Se o clima explicar pouco, essa é a conclusão — defendê-la com dados.
- A seção 4 (metodologia de integração) é onde este trabalho se diferencia. Não resumi-la em dois parágrafos; é o coração da entrega.
- Deixar a escrita para a última semana é o erro clássico. Começar o esqueleto assim que o T-031 estiver pronto.
