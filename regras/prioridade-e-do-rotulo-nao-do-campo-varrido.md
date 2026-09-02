---
id: prioridade-e-do-rotulo-nao-do-campo-varrido
projects: all
confidence: 0.7
last_confirmed: 2026-08-19
status: active
origin: bot-email (2026-08-19), camada 1 de regras de triagem — a montagem do golden set revelou a falha antes de qualquer execução real
complementa: "caso-de-golden-precisa-poder-falhar"
---
Quando várias regras podem casar a mesma entrada, a prioridade é do **RÓTULO** (da consequência),
não do **CAMPO** varrido: varra todos os campos e resolva do erro mais caro para o mais barato.
Varredura campo-a-campo com `return` no primeiro casamento esconde o sinal de maior consequência
atrás do sinal do campo que veio primeiro.

**Esperado:** um remetente automático que pede assinatura seria classificado como `acao`
**Aconteceu:** a varredura era campo a campo (remetente, depois assunto). `noreply@govbr` com
assunto "Documento aguardando assinatura" casava `ruido` no **remetente** e nunca chegava ao
assunto — a regra arquivava exatamente o que pedia ação.

## Por que passa despercebido

A ordem dos campos parece uma decisão de implementação (é só o `for` de fora), enquanto a ordem
dos rótulos parece a decisão de negócio. É o contrário: **a ordem dos campos É a política**, e
uma política que ninguém escolheu. No código, os dois laços aninhados são simétricos; no efeito,
não são.

Some ainda mais fácil quando o campo "errado" é o mais barato de olhar. Remetente é uma string
curta e casa rápido, então é natural varrer primeiro — e é justamente o campo com o sinal mais
fraco.

## Como aplicar

1. **Inverta os laços:** o laço de fora é o do rótulo, em ordem de consequência; o de dentro
   varre os campos. `for label in PRIORIDADE: for campo in campos:` — nunca o oposto.
2. **Escreva a ordem de consequência como constante nomeada**, com o motivo ao lado. Se a ordem
   vive implícita na sequência de `if`s, a próxima pessoa reordena sem saber o que está mudando.
3. **Pergunte por par de rótulos: quanto custa confundir A com B, e B com A?** Se as duas
   respostas não forem iguais, existe ordem obrigatória e ela precisa estar codificada. Rótulos
   com custo simétrico podem ficar em qualquer ordem — e é bom dizer isso também.
4. **Teste o caso que casa DOIS rótulos ao mesmo tempo**, com o de maior consequência no campo
   varrido por último. Sem esse caso, a suíte fica verde com a ordem errada: cada rótulo isolado
   funciona, e o conflito é o único cenário que discrimina.
5. **Configuração explícita do usuário fica acima da prioridade automática.** Uma lista que a
   pessoa escreveu é decisão dela, não sinal a ser ponderado.

## Corolário genérico

Vale para qualquer resolução de conflito por varredura: roteamento por regras, precedência de
CSS artesanal, matching de permissões, seleção de handler, triagem de alerta. **Quando duas
dimensões podem decidir (o QUE casou e ONDE casou), a que tem consequência assimétrica tem de
ser a de fora.** Se você não sabe qual delas é a de fora no seu código, é porque ela foi
escolhida pela ordem em que você digitou.
