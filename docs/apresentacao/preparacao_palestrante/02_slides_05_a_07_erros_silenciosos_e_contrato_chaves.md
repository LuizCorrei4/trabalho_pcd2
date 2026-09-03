# 📘 Módulo 2: Erros Silenciosos e o Contrato de Chaves (Slides 5 a 7)

Este documento aprofunda os aspectos mais técnicos de engenharia de dados do projeto: a detecção e correção de erros silenciosos e o desenvolvimento do contrato de integridade de chaves.

---

## 📌 Slide 5 — Erros que não levantam exceção nenhuma

### 1. Resumo Executivo e Mensagem Central
- O principal risco em projetos de Ciência de Dados não são as exceções de execução (como `KeyError` ou `IndexError`), mas sim **erros semânticos silenciosos**: o código executa com código de saída 0, gera DataFrames completos, mas os números gerados são falsos.
- Foram descobertos quatro erros silenciosos graves nas fontes originais:
  1. **O Bloqueador do IPCA:** O sinal de menos de todas as deflações foi apagado por uma limpeza ingênua de strings.
  2. **INMET:** Mudança estrutural de layout em 2019 e sentinelas numéricos `-9999` que virariam temperaturas de milhares de graus negativos.
  3. **ANA (Monitor de Secas):** Revisões empilhadas no mesmo payload da API com valores de placeholder (`123456`) e erros de escala de 100×.
  4. **ANP:** Linhas duplicadas de coletas onde a média aritmética simples distorcia o preço do combustível em até 45,4%.

---

### 2. Anatomia Detalhada dos 4 Erros e Correções no Código

#### A. O Bloqueador do IPCA: Inversão do Sinal e Aniquilação de Deflações
- **Causa Raiz:** No código original de coleta do SIDRA ([`src/coleta/sidra_ipca/01_ibge_ipca_download.py`](../../src/coleta/sidra_ipca/01_ibge_ipca_download.py)), o IBGE publica marcadores textuais quando um dado não está disponível (`-` para não publicado, `...` para não aplicável).
  O desenvolvedor usou:
  ```python
  # CÓDIGO ANTERIOR CORROMPIDO:
  df_clean['valor'] = pd.to_numeric(
      df_clean['valor'].astype(str).str.replace('...', '', regex=False)
                                   .str.replace('-', '', regex=False),
      errors='coerce'
  )
  ```
- **Consequência Devastadora:** A instrução `.str.replace('-', '')` removeu o hífen solto, mas **removeu também o sinal negativo de qualquer número real**. Um registro de deflação de `-0.50%` virou `0.50%`, e um choque de `-56.62%` no tomate virou `+56.62%`!
- **Métricas do Impacto:**
  | Métrica | Base com o Bug | Base Corrigida |
  |---|:---:|:---:|
  | Total de linhas | 83.383 | 83.383 |
  | Contagem de valores negativos | **0** | **32.696** |
  | Valor mínimo observado | 0,00 % | **−56,62 %** |
  | Média da variação mensal | **3,14 %/mês** (~45% a.a. composto) | **0,75 %/mês** |
  | Média do grupo Alimentação | 2,87 %/mês | **0,59 %/mês** (ordem de grandeza real) |
