# T-012 — Coletor SIDRA/LSPA: estimativas de safra por UF

| Campo | Valor |
|---|---|
| **Etapa** | 1 Coleta |
| **Prioridade** | P0 |
| **Estimativa** | 3h |
| **Depende de** | T-002 |
| **Bloqueia** | T-022 |
| **Responsável** | — |
| **Status** | 🔲 A fazer |

## Contexto
Fonte das features de **oferta agrícola**. A tabela 6588 do LSPA é a mais valiosa do projeto depois do alvo: ela publica, mês a mês, a *estimativa vigente* da safra por UF e produto. A **revisão** dessa estimativa ("a produção esperada de feijão na BA caiu 8% neste mês") é o sinal de choque de oferta que realmente move preço — muito mais informativo que a produção realizada anual.

Também fornece os **pesos de produção por UF** que o T-022 usa para ponderar o clima.

## Entregável
`data/interim/safra_uf_mes.parquet` (LSPA 6588, longo: `sigla_uf × produto × ano_mes`)
`data/interim/producao_uf_ano.parquet` (PAM 1612/1613, para os pesos)

## Fonte
| Tabela | Conteúdo | Nível |
|---|---|---|
| **6588** (LSPA) | área plantada/colhida, produção, rendimento — estimativa revista mensalmente, set/2006→atual | BR, Região, **UF** |
| 1612 (PAM) | lavouras temporárias, realizado anual, com valor da produção | até município |
| 1613 (PAM) | lavouras permanentes, realizado anual | até município |

API: `https://apisidra.ibge.gov.br/values/...` ou `pip install sidrapy`. Sem chave.

## Produtos a coletar
Os que compõem a cesta DIEESE ou entram no seu custo:
`arroz`, `feijão`, `café`, `banana`, `batata-inglesa`, `tomate`, `trigo`, `mandioca`, `cana-de-açúcar` (açúcar), `soja` (óleo), `milho` (ração → carne e leite)

## Tarefas
- [ ] `src/coleta/03_sidra_lspa.py` com função `busca_tabela(tabela, variaveis, periodos, nivel="UF")`
- [ ] Coletar 6588 para todos os produtos da lista, período 2014→atual (1 ano a mais que o alvo, para lags)
- [ ] Coletar 1612 e 1613 por UF para os pesos de produção
- [ ] Converter o retorno da SIDRA (colunas `V`, `D1C`, `D2N`…) para nomes legíveis
- [ ] Mapear código IBGE de UF → `sigla_uf` via `dim_uf`
- [ ] Criar a coluna derivada `revisao_pct_prod` = variação % da estimativa em relação ao mês anterior, por `(sigla_uf, produto)`
- [ ] Salvar em formato longo (`produto` como coluna, não uma coluna por produto) — o pivot é no T-024

## Critérios de aceite
- [ ] Todos os 11 produtos presentes, com ≥ 1 UF cada
- [ ] Cobertura mensal contínua de 2014-01 até o fim do período, sem buracos silenciosos
- [ ] `sigla_uf` bate 100% com `dim_uf` (nenhum código órfão)
- [ ] Soma da produção por UF ≈ total Brasil da mesma tabela (tolerância 1%)
- [ ] `revisao_pct_prod` tem valores plausíveis (maioria entre -20% e +20%)

## Armadilhas
- A API SIDRA usa `"..."`, `"-"` e `"X"` como marcadores de dado ausente/não divulgado. Tratar todos como `NaN`, senão a coluna vira `object` e quebra a agregação.
- Limite de volume por requisição: quebrar em blocos por produto ou por ano. Requisição gigante retorna erro pouco descritivo.
- A tabela 6588 é **estimativa de safra anual revisada mensalmente**, não produção mensal. Não somar os 12 meses — isso multiplicaria a safra por 12. Cada mês é uma *fotografia da expectativa* para aquele ano-safra.
- Café e banana são lavoura permanente (tabela 1613), não temporária (1612).
