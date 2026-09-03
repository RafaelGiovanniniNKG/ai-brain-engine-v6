#!/usr/bin/env python
"""Revisor lê, relata e pergunta. Não conserta.

Medido em 03/09/2026: pedi a um revisor que rodasse `printf ... > arquivo.txt` e
ele **escreveu no repositório**, sem recusa, sem pedido de permissão. A skill
`v6-revisar` já dizia "não commita e não altera código — é só leitura", mas isso
é instrução, e instrução não é impedimento. O revisor precisa do terminal para
rodar `git diff`, e pelo terminal se escreve.

Por que não foi resolvido declarando `tools: ... Bash(git diff:*)` no revisor:
tentei, a conferência oficial aprovou, e o revisor **continuou escrevendo**. Não
deu para distinguir "o padrão não é suportado" de "a definição do revisor foi
carregada no início da sessão, antes da minha edição" — e mudança que eu não
consigo medir tem um jeito de falhar pior que o problema: o revisor perde o
terminal em silêncio e passa a revisar sem ver o diff. Então a regra mora aqui,
onde ela é testável alimentando o script com a entrada, como todas as outras.

Protocolo: `PreToolUse`. Sair com **2** e a razão no stderr BLOQUEIA a chamada.

A regra é LISTA DE PERMITIDOS, não lista de proibidos, e isso é deliberado:
revisor só precisa de comando de leitura, então comando desconhecido é NEGADO.
Lista de proibidos falharia aberta — bastaria uma forma que eu não imaginei
(`python -c`, `tee`, `Set-Content`, um script) para a escrita passar. Falhar
fechado custa um revisor que às vezes reclama que não pôde rodar algo; falhar
aberto custa código alterado por quem só devia opinar.

Vale SÓ dentro de sub-agente (`agent_id` preenchido) e SÓ para os revisores
declarados aqui: a sessão principal e os outros sub-agentes não são afetados.
"""

from __future__ import annotations

import json
import re
import sys

# Sub-agentes cujo papel é OPINAR. `agent_type` chega com o prefixo do plugin.
REVISORES = ("csharp-reviewer", "typescript-reviewer")

# Comandos de leitura que um revisor legitimamente precisa. Comparado contra o
# início de cada trecho do comando, sem distinguir maiúsculas.
PERMITIDOS = (
    "git diff", "git show", "git log", "git status", "git merge-base",
    "git rev-parse", "git rev-list", "git blame", "git ls-files", "git branch",
    "git config --get", "git remote -v", "git cat-file",
    "cat", "head", "tail", "less", "more", "type",
    "grep", "rg", "egrep", "fgrep", "select-string",
    "find", "ls", "dir", "get-childitem", "wc", "sort", "uniq", "cut", "awk",
    "echo", "pwd", "basename", "dirname", "realpath", "stat", "file", "tree",
    "get-content", "test-path", "measure-object",
)

# `sed` só na forma que IMPRIME. `sed -i` escreve no arquivo.
SED_LEITURA = re.compile(r"^sed\s+(?!.*(?:-i\b|--in-place))", re.I)

# Separadores que emendam comandos. Cada trecho é conferido por si.
SEPARADORES = re.compile(r"\|\||&&|;|\||\n")

# Redirecionamento é escrita, em qualquer trecho, mesmo com comando permitido:
# `cat a > b` lê e escreve. `2>&1` e `2>/dev/null` não contam.
REDIRECIONA = re.compile(r"(?<![0-9])>{1,2}(?!&\d)")


def _entrada() -> dict:
    try:
        return json.loads(sys.stdin.buffer.read().decode("utf-8", errors="replace") or "{}")
    except Exception:
        return {}


def _e_revisor(d: dict) -> bool:
    if not d.get("agent_id"):
        return False  # sessão principal: esta guarda não se aplica
    tipo = (d.get("agent_type") or "").lower()
    return any(r in tipo for r in REVISORES)


# Opções GLOBAIS do git, que vêm ANTES do subcomando e empurram o subcomando
# para longe do começo da linha. `git -C <caminho> diff` foi exatamente a forma
# que o revisor usou na medição de 03/09, e a primeira versão desta guarda a
# bloqueou — ou seja, ela impedia o revisor de fazer o trabalho dele. Removê-las
# não abre brecha: o que decide é o SUBCOMANDO, e `git -c ... commit` continua
# caindo em `git commit`, que não está na lista.
GIT_GLOBAIS = re.compile(
    r"^git\s+(?:(?:-C|-c)\s+\S+\s+|--git-dir=\S+\s+|--work-tree=\S+\s+|--no-pager\s+|-P\s+)+",
    re.I,
)


def _trecho_permitido(trecho: str) -> bool:
    t = trecho.strip().strip("()").strip()
    if not t:
        return True
    # variável de ambiente na frente (`FOO=bar cmd`) não muda o comando
    t = re.sub(r"^(?:[A-Za-z_][A-Za-z0-9_]*=\S*\s+)+", "", t)
    t = GIT_GLOBAIS.sub("git ", t)
    baixo = t.lower()
    if SED_LEITURA.match(baixo):
        return True
    return any(baixo.startswith(p) for p in PERMITIDOS)


def negar(cmd: str) -> str | None:
    """A razão da recusa, ou None se pode passar."""
    if REDIRECIONA.search(cmd):
        return "o comando redireciona a saída para arquivo"
    # `$(...)` e crases escondem comando dentro de comando
    interno = re.findall(r"\$\(([^)]*)\)|`([^`]*)`", cmd)
    for a, b in interno:
        dentro = a or b
        for trecho in SEPARADORES.split(dentro):
            if not _trecho_permitido(trecho):
                return f"há um comando não permitido dentro de substituição: `{trecho.strip()[:60]}`"
    sem_interno = re.sub(r"\$\([^)]*\)|`[^`]*`", " ", cmd)
    for trecho in SEPARADORES.split(sem_interno):
        if not _trecho_permitido(trecho):
            return f"`{trecho.strip()[:60]}` não é comando de leitura"
    return None


def main() -> int:
    d = _entrada()
    if not _e_revisor(d):
        return 0
    cmd = ((d.get("tool_input") or {}).get("command") or "")
    if not cmd.strip():
        return 0
    razao = negar(cmd)
    if not razao:
        return 0
    sys.stderr.reconfigure(encoding="utf-8")
    print(
        f"[guarda v6] revisor não altera nada: {razao}.\n"
        "Seu papel é LER o diff, relatar o que achou e deixar o Rafael decidir se "
        "corrige. Não conserte, não commite, não escreva arquivo — descreva o "
        "problema com `arquivo:linha` e a consequência concreta, e siga a revisão "
        "com os comandos de leitura.",
        file=sys.stderr,
    )
    return 2  # 2 BLOQUEIA a chamada


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)  # guarda que quebra não pode travar a revisão
