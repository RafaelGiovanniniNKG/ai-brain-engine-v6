---
id: ligar-um-plugin-no-meio-da-sessao-nao-liga-os-gatilhos
projects: all
confidence: 0.9
last_confirmed: 2026-09-03
origin: 2026-09-03 — o `/plugin uninstall ecc@ecc` desligou o ai-brain-engine-v6 de tabela; religar por `settings.json` fez `claude plugin list` dizer `enabled` e o diagnóstico dizer "Tudo de pé", mas edição de `.ts` (minha e de sub-agente) não registrou NADA no estado. Só a sessão seguinte carrega os gatilhos.
status: active
---
Plugin religado no meio da sessão **não** tem gatilhos vivos nela: `claude plugin list` e o
diagnóstico leem a configuração, não o que a sessão carregou. Depois de mexer em plugin, abra
sessão nova antes de afirmar que o motor está medindo — e desconfie de pasta de estado vazia.
