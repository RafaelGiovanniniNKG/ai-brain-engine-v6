---
rule: Componente que monta a propria configuracao ignora a variavel de ambiente que voce setou - e pode apontar para PRODUCAO
origin: sessao 2026-08-04, Onda 8 (Grupo B) do OperationalManagement - subi o worker com a connection string do DEV imposta por env var, e a trilha legada foi escrita em PRODUCAO por um SEGUNDO DbContext que nao le env var nenhuma
projects: all
confidence: 0.95
confidence_origem: MUITO alta (DUAS ocorrencias em componentes diferentes no MESMO dia: EventStoreSqlContext e BaseBlobStorageRepository)
complementa2: "portao-de-leitura-antes-de-escrita-irreversivel"
status: active
complementa: "nunca-sql-hml-prod", "grep-para-provar-ausencia-precisa-dos-dois-lados"
---

## A regra

Fixar a connection string por variavel de ambiente (`ConnectionStrings__DefaultConnection`) só controla os
contextos registrados por **`AddDbContext`**, que recebem as opcoes do `IConfiguration` do host. Um
`DbContext` com **`OnConfiguring` proprio** monta a sua propria configuracao e **nao ve nada disso**.

Antes de rodar qualquer processo contra um ambiente sensivel, enumere **todos** os `DbContext` do grafo e,
para cada um, responda: *de onde ELE tira a connection string?* Se algum tiver `OnConfiguring` com
`ConfigurationBuilder` interno, a sua env var nao o alcanca — e a guarda tem de ser no **arquivo que ele le**.

Tres detalhes que se combinam para o pior caso:

1. **`AddScoped<MeuContext>()` em vez de `AddDbContext<MeuContext>()`** — sinal de que as opcoes nao vem do
   host. Procure por isso no bootstrapper: e a pista mais barata.
2. **O nome da variavel de ambiente pode ser OUTRO.** O host lia `DOTNET_ENVIRONMENT` (worker generico) e o
   `OnConfiguring` lia **`ASPNETCORE_ENVIRONMENT`**. Setei a primeira; a segunda ficou vazia, o
   `appsettings.{vazio}.json` nao existe, e sobrou o `appsettings.json` puro.
3. **`appsettings.json` costuma ser o de PRODUCAO**, com o de dev por cima via arquivo de ambiente. Sem o
   nome do ambiente, o "por cima" nao acontece e o que vale e producao.

## O que aconteceu

Medicao do worker de inativacao contra o DEV. Cuidados que eu tomei e que **funcionaram** para o contexto
principal: `DOTNET_ENVIRONMENT=Development`, `ConnectionStrings__DefaultConnection=<DEV>` imposta por env
var, e guarda abortando se o banco nao terminasse em `Dev`. O DEV recebeu as escritas de negocio e foi
restaurado exato ao final — conferido linha a linha.

O `EventStoreSqlContext` (a trilha legada `StoredEvent`) e um **segundo** contexto, registrado com
`AddScoped`, com `OnConfiguring` que faz `ConfigurationBuilder().SetBasePath(Directory.GetCurrentDirectory())
.AddJsonFile("appsettings.json").AddJsonFile($"appsettings.{ASPNETCORE_ENVIRONMENT}.json")` e **nenhum**
`AddEnvironmentVariables()`. Resultado: ele resolveu a connection string do `appsettings.json` do worker, que
aponta para producao, e as ~54 linhas de trilha da execucao foram gravadas **em producao**.

**Como eu soube que a escrita nao falhou** (a parte que vale como metodo): `InMemoryBus.RaiseEvent` chama
`_eventStore?.Save(...)` **sem try/catch**. Se o `Save` tivesse estourado, a excecao subiria do handler ate o
`try/catch` por filial do sync, que abortaria aquela filial **na primeira** referencia criada — eu veria ~5
referencias, uma por filial. Vi as **37**. Logo o `Save` completou, logo escreveu no destino que resolveu.
A ausencia de erro no console nao provava nada; a **contagem** provou.

## Como aplicar

