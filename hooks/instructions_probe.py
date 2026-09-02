#!/usr/bin/env python
"""Prova o que REALMENTE chegou ao modelo como instrução.

Existe por causa da falha central do v5: o `AGENTS.md` era a constituição do
motor e nunca era lido (o Claude Code lê `CLAUDE.md`), e as 36 regras vivas
nunca eram injetadas. Ninguém percebeu porque não havia como olhar.

O evento `InstructionsLoaded` entrega o caminho, o motivo e o conteúdo de cada
arquivo de instrução carregado. Este script só anota. É temporário: sai do
`hooks.json` quando o Passo 1 estiver provado (está registrado no plano).

Não escreve nada no stdout — hook `async` descarta a saída, e mesmo se não
descartasse, ruído no início da sessão é o que este motor existe para evitar.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

DESTINO = Path(__file__).resolve().parent.parent / "_prova" / "instrucoes-carregadas.log"


def main() -> int:
    try:
        d = json.loads(sys.stdin.read() or "{}")
    except Exception:
        return 0
    conteudo = d.get("content") or ""
    linha = "\t".join([
        datetime.now().isoformat(timespec="seconds"),
        str(d.get("session_id", ""))[:8],
        str(d.get("load_reason", "?")),
        str(d.get("cwd", "")),
        str(d.get("file_path", "")),
        f"{len(conteudo)}ch",
        f"{len(conteudo.splitlines())}linhas",
    ])
    try:
        DESTINO.parent.mkdir(parents=True, exist_ok=True)
        with DESTINO.open("a", encoding="utf-8", newline="\n") as f:
            f.write(linha + "\n")
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
