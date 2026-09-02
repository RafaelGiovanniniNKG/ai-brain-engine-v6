---
rule: Em PowerShell, `Write-Output` dentro de funcao E parte do valor de retorno - atribuir o resultado ENGOLE o relatorio
origin: sessao 2026-08-04, Onda 7 (bloco Colaborador/usuario) do OperationalManagement - `$x = Caso ...` apagou o relatorio de 6 casos, incluindo os DOIS canarios, e o mesmo defeito reapareceu no script de limpeza 20 minutos depois
projects: all
confidence: 0.85
confidence_origem: alta (dois sintomas completamente diferentes, mesma causa, no mesmo dia)
status: active
complementa: "canario-prova-que-a-sonda-le-nao-que-ela-reporta", "instrumentacao-de-medicao-precisa-de-caso-canario"
---

## A regra

Em PowerShell **nao existe** "imprimir" separado de "retornar": tudo que uma funcao escreve no stream de
saida compoe o valor de retorno. Logo:

* `$x = MinhaFuncao ...` **captura o relatorio junto com o dado** — e a saida desaparece da tela e do
  transcript, sem erro nenhum;
* uma funcao que imprime um rotulo e devolve uma lista devolve **rotulo + lista**, e o consumidor recebe o
  rotulo como **primeiro elemento**.

Numa funcao que precisa relatar **e** devolver, escolha um:
1. devolva por **variavel de escopo de script** (`$script:ultimaResp = $r`) e deixe o stream para o relato;
2. relate por `Write-Host`/`Write-Information` (que nao entram no stream de saida) e devolva pelo stream;
3. nao relate dentro da funcao — imprima no chamador.

## O que aconteceu

Roteiro de medicao de 63 casos. A funcao `Caso` imprimia o bloco do caso (metodo, payload, status, corpo,
consulta de verificacao, delta da trilha) **e** devolvia a resposta HTTP, para o chamador extrair o id
gerado. Seis casos precisavam desse id, e por isso foram escritos como `$fA = Caso 'F1' ...`.

**Esses seis casos sairam do transcript inteiros.** Sem excecao, sem aviso, sem linha vazia — apenas nao
existiam. Os outros 57 apareceram normalmente, o que fazia a medicao parecer completa.

O agravante: entre os seis estavam **os dois casos-canario** (`F1` e `E1`) e o caso que media o achado
central do bloco na entrada (`E2`: campos enviados no payload que o legado descarta). O canario existe para
provar que o instrumento enxerga o sistema — e ele foi **uma das vitimas** do defeito. Um canario nao pode
validar o mecanismo que o apaga.

**Vinte minutos depois, o mesmo defeito no script de limpeza**, com sintoma irreconhecivel: uma funcao
`CarregarPks($arquivo, $rotulo)` que imprimia `"baseline de PKs Employee: 23"` e devolvia o array de PKs.
O rotulo virou o elemento `[0]` da lista, foi interpolado num `IN (...)` de SQL e o banco respondeu
**`Conversion failed when converting from a character string to uniqueidentifier`** — um erro que nao
menciona nem funcao, nem retorno, nem PowerShell.

## Como aplicar

1. **Toda funcao que imprime NAO pode ter o retorno atribuido.** Se voce escreveu `$x = f ...` e `f`
   imprime, ha um bug — mesmo que o codigo funcione (`$x.Prop` ainda resolve, por enumeracao de membro, e
   foi isso que escondeu o defeito por uma execucao inteira).
2. **Ao instrumentar medicao, conte os casos.** O roteiro deve imprimir `casos executados: N` e voce deve
   conferir que N casos aparecem no transcript. Ausencia silenciosa nao dispara nada.
3. **Desconfie de erro de tipo vindo de lista construida por funcao.** "conversao falhou para
   uniqueidentifier/int" numa lista de ids costuma ser um rotulo que entrou no array.
4. **`return ,$lista`** resolve a enumeracao do array/DataTable, **nao** resolve o rotulo impresso — sao
   dois problemas distintos que se parecem.
5. Quando o defeito aparece **duas vezes com sintomas diferentes**, registre a causa e nao o sintoma: o
   proximo sintoma vai ser um terceiro.
