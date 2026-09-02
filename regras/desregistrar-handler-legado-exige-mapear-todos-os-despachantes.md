---
rule: Antes de desregistrar um handler legado do DI, mapear TODOS os despachantes do command — não só a rota
origin: sessao 2026-08-03, Onda 5 (bloco Referencia) do OperationalManagement — dois workers de producao despachavam os mesmos commands que a rota
projects: all
confidence: 0.85
confidence_origem: alta (o erro apareceu nos dois sentidos na mesma sessao: contar DI superestimou, contar rota criou um falso orfao)
status: active
complementa: "evento-legado-no-op-ainda-grava-no-event-store", "grep-para-provar-ausencia-precisa-dos-dois-lados"
---

## A regra

"Migrei a rota, logo posso desligar o handler legado" só vale quando a rota é o **único** despachante. Antes
de remover um registro de DI, procure `new XxxCommand` **e** `Map<XxxCommand>` em todo o repositório, fora de
testes. Um handler pode ter chamadores que nenhum controller revela: workers, jobs, sincronizadores,
backfills, outros AppServices.

E o inverso também: **falta de rota não é falta de chamador.** Para declarar um registro órfão, exija os
**dois** lados — sem rota **e** sem despachante.

## O que aconteceu

Nas ondas 1–4 o handler legado sempre tinha um único chamador (a rota), e desregistrar era seguro. Na onda 5,
`Reference` e `Vehicle` tinham a rota **mais** dois `BackgroundService` de produção, num projeto separado
(`SiStocklerServiceOrder.Worker`) que chama o **mesmo** `NativeInjectorBootStrapper.RegisterServices` da API —
ou seja, compartilha o grafo de DI inteiro. Desregistrar teria parado o sincronizador AgroSync em produção.
Pior: vários desses `SendCommand` não são awaited em métodos `void`, então a exceção "no handler registered"
viraria uma `Task` faulted não observada — **falha silenciosa**.

No mesmo bloco, o erro apareceu **espelhado**: um levantamento anterior contou `IRequestHandler<...>` no DI e
superestimou o escopo (registro de DI não é rota); a correção passou a contar rotas — e criou um falso órfão,
porque `Vehicle.Delete` não tem rota mas tem dois chamadores internos vivos.

## Como aplicar

1. Por command, rode a busca nos **dois** padrões de construção (`new XxxCommand`, `Map<XxxCommand>`) em todo
   o repo, excluindo testes. A lista de despachantes é o insumo; a rota é só um deles.
2. Se houver despachante fora da rota, o verbo **não é** "trocar legado por novo": ou o handler legado fica
   registrado (dois caminhos de escrita vivos no mesmo agregado, com o custo de divergirem), ou os
   chamadores internos entram no escopo. **Isso é decisão do usuário, não detalhe de implementação** — muda o
   tamanho da onda.
3. Verifique se workers compartilham o container de DI da API (procure a chamada ao bootstrapper no
   `Program.cs` de cada projeto executável). Compartilhar significa que uma remoção atinge processos que você
   não está testando.
4. Suspeite de `SendCommand` não-awaited em método `void`: ali a ausência de handler não estoura, **silencia**.
5. Ao afirmar "órfão", escreva a evidência dos dois lados na mesma linha: "sem rota **e** sem despachante".
   Só um dos lados é meia-prova.
