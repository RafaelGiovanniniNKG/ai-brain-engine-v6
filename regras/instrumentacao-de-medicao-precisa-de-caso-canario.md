---
rule: Roteiro de medição precisa de um caso-canário que FALHA se a instrumentação estiver quebrada
origin: sessao 2026-08-03, Onda 5 (bloco Referencia) do OperationalManagement — 43 casos medidos com a coluna "o que ficou gravado" vazia, e a execucao inteira teve de ser repetida
projects: all
confidence: 0.85
confidence_origem: alta (a instrumentacao falhou silenciosamente em 100% dos casos e nenhum caso reclamou)
status: active
complementa: "caso-de-golden-precisa-poder-falhar"
---

## A regra

Uma medição tem duas coisas que podem estar erradas: **o sistema medido** e **o instrumento**. O roteiro
verifica o primeiro. Nada verifica o segundo — a menos que você inclua um caso cuja resposta você já conhece
e que **falha alto** se o instrumento estiver mudo.

Sonda silenciosa é pior que sonda ausente: ela produz uma tabela cheia de "0 linha(s)" que se lê como
"o verbo não gravou nada", quando na verdade significa "eu não sei olhar".

## O que aconteceu

O script de medição consultava o banco depois de cada requisição para registrar o que ficou gravado. Três
bugs, todos no instrumento:

1. `return $t` de um `DataTable` em PowerShell é **enumerado** na saída — a função devolvia DataRows soltos e
   `.Rows` desaparecia. Toda linha "DB" saiu como `(nenhuma linha)`. Corrigido com `return ,$t`.
2. `ORDER BY Id DESC` sobre uma coluna `uniqueidentifier` **não ordena por tempo** — a lista de eventos novos
   por caso saía vazia mesmo com o delta acusando `+1`.
3. A limpeza dependia de um carimbo de texto no payload da trilha; o payload não continha o carimbo.

Os status HTTP e os corpos estavam corretos o tempo todo, o que tornou a saída **plausível**: 43 casos com
status certo e "nenhuma linha" gravada. O erro só apareceu porque um total agregado no fim do script
(`RD carimbo = 4`) contradisse os "(nenhuma linha)" individuais. Sem esse total, a medição teria sido
declarada válida — e o golden nasceria cego exatamente na dimensão que mais importa.

## Como aplicar

1. **Inclua um caso cuja resposta você já sabe** e que exercita o instrumento inteiro (requisição → consulta →
   formatação). Um caminho felizardo simples serve: se ele não mostrar a linha gravada, o instrumento está
   quebrado, não o sistema.
2. **Cruze granularidades.** Sempre imprima um total agregado no fim e confira contra a soma dos casos. Foi a
   única coisa que denunciou a falha aqui.
3. **Trate "vazio" como suspeito, não como resultado.** Antes de escrever "o verbo não gravou", prove que a
   sonda enxerga *algo* — de preferência no mesmo formato e no mesmo caso.
4. **Ordene por coluna temporal, nunca por chave opaca.** GUID, hash e id aleatório não têm ordem cronológica;
   `ORDER BY` neles compila, roda e mente.
5. Se o roteiro precisar ser repetido, conte o custo: estado intermediário por caso **não é reconstituível** do
   estado final. Instrumento errado custa a execução inteira — e efeitos irreversíveis (aqui, um `IDENTITY` que
   avançou 6 valores e não volta) acontecem duas vezes.
