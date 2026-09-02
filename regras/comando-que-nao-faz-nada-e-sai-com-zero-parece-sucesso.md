---
id: comando-que-nao-faz-nada-e-sai-com-zero-parece-sucesso
projects: all
confidence: 0.85
status: active
last_confirmed: 2026-08-14
origin: ServiceDesk (2026-08-14) — `docker compose up -d --build` sem `--profile app` subiu so a infraestrutura, imprimiu "Built", saiu com 0, e o script anunciou "MODO APRESENTACAO LIGADO" com a API rodando no modo anterior.
---
Um comando que **filtra** o que vai executar (profile, tag, filtro de teste, seletor de label) e que
nao encontra nada para fazer normalmente sai com **codigo 0**. "Nao havia nada a fazer" e "fiz tudo"
sao indistinguiveis pelo exit code, e qualquer verificacao baseada em `$LASTEXITCODE` ou `$?`
aprova os dois.

**Esperado:** o script sobe a API em modo apresentacao e o banner confirma
**Aconteceu:** o `compose.yaml` mantinha a API e cinco workers atras do profile `app`. Sem
`--profile app`, o docker subiu so a infraestrutura, escreveu `Built` e `Container ... Running`, e
saiu com 0. O script imprimiu o banner amarelo de sucesso. A API continuou no ar **com a
configuracao antiga**, e so um `docker compose ps` mostrando `Up 15 minutes` — tempo demais para
quem acabou de ser recriado — denunciou.

## Como aplicar

1. Depois de um comando que deveria RECRIAR ou MODIFICAR algo, conferir o **efeito**, nao o exit
   code. Idade do container, hash da imagem, contagem de linhas afetadas, timestamp do artefato.
2. `Up 15 minutes` logo depois de um `up --build` e prova de que ele nao foi tocado. A idade e o
   teste mais barato que existe para "recriou mesmo?".
3. Quando o comando aceita filtro, tratar a ausencia de filtro como **erro de uso**, nao como
   padrao razoavel. Se o script precisa de `--profile app`, ele nao pode funcionar sem.
4. Banner de sucesso escrito pelo proprio script nao e evidencia de nada — ele imprime porque
   chegou na linha, nao porque o mundo mudou.

## Corolario generico (vale fora deste repo)

**Exit code responde "o comando terminou bem?", nunca "o comando fez o que eu queria?".** Onde
o alvo e selecionado por filtro, o caminho de "selecionei zero alvos" e um caminho de SUCESSO —
e e exatamente o caminho que voce nao quer.
