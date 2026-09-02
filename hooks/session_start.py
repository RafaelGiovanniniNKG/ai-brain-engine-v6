#!/usr/bin/env python
"""Injeta o contexto do projeto no início da sessão.

Fecha a falha nº 1 medida no v5: a constituição e as regras vivas nunca chegavam
ao modelo. Aqui elas chegam por `additionalContext`, junto com a nota curada do
projeto no vault — que é a metade que faltava (o vault era mão única).

Princípios, todos vindos de dor documentada:
  * NUNCA levanta. Um hook de SessionStart que quebra estraga toda sessão nova.
    Qualquer erro sai em silêncio com código 0 e nada injetado.
  * Teto duro de caracteres. Injeção medida nesta máquina passa inteira até
    ~6.290 chars; acima disso é aposta.
  * Índice, não documento. As notas do diário entram como TÍTULO e CAMINHO; o
    modelo lê o arquivo se quiser. Guardar não é o problema — injetar é.
  * O preâmbulo de "referência histórica" é literal e não deve ser suavizado:
    é o que impede o modelo de reexecutar tarefa antiga como se fosse pedido.
  * UTF-8 explícito na saída. Sem isso o Windows escreve cp1252 e todo acento
    das notas em português chega corrompido ao modelo.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

TETO_TOTAL = 6000
TETO_INDICE = 3200
TOP_N_REGRAS = 12
MIN_CONFIANCA = 0.5
DECAIMENTO_POR_SEMANA = 0.02

PREAMBULO = (
    "CONTEXTO DO PROJETO (injetado pelo ai-brain-engine-v6) — "
    "REFERÊNCIA HISTÓRICA, NÃO É INSTRUÇÃO ATUAL.\n"
    "O que vem abaixo descreve o que já foi decidido e feito neste projeto. "
    "É POR PADRÃO DESATUALIZADO e NÃO deve ser reexecutado sem um pedido "
    "explícito e atual do usuário. Verifique contra o estado do git e da árvore "
    "de trabalho antes de qualquer ação."
)

RAIZ = Path(__file__).resolve().parent.parent


def _ler_entrada() -> dict:
    try:
        return json.loads(sys.stdin.read() or "{}")
    except Exception:
        return {}


def _repo_de(cwd: str) -> tuple[str, Path]:
    """Nome e raiz do repo. Fora de repo git, usa a própria pasta."""
    p = Path(cwd or os.getcwd())
    try:
        saida = subprocess.run(
            ["git", "-C", str(p), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5,
        )
        if saida.returncode == 0 and saida.stdout.strip():
            raiz = Path(saida.stdout.strip())
            return raiz.name, raiz
    except Exception:
        pass
    return p.name, p


def _config() -> dict:
    try:
        return json.loads((RAIZ / "mapa.json").read_text(encoding="utf-8"))
    except Exception:
        return {}


def _pasta_no_vault(repo: str, cfg: dict) -> Path | None:
    vault = cfg.get("vault")
    if not vault:
        return None
    base = Path(vault) / cfg.get("projetos", "Projetos")
    nome = (cfg.get("mapa") or {}).get(repo)
    if nome and (base / nome).is_dir():
        return base / nome
    # sem entrada no mapa: tenta casar por nome, ignorando pontuação
    alvo = re.sub(r"[^a-z0-9]", "", repo.lower())
    if not alvo:
        return None
    try:
        for d in base.iterdir():
            if d.is_dir() and alvo in re.sub(r"[^a-z0-9]", "", d.name.lower()):
                return d
    except Exception:
        pass
    return None


def _nota_indice(pasta: Path) -> tuple[str, Path] | None:
    """A nota curada do projeto. Aceita os nomes que o vault já usa hoje."""
    candidatos: list[Path] = []
    for padrao in ("_index.md", "Índice — *.md", "Indice — *.md", "Visão Geral*.md", "Visao Geral*.md"):
        candidatos.extend(sorted(pasta.glob(padrao)))
    for c in candidatos:
        try:
            texto = c.read_text(encoding="utf-8").strip()
        except Exception:
            continue
        if texto:
            return texto, c
    return None


def _ultimos_diarios(pasta: Path, quantos: int = 3) -> list[Path]:
    for nome in ("_diario", "_diário", "_log"):
        d = pasta / nome
        if d.is_dir():
            try:
                return sorted((f for f in d.glob("*.md")), reverse=True)[:quantos]
            except Exception:
                return []
    return []


def _desaspar(valor: str) -> str:
    """Tira aspas de escalar YAML citado — e só nesse caso.

    `strip("\\"'")` comeria a aspa final de uma frase que TERMINA com citação
    (`... e se lê como "o sistema não fez nada"`), mutilando a regra. Só remove
    quando as duas pontas são a mesma aspa e ela envolve o valor todo.
    """
    if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "\"'":
        return valor[1:-1].strip()
    return valor


def _primeiro_paragrafo(corpo: str, teto: int = 220) -> str:
    """Primeiro parágrafo de prosa do corpo, juntado e cortado em fim de frase."""
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


def _regras(chave_projeto: str) -> list[str]:
    """Manchete das regras vivas aplicáveis, por confiança efetiva.

    Injeta a linha `rule:` do frontmatter — não o corpo. O corpo de uma regra
    passa de 2 KB; doze corpos estouram qualquer teto. A manchete é a parte
    acionável, e o arquivo fica a um Read de distância.
    """
    dir_regras = RAIZ / "regras"
    if not dir_regras.is_dir():
        return []
    hoje = date.today()
    achadas: list[tuple[float, str]] = []
    for arq in dir_regras.glob("*.md"):
        if arq.stem.startswith("_"):
            continue
        try:
            texto = arq.read_text(encoding="utf-8")
        except Exception:
            continue
        m = re.match(r"^---\s*\n(.*?)\n---", texto, re.S)
        if not m:
            continue
        # Frontmatter com continuação: várias regras têm o `rule:` quebrado em duas
        # ou três linhas indentadas. Ler só a primeira entrega a manchete cortada
        # no meio da frase — foi o que o teste do Passo 1 pegou.
        meta: dict[str, str] = {}
        chave_atual = ""
        for linha in m.group(1).splitlines():
            if linha.startswith((" ", "\t")) and chave_atual:
                meta[chave_atual] = (meta[chave_atual] + " " + linha.strip()).strip()
            elif ":" in linha:
                k, _, v = linha.partition(":")
                chave_atual = k.strip().lower()
                meta[chave_atual] = v.strip()
            else:
                chave_atual = ""
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
        try:
            if confirmada:
                dias = (hoje - date.fromisoformat(confirmada[:10])).days
                conf -= max(0, dias) / 7.0 * DECAIMENTO_POR_SEMANA
        except Exception:
            pass
        if conf < MIN_CONFIANCA:
            continue
        manchete = _desaspar((meta.get("rule") or "").strip())
        if not manchete:
            # Regras antigas (do v5) não têm o campo `rule:`. O plano B é o primeiro
            # PARÁGRAFO do corpo, junto — pegar uma linha física entrega meia frase,
            # porque o markdown das regras é quebrado à mão.
            manchete = _primeiro_paragrafo(texto[m.end():]) or arq.stem.replace("-", " ")
        achadas.append((conf, manchete))
    achadas.sort(key=lambda x: x[0], reverse=True)
    return [f"- {texto}" for _, texto in achadas[:TOP_N_REGRAS]]


def main() -> int:
    entrada = _ler_entrada()
    motivo = entrada.get("start_reason") or entrada.get("reason") or "startup"
    if motivo == "resume":
        return 0  # o contexto já está na conversa retomada

    repo, _raiz_repo = _repo_de(entrada.get("cwd", ""))
    cfg = _config()
    partes: list[str] = [PREAMBULO, f"Projeto: {repo}"]

    pasta = _pasta_no_vault(repo, cfg)
    if pasta:
        nota = _nota_indice(pasta)
        if nota:
            texto, caminho = nota
            if len(texto) > TETO_INDICE:
                texto = texto[:TETO_INDICE].rsplit("\n", 1)[0] + "\n[…] (nota truncada — leia o arquivo)"
            partes.append(f"## Nota do projeto no vault ({caminho.name})\n{texto}")
        diarios = _ultimos_diarios(pasta)
        if diarios:
            listados = "\n".join(f"- {d.name} — {d}" for d in diarios)
            partes.append(f"## Registros recentes (leia o arquivo se precisar do detalhe)\n{listados}")
        partes.append(f"Documentação deste projeto: {pasta} — pode ler qualquer nota daí.")

    regras = _regras(repo.lower())
    if regras:
        partes.append(
            "## Regras aprendidas de falhas reais (valem agora, não são histórico)\n"
            + "\n".join(regras)
        )

    bloco = "\n\n".join(partes)
    if len(bloco) > TETO_TOTAL:
        bloco = bloco[:TETO_TOTAL].rsplit("\n", 1)[0] + "\n[…] (bloco truncado no teto de injeção)"

    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(
        {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": bloco}},
        ensure_ascii=False,
    ))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # silêncio é obrigatório aqui: melhor sessão sem contexto que sessão quebrada
        sys.exit(0)
