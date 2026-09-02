"""Prova do portão do encerramento: sete cenários, em ordem, com o veredito de cada um.

Rodar: python testes/prova_portao.py   (sai 0 se todos passarem)

Usa a POC `cqrs-reference-architecture` como alvo, só para LER caminho de projeto
— nenhum arquivo dela é tocado. Se a POC não estiver na máquina, o cenário que
resolve o projeto de teste degrada para o comando genérico, e o resto continua
valendo.

O cenário 3 existe por um defeito real: o padrão `FAILED` sem distinguir
maiúsculas casava com o `Failed: 0` do relatório de SUCESSO do `dotnet test`, e o
portão lia teste verde como vermelho.
"""
import json, os, subprocess, sys, time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
H = Path(r"C:\Github\ai-brain-engine-v6\hooks")
SESSAO = "prova-portao-passo3"
ARQ = r"C:\Github\cqrs-reference-architecture\src\CqrsReference.Application\Abstractions\IRequest.cs"
REPO = r"C:\Github\cqrs-reference-architecture"

sys.path.insert(0, str(H))
import estado  # noqa


def rodar(script: str, payload: dict) -> tuple[int, str]:
    p = subprocess.run(
        [sys.executable, str(H / script)],
        input=json.dumps(payload), capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=90,
    )
    return p.returncode, (p.stdout or "").strip()


def stop() -> str:
    _, saida = rodar("stop_gate.py", {
        "session_id": SESSAO, "hook_event_name": "Stop",
        "last_assistant_message": "Pronto, ajustado e testado.", "cwd": REPO,
    })
    if not saida:
        return "LIBEROU"
    d = json.loads(saida)["hookSpecificOutput"]
    if d.get("permissionDecision") == "deny":
        return "NEGOU :: " + d["permissionDecisionReason"]
    return "LIBEROU (com aviso) :: " + (d.get("systemMessage") or "")


def limpar():
    estado.gravar(SESSAO, {})


def editou():
    rodar("post_edit.py", {
        "session_id": SESSAO, "tool_name": "Edit",
        "tool_input": {"file_path": ARQ}, "cwd": REPO,
    })


def rodou_teste(saida: str, cmd: str = "dotnet test test/CqrsReference.Application.Tests"):
    rodar("post_bash.py", {
        "session_id": SESSAO, "tool_name": "Bash",
        "tool_input": {"command": cmd}, "tool_use_result": saida, "cwd": REPO,
    })


def falou(texto: str):
    rodar("user_prompt.py", {"session_id": SESSAO, "prompt": texto})


def mostra(titulo: str, resultado: str, espera: str):
    ok = resultado.startswith(espera)
    print(f"\n{'✔' if ok else '✘'} {titulo}\n   esperado: {espera} | obtido: {resultado.split(' :: ')[0]}")
    if " :: " in resultado:
        for l in resultado.split(" :: ", 1)[1].splitlines():
            if l.strip():
                print("     |", l[:120])
    return ok


tudo = []

print("=" * 70)
print("1) sem edição nenhuma na sessão")
limpar()
tudo.append(mostra("nada editado -> não tem o que provar", stop(), "LIBEROU"))

print("\n" + "=" * 70)
print("2) editou .cs e não rodou teste  (o caso do dia a dia)")
limpar(); editou()
tudo.append(mostra("editou sem testar -> nega e aponta o projeto certo", stop(), "NEGOU"))

print("\n" + "=" * 70)
print("3) rodou o teste e passou de verdade")
rodou_teste("Passed!  - Failed: 0, Passed: 319, Skipped: 0, Total: 319")
tudo.append(mostra("verde provado depois da edição -> libera", stop(), "LIBEROU"))

print("\n" + "=" * 70)
print("4) editou de novo e o teste falhou")
limpar(); editou(); time.sleep(0.01)
rodou_teste("Failed!  - Failed: 1, Passed: 318, Skipped: 0, Total: 319")
tudo.append(mostra("teste vermelho -> nega", stop(), "NEGOU"))

print("\n" + "=" * 70)
print("5) saída que não dá para concluir nada (indeterminado)")
limpar(); editou(); time.sleep(0.01)
rodou_teste("Determining projects to restore...\nRestored in 2,3s")
tudo.append(mostra("indeterminado NÃO é verde -> nega", stop(), "NEGOU"))

print("\n" + "=" * 70)
print("6) o Rafael diz a frase de escape")
limpar(); editou(); time.sleep(0.01)
falou("deixa assim por enquanto, termina assim mesmo que eu vejo depois")
tudo.append(mostra("escape explícito -> libera a vez", stop(), "LIBEROU"))

print("\n" + "=" * 70)
print("7) portão não pode travar a sessão: 4 tentativas seguidas")
limpar(); editou()
for i in (1, 2, 3):
    r = stop()
    print(f"   tentativa {i}: {r.split(' :: ')[0]}")
    tudo.append(r.startswith("NEGOU"))
r4 = stop()
tudo.append(mostra("na 4a vez desiste e AVISA que não está verificado", r4, "LIBEROU"))

limpar()
print("\n" + "=" * 70)
print(f"RESULTADO: {sum(tudo)}/{len(tudo)} cenários como esperado")
sys.exit(0 if all(tudo) else 1)
