---
rule: Skip em massa nos smokes e' concorrencia da PROPRIA execucao, nao lixo da anterior
origin: sessao 2026-08-03, migracao CQRS do OperationalManagement (remocao dos blocos mortos)
projects: all
confidence: 0.85
confidence_origem: alta (medido 3x nesta sessao, com o mecanismo isolado)
status: active
corrige: a regra anterior "skips em massa = Docker saturado por containers orfaos"
---

## A regra

Suite com **skips em massa** (ou `TimeoutException`) nos testes gated por container **nao**
significa, por si, "Docker saturado por orfaos de execucoes anteriores". Antes de limpar
qualquer coisa, **medir `docker ps` DURANTE a execucao**. O gatilho mais provavel e' a
**concorrencia da propria execucao**: o xUnit paraleliza colecoes, cada classe de smoke sobe
o SEU container de banco, e N containers simultaneos nao ficam *prontos* dentro do timeout do
Testcontainers — `StartAsync` estoura, o gate `Skip.IfNot(fixture.Available)` converte a falha
em **skip**, e a suite fica verde com dezenas de testes a menos.

## Por que a regra antiga enganava

A regra registrada dizia "orfaos acumulados, `docker rm -f` em todos → volta ao normal".
Nesta maquina havia **6 containers, todos de outro projeto**, zero orfaos — e a suite deu
`995 ok / 1 falha / 75 skips` contra a baseline `1068 / 0 / 3` (mesmo total: 1071). Seguindo a
regra antiga eu limparia containers que nao existiam, veria o sintoma persistir e concluiria
"entao e' codigo" — que era exatamente a conclusao errada.

## Como diagnosticar (na ordem)

1. **`docker ps` durante a execucao.** Aqui apareceram **16 SQL Server simultaneos**, 15 deles
   nascidos em 7 segundos, de 35 classes que dependem de container. 16 x ~2 GB prontos numa
   maquina de 15,5 GB nao cabe.
2. **Rodar UMA classe sozinha.** E' o experimento que decide. A classe que skipava passou em
   **836 ms** isolada. Se passa sozinha e skipa em conjunto, e' concorrencia — nao codigo.
3. Docker saudavel nao e' prova de nada: `docker run hello-world` subiu na hora e um SQL Server
   avulso ficou pronto em 12 s. Container pequeno sobe; N containers de 2 GB nao.

## Como corrigir sem tocar no repo

Um `.runsettings` **fora do repo** (scratchpad) limitando o paralelismo, passado por
`--settings`. Com `MaxCpuCount=1` + `xUnit/maxParallelThreads=3` a baseline voltou exata
(`1068 / 0 / 3`) em 1m29s.

⚠️ **`dotnet test -- xUnit.maxParallelThreads=3` na linha de comando NAO pegou** — medi o pico
depois e continuavam 16 containers. O arquivo de runsettings funcionou. **Verifique que o
limite pegou medindo o pico, nao assumindo pelo flag.**

## A regra irma, que vale sozinha

**Ler o resultado da suite inclui ler a CONTAGEM DE SKIPS.** Skip e' pior que falha porque
conta como verde. E **conferir o TOTAL**: aqui o total (1071) era identico ao da baseline, o que
provou de imediato que nenhum teste havia sido criado ou perdido — 72 apenas deixaram de rodar.
