#!/usr/bin/env python
"""Diz o que o motor precisa e o que está faltando. Nada mais.

Existe porque a instalação à mão tem oito passos, e passo esquecido em motor de
qualidade some em silêncio: sem `slopwatch` o sensor de .NET simplesmente não
acha nada, e "não achou nada" se lê como "está tudo bem".

Uso:
    python hooks/doutor.py            # tabela legível
    python hooks/doutor.py --json     # para o instalador consumir
    python hooks/doutor.py --curto    # uma linha por item faltando (para injetar)

Sai 0 quando o essencial está de pé, 1 quando falta essencial.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def _tem_comando(nome: str) -> bool:
    if shutil.which(nome):
        return True
    # ferramenta global do .NET não entra no PATH desta sessão do shell às vezes
    tools = Path.home() / ".dotnet" / "tools"
    return any((tools / f"{nome}{ext}").is_file() for ext in ("", ".exe", ".cmd"))


def _config_claude() -> dict:
    try:
        return json.loads((Path.home() / ".claude" / "settings.json").read_text(encoding="utf-8"))
    except Exception:
        return {}


def _plugin_carrega() -> tuple[bool, str]:
    if not shutil.which("claude"):
        return False, "o comando `claude` não está no PATH"
    try:
        p = subprocess.run(["claude", "plugin", "list"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=90)
    except Exception as e:
        return False, str(e)[:80]
    saida = (p.stdout or "") + (p.stderr or "")
    bloco = next((pedaco for pedaco in saida.split("❯") if "ai-brain-engine-v6" in pedaco), "")
    if not bloco:
        return False, "não instalado (`claude plugin install`)"
    if "failed to load" in bloco.lower():
        erro = next((l.strip() for l in bloco.splitlines() if "Error:" in l), "erro não identificado")
        return False, erro[:120]
    if "disabled" in bloco.lower():
        return False, "instalado, mas desligado"
    return True, "enabled"


def diagnostico() -> list[dict]:
    cfg = _config_claude()
    vault = None
    try:
        vault = json.loads((RAIZ / "mapa.json").read_text(encoding="utf-8")).get("vault")
    except Exception:
        pass
    local = RAIZ / "local.json"
    if local.is_file():
        try:
            vault = json.loads(local.read_text(encoding="utf-8")).get("vault") or vault
        except Exception:
            pass
    if os.environ.get("V6_VAULT"):
        vault = os.environ["V6_VAULT"]

    itens: list[dict] = []

    def add(nome, ok, essencial, conserto, detalhe=""):
        itens.append({"item": nome, "ok": bool(ok), "essencial": essencial,
                      "conserto": conserto, "detalhe": detalhe})

    ok_plugin, det = _plugin_carrega()
    add("plugin carregado", ok_plugin, True, "powershell -File instalar.ps1", det)
    add("python 3.10+", sys.version_info >= (3, 10), True, "instale o Python 3.12",
        f"{sys.version_info.major}.{sys.version_info.minor}")
    add("git", _tem_comando("git"), True, "instale o Git")
    add("dotnet", _tem_comando("dotnet"), False, "instale o .NET SDK")
    add("node", _tem_comando("node"), False, "instale o Node")

    add("csharp-ls (erro do compilador no contexto)", _tem_comando("csharp-ls"), False,
        "dotnet tool install --global csharp-ls")
    add("typescript-language-server", _tem_comando("typescript-language-server"), False,
        "npm i -g typescript-language-server typescript")
    add("slopwatch (sensor de .NET)", _tem_comando("slopwatch"), False,
        "dotnet tool install --global Slopwatch.Cmd")
    add("eslint do motor (sensor de TS)",
        (RAIZ / "sensores" / "eslint" / "node_modules" / "eslint" / "bin" / "eslint.js").is_file(),
        False, "cd sensores/eslint && npm install")

    add("vault encontrado", bool(vault) and Path(str(vault)).is_dir(), True,
        "aponte o caminho em local.json (chave \"vault\")", str(vault or "não definido"))
    add("memória automática no vault", bool(cfg.get("autoMemoryDirectory")), False,
        "powershell -File instalar.ps1", str(cfg.get("autoMemoryDirectory") or "não definida"))
    add("regras vivas presentes", len(list((RAIZ / "regras").glob("*.md"))) > 5, True,
        "o repo do motor está incompleto", f"{len(list((RAIZ / 'regras').glob('*.md')))} arquivos")
    add("instrução compartilhada (CLAUDE.md acima dos repos)",
        (Path(str(vault)).parent / "CLAUDE.md").is_file() if vault else False, False,
        "powershell -File instalar.ps1")
    add("pyyaml (frontmatter do diário)", _modulo("yaml"), False,
        "python -m pip install pyyaml", "sem ele usa o serializador simples embutido")
    return itens


def _modulo(nome: str) -> bool:
    try:
        __import__(nome)
        return True
    except Exception:
        return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--curto", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    itens = diagnostico()
    faltando_essencial = [i for i in itens if not i["ok"] and i["essencial"]]
    faltando_resto = [i for i in itens if not i["ok"] and not i["essencial"]]

    if args.json:
        print(json.dumps(itens, ensure_ascii=False, indent=1))
    elif args.curto:
        for i in faltando_essencial + faltando_resto:
            print(f"{'FALTA (essencial)' if i['essencial'] else 'falta'}: {i['item']} → {i['conserto']}")
    else:
        largura = max(len(i["item"]) for i in itens) + 2
        print("=" * (largura + 40))
        for i in itens:
            marca = "✔" if i["ok"] else ("✘" if i["essencial"] else "·")
            print(f" {marca} {i['item']:<{largura}} {i['detalhe'][:38]}")
            if not i["ok"]:
                print(f"   {'':<{largura}} conserto: {i['conserto']}")
        print("=" * (largura + 40))
        if faltando_essencial:
            print(f"FALTA ESSENCIAL: {len(faltando_essencial)} item(ns) — o motor não funciona assim.")
        elif faltando_resto:
            print(f"De pé, com {len(faltando_resto)} sensor(es) desligado(s) — o resto funciona.")
        else:
            print("Tudo de pé.")
    return 1 if faltando_essencial else 0


if __name__ == "__main__":
    raise SystemExit(main())
