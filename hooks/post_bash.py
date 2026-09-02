#!/usr/bin/env python
"""Anota execução de teste e de build, com o veredito.

Regra de projeto, e ela é o coração do portão: **só conta como VERDE o que dá
para provar verde.** Se o comando rodou mas a saída não permite concluir que
passou, o registro fica `ok: null` — e o portão trata indeterminado como não
provado, não como sucesso.

Isso vem de uma das regras vivas do Rafael: "classifique em três, não em dois —
esperado segue, sabidamente errado aborta, indeterminado aborta também".
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import estado  # noqa: E402

# comando -> tipo de execução
PADROES_TESTE = (
    r"\bdotnet\s+test\b", r"\bng\s+test\b", r"\bnpm\s+(run\s+)?test\b",
    r"\byarn\s+test\b", r"\bnpx\s+(jest|vitest|karma)\b", r"\b(jest|vitest)\b",
    r"\bpytest\b", r"\bdart\s+test\b", r"\bflutter\s+test\b",
)
PADROES_BUILD = (r"\bdotnet\s+build\b", r"\bdotnet\s+publish\b", r"\bng\s+build\b", r"\btsc\b(?!\s*--version)")

# marcas de sucesso e de falha na saída. Falha vence empate.
SUCESSO = (
    r"\bPassed!", r"Passed:\s*\d+", r"Test Run Successful",
    r"\bSUCCESS\b", r"Executed \d+ of \d+ \(SUCCESS\)",
    r"Tests:.*\b\d+ passed", r"\b\d+ passed\b", r"Build succeeded",
    r"Compilação bem-sucedida", r"todos os testes",
)
FALHA = (
    r"Failed:\s*[1-9]", r"Test Run Failed", r"\b[1-9]\d* failed\b",
    r"\berror [A-Z]{2}\d+", r"\berro [A-Z]{2}\d+",
    r"Compilação falhou", r"\bexit code [1-9]", r"não foi possível",
)

# Padrões em que a CAIXA é a informação. `\bFAILED\b` sem distinguir maiúsculas
# casa com o `Failed: 0` do relatório de SUCESSO do `dotnet test` — lê verde como
# vermelho. Custou um cenário da própria prova deste portão.
FALHA_MAIUSCULA = (r"\bFAILED\b", r"Build FAILED", r"\bFailed!", r"\bERROR\b")


def _tipo(cmd: str) -> str | None:
    if any(re.search(p, cmd, re.I) for p in PADROES_TESTE):
        return "teste"
    if any(re.search(p, cmd, re.I) for p in PADROES_BUILD):
        return "build"
    return None


def _veredito(d: dict, saida: str) -> bool | None:
    """True/False quando dá para provar; None quando é indeterminado."""
    r = d.get("tool_use_result")
    if isinstance(r, dict):
        for chave in ("exit_code", "exitCode", "returncode"):
            if isinstance(r.get(chave), int):
                return r[chave] == 0
    tr = d.get("tool_result")
    if isinstance(tr, dict) and isinstance(tr.get("outcome"), str):
        if tr["outcome"] == "failure":
            return False
    if any(re.search(p, saida, re.I) for p in FALHA):
        return False
    if any(re.search(p, saida) for p in FALHA_MAIUSCULA):
        return False
    if any(re.search(p, saida, re.I) for p in SUCESSO):
        return True
    return None


def main() -> int:
    try:
        d = json.loads(sys.stdin.read() or "{}")
    except Exception:
        return 0
    cmd = ((d.get("tool_input") or {}).get("command") or "")
    if not cmd:
        return 0
    tipo = _tipo(cmd)
    if not tipo:
        return 0
    r = d.get("tool_use_result")
    saida = r if isinstance(r, str) else json.dumps(r, ensure_ascii=False) if r else ""
    estado.registrar_execucao(d.get("session_id", ""), cmd, tipo, _veredito(d, saida))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
