"""Prova da guarda de commit. Rodar: python testes/prova_guarda_commit.py

Os casos de PASSAR importam mais que os de bloquear: os dois falsos positivos
históricos desta guarda (`git add .claude/prds/` e uma mensagem que menciona
`core.hooksPath`) estão aqui como teste de regressão. Falso positivo em guarda é
caro duas vezes — atrapalha o trabalho e ensina a desligar a guarda.
"""
import json, subprocess, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
GUARDA = Path(__file__).resolve().parent.parent / "hooks" / "guarda_commit.py"

BLOQUEIA, PASSA = 2, 0

CASOS = [
    # (esperado, comando, por que este caso existe)
    (PASSA,    'git commit -m "feat(motor): sensores por edicao"', "commit normal"),
    (BLOQUEIA, 'git commit -m "feat: x\n\nCo-Authored-By: alguem <a@b.c>"', "coautoria de IA"),
    (BLOQUEIA, 'git commit -m "docs: ajusta o CLAUDE.md do projeto"', "cita ferramenta de IA"),
    (BLOQUEIA, 'git commit -m "chore: AI-generated fixture"', "declara geracao por IA"),
    (PASSA,    'git add .claude/prds/poc.md', "FALSO POSITIVO HISTORICO: o caminho contem a palavra"),
    (PASSA,    'wc -l commit_guard.py', "FALSO POSITIVO HISTORICO: substring 'commit' fora de git"),
    (PASSA,    'git commit -m "chore(ratchet): commitar as regras vivas"', "'commitar' na mensagem"),
    (BLOQUEIA, 'git commit --no-verify -m "feat: x"', "pula os hooks do repo"),
    (BLOQUEIA, 'git commit -n -m "feat: x"', "-n equivale a --no-verify"),
    (BLOQUEIA, 'git -c core.hooksPath=/dev/null commit -m "feat: x"', "redireciona os hooks"),
    (PASSA,    'git commit -m "fix: nao confiar em core.hooksPath"',
               "FALSO POSITIVO HISTORICO: mencao entre aspas nao e bypass"),
    (PASSA,    'git commit', "sem mensagem no comando: nao ha o que validar"),
    (PASSA,    'git commit --amend --no-edit', "amend sem edicao: a mensagem antiga ja passou"),
    (BLOQUEIA, 'git commit -F - <<EOF\nfeat: x\n\nGenerated with Claude\nEOF', "heredoc E a mensagem"),
    (PASSA,    'cat > nota.py <<EOF\n# menciona Claude no conteudo\nEOF', "heredoc de ARQUIVO, nao de commit"),
    (BLOQUEIA, 'git commit -am "wip: Claude ajudou"', "cluster de flags curtas -am"),
    (BLOQUEIA, 'git commit --message="feat: Claude"', "forma --message="),
    (PASSA,    'git push origin master', "push nao e commit"),
    (PASSA,    'git commit -F - <<EOF\nfix: separar o corpo do heredoc\n\nO v5 bloqueava mensagem que mencionava core.hooksPath.\nEOF',
               "REGRESSAO: mencao a core.hooksPath no CORPO do heredoc nao e bypass (o guard do v5 barrava)"),
    (BLOQUEIA, 'git -c core.hooksPath=/tmp/vazio commit -F - <<EOF\nfix: x\nEOF',
               "bypass de verdade continua bloqueado, mesmo com heredoc"),
]


def rodar(cmd: str) -> int:
    p = subprocess.run([sys.executable, str(GUARDA)],
                       input=json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}}),
                       capture_output=True, text=True, encoding="utf-8", timeout=30)
    return p.returncode


falhas = []
for esperado, cmd, porque in CASOS:
    obtido = rodar(cmd)
    ok = obtido == esperado
    rotulo = {0: "PASSA", 2: "BLOQUEIA"}
    print(f"{'✔' if ok else '✘'} {rotulo.get(esperado):8s} | {cmd.splitlines()[0][:58]:58s} | {porque}")
    if not ok:
        falhas.append((cmd, esperado, obtido, porque))

print("=" * 70)
print(f"RESULTADO: {len(CASOS) - len(falhas)}/{len(CASOS)} casos como esperado")
for cmd, esp, obt, porque in falhas:
    print(f"  FALHOU: esperava {esp}, obteve {obt} — {porque}\n    {cmd[:100]}")
sys.exit(0 if not falhas else 1)
