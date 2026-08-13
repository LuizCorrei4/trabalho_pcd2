# T-001 — Estrutura do repositório e ambiente

| Campo | Valor |
|---|---|
| **Etapa** | 0 Fundação |
| **Prioridade** | P0 |
| **Estimativa** | 1h |
| **Depende de** | — |
| **Bloqueia** | T-002, T-010, T-013 |
| **Responsável** | — |
| **Status** | 🔲 A fazer |

## Contexto
Nada começa antes de existir um lugar previsível para colocar os arquivos. A regra que sustenta a reprodutibilidade do projeto é: **`data/raw/` é imutável** — nenhum CSV é editado à mão, todo tratamento é script.

## Entregável
Árvore de pastas + `requirements.txt` + `.gitignore` + `README.md` na raiz.

## Tarefas
- [ ] Criar a árvore:
  ```
  data/raw/{dieese,inmet,sidra,conab,bcb,ana}/
  data/interim/ 
    data/interim/csv
    data/interim/parquet
  data/processed/
  src/coleta/  src/tratamento/  src/analise/
  notebooks/
  outputs/figuras/  outputs/tabelas/
  ```
- [ ] `requirements.txt` com: `pandas numpy requests pdfplumber sidrapy pyarrow matplotlib seaborn scikit-learn statsmodels xgboost shap jupyter`
- [ ] Criar ambiente virtual e instalar (`python -m venv .venv`)
- [ ] `.gitignore` ignorando `.venv/`, `data/raw/`, `__pycache__/`, `.ipynb_checkpoints/`
- [ ] `git init` + primeiro commit
- [ ] `src/config.py` com constantes compartilhadas: `DATA_RAW`, `DATA_INTERIM`, `DATA_PROCESSED`, `PERIODO_INICIO = "2015-01"`, `PERIODO_FIM`, lista de capitais

## Critérios de aceite
- [ ] `pip install -r requirements.txt` roda limpo em máquina zerada
- [ ] `import src.config` funciona de qualquer script do projeto
- [ ] Todos os caminhos de arquivo no projeto vêm de `config.py` — zero caminho absoluto hardcoded
- [ ] `git status` limpo com `data/raw/` populado (confirma que o `.gitignore` funciona)

## Armadilhas
- **Não versionar `data/raw/`** — os ZIPs do INMET passam de 1 GB somados e vão estourar o repositório.
- O caminho do projeto tem acento e espaço (`Prática Ciencia de Dados 2`). Usar `pathlib.Path` em todo lugar, nunca concatenação de string com `/` ou `\`.
- Fixar `encoding="utf-8"` explicitamente em toda leitura/escrita de texto — no Windows o padrão ainda pode ser `cp1252` e vai quebrar com acentos nos nomes das capitais.
