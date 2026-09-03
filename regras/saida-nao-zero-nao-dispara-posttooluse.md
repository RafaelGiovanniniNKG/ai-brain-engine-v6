---
id: saida-nao-zero-nao-dispara-posttooluse
projects: all
confidence: 1.0
last_confirmed: 2026-09-03
origin: 2026-09-03 — o motor escutava só `PostToolUse` e ficou CEGO a toda execução vermelha. Medido com o mesmo texto de comando duas vezes: `exit 0` gravou o registro, `exit 1` não gravou nada. Isso abre falso verde — teste do projeto A reprova sem deixar rastro, teste do projeto B passa, e o portão libera.
status: active
---
Comando com saída **não-zero** não dispara `PostToolUse`: dispara `PostToolUseFailure`, e a saída
dele vem em `error`, não em `tool_use_result`. Sonda que escuta só o evento de sucesso mede
apenas o que deu certo — e "não vi falha" se lê como "não houve falha".
