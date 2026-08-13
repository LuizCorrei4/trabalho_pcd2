# T-012 — Coletor SIDRA/LSPA: estimativas de safra por UF

| Campo | Valor |
|---|---|
| **Etapa** | 1 Coleta |
| **Prioridade** | P0 |
| **Estimativa** | 3h |
| **Depende de** | T-002 |
| **Bloqueia** | T-022 |
| **Responsável** | — |
| **Status** | ✅ Feito |

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
- [x] `src/coleta/03_sidra_lspa.py` com função `busca_tabela(tabela, variaveis, periodos, nivel="UF")`
- [x] Coletar 6588 para todos os produtos da lista, período 2014→atual (1 ano a mais que o alvo, para lags)
- [x] Coletar 1612 e 1613 por UF para os pesos de produção
- [x] Converter o retorno da SIDRA (colunas `V`, `D1C`, `D2N`…) para nomes legíveis
- [x] Mapear código IBGE de UF → `sigla_uf` via `dim_uf`
- [x] Criar a coluna derivada `revisao_pct_prod` = variação % da estimativa em relação ao mês anterior, por `(sigla_uf, produto)`
- [x] Salvar em formato longo (`produto` como coluna, não uma coluna por produto) — o pivot é no T-024

## Critérios de aceite
- [x] Todos os 11 produtos presentes, com ≥ 1 UF cada
- [x] Cobertura mensal contínua de 2014-01 até o fim do período, sem buracos silenciosos
- [x] `sigla_uf` bate 100% com `dim_uf` (nenhum código órfão)
- [x] Soma da produção por UF ≈ total Brasil da mesma tabela (tolerância 1%)
- [x] `revisao_pct_prod` tem valores plausíveis (maioria entre -20% e +20%)

## Armadilhas
- A API SIDRA usa `"..."`, `"-"` e `"X"` como marcadores de dado ausente/não divulgado. Tratar todos como `NaN`, senão a coluna vira `object` e quebra a agregação.
- Limite de volume por requisição: quebrar em blocos por produto ou por ano. Requisição gigante retorna erro pouco descritivo.
- A tabela 6588 é **estimativa de safra anual revisada mensalmente**, não produção mensal. Não somar os 12 meses — isso multiplicaria a safra por 12. Cada mês é uma *fotografia da expectativa* para aquele ano-safra.
- Café e banana são lavoura permanente (tabela 1613), não temporária (1612).

## Notas da implementação
Script: `src/coleta/03_sidra_lspa.py` · QA: `data/interim/qa_T-012_sidra.md`

- **Café na 6588 não tem categoria "total".** A categoria `40527` ("9/10 Café total") existe nos metadados mas retorna `-` em todos os meses; só arábica (`39454`) e canephora (`39455`) são publicadas. O script soma as duas. Sintoma se alguém trocar isso: café com produção zero.
- **`revisao_pct_prod` é calculada dentro do mesmo `ano_safra`, com janeiro sempre `NaN`.** Dezembro/2015 e janeiro/2016 falam de safras diferentes — a variação entre eles não é revisão de estimativa, é troca de ano-safra. Sem isso a feature ganha um salto falso de ±100% todo janeiro.
- Safras múltiplas (feijão 1ª/2ª/3ª, milho 1ª/2ª, batata 1ª/2ª/3ª) são somadas no produto canônico. **Rendimento não pode ser somado** — é recalculado como produção/área colhida.
- Usar `groupby().sum(min_count=1)` e nunca `pivot_table(aggfunc="sum")` ao empilhar as variáveis: o segundo transforma grupo todo-`NaN` em `0` e cria exatamente o buraco silencioso que o critério de aceite quer pegar.
- Além dos dois parquets, o script grava os `.csv` equivalentes (o `.gitignore` versiona csv e ignora parquet) e o retorno bruto em `data/raw/sidra/`.