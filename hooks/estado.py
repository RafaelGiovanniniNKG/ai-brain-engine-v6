#!/usr/bin/env python
"""Registro do que aconteceu na sessão. Sem LLM, sem rede, sem opinião.

O portão do encerramento precisa responder a uma pergunta de fato — "editou
código e rodou teste verde depois?" — e a transcrição da sessão não serve para
isso: a documentação oficial avisa que ela é escrita de forma assíncrona e pode
atrasar em relação ao turno atual. Então cada hook anota o que viu, aqui, na
hora.

Isto também é a camada 0 da documentação automática (Passo 4): o mesmo registro
que decide o portão é o que depois alimenta o diário no vault.

Um arquivo JSON por sessão. Escrita atômica (grava em `.tmp` e renomeia), porque
dois hooks podem disparar quase juntos e um arquivo meio escrito é pior que
nenhum.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

EXT_CODIGO = {".cs", ".razor", ".cshtml", ".ts", ".tsx", ".mts", ".cts", ".js", ".mjs", ".dart"}


def pasta() -> Path:
    base = os.environ.get("CLAUDE_PLUGIN_DATA") or os.environ.get("LOCALAPPDATA")
    raiz = Path(base) / "ai-brain-engine-v6" if base else Path(__file__).resolve().parent.parent / "_estado"
    raiz.mkdir(parents=True, exist_ok=True)
    return raiz


def _caminho(sessao: str) -> Path:
    seguro = "".join(c for c in (sessao or "sem-sessao") if c.isalnum() or c in "-_")[:64]
    return pasta() / f"{seguro or 'sem-sessao'}.json"


def ler(sessao: str) -> dict:
    try:
        return json.loads(_caminho(sessao).read_text(encoding="utf-8"))
    except Exception:
        return {}


def gravar(sessao: str, dados: dict) -> None:
    alvo = _caminho(sessao)
    tmp = alvo.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
        os.replace(tmp, alvo)
    except Exception:
        pass


def anotar(sessao: str, **campos) -> dict:
    d = ler(sessao)
    d.update(campos)
    gravar(sessao, d)
    return d


def registrar_edicao(sessao: str, arquivo: str, repo: str | None, reprovou: str = "") -> None:
    """Uma edição de CÓDIGO. Edição de markdown ou json não pede teste."""
    if Path(arquivo).suffix.lower() not in EXT_CODIGO:
        return
    d = ler(sessao)
    d["ultima_edicao"] = {"ts": time.time(), "arquivo": arquivo, "repo": repo or ""}
    arquivos = d.get("arquivos_tocados") or []
    if arquivo not in arquivos:
        arquivos.append(arquivo)
    d["arquivos_tocados"] = arquivos[-50:]
    if reprovou:
        d["sensor_reprovou"] = {"ts": time.time(), "arquivo": arquivo, "resumo": reprovou[:800]}
    gravar(sessao, d)


def registrar_execucao(sessao: str, comando: str, tipo: str, ok: bool | None) -> None:
    """Um `dotnet test`, `ng test`, `dotnet build`… com o veredito, quando dá para provar."""
    d = ler(sessao)
    d[f"ultimo_{tipo}"] = {"ts": time.time(), "comando": comando[:300], "ok": ok}
    gravar(sessao, d)


def liberar(sessao: str, motivo: str) -> None:
    anotar(sessao, escape={"ts": time.time(), "motivo": motivo[:200]})
