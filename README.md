# Trabalho de Prática em Ciência de Dados II (SSC0957)

Este repositório contém a organização inicial e os códigos a serem desenvolvidos para o trabalho da disciplina, focando no cruzamento de dados heterogêneos para estudos sobre **crises climáticas e alimentares no cenário brasileiro**.

## Estrutura do Repositório

Como o projeto será desenvolvido por 5 pessoas ao longo de 4 meses, adotamos uma organização de pastas escalável e profissional:

* `data/`: Diretório para os conjuntos de dados (Ignorado pelo Git, exceto estrutura).
  * `raw/`: Dados brutos, como baixados da fonte. **NUNCA modifique estes arquivos**.
  * `processed/`: Dados limpos e preparados que serão usados nos modelos.
* `notebooks/`: Jupyter Notebooks (.ipynb) utilizados para exploração de dados, prototipagem e experimentação. Sugere-se nomear de forma sequencial, ex: `01_nome_analise_descritiva.ipynb`.
* `src/` (ou `scripts/`): Scripts Python modulares e reutilizáveis (código para download de dados, limpeza, treinamento de modelos).
* `models/`: Modelos treinados salvos (ex: `.pkl`, `.joblib`).
* `reports/`: Relatórios finais, apresentações e análises.
* `figures/`: Gráficos exportados e imagens para uso no relatório ou README.
* `docs/`: Documentação adicional sobre as bases de dados e a metodologia.

## Configuração Inicial do Ambiente

Para garantir que todos do grupo usem as mesmas versões de bibliotecas, recomendamos o uso de um ambiente virtual.

1. **Crie o ambiente virtual (já configurado localmente como `.venv`):**
   ```bash
   python3 -m venv .venv
   ```

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
