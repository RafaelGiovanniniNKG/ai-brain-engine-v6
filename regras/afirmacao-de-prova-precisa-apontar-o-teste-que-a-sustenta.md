---
rule: Afirmacao de prova em doc de estado (ou em comentario de codigo) precisa apontar o teste que a sustenta - senao ela e uma divida disfarcada de garantia
origin: sessao 2026-08-10, retomada da POC cqrs-reference-architecture - o docs/ESTADO.md tinha QUATRO afirmacoes de prova falsas, e uma classe prometia num comentario um teste que nunca existiu
projects: all
confidence: 0.85
confidence_origem: alta (quatro ocorrencias independentes no mesmo documento, todas do mesmo tipo)
status: active
complementa: "canario-prova-que-a-sonda-le-nao-que-ela-reporta", "grep-para-provar-ausencia-precisa-dos-dois-lados", "caso-de-golden-precisa-poder-falhar"
---

## A regra

Num documento cuja funcao e dizer em que se pode confiar, **afirmacao de prova e a linha mais perigosa do
arquivo** — porque quem le decide, a partir dela, o que NAO precisa verificar.

Toda frase da forma "isto tem teste", "verificado", "os tres estao cobertos", "N testes contra M alvos"
precisa poder ser resolvida para **um arquivo e um nome de teste**. Se nao dá, ou a frase muda, ou o teste
nasce. Vale igual para comentario de codigo que descreve o teste que protege a classe.

## O que aconteceu

Retomando a POC, o pedido era corrigir **uma** afirmacao desatualizada no `ESTADO.md` ("o CI nunca foi
executado" — tinha executado). Conferindo o resto contra o repo, apareceram outras tres, todas do mesmo
tipo:

| Afirmava | Realidade |
|---|---|
| "O CI nunca foi executado" | Rodou; tres trilhas verdes, e os dois commits seguintes eram os defeitos que ele achou |
| "9 testes identicos contra **3** transportes" | Contra **2**. O terceiro transporte nao tinha um unico teste funcional |
| "Os **tres** timeouts tem teste travando o tempo" | Dois tinham, e eram de comportamento. O terceiro nao tinha nenhum |
| "`SocketTimeout` ajustado **apenas** no fixture de caos" | Estava em producao tambem — quem descobriu foi o teste novo |

E o caso mais instrutivo estava no **codigo**, nao no doc: a classe `IntegrationEventFactory` explicava que
o caso nao mapeado levanta excecao "e e o que faz o teste falhar em vez de o evento desaparecer". **Esse
teste nao existia.** A defesa estava escrita, o raciocinio estava certo, e ninguem tinha fechado o ciclo — a
excecao so acenderia se alguem tropecasse nela em producao, que e o modo de falha que ela existe para evitar.

Nenhuma das quatro era mentira deliberada. Todas foram verdade *de intencao* no momento em que foram
escritas, e nenhuma tinha como envelhecer visivelmente.

## Como aplicar

1. **Ao escrever a afirmacao**, cite o alvo: "`TimeoutConfigurationTests` trava os valores" em vez de "os
   tres tem teste". Nome de teste apodrece de forma ruidosa — um `grep` que nao casa mais e um sinal; uma
   frase generica nao tem como reprovar.
2. **Ao retomar um doc de estado, audite as afirmacoes de prova antes de confiar nelas** — e comece pelas
   que contam ("N testes", "os tres", "verificado"). Custa um `grep` por afirmacao e derruba o pior tipo de
   suposicao herdada.
3. **Comentario que descreve um teste e uma promessa executavel.** Se o comentario diz "o teste pega isso",
   `grep` pelo teste. Comentario e o unico lugar onde uma prova inexistente soa mais convincente que no
   doc, porque esta ao lado do codigo.
4. **Prefira pagar a divida a corrigir a frase.** Nas quatro, escrever o teste faltante foi mais barato que
   discutir a redacao — e o `ClockSkew`, que nao tinha nem teste de valor nem de comportamento, saiu coberto
   em 20 linhas.
5. **Quando a afirmacao nao puder ser provada agora, diga isso na propria linha.** "Analise de codigo e
   documentacao; o emulador nao foi subido para medir" e uma frase honesta e util. "Nao ha emulador" era
   falsa e fazia a proxima pessoa descartar o caminho sem olhar.

## Corolario

Um doc de estado tem duas populacoes de frase: as que descrevem **decisao** (envelhecem bem, porque a
decisao ou vale ou foi revogada) e as que descrevem **prova** (envelhecem em silencio, porque o mundo muda
sem avisar o arquivo). Na retomada, trate as primeiras como contexto e as segundas como hipoteses.
