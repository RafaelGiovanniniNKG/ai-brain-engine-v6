---
rule: Caso de E2E que semeia com PK FIXA só passa uma vez — e o 2º run acusa a migração pelo resíduo do 1º
origin: sessao 2026-08-04, E2E de UI do OperationalManagement — 18/18 virou 17/18 sem nenhuma mudanca de codigo
projects: all
confidence: 0.85
confidence_origem: alta (o caso passou isolado, falhou no run seguinte, e a causa foi confirmada apagando a linha)
complementa: "caso-de-golden-precisa-poder-falhar"
status: active
---

## A regra

Se um caso de teste grava com **chave primária fixa**, ele tem exatamente **uma** execução válida por banco.
Da segunda em diante o `Create` responde 422/409 e o vermelho aponta para a API — quando o autor do problema
é o próprio caso, que deixou resíduo.

Antes de fixar uma PK, responda: **como esta linha sai daqui?** Se não houver endpoint de Delete, o caso
precisa de um caminho que funcione com a linha já existente.

## O que aconteceu

O caso *"um ciclo criado pela API MIGRADA aparece na tela"* semeava
`cleaningExecutionCycleId = 'e2e70000-...-0001'`, fixo, e **não tinha limpeza alguma**. Ele passou verde numa
execução isolada. No run completo seguinte, sem uma linha de código ter mudado:

```
Error: o Create MIGRADO tem de responder 200
Expected: 200
Received: 422
```

O 422 era a **API migrada acertando** — a linha já existia, do meu próprio run anterior. E o `CleaningExecutionCycle`
**não expõe Delete**: o controller só tem `Read`, `Create` e `Update` (medido, não presumido).

## Como aplicar

1. **PK fixa exige rota de saída.** Se existe Delete, apague no início do caso (não no fim: um caso que falha
   no meio nunca chega ao fim). Se não existe, use **create-ou-update**:

   ```ts
   const criado = await post(rota, corpo);
   let ok = criado.status() === 200, qual = `POST ${criado.status()}`;
   if (!ok) { const p = await put(rota, corpo); ok = p.status() === 200; qual += ` -> PUT ${p.status()}`; }
   expect(ok, `uma escrita MIGRADA tinha de responder 200 (tentativas: ${qual})`).toBe(true);
   ```

   Todo run exercita **uma escrita migrada**, nada acumula, e o caso ainda falha se as duas falharem.
2. **Registre qual ramo rodou** (`console.log`). Sem isso, "passou" não distingue Create de Update, e um Create
   quebrado ficaria escondido para sempre atrás do Update.
3. **Prove a idempotência executando duas vezes**, não raciocinando. Aqui: run 1 `POST 200`, run 2
   `POST 422 -> PUT 200`, os dois verdes. Isso cobre os DOIS ramos — um único run cobre um só.
4. A alternativa "PK nova a cada run" troca o bug por acúmulo silencioso na base. Só vale se houver Delete.
5. **Passar isolado e falhar no conjunto é assinatura de resíduo**, não de flakiness. Não recorra a `retries`
   antes de procurar o estado que o caso anterior deixou.
