---
name: v6-ideia
description: Ajuda a tirar um projeto novo do papel ANTES de existir código — entende a ideia, faz as perguntas de negócio, discute honestamente se a ideia se sustenta, pesquisa o que é verificável, escreve as regras duras e o fatiamento em escada, e registra tudo como nota de visão no cofre. Use quando o Rafael disser que tem uma ideia, quiser definir negócio ou regras, ou quiser trocar ideia sobre se algo vale a pena. Não cria repositório e não escreve código.
---

# Uma ideia nova, antes de qualquer código

Esta skill existe para a fase em que não há repositório, não há stack e não há o que medir — só uma ideia e a pergunta honesta de se ela se sustenta. O produto dela é **uma nota de visão no cofre** e uma lista de decisões numeradas esperando resposta dele. Nada mais.

**Não faça aqui:** criar repositório, escolher stack, escrever código, escrever plano de construção. Plano é a próxima etapa e só nasce depois que a visão for aprovada — antes disso ele só compromete você com um desenho que a conversa ainda vai mudar.

O molde é o que ele já validou: `Projetos/ERP Varejo Fiscal/Ideia e Visão (…)`. Vale a pena abrir essa nota antes de escrever a primeira, para copiar a forma.

## O que o Rafael espera desta conversa

Ele **não** quer entusiasmo. Duas vezes o trabalho só ficou útil quando o argumento dele foi derrubado com medição: o desempenho não era o motivo para construir o mediator próprio, e o Blazor tinha má fama que pertencia a outro Blazor. Se a razão que ele dá para a ideia não se sustenta, **diga, com o que sustenta o contrário** — e continue ajudando a construir a ideia. Concordar por gentileza é o pior serviço possível aqui.

E ele já disse, com essas palavras, que não entende explicação por jargão quando o desenho é seu e não dele. Descreva o que acontece.

---

## Fase 1 — Devolver a ideia antes de opinar

Escute e **reformule em três a cinco linhas**: quem usa, que dor sente hoje, o que faz em vez disso, e o que muda com a ideia. Peça a confirmação de que você entendeu.

Isso não é formalidade. Ideia contada em voz alta costuma ter dois produtos dentro, e o resto da conversa vira confusão se você não separar os dois agora.

## Fase 2 — As perguntas, todas de uma vez

Uma rodada só, de 5 a 8 perguntas, juntas. **Nunca pingadas** — pergunta pingada faz ele responder a esmo e cansa antes da metade. Diga que ele pode responder as que quiser e pular as outras.

O que precisa estar coberto, adaptando ao caso:
- **Quem paga**, e não quem usa — às vezes não é a mesma pessoa.
- **O que a pessoa faz hoje** sem o produto. Planilha, caderno, concorrente, ou nada. Se a resposta é "nada", pergunte por que a dor não doeu o bastante até hoje.
- **Quanto custa a dor** para ela, em dinheiro ou em hora. Sem isso não há preço.
- **O diferencial em uma palavra**, e como você provaria essa palavra a um cético.
- **Os limites reais dele**: dinheiro que pode entrar, hora por semana, prazo, sozinho ou com alguém.
- **Amarras de fora**: lei, órgão regulador, certificação, contrato, licença.
- **A primeira venda concreta**: para quem, quando, por quanto.

## Fase 3 — Bater a ideia contra a realidade

Só aqui você pesquisa, e só o que é **verificável**: existe concorrente e quanto cobra, existe exigência legal, quanto custa o insumo, a biblioteca necessária tem licença que serve. Cada número no cofre vai com a fonte, e número que você não achou vai escrito como **estimativa**, com a conta à vista.

Duas regras da casa que valem desde a primeira linha:
- **Nada de dependência de núcleo com licença paga**, e nem "camada grátis" de produto pago. Ao citar biblioteca ou ferramenta, **verifique e declare a licença**.
- Custo recorrente conta por mês e por ano, não por unidade solta.

Depois, três blocos que a nota precisa ter e que ninguém escreve sozinho:

**O argumento mais forte contra.** Não a lista de riscos: o motivo pelo qual uma pessoa sensata diria "não faça". Escreva do jeito que ela diria.

**O que faria isso morrer.** A condição concreta, não "falta de mercado" — algo como "se o órgão X exigir Y, o produto inteiro para".

**Como saber em pouco tempo.** O teste mais barato que muda a resposta: uma conversa com um cliente real, um edital lido, uma planilha de custo, um protótipo de tela. Isso vale mais que qualquer parágrafo de análise, e é o que ele deve fazer antes de escrever a primeira linha de código.

## Fase 4 — Regras duras

Estas são as que valem mesmo, o que o produto **não pode** deixar acontecer, escritas de forma que dê para conferir depois. Não é regra de negócio no sentido de manual: é invariante — "venda nunca sai sem X", "o valor de Y nunca é recalculado depois de Z".

Separe do restante o **anti-escopo**: o que o produto de propósito não vai fazer na primeira versão. É a seção que mais evita retrabalho, e é a primeira que ele vai querer furar.

## Fase 5 — A escada

Fatiamento onde **cada degrau já dá dinheiro ou já ensina algo**, e não "fase 1 de 4 que só serve para a fase 2". Ele pensa assim naturalmente — na lanchonete a escada foi entrega de casa, depois carrinho, depois loja; no ERP foi Simples e um estado só antes de qualquer coisa maior. Copie esse jeito.

Para cada degrau: o que a pessoa consegue fazer, o que ele precisa ter pronto, e o sinal de que está na hora de subir.

## Fase 6 — Escrever no cofre

Confirme o nome do projeto com ele — a pasta vai carregar esse nome por anos.

```
Projetos/<Nome>/Ideia e Visão (<Nome>).md
Projetos/<Nome>/Pesquisas (<Nome>).md        # só se houve pesquisa com fonte
```

Frontmatter com `projeto`, `tipo: visão`, `criado_em`, `tags`. Seções, na ordem que ele já aprovou: a aposta e as decisões tomadas · o princípio que atravessa tudo · o formato do produto · as dores atacadas · a jornada de quem usa · as regras duras · a escada · o anti-escopo · riscos e verdades que não podem ser esquecidas · as decisões abertas · o estado do projeto com a data.

**Decisões abertas numeradas `R1`, `R2`, `R3`…**, uma pergunta por item, com as opções e a sua recomendação. É o formato que funcionou: ele responde por número e a nota registra a resposta com a data ao lado. Enquanto houver `R` sem resposta, o projeto não está pronto para plano.

Duas coisas sobre como escrever:
- **Sem marcas de versão.** Nada de "novo na v2", "o que mudou", coluna de situação, "antes previa outra coisa". Ele devolveu um documento inteiro por causa disso. A nota descreve o que é hoje.
- **Trabalho não decidido é pendência, nunca conclusão.** Se ele disse "acho que sim", a nota escreve "acho que sim", não "decidido".

## Fase 7 — Fechar

No chat, em poucas linhas: o que você entendeu, o argumento mais forte contra, o teste mais barato que muda a resposta, e as decisões `R` esperando ele. Diga onde a nota ficou.

Se ele aprovar a visão, o passo seguinte é a `v6-tarefa` no tamanho grande — especificação e plano de construção. **Quando o repositório nascer, registre o par repositório → pasta do cofre no `mapa.json` do motor**, senão a sessão dentro dele começa sem contexto nenhum e todo este trabalho fica invisível.
