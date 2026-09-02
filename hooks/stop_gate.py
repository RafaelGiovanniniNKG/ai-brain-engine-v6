#!/usr/bin/env python
"""O portão: nega o encerramento quando houve código editado sem teste verde.

Este é o buraco que nenhuma versão do motor cobria. Instrução escrita não
resolve — a documentação oficial é explícita: `CLAUDE.md` é contexto, não
configuração imposta, e "para bloquear uma ação independentemente do que o
Claude decida, use um hook". O evento `Stop` pode NEGAR o encerramento, e é o
único lugar onde "não afirme sem prova" deixa de ser texto e passa a ser fato.

Nível escolhido pelo Rafael em 02/09/2026: **RÍGIDO** — não devolve código
editado sem teste verde, mesmo sem afirmação nenhuma.

Duas mitigações obrigatórias, senão o rígido é insuportável:
  1. aponta o PROJETO DE TESTE afetado, para não rodar a suíte inteira;
  2. não repete o que já provou — teste verde mais novo que a última edição
     libera na hora.

Três travas para o portão não virar armadilha:
  * escape explícito do Rafael (anotado pelo hook do prompt) libera a vez;
  * no máximo 3 bloqueios por sessão — portão que nega para sempre é sessão
    travada, e travar o trabalho dele é pior que deixar passar;
  * indeterminado conta como NÃO provado (regra dele: "indeterminado aborta
    também") — mas sempre dizendo o que falta, nunca só recusando.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import estado  # noqa: E402

MAX_BLOQUEIOS = 3
AFIRMACOES = ("testado", "validado", "funcionando", "passou", "suíte verde", "suite verde", "tudo verde", "está pronto", "esta pronto")


def _projeto_de_teste(arquivo: str) -> str:
    """Comando de teste mais estreito que cobre o arquivo editado."""
    p = Path(arquivo)
    if p.suffix.lower() in (".ts", ".tsx", ".js", ".mjs"):
        return "npm test  (ou `ng test --include <caminho>` para estreitar)"

    csproj = None
    for pasta in [p.parent, *p.parents]:
        achados = sorted(pasta.glob("*.csproj"))
        if achados:
            csproj = achados[0]
            break
    if not csproj:
        return "dotnet test"

    nome = csproj.stem
    if nome.endswith((".Tests", ".Test", "Tests")):
        return f'dotnet test "{csproj}"'

    # src/X -> test/X.Tests (o padrão dos repos daqui)
    raiz = csproj.parent.parent.parent if "src" in {q.name.lower() for q in csproj.parents} else csproj.parent.parent
    for pasta_teste in ("test", "tests"):
        for sufixo in (".Tests", ".Test", ".UnitTests"):
            cand = raiz / pasta_teste / f"{nome}{sufixo}" / f"{nome}{sufixo}.csproj"
            if cand.is_file():
                return f'dotnet test "{cand}"'
    return f"dotnet test  (não achei o projeto de teste de {nome}; rode o mais próximo)"


def main() -> int:
    try:
        d = json.loads(sys.stdin.read() or "{}")
    except Exception:
        return 0

    sessao = d.get("session_id", "")
    est = estado.ler(sessao)
    edicao = est.get("ultima_edicao")
    if not edicao:
        return 0  # nada de código foi editado nesta sessão

    # escape explícito do Rafael, mais novo que a edição, libera a vez
    escape = est.get("escape")
    if escape and escape.get("ts", 0) >= edicao.get("ts", 0):
        estado.anotar(sessao, escape=None, bloqueios=0)
        return 0

    if int(est.get("bloqueios") or 0) >= MAX_BLOQUEIOS:
        # já barrei três vezes: o problema não é desatenção, é dificuldade.
        # Deixo passar e digo em voz alta que está passando sem prova.
        estado.anotar(sessao, bloqueios=0)
        sys.stdout.reconfigure(encoding="utf-8")
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "Stop",
            "systemMessage": (
                "PORTÃO DESISTIU: barrei 3 vezes e o teste continua sem prova de verde. "
                "Estou liberando o encerramento, mas o trabalho NÃO está verificado — "
                "diga isso ao Rafael com essas palavras."
            ),
        }}, ensure_ascii=False))
        return 0

    teste = est.get("ultimo_teste") or {}
    ts_edicao = edicao.get("ts", 0)
    ts_teste = teste.get("ts", 0)
    ok = teste.get("ok")
    arquivo = edicao.get("arquivo", "")
    comando = _projeto_de_teste(arquivo)

    motivo = None
    if ts_teste < ts_edicao:
        motivo = (
            f"você editou `{Path(arquivo).name}` e NENHUM teste rodou depois disso."
            if not teste else
            f"o último teste rodou ANTES da sua edição em `{Path(arquivo).name}` — ele não prova nada sobre ela."
        )
    elif ok is False:
        motivo = f"o último teste rodou depois da edição e FALHOU (`{teste.get('comando','')}`)."
    elif ok is None:
        motivo = (
            f"o teste rodou (`{teste.get('comando','')}`), mas a saída não permite concluir que passou. "
            "Indeterminado não é verde."
        )

    if not motivo:
        # verde provado depois da última edição: não repito o que já foi provado
        estado.anotar(sessao, bloqueios=0)
        return 0

    sensor = est.get("sensor_reprovou")
    extra = ""
    if sensor and sensor.get("ts", 0) >= ts_teste:
        extra = f"\n\nE tem sensor reprovado em aberto: {sensor.get('resumo','')[:300]}"

    afirmou = [a for a in AFIRMACOES if a in (d.get("last_assistant_message") or "").lower()]
    if afirmou:
        extra += (
            f"\n\nATENÇÃO: sua última mensagem afirma \"{afirmou[0]}\" sem prova que sustente. "
            "Afirmação de prova precisa apontar o comando e a saída."
        )

    n = int(est.get("bloqueios") or 0) + 1
    estado.anotar(sessao, bloqueios=n)

    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "Stop",
        "permissionDecision": "deny",
        "permissionDecisionReason": (
            f"PORTÃO DO MOTOR (v6) — não encerre ainda: {motivo}{extra}\n\n"
            f"Rode agora, só o que cobre o que você mexeu:\n    {comando}\n\n"
            "Se falhar, conserte a causa — não desabilite o teste, não silencie o aviso "
            "e não relaxe a asserção. Se passar, diga o resultado com o número.\n"
            f"(bloqueio {n} de {MAX_BLOQUEIOS}. O Rafael libera dizendo \"termina assim mesmo\".)"
        ),
    }}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # portão que quebra não pode travar a sessão: em dúvida, libera
        sys.exit(0)
