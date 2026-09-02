---
rule: Antes de escrita irreversível, use uma operação de LEITURA que revele o destino efetivo — e aborte se não for o esperado
origin: sessao 2026-08-04, Onda 9 (VideoIntegration) do OperationalManagement — o portão acusou "Azure de produção" quando eu já tinha setado a variável de ambiente para o Azurite
projects: all
confidence: 0.85
confidence_origem: alta (o portão pegou o erro na primeira execução, e o dano evitado era irreversível)
complementa: "dbcontext-que-monta-a-propria-config-ignora-a-variavel-que-voce-setou", "canario-prova-que-a-sonda-le-nao-que-ela-reporta"
status: active
---

## A regra

Quando a próxima operação é **irreversível** (sobrescrever um arquivo em caminho fixo, apagar sem soft-delete,
disparar e-mail, chamar um provedor de pagamento), não confie na configuração que você passou. **Pergunte ao
processo em execução com qual destino ele está falando, por uma operação de LEITURA, e aborte se a resposta não
for o esperado.**

Configuração é uma *intenção*. O portão de leitura é uma *medição*. Entre as duas cabe um componente que monta
a própria configuração e ignora a sua variável de ambiente.

## O que aconteceu

Os 2 verbos a migrar sobem um vídeo com `UploadFromFileOverwriteAsync("Videos/<GUID>.mp4", ...)` — caminho
**fixo**, e `DeleteIfExistsAsync` antes do upload. E o pior detalhe: `appsettings.json` (produção) e
`appsettings.Development.json` tinham a **mesma conta de blob** e o **mesmo container**. Não existia "ambiente
errado" detectável por nome — a guarda de "o banco tem de terminar em `Dev`", que funcionou nas 8 ondas
anteriores, não tem análogo quando dev e prod compartilham o destino.

Subi o Azurite, passei `ConnectionStrings__AzureBlobStorageConnection` por variável de ambiente, e **antes de
qualquer POST** rodei o verbo **GET** do mesmo controller — ele devolve um SAS, e o **host do URI revela a conta
efetiva**:

```
VideoIntegrationDriver -> host=cs21003bffd9536674f.blob.core.windows.net
🔴 ABORTAR: a API esta apontada para o AZURE REAL. NENHUM POST.
```

A variável não pegou: o `BaseBlobStorageRepository` monta a própria configuração sem
`AddEnvironmentVariables()`. **Se eu tivesse confiado nela, o primeiro caso do roteiro teria apagado e
sobrescrito o vídeo institucional de produção.** Corrigida a causa raiz, o mesmo portão passou a dizer
`127.0.0.1:10000`, e só então o roteiro de 10 casos rodou.

## Como aplicar

1. **Procure um verbo de leitura que vaze o destino.** Vale mais que qualquer log: um SAS, uma URL de retorno,
   um health-check que ecoa o endpoint, um `SELECT @@SERVERNAME`. Se não existir, crie um — uma sonda somente
   leitura é barata comparada ao dano.
2. **O portão vive no script, não na sua cabeça.** Codifique `if (destino não é o esperado) { throw }` e
   derrube o processo. Um portão que você "confere olhando" não roda na próxima vez.
3. **Classifique em três, não em dois:** esperado → segue; sabidamente errado → aborta; **indeterminado →
   aborta também**. "Não consegui classificar a resposta" é motivo para parar, não para continuar.
4. **Rode o portão DEPOIS de cada mudança de configuração ou rebuild**, não só na primeira vez. Foi o mesmo
   portão, reexecutado, que provou que a correção funcionou — isso o torna também o teste de discriminação da
   correção: vermelho antes, verde depois.
5. **Quando dev e prod compartilham o destino, diga isso em voz alta** no cabeçalho do script, com o motivo
   pelo qual o portão existe. A próxima pessoa (ou a próxima sessão) vai presumir que existe separação.
6. Se não houver como apontar para um destino seguro (emulador, container de teste), **a medição não acontece
   sem autorização humana explícita.** Escolher entre "não medir" e "medir em produção" não é decisão do agente.

## Corolário

O padrão que se repete: **eu setei X, logo o sistema usa X** é uma inferência, não um fato. Vale para variável
de ambiente, para arquivo de configuração, para binário recompilado (reverter o fonte não reverte o `bin`) e
para mock em teste. Em todos, o conserto é o mesmo: **fazer o sistema declarar o que ele está usando, e
verificar essa declaração antes do ponto de não-retorno.**
