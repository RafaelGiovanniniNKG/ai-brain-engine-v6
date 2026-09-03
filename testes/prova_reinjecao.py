"""Prova da reinjeção das regras: sete cenários, com o veredito de cada um.

Rodar: python testes/prova_reinjecao.py   (sai 0 se todos passarem)

Existe por um furo de desenho, não de código: as regras vivas chegam ao modelo
uma vez, no início da sessão. Quando a conversa fica longa o programa a RESUME e
joga o começo fora — as regras incluídas. Elas desaparecem em silêncio no meio
do trabalho, e numa sessão longa, que é onde o erro caro acontece, o motor fica
mudo justamente quando mais deveria falar.

Não dá para consertar no lugar óbvio: `SessionStart` não dispara depois de um
resumo, e `PostCompact`, que dispara, não pode injetar contexto. Daí os dois
passos: `PostCompact` anota, `UserPromptSubmit` devolve no próximo pedido.

Os cenários que mais importam são os NEGATIVOS: não injetar quando não houve
resumo, e não repetir a cada mensagem depois de um.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
RAIZ = Path(__file__).resolve().parent.parent
H = RAIZ / "hooks"
SESSAO = "prova-reinjecao"
CWD = str(RAIZ)

sys.path.insert(0, str(H))
import estado  # noqa: E402


def rodar(modo: str, payload: dict) -> str:
    p = subprocess.run(
        [sys.executable, str(H / "reinjetar.py"), modo], input=json.dumps(payload),
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=90,
    )
    return (p.stdout or "").strip()


def contexto(saida: str) -> str:
    if not saida:
        return ""
    try:
        return json.loads(saida)["hookSpecificOutput"].get("additionalContext") or ""
    except Exception:
        return ""


def pedido(texto: str = "segue") -> str:
    return rodar("--auto", {"session_id": SESSAO, "cwd": CWD,
                            "hook_event_name": "UserPromptSubmit", "prompt": texto})


def houve_resumo(motivo: str = "auto") -> None:
    rodar("--marcar", {"session_id": SESSAO, "cwd": CWD,
                       "hook_event_name": "PostCompact", "compaction_reason": motivo})


def mostra(titulo: str, obtido: str, espera: str, detalhe: str = "") -> bool:
    ok = obtido == espera
    print(f"\n{'✔' if ok else '✘'} {titulo}\n   esperado: {espera} | obtido: {obtido}")
    if detalhe:
        print("     |", detalhe[:150])
    return ok


tudo: list[bool] = []
try:
    estado.gravar(SESSAO, {"inicio": time.time(), "cwd": CWD})

    print("=" * 70)
    print("1) pedido do Rafael numa sessão que NÃO foi resumida")
    tudo.append(mostra("não injeta nada (senão repetiria a cada mensagem)",
                       "CALADO" if not pedido() else "INJETOU", "CALADO"))

    print("\n" + "=" * 70)
    print("2) houve resumo: o próximo pedido devolve as regras")
    houve_resumo()
    marca = (estado.ler(SESSAO).get("contexto_perdido") or {}).get("motivo")
    tudo.append(mostra("o resumo fica anotado", str(marca), "auto"))
    ctx = contexto(pedido())
    tudo.append(mostra("as regras voltam", "INJETOU" if ctx else "CALADO", "INJETOU",
                       f"{len(ctx)} chars"))
    tudo.append(mostra("e o texto diz POR QUE está voltando",
                       "EXPLICA" if "conversa foi resumida" in ctx else "sem motivo", "EXPLICA"))
    tudo.append(mostra("sem repetir a nota do projeto (só o que desaparece calado)",
                       "SÓ REGRAS" if ("Regras aprendidas" in ctx and "Nota do projeto" not in ctx)
                       else "bloco errado", "SÓ REGRAS"))

    print("\n" + "=" * 70)
    print("3) o pedido SEGUINTE, sem novo resumo")
    tudo.append(mostra("não repete: uma vez por resumo, não por mensagem",
                       "CALADO" if not pedido() else "INJETOU", "CALADO"))

    print("\n" + "=" * 70)
    print("4) o modelo da sessão trocou")
    ctx = contexto(rodar("--injetar", {
        "session_id": SESSAO, "cwd": CWD, "hook_event_name": "PostModelSwitch",
        "from_model": "claude-opus-4", "to_model": "claude-opus-5",
    }))
    tudo.append(mostra("injeta direto, sem depender de marca de resumo",
                       "INJETOU" if "Regras aprendidas" in ctx else "CALADO", "INJETOU"))
    tudo.append(mostra("e diz que o motivo foi a troca de modelo",
                       "EXPLICA" if "modelo desta sessão mudou" in ctx else "sem motivo",
                       "EXPLICA"))
finally:
    estado.gravar(SESSAO, {})

print("\n" + "=" * 70)
print(f"RESULTADO: {sum(tudo)}/{len(tudo)} cenários como esperado")
sys.exit(0 if all(tudo) else 1)
