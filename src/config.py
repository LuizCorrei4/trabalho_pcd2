"""Constantes compartilhadas do projeto (T-001).

Todo caminho de arquivo do projeto sai daqui — nenhum script monta caminho
absoluto na mão. Os caminhos são derivados da posição deste arquivo, então o
projeto funciona em qualquer máquina e com acento/espaço no caminho, porque
tudo é `pathlib.Path` (armadilha do T-001).
"""

from pathlib import Path

# ---------------------------------------------------------------- caminhos ---
RAIZ = Path(__file__).resolve().parent.parent

DATA = RAIZ / "data"
DATA_RAW = DATA / "raw"
DATA_INTERIM = DATA / "interim"
DATA_PROCESSED = DATA / "processed"

RAW_INMET = DATA_RAW / "inmet"
RAW_ANA = DATA_RAW / "ana"
RAW_IBGE = DATA_RAW / "ibge"

OUTPUTS = RAIZ / "outputs"
OUT_FIGURAS = OUTPUTS / "figuras"
OUT_TABELAS = OUTPUTS / "tabelas"

DOCS = RAIZ / "docs"

# Tabela-dimensão canônica das UFs, entregue pelo T-002. Ainda pode não existir:
# quem depende dela deve usar `src.ufs.carregar_ufs()`, que cai para a API do
# IBGE enquanto o T-002 não estiver pronto.
DIM_UF = DATA_PROCESSED / "dim_uf.csv"


def garantir_pastas() -> None:
    """Cria as pastas de dados que os coletores usam.

    `data/raw/` e `data/interim/` não são versionados (ver `.gitignore`), então
    num clone novo essas subpastas não existem.
    """
    for p in (
        DATA_RAW,
        DATA_INTERIM,
        DATA_PROCESSED,
        RAW_INMET,
        RAW_ANA,
        RAW_IBGE,
        OUT_FIGURAS,
        OUT_TABELAS,
    ):
        p.mkdir(parents=True, exist_ok=True)


# ----------------------------------------------------------------- período ---
# Janela-alvo da análise: 138 meses (é a contagem que o T-021 usa).
PERIODO_INICIO = "2015-01"
PERIODO_FIM = "2026-06"

# O clima é baixado com 1 ano de folga antes do início, para alimentar as
# features de lag do T-023 sem perder os primeiros meses da janela-alvo.
ANO_INICIO_CLIMA = 2014
ANO_FIM_CLIMA = 2026

# ------------------------------------------------------------------- rede ---
# O portal do INMET derruba a conexão ("Connection reset by peer") para clientes
# sem User-Agent de navegador. Sem isto o download do T-014 não funciona.
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
HTTP_TIMEOUT = 120  # segundos
HTTP_TENTATIVAS = 4  # tentativas por arquivo, com espera exponencial
