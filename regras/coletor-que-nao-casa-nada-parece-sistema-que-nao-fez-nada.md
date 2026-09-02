---
rule: Um coletor de tráfego preso a host/porta fixa mede ZERO e se lê como "o sistema não fez nada"
origin: sessao 2026-08-04, E2E de UI do OperationalManagement — 6 specs vermelhos acusando a migracao; o defeito era o filtro
projects: all
confidence: 0.85
confidence_origem: alta (6 casos, 3 arquivos, todos com a mesma forma de falha, e todos verdes depois de trocar so o filtro)
complementa: "canario-prova-que-a-sonda-le-nao-que-ela-reporta"
status: active
---

## A regra

Teste que afirma "a tela disparou X" costuma capturar requests com um filtro por **host e porta**:

```ts
page.on('response', (r) => { if (r.url().includes('localhost:5000')) leituras.push(...) });
...
expect(leituras.some(l => l.includes('ReadPerformedChecklist'))).toBe(true);
```

Se a aplicação passar a falar em **outra porta**, o filtro casa zero, a lista fica vazia, e a mensagem que
aparece é exatamente a mesma de um sistema quebrado: *"a lista deve carregar por ReadPerformedChecklist:"* —
com o rodapé vazio. **Nada no vermelho distingue "não capturei" de "não aconteceu".**

Filtre pelo que é **estável no contrato** (o caminho `/api/v1/...`, o nome da rota), não pelo que é
configuração de ambiente (host, porta, esquema).

## O que aconteceu

6 dos 18 casos de E2E falhavam com `Received: 0` em `posts.length` / `escritas.length` / `leituras`. A leitura
natural era grave: a migração teria desligado as telas. O único caso do mesmo arquivo que **passava** era o que
usava `https://localhost:5041` — a porta que o `environment.ts` (valor commitado) manda o SPA chamar.

Os specs tinham sido escritos quando a API subia em `localhost:5000`. Trocar
`r.url().includes('localhost:5000')` por `/localhost:(5000|5041)\//.test(r.url())` levou os 6 a verde **sem
tocar em uma linha de produção**. Nenhum dos 6 tinha relação com a migração.

## Como aplicar

1. **Nunca** ancore captura em host/porta. Ancore no caminho da API ou no nome da rota — é o que o contrato
   promete, e é o que você está testando.
2. Se o filtro *tiver* de conhecer o ambiente, leia-o da MESMA fonte que a aplicação lê (o arquivo de
   environment), não de uma constante paralela no teste. Duas fontes divergem, e a que mente é sempre a do teste.
3. **Asserção de ausência precisa de um positivo ao lado.** Antes de afirmar "não disparou a rota Y", afirme
   "disparou alguma coisa": `expect(todasAsChamadas.length).toBeGreaterThan(0)`. Sem esse par, zero-por-filtro-
   errado e zero-por-sistema-quebrado são o mesmo vermelho.
4. Faça a mensagem de falha **imprimir o que foi capturado** (`${leituras.join(' | ')}`). Foi ver esse rodapé
   VAZIO — em vez de "capturei 12 chamadas, nenhuma era a Y" — que apontou o filtro em vez do produto.
5. Quando um subconjunto passa e o resto falha com a mesma forma, **compare os que passam com os que falham
   antes de investigar o produto.** Aqui a diferença estava em uma constante de porta, visível em um diff de
   duas linhas.
