# T-020 — Padronização de chaves e calendário-espinha

| Campo | Valor |
|---|---|
| **Etapa** | 2 Tratamento |
| **Prioridade** | P0 |
| **Estimativa** | 2h |
| **Depende de** | T-002 |
| **Bloqueia** | T-024 |
| **Responsável** | — |
| **Status** | 🔲 A fazer |

## Contexto
Cada coletor produz `ano_mes` de um jeito: string `"2020-01"`, `Timestamp`, `Period`, int `202001`. Um join entre tipos diferentes não falha — ele simplesmente não casa nada e devolve tudo `NaN`. Este ticket define o contrato único e o calendário completo que serve de espinha dorsal da junção.

## Entregável
`src/tratamento/chaves.py` (contrato de chaves + validador)
`data/processed/calendario_uf_mes.parquet` (grade completa UF × mês)

## Contrato de chaves
| Chave | Tipo canônico | Formato |
|---|---|---|
| `sigla_uf` | `str` categórica | 2 letras maiúsculas |
| `ano_mes` | `pd.Period[M]` | período mensal |

Toda tabela em `data/interim/` deve sair obedecendo esse contrato. Conversão para `Timestamp` só na hora de plotar.

## Tarefas
- [ ] Escrever em `chaves.py`:
  ```python
  def padroniza_chaves(df) -> pd.DataFrame        # força os tipos canônicos
  def valida_chaves(df, nome) -> None             # levanta erro se violar
  def checa_join(antes, depois, nome) -> None     # alerta se nº de linhas mudou
  ```
- [ ] Gerar `calendario_uf_mes.parquet`: produto cartesiano `dim_uf × todos os meses do período`. É a grade completa — 27 × 138 = 3.726 linhas
- [ ] Rodar `valida_chaves()` em todas as tabelas de `data/interim/` já produzidas e corrigir as que falharem
- [ ] Documentar o contrato no README do projeto

## Critérios de aceite
- [ ] `valida_chaves()` passa em 100% das tabelas de `data/interim/`
- [ ] O calendário tem exatamente `n_ufs × n_meses` linhas, sem duplicata
- [ ] `checa_join()` de fato dispara alerta num teste proposital com chave desalinhada
- [ ] Nenhuma tabela em `interim/` guarda `ano_mes` como string

## Armadilhas
- **Um join com tipos incompatíveis não dá erro** — retorna `NaN` em silêncio. Este é o bug mais insidioso do pipeline de junção. Por isso o `checa_join()` é obrigatório após cada merge, não opcional.
- `pd.Period` não é serializado por todos os writers de Parquet dependendo da versão. Se der problema, gravar como string `"YYYY-MM"` e reconverter na leitura — mas mantendo o contrato dentro do código.
- Fuso horário: nada aqui tem hora. Se algum `Timestamp` chegar com `tz`, remover, senão a comparação de datas gera falsos negativos.
