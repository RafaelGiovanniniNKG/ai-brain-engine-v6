---
rule: Validar um JWT colado exige decodificar o HEADER (parte 0) — checar "3 partes" e o payload não detecta prefixo
origin: sessao 2026-08-03, Onda 5 do OperationalManagement — token do clipboard vinha com "Bearer " colado e eu declarei o token valido
projects: all
confidence: 0.85
confidence_origem: alta (o token passou por duas checagens e o servidor rejeitou com corpo vazio)
status: active
---

## A regra

Ao aceitar um JWT de fonte humana (clipboard, arquivo, variável de ambiente), normalize **antes** de validar:
`Trim()`, remover aspas, remover um prefixo `Bearer ` case-insensitive. E valide decodificando a **parte [0]**,
conferindo que o token **começa com `eyJ`** — não apenas que tem três partes e que o payload decodifica.

## O que aconteceu

O clipboard trazia `Bearer eyJhbGci...`. As duas checagens que eu fiz passaram:

* `Split('.').Count -eq 3` → **passa**, porque o prefixo não contém ponto: as partes ficam
  `["Bearer eyJhbGci…", "<payload>", "<assinatura>"]`;
* decodificar a parte **[1]** → **passa**, e imprimiu `azp`, `preferred_username` e um `exp` de 7,5 horas.

Declarei o token válido. O servidor respondeu **401 com corpo vazio** em toda requisição. O erro real
(`IDX14102: Unable to decode the header ... as Base64Url`) só apareceu no logger de autenticação
(`Api.Authentication.JwtBearer`), porque o handler tira o primeiro `Bearer ` do header e o que sobra ainda
começa com `Bearer `.

O sinal estava visível e eu não olhei: o header de um JWT tem ~30–60 caracteres em Base64Url; ali tinha **118**.

## Como aplicar

1. Normalize sempre: `trim` → tirar aspas → `^(?i)bearer\s+` → `trim`.
2. Valide as **três** partes, não uma. Se só o payload interessa, ainda assim decodifique a [0]: é ela que o
   servidor lê primeiro e a única que detecta lixo colado no início.
3. Cheque `StartsWith("eyJ")` — `{"` em Base64Url sempre começa assim. É a asserção mais barata que existe.
4. Se um 401 vier **com corpo vazio**, não conclua "token expirado" nem "credencial errada": vá ao logger de
   autenticação do servidor. Corpo vazio não distingue "não chegou" de "chegou malformado".
5. Nunca imprima o token. Imprima `len`, `azp`, `preferred_username`, `exp` restante e o tamanho da parte [0].

## Corolário genérico

**Uma validação que aceita a entrada errada é pior que nenhuma**, porque transfere a suspeita para o outro
lado do sistema: gastei o diagnóstico no servidor e na API porque "o token já estava validado".
