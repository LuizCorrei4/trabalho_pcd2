# T-016 — Coletor CONAB: safras, estoques e custos de produção

| Campo | Valor |
|---|---|
| **Etapa** | 1 Coleta |
| **Prioridade** | P2 (opcional) |
| **Estimativa** | 4h |
| **Depende de** | T-002 |
| **Bloqueia** | — |
| **Responsável** | — |
| **Status** | 🔲 A fazer |

## Contexto
A CONAB tem o que o IBGE não tem: **estoques públicos** e **custo de produção**. Estoque é a variável que explica por que uma quebra de safra às vezes não vira alta de preço — tem amortecedor. É conceitualmente ótima.

O problema é a chave: a CONAB trabalha em **ano-safra** (`2024/25`), não em ano-calendário, e converter isso para mês dá trabalho e introduz suposições. Por isso é P2 — o LSPA (T-012) já cobre a parte de oferta com granularidade mensal nativa.

## Entregável
`data/interim/conab_uf_safra.parquet`

## Fonte
- Séries históricas de safras: https://www.conab.gov.br/info-agro/safras/serie-historica-das-safras (XLS por produto, UF × safra)
- Portal de Informações: https://portaldeinformacoes.conab.gov.br/ (preços agropecuários, preços mínimos, custos de produção)
- Boletins mensais de safra (PDF, levantamento por UF)

## Tarefas
- [ ] Baixar os XLS de série histórica dos produtos da cesta (arroz, feijão, milho, soja, trigo)
- [ ] Parsear os XLS — o layout tem cabeçalhos em múltiplas linhas e células mescladas
- [ ] Construir a tabela de mapeamento **safra → meses** (ver Armadilhas) e documentar a regra adotada
- [ ] Coletar estoques públicos e custo de produção, se disponíveis por UF
- [ ] Salvar em formato longo: `sigla_uf`, `produto`, `ano_safra`, `variavel`, `valor`

## Critérios de aceite
- [ ] Produção total por safra bate com o boletim oficial da CONAB (tolerância 2%)
- [ ] A regra de mapeamento safra→mês está escrita no código **e** no relatório, com justificativa
- [ ] `sigla_uf` bate 100% com `dim_uf`

## Armadilhas
- **Ano-safra ≠ ano-calendário.** A safra `2024/25` de soja é plantada em out/2024 e colhida em fev–abr/2025. Atribuir a safra ao ano errado desalinha tudo. Definir e documentar uma regra explícita — sugestão: atribuir a safra aos meses de colheita, e usar a data do levantamento quando disponível.
- Cada produto tem calendário de safra diferente, e o mesmo produto tem calendário diferente por região (feijão tem 3 safras/ano). Não existe uma regra única — por isso é trabalhoso.
- Os XLS da CONAB mudam de layout entre edições. Prever revisão manual.
- **Se o tempo apertar, corte este ticket.** O LSPA já entrega oferta mensal por UF e cobre a necessidade principal do modelo.
