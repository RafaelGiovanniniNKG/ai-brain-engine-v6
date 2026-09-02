#!/usr/bin/env python
"""Bloqueia `git commit` com atribuição a IA ou com bypass de hooks.

Portado do v5 (`harness/git_commit.py` + `.claude/hooks/commit_guard.py`), onde
já pagou o preço de dois falsos positivos. Autocontido de propósito: o motor não
depende mais do repo do v5 estar por perto.

Protocolo: recebe JSON no stdin; **sair com 2 e a razão no stderr BLOQUEIA** a
chamada da ferramenta. É `PreToolUse` — o único lugar onde dá para impedir, e não
só reclamar depois.

O histórico de conserto, que é a parte valiosa:

  * Antes daqui saía `if "commit" in cmd: validar(cmd)` — duas falhas na mesma
    linha. O gatilho casava substring, então `wc -l commit_guard.py` e
    `chore(ratchet): commitar...` entravam; e o que ia ao validador era o COMANDO
    inteiro, então qualquer caminho com a palavra proibida derrubava a chamada.
    Na prática, `git add .claude/prds/` era bloqueado porque o caminho contém a
    palavra. **Falso positivo em guarda é caro duas vezes: atrapalha o trabalho e
    ensina a desligar a guarda.**
  * `commit` tem de ser um TOKEN, e tem de existir um token `git`.
  * Valida-se a MENSAGEM, não a linha de comando.
  * Corpo de heredoc é separado: `git commit -F - <<EOF` tem a mensagem no corpo;
    `cat > arquivo.py <<EOF` tem conteúdo de arquivo, que não interessa à guarda.
  * Flag de git é sensível a caixa: comparar em minúsculas fazia `-F` nunca casar.
  * `core.hooksPath` dentro de mensagem entre aspas não é bypass — foi falso
    positivo no primeiro commit desta própria guarda.

Limites ditos em voz alta em vez de fingidos: `git commit` sem mensagem (abre
editor) e `--amend --no-edit` não têm mensagem no comando, então não há o que
validar; e `-F arquivo` num comando composto que escreve o arquivo e commita em
seguida ainda não existe quando a guarda roda. **Esta guarda existe contra
atribuição ACIDENTAL, não contra um adversário.**
"""

from __future__ import annotations

import json
import os
import re
import shlex
import sys
from pathlib import Path

PROIBIDOS_PADRAO = "Co-Authored-By,Claude,AI-generated,Generated with Claude,🤖"

_HEREDOC_RE = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")
_FLAGS_MENSAGEM = ("-m", "--message")
_FLAGS_ARQUIVO = ("-F", "--file")


def _proibidos() -> list[str]:
    bruto = os.getenv("GIT_COMMIT_FORBIDDEN_PATTERNS", PROIBIDOS_PADRAO)
    return [p.strip() for p in bruto.split(",") if p.strip()]


def validar_mensagem(mensagem: str) -> tuple[bool, str | None]:
    for p in _proibidos():
        if re.search(re.escape(p), mensagem, re.IGNORECASE):
            return False, f"padrão proibido na mensagem de commit: {p}"
    return True, None


def _eh_token_git(token: str) -> bool:
    base = token.strip("\"'").replace("\\", "/").rsplit("/", 1)[-1].lower()
    return base.removesuffix(".exe") == "git"


def separar_heredocs(comando: str) -> tuple[str, list[str]]:
    """Devolve (comando sem os corpos, corpos)."""
    linhas = comando.split("\n")
    mantidas: list[str] = []
    corpos: list[str] = []
    i = 0
    while i < len(linhas):
        mantidas.append(linhas[i])
        m = _HEREDOC_RE.search(linhas[i])
        i += 1
        if not m:
            continue
        delim = m.group(2)
        corpo: list[str] = []
        while i < len(linhas) and linhas[i].strip() != delim:
            corpo.append(linhas[i])
            i += 1
        i += 1
        corpos.append("\n".join(corpo))
    return "\n".join(mantidas), corpos


def eh_git_commit(comando: str) -> bool:
    cabeca, _ = separar_heredocs(comando)
    try:
        tokens = shlex.split(cabeca, posix=False)
    except ValueError:
        tokens = cabeca.split()
    if not any(_eh_token_git(t) for t in tokens):
        return False
    return any(t.strip("\"'").lower() == "commit" for t in tokens)


