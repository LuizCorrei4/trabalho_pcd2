"""T-014, etapa 4 — verifica os critérios de aceite do ticket.

Uso (a partir da raiz do repositório):

    python -m src.coleta.inmet.validar

Sai com 0 se todos os critérios passam e 1 se algum falha. Cada critério imprime
o número que o sustenta — é esse número que vai para o relatório de qualidade do
T-025, e é ele que permite discutir se a cobertura é suficiente.
"""

from __future__ import annotations

import argparse

import pandas as pd

from ... import config, ufs as mod_ufs
from . import FAIXA_CHUVA_DIA_MM, FAIXA_TEMPERATURA_C, SENTINELA_AUSENTE
from .agrega_dia import SAIDA as SAIDA_DIARIA
from .catalogo import MINIMO_ESTACOES, SAIDA as SAIDA_CATALOGO

# O T-014 exige cobertura temporal de ao menos 90% dos dias do período com pelo
# menos uma estação válida por UF.
MINIMO_COBERTURA_PCT = 90.0

COLUNAS_TEMPERATURA = ("temp_media", "temp_max", "temp_min")


TABELA_COBERTURA = config.OUT_TABELAS / "inmet_cobertura_uf_ano.csv"
DOC_COBERTURA = config.DOCS / "cobertura_inmet.md"


def _exportar_cobertura(na_janela: pd.DataFrame, cobertura: pd.Series) -> None:
    """Grava a cobertura por UF × ano — insumo direto do T-021 e do T-025.

    A cobertura agregada do período esconde o padrão que importa: onde o buraco
    está concentrado no tempo. É isso que decide se dá para imputar ou se a UF
    precisa sair da análise.
    """
    validas = na_janela[na_janela["chuva_mm"].notna() | na_janela["temp_media"].notna()]

    dias = na_janela.groupby(["sigla_uf", "ano"])["data"].nunique().rename("dias_no_ano")
    validos = validas.groupby(["sigla_uf", "ano"])["data"].nunique().rename("dias_validos")
    estacoes = validas.groupby(["sigla_uf", "ano"])["codigo_estacao"].nunique().rename("estacoes_validas")

    tabela = pd.concat([dias, validos, estacoes], axis=1).reset_index()
    tabela["dias_validos"] = tabela["dias_validos"].fillna(0).astype(int)
    tabela["estacoes_validas"] = tabela["estacoes_validas"].fillna(0).astype(int)
    tabela["pct_cobertura"] = (100 * tabela["dias_validos"] / tabela["dias_no_ano"]).round(1)

    TABELA_COBERTURA.parent.mkdir(parents=True, exist_ok=True)
    tabela.to_csv(TABELA_COBERTURA, index=False, encoding="utf-8")

    por_ano = tabela.groupby("ano")["pct_cobertura"].mean().round(1)
    linhas = [
        "# Cobertura temporal do INMET por UF (T-014)",
        "",
        "Gerado por `python -m src.coleta.inmet.validar`. Não editar à mão.",
        "",
        f"Janela-alvo: **{config.PERIODO_INICIO} a {config.PERIODO_FIM}**. Um dia conta como",
        "coberto quando ao menos uma estação da UF registrou chuva **ou** temperatura",
        "válida naquele dia.",
        "",
        f"O critério de aceite do T-014 é **>= {MINIMO_COBERTURA_PCT:.0f}%** dos dias por UF.",
        "",
        "## Cobertura no período, por UF",
        "",
        "| UF | % dos dias cobertos | Atende o critério |",
        "|---|---|---|",
    ]
    for uf, valor in cobertura.sort_values().items():
        linhas.append(f"| {uf} | {valor:.1f}% | {'sim' if valor >= MINIMO_COBERTURA_PCT else '**NÃO**'} |")

    linhas += [
        "",
        "## Cobertura média entre UFs, por ano",
        "",
        "| Ano | Cobertura média |",
        "|---|---|",
    ]
    for ano, valor in por_ano.items():
        linhas.append(f"| {ano} | {valor:.1f}% |")

    linhas += [
        "",
        "A tabela completa por UF × ano está em",
        f"`{TABELA_COBERTURA.relative_to(config.RAIZ)}`.",
        "",
        "## Duas limitações reais da fonte",
        "",
        "**1. Roraima.** São 3 estações no catálogo e efetivamente 1 ativa na maior",
        "parte da série. Em 2021 e 2026 ela não produziu **nenhum** dia válido, e em",
        "2025 cobriu 24,7% do ano. Nenhum tratamento de dados resolve isso — a medição",
        "não existe. Amapá tem problema parecido, mais brando.",
        "",
        "**2. Há um buraco nacional em 2021-2022.** Não é limitação de UF pequena: o Rio",
        "Grande do Norte, com 9 estações e 100% de cobertura em todos os outros anos, cai",
        "para 38,1% em 2021 e 68,2% em 2022. O preenchimento da coluna de chuva no país",
        "inteiro cai de 85,1% em 2019 para 47,1% em 2021.",
        "",
        "Isso é especialmente inconveniente para este projeto: **2021 é justamente o ano",
        "da crise hídrica do Centro-Sul**, que o Monitor de Secas (T-015) aponta como o",
        "mais severo da série. A análise desse episódio vai depender de imputação, e a",
        "incerteza precisa constar no relatório.",
        "",
        "## Encaminhamento",
        "",
        "Este é um limite da fonte, não do coletor, e a decisão de como tratá-lo é do",
        "T-021 (agregação para UF × mês), que já tem a imputação por normal",
        "climatológica entre suas tarefas. O próprio T-014 registra o",
        "[NASA POWER](https://power.larc.nasa.gov/) como fonte de imputação recomendada:",
        "entrega série por lat/lon em grade, sem falha de estação, e resolveria tanto",
        "Roraima quanto o buraco de 2021-2022.",
        "",
    ]
    DOC_COBERTURA.parent.mkdir(parents=True, exist_ok=True)
    DOC_COBERTURA.write_text("\n".join(linhas), encoding="utf-8")
    print(f"         + {TABELA_COBERTURA.relative_to(config.RAIZ)}")
    print(f"         + {DOC_COBERTURA.relative_to(config.RAIZ)}")


