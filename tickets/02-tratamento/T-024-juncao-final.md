# T-024 — Junção final: `fato_cesta_uf_mes`

| Campo | Valor |
|---|---|
| **Etapa** | 2 Tratamento |
| **Prioridade** | P0 |
| **Estimativa** | 3h |
| **Depende de** | T-011, T-013, T-020, T-023 |
| **Bloqueia** | T-025, T-030, T-031, T-040, T-041 |
| **Responsável** | — |
| **Status** | 🔲 A fazer |

## Contexto
O ticket que cumpre o requisito central do trabalho: **unir 3+ fontes por uma variável comum**. Aqui as tabelas de `interim/` viram a tabela analítica única. Depois daqui, nenhum notebook deve ler `interim/` — todos leem só este arquivo.

## Entregável
`data/processed/fato_cesta_uf_mes.parquet`
`outputs/tabelas/dicionario_variaveis.csv`

## Ordem de junção

```
calendario_uf_mes                       (grade completa: espinha)
  └─ LEFT JOIN cesta_capital_mes        on (sigla_uf, ano_mes)   → alvo
  └─ LEFT JOIN clima_uf_mes             on (sigla_uf, ano_mes)   → clima local
  └─ LEFT JOIN features_clima           on (sigla_uf, ano_mes)   → lags
  └─ LEFT JOIN safra_uf_mes  (pivot)    on (sigla_uf, ano_mes)   → safra local
  └─ LEFT JOIN clima_ponderado_mes      on (ano_mes)             → broadcast nacional
  └─ LEFT JOIN macro_br_mes             on (ano_mes)             → broadcast nacional
  └─ LEFT JOIN seca_uf_mes    [T-015]   on (sigla_uf, ano_mes)
  └─ LEFT JOIN ipca_subitem   [T-017]   on (sigla_uf, ano_mes)
```

**Sempre `LEFT JOIN` a partir do calendário. Nunca `INNER`** — perder linha silenciosamente é o erro mais caro desta etapa.

## Tarefas
- [ ] `src/tratamento/20_junta.py` seguindo exatamente a ordem acima
- [ ] Rodar `checa_join()` (T-020) após **cada** merge, com asserção de contagem de linhas
- [ ] Pivotar `safra_uf_mes` de longo para largo (uma coluna por produto) antes de juntar
- [ ] Construir as três versões do alvo:
  - `valor_cesta_nominal` (direto do DIEESE)
  - `valor_cesta_real` = nominal ÷ `ipca_indice_base` × 100 (base 2015-01)
  - `var_pct_cesta_mm` = variação % mês a mês, por UF ← **alvo principal do modelo**
- [ ] Descartar linhas sem alvo (UFs/meses fora da pesquisa DIEESE)
- [ ] Gerar o dicionário de variáveis: nome, descrição, fonte, unidade, granularidade nativa
- [ ] Salvar em Parquet

## Critérios de aceite
- [ ] Chave `(sigla_uf, ano_mes)` única — `df.duplicated(subset=chave).sum() == 0`
- [ ] Contagem de linhas confere: ~2.350 para o recorte de 17 capitais
- [ ] Nenhuma coluna com > 40% de nulos sem justificativa escrita no dicionário
- [ ] Cada `LEFT JOIN` está registrado no log com linhas antes/depois e taxa de match
- [ ] `valor_cesta_real` de 2015-01 ≈ `valor_cesta_nominal` de 2015-01 (validação do deflator)
- [ ] `var_pct_cesta_mm` tem média próxima de zero e desvio plausível (~2-4%)
- [ ] O dicionário cobre 100% das colunas
- [ ] **≥ 3 fontes distintas presentes na tabela final** — requisito do trabalho, verificar explicitamente

## Armadilhas
- **Broadcast é intencional, mas precisa ser consciente.** As colunas macro e de clima ponderado são idênticas para todas as UFs no mesmo mês. Elas explicam variação *no tempo*, nunca variação *entre capitais*. Se o modelo depender só delas, ele não está usando a dimensão geográfica dos dados — o T-041 precisa checar isso.
- Colisão de nomes de coluna: várias tabelas têm `chuva_mm_mes`. Usar `suffixes=("", "_pond")` explícito ou renomear antes do merge; senão o pandas cria `_x` e `_y` e ninguém mais sabe qual é qual.
- Após pivotar a safra, UFs que não produzem determinado produto ficam com `NaN`. Aqui `NaN` significa "não produz", não "dado faltante" — preencher com `0` é defensável, mas precisa ser decisão documentada, não acidente.
- Conferir que o deflacionamento usa a **mesma base** em todo o projeto. Base inconsistente entre notebooks gera números que não batem no relatório.
