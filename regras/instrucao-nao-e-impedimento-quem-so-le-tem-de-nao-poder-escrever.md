---
id: instrucao-nao-e-impedimento-quem-so-le-tem-de-nao-poder-escrever
projects: all
confidence: 1.0
last_confirmed: 2026-09-03
origin: 2026-09-03 — a skill de revisão declarava "não commita e não altera código — é só leitura", e a medição mostrou o contrário: pedi a um revisor que rodasse `printf ... > arquivo.txt` e ele escreveu no repositório, sem recusa e sem pedido de permissão. Ele tem acesso ao terminal porque precisa rodar `git diff`, e pelo terminal se escreve. Declarar o padrão no `tools` do agente foi aprovado pela conferência oficial e NÃO restringiu nada.
status: active
---
Papel que "só lê" precisa **não poder** escrever, não ser instruído a não escrever: instrução é
intenção e portão é medição. E a restrição vale como LISTA DE PERMITIDOS — lista de proibidos falha
aberta, porque basta uma forma que você não imaginou (`tee`, `python -c`, um script) para a escrita
passar. Falhar fechado custa uma reclamação; falhar aberto custa código alterado por quem só devia
opinar. Ver [[afirmacao-de-prova-precisa-apontar-o-teste-que-a-sustenta]].
