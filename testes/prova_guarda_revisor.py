"""Prova de que revisor lê mas não escreve: vinte e quatro casos.

Rodar: python testes/prova_guarda_revisor.py   (sai 0 se todos passarem)

Nasceu de uma medição, não de uma suspeita: em 03/09/2026 pedi a um revisor que
rodasse `printf ... > arquivo.txt` e ele escreveu no repositório, sem recusa e
sem pedido de permissão. A skill já dizia "é só leitura" — mas instrução não é
impedimento, e o revisor precisa do terminal para rodar `git diff`.

A regra é LISTA DE PERMITIDOS: comando desconhecido é negado. Lista de proibidos
falharia aberta — bastaria uma forma não imaginada para a escrita passar.

Os casos que mais importam são de DOIS tipos, e os dois têm de ficar verdes:
  * o revisor consegue fazer seu trabalho (ler o diff, buscar, abrir arquivo);
  * e não consegue escrever, nem por caminho torto (redirecionamento, `sed -i`,
    comando emendado com `&&`, comando escondido em `$(...)`).
E o mais importante de todos: a guarda **não afeta a sessão principal**, onde
escrever é o trabalho.
"""
import json
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
H = Path(__file__).resolve().parent.parent / "hooks"

REVISOR = {"agent_id": "subagent_123", "agent_type": "ai-brain-engine-v6:csharp-reviewer"}


def rodar(cmd: str, quem: dict) -> tuple[bool, str]:
    """(bloqueou?, razão). Sair com 2 bloqueia a chamada."""
    p = subprocess.run(
        [sys.executable, str(H / "guarda_revisor.py")],
        input=json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd},
                          "hook_event_name": "PreToolUse", **quem}).encode("utf-8"),
        capture_output=True, timeout=60,
    )
    return p.returncode == 2, (p.stderr or b"").decode("utf-8", "replace").strip()


tudo: list[bool] = []


def caso(cmd: str, espera_bloqueio: bool, porque: str, quem: dict = REVISOR) -> None:
    bloqueou, razao = rodar(cmd, quem)
    ok = bloqueou == espera_bloqueio
    tudo.append(ok)
    marca = "✔" if ok else "✘"
    rotulo = "BLOQUEIA" if bloqueou else "PASSA   "
    print(f"{marca} {rotulo} | {cmd[:56]:<56} | {porque}")
    if not ok and razao:
        print(f"           razão dada: {razao.splitlines()[0][:100]}")


print("=" * 100)
print("O revisor consegue trabalhar")
caso("git diff --stat HEAD~1", False, "ler o diff e o trabalho dele")
caso("git -C C:/Github/ai-brain-engine-v6 diff --stat HEAD~1", False,
     "com -C: a forma que o revisor USOU na medicao")
caso("git --no-pager diff", False, "opcao global antes do subcomando")
caso("git -c core.pager=cat show HEAD", False, "-c antes de subcomando de leitura")
caso("git -c core.hooksPath=/dev/null commit -m x", True,
     "opcao global NAO libera subcomando de escrita")
caso("git show HEAD:hooks/estado.py", False, "abrir versao antiga")
caso("git merge-base HEAD origin/master", False, "achar a base da branch")
caso("grep -rn 'IRequest' src/", False, "buscar no codigo")
caso("cat src/Program.cs", False, "abrir arquivo")
caso("sed -n '1,50p' src/Program.cs", False, "sed que IMPRIME")
caso("git diff --stat | head -40", False, "emendar duas leituras")
caso("dotnet test 2>&1 | grep -i failed", True, "rodar teste nao e ler diff")

print()
print("E nao consegue escrever, nem por caminho torto")
caso("printf 'x' > ESCRITA-DE-REVISOR.txt", True, "o caso MEDIDO em 03/09")
caso("echo x >> src/Program.cs", True, "acrescentar tambem e escrever")
caso("sed -i 's/a/b/' src/Program.cs", True, "sed -i escreve no arquivo")
caso("cat src/Program.cs > copia.cs", True, "comando permitido + redirecionamento")
caso("git diff --stat && rm -rf src", True, "escondido depois do &&")
caso("echo $(printf 'x' > y.txt)", True, "escondido em substituicao")
caso("git commit -am 'conserto do revisor'", True, "revisor nao commita")
caso("python -c \"open('x.cs','w').write('1')\"", True, "interprete nao esta na lista")
caso("git diff --stat 2>/dev/null", False, "descartar erro NAO e escrever")

print()
print("E a sessão principal NÃO é afetada — lá escrever é o trabalho")
caso("printf 'x' > qualquer.txt", False, "sem agent_id: passa", quem={})
caso("sed -i 's/a/b/' src/Program.cs", False, "sem agent_id: passa", quem={})
caso("printf 'x' > qualquer.txt", False, "outro sub-agente, nao revisor",
     quem={"agent_id": "subagent_9", "agent_type": "general-purpose"})

print("=" * 100)
print(f"RESULTADO: {sum(tudo)}/{len(tudo)} casos como esperado")
sys.exit(0 if all(tudo) else 1)
