#!/usr/bin/env python
"""Escreve no vault o que aconteceu na sessão. Um processo, uma chamada de modelo.

Roda SEMPRE destacado da sessão (quem dispara é `hooks/gatilho_diario.py`), por
três motivos medidos:
  * o hook de fim de sessão tem 1,5 s de orçamento compartilhado e há sete
    defeitos registrados de ele ser morto no meio;
  * no Windows, gerar filho pelo caminho comum a partir do encerramento faz o
    Claude Code esperar a árvore inteira de processos, ignorando o timeout;
  * documentação não pode atrasar a sua resposta.

Três garantias:
  1. **Idempotente.** Guarda a assinatura do que já escreveu; nada novo, não
     escreve. É o conserto do "mesmo plano capturado três vezes no mesmo dia".
  2. **Serializado.** Trava por repo; dois disparos simultâneos não escrevem
     juntos.
  3. **Nunca depende do modelo.** Se o `claude -p` falhar, cair ou demorar, o
     bloco é escrito com o resumo MECÂNICO (pedidos, arquivos, teste, commits) e
     marcado como não destilado. Documentação que só existe quando o modelo
     responde não é documentação.

Uso: python destilar.py --sessao <id> [--motivo stop|precompact|sessionend]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "hooks"))
import estado  # noqa: E402
import vault  # noqa: E402

# `V6_MODELO_RESUMO` existe para poder provar o caminho de FALHA: apontando para
# um modelo inexistente, o destilador tem de escrever o resumo mecânico e marcar
# a nota como não destilada. Caminho de erro que não é testado não funciona.
MODELO = os.environ.get("V6_MODELO_RESUMO") or "claude-haiku-4-5"
TETO_MODELO_SEG = int(os.environ.get("V6_TETO_RESUMO") or 90)


def _git(repo: Path, *args: str) -> str:
    try:
        r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=15)
        return (r.stdout or "").strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def _repo_da_sessao(d: dict) -> Path | None:
    for candidato in (
        (d.get("ultima_edicao") or {}).get("repo"),
        d.get("cwd"),
    ):
        if candidato:
            p = Path(candidato)
            topo = _git(p, "rev-parse", "--show-toplevel")
            if topo:
                return Path(topo)
            if p.is_dir():
                return p
    return None


def _digest_mecanico(d: dict, repo: Path | None) -> dict:
    pedidos = [p["texto"] for p in (d.get("pedidos") or []) if p.get("texto")]
    arquivos = d.get("arquivos_tocados") or []
    teste = d.get("ultimo_teste") or {}
    return {
        "pedidos": pedidos,
        "arquivos": arquivos,
        "commits": d.get("commits") or [],
        "teste": teste,
        "sensor": d.get("sensor_reprovou") or {},
        "branch": _git(repo, "rev-parse", "--abbrev-ref", "HEAD") if repo else "",
        "sujo": len([l for l in (_git(repo, "status", "--short") or "").splitlines() if l.strip()]) if repo else 0,
    }


def _texto_mecanico(dig: dict) -> str:
    linhas = []
    if dig["pedidos"]:
        linhas.append("**Pedidos desta sessão:**")
        linhas += [f"- {p}" for p in dig["pedidos"][:8]]
    if dig["commits"]:
        linhas.append("\n**Commits:**")
        linhas += [f"- `{c['sha'][:8]}` {c['mensagem']}" for c in dig["commits"]]
    if dig["arquivos"]:
        linhas.append(f"\n**Arquivos de código tocados ({len(dig['arquivos'])}):**")
        linhas += [f"- `{Path(a).name}`" for a in dig["arquivos"][:12]]
        if len(dig["arquivos"]) > 12:
            linhas.append(f"- … e {len(dig['arquivos']) - 12} outros")
    t = dig["teste"]
    if t:
        veredito = {True: "passou", False: "FALHOU", None: "indeterminado"}[t.get("ok")]
        linha = f"\n**Último teste:** `{t.get('comando','')}` → **{veredito}**"
        # A linha do placar entra palavra por palavra. Escrever só "passou" no
        # diário é a mesma afirmação sem prova que este motor existe para
        # impedir — quem ler amanhã precisa do número, não do adjetivo.
        if t.get("evidencia"):
            linha += f"\n  - saída: `{t['evidencia']}`"
        linhas.append(linha)
    if dig["sensor"]:
        linhas.append(f"\n**Sensor reprovou:** {dig['sensor'].get('arquivo','')}")
    if dig["sujo"]:
        linhas.append(f"\n**Não commitado ao fim:** {dig['sujo']} arquivo(s).")
    return "\n".join(linhas).strip()


def _destilar_com_modelo(dig: dict, repo_nome: str) -> str:
    entrada = json.dumps(dig, ensure_ascii=False, indent=1)[:20000]
    prompt = (
        "Você recebe o registro MECÂNICO de uma sessão de programação no repositório "
        f"`{repo_nome}` (pedidos do usuário, arquivos tocados, commits, resultado de teste).\n"
        "Escreva em português do Brasil, em no máximo 8 linhas, três blocos com estes títulos "
        "exatos em negrito: **O que foi feito**, **O que foi decidido**, **O que ficou pendente**.\n"
        "Regras: só afirme o que o registro sustenta; se não houver decisão ou pendência, escreva "
        "'nada registrado'; não elogie, não resuma o resumo, não invente número; se o teste falhou "
        "ou ficou indeterminado, diga isso explicitamente na pendência.\n\n"
        f"REGISTRO:\n{entrada}"
    )
    try:
        r = subprocess.run(
            ["claude", "-p", "--model", MODELO, prompt],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=TETO_MODELO_SEG,
        )
        saida = (r.stdout or "").strip()
        return saida if r.returncode == 0 and len(saida) > 40 else ""
    except Exception:
        return ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sessao", required=True)
    ap.add_argument("--motivo", default="stop")
    args = ap.parse_args()

    d = estado.ler(args.sessao)
    if not d:
        return 0

    # nada novo desde a última escrita: sai sem tocar em nada
    assin = estado.assinatura(d)
    if d.get("diario_assinatura") == assin:
        return 0
    if not (d.get("pedidos") or d.get("arquivos_tocados") or d.get("commits")):
        return 0

    repo = _repo_da_sessao(d)
    repo_nome = repo.name if repo else "sem-repo"

    # trava por repo: dois disparos não escrevem juntos
    trava = estado.pasta() / f"trava-{vault.slug(repo_nome)}.lock"
    try:
        fd = os.open(str(trava), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
    except FileExistsError:
        try:  # trava órfã de processo morto há mais de 10 min
            if time.time() - trava.stat().st_mtime > 600:
                trava.unlink()
            else:
                return 0
        except Exception:
            return 0
    except Exception:
        pass

    try:
        pasta = vault.pasta_no_vault(repo_nome)
        if not pasta:
            cfg = vault.config()
            if not cfg.get("vault"):
                return 0
            pasta = Path(cfg["vault"]) / cfg.get("projetos", "Projetos") / repo_nome
        pasta.mkdir(parents=True, exist_ok=True)

        agora = datetime.now()
        arquivo = pasta / "_diario" / f"{agora:%Y-%m-%d}.md"

        dig = _digest_mecanico(d, repo)
        corpo_modelo = _destilar_com_modelo(dig, repo_nome)
        mecanico = _texto_mecanico(dig)

        # O cabeçalho é a CHAVE do upsert, então tem de ser estável para a mesma
        # sessão: hora de INÍCIO e primeiro pedido. Usando a hora do momento, cada
        # nova destilação da mesma sessão criava um bloco novo — exatamente o
        # problema que o upsert existe para resolver, e foi o que a prova pegou.
        inicio = datetime.fromtimestamp(float(d.get("inicio") or time.time()))
        primeiro_pedido = (dig["pedidos"] or ["sessão sem pedido registrado"])[0]
        titulo = vault.slug(primeiro_pedido, 48) or "sessao"
        cabecalho = f"## {inicio:%H:%M} — {titulo}"

        partes = [cabecalho, ""]
        if corpo_modelo:
            partes += [corpo_modelo, ""]
        else:
            partes += [
                "> Resumo **não destilado** — o modelo de resumo não respondeu. "
                "O registro mecânico abaixo é verdade medida; a leitura dele é sua.",
                "",
            ]
        partes += [mecanico, ""]
        partes.append(
            f"<!-- motivo do disparo: {args.motivo} · sessão {args.sessao[:8]} · "
            f"assinatura {assin} -->"
        )
        bloco = "\n".join(partes)

        atual = vault.ler(arquivo)
        meta, corpo = vault.partir(atual)
        corpo = vault.upsert_bloco(corpo, cabecalho, bloco)

        meta_novo = {
            "data": f"{agora:%Y-%m-%d}",
            "repo": repo_nome,
            "branch": dig["branch"] or "",
            "tipo": "diario-automatico",
            "sessoes": len({m for m in re.findall(r"sessão (\w{8})", corpo)}) or 1,
            "destilado": bool(corpo_modelo),
            "modificado": agora.isoformat(timespec="seconds"),
        }
        if isinstance(meta, dict):
            meta_novo = {**{k: v for k, v in meta.items() if k not in meta_novo}, **meta_novo}

        if vault.escrever(arquivo, vault.frontmatter(meta_novo) + "\n" + corpo.lstrip()):
            estado.anotar(args.sessao, diario_assinatura=assin, diario_ts=time.time(),
                          diario_arquivo=str(arquivo))
        return 0
    finally:
        try:
            trava.unlink()
        except Exception:
            pass


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
