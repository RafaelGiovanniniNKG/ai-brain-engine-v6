# ai-brain-engine-v6

Plugin de Claude Code, de uso pessoal. Instala **na máquina**, trabalha **dentro** de qualquer
repositório e **não escreve um único arquivo lá**.

Ele existe para fechar quatro falhas medidas no v5 (diagnóstico de 28/08/2026):

| Falha | O que o v6 faz |
|---|---|
| As regras aprendidas nunca chegavam ao modelo | Injeta no início da sessão, e o que é mecânico vira bloqueio em vez de texto |
| Nenhum sensor mecânico em .NET/Angular | Servidor de linguagem, `slopwatch`, ESLint externo, afirmação de camada — tudo fora do repo |
| Nada impedia dizer "pronto" sem prova | Nega o encerramento quando houve edição de código sem teste verde |
| O vault era mão única e dependia de lembrar | Captura por gatilho automático, com cursor e hash, e leitura de volta na sessão seguinte |

**Plano, decisões e evidências:** `C:\Github\obsidian-vault\Projetos\ai-brain-engine-v6`.
Nenhum documento de plano vive neste repositório — é a mesma regra que vale para os repos de
trabalho.

## Estado

Passos 0 a 6 executados — ver o registro de execução no plano, no vault.

## Instalar numa máquina zerada

São **quatro coisas**, nesta ordem. O passo 3 é um comando só; ele faz todo o resto e no
final imprime o que ficou faltando.

### 1. O que a máquina precisa ter antes

Nada disso o motor instala — é o chão em que ele pisa. Só o Claude Code e o Python são
obrigatórios; sem os outros o motor sobe com aquele sensor desligado, e o diagnóstico diz qual.

| O que | Como | Obrigatório |
|---|---|---|
| Claude Code | instalador oficial | sim |
| Python 3.10 ou mais novo | `winget install Python.Python.3.12` (o comando tem de se chamar `python`) | sim — todo hook do motor é Python |
| Git | `winget install Git.Git` | sim |
| SDK do .NET | `winget install Microsoft.DotNet.SDK.10` | só para os sensores de C# |
| Node | `winget install OpenJS.NodeJS.LTS` | só para o sensor de TypeScript |

### 2. Trazer os dois repositórios privados

O motor não serve de nada sem o cofre — é lá que ele lê o contexto e escreve o diário. Os dois
são privados, então autentique primeiro (`gh auth login`, ou o Git Credential Manager na
primeira `clone`).

```powershell
git clone https://github.com/RafaelGiovanniniNKG/ai-brain-engine-v6.git C:\Github\ai-brain-engine-v6
git clone https://github.com/RafaelGiovanniniNKG/obsidian-vault.git      C:\Github\obsidian-vault
```

Se o cofre for para outro lugar, passe o caminho no passo seguinte com `-Vault`.

### 3. Rodar o instalador

```powershell
powershell -ExecutionPolicy Bypass -File C:\Github\ai-brain-engine-v6\instalar.ps1
```

Pode rodar de novo quantas vezes quiser: cada passo confere antes de agir, diz `[feito]` ou
`[ja ok]`, e nada é sobrescrito sem backup. Ele acha o cofre, grava o caminho em `local.json`
(que não vai para o git — é o único arquivo que muda de máquina para máquina), cria o
`CLAUDE.md` acima dos repositórios se não existir, instala as ferramentas de medição, registra
o plugin no escopo do usuário, aponta a memória automática para o cofre, desliga o ECC se
estiver ligado e roda as quatro provas. Termina imprimindo o diagnóstico.

### 4. Conferir

```powershell
powershell -ExecutionPolicy Bypass -File C:\Github\ai-brain-engine-v6\instalar.ps1 -Conferir
```

Só diagnostica, não muda nada. Uma linha por conferência, e `Tudo de pé` no fim. Depois abra
uma sessão nova **dentro de um repositório** — o motor não entra em vigor na sessão que já
estava aberta.

### Para desenvolver o motor sem instalar

```powershell
claude --plugin-dir C:\Github\ai-brain-engine-v6
```

## O que você digita

