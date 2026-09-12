"""Cache local em disco do resultado do LLM.

Uma entrada por combinação de (conteúdo de cada documento, versão do prompt, modelo, esquema).
Mesmos PDFs, mesma chave, nenhuma chamada. Diretório: EXTRACTOR_CACHE_DIR ou
<DATA_DIR>/cache/extractor (data/cache/ já é ignorado pelo git). Escrita atômica; diretório sem
permissão de escrita só gera aviso. `por_numero/<numero>.json` aponta para a última chave do processo
para `analisar` achar o resultado quando só recebe o número.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)
VERSAO_CACHE = 1


def dir_padrao() -> Path:
    explicito = os.environ.get("EXTRACTOR_CACHE_DIR", "").strip()
    if explicito:
        return Path(explicito)
    return Path(os.environ.get("DATA_DIR", "data")) / "cache" / "extractor"


def chave(documentos: list[tuple[str, str]], versao_prompt: str, modelo: str, hash_esquema: str) -> str:
    """SHA-256 de (versão do cache, prompt, modelo, esquema, [(nome, sha256 do arquivo) ordenados])."""
    h = hashlib.sha256()
    h.update(f"cache-v{VERSAO_CACHE}|{versao_prompt}|{modelo}|{hash_esquema}".encode())
    for nome, sha in sorted(documentos):
        h.update(f"|{nome}|{sha}".encode())
    return h.hexdigest()


class Cache:
    def __init__(self, diretorio: Path | None = None, ativo: bool = True) -> None:
        self.dir = Path(diretorio) if diretorio else dir_padrao()
        self.ativo = ativo

    def _caminho(self, chave_: str) -> Path:
        return self.dir / f"{chave_}.json"

    def _ponteiro(self, numero: str) -> Path:
        return self.dir / "por_numero" / f"{numero}.json"

    def ler(self, chave_: str) -> dict[str, Any] | None:
        if not self.ativo:
            return None
        caminho = self._caminho(chave_)
        if not caminho.is_file():
            return None
        try:
            return json.loads(caminho.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            log.warning("cache ilegível em %s (%s); ignorando", caminho, exc)
            return None

    def gravar(self, chave_: str, payload: dict[str, Any], numero: str | None = None) -> bool:
        if not self.ativo:
            return False
        try:
            self.dir.mkdir(parents=True, exist_ok=True)
            _escrever_atomico(self._caminho(chave_), payload)
            if numero:
                self._ponteiro(numero).parent.mkdir(parents=True, exist_ok=True)
                _escrever_atomico(self._ponteiro(numero), {"numero": numero, "chave": chave_})
            return True
        except OSError as exc:
            log.warning("não foi possível gravar o cache em %s (%s); seguindo sem cache", self.dir, exc)
            return False

    def ler_por_numero(self, numero: str) -> dict[str, Any] | None:
        if not self.ativo:
            return None
        ponteiro = self._ponteiro(numero)
        if not ponteiro.is_file():
            return None
        try:
            chave_ = json.loads(ponteiro.read_text(encoding="utf-8")).get("chave")
        except (OSError, ValueError):
            return None
        return self.ler(chave_) if chave_ else None

    def limpar(self) -> int:
        n = 0
        if self.dir.is_dir():
            for arq in list(self.dir.glob("*.json")) + list((self.dir / "por_numero").glob("*.json")):
                arq.unlink(missing_ok=True)
                n += 1
        return n


def _escrever_atomico(caminho: Path, payload: dict[str, Any]) -> None:
    texto = json.dumps(payload, ensure_ascii=False, indent=1, default=str)
    fd, tmp = tempfile.mkstemp(dir=str(caminho.parent), prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(texto)
        os.replace(tmp, caminho)
    finally:
        Path(tmp).unlink(missing_ok=True)
