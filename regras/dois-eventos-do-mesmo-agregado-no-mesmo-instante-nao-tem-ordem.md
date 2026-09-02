---
id: dois-eventos-do-mesmo-agregado-no-mesmo-instante-nao-tem-ordem
projects: Projeto-SiStockler.ServiceDesk, POC-cqrs-reference-architecture
confidence: 0.9
status: active
last_confirmed: 2026-08-14
origin: ServiceDesk (2026-08-14) — `dbo.SlaPolicies.Padrao=1` e `read.SlaPolicies.Padrao=0`; a API respondia que NAO havia politica padrao enquanto a escrita dizia que havia. Quinta ocorrencia da familia "gravado e nunca lido" no mesmo dia.
---
Um caso de uso que CRIA um agregado e logo em seguida MUDA o mesmo agregado levanta dois eventos com o
mesmo `OccurredAt`. Se o despacho ordena so por tempo e a projecao so guarda por tempo, **nenhuma das
duas camadas sabe qual veio depois** — e o que a tela mostra vira sorteio.

**Esperado:** criar a politica com `padrao: true` deixa a leitura com `Padrao = 1`
**Aconteceu:** `SlaPolicy.Criar` levantava `SlaPolicyChanged(Padrao: false)` e o handler chamava
`DefinirComoPadrao(true)` em seguida, levantando um segundo evento. Os dois saiam do outbox com
`OccurredAt` identico ate o ultimo digito (`12:59:54.2896390`), o `ORDER BY OccurredAt` do
`SqlOutboxStore` nao tinha desempate, e o guarda `LastEventAt <= @quando` da projecao deixava os dois
passarem. Venceu o `false`. **O estado do agregado sempre esteve certo** — so a leitura errava.

## Como aplicar

1. Quando um handler cria e ja ajusta o mesmo agregado, passar o estado final para a **fabrica**, para
   que exista UM evento. Ajustar depois so e seguro quando o segundo evento nasce em outra transacao,
   num instante posterior (o caminho de "promover uma politica que ja existe" continua valido).
2. Mudar OUTROS agregados na mesma transacao nao tem esse problema — `subjectId` diferente, projecao
   diferente. O empate so existe entre eventos do MESMO sujeito.
3. O teste que guarda isso conta EVENTOS, nao estado. `Assert.True(politica.Padrao)` passa igual no
   codigo defeituoso, porque a escrita nunca esteve errada; o que denuncia e `Assert.Single(eventos)`.
4. Ao investigar divergencia escrita/leitura, comparar os `OccurredAt` do outbox para o mesmo
   `subjectId` ANTES de suspeitar do handler. Timestamps iguais sao a assinatura deste defeito.

## Corolario generico (vale fora deste repo)

**Relogio nao e ordem.** Ordenar eventos por tempo so funciona enquanto os tempos forem distintos —
e dois eventos da mesma transacao quase sempre nao sao. Onde a ordem importa de verdade, ela precisa
de uma sequencia monotona (identity/versao do agregado), nao de um `DateTimeOffset`. Enquanto essa
sequencia nao existir, a regra pratica e **nao produzir o empate**: um evento por agregado por
transacao.
