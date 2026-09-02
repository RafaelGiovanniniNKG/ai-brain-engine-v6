---
rule: Reverter uma mutacao de teste e a operacao INVERSA, nunca `git checkout` - e comparar strings nao prova restauracao byte a byte
origin: sessao 2026-08-04, Onda 6 (bloco Motorista) do OperationalManagement - um `git checkout --` apagou a migracao inteira de um controller nao commitado, e um WriteAllText "restaurado" removeu o BOM de outro arquivo
projects: all
confidence: 0.85
confidence_origem: alta (os dois erros aconteceram na MESMA prova por mutacao, um atras do outro)
status: active
complementa: "modo-de-gravacao-destrutivo-exige-filtro-de-um-teste", "canario-prova-que-a-sonda-le-nao-que-ela-reporta"
---

## A regra

Para provar que uma guarda morde, voce muta o codigo, roda, e desfaz. **O desfazer e a parte perigosa.**

1. **`git checkout -- <arquivo>` nao e "desfazer minha ultima edicao", e "voltar ao HEAD".** Num arquivo com
   trabalho **nao commitado**, ele apaga o trabalho — silenciosamente, sem confirmacao, sem reflog.
   Reverta pela **operacao inversa**: guarde o conteudo original em memoria antes de mutar e reescreva-o.
2. **Comparar strings nao prova restauracao byte a byte.** `ReadAllText` **nao devolve o BOM** e
   `WriteAllText` com `UTF8Encoding(false)` **nao o reescreve**. Um `$restaurado -eq $original` pode dar
   `True` com o arquivo alterado no disco. Para conferir de verdade, compare **bytes** — ou pergunte ao
   `git status`, que ve o que a comparacao de string nao ve.

## O que aconteceu

Prova por mutacao de uma guarda de contrato ViewModel→command. Dois erros em sequencia:

**(a)** A primeira mutacao removeu um campo do mapeamento num controller. Para desfazer, usei
`git checkout -- DriverDataController.cs` — e aquele arquivo tinha a **migracao inteira do controller** ainda
nao commitada. O checkout devolveu o arquivo ao legado: perdeu o `ISender`, as tres actions migradas e os
comentarios. O que pegou o erro foi o `[Obsolete(error: true)]` **na interface** do AppService legado: tres
`CS0619` no build seguinte, apontando exatamente as chamadas que tinham voltado. Sem essa guarda — que
existia por causa de um review anterior — a perda teria ido para o commit.

Bonus: aquela mutacao nem testava a guarda. Os commands sao `record` posicionais com todos os parametros
obrigatorios, entao **omitir um campo no controller e erro de compilacao**, nao falha de teste. A mutacao
correta era outra: acrescentar um campo **novo** ao ViewModel — que e' justamente o cenario que a guarda
existe para pegar (outra frente acrescenta o campo, a action o descarta, nada reclama).

**(b)** A segunda mutacao (a correta) foi revertida com `WriteAllText` do conteudo original e conferida com
`$conf -eq $orig` → **`True`**. Mesmo assim o `git status` mostrava o arquivo **modificado**: o original tinha
BOM (`EF BB BF`), a string lida nao o continha, e a regravacao o descartou. O diff era uma linha de ruido de
encoding num arquivo que nao pertencia ao commit.

## Como aplicar

1. Antes de mutar, **leia e guarde** o conteudo original numa variavel. Reverta gravando-o de volta.
2. Preserve o encoding: detecte o BOM lendo **bytes** (`ReadAllBytes`, checar `EF BB BF`) e reescreva com
   `UTF8Encoding($true)` se ele existia. Ou mute com uma ferramenta que preserve o encoding.
3. **Confira com `git status`/`git diff`, nao com igualdade de string.** O git compara bytes; a string, nao.
4. Prefira mutar arquivos **sem trabalho nao commitado**. Se nao der, aceite que o unico desfazer seguro e a
   operacao inversa.
5. Escolha a mutacao que o **teste** pega, nao a que o **compilador** pega. Se o build quebra, voce provou
   que o C# tem tipos — nao que a guarda funciona. Pergunte: "que mudanca compila e passa despercebida?"
6. Mantenha guardas de compilacao (`[Obsolete(error: true)]`) mesmo quando parecem redundantes: aqui uma
   delas foi a unica coisa entre um `git checkout` distraido e um commit com codigo revertido.
