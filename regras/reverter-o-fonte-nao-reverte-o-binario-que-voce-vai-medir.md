---
rule: Reverter o FONTE de uma mutacao nao reverte o BINARIO - recompile antes de medir, e confira o artefato certo
origin: sessao 2026-08-04, Onda 8 (Grupo B) do OperationalManagement - medi o sync contra um bin que ainda carregava a mutacao da prova por mutacao, e quase reportei "validado" tendo medido o LEGADO
projects: all
confidence: 0.85
confidence_origem: alta (a medicao inteira saiu invalida, e o unico sinal foi a trilha cair na tabela errada)
complementa: "reverter-mutacao-de-teste-nao-e-git-checkout", "canario-prova-que-a-sonda-le-nao-que-ela-reporta"
status: active
---

## A regra

Prova por mutacao tem **quatro** passos, nao tres: mutar → rodar → **reverter o fonte** → **RECOMPILAR**.
Rodar o teste da mutacao **compila** a solucao com ela; reverter o arquivo depois deixa o fonte certo e o
**artefato errado**. Qualquer medicao seguinte roda o codigo mutado.

E ao conferir se o rebuild pegou, confira **o artefato que carrega a mudanca**, nao o executavel. Um `.exe`
nao e relinkado quando so um assembly de dependencia muda — o timestamp dele fica parado e parece que nada
aconteceu (ou que tudo esta atualizado, o que e' pior).

## O que aconteceu

Prova por mutacao de uma guarda de DI: troquei um registro para apontar de volta ao handler legado, rodei o
teste (ficou vermelho, como devia), e reverti o fonte gravando os bytes originais — com `git status`
confirmando. Correto ate ai.

Vinte minutos depois subi a API e medi um sync de 5 filiais contra o DEV. **O `bin` ainda tinha a mutacao.**
O handler legado rodou, a trilha foi para a tabela `StoredEvent` em vez do Outbox, e 40 referencias + 48
veiculos entraram no banco pelo caminho antigo.

**O que denunciou:** um cruzamento que eu quase nao fiz — conferir **onde** a trilha caiu. `StoredEvent +41` e
`Outbox 0` era o oposto exato do esperado. E a composicao fechava com a mutacao ser **so no Create**: as 41
linhas eram 40 `CreateReferenceEvent` + 1 `UpdateReferenceEvent`, todas do Create legado (que levanta Update
no ramo de upsert). Sem esse cruzamento, o relatorio teria sido "sync validado" — sobre uma execucao do
legado.

**O que NAO denunciou:** o timestamp do `Api.exe`. Ele estava em 13:44 antes e depois, porque o projeto do
executavel nao mudou — so o assembly de DI. Eu conferi o artefato errado e concluí "nao recompilou", quando a
verdade era "recompilou o que importava, e eu olhei outra coisa".

## Como aplicar

1. **Recompile depois de reverter**, sempre, antes de qualquer medicao. Trate o rebuild como parte do
   desfazer, nao como passo separado.
2. **Confira o artefato que carrega a mudanca.** Mudou a camada de DI? Olhe o DLL da camada de DI no `bin` de
   quem vai rodar. Mudou um handler? Olhe o DLL dele. O `.exe` so muda quando o projeto dele muda.
3. **Toda medicao precisa de um cruzamento que distinga "codigo novo rodou" de "codigo velho rodou"**, e ele
   tem de ser independente do resultado que voce quer. Aqui foi a TABELA onde a trilha caiu: o legado escreve
   em `StoredEvent`, o slice no Outbox. Um numero de linhas criadas nao distinguiria — os dois criam.
4. Se o sistema tem duas implementacoes vivas do mesmo verbo durante a coexistencia, **essa dicotomia e o seu
   melhor canario**. Meca-a em toda execucao, nao so quando desconfiar.
5. Prefira mutar em worktree separado, ou reverter+rebuild na mesma sequencia de comandos, para que nao exista
   janela em que o fonte e o binario discordam.
6. **Em container, recriar nao e reconstruir.** `docker compose up -d api` recria o container a partir da
   IMAGEM que ja existe, sai com zero e escreve `Started` — e sobe o binario de antes da sua mudanca. So o
   `--build` reconstroi. Em 2026-08-18, no Service Desk, isso custou tres execucoes de E2E: a consulta de
   leitura tinha ganhado tres colunas novas, o teste media a API antiga, e o vermelho dizia que o dado nao
   estava na tela — uma frase que descreve exatamente o defeito que a fatia acabara de corrigir.

## Corolario generico

**"Revertido" e uma afirmacao sobre o fonte; "vou medir" e uma pergunta sobre o binario.** Entre os dois ha um
compilador, e ele so age quando alguem o chama.
