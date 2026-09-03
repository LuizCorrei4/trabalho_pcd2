# 🧪 Pacote de Tratamento e Junção de Dados (`src/tratamento`)

Este pacote transforma as tabelas isoladas da camada `data/interim/` nas tabelas modeladas finais em `data/processed/`, aplicando padronização de chaves, agregações espaciais e junções relacionais controladas.

---

## 1. Módulos e Scripts do Pipeline

| Script / Módulo | Ticket | Objetivo Principal | Entrada Principal | Saída Gerada |
|---|:---:|---|---|---|
| **[`chaves.py`](chaves.py)** | T-020 | Padronização de tipos de chaves (`sigla_uf`, `ano_mes` Period[M]) e validação estrita de joins (`checa_join`). | Múltiplas | Utilitário compartilhado |
| **[`21_clima_uf_mes.py`](21_clima_uf_mes.py)** | T-021 | Agregação espacial das 701 estações meteorológicas para a grade UF × mês via **mediana**. | `data/interim/clima_estacao_mes.parquet` | `data/interim/clima_uf_mes.parquet` |
| **[`24_junta.py`](24_junta.py)** | T-024 | Criação do calendário e LEFT JOIN das 5 fontes primárias (IPCA, Clima UF, Safra, Seca, Macro). | Tabelas em `data/interim/` | `data/processed/fato_alimentos_uf_mes.parquet` |
| **[`25_combustiveis.py`](25_combustiveis.py)** | T-025 | Estruturação de combustíveis ANP com média ponderada por postos e junção ao fato. | `data/raw/combustiveis/combustivel.csv` | `data/processed/fato_alimentos_combustiveis_uf_mes.parquet` |
| **[`orquestrador.py`](orquestrador.py)** | — | Coordena a execução sequencial automatizada de todo o pipeline de tratamento. | Módulos acima | Tabelas fatos e dicionários |

---

## 2. Decisões Metodológicas Cruciais

1. **Clima por Mediana (e não Média):**  
   Sensores meteorológicos podem apresentar defeitos com leituras espúrias. A mediana é imune a outliers individuais de estações com sensor quebrado. Estações com menos de 70% de dias válidos no mês são descartadas antes da agregação.
2. **Combustíveis Ponderados por Postos:**  
   UFs e meses com maior número de postos pesquisados dominam a média ponderada, eliminando duplicatas de coletas parciais sem decisões arbitrárias.
3. **Espinha de Calendário Completa (27 UFs × 138 meses):**  
   Todo merge relacional é `LEFT JOIN` sobre a grade completa de meses e UFs. Isso garante que a ausência de dados seja identificada explicitamente como `NaN`, sem perdas silenciosas de linhas.

---

## 3. Como Executar o Pipeline de Tratamento

Você pode executar o tratamento de forma integrada via Runner:

```bash
# Executa a sequência completa de tratamento (clima -> fato -> combustíveis)
python -m src.coleta.runner --tratamento

# Ou executa tudo de ponta a ponta (coleta + tratamento)
python -m src.coleta.runner --completo
```

Para mais informações, consulte o [Guia do Desenvolvedor](../../docs/guia_do_desenvolvedor.md) e os [Dicionários de Variáveis](../../outputs/tabelas/).
