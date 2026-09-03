#!/usr/bin/env python
"""Devolve as regras vivas ao modelo quando elas caem do contexto.

O furo: quando a conversa fica longa, o programa a RESUME e joga o começo fora
— e o começo é justamente onde o motor injetou as regras aprendidas. Elas
desaparecem no meio do trabalho, em silêncio, e o modelo segue sem saber que
existiam. Numa sessão longa, que é onde o erro caro acontece, o motor fica
mudo exatamente quando mais deveria falar.

Por que não dá para resolver no lugar óbvio:
  * `SessionStart` **não** dispara depois de um resumo (dispara em início,
    retomada, limpeza e bifurcação).
  * `PostCompact` dispara, mas **não pode injetar contexto** — só observar.

Então são dois passos, e é por isso que este arquivo existe:
  1. `PostCompact` só ANOTA que houve resumo (`--marcar`).
  2. `UserPromptSubmit`, que PODE injetar, devolve as regras no próximo pedido
     do Rafael e dá baixa na marca (`--injetar`). Uma vez por resumo, não a
     cada mensagem: repetir o mesmo bloco a cada turno gastaria contexto para
     dizer o que já foi dito.

`PostModelSwitch` usa `--injetar` direto, porque esse evento PODE injetar e
porque trocar de modelo é o momento em que menos se pode supor que o novo
modelo herdou as instruções. É também a "reauditoria a cada modelo novo" que o
Passo 7 do plano pedia e que só existia como lembrete no papel.

Nunca levanta e nunca bloqueia: se algo falhar aqui, a sessão segue sem a
reinjeção, que é ruim mas não é quebrado.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import estado  # noqa: E402
import session_start as inicio  # noqa: E402

# Só o texto muda entre os dois motivos; o bloco é o mesmo.
CABECALHO = {
    "resumo": (
        "REGRAS DO MOTOR (v6), DEVOLVIDAS — a conversa foi resumida e o começo dela saiu "
        "do contexto, junto com estas regras. Elas continuam valendo: cada uma nasceu de "
        "uma falha real medida neste ambiente, não de preferência de estilo."
    ),
    "modelo": (
        "REGRAS DO MOTOR (v6), DEVOLVIDAS — o modelo desta sessão mudou, e não se pode "
        "supor que o novo herdou as instruções do anterior. Cada regra abaixo nasceu de "
        "uma falha real medida neste ambiente."
    ),
}


def _entrada() -> dict:
    try:
        return json.loads(sys.stdin.read() or "{}")
    except Exception:
        return {}


def _marcar(d: dict) -> int:
    """Anota que houve resumo. Quem injeta é o próximo pedido do Rafael."""
    estado.anotar(d.get("session_id", ""),
                  contexto_perdido={"ts": time.time(),
                                    "motivo": d.get("compaction_reason") or "resumo"})
    return 0


def _injetar(d: dict, motivo: str) -> int:
    bloco = inicio.montar_bloco(d.get("cwd", ""), so_as_regras=True)
    if not bloco:
        return 0
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": d.get("hook_event_name") or "UserPromptSubmit",
        "additionalContext": CABECALHO.get(motivo, CABECALHO["resumo"]) + "\n\n" + bloco,
    }}, ensure_ascii=False))
    return 0


def main() -> int:
    modo = sys.argv[1] if len(sys.argv) > 1 else "--auto"
    d = _entrada()

    if modo == "--marcar":
        return _marcar(d)

    if modo == "--injetar":
        return _injetar(d, "modelo")

    # --auto: no pedido do Rafael, injeta SÓ se houver resumo pendente.
    sessao = d.get("session_id", "")
    pendente = (estado.ler(sessao).get("contexto_perdido") or {}).get("ts")
    if not pendente:
        return 0
    estado.anotar(sessao, contexto_perdido=None)  # baixa: uma vez por resumo
    return _injetar(d, "resumo")


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
