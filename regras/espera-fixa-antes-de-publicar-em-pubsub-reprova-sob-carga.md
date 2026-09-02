---
rule: Em teste de pub/sub, espera fixa antes de publicar nao deixa o teste lento - ela o REPROVA sob carga, porque publicacao sem assinatura e descartada. Espere a condicao, e faca da espera uma pre-condicao do objeto
origin: sessao 2026-08-10, POC cqrs-reference-architecture - um Task.Delay(2s) fixo antes de publicar tornava DeadLetter_vai_para_quarentena intermitente no runner do CI, e o sintoma apontava para a quarentena
projects: all
confidence: 0.85
confidence_origem: alta (reprovou num runner e passou no seguinte sem mudanca de codigo; a correcao fechou a corrida por construcao e o CI ficou verde)
status: active
complementa: "instrumentacao-de-medicao-precisa-de-caso-canario", "canario-prova-que-a-sonda-le-nao-que-ela-reporta", "skip-em-massa-e-concorrencia-da-execucao-nao-orfaos"
---

## A regra

Espera fixa antes de uma acao assincrona costuma ser tratada como divida de elegancia — "funciona, so nao e
bonito". Em **pub/sub e o contrario**: como mensagem publicada sem assinatura registrada e **descartada**, a
espera curta demais nao produz lentidao nem falha tardia. Ela produz **teste que reprova**, e so quando a
maquina esta carregada.

Troque por espera de **condicao**, e prefira que a espera seja **pre-condicao do objeto**: se o unico jeito
de obter a assinatura for por um construtor que ja espera, nao ha como esquecer de esperar.

## O que aconteceu

A bateria de contrato do transporte tinha, antes de cada publicacao:

```csharp
private static Task AguardarAssinaturaAsync() => Task.Delay(TimeSpan.FromSeconds(2));
```

com um comentario correto ao lado, explicando que publicar antes de a assinatura existir descarta a mensagem.
Local, sempre verde. No primeiro runner de CI, `DeadLetter_vai_para_quarentena` reprovou; no runner seguinte,
**passou sem nenhuma mudanca de codigo**.

O diagnostico era barato — estava escrito no proprio harness — mas o **sintoma apontava para o lugar errado**:
"Esperava 1 mensagem em quarentena, encontrei 0". Quem le isso vai investigar dead-letter, politica de
tentativas e o broker. A causa estava a trinta linhas de distancia, num `Task.Delay`, e o transporte nao
tinha defeito algum.

A correcao: uma mensagem de **sondagem** republicada em laco ate atravessar o caminho completo ate o consumo,
e so entao o teste publica o que vai medir. Detalhes que fizeram diferenca:

- **A sondagem precisa ser filtrada antes do handler do teste.** Sem isso ela contaria como entrega, gastaria
  tentativa e entraria na quarentena — quebrando justamente os testes que afirmam sobre contagem.
- **Observar a Task do consumo dentro do laco.** Se assinar falha, o erro aparece como "a mensagem nao
  chegou" no fim do teste, com a excecao real engolida pela Task de segundo plano.
- **`AssinarAsync` devolvendo a assinatura ja pronta** eliminou a categoria do erro: nao existe mais o estado
  "assinei mas ainda nao esperei".

Dois ganhos que nao eram o objetivo: o teste de "publicacao sem assinatura e descartada" ficou **mais forte**
(antes, "nao chegou nada" se confundia com "a assinatura ainda nao estava pronta"), e a falha passou a nomear
qual assinatura de qual destino nao ficou pronta.

## Como aplicar

1. **Nunca `Task.Delay` fixo antes de publicar** num transporte com semantica de descarte. Se a espera for
   inevitavel, ela e um bug com prazo, nao um detalhe de estilo.
2. **Sonde com trafego real, nao com introspeccao do broker.** Uma sondagem que percorre o mesmo caminho da
   mensagem verdadeira funciona igual em todos os transportes, e dispensa um ponto de extensao por broker —
   que foi a razao pela qual a correcao chegou a ser considerada caso pesado.
3. **Filtre a sondagem por tipo reservado** e responda `Completed` antes do handler sob teste.
4. **Faca canario da propria sondagem.** Mutar o tipo publicado deve reprovar por timeout da sondagem,
   nomeando destino e assinatura. Sem esse canario, uma sondagem que nunca falha e indistinguivel de uma
   espera vacua.
5. **Cancele o consumo no fim do teste.** Descartar o `CancellationTokenSource` sem cancelar deixa cada laco
   vivo ate o fim da colecao, segurando recurso no broker — vazamento que so aparece como lentidao difusa.

## Corolario

Teste intermitente cujo diagnostico "e obvio quando se olha" costuma ser exatamente o que ninguem olha,
porque o sintoma aponta para outro lugar. O sinal de que a correcao e a certa nao e o teste voltar ao verde —
e o **modo de falha mudar de endereco**: passar a acusar a etapa que realmente nao aconteceu.
