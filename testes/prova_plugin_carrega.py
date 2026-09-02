"""Prova que o plugin CARREGA. Rodar: python testes/prova_plugin_carrega.py

Este é o teste que faltava e o mais barato de todos. No Passo 6 o plugin passou a
**falhar ao carregar** — `hooks.PreToolUse.0.hooks.0: expected string, received
array` — e nada disso aparece quando se testa cada script na mão: os quatro
outros testes continuavam verdes enquanto, numa sessão real, hook nenhum
dispararia.

A forma de lista (exec) para o comando é documentada como mais segura para
caminho com espaço, e funciona em vários eventos — mas o `PreToolUse` a recusa, e
um `PreToolUse` inválido derruba o plugin inteiro.

Script que funciona não é plugin que carrega.
"""
import json, re, subprocess, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
RAIZ = Path(__file__).resolve().parent.parent
NOME = "ai-brain-engine-v6"
tudo = []


def mostra(titulo: str, ok: bool, detalhe: str = "") -> bool:
    print(f"{'✔' if ok else '✘'} {titulo}" + (f"  — {detalhe}" if detalhe else ""))
    tudo.append(ok)
    return ok


# 1) o hooks.json é JSON válido
bruto = (RAIZ / "hooks" / "hooks.json").read_text(encoding="utf-8")
try:
    cfg = json.loads(bruto)
    mostra("hooks.json é JSON válido", True)
except Exception as e:
    mostra("hooks.json é JSON válido", False, str(e))
    cfg = {"hooks": {}}

# 2) todo comando é STRING (a regressão do Passo 6)
listas = []
scripts_faltando = []
for evento, entradas in (cfg.get("hooks") or {}).items():
    for entrada in entradas:
        for h in entrada.get("hooks", []):
            cmd = h.get("command")
            if not isinstance(cmd, str):
                listas.append(f"{evento}: {type(cmd).__name__}")
                continue
            m = re.search(r"hooks/([a-z_]+\.py)", cmd)
            if m and not (RAIZ / "hooks" / m.group(1)).is_file():
                scripts_faltando.append(f"{evento}: {m.group(1)}")
mostra("todo comando de hook é string, não lista", not listas, ", ".join(listas) or "todos string")
mostra("todo script referenciado existe", not scripts_faltando, ", ".join(scripts_faltando) or "todos presentes")

# 3) todo hook tem timeout declarado (silêncio por timeout é o pior tipo)
sem_timeout = [
    f"{ev}"
    for ev, entradas in (cfg.get("hooks") or {}).items()
    for entrada in entradas
    for h in entrada.get("hooks", [])
    if "timeout" not in h
]
mostra("todo hook declara timeout", not sem_timeout, ", ".join(sem_timeout) or "todos declaram")

# 4) as skills têm frontmatter com name e description
skills = list((RAIZ / "skills").glob("*/SKILL.md"))
ruins = []
for s in skills:
    t = s.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---", t, re.S)
    if not m or "name:" not in m.group(1) or "description:" not in m.group(1):
        ruins.append(s.parent.name)
mostra(f"as {len(skills)} skills têm name e description", not ruins, ", ".join(ruins) or "todas ok")

# 5) e o que importa: a ferramenta consegue carregar o plugin
try:
    p = subprocess.run(["claude", "plugin", "list"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=120)
    saida = (p.stdout or "") + (p.stderr or "")
    bloco = ""
    for pedaco in saida.split("❯"):
        if NOME in pedaco:
            bloco = pedaco
            break
    if not bloco:
        mostra("o plugin aparece instalado", False, "não encontrado em `claude plugin list`")
    else:
        falhou = "failed to load" in bloco.lower()
        erro = next((l.strip() for l in bloco.splitlines() if "Error:" in l), "")
        mostra("o plugin CARREGA sem erro", not falhou, erro[:160] if falhou else "enabled")
except FileNotFoundError:
    print("… `claude` não está no PATH; o cenário de carga foi pulado")
except Exception as e:
    mostra("o plugin CARREGA sem erro", False, str(e)[:120])

print("=" * 70)
print(f"RESULTADO: {sum(tudo)}/{len(tudo)} cenários como esperado")
sys.exit(0 if all(tudo) else 1)
