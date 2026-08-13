# T-025 — Relatório de qualidade dos dados

| Campo | Valor |
|---|---|
| **Etapa** | 2 Tratamento |
| **Prioridade** | P1 |
| **Estimativa** | 2h |
| **Depende de** | T-024 |
| **Bloqueia** | — |
| **Responsável** | — |
| **Status** | 🔲 A fazer |

## Contexto
Antes de rodar qualquer modelo, é preciso saber onde a base é frágil. Este relatório evita a pior situação possível numa apresentação: descobrir na hora da pergunta do professor que uma UF inteira estava com clima imputado, ou que 30% de uma coluna é nulo.

Também rende material direto para a seção de limitações do relatório final — que é o que separa um trabalho honesto de um trabalho que só mostra o que deu certo.

## Entregável
`notebooks/00_qualidade.ipynb`
`outputs/tabelas/qualidade_dados.csv`
`outputs/figuras/heatmap_nulos.png`

## Tarefas
- [ ] Tabela de nulos: % por coluna, e por coluna × ano (nulo concentrado num período é bem pior que nulo espalhado)
- [ ] Heatmap de cobertura UF × ano — identifica visualmente buracos regionais
- [ ] Contagem de linhas por UF e por ano; listar UFs com série incompleta
- [ ] Estatísticas descritivas de todas as numéricas (`describe()`) com checagem de valores impossíveis
- [ ] Detecção de outliers no alvo: variação mensal > 3 desvios-padrão — investigar cada caso e classificar como erro de parsing ou evento real
- [ ] Quantificar o clima imputado: % de linhas com `clima_imputado = True`, por UF
- [ ] Verificar continuidade temporal: nenhum mês faltando no meio da série de nenhuma UF
- [ ] Escrever a **seção de limitações** em markdown, pronta para colar no relatório final

## Critérios de aceite
- [ ] Toda coluna com > 20% de nulos tem uma linha de justificativa escrita
- [ ] Todo outlier do alvo acima de 3σ foi classificado como erro (corrigido) ou evento real (documentado, com o que aconteceu)
- [ ] O heatmap de cobertura está gerado e é legível
- [ ] A seção de limitações está escrita e cobre: cobertura desigual entre UFs, imputação climática, perda dos preços por produto do DIEESE, uso de broadcast para variáveis nacionais
- [ ] Uma decisão explícita foi tomada sobre cada coluna problemática: manter, imputar ou descartar

## Armadilhas
- Outlier no alvo pode ser **real**: o preço do arroz explodiu em 2020, o do café em 2024-2025. Não remover automaticamente — investigar. Remover evento real é remover justamente o que o modelo deveria aprender.
- Nulo concentrado num ano específico costuma indicar mudança de layout na fonte, não ausência de dado. Vale voltar ao coletor antes de imputar.
- Se uma UF tiver cobertura muito ruim, considerar excluí-la do modelo — mas dizendo isso claramente no relatório, não em silêncio.
