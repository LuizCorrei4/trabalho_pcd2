# Plano Definitivo: Coleta de Dados de Inflação Alimentar via SIDRA/IBGE

Este plano substitui a coleta falha em PDFs do DIEESE por um processo científico e escalável usando a API oficial do IBGE, alinhado à proposta do projeto de analisar a volatilidade regional de alimentos.

## 1. O Que Será Coletado (Escopo)

A coleta será feita integralmente na **Tabela 7060 do SIDRA** (IPCA Geral, grupos, subgrupos, itens e subitens).

### 1.1 Cobertura Geográfica
- **Extração Total:** Todas as 16 Regiões Metropolitanas e Municípios Monitorados (Código Territorial 6 e 39).
- **Justificativa:** Ter todas as regiões permite criar mapas de calor interativos e testar hipóteses espaciais (ex: "Seca no Sul encarece a comida no Norte?").

### 1.2 Variáveis, Métricas e Período
Para cada localidade e cada mês (**de Janeiro de 2006 até o mês mais recente de 2026**), coletaremos:
1. **Variação Mensal (%):** Código `63`. Mede o "choque" de preço do mês.
2. **Peso Mensal (%):** Código `66`. Mede o impacto no bolso. (Exemplo: o tomate pode subir 50% em um mês, mas o peso dele no orçamento é de apenas 0,3%. Já uma alta de 5% no arroz causa um estrago muito maior).

*Nota sobre o período:* A coleta bruta será feita retroativamente até 2006 (totalizando 20 anos de histórico). Esse período abrange inúmeros ciclos de El Niño/La Niña, além de grandes eventos econômicos globais (crise de 2008, pandemia de 2020) e locais (crise hídrica de 2014/15). É sempre mais prudente coletar o máximo de histórico na fase de Engenharia de Dados; se necessário, a equipe pode limitar a série temporal durante a modelagem para evitar quebras metodológicas antigas.

### 1.3 Nível de Detalhamento dos Alimentos
Nós coletaremos duas camadas de dados para análise cruzada:
- **Camada Macro:** O grupo `7169` ("1. Alimentação e Bebidas"). Representa o custo genérico de se alimentar na região.
- **Camada Micro (Itens Sensíveis):** Selecionaremos e extrairemos códigos de subitens extremamente sensíveis a choques logísticos ou climáticos. Exemplos de códigos de subitens:
  - Arroz (sensível à água no Sul)
  - Feijão Carioca e Feijão Preto (impactos de seca em safrinhas)
  - Carnes Bovinas (sensível ao custo do milho e exportação)
  - Tomate, Batata e Hortaliças (produtos de ciclo curto, altamente reativos à chuva/geada)
  - Óleo de Soja (impactado pelo mercado externo e clima no Centro-Oeste)

## 2. Metodologia de Implementação (Código)

### 2.1 A Ferramenta
Criaremos um script em Python (`src/coleta/sidra_ipca/01_ibge_ipca_download.py`) utilizando a biblioteca `sidrapy`. 

### 2.2 Pipeline Sugerido
1. **Definição de Dicionário:** Criar um dicionário mapeando o nome humano para o código IBGE (ex: `{'Alimentacao_Bebidas': '7169', 'Arroz': '7171', ...}`).
2. **Loop de Requisições:** Fazer um laço iterando sobre a lista de códigos de produtos para puxar a Variação (63) e o Peso (66) para todo o período.
3. **Limpeza:** A API do SIDRA retorna a primeira linha como um cabeçalho descritivo. O script deve remover essa linha, converter as colunas de "Valor" numérico (de string para float) e alinhar os meses em formato `YYYY-MM`.
4. **Agregação:** Unir todas as respostas em um único e gigante *DataFrame* em formato *long* (`Local | Data | Item | Variacao | Peso`).
5. **Armazenamento:** Salvar o arquivo final em `data/raw/sidra_ipca/ipca_alimentos_rm.parquet`. Usaremos `.parquet` em vez de `.csv` por ser muito mais rápido e leve, respeitando o limite do GitHub.

## 3. Entregáveis Deste Plano

Este plano irá substituir os antigos tickets T-010 e T-011 pela seguinte estrutura:

- **T-010-ibge-sidra-download:** Script de coleta via `sidrapy` parametrizado.
- **T-011-ibge-sidra-limpeza:** Script de conversão de tipos (ex: datas, floats), verificação de valores nulos (meses sem medição) e salvamento em formato `.parquet`.

## 4. Próximos Passos
O próximo passo, após aprovação da equipe para abandonar a versão anterior, é refatorar os arquivos `tickets/01-coleta/T-010...` e `T-011...` baseando-se neste novo escopo estruturado.
