"""Utilitários de rede compartilhados pelos coletores.

Concentra três coisas que todo coletor do projeto precisa acertar e que são
fáceis de errar de formas silenciosas:

1. **User-Agent de navegador** — o portal do INMET fecha a conexão sem ele.
2. **Retentativa com espera exponencial** — os portais do governo dão 502/timeout
   com frequência; um coletor que morre no ano 7 de 13 é inútil.
3. **Download atômico** — o arquivo só aparece no destino final quando terminou
   de baixar. Sem isso, um Ctrl-C no meio deixa um ZIP truncado que *parece*
   pronto, e o erro só aparece muito depois, na leitura.
"""

from __future__ import annotations

import time
from pathlib import Path

import requests

from . import config


def sessao() -> requests.Session:
    """Sessão HTTP com o User-Agent que os portais do governo exigem."""
    s = requests.Session()
    s.headers.update({"User-Agent": config.USER_AGENT})
    return s


def _com_retentativa(descricao: str, funcao):
    """Executa `funcao()`, repetindo com espera exponencial em caso de falha."""
    ultimo_erro: Exception | None = None
    for tentativa in range(1, config.HTTP_TENTATIVAS + 1):
        try:
            return funcao()
        except (requests.RequestException, OSError) as erro:
            ultimo_erro = erro
            if tentativa == config.HTTP_TENTATIVAS:
                break
            espera = 2**tentativa
            print(
                f"    ! {descricao}: {type(erro).__name__} "
                f"(tentativa {tentativa}/{config.HTTP_TENTATIVAS}), "
                f"repetindo em {espera}s"
            )
            time.sleep(espera)
    raise RuntimeError(f"falhou depois de {config.HTTP_TENTATIVAS} tentativas: {descricao}") from ultimo_erro


def get_texto(url: str, cache: Path | None = None, forcar: bool = False) -> str:
    """GET que devolve texto, opcionalmente cacheado em disco.

    O cache é o dado bruto exatamente como veio da fonte — é ele que vai para
    `data/raw/`, para que a agregação seja reprodutível sem rede.
    """
    if cache is not None and cache.exists() and not forcar:
        return cache.read_text(encoding="utf-8")

    def _fazer() -> str:
        with sessao() as s:
            r = s.get(url, timeout=config.HTTP_TIMEOUT)
            r.raise_for_status()
            # As APIs do IBGE e da ANA devolvem UTF-8 mas nem sempre declaram,
            # e aí o requests adivinha ISO-8859-1 e estraga os acentos.
            r.encoding = r.encoding if "charset" in r.headers.get("content-type", "") else "utf-8"
            return r.text

    texto = _com_retentativa(url, _fazer)
    if cache is not None:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(texto, encoding="utf-8")
    return texto


def tamanho_remoto(url: str) -> int | None:
    """Tamanho do arquivo remoto em bytes, ou None se o servidor não informar.

    Usa GET com Range de 1 byte em vez de HEAD porque o portal do INMET
    responde HEAD com reset de conexão.
    """
    try:
        with sessao() as s:
            r = s.get(url, headers={"Range": "bytes=0-0"}, timeout=config.HTTP_TIMEOUT, stream=True)
            r.close()
            faixa = r.headers.get("Content-Range", "")
            if "/" in faixa:
                return int(faixa.rsplit("/", 1)[1])
    except (requests.RequestException, ValueError):
        pass
    return None


def baixar_arquivo(url: str, destino: Path, forcar: bool = False) -> bool:
    """Baixa `url` para `destino`. Devolve True se baixou, False se reaproveitou.

    Idempotente: se o arquivo local já existe com o mesmo tamanho do remoto, não
    baixa de novo. Isso torna o coletor seguro para rodar várias vezes e permite
    retomar de onde parou depois de uma interrupção.
    """
    destino.parent.mkdir(parents=True, exist_ok=True)
    esperado = tamanho_remoto(url)

    if destino.exists() and not forcar:
        local = destino.stat().st_size
        if esperado is None:
            print(f"    = {destino.name} já existe ({local / 1e6:.1f} MB); tamanho remoto desconhecido, mantendo")
            return False
        if local == esperado:
            print(f"    = {destino.name} já completo ({local / 1e6:.1f} MB)")
            return False
        print(f"    ~ {destino.name} incompleto ({local / 1e6:.1f} de {esperado / 1e6:.1f} MB), baixando de novo")

    parcial = destino.with_suffix(destino.suffix + ".part")

    def _fazer() -> None:
        with sessao() as s, s.get(url, timeout=config.HTTP_TIMEOUT, stream=True) as r:
            r.raise_for_status()
            baixado = 0
            with parcial.open("wb") as f:
                for bloco in r.iter_content(chunk_size=1 << 20):
                    if bloco:
                        f.write(bloco)
                        baixado += len(bloco)
        if esperado is not None and baixado != esperado:
            parcial.unlink(missing_ok=True)
            raise OSError(f"tamanho divergente: recebi {baixado} bytes, esperava {esperado}")

    _com_retentativa(f"download de {destino.name}", _fazer)
    parcial.replace(destino)  # atômico: só agora o arquivo final passa a existir
    print(f"    + {destino.name} ({destino.stat().st_size / 1e6:.1f} MB)")
    return True
