#!/usr/bin/env python
"""Afirma a matriz de dependência entre projetos, lendo os `.csproj`.

É o sensor de camada BARATO: roda em milissegundos, a cada edição, sem compilar
nada e sem escrever um único arquivo no repositório alvo. Pega a violação mais
gritante — `Domain.csproj` referenciando `Infrastructure.csproj`.

O que ele NÃO pega, e por isso não substitui o sensor de fim de tarefa: violação
dentro de um mesmo assembly (`using Infrastructure.X` num projeto que já pode
referenciar Infrastructure) e qualquer coisa resolvida em tempo de execução.

Uso:
    python assert_refs.py --repo C:\\Github\\alvo [--regras <arquivo.json>]

Sem `--regras`, procura `<pasta deste script>/<nome-do-repo>.json`. Sem arquivo
de regras, sai 0 em silêncio — repo sem regra declarada não é repo reprovado.

Sai 2 quando há violação (contrato de hook do Claude Code), 0 quando passa.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RX_REF = re.compile(r'<ProjectReference\s+[^>]*Include="([^"]+)"', re.I)


def _nome(caminho: str) -> str:
    return Path(caminho.replace("\\", "/")).name.removesuffix(".csproj")


def grafo(repo: Path) -> dict[str, list[str]]:
    g: dict[str, list[str]] = {}
    for csproj in repo.rglob("*.csproj"):
        partes = {p.lower() for p in csproj.parts}
        if "bin" in partes or "obj" in partes or "node_modules" in partes:
            continue
        try:
            texto = csproj.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        g[_nome(csproj.name)] = sorted({_nome(r) for r in RX_REF.findall(texto)})
    return g


def violacoes(g: dict[str, list[str]], regras: list[dict]) -> list[str]:
    achados: list[str] = []
    for regra in regras:
        de = regra.get("de", "")
        proibidos = regra.get("proibido", [])
        excecoes = regra.get("excecao", [])
        for projeto, refs in g.items():
            if not fnmatch.fnmatch(projeto, de):
                continue
            for ref in refs:
                if any(fnmatch.fnmatch(ref, e) for e in excecoes):
                    continue
                if any(fnmatch.fnmatch(ref, p) for p in proibidos):
                    achados.append(
                        f"{projeto} -> {ref}  [{regra.get('porque', 'referência proibida')}]"
                    )
    return achados


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--regras")
    args = ap.parse_args()

    repo = Path(args.repo)
    if not repo.is_dir():
        return 0

    arquivo = Path(args.regras) if args.regras else AQUI / f"{repo.name}.json"
    if not arquivo.is_file():
        return 0  # repo sem regra declarada não é repo reprovado

    try:
        conf = json.loads(arquivo.read_text(encoding="utf-8"))
    except Exception as erro:
        print(f"regra de camada ilegível ({arquivo.name}): {erro}", file=sys.stderr)
        return 0  # regra quebrada não pode virar bloqueio de tudo

    achados = violacoes(grafo(repo), conf.get("regras", []))
    if not achados:
        return 0

    sys.stderr.reconfigure(encoding="utf-8")
    print(
        "CAMADA VIOLADA — a referência entre projetos contraria a arquitetura declarada:",
        file=sys.stderr,
    )
    for a in achados:
        print(f"  - {a}", file=sys.stderr)
    print(
        f"\nRegra declarada em: {arquivo}\n"
        "Conserte a referência. Se a arquitetura MUDOU de propósito, "
        "mude a regra no mesmo commit e diga por quê.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as erro:  # sensor que quebra não pode parar o trabalho
        print(f"assert_refs falhou: {erro}", file=sys.stderr)
        sys.exit(0)
