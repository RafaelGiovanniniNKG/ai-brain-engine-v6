---
rule: O caso-canario prova que a sonda LE; nao prova que ela REPORTA - projete as colunas explicitamente
origin: sessao 2026-08-03, Onda 6 (bloco Motorista) do OperationalManagement - o Format-Table descartou a coluna que dois casos mediam, e a evidencia de um deles foi apagada pelo caso seguinte
projects: all
confidence: 0.85
confidence_origem: alta (o canario passou, e ainda assim dois casos sairam sem a coluna medida)
status: active
complementa: "instrumentacao-de-medicao-precisa-de-caso-canario", "caso-de-golden-precisa-poder-falhar"
---

## A regra

Um caso-canario prova que o instrumento **enxerga** o sistema. Nao prova que ele **mostra o que importa**.
Sao duas falhas diferentes, e a segunda passa pelo canario sem acender luz nenhuma.

Em consulta de verificacao, **projete as colunas explicitamente e curtas** (`LEFT(col, 30)`), e nunca deixe
a coluna que o caso mede depender de formatacao automatica, largura de terminal ou do tamanho do dado de
*outra* linha do mesmo resultado.

## O que aconteceu

O roteiro tinha canario e ele funcionou — a primeira requisicao mostrou a linha gravada, provando que a
sonda lia o banco. Todos os 48 casos sairam com status, corpo e tabela preenchidos: uma medicao de aparencia
impecavel.

Mas a verificacao usava `SELECT *`-ish + `Format-Table -AutoSize | Out-String -Width 200`. Quando um caso
gravou uma descricao de **250 caracteres**, o formatador redistribuiu a largura e **silenciosamente
descartou as ultimas colunas** de todos os resultados seguintes daquela tabela. As colunas descartadas foram
`QuestionOrderNumber` e `Inactive` — exatamente as que dois casos existiam para medir.

O agravante: a linha do caso `inactive` omitido foi **apagada pelo Delete do caso seguinte**. O estado
intermediario nao era reconstituivel do estado final, entao nao bastou reconsultar: o caso teve de ser
**remedido do zero**.

O canario nao podia pegar isso. Ele rodou primeiro, com dados curtos, quando todas as colunas ainda cabiam.

## Como aplicar

1. **Projete colunas explicitamente** na consulta de verificacao, e trunque no SQL (`LEFT(descr, 30)`), nao
   na exibicao. O que o caso mede tem de estar entre as primeiras colunas.
2. **Nunca use `-AutoSize` para evidencia.** Ele e um formatador de conveniencia: prioriza caber, e cortar
   coluna e a forma dele de caber. Cortar sem avisar e o comportamento normal, nao um bug.
3. **Cuidado com o dado longo de propósito.** Se o roteiro tem um caso de "campo no limite da coluna", esse
   dado vai contaminar a exibicao de todos os outros casos que consultam a mesma tabela.
4. **Ordene os casos pensando na evidencia**: um caso destrutivo depois de um caso observacional apaga a
   prova do primeiro. Se nao der para reordenar, capture o estado no proprio caso, nao ao final.
5. **Ao remedir**, semeie o estado inicial no valor **contrario** ao esperado — senao a nova medicao nasce
   verde afirmando o que voce ja presumia.

## Corolario

Toda medicao tem tres coisas que podem estar erradas: o sistema, a leitura do instrumento e o **relato** do
instrumento. Canario cobre a segunda. A terceira exige projetar a saida de proposito.
