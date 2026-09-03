#!/usr/bin/env python
"""Dispara o destilador — e sai na hora.

Serve três eventos, com papéis diferentes:
  * `Stop` (600 s de orçamento) é o gatilho PRIMÁRIO, com intervalo mínimo de 10
    minutos entre disparos;
  * `PreCompact` é ponto de checagem — o que for compactado não volta;
  * `SessionEnd` é tentativa final, e só isso: tem 1,5 s de orçamento
    compartilhado e há sete defeitos registrados de ele ser morto no meio,
    inclusive um em que hooks de plugin não disparam nesse evento.

Por isso a documentação NÃO depende do fim de sessão. Se o encerramento não
disparar, o `Stop` da última resposta já escreveu.

O filho é gerado de verdade destacado: no Windows, gerar filho pelo caminho
comum a partir do encerramento faz o Claude Code esperar a árvore inteira de
processos e ignorar o timeout — a sessão trava na saída.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import estado  # noqa: E402

DESTILADOR = Path(__file__).resolve().parent.parent / "captura" / "destilar.py"
INTERVALO_STOP_SEG = 600


def main() -> int:
    # A sessão que o destilador abre para resumir NÃO pode disparar outro
    # destilador: sem esta marca o motor documenta a si mesmo, e num dia ruim
    # documenta em laço.
    if os.environ.get("V6_FILHO"):
        return 0
    try:
        d = json.loads(sys.stdin.buffer.read().decode("utf-8", errors="replace") or "{}")
    except Exception:
        return 0

    sessao = d.get("session_id", "")
    evento = d.get("hook_event_name", "Stop")
    if not sessao or not DESTILADOR.is_file():
        return 0

    est = estado.ler(sessao)
    if not est:
        return 0

    if evento == "Stop":
        if time.time() - float(est.get("diario_ts") or 0) < INTERVALO_STOP_SEG:
            return 0
        if estado.assinatura(est) == est.get("diario_assinatura"):
            return 0

    bandeiras = 0
    if sys.platform == "win32":
        # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW
        bandeiras = 0x00000008 | 0x00000200 | 0x08000000

    try:
        subprocess.Popen(
            [sys.executable, str(DESTILADOR), "--sessao", sessao, "--motivo", evento],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=bandeiras, close_fds=True,
            start_new_session=(sys.platform != "win32"),
        )
    except Exception:
        pass
    return 0  # sempre imediato: documentação não atrasa resposta


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
