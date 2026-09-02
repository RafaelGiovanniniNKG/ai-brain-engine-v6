"""Prova da documentação automática (Passo 4): seis cenários.

Rodar: python testes/prova_diario.py   (sai 0 se todos passarem)

Escreve num vault DESCARTÁVEL (`V6_VAULT` aponta para uma pasta temporária), não
no cofre de verdade. O cenário 5 força a falha do modelo de resumo apontando
`V6_MODELO_RESUMO` para um modelo inexistente — o caminho de erro tem de escrever
o registro mecânico e marcar a nota como não destilada.
"""
import json, os, re, shutil, subprocess, sys, tempfile, time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "hooks"))
import estado  # noqa
import vault  # noqa

SESSAO = "prova-diario-passo4"
REPO = str(RAIZ)  # o próprio motor serve de alvo: é um repo git de verdade
COFRE = Path(tempfile.mkdtemp(prefix="v6-vault-"))
os.environ["V6_VAULT"] = str(COFRE)

tudo = []


def hook(script: str, payload: dict, env: dict | None = None) -> str:
    amb = {**os.environ, **(env or {})}
    p = subprocess.run([sys.executable, str(RAIZ / "hooks" / script)],
                       input=json.dumps(payload), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=60, env=amb)
    return (p.stdout or "").strip()


def destilar(motivo="stop", env: dict | None = None) -> int:
    amb = {**os.environ, **(env or {})}
    p = subprocess.run([sys.executable, str(RAIZ / "captura" / "destilar.py"),
                        "--sessao", SESSAO, "--motivo", motivo],
                       capture_output=True, text=True, timeout=180, env=amb)
    return p.returncode


def nota() -> Path | None:
    achados = sorted(COFRE.rglob("_diario/*.md"))
    return achados[0] if achados else None


def mostra(titulo: str, ok: bool, detalhe: str = "") -> bool:
    print(f"\n{'✔' if ok else '✘'} {titulo}")
    for l in (detalhe or "").splitlines():
        if l.strip():
            print("     |", l[:120])
    tudo.append(ok)
    return ok


print("=" * 70)
print("vault de teste:", COFRE)
estado.gravar(SESSAO, {})

print("\n1) sessão vazia não gera nota")
destilar()
mostra("nada aconteceu -> nada escrito", nota() is None)

print("\n2) sessão com pedido, edição, teste verde e commit")
hook("user_prompt.py", {"session_id": SESSAO, "prompt": "faz o passo 4 do plano do motor", "cwd": REPO})
hook("post_edit.py", {"session_id": SESSAO, "tool_name": "Edit",
                      "tool_input": {"file_path": str(RAIZ / "hooks" / "estado.py")}, "cwd": REPO})
hook("post_bash.py", {"session_id": SESSAO, "tool_name": "Bash",
                      "tool_input": {"command": "dotnet test test/Alvo.Tests"},
                      "tool_use_result": "Passed!  - Failed: 0, Passed: 42, Total: 42", "cwd": REPO})
hook("post_bash.py", {"session_id": SESSAO, "tool_name": "Bash",
                      "tool_input": {"command": "git commit -m 'feat: teste'"},
                      "tool_use_result": "[master a1b2c3d] feat: teste\n 2 files changed", "cwd": REPO})
destilar()
n = nota()
texto = vault.ler(n) if n else ""
ok = bool(n) and "a1b2c3d" in texto and "Passed: 42" in texto and "passo 4" in texto.lower()
mostra("escreveu a nota do dia com pedido, commit e a EVIDENCIA do teste", ok,
       f"arquivo: {n.name if n else '(nenhum)'}\n" + "\n".join(texto.splitlines()[:14]))

print("\n3) frontmatter é YAML válido e plano")
meta, corpo = vault.partir(texto)
ok = isinstance(meta, dict) and meta.get("tipo") == "diario-automatico" and meta.get("repo") == Path(REPO).name \
     and not any(isinstance(v, (dict, list)) for v in meta.values())
mostra("frontmatter válido, plano, com repo e tipo", ok, json.dumps(meta, ensure_ascii=False, default=str))

print("\n4) rodar de novo NÃO duplica (idempotência)")
antes = texto
destilar(); destilar()
depois = vault.ler(nota())
blocos = len(re.findall(r"^## \d\d:\d\d — ", depois, re.M))
mostra("dois disparos extras -> um único bloco, conteúdo intacto",
       blocos == 1 and depois == antes, f"blocos no arquivo: {blocos}")

print("\n5) modelo de resumo indisponível -> registro mecânico, marcado")
hook("user_prompt.py", {"session_id": SESSAO, "prompt": "agora conserta o portao", "cwd": REPO})
destilar(env={"V6_MODELO_RESUMO": "modelo-que-nao-existe-999", "V6_TETO_RESUMO": "25"})
depois = vault.ler(nota())
meta2, _ = vault.partir(depois)
ok = ("não destilado" in depois) and meta2.get("destilado") is False and "conserta o portao" in depois
mostra("caiu no plano B e DECLAROU que não destilou", ok,
       "\n".join([l for l in depois.splitlines() if "destilado" in l or "plano" in l.lower()][:4]))

print("\n6) upsert por cabeçalho: novo conteúdo, ainda um bloco")
blocos = len(re.findall(r"^## \d\d:\d\d — ", depois, re.M))
mostra("atualizou o bloco em vez de anexar outro", blocos == 1, f"blocos: {blocos}")

print("\n7) nome de arquivo e slug seguros no Windows")
casos = {"Onda 8: migração — Grupo B": "onda-8-migracao-grupo-b", "CON": "nota-con",
         'a/b\\c:d*e?f"g<h>i|j': "a-b-c-d-e-f-g-h-i-j", "": "nota"}
ruins = {k: (vault.slug(k), esperado) for k, esperado in casos.items() if vault.slug(k) != esperado}
mostra("dois-pontos, barra, curinga, nome reservado e vazio tratados", not ruins,
       json.dumps(ruins, ensure_ascii=False) if ruins else "todos os casos como esperado")

print("\n8) plano B do YAML: máquina nova, sem pyyaml instalado")
guardado = vault.yaml
try:
    vault.yaml = None   # simula a máquina que não tem pyyaml
    fm = vault.frontmatter({"titulo": "Onda 8: migração — Grupo B", "destilado": True,
                            "sessoes": 3, "obs": "valor com # e: dois-pontos"})
    meta, _ = vault.partir(fm + "\ncorpo")
    ok = (meta.get("titulo") == "Onda 8: migração — Grupo B" and meta.get("destilado") is True
          and str(meta.get("sessoes")) == "3" and "dois-pontos" in str(meta.get("obs")))
    mostra("frontmatter sem pyyaml sobrevive a `:`, acento e `#`", ok,
           fm.replace(chr(10), " | "))
finally:
    vault.yaml = guardado

print("\n9) o diagnóstico da máquina roda e responde")
import subprocess
d = subprocess.run([sys.executable, str(RAIZ / "hooks" / "doutor.py"), "--json"],
                   capture_output=True, text=True, encoding="utf-8", timeout=180)
try:
    itens = json.loads(d.stdout or "[]")
except Exception:
    itens = []
mostra("doutor.py lista os itens da máquina", len(itens) >= 8,
       f"{len(itens)} itens, {sum(1 for i in itens if not i['ok'])} faltando")

estado.gravar(SESSAO, {})
shutil.rmtree(COFRE, ignore_errors=True)
print("\n" + "=" * 70)
print(f"RESULTADO: {sum(tudo)}/{len(tudo)} cenários como esperado")
sys.exit(0 if all(tudo) else 1)
