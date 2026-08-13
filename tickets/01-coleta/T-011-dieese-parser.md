# T-011 — Parser DIEESE: PDF → variável-alvo ⚠️ GARGALO

| Campo | Valor |
|---|---|
| **Etapa** | 1 Coleta |
| **Prioridade** | P0 |
| **Estimativa** | 8h |
| **Depende de** | T-010, T-002 |
| **Bloqueia** | T-024 (e portanto toda a modelagem) |
| **Responsável** | — |
| **Status** | 🔲 A fazer |

## Contexto
**Este é o ticket mais arriscado do projeto.** Ele produz a variável-alvo; sem ele não há modelo. O layout dos PDFs do DIEESE varia entre anos e a tabela "Todas as capitais" nem sempre está na mesma página. Deve começar no dia 1 e ter dedicação exclusiva.

Se este ticket travar por mais de 2 dias, acionar o plano B (ver Armadilhas) em vez de insistir.

## Entregável
`data/interim/cesta_capital_mes.parquet`

## Schema
| Coluna | Tipo | Descrição |
|---|---|---|
| `sigla_uf` | str(2) | via `dim_uf` |
| `ano_mes` | period[M] | mês de **referência** da pesquisa |
| `valor_cesta_nominal` | float | R$ |
| `horas_trabalho` | float | horas necessárias para comprar a cesta |
| `pct_salario_minimo` | float | % do salário mínimo líquido |
| `arquivo_origem` | str | rastreabilidade |

## Tarefas
- [ ] Explorar 3 PDFs de anos distintos (2015, 2020, 2026) e mapear a estrutura da tabela em cada um
- [ ] `src/coleta/02_dieese_parser.py` usando `pdfplumber.extract_tables()`; se falhar, `extract_text()` + regex por linha
- [ ] Localizar a página da tabela por busca textual (`"Todas as capitais"` / `"Capitais"`), **não** por número de página fixo
- [ ] Normalizar números brasileiros: `"1.234,56"` → `1234.56`
- [ ] Mapear nome da capital → `sigla_uf` com `mapear_para_uf()` do T-002
- [ ] Extrair o mês de **referência** (não o de publicação) — o relatório de fevereiro traz os dados de janeiro
- [ ] Log de linhas extraídas por arquivo
- [ ] Validação manual: conferir 10 meses sorteados contra o PDF aberto na mão

## Critérios de aceite
- [ ] ≥ 17 linhas para cada mês do período (27 a partir de 2025-08)
- [ ] `valor_cesta_nominal` entre R$ 200 e R$ 1.500 em 100% das linhas — fora disso é erro de parsing, não realidade
- [ ] Zero duplicatas em `(sigla_uf, ano_mes)`
- [ ] Variação mês a mês > 25% em qualquer capital é sinalizada e revisada manualmente
- [ ] Os 10 meses da validação manual batem exatamente com o PDF
- [ ] Série de São Paulo plotada é contínua e monotonicamente plausível (sem serrote nem degrau artificial)

## Armadilhas
- **Mês de referência ≠ mês de publicação.** Errar isso desloca a série inteira em 1 mês e destrói silenciosamente toda a análise de lag. É o erro mais perigoso do projeto inteiro.
- Layout muda entre anos. Escrever o parser tolerante a variação e **falhar alto** (exceção) quando não reconhecer, em vez de retornar linha vazia.
- Separador decimal brasileiro: `1.234,56`. Um `float("1.234,56")` mal tratado vira `1.234` e ninguém percebe.
- Desde abril/2018 os **preços por produto individual** não são públicos — só o valor agregado. Não perder tempo tentando extrair item a item; usar T-017 (IPCA por subitem) como proxy.
- **Plano B se travar:** usar o sistema de consulta em https://www.dieese.org.br/cesta/ (inspecionar a requisição do formulário no DevTools e replicá-la), ou reduzir o escopo para as 17 capitais principais e um período mais curto com layout estável.
