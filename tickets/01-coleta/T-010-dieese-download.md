# T-010 — Baixar os PDFs mensais do DIEESE

| Campo | Valor |
|---|---|
| **Etapa** | 1 Coleta |
| **Prioridade** | P0 |
| **Estimativa** | 2h |
| **Depende de** | T-001 |
| **Bloqueia** | T-011 |
| **Responsável** | — |
| **Status** | 🔲 A fazer |

## Contexto
A variável-alvo do projeto (valor da cesta básica por capital/mês) só existe publicamente dentro dos relatórios mensais em PDF do DIEESE. Este ticket só baixa; a extração é o T-011.

## Entregável
`data/raw/dieese/{ANOMES}cestabasica.pdf` — ~140 arquivos (2015-01 a 2026-06)
`data/raw/dieese/_download_log.csv` — status de cada tentativa

## Fonte
- Índice: https://www.dieese.org.br/analisecestabasica/analiseCestaBasicaAnteriores.html
- Padrão de URL: `https://www.dieese.org.br/analisecestabasica/{ANO}/{ANOMES}cestabasica.pdf`
  - ex.: `.../2026/202601cestabasica.pdf`

## Tarefas
- [ ] `src/coleta/01_dieese_download.py` iterando ano/mês do período
- [ ] Gravar log com: `ano_mes`, `url`, `status_http`, `tamanho_bytes`, `ok`
- [ ] Ser educado com o servidor: `time.sleep(1)` entre requisições, `User-Agent` identificável
- [ ] Idempotência: se o arquivo já existe e tem tamanho > 10 KB, pular
- [ ] Fallback: para os meses em que o padrão de URL falhar, raspar o link real da página de índice

## Critérios de aceite
- [ ] ≥ 95% dos meses do período baixados com sucesso
- [ ] Os meses faltantes estão listados explicitamente no log com o motivo
- [ ] Rodar o script duas vezes seguidas não rebaixa nada (idempotente)
- [ ] Nenhum arquivo com 0 bytes ou que seja HTML de erro salvo com extensão `.pdf`

## Armadilhas
- Anos mais antigos usam padrões de URL diferentes (`analiseCestaBasica{ANOMES}.pdf` sem a pasta do ano). Se o padrão principal der 404, tentar as variantes antes de marcar como falha.
- Verificar que o conteúdo é PDF de verdade: os primeiros bytes devem ser `%PDF`. Servidor pode devolver 200 com página de erro.
- Se o download em massa começar a ser bloqueado, aumentar o sleep. Não paralelizar — são só 140 arquivos.
