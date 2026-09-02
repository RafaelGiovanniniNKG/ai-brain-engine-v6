---
rule: Veredito automatico que PRESUME o estado inicial reprova sucesso - compare contra o estado MEDIDO, e quando o inicial estiver sujo, refaca a medicao a partir de um estado limpo
origin: sessao 2026-08-07, milestone 10 (replay) da POC cqrs-reference-architecture - meu script de verificacao ao vivo imprimiu "FALHOU: a projecao REPROCESSOU. O inbox nao segurou", e o inbox estava perfeito; o que ele detectou foi a projecao SAINDO de um atraso que eu nao sabia que existia
projects: all
confidence: 0.85
confidence_origem: alta (o veredito era categorico, estava errado, e eu quase reportei "o milestone 10 falhou" para o usuario)
complementa: "canario-prova-que-a-sonda-le-nao-que-ela-reporta", "instrumentacao-de-medicao-precisa-de-caso-canario", "golden-valor-cumulativo-vira-delta-e-divergencia-que-move-exige-dois-lados"
status: active
---

## A regra

Quando o veredito e da forma **"este numero nao pode subir"**, ele carrega uma premissa escondida:
*o numero ja estava no valor certo antes*. Se o estado inicial estiver incompleto, atrasado ou sujo,
a correcao legitima faz o numero subir e o veredito grita FALHOU em cima de um sucesso.

Antes de escrever `if (depois != antes) { falhou }`, responda: **como eu sei que `antes` estava certo?**

- Se sei porque **medi** (e a medicao mostra o valor esperado), pode comparar.
- Se estou **presumindo** — porque a stack subiu, porque o teste passou antes, porque "deveria estar
  em dia" — o veredito nao vale. Ou meco o estado inicial e afirmo sobre ele, ou **refaco a operacao
  a partir de um estado que eu mesmo levei ao valor certo**.

O segundo caminho e quase sempre o melhor e o mais barato: **rode a operacao duas vezes.** A primeira
leva o sistema ao estado consistente (e pode mudar tudo, legitimamente); a segunda roda com tudo em
dia, e *ai* sim nada pode mudar. A segunda rodada e a prova limpa, porque a premissa passou a ser
fato observado em vez de suposicao.

E escolha o campo mais **delator** para afirmar, nao o mais obvio: prefira o acumulador que so cresce
(contador, soma) ao total de registros, porque o acumulador denuncia duplicacao mesmo quando a
contagem de itens continua igual.

## O que aconteceu

Milestone de replay: reenviar eventos ja publicados para que um assinante que entrou depois receba o
que passou. O reenvio vai para **todos** os assinantes, e a seguranca disso depende do inbox — cada
assinatura descarta o que ja processou. O teste do desenho era exatamente esse: *depois do replay, a
projecao nao pode ter reprocessado nada*.

Escrevi o script de verificacao ao vivo com o veredito direto:

```powershell
if ($depois.Proj -ne $antes.Proj) { "FALHOU: a projecao REPROCESSOU. O inbox nao segurou." }
```

Rodou, e imprimiu FALHOU. `projection` foi de 23 para 26, `documentos` de 14 para 16.

So que o inbox estava correto. O que eu nao sabia: **a projecao tambem estava atrasada**. A outbox
tinha 26 eventos publicados, a auditoria processara 15 e a projecao 23 — ela tinha perdido eventos
anteriores a sua propria criacao, um milestone antes, e nenhum documento do projeto registrava isso.
O replay corrigiu as duas assinaturas de uma vez. Os "2 documentos novos" eram clientes que nunca
haviam entrado na projecao.

Meu veredito codificou "23 e o valor certo" sem nunca ter verificado. A premissa era falsa, e a
conclusao saiu invertida: reportou quebra de garantia onde houve recuperacao.

A prova limpa veio de rodar o replay **de novo**, agora com as duas assinaturas em 26:

```
antes:  projection=26 audit=26 docs=16 itens=16 suspensoes=7
depois: projection=26 audit=26 docs=16 itens=16 suspensoes=7
```

26 eventos reentregues as duas assinaturas, nada mudou — incluindo `suspensoes`, que e o campo que
duplicaria primeiro, porque sobe incondicionalmente justamente por confiar no inbox. Ai sim o
veredito significa alguma coisa.

## Diretiva de prevencao

1. Para todo veredito do tipo "X nao pode mudar", escreva ao lado **por que X estava certo antes**.
   Se a resposta for uma suposicao, o veredito ainda nao existe.
2. Quando a operacao a ser provada e **idempotente** (replay, sync, reconciliacao, import), rode-a
   **duas vezes** e afirme sobre a segunda. A primeira estabelece a premissa; a segunda a testa.
3. Prefira afirmar sobre **acumuladores** (somas, contadores que so crescem) a afirmar sobre totais:
   duplicacao aparece neles mesmo quando a contagem de entidades nao muda.
4. Um veredito automatico que imprime FALHOU **nao encerra a investigacao** — ele a comeca. Antes de
   reportar falha ao usuario, explique cada numero que mudou. Se algum so faz sentido com uma
   premissa que voce nao mediu, o problema esta no veredito, nao no sistema.
