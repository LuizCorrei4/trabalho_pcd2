# T-051 — Apresentação

| Campo | Valor |
|---|---|
| **Etapa** | 5 Entrega |
| **Prioridade** | P0 |
| **Estimativa** | 3h |
| **Depende de** | T-050 |
| **Responsável** | grupo todo |
| **Status** | 🔲 A fazer |

## Contexto
A apresentação não é o relatório resumido — é uma narrativa com três atos: *a pergunta*, *o que foi preciso fazer para respondê-la*, *o que se descobriu*. O trabalho de integração de dados, que é o mais custoso do projeto, é invisível se não for mostrado deliberadamente.

⚠️ **Conferir o tempo disponível** antes de montar. Regra prática: ~1 minuto por slide.

## Entregável
`apresentacao/apresentacao.pdf`

## Roteiro sugerido (~12 slides / 15 min)

| # | Slide | Conteúdo |
|---|---|---|
| 1 | Capa | Tema, integrantes |
| 2 | A pergunta | Por que a cesta básica importa — 1 número de impacto |
| 3 | As fontes | Diagrama das 3+ fontes com granularidade de cada uma |
| 4 | **O desafio da integração** ⭐ | A chave `(UF, mês)` e o pipeline. Este é o slide que mostra o trabalho real |
| 5 | **A sacada** ⭐ | Clima da capital ≠ clima que importa → clima ponderado pela produção |
| 6 | Os dados | 1 figura de EDA — a série do alvo, nominal vs. real |
| 7 | Correlação | A CCF com o lag ótimo — o gráfico mais interessante do trabalho |
| 8 | Clusters | O mapa do Brasil colorido |
| 9 | Modelo | Protocolo de validação temporal + tabela de métricas |
| 10 | O que pesa | SHAP agregado por família de variável |
| 11 | Conclusões | 3 achados em frases curtas |
| 12 | Limitações | Honestidade explícita — antecipa a pergunta do professor |

## Tarefas
- [ ] Confirmar tempo e formato exigidos
- [ ] Montar os slides com **pouco texto** — no máximo 5 linhas por slide
- [ ] Reaproveitar as figuras marcadas como "candidatas à apresentação" no T-030
- [ ] Definir quem fala cada bloco
- [ ] **Ensaiar cronometrado** pelo menos duas vezes
- [ ] Preparar respostas para as perguntas prováveis (ver abaixo)
- [ ] Levar backup em PDF e em pendrive

## Perguntas prováveis — preparar resposta
- *Por que essa chave de junção e não outra?* → porque a granularidade do alvo determina a de todo o resto
- *Como sabem que não há vazamento no modelo?* → protocolo de split temporal, escalonamento dentro do Pipeline, teste tocado uma vez
- *Correlação ou causalidade?* → associação; Granger é precedência preditiva, não causalidade
- *Por que o R² não é mais alto?* → o preço depende de margem de varejo, câmbio e expectativa, que não estão na base
- *Por que não usaram o clima da própria capital?* → usamos as duas famílias; e a justificativa da ponderação por produção (slide 5)

## Critérios de aceite
- [ ] Cabe no tempo, com margem — verificado em ensaio cronometrado
- [ ] Toda figura é legível projetada (fonte ≥ 18pt, contraste alto)
- [ ] Os slides 4 e 5 (integração e ponderação) estão bem contados — é onde está o mérito técnico
- [ ] Cada integrante fala
- [ ] O slide de limitações existe
- [ ] Backup em PDF pronto

## Armadilhas
- Gastar 10 dos 15 minutos falando de coleta de dados e chegar ofegante nas conclusões. Cronometrar de verdade.
- Slide com print de código ou de tabela do pandas: ilegível e desperdiça tempo. Só figuras e frases.
- Não ler os slides em voz alta. Slide é apoio, não roteiro.
- Não esconder o que não funcionou — o slide de limitações costuma render pontos, não perdê-los.
