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
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import regras as regras_mod  # noqa: E402
import vault as vault_mod  # noqa: E402

TETO_TOTAL = 6000
TETO_INDICE = 4000  # a nota do projeto é a peça de maior sinal: come primeiro
TOP_N_REGRAS = 12  # confiança, decaimento e escopo vivem em hooks/regras.py

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


def _orcamento_memoria(indice: Path | None = None) -> str:
    """Avisa quando o índice da memória automática se aproxima do teto.

    A regra oficial: as primeiras 200 linhas do índice, ou os primeiros 25 KB, o
    que vier primeiro, são carregados no início de toda conversa — **e o que passa
    disso não é carregado**. Silenciosamente. Um índice que cresceu virou memória
    que desapareceu sem ninguém perceber, e é exatamente o tipo de falha que este
    motor existe para tornar visível.

    O parâmetro existe para o teste poder exercitar os DOIS lados.
    """
    try:
        if indice is None:
            cfg = json.loads((Path.home() / ".claude" / "settings.json").read_text(encoding="utf-8"))
            pasta = cfg.get("autoMemoryDirectory")
            if not pasta:
                return ""
            indice = Path(pasta.replace("~", str(Path.home()))) / "MEMORY.md"
        texto = Path(indice).read_text(encoding="utf-8")
    except Exception:
        return ""
    linhas, bytes_ = len(texto.splitlines()), len(texto.encode("utf-8"))
    if linhas < 160 and bytes_ < 20480:
        return ""
    return (
        f"⚠ ORÇAMENTO DA MEMÓRIA: o índice está em {linhas}/200 linhas e "
        f"{bytes_}/25600 bytes. O que passar do teto **deixa de ser carregado, sem aviso**. "
        "Hora de curar o índice (skill `v6-curar`)."
    )


def _sensores_faltando() -> str:
    """Diz quais sensores não estão instalados NESTA máquina.

    Só as checagens baratas (existe o binário? existe a pasta?) — menos de 50 ms,
    porque isto roda antes de toda sessão. O diagnóstico completo é
    `python hooks/doutor.py`.

    Existe porque sensor ausente é a pior falha possível deste motor: ele não
    grita, ele simplesmente não acha nada — e "não achou nada" se lê como "está
    tudo bem". Numa máquina nova, sem isto, o motor pareceria funcionando.
    """
    import shutil
    faltas: list[str] = []
    if not (shutil.which("slopwatch") or (Path.home() / ".dotnet" / "tools" / "slopwatch.exe").is_file()):
        faltas.append("slopwatch (teste desligado, aviso silenciado, catch vazio em .cs)")
    if not (RAIZ / "sensores" / "eslint" / "node_modules" / "eslint" / "bin" / "eslint.js").is_file():
        faltas.append("eslint do motor (fronteira de módulo e trapaça em .ts)")
    if not (shutil.which("csharp-ls") or (Path.home() / ".dotnet" / "tools" / "csharp-ls.exe").is_file()):
        faltas.append("csharp-ls (erro do compilador aparecendo sozinho)")
    if not faltas:
        return ""
    return (
        "⚠ SENSOR AUSENTE nesta máquina — o motor está medindo MENOS do que deveria, "
        "e sensor que não roda não acusa nada:\n"
        + "\n".join(f"- {f}" for f in faltas)
        + "\nConserto: `powershell -File <motor>/instalar.ps1`. "
        "Diga isso ao Rafael antes de afirmar que algo está verificado."
    )


def main() -> int:
    entrada = _ler_entrada()
    motivo = entrada.get("start_reason") or entrada.get("reason") or "startup"

    # A hora de início fica marcada ANTES de qualquer coisa, e mesmo em sessão
    # retomada. É ela que separa "arquivo que já estava sujo quando eu cheguei"
    # de "arquivo que mudou nesta sessão" — sem essa marca, o sensor de edição
    # pelo terminal registraria a sujeira alheia como trabalho meu, e o portão
    # barraria a sessão por algo que ninguém tocou.
    try:
        import estado as estado_mod  # noqa: PLC0415
        if not estado_mod.ler(entrada.get("session_id", "")).get("inicio"):
            estado_mod.anotar(entrada.get("session_id", ""), inicio=time.time(),
                              cwd=entrada.get("cwd", ""))
    except Exception:
        pass

    if motivo == "resume":
        return 0  # o contexto já está na conversa retomada

    bloco = montar_bloco(entrada.get("cwd", ""))
    if not bloco:
        return 0

    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(
        {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": bloco}},
        ensure_ascii=False,
    ))
    return 0


def montar_bloco(cwd: str, so_as_regras: bool = False) -> str:
    """O bloco de contexto do projeto. Uma função, dois consumidores.

    Foi extraído de `main` porque o início da sessão não é o único momento em
    que este bloco precisa chegar ao modelo: quando a conversa fica longa o
    programa a resume e joga o começo fora — as regras vivas incluídas — e
    `SessionStart` NÃO dispara nesse caso. Ver `hooks/reinjetar.py`.

    `so_as_regras` serve à reinjeção: depois de um resumo, a nota do projeto e o
    aviso de orçamento provavelmente sobreviveram (ou o modelo sabe onde ler);
    o que desaparece calado são as regras.
    """
    repo, _raiz_repo = _repo_de(cwd)
    partes: list[str] = [PREAMBULO, f"Projeto: {repo}"]

    pasta = None if so_as_regras else vault_mod.pasta_no_vault(repo)
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

    aviso = "" if so_as_regras else _orcamento_memoria()
    if aviso:
        partes.insert(1, aviso)  # logo depois do preâmbulo: é o que não pode passar batido

    faltando = "" if so_as_regras else _sensores_faltando()
    if faltando:
        partes.insert(1, faltando)

    # As regras entram por ÚLTIMO e cabem no que sobrou. Corte cego no fim do
    # bloco parte a última regra no meio da frase, e meia regra é pior que
    # nenhuma — o modelo obedece uma instrução que ninguém escreveu. Então se
    # falta espaço, descarta-se regra INTEIRA, da menor confiança para cima, e
    # diz-se quantas ficaram de fora. A nota do projeto e o aviso de orçamento
    # nunca são sacrificados: aquilo o modelo não tem como buscar sozinho.
    regras = regras_mod.manchetes(repo.lower(), TOP_N_REGRAS)
    cabecalho_regras = "## Regras aprendidas de falhas reais (valem agora, não são histórico)"
    base = "\n\n".join(partes)
    mostradas = list(regras)
    while mostradas:
        rodape = (
            f"\n(+{len(regras) - len(mostradas)} regra(s) de menor confiança não listadas — "
            f"estão em `ai-brain-engine-v6/regras/`)" if len(mostradas) < len(regras) else ""
        )
        tentativa = base + "\n\n" + cabecalho_regras + "\n" + "\n".join(mostradas) + rodape
        if len(tentativa) <= TETO_TOTAL:
            base = tentativa
            break
        mostradas.pop()
    bloco = base
    if len(bloco) > TETO_TOTAL:  # nem sem regra nenhuma cabe: sobra cortar a nota
        bloco = bloco[:TETO_TOTAL].rsplit("\n", 1)[0] + "\n[…] (nota do projeto truncada — leia o arquivo)"
    return bloco


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # silêncio é obrigatório aqui: melhor sessão sem contexto que sessão quebrada
        sys.exit(0)