- **A Correção Definitiva ([`01_ibge_ipca_download.py:162-167`](../../src/coleta/sidra_ipca/01_ibge_ipca_download.py#L162-L167)):**
  ```python
  MARCADORES = ['-', '...', '..', 'X', '']
  valor_texto = df_clean['valor'].astype(str).str.strip()
  df_clean['valor'] = pd.to_numeric(
      valor_texto.where(~valor_texto.isin(MARCADORES)),
      errors='coerce'
  )
  ```
  O uso de `.where(~valor_texto.isin(MARCADORES))` garante que apenas a string `"-"` idêntica e isolada seja mascarada como `NaN`, preservando intacto qualquer número negativo.
- **Teste de Regressão Permanente ([`24_junta.py:410-412`](../../src/tratamento/24_junta.py#L410-L412)):**
  ```python
  n_neg = int((fato["ipca_var_alimentacao"] < 0).sum())
  assert n_neg > 0, "nenhuma deflação no alvo — o bug do sinal do IPCA voltou"
  ```

---

#### B. INMET: Quebra de Layout em 2019 e Sentinelas `-9999`
- **Quebra de Formato:** Entre 2014-2018 e 2019-2026, o INMET alterou os arquivos sem aviso:
  - O caminho dos CSVs dentro do ZIP mudou (`2014/INMET_...` para a raiz `INMET_...`).
  - Cabeçalhos mudaram acentuação (`REGIÃO:` vs `REGIAO:`).
  - Formato de data mudou de `2014-01-01` para `2019/01/01`.
  - Ausência de dado era preenchida como `-9999` até 2018 e como campo vazio pós-2019.
- **Tratamento no Código ([`src/coleta/inmet/agrega_dia.py:61-115`](../../src/coleta/inmet/agrega_dia.py#L61-L115)):**
  ```python
  VALORES_AUSENTES = ["-9999", "-9999.0", "-9999,0", "-9999.00", "-9999,00"]
  # Mapeamento dinâmico de colunas por expressões regulares normalizadas em colunas.py
  df = pd.read_csv(..., na_values=VALORES_AUSENTES, decimal=",")
  ```
  Caso o `-9999` não fosse convertido em `NaN` na leitura, uma média mensal de temperatura transformaria dias com sensor inoperante em médias de −3.000 °C, destruindo toda a modelagem climática.

---

#### C. Monitor de Secas (ANA): Revisões Empilhadas e Placeholders
- **O Problema:** Ao consultar a API RPC da ANA, a lista `areas` de cada estado devolve **todas as revisões históricas de um mesmo mês empilhadas**, sem discriminar a versão válida. Dos 2.422 meses cadastrados, 66 vinham duplicados entre 2 e 4 vezes.
- **Valores Corrompidos nas Versões Antigas:**
  - Em 2015-04 na Bahia, uma versão preliminar trouxe os pontos-base com dois zeros a mais: `984700` no lugar de `9847` (indicando 9.847% de área estadual).
  - Em 2016-06, a categoria S4 continha um placeholder de teste de digitação: `123456`.
- **Resolução Elegante ([`src/coleta/monitor_secas/agrega_uf_mes.py:65-79`](../../src/coleta/monitor_secas/agrega_uf_mes.py#L65-L79)):**
  A equipe inspecionou a geração de dados da ANA e constatou que cada mapa emitido pelo comitê técnico recebe um `id` autoincremental sequencial. A versão vigente é garantida **pelo maior `id_registro`**. O coletor filtra estritamente `df.sort_values("id_registro").groupby(["sigla_uf", "ano", "mes", "categoria"]).last()`, expurgando placeholders e gravando as discrepâncias em tabela de auditoria.

---

#### D. ANP: Ponderação Amostral vs Média Simples
- **O Problema:** A base de preços de combustíveis da ANP trouxe 182 grupos duplicados em `(sigla_uf, ano_mes, produto)` — notadamente em abril/2026 (duas levas de coleta) e postos isolados com apenas 1 registro no início dos anos 2000.
- **O Perigo da Média Simples:** Se fizermos `df.groupby(...).mean()`, um registro isolado de 1 posto com erro de digitação terá o mesmo peso de uma leva com 5.681 postos pesquisados.
- **Exemplo Real no Pará (Fevereiro/2008 - GLP 13 kg):**
  - Leva 1: 1 posto com R$ 17,98 (anomalia).
  - Leva 2: 674 postos com média de R$ 32,95.
  - **Média Simples:** $(17,98 + 32,95) / 2 = \text{R\$} 25,46$ (Erro medido: **−45,4%** contra a realidade).
  - **Média Ponderada Pelo Nº de Postos ([`src/tratamento/25_combustiveis.py:122-128`](../../src/tratamento/25_combustiveis.py#L122-L128)):**
    $$\text{Preço Ponderado} = \frac{\sum (\text{preco\_venda\_medio} \times \text{quantidade\_registros})}{\sum \text{quantidade\_registros}} = \text{R\$} 32,91$$
    O valor ponderado reflete com precisão o preço médio ponderado de mercado.

---

### 3. Perguntas Prováveis da Banca e Respostas Afiadas

> **Pergunta da Banca:** *"Como vocês garantem que não existem outros erros silenciosos como o do sinal do IPCA em outras partes da base?"*  
> **Resposta do Palestrante:**  
> "Estabelecemos uma política de validação em camadas. Além das asserções estruturais de integridade em código, rodamos validações semânticas de domínio físico em todas as variáveis numéricas:
> 1. Temperatura limitada estritamente ao intervalo físico [−10 °C, 50 °C].
> 2. Preço de combustível líquido validado no intervalo [1,00, 15,00] R$/litro e GLP em [20, 200] R$/botijão ([`25_combustiveis.py:367-368`](../../src/tratamento/25_combustiveis.py#L367-L368)).
> 3. Monotonia cumulativa estrita das categorias do Monitor de Secas ($S_0 \ge S_1 \ge S_2 \ge S_3 \ge S_4$).
> 4. Confronto com eventos históricos conhecidos (validação factual out-of-band)."

---

## 📌 Slide 6 — As três armadilhas da junção

### 1. Resumo Executivo e Mensagem Central
- Ao realizar o cruzamento relacional entre bases heterogêneas, existem três mecanismos padrão do Pandas e de motores SQL que operam sem emitir alertas e que corrompem a integridade dos dados:
  1. **Armadilha 1 (Incompatibilidade de Tipo Temporal):** Merge que não dá erro mas devolve 100% de nulos.
  2. **Armadilha 2 (Explosão Cartesiana / Fan-Out):** Merge direto sobre grão não-pivoteado que multiplica o tamanho da tabela por 11.
  3. **Armadilha 3 (Variação Temporal em Índices com Gaps):** Uso ingênuo de `shift(1)` em séries com meses faltantes que rotula um salto de 4 meses como variação mensal.

---

### 2. Mecanismo Técnico de Cada Armadilha

#### Armadilha 1: O Merge Vazio sem Warning
- **Ocorre quando:** Uma tabela armazena a coluna de mês como `str "YYYY-MM"` (ex: `"2015-01"`) e a outra como `str "YYYY-MM-DD"` (ex: `"2015-01-01"`) ou como `pd.Timestamp`.
- **Comportamento do Pandas:** O Pandas aceita a operação `df1.merge(df2, on="ano_mes", how="left")`. Como os tipos de dados ou strings diferem em nível de caractere, **nenhuma chave casa**. O DataFrame resultante mantém as 3.726 linhas, mas **todas as novas colunas viram 100% NaN**. Nenhum `KeyError` é disparado.

#### Armadilha 2: A Multiplicação por 11 (Fan-Out)
- **Ocorre quando:** A base da direita possui uma chave secundária oculta que não faz parte da cláusula `on`. No caso da safra ([`safra_uf_mes.parquet`](../../data/interim/safra_uf_mes.parquet)), o grão nativo é `(sigla_uf, ano_mes, produto)`. Há 11 produtos agrícolas para cada mês e estado.
- **O Desastre do Merge Direto:** Fazer `fato.merge(safra, on=["sigla_uf", "ano_mes"], how="left")` duplica cada linha da esquerda por 11! A base salta de **3.726 para 40.986 linhas**.
- **A Pegadinha:** A taxa de match reportada seria de ~79,6%, o que levaria um desenvolvedor desatento a achar que o merge foi bem-sucedido.

#### Armadilha 3: O Falso Shift Temporal
- **O Cenário:** A ANP possui lacunas de pesquisa de combustível em 33 meses da janela de 138 meses. Em São Paulo, suponha que haja dados em março/2018 (R$ 4,03) e em julho/2018 (R$ 4,30), sem registros em abril, maio e junho.
- **O Cálculo Ingênuo:**
  ```python
  df["var_mensal"] = (df["preco"] / df["preco"].shift(1) - 1) * 100
  ```
- **A Falsidade:** O `shift(1)` pega a linha imediatamente anterior na memória do DataFrame. Ele calcula $(4,30 / 4,03 - 1) = +6,86\%$ e grava como se fosse a variação de um único mês! Uma variação acumulada de 4 meses é introduzida como choque mensal, gerando outliers artificiais nas regressões.

---

## 📌 Slide 7 — O contrato de chaves que fecha as três portas

### 1. Resumo Executivo e Mensagem Central
- Para neutralizar de forma definitiva as três armadilhas de junção, foi desenvolvido o módulo central [`src/tratamento/chaves.py`](../../src/tratamento/chaves.py).
- Toda fonte de dados é obrigada a passar por esse módulo antes de qualquer merge. Ele implementa três funções guardiãs:
  1. `padroniza_chaves(df)`: Converte qualquer representação temporal para **`pd.Period[M]`** e padroniza `sigla_uf` em 2 maiúsculas.
  2. `valida_chaves(df, nome, unica=True)`: Confere restrições de unicidade e tipagem estrita com asserções invioláveis.
  3. `checa_join(antes, depois, nome, chave)`: Monitora a invariância de linhas e taxa de match, abortando a execução se houver fan-out ou match zero.

### 2. Implementação no Código

#### Por que `pd.Period[M]` é a Escolha Superior? ([`chaves.py:117-142`](../../src/tratamento/chaves.py#L117-L142))
```python
if "ano_mes" in out.columns:
    col = out["ano_mes"]
    if isinstance(col.dtype, pd.PeriodDtype):
        out["ano_mes"] = col.dt.asfreq("M")
    elif pd.api.types.is_datetime64_any_dtype(col):
        out["ano_mes"] = col.dt.to_period("M")
    else:
        out["ano_mes"] = pd.PeriodIndex(col.astype(str).str.strip(), freq="M")
```
> **Por que não `pd.Timestamp`?**  
> O `pd.Timestamp` (ou `datetime64[ns]`) exige um dia específico (ex: `2015-01-01 00:00:00`). Se uma base tiver dia 01 e a outra dia 31, o merge falha. O `pd.Period[M]` representa o intervalo contínuo do mês inteiro (`Period('2015-01', 'M')`), **eliminando ontologicamente a existência do componente 'dia'**.

#### Como Neutralizamos a Armadilha 2 (Fan-Out)? ([`chaves.py:174-213`](../../src/tratamento/chaves.py#L174-L213))
1. O Pandas é chamado com o parâmetro de validação estrito: `fato.merge(..., validate="m:1")`. Se o lado direito tiver chaves duplicadas, o Pandas levanta exceção de schema imediatamente.
2. A função `checa_join()` audita o tamanho:
   ```python
   if len(depois) > len(antes):
       raise ValueError(f"[{nome}] o merge inflou {len(antes):,} -> {len(depois):,} linhas! Pivote antes de juntar.")
   ```

#### Como Neutralizamos a Armadilha 3 (Falso Shift)? ([`25_combustiveis.py:134-145`](../../src/tratamento/25_combustiveis.py#L134-L145))
Antes de executar qualquer `.shift(1)` ou `.shift(12)`, o código projeta os dados sobre uma **grade cartesiana completa de todos os meses do calendário** (`monta_grade`):
```python
# Se houver buraco na coleta, o mês intermediário entra como linha com preço NaN:
largo = monta_grade(meses).merge(largo, on=["sigla_uf", "ano_mes"], how="left")

# O shift agora opera sobre a grade contígua regular:
# O mês seguinte a um buraco compara com NaN, resultando legitimamente em NaN!
largo["comb_var_mm"] = (largo["preco"] / largo["preco"].shift(1) - 1) * 100
```
Com isso, nenhuma variação mensal é inventada sobre períodos descontinuados.

### 3. Perguntas Prováveis da Banca e Respostas Afiadas

> **Pergunta da Banca:** *"A validação `validate='m:1'` não é nativa do Pandas? Por que vocês precisaram criar a função `checa_join` em cima disso?"*  
> **Resposta do Palestrante:**  
> "A cláusula `validate='m:1'` do Pandas impede a multiplicação de linhas, mas é completamente cega para a **perda silenciosa de match** (a Armadilha 1). Se os tipos de dados divergirem e o match for 0%, `validate='m:1'` aceita normalmente e devolve uma coluna inteira de `NaN`. O `checa_join` valida a taxa de match (`match_pct > 0%`), loga a contagem de linhas para auditoria visual e assegura a preservação da espinha dorsal do pipeline."
