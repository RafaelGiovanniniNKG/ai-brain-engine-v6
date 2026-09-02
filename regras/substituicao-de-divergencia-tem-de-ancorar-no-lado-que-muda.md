---
rule: A substituição de divergência aprovada tem de ancorar no lado que MUDA, nunca no valor solto — e exigir contagem exata
origin: sessao 2026-08-04, Onda 8 (Grupo B) do OperationalManagement — a guarda de contagem exata derrubou o proprio autor dela
projects: all
confidence: 0.85
confidence_origem: alta (a guarda pegou o erro em execucao, na primeira rodada, e o erro era meu)
complementa: "caso-de-golden-precisa-poder-falhar"
status: active
---

## A regra

Quando um golden gravado no legado precisa ser reconciliado com o comportamento novo, a substituição
(`AplicarDivergenciasAprovadas`) tem de casar **o lado que muda**, não o **valor** que mudou. O mesmo valor
quase sempre aparece nos dois lados — no `REQ` que o cliente enviou e no `RES` que o servidor devolveu — e só
um dos dois é a divergência. Substituir os dois **apaga a evidência** em vez de reconciliá-la.

E exija **contagem exata** sempre que o número for conhecido. `ocorrenciasExigidas: 1` é o que transforma
"achei e troquei" em "achei o que eu disse que ia achar".

## O que aconteceu

O achado D4 era: no upsert, o legado ecoava no corpo o `referenceId` **do payload**, que não é a linha gravada —
o cliente recebia um id inexistente no banco. O slice passou a devolver a PK real.

A substituição que eu escrevi procurava `"referenceId":"<ID-NOVO-DO-PAYLOAD>"`. A guarda estourou:

```
Expected achadas to be 1 ... Achadas: 2
```

As duas ocorrências eram:

```
REQ  {"referenceId":"<ID-NOVO-DO-PAYLOAD>", ...}      <- o payload. O slice manda IDENTICO.
RES  {"data":{"referenceId":"<ID-NOVO-DO-PAYLOAD>",   <- o corpo. E' ESTE que muda.
```

Se as duas fossem trocadas, o golden passaria a dizer que o cliente enviou o id semeado. Isso reconcilia a
comparação — e **destrói o caso**: a única razão pela qual o D4 é visível é o payload trazer um id **diferente**
do que está no banco. O golden ficaria verde provando o contrário do que foi medido.

Ancorada em `"data":{"referenceId":"<ID-NOVO-DO-PAYLOAD>"` — o prefixo `"data":{` só existe na resposta — a
contagem virou 1 e passou.

## Como aplicar

1. Antes de escrever a substituição, **conte à mão** quantas vezes o alvo aparece no bloco. Se for mais de uma,
   o alvo está errado, não a contagem.
2. Ancore no **contexto estrutural** que só existe no lado que muda: `"data":{` para corpo de resposta,
   o prefixo `RES ` / `DB ` da linha, o nome do campo pai. Nunca no valor nu.
3. **Escopar por caso não basta.** A escopagem por bloco resolve "casou no caso errado"; ela não resolve
   "casou nas duas pontas do caso certo". São dois erros diferentes e precisam das duas guardas.
4. Depois de a substituição passar, releia o bloco reconciliado e pergunte: **o `REQ` ainda contradiz o `DB`?**
   Se a contradição que era o achado desapareceu, a substituição comeu a evidência.
5. A guarda de contagem exata **tem de estourar**, não avisar. A mensagem dela deve dizer o que o zero
   significa (golden regravado com a saída do slice → comparação virou espelho) e o que o excesso significa
   (o alvo pegou mais de um lado).
