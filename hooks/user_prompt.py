#!/usr/bin/env python
"""Escuta o escape do portão na fala do Rafael.

O portão do encerramento é rígido de propósito, mas não pode virar cadeia: uma
frase explícita libera o encerramento da vez. Fica aqui, e não numa decisão do
modelo, porque autorização tem que vir de quem manda — se o modelo pudesse se
liberar, não seria portão.

Não bloqueia nada e não injeta nada: só anota.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import estado  # noqa: E402

# Frases de liberação. Deliberadamente explícitas: nada de "ok", "segue",
# "beleza" — palavra comum viraria escape acidental e o portão sumiria sozinho.
ESCAPES = (
    r"termina assim mesmo",
    r"encerra assim mesmo",
    r"pode encerrar sem (rodar |o )?teste",
    r"sem rodar (o )?teste",
    r"n[ãa]o precisa (rodar )?(o )?teste",
    r"deixa (o )?teste (pra|para) depois",
    r"pula o (port[ãa]o|teste)",
    r"ignora o port[ãa]o",
)


def main() -> int:
    try:
        d = json.loads(sys.stdin.read() or "{}")
    except Exception:
        return 0
    texto = (d.get("prompt") or d.get("user_prompt") or "")
    if not isinstance(texto, str) or not texto.strip():
        return 0
    for padrao in ESCAPES:
        m = re.search(padrao, texto, re.I)
        if m:
            estado.liberar(d.get("session_id", ""), m.group(0))
            break
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
