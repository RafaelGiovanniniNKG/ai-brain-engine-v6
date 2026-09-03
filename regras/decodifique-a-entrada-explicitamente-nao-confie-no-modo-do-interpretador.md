---
id: decodifique-a-entrada-explicitamente-nao-confie-no-modo-do-interpretador
projects: all
confidence: 1.0
last_confirmed: 2026-09-03
origin: 2026-09-03 — o pedido "/v6-tarefa fechar ... o teste de licença declarada" foi gravado como `licenÃ§a` no estado de uma sessão REAL da POC, e daí foi para o diário. O motor declarava "UTF-8 explícito na saída" e tinha esquecido a ENTRADA: `sys.stdin.read()` decodifica com o padrão da máquina (cp1252 no Windows). Pior, o defeito não reproduzia testando na mão — o shell interativo roda com o modo UTF-8 do interpretador e o processo do gatilho não.
status: active
---
Decodifique a ENTRADA explicitamente (`sys.stdin.buffer.read().decode("utf-8")`), nunca pelo
padrão do interpretador: o modo UTF-8 pode estar ligado no seu shell e desligado no processo que
roda de verdade — então o acento corrompe em produção e o teste na mão passa verde. Quem declara
encoding na saída e não na entrada só resolveu metade.
