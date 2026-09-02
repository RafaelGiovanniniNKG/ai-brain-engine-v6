---
rule: Grep para provar ausencia de uso precisa cobrir os DOIS lados do limite de palavra
origin: sessao 2026-08-03, remocao dos blocos mortos do OperationalManagement
projects: all
confidence: 0.85
confidence_origem: alta (os dois erros ocorreram na mesma sessao, em direcoes opostas)
status: active
complementa: "grep para provar que algo NAO e' usado precisa de \\b"
---

## A regra

`\b` resolve **um** dos dois erros e **cria** o outro. Ao provar que um tipo nao e' mais usado,
rode as duas formas e concilie:

- **Sem `\b`** → falso POSITIVO: `AuditDocument` casa em `AuditDocumentCode`;
  `EmployeeImportResultViewModel` casa em `SeniorEmployeeImportResultViewModel` (foi assim que
  uma justificativa FALSA entrou num commit, `d13e48e`).
- **Com `\b`** → falso NEGATIVO: `\bProtectiveEquipment\b` **nao** casa em
  `IProtectiveEquipmentAppService` nem em `ProtectiveEquipmentViewModel`. Nesta sessao isso
  subcontou o DI em **215 ocorrencias** e escondeu 5 interfaces `I*AppService` e 27 arquivos de
  command/event/validation da lista de remocao.

## O caso que quase destruiu codigo fora de escopo

Classificar por **prefixo do nome do arquivo** parecia seguro e teria apagado
`Domain/Enums/SixS/ActionStatus.cs` e `ActionPriority.cs` — que, apesar da pasta `SixS`, sao
enums **do FastResponse** (fora de escopo), usados por 5 arquivos vivos. Nome e pasta nao
provam pertencimento: **medir quem usa o tipo**, e so entao decidir.

## O caso na direcao oposta

O token `Signature` casa dentro de **`IsSignature`**, que e' campo das fotos de Checklist e
Cleaning **ja migradas**. Uma remocao por linha com esse token teria apagado o mapeamento EF e
os `ForMember` do IsSignature — quebrando verbos migrados **em silencio**. Solucao: lookbehind
`(?<!Is)Signature`. Dos 131 arquivos que o grep sem guarda apontava como afetados, **~120 eram
esse falso positivo**.

## Como aplicar

1. Liste candidatos por **nome E por pasta** (`Create*Command` vive em `XxxCommands/` e nao
   comeca com o nome do bloco — 27 arquivos entraram na lista so por essa regra).
2. Rode o grep **sem** `\b` para achar tudo, e trate cada acerto como *candidato*, nao como
   prova.
3. Para cada tipo ambiguo, meça **quem o usa fora do conjunto a remover**. Uso vivo = preservar.
4. Onde a remocao e' por LINHA, prove que o token nao e' substring de um identificador vivo
   (`Is`+X, `I`+X, X+`Code`). Onde for por BLOCO (mapeamento EF, metodo), remova por **balanco
   de delimitadores** — num bloco a maioria das linhas nao contem o nome do tipo.
5. Depois de remover, rode um grep de **referencias residuais** e exija que o que sobrou seja
   exatamente a lista de arquivos que voce planejava editar. Aqui isso reduziu o problema a
   5 arquivos e expos o resto.
6. O compilador e' a rede final, mas nao substitui o passo 5: ele acha o que quebrou, nao o que
   voce apagou por engano e ninguem usava.