def _ler_arquivo_mensagem(caminho: str) -> list[str]:
    try:
        return [Path(caminho.strip("\"'")).read_text(encoding="utf-8", errors="replace")]
    except OSError:
        return []


def extrair_mensagens(comando: str) -> list[str]:
    if not eh_git_commit(comando):
        return []
    cabeca, corpos = separar_heredocs(comando)
    try:
        tokens = shlex.split(cabeca, posix=True)
    except ValueError:
        tokens = cabeca.split()

    mensagens: list[str] = []
    quer_stdin = False
    entendeu = False
    i = 0
    while i < len(tokens):
        # sem .lower(): flag de git é sensível a caixa
        t = tokens[i]
        prox = tokens[i + 1] if i + 1 < len(tokens) else None
        if t in _FLAGS_MENSAGEM and prox is not None:
            mensagens.append(prox); entendeu = True; i += 2; continue
        if t.startswith("--message="):
            mensagens.append(t.split("=", 1)[1]); entendeu = True; i += 1; continue
        if t in _FLAGS_ARQUIVO and prox is not None:
            entendeu = True
            if prox == "-":
                quer_stdin = True
            else:
                mensagens.extend(_ler_arquivo_mensagem(prox))
            i += 2; continue
        if t.startswith("--file="):
            entendeu = True
            v = t.split("=", 1)[1]
            if v == "-":
                quer_stdin = True
            else:
                mensagens.extend(_ler_arquivo_mensagem(v))
            i += 1; continue
        if t.startswith("-") and not t.startswith("--") and "m" in t[1:]:
            pos = t.index("m", 1)
            if pos == len(t) - 1:
                if prox is not None:
                    mensagens.append(prox); entendeu = True; i += 2; continue
            else:
                mensagens.append(t[pos + 1:]); entendeu = True; i += 1; continue
        i += 1

    if quer_stdin:
        mensagens.extend(corpos)

    # Fail-closed: é commit, tem cara de trazer mensagem e o parser não entendeu
    # nada. Lacuna de parsing vira "olha tudo", nunca "deixa passar".
    if not mensagens and not entendeu and any(
        t.startswith(("-m", "--message", "-F", "--file")) for t in tokens
    ):
        return [comando]
    return mensagens


def detectar_bypass(comando: str) -> str | None:
    """Razão do bloqueio se o comando tenta pular hooks; None se limpo.

    Olha só a CABEÇA do comando, sem os corpos de heredoc. O v5 olhava a string
    inteira e por isso bloqueava um commit cuja MENSAGEM (escrita por heredoc)
    mencionava `core.hooksPath` — foi o que me barrou ao commitar este próprio
    conserto. O corpo de heredoc é conteúdo, não comando.
    """
    cabeca, _corpos = separar_heredocs(comando)
    try:
        tokens = shlex.split(cabeca, posix=False)
    except ValueError:
        return None  # comando mal-formado: deixa o shell rejeitar
    baixo = [t.lower() for t in tokens]
    if not any(_eh_token_git(t) for t in baixo):
        return None
    if "--no-verify" in baixo:
        return "`git --no-verify` pula os hooks do repo (é bypass da guarda)"
    if "commit" in baixo and "-n" in baixo:
        return "`git commit -n` equivale a --no-verify (pula hooks)"
    # substring só em token NÃO citado: mensagem que MENCIONA core.hooksPath não é bypass
    sem_aspas = [t for t in baixo if not t.startswith(('"', "'"))]
    if any("core.hookspath" in t for t in sem_aspas):
        return "`core.hooksPath` redireciona os hooks do repo (bypass de guarda)"
    return None


def main() -> int:
    try:
        d = json.load(sys.stdin)
    except Exception:
        return 0  # sem entrada legível: não interfere
    cmd = (d.get("tool_input") or {}).get("command", "")
    if not cmd:
        return 0

    sys.stderr.reconfigure(encoding="utf-8")
    razao = detectar_bypass(cmd)
    if razao:
        print(f"[guarda v6] bloqueado: {razao}", file=sys.stderr)
        return 2
    for mensagem in extrair_mensagens(cmd):
        ok, porque = validar_mensagem(mensagem)
        if not ok:
            print(
                f"[guarda v6] bloqueado: {porque}\n"
                "Reescreva a mensagem sem citar ferramenta de IA nem coautoria. "
                "Se precisar nomear o arquivo de instruções, escreva "
                "\"arquivo de instrução\".",
                file=sys.stderr,
            )
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
