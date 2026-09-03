# Trabalho de Prática em Ciência de Dados II (SSC0957)

Este repositório contém a organização inicial e os códigos a serem desenvolvidos para o trabalho da disciplina, focando no cruzamento de dados heterogêneos para estudos sobre **crises climáticas e alimentares no cenário brasileiro**.

## 📚 Central de Documentação do Projeto

Para navegar com clareza pelo repositório, consulte os guias especializados:

| Documento | Público / Objetivo | O que você encontrará |
|---|---|---|
| 🛠️ [**Guia do Desenvolvedor & Arquitetura**](docs/guia_do_desenvolvedor.md) | Desenvolvedores e Revisores | Ciclo de vida dos dados, sistema de logging em 4 camadas, backups com rollback, contratos e como adicionar coletores. |
| 📡 [**Pacote de Coleta e Ingestão**](src/coleta/README.md) | Engenharia de Dados | Detalhes das 6 fontes (IPCA, INMET, Seca, Safra, BCB, Combustíveis), endpoints e granularidades. |
| 🧪 [**Pacote de Tratamento e Junção**](src/tratamento/README.md) | Ciência de Dados & Modelagem | Regras de agregação (mediana climática, ponderação por postos) e construção da tabela fato final. |
| 📋 [**Board de Tickets e Backlog**](tickets/README.md) | Toda a Equipe | Critérios de aceite, cronograma, dependências e status de cada tarefa (T-001 a T-051). |
| 📊 [**Dicionários de Variáveis**](outputs/tabelas/) | Modelagem & Estatística | Dicionários descritivos com unidade, fonte, granularidade nativa e % de nulos de cada coluna. |

---

## Estrutura do Repositório

Como o projeto é desenvolvido por 5 pessoas ao longo de 4 meses, adotamos uma organização escalável e profissional:

* `data/`: Diretório para os conjuntos de dados (Ignorado pelo Git, exceto estrutura).
  * `raw/`: Dados brutos, como baixados da fonte. **NUNCA modifique estes arquivos**.
  * `interim/`: Tabelas intermediárias produzidas pelos coletores (Parquet/CSV), antes da junção final.
  * `processed/`: Dados limpos e preparados que serão usados nos modelos (dim_uf e tabelas fatos).
* `notebooks/`: Jupyter Notebooks (.ipynb) utilizados para exploração de dados e prototipagem.
* `src/`: Scripts Python modulares e reutilizáveis:
  * `config.py`: **todos** os caminhos e constantes do projeto saem daqui — nenhum caminho absoluto espalhado.
  * `logging_config.py`: motor de auditoria em 4 camadas e gestão de backups com rollback automático.
  * `rede.py`: utilitários HTTP compartilhados (User-Agent, retentativas exponenciais).
  * `ufs.py`: tabela de UFs canônica baseada no `dim_uf.csv`.
  * `coleta/`: orquestrador CLI (`runner.py`) e submódulos das 6 fontes de dados. Ver [`src/coleta/README.md`](src/coleta/README.md).
  * `tratamento/`: orquestrador de junção e pipelines de agregação espacial e fatos. Ver [`src/tratamento/README.md`](src/tratamento/README.md).
* `outputs/`: Tabelas (`tabelas/`) e figuras (`figuras/`) geradas por script.
* `tickets/`: Backlog do projeto. Comece pelo [board](tickets/README.md).
* `docs/`: Documentação sobre as bases de dados, proposta e metodologia.

### Como rodar os coletores (Orquestrador Unificado)

O repositório conta com um **Orquestrador Central e Unificado** (`src/coleta/runner.py`) para baixar, atualizar e auditar todas as bases de dados de forma segura, reprodutível e idempotente:

