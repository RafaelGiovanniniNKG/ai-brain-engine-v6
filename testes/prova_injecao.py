"""Prova da injeção de início de sessão. Rodar: python testes/prova_injecao.py

Este teste existe porque a peça ficou sem ele até o Passo 6 — e na primeira
refatoração eu removi a função de orçamento junto com outras, o `except` que
protege a sessão engoliu o erro, e a injeção passou a sair **vazia sem
reclamar**. Hook que não pode derrubar a sessão precisa de teste, justamente
porque ele nunca vai gritar.
"""
import json, os, subprocess, sys, tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "hooks"))
import importlib.util
spec = importlib.util.spec_from_file_location("ss", RAIZ / "hooks" / "session_start.py")
ss = importlib.util.module_from_spec(spec); spec.loader.exec_module(ss)

tudo = []


def injetar(cwd: str, motivo: str = "startup") -> str:
    p = subprocess.run([sys.executable, str(RAIZ / "hooks" / "session_start.py")],
                       input=json.dumps({"cwd": cwd, "start_reason": motivo}),
                       capture_output=True, text=True, encoding="utf-8", timeout=60)
    saida = (p.stdout or "").strip()
    if not saida:
        return ""
    return json.loads(saida)["hookSpecificOutput"]["additionalContext"]


def mostra(titulo: str, ok: bool, detalhe: str = "") -> bool:
    print(f"{'✔' if ok else '✘'} {titulo}" + (f"  — {detalhe}" if detalhe else ""))
    tudo.append(ok)
    return ok


print("=" * 70)
b = injetar(str(RAIZ))
mostra("injeta no próprio motor", len(b) > 300, f"{len(b)} chars")
mostra("traz o preâmbulo de referência histórica",
       "REFERÊNCIA HISTÓRICA" in b and "NÃO deve ser reexecutado" in b)
mostra("acento chega intacto (UTF-8 explícito)", "ação" in b or "não" in b)
mostra("traz regras vivas", "Regras aprendidas" in b)
mostra("nunca corta regra no meio da frase",
       not b.rstrip().endswith(("-", ",", "que", "de", "e")) and "bloco truncado" not in b)
mostra("respeita o teto de injeção", len(b) <= ss.TETO_TOTAL, f"{len(b)}/{ss.TETO_TOTAL}")

poc = r"C:\Github\cqrs-reference-architecture"
if Path(poc).is_dir():
    b2 = injetar(poc)
    mostra("acha a nota-índice curada da POC", "Nota do projeto no vault" in b2)
    mostra("traz a armadilha que faz perder tempo", "14 containers" in b2)
    mostra("diz quantas regras ficaram de fora, se ficaram",
           ("não listadas" in b2) or ("Regras aprendidas" in b2))
else:
    print("… POC ausente; três cenários pulados")

mostra("sessão retomada não injeta nada", injetar(str(RAIZ), "resume") == "")
mostra("pasta que não é repo não quebra", isinstance(injetar(str(Path(tempfile.gettempdir()))), str))

t = Path(tempfile.mkdtemp())
pequeno = t / "p.md"; pequeno.write_text("- linha\n" * 40, encoding="utf-8")
grande = t / "g.md"; grande.write_text("- linha bem comprida para gastar bytes de verdade\n" * 500, encoding="utf-8")
mostra("orçamento: índice pequeno não avisa", ss._orcamento_memoria(pequeno) == "")
mostra("orçamento: índice grande AVISA", "ORÇAMENTO DA MEMÓRIA" in ss._orcamento_memoria(grande))
mostra("orçamento: arquivo inexistente não quebra", ss._orcamento_memoria(t / "nao-existe.md") == "")

print("=" * 70)
print(f"RESULTADO: {sum(tudo)}/{len(tudo)} cenários como esperado")
sys.exit(0 if all(tudo) else 1)
