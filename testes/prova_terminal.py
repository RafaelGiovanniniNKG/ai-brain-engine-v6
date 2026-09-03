"""Prova do sensor de edição pelo TERMINAL: nove cenários, com o veredito de cada um.

Rodar: python testes/prova_terminal.py   (sai 0 se todos passarem)

Existe por um furo medido em 03/09/2026: o aviso de edição só chega quando o
arquivo é mexido pela ferramenta de edição. Mexer pelo terminal — `sed -i`, `>`,
heredoc, um script que escreve — não gerava aviso nenhum, e o encerramento
liberava trabalho não provado. Criei e alterei um `.ts` por `printf >` e `sed -i`
e o registro da sessão não mudou uma vírgula. É o mesmo tipo de furo que a
delegação para sub-agente abria: um caminho por fora da prova, e pior, porque o
modo automático de trabalho manda editar assim.

O sensor não adivinha pelo texto do comando (script que escreve arquivo passaria
batido): pergunta ao git o que está sujo e usa a hora de modificação para
separar o que mudou nesta sessão da sujeira que já estava lá. Os dois cenários
que mais importam são os NEGATIVOS — sujeira anterior e troca de branch não
podem virar armadilha.

Monta e apaga um repositório git descartável no diretório temporário. Não toca
em repo nenhum de verdade.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
H = Path(__file__).resolve().parent.parent / "hooks"
SESSAO = "prova-terminal"

sys.path.insert(0, str(H))
import estado  # noqa: E402


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=30)


def montar() -> Path:
    """Repo descartável com um arquivo commitado e um já sujo ANTES da sessão."""
    repo = Path(tempfile.mkdtemp(prefix="v6-prova-terminal-"))
    _git(repo, "init", "-q", ".")
    _git(repo, "config", "user.email", "prova@local")
    _git(repo, "config", "user.name", "prova")
    (repo / "antigo.ts").write_text("export const antigo = 1;\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base")
    (repo / "sujo-antes.ts").write_text("export const jaSujo = 1;\n", encoding="utf-8")
    # A hora vai marcada NA MÃO, um minuto no passado. Escrever o arquivo e
    # marcar o início da sessão logo depois deixava esta prova INTERMITENTE: a
    # granularidade do carimbo de hora do sistema de arquivos fazia os dois
    # instantes empatarem, e a sujeira anterior contava como trabalho da sessão
    # (9/11 numa execução, 11/11 na seguinte). Prova que às vezes reprova ensina
    # a ignorar vermelho — então aqui o relógio é controlado, não aguardado.
    envelhecer(repo / "sujo-antes.ts", 60)
    return repo


def envelhecer(arquivo: Path, segundos: float) -> None:
    """Empurra a hora de modificação para o passado, sem dormir."""
    quando = time.time() - segundos
    os.utime(arquivo, (quando, quando))


def rejuvenescer(arquivo: Path, segundos: float = 5) -> None:
    """Puxa a hora de modificação para o futuro próximo, sem dormir.

    Serve para provar que uma SEGUNDA edição do mesmo arquivo é notada: sem
    isso a prova dependia de `sleep(1.1)` para o carimbo mudar."""
    quando = time.time() + segundos
    os.utime(arquivo, (quando, quando))


def rodar(script: str, payload: dict) -> str:
    p = subprocess.run(
        [sys.executable, str(H / script)], input=json.dumps(payload),
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=90,
    )
    return (p.stdout or "").strip()


def bash(repo: Path, cmd: str, saida: str = "ok") -> str:
    """Um comando de terminal que TERMINOU BEM, no formato real da entrada."""
    return rodar("post_bash.py", {
        "session_id": SESSAO, "tool_name": "Bash", "hook_event_name": "PostToolUse",
        "tool_input": {"command": cmd},
        "tool_use_result": [{"type": "text", "text": saida}], "cwd": str(repo),
    })


def editou_por_ferramenta(repo: Path, arquivo: Path) -> None:
    rodar("post_edit.py", {
        "session_id": SESSAO, "tool_name": "Write",
        "tool_input": {"file_path": str(arquivo)}, "cwd": str(repo),
    })


def stop(repo: Path) -> str:
    s = rodar("stop_gate.py", {
        "session_id": SESSAO, "hook_event_name": "Stop",
        "last_assistant_message": "Pronto, ajustado.", "cwd": str(repo),
    })
    if not s:
        return "LIBEROU"
    o = json.loads(s)["hookSpecificOutput"]
    return "NEGOU" if o.get("permissionDecision") == "deny" else "LIBEROU (com aviso)"


def mostra(titulo: str, obtido: str, espera: str, detalhe: str = "") -> bool:
    ok = obtido == espera
    print(f"\n{'✔' if ok else '✘'} {titulo}\n   esperado: {espera} | obtido: {obtido}")
    if detalhe:
        print("     |", detalhe[:150])
    return ok


tudo: list[bool] = []
repo = montar()
try:
    # A sessão começa AGORA. `sujo-antes.ts` foi escrito antes desta marca.
    estado.gravar(SESSAO, {"inicio": time.time(), "cwd": str(repo)})

    print("=" * 70)
    print("1) sujeira que já estava na árvore quando a sessão começou")
    r = bash(repo, "git status")
    tudo.append(mostra("não conta como trabalho desta sessão",
                       "NADA" if not r else "REGISTROU", "NADA"))
    tudo.append(mostra("e o encerramento não é barrado por ela", stop(repo), "LIBEROU"))

    print("\n" + "=" * 70)
    print("2) escrita por redirecionamento do shell (`>`)")
    (repo / "novo.ts").write_text("export const n = 1;\n", encoding="utf-8")
    r = bash(repo, "printf 'export const n = 1;\\n' > novo.ts")
    tudo.append(mostra("o sensor avisa o modelo no mesmo turno",
                       "AVISOU" if "TERMINAL" in r else "calado", "AVISOU"))
    tudo.append(mostra("e o encerramento pede prova", stop(repo), "NEGOU"))

    print("\n" + "=" * 70)
    print("3) teste verde depois da edição pelo terminal")
    bash(repo, "npx vitest run", "Tests:  3 passed")
    tudo.append(mostra("verde dá baixa -> libera", stop(repo), "LIBEROU"))

    print("\n" + "=" * 70)
    print("4) o MESMO arquivo editado DE NOVO, depois do verde")
    (repo / "novo.ts").write_text("export const n = 2;\n", encoding="utf-8")
    rejuvenescer(repo / "novo.ts")
    r = bash(repo, "sed -i 's/n = 1/n = 2/' novo.ts")
    tudo.append(mostra("segunda edição do mesmo arquivo não passa batida",
                       "AVISOU" if "TERMINAL" in r else "calado", "AVISOU"))
    tudo.append(mostra("e o encerramento barra outra vez", stop(repo), "NEGOU"))

    print("\n" + "=" * 70)
    print("5) trocar de branch muda arquivo de código sem ninguém editar")
    bash(repo, "npx vitest run", "Tests:  3 passed")
    (repo / "antigo.ts").write_text("export const antigo = 99;\n", encoding="utf-8")
    r = bash(repo, "git checkout outra-branch")
    tudo.append(mostra("mover a árvore NÃO é editar (senão o portão vira armadilha)",
                       "NADA" if not r else "REGISTROU", "NADA"))

    print("\n" + "=" * 70)
    print("6) arquivo que não é código, mexido pelo terminal")
    (repo / "leia.md").write_text("nada a provar aqui\n", encoding="utf-8")
    r = bash(repo, "printf 'nada\\n' > leia.md")
    tudo.append(mostra("markdown não pede teste",
                       "NADA" if not r else "REGISTROU", "NADA"))

    print("\n" + "=" * 70)
    print("7) edição pela FERRAMENTA não é anunciada como se fosse do terminal")
    (repo / "porFerramenta.ts").write_text("export const f = 1;\n", encoding="utf-8")
    rejuvenescer(repo / "porFerramenta.ts")
    editou_por_ferramenta(repo, repo / "porFerramenta.ts")
    r = bash(repo, "git status")
    tudo.append(mostra("o sensor do terminal fica calado sobre ela",
                       "NADA" if "TERMINAL" not in r else "ANUNCIOU", "NADA"))
    tudo.append(mostra("mas a edição continua valendo para o encerramento",
                       stop(repo), "NEGOU"))
finally:
    estado.gravar(SESSAO, {})
    shutil.rmtree(repo, ignore_errors=True)

print("\n" + "=" * 70)
print(f"RESULTADO: {sum(tudo)}/{len(tudo)} cenários como esperado")
sys.exit(0 if all(tudo) else 1)
