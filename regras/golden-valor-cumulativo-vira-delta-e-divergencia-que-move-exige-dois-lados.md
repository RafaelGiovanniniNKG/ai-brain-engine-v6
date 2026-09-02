---
rule: No transcript de golden, valor cumulativo vira DELTA; e divergencia que MOVE um valor exige reportar os DOIS lados
origin: sessao 2026-08-03, Onda 4 (bloco Incendio) do OperationalManagement
projects: all
confidence: 0.85
confidence_origem: alta (os dois defeitos apareceram no mesmo transcript e o segundo cegava justamente a correcao aprovada)
status: active
complementa: "GOLDEN: valor sentinela precisa de rotulo proprio; divergencia aprovada tem de EXIGIR o valor de ORIGEM"
---

## A regra

**(a) Nunca reporte total acumulado num transcript de golden.** Reporte o **delta do caso**. Um total faz
cada caso carregar a soma de todos os anteriores: inserir um caso no meio do roteiro desloca os numeros de
todos os seguintes, e a diferenca aparece em N linhas que nada tem a ver com a mudanca. O golden deixa de
ser evidencia e passa a ser custo de manutencao — que e' como um golden morre (regravado no automatico).

**(b) Quando a divergencia aprovada MOVE um valor de um lugar para outro, o transcript tem de reportar os
DOIS lugares.** Reportar so a origem faz o lado novo desaparecer da evidencia, e o "0" do lado antigo fica
**indistinguivel de nao ter gravado nada**.

## O caso (b), que e' o perigoso

No bloco Incendio, o legado montava a linha de log com o `Guid.Empty` do command e a trilha nascia **ORFA**
(apontando para uma PK que nao existia). A divergencia aprovada foi: a trilha passa a apontar a **PK real**.

O transcript consultava o log **so em `Guid.Empty`**:

| | legado | slice |
|---|---|---|
| `LOG em Guid.Empty` | `1 linha(s) aponta=ORFAO` | `0 linha(s)` |

Esse `0` do slice seria **exatamente o mesmo** se o slice tivesse **deixado de gravar a trilha**. Ou seja: o
golden ficava cego no unico ponto que a decisao do usuario mandava consertar. Corrigido reportando os dois
lados (`em Guid.Empty ->` e `na PK ->`), o legado prova o orfao (**1 / 0**) e o slice prova a correcao
(**0 / 1**).

## Como aplicar

1. Toda contagem no transcript e' **delta por caso** (`+N`), nunca total.
2. Liste as divergencias aprovadas ANTES de escolher o que o transcript reporta. Para cada uma que **move**
   um valor (de coluna, de tabela, de campo do corpo), reporte **origem e destino** no mesmo transcript.
3. Na lista fechada de divergencias, prefira **MOVER o valor capturado do golden** a reescreve-lo: assim a
   substituicao afirma "o mesmo registro, agora no lugar certo" em vez de "algum registro em algum lugar".
4. Corrigir o formato do transcript **exige regravar o golden com o LEGADO religado** (`git stash` do write
   path novo, regravar com `GOLDEN_RECORD=1`, `git stash pop`). Regravar com o codigo novo ativo transforma a
   comparacao em espelho — e' o mesmo erro que a regra do "valor de ORIGEM" existe para pegar.
5. Um teste **AO LADO** cobre o que o golden nao pode: onde o legado grava zero (aqui, `OutboxMessage`), o
   golden congela um zero e nao diz nada sobre o conteudo novo — o `Action` e a contagem tem de ser MEDIDOS
   em teste proprio.
