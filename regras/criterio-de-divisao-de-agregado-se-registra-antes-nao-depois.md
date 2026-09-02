---
rule: Criterio de divisao de agregado se registra ANTES de a abstracao existir, e precisa ser falsificavel
origin: sessao 2026-08-11, Onda 5 do SiStockler.ServiceDesk (tipos e campos dinamicos) — portao registrado antes de escrever a abstracao
projects: all
confidence: 0.6
confidence_origem: media (regra preventiva; o custo de nao te-la e conhecido, o beneficio ainda nao foi colhido)
status: active
complementa: "afirmacao de prova precisa apontar o teste que a sustenta"
---

## A regra

Quando voce decide **generalizar** — um tipo configuravel, um agregado que atende dois casos, uma
abstracao que ainda tem um consumidor so —, escreva **antes** a condicao que faria voce desfazer a
generalizacao. Ela precisa ser **contavel**, com uma **data de verificacao**.

Depois nao funciona, e o motivo nao e disciplina: depois de a abstracao existir, todo caso novo
parece caber nela. Cabe mesmo — abstracao boa acomoda. O que se perde e a capacidade de perceber
que ela virou duas coisas com um nome so, porque o critério passa a ser negociado contra o custo
de refazer.

## Por que "falsificavel" e o adjetivo que importa

"Dividimos se ficar complexo demais" nao e criterio: nao ha estado do mundo que o torne falso.
Serve para encerrar a discussao, nao para decidir.

Um criterio util tem tres partes:

1. **Contagem**, nao impressao — "≥3 campos obrigatorios exclusivos", nao "muitos campos proprios".
2. **Quorum**, quando ha varios sinais fracos — "duas destas tres", porque um sinal isolado
   costuma ser ruido e tres simultaneos costumam chegar tarde demais.
3. **Momento de verificar**, marcado num ponto do plano que vai acontecer de qualquer jeito — "ao
   fim da Onda 6". Sem isso o critério existe e ninguem o consulta.

## O caso concreto que originou a regra

O plano do service desk aceitou um risco declarado: **abstracao de tipo prematura**. Um `Ticket`
configuravel atende "incidente de TI" e "parada de maquina", e as duas podem nao ser a mesma coisa
— a duracao da parada e valor de negocio (MTTR, minutos perdidos), ha unicidade entre instancias, e
o "solicitante" e uma maquina.

Criterio registrado ANTES de a Onda 5 escrever a abstracao:

> Divide-se `Ticket` em `ProductionStop` se, **ao fim da Onda 6**, DUAS destas forem verdadeiras:
> (a) ≥3 campos obrigatorios exclusivos de parada;
> (b) ≥2 transicoes exclusivas de parada;
> (c) ≥1 invariante de parada que exija LER outro chamado.

O item (c) e o mais forte dos tres e vale explicar: invariante que precisa ler outro agregado e o
sintoma classico de fronteira errada. "No maximo uma parada aberta por ativo" e exatamente isso — e
esta no plano desde o inicio.

**De-risking que torna o criterio barato de exercer:** a projecao absorve a divisao (uma colecao
com discriminador). Dividir o lado de escrita nao forca fork no Angular nem no Flutter. Foi essa
escolha que permitiu aceitar o risco em vez de decidir cedo.

## Como aplicar

1. Antes do commit que cria a abstracao, registre o critério — arquivo versionado, nao conversa.
2. Escreva **onde** ele sera verificado, e prefira um marco que ja existe no plano.
3. Escreva o **de-risking**: o que voce fez hoje para que dividir amanha custe pouco. Se nao houver
   nada, o critério e teatro — voce nao vai dividir, e sabe disso.
4. Na data marcada, **conte**. Se o quorum bateu, divida; se nao bateu, registre a contagem e siga.
   Registrar a contagem que NAO bateu e o que impede a mesma discussao de voltar em tres meses.
5. Se voce nao consegue escrever o critério, isso e informacao: significa que nao sabe o que
   distingue os dois casos — e generalizar sem saber o que se esta unindo e o modo mais caro de
   descobrir.
