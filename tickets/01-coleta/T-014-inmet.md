# T-014 — Coletor INMET: dados meteorológicos históricos

| Campo | Valor |
|---|---|
| **Etapa** | 1 Coleta |
| **Prioridade** | P0 |
| **Estimativa** | 6h |
| **Depende de** | T-002 |
| **Bloqueia** | T-021 |
| **Responsável** | — |
| **Status** | 🔲 A fazer |

## Contexto
Fonte primária de clima. O volume é grande (dado horário de centenas de estações) e a qualidade é irregular — estações abrem, fecham e falham. Este ticket só **baixa e consolida em dado diário por estação**; a agregação para UF×mês é o T-021.

## Entregável
`data/raw/inmet/{ANO}.zip` — arquivos brutos
`data/interim/clima_estacao_dia.parquet` — estação × dia
`data/interim/catalogo_estacoes.csv` — estação → UF, lat, lon, altitude

## Fonte
- ZIPs anuais ✅ verificado: `https://portal.inmet.gov.br/uploads/dadoshistoricos/{ANO}.zip` (2000→2026)
- Catálogo de estações automáticas: https://portal.inmet.gov.br/paginas/catalogoaut

## Tarefas
- [ ] `src/coleta/05_inmet_download.py`: baixar os ZIPs de 2014 a 2026 (1 ano a mais que o alvo, para lags)
- [ ] Montar `catalogo_estacoes.csv` com `codigo_estacao`, `nome`, `sigla_uf`, `lat`, `lon`, `altitude`. O cabeçalho de cada CSV dentro do ZIP também traz esses metadados — extrair de lá é mais confiável que raspar a página
- [ ] `src/coleta/06_inmet_agrega_dia.py`: ler os CSVs de dentro do ZIP **sem extrair tudo pro disco** (`zipfile.ZipFile` + `pd.read_csv` no buffer)
- [ ] Agregar hora → dia por estação:
  - `chuva_mm` = **soma** das horas
  - `temp_min` / `temp_media` / `temp_max` = min / média / max
  - `umidade_media`, `radiacao_total`
  - `horas_validas` = contagem de registros não nulos no dia (indicador de qualidade)
- [ ] Marcar como nulo o dia com `horas_validas < 18`
- [ ] Salvar em Parquet particionado por ano

## Critérios de aceite
- [ ] ≥ 400 estações no catálogo, todas com `sigla_uf` preenchida e batendo com `dim_uf`
- [ ] Todas as 27 UFs têm ao menos 1 estação
- [ ] Chuva diária sempre ≥ 0 e < 500 mm; temperatura entre -10 °C e 50 °C — fora disso é sentinela de erro, não clima
- [ ] Nenhum valor `-9999` sobrevivendo como número na tabela final
- [ ] Cobertura temporal: ≥ 90% dos dias do período têm ao menos 1 estação válida por UF

## Armadilhas
- **`-9999` é o código de ausência do INMET.** Se não for convertido para `NaN` antes de qualquer média, a temperatura média da estação vira um número absurdamente negativo e contamina tudo silenciosamente. Tratar isso na leitura, não depois.
- Encoding dos CSVs é **`latin-1`**, não UTF-8. E o separador é `;`, com vírgula decimal (`decimal=","`).
- As 8 primeiras linhas de cada CSV são cabeçalho de metadados, não dados. `skiprows=8`.
- Os nomes das colunas mudaram ao longo dos anos (`PRECIPITAÇÃO TOTAL, HORÁRIO (mm)` vs variações). Normalizar os nomes com um mapeamento explícito por padrão de texto, não por posição.
- Volume: os ZIPs somados passam de 1 GB. Não versionar no git (já coberto pelo `.gitignore` do T-001).
- **Alternativa se este ticket virar um pântano:** [NASA POWER](https://power.larc.nasa.gov/) entrega série **mensal** direto por lat/lon, em grade, sem falhas de estação e sem cadastro. Basta pedir o ponto de cada capital ou de cada centroide de UF. Perde-se granularidade diária (adeus `dias_sem_chuva`), mas resolve o clima básico em 1h em vez de 6h. Vale usar de qualquer forma como fonte de imputação para os buracos do INMET.
