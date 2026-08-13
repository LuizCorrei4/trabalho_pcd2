# T-002 — Construir a tabela-dimensão `dim_uf.csv`

| Campo | Valor |
|---|---|
| **Etapa** | 0 Fundação |
| **Prioridade** | P0 |
| **Estimativa** | 1h |
| **Depende de** | T-001 |
| **Bloqueia** | T-011, T-012, T-014, T-015, T-016, T-017, T-020 |
| **Responsável** | — |
| **Status** | 🔲 A fazer |

## Contexto
Cada fonte identifica o mesmo lugar de um jeito diferente: o DIEESE escreve `"Belém"`, o INMET dá lat/lon de estação, o SIDRA usa código IBGE `15`, a CONAB usa `PA`. Sem uma tabela canônica que amarre tudo, cada junção vira uma sessão de `str.replace()` e o erro passa despercebido.

Este ticket é 1 hora de trabalho que destrava todos os outros. Fazer **antes** de qualquer coletor.

## Entregável
`data/processed/dim_uf.csv` — 27 linhas, uma por UF.

## Schema
| Coluna | Tipo | Exemplo |
|---|---|---|
| `sigla_uf` | str(2) | `SP` |
| `nome_uf` | str | `São Paulo` |
| `capital` | str | `São Paulo` |
| `capital_norm` | str | `sao paulo` (minúscula, sem acento — chave de match) |
| `cod_ibge_uf` | int | `35` |
| `cod_ibge_capital` | int | `3550308` |
| `lat` / `lon` | float | `-23.5505` / `-46.6333` |
| `regiao` | str | `Sudeste` |
| `no_dieese` | bool | `True` se está nas 17 capitais da série longa |

## Tarefas
- [ ] Buscar UFs: `GET https://servicodados.ibge.gov.br/api/v1/localidades/estados`
- [ ] Buscar municípios capitais e extrair `cod_ibge_capital`
- [ ] Preencher lat/lon das capitais (usar a API de malhas do IBGE ou uma constante manual — são só 27 pares)
- [ ] Criar `capital_norm` com `unicodedata.normalize('NFKD', s).encode('ascii','ignore')` + `.lower().strip()`
- [ ] Marcar `no_dieese` para as 17 capitais da série histórica longa
- [ ] Escrever helper reutilizável em `src/tratamento/chaves.py`:
  ```python
  def normaliza_nome(s: str) -> str: ...
  def mapear_para_uf(nomes: pd.Series) -> pd.Series: ...   # nome de cidade → sigla_uf
  ```

## Critérios de aceite
- [ ] Exatamente 27 linhas, `sigla_uf` única, zero nulos
- [ ] `mapear_para_uf()` acerta 27/27 num teste com os nomes escritos **com acento, sem acento e em CAIXA ALTA**
- [ ] `cod_ibge_capital` tem 7 dígitos e seus 2 primeiros batem com `cod_ibge_uf`

## Armadilhas
- Toda junção geográfica do projeto deve passar por `sigla_uf`, **nunca** por nome de cidade direto.
- Brasília/DF: o DIEESE às vezes escreve `Brasília` e às vezes `Distrito Federal`. Tratar os dois no mapeamento.
- Cuidado com `cod_ibge_uf` lido como string com zero à esquerda (`"11"` vs `11`). Fixar o tipo na leitura: `dtype={"cod_ibge_uf": int}`.