| Comando | Quando |
|---|---|
| `/v6-ideia` | você tem uma ideia e ainda não há código. Define o negócio e as regras, discute honestamente se a ideia se sustenta, e escreve a nota de visão no cofre |
| `/v6-conhecer` | primeira sessão num repositório sem nota no cofre. Levanta arquitetura, o padrão que um arquivo novo tem de imitar e como aquilo roda de verdade — e escreve no cofre, nunca no repositório |
| `/v6-tarefa <o que fazer>` | qualquer mudança de código. Ele escolhe a cerimônia pelo tamanho: pequena vai direto, média pede um sim no chat, grande escreve especificação e plano no cofre e espera aprovação |
| `/v6-revisar` | antes de abrir PR, ou fechando uma tarefa. Vários revisores em paralelo no diff da branch, um verificador por achado. Não commita nada |
| `/v6-pr <id ou URL>` | um PR de verdade, do Azure ou do GitHub. Igual ao anterior mais os eixos de **arquitetura** e **testes**, porque o que passa num PR vira o padrão do repositório amanhã |
| `/v6-arquitetura` | a saúde da arquitetura do repositório **inteiro**, não de um diff. Achados numerados com evidência e critério de pronto executável; relatório no cofre |
| `/v6-regra` | algo deu errado por um motivo que vai se repetir. Registra a lição como regra viva, que o motor passa a injetar em toda sessão e em todo revisor |
| `/v6-curar` | quando o diário juntou muitas sessões. Propõe uma nota-índice **ao lado** da atual, para você comparar |

O resto acontece sozinho e você nunca digita: contexto no início da sessão, medição a cada
arquivo editado, recusa de encerrar sem teste verde, e o diário no cofre.

## Estrutura

```
.claude-plugin/       manifesto do plugin e do marketplace de uma peça
.lsp.json             C# e TypeScript com diagnóstico ligado
instalar.ps1          instalação em um comando, idempotente (-Conferir só diagnostica)
local.json            caminho do cofre nesta máquina — fora do git, o único arquivo local
mapa.json             repo -> pasta do projeto no cofre
hooks/hooks.json      todos os gatilhos; comando em STRING, nunca em lista
hooks/session_start   monta o bloco de contexto (teto de 6.000 caracteres)
hooks/post_edit       despacha os sensores no arquivo que acabou de ser editado
hooks/post_bash       teste/build/commit, e o código mexido pelo TERMINAL
hooks/stop_gate       o portão: nega encerrar quando editou código e não provou
hooks/reinjetar       devolve as regras quando a conversa é resumida ou o modelo troca
hooks/gatilho_diario  dispara o resumo do dia em processo destacado
hooks/guarda_commit   confere a mensagem de commit antes de ela ir
hooks/doutor          o diagnóstico, uma linha por conferência
hooks/vault           escrita no cofre: slug, frontmatter, UTF-8, escrita atômica
captura/destilar      a chamada de modelo que resume a sessão, com plano B mecânico
regras/               as regras vivas, uma por arquivo (39: 37 portadas do v5, 2 nascidas aqui)
sensores/             slopwatch, eslint próprio e a matriz de camadas — fora dos repos
skills/               v6-ideia, v6-conhecer, v6-tarefa, v6-revisar, v6-pr,
                      v6-arquitetura, v6-regra, v6-curar
agents/               revisores de stack: csharp-reviewer, typescript-reviewer
testes/               sete provas: plugin carrega, injeção, portão, diário, guarda,
                      edição pelo terminal, reinjeção das regras
_prova/               saída da sonda; não versionado
```

## Por que só dois agentes

Cada agente cobra o nome e a descrição dele em **toda** sessão, ligado ou não. Foi assim que o
plugin anterior chegou a ~31.500 tokens sempre presentes, com 64 agentes dos quais quase nenhum
tinha a ver com o trabalho daqui.

Então a régua é: **agente só existe onde um prompt reutilizável e específico ganha de um foco
escrito na hora.** Isso vale para C# e para o front, que são as duas stacks da casa e onde há
armadilha acumulada que vale guardar. Para os outros eixos de revisão — correção, arquitetura,
testes, padrão do repositório — as skills usam agente de propósito geral com o foco declarado no
prompt, e isso custa zero quando ninguém está revisando.

E a divisão de trabalho não muda: **agente acha, a sessão principal confere e decide.** Quem
libera o encerramento é o resultado do teste, nunca a aprovação de outro agente.

## Regras da casa

- Uma regra só nasce de falha real, com o `origin` apontando a sessão ou o commit que a originou.
- Injeção é limitada de propósito: manchete da regra, não o corpo.
- Hook que pode quebrar a sessão sai em silêncio com código 0.
- Nada de licença paga.
