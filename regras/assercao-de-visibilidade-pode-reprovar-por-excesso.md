---
id: assercao-de-visibilidade-pode-reprovar-por-excesso
projects: all
confidence: 0.9
status: active
last_confirmed: 2026-08-17
origin: Service Desk web (2026-08-17) — `auditoria.spec.ts` reprovava intermitente com "toBeVisible() failed". A causa nao era ausencia: o locator resolvia para DOIS elementos, e o strict mode do Playwright recusa locator ambiguo.
---
`toBeVisible()` que reprova **nem sempre reprova por ausencia**. Em Playwright, um locator que casa
com mais de um elemento e recusado por strict mode, e a mensagem comeca igual — "toBeVisible()
failed". Diagnosticar pela primeira linha leva a procurar o elemento que falta, quando o problema e
que ele **aparece duas vezes**.

**Esperado:** o teste reprovava porque a trilha ainda nao tinha o fato (consistencia eventual)
**Aconteceu:** a trilha tinha o fato DUAS vezes, de origens diferentes — abrir o chamado ja definia
atendente quando o tipo reaproveitado tinha grupo padrao, e a acao do teste gerava o segundo. Os
dois com horario e rastro distribuido proprios. Zero duplicacao no banco: o dado estava certo, o
locator e que era ambiguo.

## Como aplicar

1. Ler a mensagem INTEIRA antes de diagnosticar. "resolved to 2 elements" muda completamente o que
   se procura, e vem depois da linha que todo mundo le.
2. Instabilidade que **passa isolada e reprova na suite** e quase sempre estado global: outro teste
   criou algo que muda o comportamento do seu. Aqui, um tipo de chamado reaproveitado com grupo
   padrao passou a atribuir atendente na abertura.
3. **Nao resolver com `.first()`.** Ele silencia a ambiguidade e enfraquece a afirmacao: passa a
   valer mesmo que a acao do proprio teste nao tenha registrado nada. A saida e ancorar num fato que
   SO a acao do teste produz.
4. Antes de mexer no teste, conferir se o duplicado e legitimo. Se o mesmo identificador de mensagem
   aparecer duas vezes, ai sim e defeito de deduplicacao — e o conserto e outro.

## Corolario generico (vale fora deste repo)

**Uma assercao existe para falhar por UM motivo, e "encontrei demais" e um motivo diferente de "nao
encontrei".** Quando os dois produzem a mesma primeira linha de erro, o diagnostico rapido erra — e
o conserto rapido (`.first()`, `nth(0)`, relaxar o seletor) transforma um teste que estava tentando
dizer algo num teste que nao diz mais nada.
