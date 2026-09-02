---
rule: Validar no processo que despacha EM PRODUCAO, nao no que esta a mao - pipeline de MediatR e por processo, nao por assembly
origin: sessao 2026-08-04, Onda 8 (Grupo B) do OperationalManagement - validei o sync na API e declarei "validado"; os behaviors nao existem nos dois workers, onde os slices gravariam ZERO em silencio
projects: all
confidence: 0.85
confidence_origem: alta (o csharp-reviewer achou; eu confirmei por grep e o achado invalidou a validacao inteira)
complementa: "reverter-o-fonte-nao-reverte-o-binario-que-voce-vai-medir", "desregistrar-handler-legado-exige-mapear-todos-os-despachantes"
status: active
---

## A regra

Registro de **handler** vive no container compartilhado; registro de **behavior** (pipeline) vive no
`AddMediatR` de **cada processo executavel**. Um mesmo command, despachado do mesmo container, roda com
pipeline na API e **sem pipeline nenhum** no worker.

Portanto: **mapeie os despachantes (isso todo mundo lembra) E o PIPELINE de cada processo que despacha.**
E valide no processo que despacha em producao — nao no que esta mais facil de subir.

Se o processo de producao esta indisponivel, o resultado nao e' "validado com uma ressalva". E' **nao
validado**, e tem de ser dito assim.

## O que aconteceu

Migrei 6 verbos para slices CQRS. Os handlers novos **nao** chamam `SaveChangesAsync` de proposito — quem
persiste e' o `TransactionBehavior`, depois do handler. Isso e' correto no padrao-alvo, e foi conferido.

Os 7 `AddOpenBehavior` estavam registrados em **um** lugar: o `Startup.cs` da API. Os dois workers faziam
`services.AddMediatR(cfg => cfg.RegisterServicesFromAssembly(typeof(Program).Assembly))` e nada mais. Nos
workers, portanto: `_context.Set<T>().Add(entidade)` → handler retorna → **ninguem salva**. O adaptador
devolvia `true`, o worker logava "concluido", e **zero linha** era gravada. O legado persistia porque o
`Commit()` estava **dentro** do handler.

Perda funcional total e silenciosa do motor de sincronizacao — que roda a cada minuto em producao.

**Eu validei por HTTP no processo da API**, que tem o pipeline, e escrevi "sync validado". O despachante de
producao e' o worker. O caminho validado **nao era** o caminho de producao.

**E o pior:** a prova que eu usei era boa (a trilha caindo no Outbox em vez da tabela legada — ver a regra
irma sobre binario), mas **so discrimina onde o pipeline existe**. No worker o resultado seria
`trilha antiga +0 / trilha nova +0` — indistinguivel de "nada aconteceu" para qualquer sonda que nao conte as
linhas de negocio. A minha melhor sonda era cega exatamente no processo que importava.

A guarda de DI tambem nao podia pegar: ela inspeciona o bootstrapper compartilhado, e os behaviors nao estao
nele.

## Como aplicar

1. **Enumere os processos executaveis** (todo `Program.cs`/`Startup.cs` com `Main`/host) e, para cada um,
   liste: o container que ele monta **e** o pipeline que ele registra. Dois eixos, nao um.
2. `grep` por `AddOpenBehavior` / `AddBehavior` / `Decorate` / registro de `IPipelineBehavior` **no
   repositorio inteiro**. Se aparecer em menos processos do que despacham o command, ha assimetria.
3. **Escreva um teste que assere o pipeline por processo**, no mesmo lugar em que voce assere o container. Uma
   guarda que le so o bootstrapper compartilhado declara meio fato.
4. Ao mover persistencia do handler para um behavior, pergunte: **quantos processos precisam desse behavior
   agora?** Mover para o pipeline troca "funciona em todo lugar que resolve o handler" por "funciona onde o
   pipeline foi registrado".
5. **Escolha o canario pensando no processo mais pobre.** "A trilha caiu na tabela nova" so distingue onde a
   trilha e' escrita. Onde nada e' escrito, o canario precisa contar **linha de negocio**.
6. Se o processo de producao estiver indisponivel (proibido, sem credencial, sem ambiente), pare e diga
   **"nao validado"**. Trocar de processo e chamar de equivalente e' a substituicao silenciosa que esta regra
   existe para impedir.

## Corolario generico

**"Rodei e funcionou" e uma afirmacao sobre um processo, nao sobre um codigo.** Num sistema com varios
executaveis compartilhando o mesmo container, o codigo e' o mesmo e o comportamento nao.
