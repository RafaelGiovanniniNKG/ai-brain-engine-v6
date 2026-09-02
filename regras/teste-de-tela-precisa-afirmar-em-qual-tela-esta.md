---
rule: Teste de tela precisa afirmar EM QUAL tela esta antes de afirmar o conteudo - navegacao que nao acontece nao levanta erro
origin: sessao 2026-08-18, fatia "o ativo aparece no chamado" do Service Desk - o clique no menu nao navegou, o teste seguiu medindo a tela anterior, e a mensagem de falha apontou para o produto
projects: all
confidence: 0.85
confidence_origem: alta (dois casos na mesma execucao, e nos dois a falha relatada era sobre o conteudo, nunca sobre a navegacao)
complementa: "coletor-que-nao-casa-nada-parece-sistema-que-nao-fez-nada", "canario-prova-que-a-sonda-le-nao-que-ela-reporta"
status: active
---

## A regra

`click()` num link de navegacao **passa** mesmo quando a navegacao nao acontece: o Playwright promete que
achou e clicou o elemento, e nao que o roteador levou a algum lugar. Depois disso o teste continua rodando
contra a tela ANTERIOR, e a falha aparece muitos passos adiante, com o texto de uma asserção de conteúdo:

```ts
await irPara(page, 'Abrir chamado');          // clicou. nao navegou. verde.
await expect(page.getByRole('combobox').first()).toBeVisible();   // a tela ANTERIOR tambem tem combobox
await expect(page.getByLabel('Equipamento')).toHaveCount(1);      // vermelho, "0 elements"
```

O vermelho diz *"o equipamento nao esta na lista"* — uma frase sobre o produto. O defeito era o teste estar
na tela errada. **Depois de cada navegacao, afirme a URL** (`await expect(page).toHaveURL(/\/abrir$/)`), ou
navegue por `goto` quando a rota e conhecida.

E o agravante: **nao use, para reconhecer a tela, um texto que existe nas duas.** A palavra "Equipamento" é
o rotulo do seletor na tela de abertura E o titulo do bloco na tela do chamado. A primeira asserção passou
na tela errada, e só a segunda falhou — o que deslocou a suspeita para o dado.

## O que aconteceu

Duas vezes na mesma execucao, na mesma fatia:

1. `irPara(page, 'Abrir chamado')` a partir de `/admin/ativos` nao navegou. O `page.reload()` seguinte
   recarregou o cadastro de ativos, e o teste passou 45 segundos reconsultando um `<select>` que **so existe
   na outra tela**, relatando `0 elements`. O que denunciou foi o *page snapshot* do relatorio, onde estava
   o texto "Máquina, sala, equipamento — o que um chamado pode apontar": a descricao da tela de administracao.
2. Corrigido o primeiro, o clique em "Ver o chamado" tambem nao levou ao detalhe, e a retentativa passou a
   recarregar o formulario de abertura recem-esvaziado. Dessa vez o locator resolveu para um `<option>`
   **oculto** com o nome da maquina — a lista do formulario — e o relatorio disse `Received: hidden`.
   "Hidden" era a pista: no detalhe aquele nome e um paragrafo, nunca uma opcao de select.

Com `await expect(page).toHaveURL(/\/chamados\/[0-9a-f-]{36}$/)` no lugar, a falha passou a aparecer **no
passo da navegacao**, e a correcao levou 1 execucao em vez de 3.

## Como aplicar

1. Toda navegacao — clique em menu, botao que chama `router.navigate`, redirecionamento esperado — termina
   com uma asserção de URL. Uma linha.
2. Quando a rota e conhecida e estavel, prefira `page.goto('/abrir')` a clicar no menu. Testar o menu é
   um teste PROPRIO, e nao um pre-requisito silencioso de todos os outros.
3. Guarde a URL (`const endereco = page.url()`) e faça a retentativa com `goto(endereco)`, nao com
   `reload()`: `reload()` repete a pagina em que você **está**, que é justamente o que está em duvida.
4. Escolha o texto-ancora da tela por **exclusividade**, nao por conveniencia. Se a palavra aparece em duas
   telas do fluxo, ela nao serve para dizer onde você está.
5. Quando um `toPass` estoura, leia o `error-context.md` inteiro antes de mexer no produto: o *page snapshot*
   diz em que tela o teste morreu, e `hidden` versus `not found` distingue "elemento de outra tela" de
   "elemento que nao existe".
