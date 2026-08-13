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
- Para série mais longa, verificar as tabelas 1419 e 7062 (metodologias/períodos anteriores)

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
- **O IPCA não cobre as 27 capitais** — são ~16 áreas de pesquisa. Isso reduz o número de UFs disponíveis para qualquer análise que use esta fonte. Não é motivo para descartar, mas o relatório precisa dizer.
- A tabela 7060 começa em **jan/2020**. Para o período 2015-2019 é preciso emendar com a tabela da metodologia anterior — emenda de série exige cuidado e deve ser documentada.
- O IPCA mede **variação**, não nível de preço. Não é comparável em reais com o valor da cesta do DIEESE; só as variações percentuais são comparáveis.
- Como fonte auxiliar, esta tabela também serve para **validar o T-011**: a variação do grupo "Alimentação no domicílio" do IPCA deve correlacionar fortemente com a variação da cesta DIEESE na mesma capital. Se não correlacionar, há erro no parser. É um bom teste cruzado.
