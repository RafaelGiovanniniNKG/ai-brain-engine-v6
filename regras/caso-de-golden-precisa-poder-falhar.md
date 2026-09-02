---
rule: Todo caso de golden precisa de estado inicial que permita a asserção FALHAR
origin: sessao 2026-08-03, Onda 4 (bloco Incendio) do OperationalManagement — dois casos furados na PRIMEIRA gravacao
projects: all
confidence: 0.85
confidence_origem: alta (dois casos independentes, na mesma gravacao, ambos "verdes" medindo nada)
status: active
complementa: "golden ausente e FALHA; divergencia aprovada tem de EXIGIR o valor de ORIGEM"
---

## A regra

Antes de gravar um golden, para cada caso pergunte: **com o comportamento OPOSTO, este caso ficaria
diferente?** Se a resposta for "nao", o caso nao mede nada — e vai ficar verde para sempre.

Um caso de golden tem tres partes que podem furar independentemente: o **payload**, o **estado inicial**
(seed) e a **rota**. A revisao normalmente olha o payload e esquece o seed.

## Os dois casos que furaram (achados pela EXECUCAO, nao por revisao)

**1. O caso da FK orfa nao chegou na FK.** O caso "Create com `FireExtinguisherTypeId` inexistente" usava
como PK um id **ja semeado**. A pre-checagem de **duplicidade** do handler responde 422 **antes** de o
insert chegar ao banco — o caso media a duplicidade, nao a FK, e o titulo dizia FK. Passava verde.
Correcao: id exclusivo do caso (`IdParaTipoOrfao`), documentado no proprio campo.

**2. O caso da bandeira nao provou a bandeira.** O achado central do bloco era "o Delete grava `Active =
true`, isto e, ATIVA a linha". A linha semeada nascia com `Active = true`. Depois do Delete ela continuava
`true` — e "continuava" era o **estado inicial**, nao o efeito do verbo. Correcao: semear `Active = false`,
com o motivo escrito no seed.

## Como aplicar

1. Para cada caso, escreva no comentario **o que ele distingue**. Se a frase nao tiver um "em vez de",
   provavelmente o caso nao discrimina nada.
2. **Bandeira/estado:** semeie sempre o valor **contrario** ao que o verbo deve gravar. Semear igual e' o
   modo classico de um teste de bandeira nascer decorativo.
3. **Caso que exercita a camada N:** garanta que nenhuma checagem da camada N-1 dispara primeiro
   (duplicidade antes de FK, validator antes de handler, `[ApiController]` antes do pipeline). Um caso que
   mede "o erro errado" e' pior que caso ausente: ele documenta uma garantia que nao existe.
4. Prefira **um id exclusivo por caso** a reaproveitar seeds. Reaproveitar acopla casos e faz a ordem do
   roteiro virar contrato implicito.
5. Depois de gravar, **releia o golden como evidencia**, nao como saida: para cada linha, o que ela proibiria
   se alguem quebrasse o codigo? Foi essa releitura que achou os dois casos aqui.
