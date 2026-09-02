---
id: modo-de-gravacao-destrutivo-exige-filtro-de-um-teste
projects: all
confidence: 0.6
last_confirmed: 2026-07-31
status: active
origin: migracao-operacional Onda 2 Passo 5 (2026-07-31) — rodei GOLDEN_RECORD=1 com o filtro `~ContratoGoldenTests&~Cleaning` para conferir determinismo de DOIS goldens; ele casou SETE e regravou os goldens dos Passos 1-4 com a saída do código novo
---
Modo de gravação de baseline/golden/snapshot é **destrutivo por definição**. Ativá-lo com filtro por
**substring** é apostar que nenhum teste irmão casa — e nomes de teste de um mesmo domínio casam entre si
quase sempre. **Ativar só com filtro que nomeia UM teste** (nome totalmente qualificado, ou uma execução por
arquivo).

**Esperado:** `--filter "~ContratoGoldenTests&~Cleaning"` alcançaria os 2 goldens que eu acabara de criar
**Aconteceu:** casou **7** (os 5 dos passos anteriores também tinham "Cleaning" e "ContratoGoldenTests" no
nome) e regravou os 5 antigos com a saída do **código novo** — transformando cada um num espelho de si mesmo,
que é exatamente o modo de falha que aqueles goldens existem para impedir. A saída da rodada dizia
`Aprovado: 7` e eu li como sucesso, não como alarme.

## Como aplicar

1. Antes de rodar em modo de gravação, rodar o **mesmo filtro em modo normal** e conferir a **contagem**. Se o
   número de testes não é exatamente o esperado, o filtro está errado — e essa é a única chance de ver isso
   antes de a gravação acontecer.
2. Preferir filtro por nome totalmente qualificado (`FullyQualifiedName=Namespace.Classe.Metodo`) ou uma
   invocação por arquivo, nunca `~substring` composta.
3. Tratar a **contagem de testes executados** como asserção: em gravação, `Aprovado: N` com N maior que o
   esperado é falha silenciosa, não sucesso.
4. Se o artefato regravado é **tracked**, `git status` denuncia na hora — conferir `git status` logo após
   qualquer rodada de gravação, antes de seguir. (No caso, os 5 antigos eram tracked e apareceram como ` M`;
   os 2 novos ainda não estavam no índice e não teriam denunciado nada.)

## O que salvou

As guardas criadas no passo anterior, **contra o próprio autor delas**: exigir o status de **ORIGEM** na
substituição de divergência aprovada, e "golden ausente é falha". A suíte completa acusou 5 falhas com a
mensagem da guarda de golden-espelho; sem ela, os 5 goldens regravados **passariam verdes** e a migração
seguiria com cinco espelhos no lugar de cinco evidências.

## Corolário genérico

**Uma guarda só prova o seu valor quando pega quem a escreveu.** Guarda que nunca disparou é hipótese; a que
dispara contra o autor, no mês seguinte, é infraestrutura. Vale para snapshot testing, `--update-snapshots`,
`--fix`, `--write`, migrations `--force` e qualquer flag cujo efeito seja sobrescrever evidência.
