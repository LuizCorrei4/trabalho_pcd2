# T-017 — Coletor IPCA por subitem (SIDRA 7060)

| Campo | Valor |
|---|---|
| **Etapa** | 1 Coleta |
| **Prioridade** | P2 (opcional — **compensa a limitação do DIEESE**) |
| **Estimativa** | 2h |
| **Depende de** | T-002 |
| **Bloqueia** | — |
| **Responsável** | — |
| **Status** | 🔲 A fazer |

## Contexto
O DIEESE fechou o acesso público aos preços por produto individual em 2018 (ver T-011). Isso limita o alvo ao valor agregado da cesta e impede responder "o clima afeta mais o arroz ou o tomate?".

O IPCA por subitem resolve isso: o IBGE publica variação de preço de arroz, feijão, carne, tomate, batata etc. por **Região Metropolitana**, mensalmente. Serve como alvo alternativo por produto e permite uma análise muito mais rica que a do valor agregado sozinho.

## Entregável
`data/interim/ipca_subitem_rm_mes.parquet`

## Fonte
- Tabela SIDRA 7060 — *IPCA: variação mensal, acumulada no ano, acumulada em 12 meses e peso mensal* (mensal, a partir de jan/2020)
- https://sidra.ibge.gov.br/tabela/7060
- ~~Para série mais longa, verificar as tabelas 1419 e 7062~~ → **verificado** em [`01_exploracao_ipca_subitem`](../../notebooks/01_exploracao_ipca_subitem.ipynb): a emenda correta é a **1419** (jan/2012 → dez/2019), mesmos níveis territoriais e mesmos códigos de subitem. A **7062 não serve** — é o **IPCA-15**, índice diferente, não a metodologia anterior.

## ✅ Nível geográfico — resolvido (ver notebook)
A tabela **não tem nível de UF**: `nivelTerritorial` = `N1` (Brasil), `N6` (município), `N7` (RM). Buscar `N3` devolve **HTTP 404**.

As áreas de pesquisa são **16** — e é preciso concatenar **os dois níveis** (`N7` = 10 RMs + `N6` = 6 municípios); quem buscar só `N7` perde o DF, Goiânia, Campo Grande, São Luís, Aracaju e Rio Branco.

Mapeamento área → UF pelos **2 primeiros dígitos do código IBGE** (não pelo nome: `N7` vem `"Belém - PA"`, `N6` vem `"Rio Branco"`).

| | UFs |
|---|---|
| **Com IPCA (16)** | AC, BA, CE, DF, ES, GO, MA, MG, MS, PA, PE, PR, RJ, RS, SE, SP |
| **Sem cobertura (11)** | AL, AM, AP, **MT**, PB, PI, RN, RO, RR, SC, TO |

⚠️ **MT** — maior produtor de grãos do país — fica de fora. As UFs onde o clima afeta a produção não são as mesmas onde o preço é medido.

## Subitens de interesse
`arroz`, `feijão-carioca`, `carne bovina` (vários cortes), `leite longa vida`, `pão francês`, `café moído`, `açúcar`, `óleo de soja`, `banana`, `batata-inglesa`, `tomate`, `farinha de mandioca`, `manteiga`

## Tarefas
- [ ] `src/coleta/07_ipca_subitem.py` usando `sidrapy` ou a API SIDRA direta
- [ ] Coletar variação mensal e peso, por subitem, por Região Metropolitana
- [ ] Mapear **RM → `sigla_uf`** (cada RM pesquisada pelo IPCA pertence a uma UF; algumas UFs não têm RM pesquisada)
- [ ] Documentar quais UFs ficam sem cobertura
- [ ] Construir índice acumulado por subitem × RM, base fixa
- [ ] Verificar o período disponível e ajustar o recorte do projeto se necessário

## Critérios de aceite
- [ ] Todos os subitens da lista presentes, ou a ausência justificada
- [ ] Mapeamento RM → UF completo e documentado, com as UFs sem cobertura listadas explicitamente
- [ ] Sanidade: o pico do preço do arroz em 2020 e o do café em 2024-2025 aparecem claramente na série

## Armadilhas
- **O IPCA não cobre as 27 capitais** — confirmado: **16 áreas**, 11 UFs sem dado (lista acima). Não é motivo para descartar, mas o relatório precisa dizer. **Nunca plotar mapa das 27 UFs com esta fonte.**
- A tabela 7060 começa em **jan/2020**. Para o período 2015-2019 emendar com a **1419** (não a 7062).
- **3 das 16 áreas entram só em mai/2018** (Rio Branco, São Luís, Aracaju). Em 2015-2018 a cobertura real é de **13 áreas**, não 16.
- **`carne bovina` não existe como subitem** — o IPCA publica ~15 cortes separados (acém, alcatra, patinho, costela…). O agregado mais próximo é o item `1107.Carnes` (id `7283`), que mistura bovina, suína e carneiro. Escolher cortes explicitamente e justificar.
- **`feijão-carioca`** é `1101073.Feijão - carioca (rajado)` (id `12222`) — hífen e parêntese quebram match por string. Buscar por `id`.
- **O SIDRA devolve `"..."`, `".."` e `"-"` como texto** na coluna de valor. `astype(float)` levanta exceção; usar `pd.to_numeric(errors="coerce")`.
- O IPCA mede **variação**, não nível de preço. Não é comparável em reais com o valor da cesta do DIEESE; só as variações percentuais são comparáveis.
- Como fonte auxiliar, esta tabela também serve para **validar o T-011**: a variação do grupo "Alimentação no domicílio" do IPCA deve correlacionar fortemente com a variação da cesta DIEESE na mesma capital. Se não correlacionar, há erro no parser. É um bom teste cruzado.
