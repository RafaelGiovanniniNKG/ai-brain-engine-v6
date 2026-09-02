---
rule: Buffer ALUGADO guardado alem do callback le memoria de outra mensagem - e o vermelho intermitente que denuncia isso nao e ruido
origin: sessao 2026-08-18, ultimo dia do Service Desk - o penultimo push reprovou no CI com 1 falha em 165, num teste sem relacao com a mudanca, e era defeito real na mensageria
projects: all
confidence: 0.85
confidence_origem: alta (mecanismo confirmado por leitura do codigo, e o vermelho tinha assinatura inconfundivel - bytes zerados onde havia JSON)
complementa: "canario-prova-que-a-sonda-le-nao-que-ela-reporta", "coletor-que-nao-casa-nada-parece-sistema-que-nao-fez-nada"
status: active
---

## A regra

Cliente de mensageria moderno **aluga** o buffer do corpo de um pool e o **devolve quando o callback
de entrega retorna**. Guardar a `ReadOnlyMemory<byte>` num objeto que sobrevive ao callback faz esse
objeto apontar para memoria reciclada:

```csharp
// ERRADO: o envelope sobrevive ao callback, o buffer nao.
return new MessageEnvelope { Body = corpo, ... };

// CERTO: copia na fronteira, uma vez, onde o dono do buffer ainda e conhecido.
return new MessageEnvelope { Body = corpo.ToArray(), ... };
```

**A regra maior, que vale fora de mensageria:** quando uma API entrega memoria emprestada, a **copia
acontece na fronteira** — no mapeador, no adaptador, no lugar que conhece o dono. Empurrar a decisao
para quem consome espalha a armadilha por todos os consumidores, e basta um que guarde para depois.

E o corolario que custa mais caro: **um tipo que expoe `Body` como propriedade PARECE prometer que o
corpo continua valido.** Se ele nao copia, ele mente — e a mentira nao aparece em quem consome dentro
do callback, que e a maioria.

## O que aconteceu

O `AmqpEnvelopeMapper` do RabbitMQ guardava a memoria recebida sem copiar. Sobreviveu **98 commits**
porque quase todo consumidor termina dentro do callback de entrega. O unico codigo que guardava o
envelope para depois era o teste de contrato — que colocava o envelope num `TaskCompletionSource` e
afirmava o corpo em seguida:

```
Expected: "{"valor":42}"
Actual:   "\0<\0P\0\0\0\0\0\0\0^Z"
```

Reprovou **1 em 165**, num arquivo sem nenhuma relacao com a mudanca daquele push (um filtro de SQL).
Todas as tentacoes estavam alinhadas para descartar: teste "de infraestrutura", falha isolada, area
que ninguem tocou, e o projeto sendo encerrado naquele dia.

**Era defeito real.** Um teste que guardava o envelope era o unico consumidor honesto do contrato que
o tipo aparentava oferecer.

## Como aplicar

1. **Ao mapear qualquer entrega para um objeto proprio, pergunte de quem e o buffer.** Se a resposta
   for "do cliente" ou "de um pool", copie. RabbitMQ.Client aluga; `BinaryData.ToMemory()` do Azure
   Service Bus aponta para buffer proprio da mensagem e nao precisa. **Verifique, nao presuma por
   analogia entre transportes.**
2. **Escreva o porque na linha da copia.** `corpo.ToArray()` sem comentario e um convite a alguem
   "otimizar a alocacao" e reintroduzir o defeito — que volta intermitente e longe da causa.
3. **Vermelho intermitente nao e ruido por padrao.** Antes de reexecutar, leia a MENSAGEM: bytes
   zerados, valores de outra mensagem e strings truncadas sao assinatura de memoria reciclada, e nao
   de concorrencia de teste. Reexecutar esconde exatamente a classe de defeito que mais depende de
   tempo.
4. **Quando o canario nao e possivel, diga isso.** Falha temporal nao se reproduz sob demanda: mutar o
   codigo e ver verde nao absolve nada. Aqui a prova foi **leitura do codigo + assinatura do vermelho**,
   e o honesto e registrar assim, em vez de fingir uma reproducao.
5. **Suspeite do teste que "guarda para depois".** Ele costuma ser o unico que exercita a promessa que
   o tipo faz. Quando ele falha sozinho, a hipotese boa e que ele esta certo.

## Corolario generico

**Memoria emprestada tem prazo, e o prazo nao esta no tipo.** `ReadOnlyMemory<byte>` nao diz quanto
tempo aquele buffer e seu — quem sabe disso e a documentacao do cliente, e ela e lida uma vez, no dia
em que o adaptador foi escrito.
