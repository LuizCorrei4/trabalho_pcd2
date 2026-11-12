# Auditoria das evidências da EDA de safras

**Data:** 05/11/2026. **Escopo:** leitura das células e saídas gravadas do [notebook 13](../../../notebooks/13_eda_safras_oferta.ipynb), inspeção do código associado e cálculos descritivos sobre os Parquets locais. O notebook completo e o pipeline de coleta não foram reexecutados. Os números desta nota descrevem a versão local, não uma nova consulta ao IBGE.

As células abaixo são contadas a partir de zero, na ordem do JSON do notebook. A interpretação está no [estudo](02_estudo_safras_oferta.md); as ações estão no [plano](04_plano_decisoes_safras_oferta.md).

## 1. Base conferida em disco

| Item | Resultado |
|---|---|
| Fato | 2.088 linhas × 108 colunas |
| Chave `(sigla_uf, ano_mes)` | Nenhuma duplicata |
| Meses distintos | 138, de 2015-01 a 2026-06 |
| UFs | AC, BA, CE, DF, ES, GO, MA, MG, MS, PA, PE, PR, RJ, RS, SE, SP |
| Meses por UF | AC, MA e SE: 98; demais 13 UFs: 138 |
| Linhas de janeiro na fato | 180 |
| Safra interim | 44.847 linhas × 11 colunas |
| Dezembros disponíveis para agregação anual | 2014 a 2025: 12 anos |

O painel é **desbalanceado**: 16 × 138 = 2.208, não 2.088. Um `shift(1)` por UF representa um mês anterior apenas se o calendário for contíguo. A função em [eda_utils.py](../../../src/analise/eda_utils.py) agrupa por UF, mas não cria meses ausentes nem verifica continuidade; essa garantia precisa ser demonstrada para cada entrada usada.

## 2. Pontos que exigem revisão

| Local no notebook | Evidência observada | Consequência / ação |
|---|---|---|
| Célula 2, descrição da base | Multiplicação 16 × 138 associada a 2.088 linhas | Descrever o painel como desbalanceado e mostrar cobertura por UF |
| Células 3–4, auditoria de correlações | `.corr()` usa Pearson; comparação anterior é descrita como Spearman | Calcular ambos na mesma amostra antes de atribuir diferenças ao pareamento espacial |
| Célula 4, interpretação | Magnitudes próximas de −0,15 chamadas de altas e usadas para afirmar determinantes/transmissão | Reportar associação fraca e incerteza; retirar conclusão causal |
| Célula 6, concentração | Participações calculadas a partir de médias por UF na fato, com coberturas diferentes | Não tratar como participação nacional; usar 27 UFs e ano/janela comum |
| Célula 10, `n_validos` | Texto combina 27 UFs, sete janeiros e painel com 16 UFs/138 meses | Na fato há 180 janeiros: 2.088 − 180 = 1.908; a disponibilidade por cultura ainda precisa ser considerada |
| Célula 9, teto de revisão | Conta `abs() >= 50` na coluna já limitada | Não distingue valor originalmente igual a 50 de valor alterado pelo corte |
| Célula 10, conclusão sobre corte | Fração pequena no teto é apresentada como prova de preservar choques autênticos | Comparar bruto/tratado e auditar eventos; frequência baixa não estabelece relevância econômica baixa |
| Célula 10, mediana | Mediana próxima de zero usada para afirmar ausência de viés e simetria | Viés de previsão requer confrontar estimativas com realização/referência final; mediana não demonstra simetria |
| Célula 12, referência BR | Média simples entre UFs rotulada média nacional | Renomear como média simples das UFs observadas ou usar série nacional/ponderação adequada |
| Células 12–14, caso RS | Datas e números de anotações fixos; narrativa atribui resposta à seca | Derivar valores da tabela, identificar subitem e confrontar mecanismos concorrentes |
| Célula 13, volatilidade | Usa `df` inteiro, mas caixa textual fixa afirma 2018–2024 | Definir janela e gerar estatísticas do mesmo subconjunto plotado |
| Células 16–17, H2 | Correlações em níveis; Mann–Whitney entre dois blocos; sem análise do preço do feijão | Não declarar confirmação integral nem quebra estrutural identificada |
| Célula 18, handoff | Lags de 1–3 meses descritos como identificados | Repassar como candidatos exploratórios, sujeitos a incerteza e validação temporal |

## 3. Conferência da H2

O cálculo abaixo reproduz a agregação de dezembro do notebook, incluindo todas as UFs da camada interim. Os p-valores são **nominais**, sem correção por dependência temporal ou comparações múltiplas.

| Par de áreas | Spearman nos níveis, n=12 | p nominal | Spearman nas primeiras diferenças, n=11 | p nominal |
|---|---:|---:|---:|---:|
| Soja × arroz | −0,8322 | 0,000785 | +0,1909 | 0,5739 |
| Soja × feijão | −0,8811 | 0,000153 | +0,1727 | 0,6115 |

Para arroz e feijão, o Mann–Whitney unilateral entre 2014–2018 e 2019–2025 retorna U=35 e p≈0,001263. Isso reproduz o número do notebook; a validade de uma interpretação de ruptura ou causalidade não decorre dessa reprodução.

