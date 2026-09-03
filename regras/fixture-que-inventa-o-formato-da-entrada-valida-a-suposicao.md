---
id: fixture-que-inventa-o-formato-da-entrada-valida-a-suposicao
projects: all
confidence: 1.0
last_confirmed: 2026-09-03
origin: 2026-09-03 — a prova do portão alimentava `tool_use_result` como STRING; o Claude Code manda LISTA de blocos `{"type","text"}`. O código fazia `json.dumps` da lista, virava uma linha só com `\n` escapado, e os padrões ancorados em `^...$` nunca casavam: em toda sessão real o registro saía com `evidencia: ""`. A prova passava porque o fixture devolvia a própria suposição.
status: active
---
Fixture que **inventa** o formato da entrada não testa o integrador: testa a suposição de quem o
escreveu, e passa verde enquanto a produção não grava nada. Antes de escrever o caso, capture uma
entrada REAL do produtor e derive o fixture dela.
