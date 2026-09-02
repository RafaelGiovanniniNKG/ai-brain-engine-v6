---
id: evento-legado-no-op-ainda-grava-no-event-store
projects: Projeto-SiStockler.OperationalManagement, Projeto-SiStockler.ControleEmbalagem
confidence: 0.5
last_confirmed: 2026-07-30
status: active
origin: migracao-operacional Onda 2 Passo 4 (2026-07-30) — afirmei "nada se perde" ao desligar os eventos legados do CleaningSector; o csharp-reviewer achou que o RaiseEvent também gravava em StoredEvent
---
"O handler do evento legado e no-op" NAO e o mesmo que "o evento legado nao fazia nada". Antes de escrever
"nada se perde" ao desligar um `INotificationHandler` legado, SEGUIR O `RaiseEvent` ATE O FIM — nos templates
DDD deste time ele tem DOIS efeitos, e o segundo nao aparece em nenhum handler.

**Esperado:** desligar eventos cujos handlers sao no-op puro nao remove nada observavel
**Aconteceu:** o `InMemoryBus.RaiseEvent` tambem chamava `_eventStore.Save(@event)`, que serializava o evento
INTEIRO + e-mail do usuario e fazia `Add` + `SaveChanges` numa tabela de event store. Cada verbo legado
bem-sucedido deixava uma linha la; os slices migrados deixam zero. Atravessou ~19 verbos sem aparecer porque
NENHUM teste da suite olhava aquela tabela.

## Como aplicar

1. Ao desligar um evento legado, abrir a implementacao do **bus**, nao so os handlers. Procurar por
   `_eventStore`, `Save(`, `Store(`, `SaveChanges` no caminho de `RaiseEvent`/`Publish`.
2. Comparar o que a trilha NOVA guarda com o que a ANTIGA guardava, campo a campo. Trilha por evento de
   dominio enxuto (`id`, `flag`, `OccurredOn`) e mais pobre em VALORES do que a serializacao do evento legado
   completo, mesmo quando e melhor em distinguir VERBOS.
3. Se nenhum teste olha a tabela antiga, a diferenca e invisivel por construcao — escrever o saldo honesto no
   ledger e levar a decisao ao usuario, em vez de declarar equivalencia.

## Corolario generico (vale fora deste repo)

**"Nada se perde" e uma afirmacao de COBERTURA, e cobertura precisa de evidencia.** Se nenhum teste observa o
efeito que voce esta removendo, voce nao pode afirmar que ele nao existia — so que ninguem olhava.