1. `grep` por `OnConfiguring` e por `AddScoped<.*Context>` antes de apontar um processo para um ambiente
   sensivel. Cada acerto e um caminho de conexao que a sua env var nao controla.
2. Para esses contextos, a guarda tem de **replicar a resolucao deles** (mesmo diretorio base, mesmos
   arquivos, mesmo nome de variavel de ambiente) e abortar se o resultado nao for o ambiente esperado.
   Guarda que valida a *sua* string, e nao a que o codigo vai usar, e guarda decorativa.
3. Sete **todos** os nomes de variavel de ambiente em uso no processo (`DOTNET_ENVIRONMENT` **e**
   `ASPNETCORE_ENVIRONMENT`), nunca so o que o `Program.cs` le.
4. `Directory.GetCurrentDirectory()` num `OnConfiguring` significa que o **working directory** decide o
   banco. Rodar o mesmo binario de outra pasta muda o destino da escrita.
5. Depois de rodar, **confira a tabela que deveria ter recebido a trilha**. Delta zero onde voce esperava
   delta N nao e "o processo nao gravou": pode ser "gravou em outro lugar". Foi esse zero que denunciou tudo.
6. Se a escrita indevida foi em producao, **pare e reporte**. Nao leia nem limpe producao por conta propria:
   a decisao e de quem responde pelo ambiente.

## Segunda ocorrencia, no MESMO dia — e nao era um DbContext

Onda 9 (VideoIntegration). O **`BaseBlobStorageRepository`** tem construtor **sem parametros** que monta
`ConfigurationBuilder().SetBasePath(Directory.GetCurrentDirectory()).AddJsonFile("appsettings.json")
.AddJsonFile($"appsettings.{ASPNETCORE_ENVIRONMENT}.json")` — **sem `AddEnvironmentVariables()`**. Setei
`ConnectionStrings__AzureBlobStorageConnection` apontando para o Azurite e a API continuou falando com a conta
**real de producao**.

Tres coisas que tornam esta ocorrencia pior que a primeira:

- **nao e um `DbContext`.** O `grep` por `OnConfiguring` e por `AddScoped<.*Context>` que a regra original
  recomenda **nao acha isso**. O padrao a procurar e' mais largo: **`new ConfigurationBuilder()` fora do
  `Program.cs`/`Startup.cs`**. Qualquer classe que faca isso tem a propria ideia de configuracao;
- **o destino era o mesmo em DEV e em PROD.** `appsettings.json` e `appsettings.Development.json` tinham a
  MESMA conta de blob e o MESMO container. Nao havia "ambiente errado" para detectar por nome de banco — a
  guarda de sufixo `Dev` que salvou o caso do SQL nao tem analogo aqui;
- **a escrita era IRREVERSIVEL.** Caminho de blob fixo e `DeleteIfExistsAsync` antes do upload: um POST
  sobrescreveria o video de producao, sem backup e sem volta. No caso do SQL o dano foram 54 linhas de trilha
  numa tabela de auditoria; aqui seria o arquivo que a operacao usa.

**Correcao aplicada, em dois caminhos:** construtor que recebe `IConfiguration` (o que o DI escolhe, e que traz
a configuracao do host com env vars) **e** leitura explicita da variavel no construtor sem parametros, que
continua existindo porque uma subclasse o chama via `: base()`. Mais falha ALTA quando a connection string ou o
container faltam — silencio ali virava excecao obscura do SDK, longe da causa.

## Corolario generico

**"Eu fixei a connection string" e uma afirmacao sobre UM caminho de conexao.** Um processo tem tantos
caminhos quantos forem os componentes que constroem configuracao — `DbContext`, repositorio de blob, cliente de
fila —, e cada um pode ter a sua propria ideia de onde mora a verdade.

🔑 **E a licao de metodo que as duas ocorrencias compartilham:** a variavel de ambiente nao e' prova. Prova e'
**perguntar ao processo, em execucao, com qual destino ele esta falando** — de preferencia por uma operacao de
LEITURA, antes de liberar a escrita. Ver [[portao-de-leitura-antes-de-escrita-irreversivel]].
