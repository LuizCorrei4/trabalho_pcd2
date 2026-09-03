# 🎓 Guia Central de Preparação do Palestrante — SSC0957 (2026)
## Defesa Técnica e Respostas Profundas sobre a Implementação

**Disciplina:** SSC0957 — Prática em Ciência de Dados II (ICMC-USP)  
**Professor Avaliador:** Alexandre Delbem  
**Documento-Base da Apresentação:** [`docs/apresentacao/roteiro_simplificado.md`](../roteiro_simplificado.md)  
**Roteiro Completo de Referência:** [`docs/apresentacao/roteiro_detalhado.md`](../roteiro_detalhado.md)  
**Tabela Final Entregue:** [`data/processed/fato_alimentos_combustiveis_uf_mes.parquet`](../../../data/processed/fato_alimentos_combustiveis_uf_mes.parquet) (2.088 linhas × 108 colunas)

---

## 🎯 Objetivo Deste Material

Este repositório documental foi desenvolvido para municiar o palestrante com **domínio absoluto de cada linha de código, decisão matemática, tratamento de exceção silenciosa e escolha de modelagem** presentes no pipeline de dados.

A banca avaliadora (especialmente sob os critérios do Prof. Alexandre Delbem em [`docs/apresentacao/criterios_disciplina_delbem.md`](../criterios_disciplina_delbem.md)) não avalia apenas se a tabela foi gerada, mas prioritariamente:
1. **Consciência das resoluções espaço-temporais** e da representatividade dos dados por critério.
2. **Capacidade de identificar e mitigar erros grosseiros** que não quebram a execução.
3. **Justificativa teórica e empírica** para junções, imputações (ou não-imputações) e agregações.
4. **Descoberta de relações não-óbvias** e formulação de hipóteses refutáveis.

---

## 🗺️ Mapa de Navegação dos Módulos Técnicos

Cada slide de [`docs/apresentacao/roteiro_simplificado.md`](../roteiro_simplificado.md) possui um documento de suporte aprofundado contendo:
- **Resumo Executivo e Mensagem Central**: O que deve ser comunicado em 30 segundos.
- **Mapeamento Direto no Código**: Arquivos, classes, funções e números de linha em `src/`.
- **Decisões Críticas de Engenharia e Estatística**: Trade-offs, abordagens ingênuas descartadas e provas matemáticas.
- **Perguntas Prováveis e "Pegadinhas" da Banca**: Respostas afiadas, com embasamento teórico e empírico.
- **Armadilhas de Linguagem (O que NUNCA dizer)**: Termos proibidos que enfraquecem a defesa.

| Módulo | Slides Cobertos | Temas Principais |
|---|:---:|---|
| 📄 [**Módulo 1: Fundamentos e Arquitetura**](01_slides_01_a_04_fundamentos_e_arquitetura.md) | **Slides 1 a 4** | Escopo analítico (16 UFs × 138 meses), formato largo retangular, 6 fontes heterogêneas de 5 órgãos, arquitetura Medalhão (`raw` imutável, `interim`, `processed`), idempotência e integridade em disco (`BackupManager`). |
| 📄 [**Módulo 2: Erros Silenciosos e Contrato de Chaves**](02_slides_05_a_07_erros_silenciosos_e_contrato_chaves.md) | **Slides 5 a 7** | O bug bloqueador do sinal do IPCA, sentinelas `-9999` do INMET, revisões empilhadas e placeholders da ANA, as 3 armadilhas de junção (tipo de data, fan-out ×11, falso shift temporal) e a blindagem em `src/tratamento/chaves.py`. |
| 📄 [**Módulo 3: Redução, Junção e Combustíveis**](03_slides_08_a_10_reducao_juncao_e_combustiveis.md) | **Slides 8 a 10** | Mediana climática com corte de qualidade de 70% de dias válidos, winsorização de safra em ±50%, topologia dos 5 LEFT JOINs sobre a espinha de calendário (`24_junta.py`), papel logístico do diesel e validação cruzada independente por testemunha (96k coletas). |
| 📄 [**Módulo 4: Tabela Fato, Nulos e Validação**](04_slides_11_a_13_tabela_fato_nulos_e_validacoes.md) | **Slides 11 a 13** | Anatomia das 108 colunas, taxonomia rigorosa dos dados faltantes (por que não imputar zero na seca ou no combustível), flags booleanas de observabilidade e validação dupla (estrutural e choques históricos reais). |
| 📄 [**Módulo 5: Achados, Limites e Próximos Passos**](05_slides_14_a_15_achados_limites_e_proximos_passos.md) | **Slides 14 e 15** | O pico de defasagem de 4 meses entre diesel e inflação alimentar, dispersão espacial do frete (Acre +20% vs Paraná -4,7%), limites epistemológicos de uso da tabela e roadmap econométrico/ML (TWFE, GBDT, SHAP). |
| 🎯 [**Módulo 6: Simulado de Alta Tensão da Banca**](06_simulado_perguntas_da_banca.md) | **Geral** | 15 perguntas difíceis e capciosas formuladas no estilo de questionamento de banca de pós-graduação/docência com respostas exatas e memorizáveis. |

---

## ⚡ Guia Rápido de Sobrevivência para o Palestrante

### 3 Regras de Ouro na Apresentação:
1. **Nunca use a palavra "apenas" ou "simplesmente":** Nenhum merge foi "simplesmente dar um merge no pandas". Três deles teriam corrompido o dataset em silêncio se fossem feitos pelo método padrão.
2. **Defenda a semântica do vazio com orgulho:** Ter `NaN` na tabela não é defeito, é honestidade científica. Vazio no Monitor de Secas em 2016 no Paraná significa que *ninguém estava medindo*. Preencher com zero seria inventar dados falsos.
3. **Diferencie o grão da observação do grão da causalidade:** O IPCA mede o preço ao consumidor em 16 áreas urbanas; o clima e a safra ocorrem no território produtor da UF. Mostre que a equipe tem plena consciência desse trade-off e desenhou o passo T-022 justamente para ponderar estações pelo PAM.

---

## 🛠️ Comandos Rápidos para Demonstrar ao Vivo se Questionado

Se a banca pedir para ver dados reais ou rodar validações no terminal durante a arguição:

```bash
# 1. Conferir o status e integridade das 15 bases locais (dry-run instantâneo, sem rede):
python -m src.coleta.runner --status

# 2. Executar toda a suíte de testes unitários automatizados (0.4s):
python -m unittest discover -s tests -v

# 3. Rodar o pipeline de tratamento completo (T-021 -> T-024 -> T-025):
python -m src.coleta.runner --tratamento

# 4. Inspecionar as primeiras linhas e formato das 108 colunas da tabela fato:
python -c "import pandas as pd; df=pd.read_parquet('data/processed/fato_alimentos_combustiveis_uf_mes.parquet'); print(df.info())"
```
