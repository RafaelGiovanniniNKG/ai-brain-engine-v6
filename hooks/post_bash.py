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


def _saida_do_comando(d: dict) -> str:
    """A saída do comando, no formato que o Claude Code manda DE VERDADE.

    `tool_use_result` chega como **lista de blocos** `{"type","text"}` — não como
    string. O código antigo fazia `json.dumps` da lista, o que produz uma única
    linha com `\\n` escapado, e aí os padrões ancorados em `^...$` de
    `_evidencia` nunca casavam: em toda sessão real o registro saía com
    `evidencia: ""`, enquanto a prova passava porque o fixture mandava string.
    Medido em 03/09/2026 no estado da própria sessão.

    Em `PostToolUseFailure` a saída não vem em `tool_use_result`, e sim em
    `error` — sem ler esse campo, execução vermelha entra sem evidência nenhuma.
    """
    partes: list[str] = []
    r = d.get("tool_use_result")
    if isinstance(r, str):
        partes.append(r)
    elif isinstance(r, list):
        for bloco in r:
            if isinstance(bloco, str):
                partes.append(bloco)
            elif isinstance(bloco, dict):
                for chave in ("text", "content", "output"):
                    if isinstance(bloco.get(chave), str):
                        partes.append(bloco[chave])
                        break
    elif isinstance(r, dict):
        for chave in ("text", "stdout", "output"):
            if isinstance(r.get(chave), str):
                partes.append(r[chave])
    for chave in ("error", "stderr"):
        if isinstance(d.get(chave), str) and d[chave].strip():
            partes.append(d[chave])
    return "\n".join(partes).strip()


def _evidencia(saida: str) -> str:
    """A linha do placar, guardada palavra por palavra.

    Sem isso o diário registra "o teste passou" — que é exatamente a afirmação
    sem prova que este motor existe para impedir. Com isso ele registra
    "Failed: 0, Passed: 319", que é verificável por quem ler depois.
    """
    for padrao in (r"^.*Failed:\s*\d+.*$", r"^.*Passed!.*$", r"^.*Test Run.*$",
                   r"^.*Executed \d+ of \d+.*$", r"^.*Tests:.*$", r"^.*Build succeeded.*$",
                   r"^.*Compila[çc][ãa]o.*$"):
        m = re.search(padrao, saida or "", re.M | re.I)
        if m:
            return m.group(0).strip()[:200]
    return ""


def _tipo(cmd: str) -> str | None:
    if any(re.search(p, cmd, re.I) for p in PADROES_TESTE):
        return "teste"
    if any(re.search(p, cmd, re.I) for p in PADROES_BUILD):
        return "build"
    return None


def _veredito(d: dict, saida: str) -> bool | None:
    """True/False quando dá para provar; None quando é indeterminado.

    O EVENTO é o veredito mais confiável que existe aqui: comando com saída
    não-zero dispara `PostToolUseFailure`, e só comando bem-sucedido dispara
    `PostToolUse`. Medido em 03/09/2026 com o mesmo texto de comando em `exit 1`
    e `exit 0` — só o segundo chegava, e o motor ficava cego a TODA execução
    vermelha. Cego a vermelho abre um caminho de falso verde: teste do projeto A
    reprova sem deixar rastro, teste do projeto B passa e o portão libera.
    """
    if d.get("hook_event_name") == "PostToolUseFailure":
        return False
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
    saida = _saida_do_comando(d)
    sessao = d.get("session_id", "")

    # Commit bem-sucedido: a verdade que a conversa não pode falsear. O `git
    # commit` imprime `[branch sha] mensagem` — é daí que sai o registro, não da
    # afirmação de que commitou.
    if re.search(r"\bgit\b.{0,40}\bcommit\b", cmd, re.I | re.S):
        for sha_m in re.finditer(r"^\[(?:\S+\s+)?(?:\(root-commit\)\s+)?([0-9a-f]{7,40})\]\s*(.*)$",
                                 saida, re.M):
            estado.registrar_commit(sessao, sha_m.group(1), sha_m.group(2).strip(),
                                    str((d.get("cwd") or "")))

    tipo = _tipo(cmd)
    if not tipo:
        return 0
    # O `cwd` vai junto porque teste VERDE é o que dá baixa numa edição de
    # sub-agente pendente naquele diretório — sem isso a pendência sobreviveria
    # ao próprio conserto e barraria a sessão seguinte sem motivo.
    estado.registrar_execucao(sessao, cmd, tipo, _veredito(d, saida), _evidencia(saida),
                              cwd=str(d.get("cwd") or ""))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
