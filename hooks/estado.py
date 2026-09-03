#!/usr/bin/env python
"""Registro do que aconteceu na sessão. Sem LLM, sem rede, sem opinião.

O portão do encerramento precisa responder a uma pergunta de fato — "editou
código e rodou teste verde depois?" — e a transcrição da sessão não serve para
isso: a documentação oficial avisa que ela é escrita de forma assíncrona e pode
atrasar em relação ao turno atual. Então cada hook anota o que viu, aqui, na
hora.

Isto também é a camada 0 da documentação automática (Passo 4): o mesmo registro
que decide o portão é o que depois alimenta o diário no vault.

Um arquivo JSON por sessão. Escrita atômica (grava em `.tmp` e renomeia), porque
dois hooks podem disparar quase juntos e um arquivo meio escrito é pior que
nenhum.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

EXT_CODIGO = {".cs", ".razor", ".cshtml", ".ts", ".tsx", ".mts", ".cts", ".js", ".mjs", ".dart"}


def pasta() -> Path:
    base = os.environ.get("CLAUDE_PLUGIN_DATA") or os.environ.get("LOCALAPPDATA")
    raiz = Path(base) / "ai-brain-engine-v6" if base else Path(__file__).resolve().parent.parent / "_estado"
    raiz.mkdir(parents=True, exist_ok=True)
    return raiz


def _caminho(sessao: str) -> Path:
    seguro = "".join(c for c in (sessao or "sem-sessao") if c.isalnum() or c in "-_")[:64]
    return pasta() / f"{seguro or 'sem-sessao'}.json"


def ler(sessao: str) -> dict:
    try:
        return json.loads(_caminho(sessao).read_text(encoding="utf-8"))
    except Exception:
        return {}


def gravar(sessao: str, dados: dict) -> None:
    alvo = _caminho(sessao)
    tmp = alvo.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
        os.replace(tmp, alvo)
    except Exception:
        pass


def anotar(sessao: str, **campos) -> dict:
    d = ler(sessao)
    d.update(campos)
    gravar(sessao, d)
    return d


def registrar_edicao(sessao: str, arquivo: str, repo: str | None, reprovou: str = "") -> None:
    """Uma edição de CÓDIGO. Edição de markdown ou json não pede teste."""
    if Path(arquivo).suffix.lower() not in EXT_CODIGO:
        return
    d = ler(sessao)
    d["ultima_edicao"] = {"ts": time.time(), "arquivo": arquivo, "repo": repo or ""}
    arquivos = d.get("arquivos_tocados") or []
    if arquivo not in arquivos:
        arquivos.append(arquivo)
    d["arquivos_tocados"] = arquivos[-50:]
    # A hora de modificação fica marcada aqui também, para o sensor de edição
    # pelo terminal não anunciar como "mexeu pelo terminal" um arquivo que a
    # ferramenta de edição acabou de registrar. Ver registrar_edicoes_do_terminal.
    try:
        vistos = dict(d.get("mtimes_vistos") or {})
        vistos[_chave(arquivo)] = Path(arquivo).stat().st_mtime
        d["mtimes_vistos"] = vistos
    except Exception:
        pass
    if reprovou:
        d["sensor_reprovou"] = {"ts": time.time(), "arquivo": arquivo, "resumo": reprovou[:800]}
    gravar(sessao, d)


# ---------------------------------------------------------------------------
# Edição feita pelo TERMINAL
#
# O aviso de edição só chega quando o arquivo é mexido pela ferramenta de
# edição. Mexer pelo terminal — `sed -i`, `>`, `>>`, um heredoc, um script que
# escreve — não gera aviso nenhum, e o portão nunca fica sabendo. Medido em
# 03/09/2026: criei e alterei um `.ts` por `printf >` e `sed -i` e o registro
# não mudou. É o mesmo tipo de furo que a delegação para sub-agente abria: um
# caminho por fora da prova. E é pior, porque o modo automático de trabalho
# manda editar assim — dá para escapar do portão sem tentar.
#
# O conserto NÃO adivinha pelo texto do comando (script que escreve arquivo
# passaria batido). Pergunta ao git o que está sujo e usa a hora de modificação
# para separar o que mudou NESTA sessão da sujeira que já estava lá. 57 ms no
# maior repo da casa, medido antes de escolher este caminho.
# ---------------------------------------------------------------------------

# Comandos que mudam a árvore SEM ninguém editar. Trocar de branch muda arquivo
# de código, mas não é trabalho a provar — registrar isso viraria armadilha.
CMD_MOVE_ARVORE = (
    "checkout", "switch", "stash", "restore", "reset", "merge", "rebase",
    "pull", "clean", "revert", "cherry-pick", "apply", "am",
)


def _chave(arquivo: str) -> str:
    """Chave estável para o mesmo arquivo, venha de onde vier.

    No Windows `C:\\Users\\RAFAEL~1.GIO\\...` (forma curta 8.3) e
    `C:\\Users\\rafael.giovannini\\...` (forma longa) são a mesma pasta, e a
    caixa não importa — mas comparar TEXTO diz que são diferentes. A ferramenta
    de edição grava o caminho resolvido; este sensor monta o caminho a partir da
    saída do git. Sem normalizar, o sensor anuncia como "mexeu pelo terminal" um
    arquivo que a ferramenta acabou de registrar. É a mesma armadilha que já
    custou um falso verde no sensor de TypeScript.
    """
    try:
        return str(Path(arquivo).resolve()).lower()
    except Exception:
        return str(arquivo).lower()


def _sujos_do_repo(repo: str) -> list[str]:
    """Arquivos de CÓDIGO que o git vê como modificados ou novos."""
    import subprocess
    try:
        r = subprocess.run(
            ["git", "-C", str(repo), "status", "--porcelain", "--untracked-files=normal"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15,
        )
    except Exception:
        return []
    if r.returncode != 0:
        return []
    achados: list[str] = []
    for linha in (r.stdout or "").splitlines():
        caminho = linha[3:].strip().strip('"')
        if " -> " in caminho:            # rename: interessa o destino
            caminho = caminho.split(" -> ", 1)[1].strip().strip('"')
        if not caminho or caminho.endswith("/"):
            continue
        if Path(caminho).suffix.lower() not in EXT_CODIGO:
            continue
        achados.append(str(Path(repo) / caminho))
    return achados


def registrar_edicoes_do_terminal(sessao: str, repo: str, comando: str) -> list[str]:
    """Registra código que mudou nesta sessão sem passar pela ferramenta de edição.

    Devolve o que registrou, para o gatilho poder dizer em voz alta."""
    if not repo:
        return []
    d = ler(sessao)
    inicio = float(d.get("inicio") or 0)
    if not inicio:
        return []  # sem marca de início não há como separar sujeira antiga: não invento

    # Comando que MOVE a árvore: os arquivos que ele mudou passam a contar como
    # "já vistos", sem virar edição. Só pular o registro não resolvia — os
    # arquivos continuavam sujos e o comando SEGUINTE os registrava, então o
    # portão barrava depois de uma troca de branch, com um comando de atraso.
    # Medido pela prova, cenário 6.
    baixo = (comando or "").lower()
    if "git" in baixo and any(v in baixo for v in CMD_MOVE_ARVORE):
        vistos = dict(d.get("mtimes_vistos") or {})
        for arquivo in _sujos_do_repo(repo):
            try:
                vistos[_chave(arquivo)] = Path(arquivo).stat().st_mtime
            except Exception:
                continue
        anotar(sessao, mtimes_vistos=vistos)
        return []
    # A comparação é por HORA DE MODIFICAÇÃO, não por presença na lista de
    # arquivos tocados: um arquivo já registrado que é editado DE NOVO tem de
    # contar de novo, senão bastaria testar uma vez e depois mexer à vontade.
    vistos = dict(d.get("mtimes_vistos") or {})
    novos: list[str] = []
    for arquivo in _sujos_do_repo(repo):
        try:
            mtime = Path(arquivo).stat().st_mtime
        except Exception:
            continue
        if mtime <= inicio:
            continue  # já estava assim quando a sessão começou
        k = _chave(arquivo)
        if abs(float(vistos.get(k) or 0) - mtime) < 0.001:
            continue  # nada mudou desde a última conferência
        vistos[k] = mtime
        novos.append(arquivo)
    if novos:
        for arquivo in novos:
            registrar_edicao(sessao, arquivo, repo)
        anotar(sessao, mtimes_vistos=vistos)
    return novos


def registrar_execucao(sessao: str, comando: str, tipo: str, ok: bool | None,
                       evidencia: str = "", cwd: str = "") -> None:
    """Um `dotnet test`, `ng test`, `dotnet build`… com o veredito e a linha do placar.

    A evidência é obrigatória por princípio: registrar "passou" é afirmação;
    registrar "Failed: 0, Passed: 319" é prova."""
    d = ler(sessao)
    d[f"ultimo_{tipo}"] = {"ts": time.time(), "comando": comando[:300], "ok": ok,
                           "evidencia": (evidencia or "")[:200]}
    gravar(sessao, d)
    if tipo == "teste" and ok is True and cwd:
        limpar_edicao_de_agente(cwd)


# ---------------------------------------------------------------------------
# Edição feita DENTRO de um sub-agente
#
# A documentação oficial diz duas coisas que, juntas, abrem um furo no portão:
# os hooks configurados **também rodam dentro do sub-agente**, e o campo
# `agent_id` só aparece quando o hook disparou lá dentro. O que ela NÃO diz é se
# o `session_id` do sub-agente é o mesmo da sessão que o chamou.
#
# Se for outro, a edição do sub-agente vai para um registro que o portão da
# sessão principal nunca lê — e o portão libera trabalho não verificado, que é
# exatamente a única coisa que ele existe para impedir.
#
# Em vez de apostar numa das hipóteses, a edição de sub-agente é registrada
# TAMBÉM num lugar endereçado pelo diretório de trabalho, que as duas sessões
# compartilham. O portão passa a olhar os dois. Funciona igual nas duas
# hipóteses, e continua correto no dia em que a resposta mudar de versão.
# ---------------------------------------------------------------------------

VALIDADE_AGENTE_SEG = 12 * 3600


def _caminho_agente(cwd: str) -> Path:
    import hashlib
    chave = hashlib.sha256(str(Path(cwd or ".").resolve()).lower().encode("utf-8")).hexdigest()[:16]
    return pasta() / f"agente-{chave}.json"


def registrar_edicao_de_agente(cwd: str, arquivo: str, agente: str = "") -> None:
    if Path(arquivo).suffix.lower() not in EXT_CODIGO:
        return
    alvo = _caminho_agente(cwd)
    dados = {"ts": time.time(), "arquivo": arquivo, "agente": agente[:60], "cwd": cwd}
    tmp = alvo.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
        os.replace(tmp, alvo)
    except Exception:
        pass


def edicao_de_agente(cwd: str) -> dict:
    """A edição de sub-agente pendente para este diretório, se ainda vale.

    A validade existe porque este registro sobrevive à sessão: sem ela, uma
    edição de sub-agente que ninguém testou barraria toda sessão futura naquele
    repositório, e portão que nega para sempre é sessão travada."""
    try:
        d = json.loads(_caminho_agente(cwd).read_text(encoding="utf-8"))
    except Exception:
        return {}
    if time.time() - float(d.get("ts") or 0) > VALIDADE_AGENTE_SEG:
        return {}
    return d


def limpar_edicao_de_agente(cwd: str) -> None:
    try:
        _caminho_agente(cwd).unlink()
    except Exception:
        pass


def liberar(sessao: str, motivo: str) -> None:
    anotar(sessao, escape={"ts": time.time(), "motivo": motivo[:200]})


def registrar_prompt(sessao: str, texto: str, cwd: str = "") -> None:
    """O que o Rafael pediu. É a espinha do diário: sem isso o registro conta o
    que MUDOU e não o que foi PEDIDO, e quem lê depois não entende o porquê."""
    d = ler(sessao)
    pedidos = d.get("pedidos") or []
    pedidos.append({"ts": time.time(), "texto": (texto or "").strip()[:400]})
    d["pedidos"] = pedidos[-40:]
    if cwd and not d.get("cwd"):
        d["cwd"] = cwd
    if not d.get("inicio"):
        d["inicio"] = time.time()
    gravar(sessao, d)


def registrar_commit(sessao: str, sha: str, mensagem: str, repo: str = "") -> None:
    """Commit é a verdade que a conversa não pode falsear."""
    d = ler(sessao)
    commits = d.get("commits") or []
    if not any(c.get("sha") == sha for c in commits):
        commits.append({"ts": time.time(), "sha": sha, "mensagem": mensagem[:200], "repo": repo})
    d["commits"] = commits[-30:]
    gravar(sessao, d)


def assinatura(d: dict) -> str:
    """Impressão digital do que já é conhecido. Igual = nada novo para escrever."""
    import hashlib
    partes = [
        str(len(d.get("pedidos") or [])),
        str(len(d.get("arquivos_tocados") or [])),
        str(len(d.get("commits") or [])),
        json.dumps(d.get("ultimo_teste") or {}, sort_keys=True),
        json.dumps(d.get("ultima_edicao") or {}, sort_keys=True),
    ]
    return hashlib.sha256("|".join(partes).encode("utf-8")).hexdigest()[:16]
