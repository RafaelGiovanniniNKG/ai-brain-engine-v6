---
id: pasta-de-dados-do-plugin-nao-e-localappdata
projects: all
confidence: 1.0
last_confirmed: 2026-09-03
origin: 2026-09-03 — fui medir se sub-agente compartilha identidade de sessão, olhei `%LOCALAPPDATA%\ai-brain-engine-v6` (que só tinha resíduo de teste) e conclui por dez minutos que os gatilhos não estavam disparando. Estavam: dentro de um processo de hook o Claude Code define `CLAUDE_PLUGIN_DATA`, e o estado real estava em `~\.claude\plugins\data\<id>\ai-brain-engine-v6\`.
status: active
---
Dentro de um processo de hook o Claude Code define `CLAUDE_PLUGIN_DATA` (`~/.claude/plugins/data/<id>/`),
então componente que resolve a pasta por variável de ambiente grava **num lugar diferente** do que
você vê ao rodar o mesmo código na mão. Antes de concluir "não mediu nada", ache a pasta que o
processo de verdade usou — pasta vazia é sintoma de estar olhando a errada, não de ausência.
