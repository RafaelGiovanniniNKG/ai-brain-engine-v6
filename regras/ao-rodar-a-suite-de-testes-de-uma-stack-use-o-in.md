---
id: ao-rodar-a-suite-de-testes-de-uma-stack-use-o-in
projects: all
confidence: 0.7
last_confirmed: 2026-07-09
status: active
origin: iabrain-v5-sandbox run #1 (2026-07-09): validate.py deu BLOQUEADO falso porque 'python' nu nao tinha pytest
---
Ao rodar a suite de testes de uma stack, use o interpretador/binario correto do ambiente (ex.: sys.executable para pytest), nunca o nome nu que pode cair em stub da store ou faltar libs.

**Esperado:** validate --run-tests reflete o resultado real dos testes do alvo
**Aconteceu:** 'python -m pytest' nu falhou por falta de pytest no interpretador ambiente -> falso VERMELHO