```bash
# 1. Executar TODOS os coletores na sequência correta (padrão seguro: pula o que já existe)
python -m src.coleta.runner --all

# 2. Diagnóstico / Auditoria do estado das bases em disco (Dry-Run)
python -m src.coleta.runner --status

# 3. Executar apenas UMA fonte específica
python -m src.coleta.runner --fonte ipca          # IPCA Alimentos (16 Áreas Urbanas)
python -m src.coleta.runner --fonte inmet         # Clima BDMEP (INMET)
python -m src.coleta.runner --fonte seca          # Monitor de Secas (ANA)
python -m src.coleta.runner --fonte safra         # Estimativas de Safra (LSPA/PAM)
python -m src.coleta.runner --fonte bcb           # Variáveis Macroeconômicas (BCB/SGS)
python -m src.coleta.runner --fonte combustiveis  # Preços de Combustíveis (ANP)

# 4. Executar o Pipeline de Tratamento e Junção Final (Etapa 2)
python -m src.coleta.runner --tratamento         # Executa clima_uf_mes -> junta (fato) -> combustíveis

# 5. Executar a Esteira Completa End-to-End (Coleta + Tratamento)
python -m src.coleta.runner --completo           # Baixa/atualiza tudo e gera as tabelas fatos finais

# 6. Executar um SUBCONJUNTO selecionado
python -m src.coleta.runner --fontes ipca,bcb,combustiveis
python -m src.coleta.runner --fontes inmet,seca

# 7. Políticas de Sobrescrita Granular (--overwrite)
python -m src.coleta.runner --all --overwrite skip       # Padrão: pula arquivos completos
python -m src.coleta.runner --fonte ipca --force         # Força re-download e substituição total
python -m src.coleta.runner --fonte bcb --backup         # Cria cópia de segurança antes de sobrescrever
python -m src.coleta.runner --all --interactive          # Pergunta interativamente antes de sobrescrever
```

#### Arquitetura de Logging e Auditoria (4 Camadas)
1. **Console / Terminal:** Resumo em tempo real com tabela visual formatada.
2. **Log em Disco (DEBUG):** `logs/execucoes/coleta_YYYYMMDD_HHMMSS.log` (rastreabilidade completa de URLs, tempos e exceções).
3. **Manifesto JSON:** `logs/execucoes/coleta_YYYYMMDD_HHMMSS_manifest.json` (métricas estruturadas de execução por módulo).
4. **Log Transacional CSV:** `data/raw/{fonte}/_download_log.csv` (histórico atômico por requisição/chunk).


## Configuração Inicial do Ambiente

Para garantir que todos do grupo usem as mesmas versões de bibliotecas, recomendamos o uso de um ambiente virtual. Use **uma** das duas opções abaixo.

### Opção A — conda (recomendada)

```bash
conda env create -f environment.yml   # cria o ambiente "pcd2"
conda activate pcd2
```

O [`environment.yml`](environment.yml) declara o que é necessário para rodar os
coletores da etapa de coleta. As bibliotecas das etapas seguintes (geopandas,
xgboost, shap...) estão no `requirements.txt` e devem ser acrescentadas ao
`environment.yml` quando aquelas etapas começarem.

### Opção B — venv + pip

1. **Crie o ambiente virtual:**
   ```bash
   python3 -m venv .venv
   ```
   Em algumas distribuições Linux isto cria um ambiente sem `pip`; nesse caso
   instale o pacote `python3-venv` do sistema antes.

2. **Ative o ambiente:**
   * Linux/Mac:
     ```bash
     source .venv/bin/activate
     ```
   * Windows:
     ```bash
     .venv\Scripts\activate
     ```

3. **Instale as dependências:**
   ```bash
   pip install -r requirements.txt
   ```

## Próximos Passos (Dicas de Fluxo de Trabalho)

* **Git / GitHub:** Antes de iniciar o trabalho do dia, sempre faça um `git pull` para baixar as atualizações dos colegas.
* Trabalhem com **Branches** para evitar conflitos na branch `main`.
* Acompanhem o escopo definido no arquivo `docs/possiveis_perguntas.md`.
