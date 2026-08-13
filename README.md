# Trabalho de Prática em Ciência de Dados II (SSC0957)

Este repositório contém a organização inicial e os códigos a serem desenvolvidos para o trabalho da disciplina, focando no cruzamento de dados heterogêneos para estudos sobre **crises climáticas e alimentares no cenário brasileiro**.

## Estrutura do Repositório

Como o projeto será desenvolvido por 5 pessoas ao longo de 4 meses, adotamos uma organização de pastas escalável e profissional:

* `data/`: Diretório para os conjuntos de dados (Ignorado pelo Git, exceto estrutura).
  * `raw/`: Dados brutos, como baixados da fonte. **NUNCA modifique estes arquivos**. Só os ZIPs do INMET somam ~1,27 GB, então esta pasta nunca vai para o Git.
  * `interim/`: Tabelas intermediárias produzidas pelos coletores (Parquet/CSV), antes da junção final.
  * `processed/`: Dados limpos e preparados que serão usados nos modelos.
* `notebooks/`: Jupyter Notebooks (.ipynb) utilizados para exploração de dados, prototipagem e experimentação. Sugere-se nomear de forma sequencial, ex: `01_nome_analise_descritiva.ipynb`.
* `src/`: Scripts Python modulares e reutilizáveis. Organização:
  * `config.py`: **todos** os caminhos e constantes do projeto saem daqui — nenhum caminho absoluto espalhado pelo código.
  * `rede.py`: utilitários HTTP compartilhados (User-Agent, retentativa, download atômico).
  * `ufs.py`: tabela de UFs; usa o `dim_uf.csv` do T-002 quando existe e cai para a API do IBGE enquanto não existe.
  * `coleta/<fonte>/`: um subpacote por fonte de dados, cada um com seu `README.md`. Ver [`coleta/inmet/`](src/coleta/inmet/) e [`coleta/monitor_secas/`](src/coleta/monitor_secas/).
* `outputs/`: Tabelas (`tabelas/`) e figuras (`figuras/`) geradas por script.
* `tickets/`: Backlog do projeto, um arquivo por tarefa. Comece pelo [board](tickets/README.md).
* `models/`: Modelos treinados salvos (ex: `.pkl`, `.joblib`).
* `reports/`: Relatórios finais, apresentações e análises.
* `figures/`: Gráficos exportados e imagens para uso no relatório ou README.
* `docs/`: Documentação adicional sobre as bases de dados e a metodologia.

### Como rodar um coletor

Sempre a partir da **raiz do repositório**, para os imports de `src.` funcionarem:

```bash
python -m src.coleta.inmet.download          # e não python src/coleta/inmet/download.py
```

Cada coletor tem um `validar.py` que confere os critérios de aceite do ticket
correspondente e sai com código 0 ou 1.

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
