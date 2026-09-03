# 📚 Central de Documentação do Projeto — SSC0957 (2026)

**Projeto:** Crises Climáticas e Alimentares no Cenário Brasileiro  
**Disciplina:** SSC0957 — Prática em Ciência de Dados II (ICMC-USP)  
**Professor:** Alexandre Delbem  
**Tabela Final Entregue:** [`data/processed/fato_alimentos_combustiveis_uf_mes.parquet`](../data/processed/fato_alimentos_combustiveis_uf_mes.parquet) (2.088 linhas × 108 colunas)

---

## 🗺️ Mapa Semântico da Documentação

A pasta `docs/` está organizada em três grandes pilares temáticos para facilitar a consulta por desenvolvedores, pesquisadores e avaliadores:

```
docs/
├── README.md                                 <- Você está aqui (Portal Master da Documentação)
├── Proposta.md                               <- Proposta oficial aprovada da disciplina
├── guia_do_desenvolvedor.md                  <- Manual de Arquitetura, Contratos e Engenharia de Dados
│
├── analises/                                 <- Estudos Técnicos, Desenho de Junção e Auditorias de Cobertura
│   ├── analise_cobertura_safra_mt.md         <- Auditoria das 11 UFs sem IPCA e Soluções para Safra de MT
│   ├── analise_juncao_uf_mes.md              <- Desenho metodológico da junção (T-020, T-021, T-024)
│   ├── cobertura_inmet.md                    <- Auditoria da rede de estações meteorológicas (T-014)
│   └── cobertura_monitor_secas.md            <- Histórico de expansão territorial do Monitor de Secas (T-015)
│
└── apresentacao/                             <- Roteiros de Slides, Defesa Técnica e Critérios da Banca
    ├── roteiro_simplificado.md               <- Roteiro executivo de 15 slides (com notas e links técnicos)
    ├── roteiro_detalhado.md                  <- Roteiro analítico completo de 30 slides (com contagens finas)
    ├── criterios_disciplina_delbem.md        <- Requisitos e rubrica de avaliação do Prof. Alexandre Delbem
    └── preparacao_palestrante/               <- Módulos de aprofundamento e simulado da banca
        ├── README.md                         <- Guia central de defesa do palestrante
        ├── 01_slides_01_a_04_fundamentos_e_arquitetura.md <- Módulo 1 (Fundamentos e Escopo)
        ├── 02_slides_05_a_07_erros_silenciosos_e_contrato_chaves.md <- Módulo 2 (Erros Silenciosos e Chaves)
        ├── 03_slides_08_a_10_reducao_juncao_e_combustiveis.md <- Módulo 3 (Redução, Junção e Combustíveis)
        ├── 04_slides_11_a_13_tabela_fato_nulos_e_validacoes.md <- Módulo 4 (Tabela Fato, Nulos e Validações)
        ├── 05_slides_14_a_15_achados_limites_e_proximos_passos.md <- Módulo 5 (Achados e Roadmap)
        └── 06_simulado_perguntas_da_banca.md <- 15 perguntas difíceis da banca com respostas afiadas
```

---

## 📂 1. Governança e Arquitetura Geral

| Documento | Público-Alvo | Resumo do Conteúdo |
|---|---|---|
| 📋 [**`Proposta.md`**](Proposta.md) | Geral / Banca | Proposta original da disciplina (Proposta 1): objetivos analíticos, motivação socioeconômica, perguntas de pesquisa e cronograma das etapas. |
| 🛠️ [**`guia_do_desenvolvedor.md`**](guia_do_desenvolvedor.md) | Desenvolvedores / Revisores | Arquitetura técnica completa: ciclo de vida de dados (Medalhão), logging em 4 camadas, gestão de backups atômicos com rollback (`BackupManager`), contratos estáticos (`ColetaResult`) e como plugar novas fontes. |

---

## 🔬 2. Análises Técnicas e Desenho Metodológico ([`docs/analises/`](analises/))

Esta subpasta reúne as notas técnicas que embasaram cada decisão de engenharia de dados e tratamento estatístico das fontes:

| Documento | Questão Central Respondida |
|---|---|
| 🌾 [**`analise_cobertura_safra_mt.md`**](analises/analise_cobertura_safra_mt.md) | **Como fica a safra de Mato Grosso (29% da soja e 38% do milho do Brasil) se MT não tem IPCA?**<br>Rastreia o descarte no filtro final, demonstra o "ponto cego" de estados consumidores como SP/RJ e apresenta 3 soluções metodológicas (broadcast de safra nacional, ponderação PAM e matriz de transporte). |
| 🔗 [**`analise_juncao_uf_mes.md`**](analises/analise_juncao_uf_mes.md) | **Como harmonizar 4 bases em grãos diferentes para uma tabela retangular única?**<br>Documento base dos tickets T-020, T-021 e T-024: contratos de chaves, espinha de calendário e eliminação das armadilhas de join. |
| 🌦️ [**`cobertura_inmet.md`**](analises/cobertura_inmet.md) | **Qual a confiabilidade da rede meteorológica brasileira?**<br>Diagnóstico das 701 estações automáticas do INMET, quebras de layout em 2019, tratamento de sentinelas `-9999` e a crise de cobertura hídrica de 2021. |
| 🌵 [**`cobertura_monitor_secas.md`**](analises/cobertura_monitor_secas.md) | **A partir de quando cada estado passou a ser monitorado pela ANA?**<br>Linha do tempo da expansão do Monitor de Secas (2014 no Nordeste $\to$ 2020 no Centro-Sul $\to$ 2023 no Norte) e por que nulos dessa fonte não podem virar zero. |

---

## 🎤 3. Apresentação e Defesa Técnica ([`docs/apresentacao/`](apresentacao/))

Esta subpasta contém todo o material necessário para apresentar e defender o projeto perante a banca avaliadora:

| Documento | Formato / Propósito |
|---|---|
| 🗣️ [**`roteiro_simplificado.md`**](apresentacao/roteiro_simplificado.md) | **Roteiro dos 15 slides da apresentação:** contém bullets visíveis em tela, notas de fala do apresentador e links diretos para a defesa de implementação de cada slide. |
| 📖 [**`roteiro_detalhado.md`**](apresentacao/roteiro_detalhado.md) | **Roteiro expandido de 30 slides:** contém todas as tabelas completas de auditoria, contagens finas linha a linha e comandos de reprodução para consulta profunda. |
| 🎯 [**`criterios_disciplina_delbem.md`**](apresentacao/criterios_disciplina_delbem.md) | **Critérios oficiais de avaliação da disciplina:** lista os conceitos exigidos pelo Prof. Alexandre Delbem (resoluções espaço-temporais, erros grosseiros, casos especiais, relações não-óbvias). |
| 🛡️ [**`preparacao_palestrante/`**](apresentacao/preparacao_palestrante/README.md) | **Guia de Defesa Técnica do Palestrante:** 7 módulos cobrindo os 15 slides com referências em código (`src/`), teoria estatística, scripts de fala cronometrados e simulado com 15 perguntas difíceis da banca. |

---

## ⚡ Comandos Rápidos de Auditoria

Para validar as bases e a integridade da documentação diretamente no terminal:

```bash
# Auditar as 15 bases de dados em disco (instantâneo, sem rede):
python -m src.coleta.runner --status

# Rodar todos os testes unitários e de integração (0.5s):
python -m unittest discover -s tests -v

# Reexecutar o pipeline completo de tratamento (T-021 -> T-024 -> T-025):
python -m src.coleta.runner --tratamento
```
