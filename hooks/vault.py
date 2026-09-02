#!/usr/bin/env python
"""Escrita no vault Obsidian, com as armadilhas já pagas.

Cada função aqui existe por um modo de falha documentado:

  * `slug()` — o Obsidian Sync historicamente **ignorava em silêncio** arquivo
    com dois-pontos no nome, e o Windows recusa `< > : " / \\ | ? *`, espaço ou
    ponto no fim, e os nomes reservados (`CON`, `NUL`, `COM1`…). Além disso
    `# ^ [ ]` colidem com a sintaxe de link do próprio Obsidian. Por isso o slug
    é por **lista de permissão**, nunca por lista de proibição.
  * `frontmatter()` — YAML montado por junção de texto quebra com o nosso
    conteúdo: os títulos daqui são cheios de `Onda 8:` (dois-pontos), acento, e
    `—`. E o Obsidian pinta frontmatter inválido de vermelho e alguns plugins
    param de funcionar no arquivo. Então: serializador de verdade, tudo achatado
    (aninhamento não é suportado em propriedades) e valor sempre citado.
  * `escrever()` — grava em `.tmp` e renomeia. Obsidian aberto no mesmo arquivo
    pode comer uma escrita parcial. E escreve UTF-8 **sem BOM** com `\\n`: BOM
    antes do `---` mata o frontmatter, e o padrão do PowerShell daqui é justo o
    contrário.
  * `upsert_bloco()` — substitui o bloco do mesmo cabeçalho em vez de anexar
    outro. É o conserto do "mesmo plano capturado três vezes no mesmo dia".
"""

from __future__ import annotations

import json
import os
import re
import unicodedata
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent

RESERVADOS = {
    "con", "prn", "aux", "nul",
    *{f"com{i}" for i in range(1, 10)},
    *{f"lpt{i}" for i in range(1, 10)},
}


def config() -> dict:
    """`V6_VAULT` sobrepõe o caminho do vault — é o que permite testar a escrita
    sem sujar o cofre de verdade. Um escritor automático que só pode ser testado
    em produção não vai ser testado."""
    try:
        cfg = json.loads((RAIZ / "mapa.json").read_text(encoding="utf-8"))
    except Exception:
        cfg = {}
    if os.environ.get("V6_VAULT"):
        cfg["vault"] = os.environ["V6_VAULT"]
    return cfg


def pasta_no_vault(repo: str, cfg: dict | None = None) -> Path | None:
    """Pasta do projeto no vault: pelo mapa, ou casando o nome sem pontuação."""
    cfg = cfg if cfg is not None else config()
    if not cfg.get("vault"):
        return None
    base = Path(cfg["vault"]) / cfg.get("projetos", "Projetos")
    nome = (cfg.get("mapa") or {}).get(repo)
    if nome and (base / nome).is_dir():
        return base / nome
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


def slug(texto: str, teto: int = 60) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto or "")
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    limpo = re.sub(r"[^A-Za-z0-9]+", "-", sem_acento).strip("-").lower()[:teto].strip("-.")
    if not limpo or limpo in RESERVADOS:
        limpo = f"nota-{limpo}" if limpo else "nota"
    return limpo


def frontmatter(dados: dict) -> str:
    """YAML plano, valores citados, chaves ordenadas — por serializador."""
    achatado = {}
    for k, v in dados.items():
        if isinstance(v, (dict, list, tuple, set)):
            v = json.dumps(v, ensure_ascii=False) if not isinstance(v, (list, tuple)) else list(v)
        achatado[str(k)] = v
    corpo = yaml.safe_dump(achatado, allow_unicode=True, default_flow_style=False, sort_keys=True)
    return f"---\n{corpo}---\n"


def escrever(caminho: Path, conteudo: str) -> bool:
    try:
        caminho.parent.mkdir(parents=True, exist_ok=True)
        tmp = caminho.with_suffix(caminho.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            f.write(conteudo)
        os.replace(tmp, caminho)
        return True
    except Exception:
        return False


def ler(caminho: Path) -> str:
    try:
        texto = caminho.read_text(encoding="utf-8")
    except Exception:
        return ""
    return texto.lstrip("﻿")  # BOM que outra ferramenta tenha deixado


def upsert_bloco(texto: str, cabecalho: str, bloco: str) -> str:
    """Substitui o bloco de mesmo cabeçalho `## ...`; anexa se não existir."""
    linhas = texto.splitlines()
    inicio = next((i for i, l in enumerate(linhas) if l.strip() == cabecalho.strip()), None)
    novo = bloco.rstrip() + "\n"
    if inicio is None:
        base = texto.rstrip()
        return (base + "\n\n" + novo) if base else novo
    fim = len(linhas)
    for j in range(inicio + 1, len(linhas)):
        if linhas[j].startswith("## "):
            fim = j
            break
    return "\n".join(linhas[:inicio] + novo.rstrip().splitlines() + [""] + linhas[fim:]).rstrip() + "\n"


def partir(texto: str) -> tuple[dict, str]:
    """Separa frontmatter e corpo de uma nota existente."""
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?", texto, re.S)
    if not m:
        return {}, texto
    try:
        meta = yaml.safe_load(m.group(1)) or {}
    except Exception:
        meta = {}
    return (meta if isinstance(meta, dict) else {}), texto[m.end():]
