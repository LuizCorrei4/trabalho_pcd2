# T-040 — Modelo não supervisionado: clusters de capitais

| Campo | Valor |
|---|---|
| **Etapa** | 4 Modelagem |
| **Prioridade** | P1 |
| **Estimativa** | 4h |
| **Depende de** | T-024 |
| **Bloqueia** | T-050 |
| **Responsável** | — |
| **Status** | 🔲 A fazer |

## Contexto
Cumpre a parte "não supervisionado" do requisito e responde uma pergunta que a regressão não responde: **quais capitais se comportam como um mesmo mercado?**

É um ticket de baixo risco e alto retorno visual — um mapa do Brasil colorido por cluster é uma das melhores figuras possíveis para a apresentação. E o resultado pode virar feature do modelo supervisionado.

## Entregável
`notebooks/03_clustering.ipynb`
`outputs/figuras/mapa_clusters.png`, `outputs/tabelas/perfil_clusters.csv`

## Abordagem
Cada capital vira **uma linha** com um vetor de características agregadas de toda a série:

| Feature do cluster | Descrição |
|---|---|
| `custo_medio_real` | nível de preço |
| `volatilidade` | desvio-padrão de `var_pct_cesta_mm` |
| `amplitude_sazonal` | diferença entre o mês mais caro e o mais barato |
| `tendencia` | inclinação da regressão linear do valor real no tempo |
| `sensibilidade_climatica` | correlação do preço local com o clima local (defasado) |
| `pct_salario_minimo_medio` | peso da cesta na renda |

## Tarefas
- [ ] Construir a matriz capital × features agregadas (27 ou 17 linhas)
- [ ] Padronizar com `StandardScaler` — obrigatório, as escalas são muito diferentes
- [ ] **PCA** para 2 componentes: visualização + análise de quanto cada variável carrega
- [ ] **KMeans** com escolha de *k* por método do cotovelo **e** silhouette score
- [ ] Comparar com **clustering hierárquico** (dendrograma — figura excelente para relatório)
- [ ] Caracterizar cada cluster com um nome interpretável e uma descrição ("capitais do Norte, cesta cara e alta sensibilidade climática")
- [ ] Plotar o mapa do Brasil colorido por cluster
- [ ] Avaliar se `cluster` melhora o T-041 quando entra como feature categórica

## Critérios de aceite
- [ ] O *k* escolhido está justificado por cotovelo **e** silhouette, não por gosto
- [ ] Silhouette score > 0,3 (abaixo disso a estrutura é fraca e isso precisa ser dito)
- [ ] Cada cluster tem nome e interpretação escrita — cluster sem interpretação não vale nada num relatório
- [ ] Os clusters têm alguma coerência geográfica ou econômica reconhecível; se não tiverem, o porquê está discutido
- [ ] O mapa está gerado e legível
- [ ] O resultado do PCA reporta a variância explicada acumulada dos 2 primeiros componentes

## Armadilhas
- **Sem padronizar, o KMeans agrupa só pela variável de maior escala.** `custo_medio_real` (~R$ 700) domina `volatilidade` (~0,03) e o cluster vira "capital cara vs. capital barata" — trivial e sem valor.
- Com apenas 17-27 pontos, qualquer *k* > 4 produz clusters de 2-3 capitais que não generalizam. Manter *k* entre 3 e 5.
- KMeans assume clusters esféricos e de tamanho similar. Se o dendrograma contar uma história muito diferente, confiar mais no hierárquico e dizer isso.
- Alternativa: clusterizar **séries temporais** em vez de vetores agregados (`tslearn`, DTW). Mais sofisticado e mais interessante, mas mais caro — só se sobrar tempo.
- Não confundir este cluster (de capitais) com clusterizar linhas UF×mês. Agrupar capitais é o que responde a pergunta interessante.