O diagnóstico em diferenças é uma análise de sensibilidade, não um teste definitivo de substituição. A amostra é curta e agregada, e mudanças de composição regional continuam possíveis.

## 4. Revisões antes do corte

Foi feito um `inner merge` da safra interim com as chaves da fato. Assim, a comparação usa o mesmo universo UF × mês do notebook, sem acrescentar as UFs excluídas do alvo. A coluna bruta tem 18.014 valores não nulos entre as culturas, incluindo **seis valores não finitos**.

| Cultura | Revisões não nulas | `abs(raw) > 50` | `abs(raw) == 50` |
|---|---:|---:|---:|
| Arroz | 1.768 | 17 | 1 |
| Banana | 1.837 | 6 | 0 |
| Batata-inglesa | 1.054 | 11 | 0 |
| Café | 1.602 | 9 | 0 |
| Cana-de-açúcar | 1.899 | 4 | 0 |
| Feijão | 1.908 | 13 | 0 |
| Mandioca | 1.908 | 2 | 0 |
| Milho | 1.908 | 17 | 0 |
| Soja | 1.409 | 5 | 0 |
| Tomate | 1.733 | 16 | 0 |
| Trigo | 988 | 14 | 1 |

São 114 valores acima do limite em módulo (aproximadamente 0,633% dos não nulos), incluindo os seis infinitos, e dois valores originalmente no limite. Essa contagem não classifica os casos como erro ou choque real. É preciso examinar produção anterior, produção atual, UF, cultura e data. A transformação `.clip()` em [24_junta.py](../../../src/tratamento/24_junta.py) também pode converter infinito em um extremo finito; por isso a flag de não finito deve ser preservada antes do corte.

Na coleta, [safra/coletor.py](../../../src/coleta/safra/coletor.py) calcula `pct_change()` agrupado por UF, produto e ano-safra. O `NaN` de janeiro é consequência dessa construção. Para a auditoria futura, distinguir zero anterior, base positiva pequena, ausência de observação e revisão genuína.

## 5. Estatísticas da volatilidade na janela efetivamente usada

Desvio-padrão amostral (`ddof=1`), mínimo e máximo da variação mensal dos preços na fato completa. As unidades são pontos percentuais da taxa mensal. Cada coluna possui 2.088 observações.

| Subitem | Desvio-padrão | Mínimo | Máximo |
|---|---:|---:|---:|
| Arroz | 3,229 | −8,150 | +41,940 |
| Óleo de soja | 4,613 | −13,490 | +39,330 |
| Batata-inglesa | 15,276 | −40,960 | +77,040 |
| Tomate | 17,018 | −44,860 | +89,110 |

Esses números diferem do texto fixo na célula 13. O contraste entre subitens permanece, mas extremos maiores devem ser auditados, sem serem rotulados automaticamente como erros. A estatística empilhada também mistura heterogeneidade regional; complementar com dispersão por UF em janela comum.

## 6. Reprodução dos diagnósticos centrais

Executar a partir da raiz com o ambiente do projeto. O trecho lê as bases, não altera arquivos. `ano_mes` é normalizado por string porque a fato usa um tipo temporal que pode ser `Period`.

```python
import numpy as np
import pandas as pd
from scipy import stats

fato = pd.read_parquet("data/processed/fato_alimentos_combustiveis_uf_mes.parquet")
safra = pd.read_parquet("data/interim/safra_uf_mes.parquet")
for frame in (fato, safra):
    frame["ano_mes"] = pd.to_datetime(frame["ano_mes"].astype(str))

print(fato.groupby("sigla_uf").size())
print("Janeiros:", fato["ano_mes"].dt.month.eq(1).sum())
anual = safra[safra["ano_mes"].dt.month.eq(12)].copy()
anual["ano"] = anual["ano_mes"].dt.year
area = anual.groupby(["ano", "produto"])["area_plantada_ha"].sum(min_count=1).unstack()
for cultura in ("arroz", "feijao"):
    par = area[["soja", cultura]].dropna()
    mudanca = par.diff().dropna()
    print(cultura, stats.spearmanr(par["soja"], par[cultura]))
    print("Diferenças:", stats.spearmanr(mudanca["soja"], mudanca[cultura]))

bruta = safra.merge(fato[["sigla_uf", "ano_mes"]],
                   on=["sigla_uf", "ano_mes"], validate="many_to_one")
print(bruta.groupby("produto")["revisao_pct_prod"].agg(
    n="count", acima_limite=lambda s: s.abs().gt(50).sum(),
    no_limite=lambda s: s.abs().eq(50).sum()))
print("Não finitos:", (bruta["revisao_pct_prod"].notna()
      & ~np.isfinite(bruta["revisao_pct_prod"])).sum())
```

Para atualizar este estudo, salvar os resultados e o período exato junto da nova versão. Identificadores SHA-256 da conferência atual:

```text
notebooks/13_eda_safras_oferta.ipynb
923b35fb00b0b9588257674f37bc320c59efea7807457c35d01fabce3c4999b5
data/processed/fato_alimentos_combustiveis_uf_mes.parquet
4d53d74f1a565424bb9d4f10d4f78f61af703c1d5e08510a0c91f93289847f0b
data/interim/safra_uf_mes.parquet
8485fab0b5e3b861bc7f49368c883db92196f6cbdafe4e8f49be0b899a18a59c
```
