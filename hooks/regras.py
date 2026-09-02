#!/usr/bin/env python
"""As regras vivas: leitura, confiança com decaimento, e o bloco para prompt.

Fonte única. Antes isto vivia dentro do `session_start.py`, e o revisor precisava
das mesmas regras — duas cópias divergem, e regra que divergiu é pior que regra
que não existe.

**Por que existe o modo CLI:** os revisores oficiais da Anthropic leem as regras
do arquivo de instruções do projeto. Nos repositórios da empresa esse arquivo não
existe e não pode existir. Então o motor **injeta** as regras no prompt do
revisor, e para isso precisa cuspir o bloco:

    python hooks/regras.py --repo C:\\Github\\alvo            # manchetes
    python hooks/regras.py --repo C:\\Github\\alvo --completo  # com o corpo

Uma regra só entra se `status: active`, se o escopo cobre o projeto e se a
confiança **depois do decaimento** (0,02 por semana desde a última confirmação)
ainda passa do mínimo. Aprendizado que nunca é reinjetado é aprendizado morto —
e aprendizado que nunca decai é dogma.
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DIR_REGRAS = RAIZ / "regras"
MIN_CONFIANCA = 0.5
DECAIMENTO_POR_SEMANA = 0.02


def _desaspar(valor: str) -> str:
    """Tira aspas de escalar YAML citado — e só nesse caso.

    Remover a última aspa de uma frase que TERMINA em citação mutila a regra
    (`… e se lê como "o sistema não fez nada"`). Foi defeito real do Passo 1.
    """
    if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "\"'":
        return valor[1:-1].strip()
    return valor


def _primeiro_paragrafo(corpo: str, teto: int = 220) -> str:
    """Primeiro parágrafo de prosa, juntado e cortado em fim de frase.

    Regras antigas não têm o campo `rule:`. Pegar uma LINHA física do corpo
    entrega meia frase, porque o markdown delas é quebrado à mão.
    """
    linhas: list[str] = []
    for linha in corpo.strip().splitlines():
        nua = linha.strip()
        if not nua or nua.startswith(("#", ">", "```", "|", "---")):
            if linhas:
                break
            continue
        linhas.append(nua.lstrip("-*").strip() if nua.startswith(("- ", "* ")) else nua)
    texto = " ".join(linhas).strip()
    if len(texto) <= teto:
        return texto
    corte = max(texto.rfind(". ", 0, teto), texto.rfind("! ", 0, teto), texto.rfind("? ", 0, teto))
    return (texto[:corte + 1] if corte > 60 else texto[:teto].rsplit(" ", 1)[0] + "…").strip()


def _frontmatter(bruto: str) -> dict[str, str]:
    """Chave→valor, com CONTINUAÇÃO: várias regras têm o `rule:` em duas ou três
    linhas indentadas, e ler só a primeira entrega a manchete pela metade."""
    meta: dict[str, str] = {}
    atual = ""
    for linha in bruto.splitlines():
        if linha.startswith((" ", "\t")) and atual:
            meta[atual] = (meta[atual] + " " + linha.strip()).strip()
        elif ":" in linha:
            k, _, v = linha.partition(":")
            atual = k.strip().lower()
            meta[atual] = v.strip()
        else:
            atual = ""
    return meta


def carregar(chave_projeto: str) -> list[tuple[float, str, str, Path]]:
    """(confiança efetiva, manchete, corpo, arquivo), da maior confiança para a menor."""
    if not DIR_REGRAS.is_dir():
        return []
    hoje = date.today()
    achadas: list[tuple[float, str, str, Path]] = []
    for arq in sorted(DIR_REGRAS.glob("*.md")):
        if arq.stem.startswith("_"):
            continue
        try:
            texto = arq.read_text(encoding="utf-8")
        except OSError:
            continue
        m = re.match(r"^---\s*\n(.*?)\n---", texto, re.S)
        if not m:
            continue
        meta = _frontmatter(m.group(1))
        if meta.get("status", "active") != "active":
            continue
        escopo = meta.get("projects", "").strip().strip("[]").lower()
        if escopo not in ("all", "global", "*"):
            alvos = [p.strip().strip("\"'") for p in escopo.split(",") if p.strip()]
            if chave_projeto not in alvos:
                continue
        try:
            conf = float(meta.get("confidence", "0.5"))
        except ValueError:
            conf = 0.5
        confirmada = meta.get("last_confirmed", "")
        if confirmada:
            try:
                dias = (hoje - date.fromisoformat(confirmada[:10])).days
                conf -= max(0, dias) / 7.0 * DECAIMENTO_POR_SEMANA
            except ValueError:
                pass
        if conf < MIN_CONFIANCA:
            continue
        corpo = texto[m.end():].strip()
        manchete = _desaspar((meta.get("rule") or "").strip()) or _primeiro_paragrafo(corpo)
        achadas.append((conf, manchete or arq.stem.replace("-", " "), corpo, arq))
    achadas.sort(key=lambda x: x[0], reverse=True)
    return achadas


def manchetes(chave_projeto: str, quantas: int = 12) -> list[str]:
    return [f"- {m}" for _c, m, _b, _a in carregar(chave_projeto)[:quantas]]


def bloco_para_prompt(chave_projeto: str, quantas: int = 12, completo: bool = False) -> str:
    itens = carregar(chave_projeto)[:quantas]
    if not itens:
        return ""
    partes = [
        "## Regras da casa (nasceram de falhas reais neste trabalho; valem agora)",
        "Estas regras substituem o arquivo de instruções que os repositórios da "
        "empresa não podem ter. Trate cada uma como critério de reprovação: "
        "violação é achado, não sugestão.",
        "",
    ]
    for conf, manchete, corpo, arq in itens:
        partes.append(f"### {manchete}")
        partes.append(f"*(confiança {conf:.2f} · `regras/{arq.name}`)*")
        if completo:
            partes.append("")
            partes.append(corpo[:2500])
        partes.append("")
    return "\n".join(partes).strip()


def main() -> int:
    ap = argparse.ArgumentParser(description="Bloco de regras vivas para injetar em prompt.")
    ap.add_argument("--repo", required=True, help="caminho do repo alvo (o nome da pasta é a chave)")
    ap.add_argument("--completo", action="store_true", help="inclui o corpo de cada regra")
    ap.add_argument("--quantas", type=int, default=12)
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    print(bloco_para_prompt(Path(args.repo).name.lower(), args.quantas, args.completo))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
