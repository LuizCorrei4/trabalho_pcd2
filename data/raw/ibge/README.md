# `data/raw/ibge/` — lista canônica das UFs (ponte até o T-002)

**Usado por:** [`src/ufs.py`](../../../src/ufs.py) ·
**Coletado em:** 2026-08-13

## Isto não é uma fonte de dados do projeto

Não há ticket de coleta do IBGE, e nada aqui entra na análise. É **a dependência
`T-002` sendo suprida provisoriamente**.

Os tickets [T-014](../../../tickets/01-coleta/T-014-inmet.md) e
[T-015](../../../tickets/01-coleta/T-015-monitor-secas.md) declaram
`Depende de T-002`, e o [T-002](../../../tickets/00-fundacao/T-002-dim-uf.md)
entrega `data/processed/dim_uf.csv` — construído a partir desta mesma API
(a primeira tarefa do T-002 é literalmente
`GET servicodados.ibge.gov.br/api/v1/localidades/estados`).

Como o T-002 ainda não estava pronto e os dois coletores não funcionam sem a lista
das UFs, `src/ufs.py` usa o `dim_uf.csv` **quando ele existe** e cai para esta API
enquanto não existe. **No dia em que o T-002 entregar, os coletores passam a
validar contra a tabela canônica automaticamente, sem mexer em código** — basta
rodar de novo. A primeira linha da execução diz qual das duas fontes está em uso.

### Por que cada coletor precisa disto

* **T-015 não funciona sem o geocódigo.** A API do Monitor de Secas é consultada
  por `area={cod_ibge_uf}` (23 = CE, 35 = SP). Sem o mapeamento código ↔ sigla não
  há como baixar a série nem rotular a UF.
* **T-014 precisa da lista canônica** para dois critérios de aceite: `sigla_uf` das
  estações "batendo com `dim_uf`", e "todas as 27 UFs têm ao menos 1 estação".

## O que está aqui

| Arquivo | Tamanho | Conteúdo |
|---|---|---|
| `localidades_estados.json` | 2,4 KB | as 27 UFs: `id` (geocódigo), `sigla`, `nome`, `regiao` |

Fonte:

```
https://servicodados.ibge.gov.br/api/v1/localidades/estados?orderBy=nome
```

O cache é regravado sozinho se o arquivo for apagado.

## O que deu certo

- API aberta, rápida, sem cadastro e sem exigir `User-Agent` especial.
- As 27 UFs vêm completas e com acentuação correta — mas só porque o
  [`src/rede.py`](../../../src/rede.py) **força UTF-8**: a API não declara o
  charset, e sem isso o `requests` adivinha ISO-8859-1 e estraga "São Paulo",
  "Ceará", "Rondônia".

## O que deu errado / exigiu cuidado

- **`rest/adm/uf` da própria API da ANA responde 404** para cliente anônimo, então
  a associação geocódigo ↔ sigla teve que vir do IBGE. Acabou melhor: é a fonte
  mais correta de qualquer forma, e é a que o T-002 vai usar.

### Uma coleta que foi feita e depois desfeita

Esta pasta chegou a ter um segundo arquivo, `sidra_1301_area_uf.json`, com a área
territorial de cada UF (tabela SIDRA 1301, variável 615). Foi baixado sob a
hipótese de que o T-015 precisaria converter km² de seca em percentual da área da
UF.

**A hipótese estava errada:** a API do Monitor de Secas já entrega percentual da
área, não km². A área ficou sem uso nenhum — uma chamada de rede em toda execução
para alimentar uma coluna que nenhum código lia. Foi removida.

Se o [T-022](../../../tickets/02-tratamento/T-022-clima-ponderado.md) precisar de
área por UF, vale rebuscar na hora, sabendo para quê. Deixar dependência
especulativa "por se acaso servir" só cria peso morto e um ponto de falha extra.
