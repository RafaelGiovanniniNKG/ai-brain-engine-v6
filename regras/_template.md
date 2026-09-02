---
id: _template
projects: all
confidence: 0.0
last_confirmed: 2026-01-01
status: template
origin: n/a — arquivo modelo, não é regra ativa
---
Modelo de regra viva (ratchet). Uma regra por arquivo; `status: template` é ignorado pelo loader
(só carrega `active`). Regra só nasce de **falha real registrada** — `origin` é obrigatório.
Texto imperativo, 1-3 linhas. Escopo em `projects` (`all` ou lista de repos-alvo).
