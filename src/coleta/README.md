# 📡 Pacote de Coleta e Ingestão de Dados (`src/coleta`)

Este pacote contém os módulos responsáveis por se conectar a APIs governamentais, extrair arquivos brutos e estruturar os dados na camada intermediária (`data/interim/`) e bruta (`data/raw/`).

---

## 1. Fontes de Dados Integradas

| Fonte | Chave CLI | Órgão / Provedor | Grão Nativo | Arquivo de Saída Principal |
|---|:---:|---|---|---|
| **IPCA Alimentos** | `ipca` | IBGE / SIDRA (Tabs. 2938, 1419, 7060) | RM/Capital × Mês × Item | `data/raw/sidra_ipca/ipca_alimentos_rm.parquet` |
| **Clima BDMEP** | `inmet` | INMET / BDMEP | Estação × Hora/Dia | `data/interim/clima_estacao_mes.parquet` |
| **Monitor de Secas** | `seca` | ANA / Monitor de Secas | UF × Mês | `data/interim/seca_uf_mes.parquet` |
| **Estimativas de Safra** | `safra` | IBGE / SIDRA (LSPA 6588 + PAM) | UF × Mês × Produto | `data/interim/safra_uf_mes.parquet` |
| **Macroeconômico** | `bcb` | Banco Central do Brasil / SGS | Brasil × Dia/Mês | `data/interim/macro_br_mes.parquet` |
| **Combustíveis** | `combustiveis` | ANP / Levantamento de Preços | Posto/UF × Mês × Produto | `data/interim/combustiveis_uf_mes.parquet` |

---

## 2. Como Executar os Coletores

Todos os coletores são gerenciados de forma centralizada pelo **Orquestrador Unificado**:

```bash
# Executa todas as fontes (modo seguro: não rebaixa o que já existe)
python -m src.coleta.runner --all

# Executa apenas uma fonte específica
python -m src.coleta.runner --fonte <nome>   # Ex: ipca, inmet, seca, safra, bcb, combustiveis

# Força nova coleta descartando checkpoints locais
python -m src.coleta.runner --fonte ipca --force

# Executa com cópia de backup e rollback de segurança
python -m src.coleta.runner --fonte bcb --backup
```

---

## 3. Padrão Arquitetural de um Coletor

Cada subdiretório de fonte (`sidra_ipca/`, `inmet/`, `monitor_secas/`, `safra/`, `bcb/`, `combustiveis/`) expõe uma função padronizada em seu `__init__.py`:

```python
def executar_coleta(
    overwrite: str = "skip",
    ano_inicio: int | None = None,
    ano_fim: int | None = None,
    logger: logging.Logger | None = None,
    download_logger: DownloadLogger | None = None,
    interativo: bool = False,
) -> ColetaResult:
    ...
```

Para mais detalhes sobre a arquitetura de logging, checkpoints e criação de novos coletores, consulte o [Guia do Desenvolvedor](../../docs/guia_do_desenvolvedor.md).