class Relatorio:
    def __init__(self) -> None:
        self.falhas = 0

    def checar(self, nome: str, condicao: bool, detalhe: str = "") -> None:
        marca = "PASSA" if condicao else "FALHA"
        if not condicao:
            self.falhas += 1
        sufixo = f" — {detalhe}" if detalhe else ""
        print(f"  [{marca}] {nome}{sufixo}")


def validar(catalogo: pd.DataFrame, diario: pd.DataFrame) -> int:
    rel = Relatorio()
    tabela_ufs = mod_ufs.carregar_ufs()
    siglas_validas = set(tabela_ufs["sigla_uf"])

    print("\nCritério 1 — catálogo de estações")
    rel.checar(
        f"pelo menos {MINIMO_ESTACOES} estações no catálogo",
        len(catalogo) >= MINIMO_ESTACOES,
        f"{len(catalogo)} estações",
    )
    sem_uf = int(catalogo["sigla_uf"].isna().sum() + catalogo["sigla_uf"].eq("").sum())
    rel.checar("todas as estações têm sigla_uf", sem_uf == 0, f"{sem_uf} sem UF")
    fora = sorted(set(catalogo["sigla_uf"].dropna()) - siglas_validas - {""})
    rel.checar("sigla_uf do catálogo bate com dim_uf", not fora, f"siglas estranhas: {fora or 'nenhuma'}")

    print("\nCritério 2 — todas as 27 UFs têm ao menos 1 estação")
    por_uf = catalogo.groupby("sigla_uf").size()
    faltando = sorted(siglas_validas - set(por_uf.index))
    rel.checar(
        "as 27 UFs aparecem no catálogo",
        not faltando,
        f"faltando: {faltando or 'nenhuma'}; mínimo {por_uf.min()} estações ({por_uf.idxmin()})",
    )

    print("\nCritério 3 — faixas físicas na tabela diária")
    chuva = diario["chuva_mm"].dropna()
    rel.checar(
        f"chuva diária em [{FAIXA_CHUVA_DIA_MM[0]:.0f}, {FAIXA_CHUVA_DIA_MM[1]:.0f}) mm",
        bool(((chuva >= FAIXA_CHUVA_DIA_MM[0]) & (chuva < FAIXA_CHUVA_DIA_MM[1])).all()),
        f"min={chuva.min():.1f} max={chuva.max():.1f}",
    )
    for coluna in COLUNAS_TEMPERATURA:
        valores = diario[coluna].dropna()
        dentro = (valores >= FAIXA_TEMPERATURA_C[0]) & (valores <= FAIXA_TEMPERATURA_C[1])
        rel.checar(
            f"{coluna} em [{FAIXA_TEMPERATURA_C[0]:.0f}, {FAIXA_TEMPERATURA_C[1]:.0f}] °C",
            bool(dentro.all()),
            f"min={valores.min():.1f} max={valores.max():.1f}",
        )

    # Coerência interna: a máxima do dia não pode ser menor que a mínima. Não é
    # critério do ticket, mas é o teste que pega troca de coluna na origem.
    ambas = diario[["temp_max", "temp_min"]].dropna()
    invertidas = int((ambas["temp_max"] < ambas["temp_min"]).sum())
    rel.checar("temp_max >= temp_min", invertidas == 0, f"{invertidas} dias invertidos")

    print("\nCritério 4 — nenhum -9999 sobrevivendo como número")
    numericas = ["chuva_mm", *COLUNAS_TEMPERATURA, "umidade_media", "radiacao_total"]
    sobreviventes = {c: int((diario[c] == SENTINELA_AUSENTE).sum()) for c in numericas}
    total_sentinela = sum(sobreviventes.values())
    rel.checar(
        "sentinela de ausência não aparece como valor",
        total_sentinela == 0,
        f"{total_sentinela} ocorrências" + (f" em {[c for c, n in sobreviventes.items() if n]}" if total_sentinela else ""),
    )
    # Um valor muito negativo que não seja exatamente -9999 também é suspeito.
    suspeitos = int((diario[numericas] < -1000).sum().sum())
    rel.checar("nenhum valor absurdamente negativo", suspeitos == 0, f"{suspeitos} valores < -1000")

    print("\nCritério 5 — cobertura temporal por UF")
    dias_periodo = pd.period_range(config.PERIODO_INICIO, config.PERIODO_FIM, freq="D")
    na_janela = diario[
        (diario["data"] >= dias_periodo[0].start_time) & (diario["data"] <= dias_periodo[-1].end_time)
    ]
    total_dias = len(dias_periodo)

    validas = na_janela[na_janela["chuva_mm"].notna() | na_janela["temp_media"].notna()]
    dias_por_uf = validas.groupby("sigla_uf")["data"].nunique()
    dias_por_uf = dias_por_uf.reindex(sorted(siglas_validas), fill_value=0)
    cobertura = 100 * dias_por_uf / total_dias

    reprovadas = cobertura[cobertura < MINIMO_COBERTURA_PCT].sort_values()
    rel.checar(
        f"toda UF com >= {MINIMO_COBERTURA_PCT:.0f}% dos dias cobertos",
        reprovadas.empty,
        f"{len(cobertura) - len(reprovadas)}/27 UFs atendem; abaixo do corte: "
        + (", ".join(f"{uf}={v:.1f}%" for uf, v in reprovadas.items()) or "nenhuma"),
    )
    print(f"         janela {config.PERIODO_INICIO}..{config.PERIODO_FIM} = {total_dias} dias; "
          f"cobertura média {cobertura.mean():.1f}%, mediana {cobertura.median():.1f}%")

    _exportar_cobertura(na_janela, cobertura)

    print("\nResumo descritivo (para o T-021 e o T-025)")
    print(f"  linhas estação×dia: {len(diario)}")
    print(f"  estações distintas na série: {diario['codigo_estacao'].nunique()}")
    print(f"  período: {diario['data'].min().date()} a {diario['data'].max().date()}")
    presenca = {c: f"{100 * diario[c].notna().mean():.1f}%" for c in numericas}
    print(f"  preenchimento por coluna: {presenca}")
    estacoes_por_ano = diario.groupby("ano")["codigo_estacao"].nunique()
    print(f"  estações por ano: {estacoes_por_ano.to_dict()}")
    print("    (o crescimento de estações ao longo dos anos é real e cria degrau na")
    print("     média de uma UF — o T-021 precisa guardar n_estacoes por isso)")

    return rel.falhas


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="T-014 — critérios de aceite do coletor INMET")
    parser.parse_args(argv)

    if not SAIDA_CATALOGO.exists():
        print(f"ERRO: {SAIDA_CATALOGO} não existe. Rode: python -m src.coleta.inmet.catalogo")
        return 1
    if not SAIDA_DIARIA.exists() or not any(SAIDA_DIARIA.glob("*.parquet")):
        print(f"ERRO: {SAIDA_DIARIA} vazio. Rode: python -m src.coleta.inmet.agrega_dia")
        return 1

    catalogo = pd.read_csv(SAIDA_CATALOGO)
    diario = pd.read_parquet(SAIDA_DIARIA)
    print(f"T-014 — validando {SAIDA_DIARIA.relative_to(config.RAIZ)} ({len(diario)} linhas)")

    falhas = validar(catalogo, diario)

    print()
    if falhas:
        print(f"RESULTADO: {falhas} critério(s) falharam.")
        return 1
    print("RESULTADO: todos os critérios de aceite do T-014 passaram.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
