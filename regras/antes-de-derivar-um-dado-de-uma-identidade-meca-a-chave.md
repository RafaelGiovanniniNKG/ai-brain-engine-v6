---
rule: Antes de DERIVAR um dado a partir de uma identidade, MECA se a chave que une os dois lados existe
origin: sessao 2026-08-18, unidade organizacional no chamado do Service Desk - o desenho obvio era derivar o setor de quem abriu, e duas consultas mostraram que nenhuma chave casava
projects: all
confidence: 0.85
confidence_origem: alta (tres chaves candidatas testadas, todas com zero casos, e a "obvia" era a que parecia certa)
complementa: "coletor-que-nao-casa-nada-parece-sistema-que-nao-fez-nada", "canario-prova-que-a-sonda-le-nao-que-ela-reporta"
status: active
---

## A regra

"O sistema ja sabe quem e a pessoa, entao ele pode saber o setor dela" e uma inferencia sobre DUAS
tabelas, e ela e verdadeira so se existir uma chave que una as duas. **Meca a chave antes de desenhar
em cima dela** — duas consultas de contagem, cinco minutos:

```sql
SELECT COUNT(*) FROM origem o JOIN destino d ON d.chave = o.chave;   -- para CADA candidata
```

Se o resultado for zero, voce acabou de economizar uma porta, um caso de uso, um teste e uma tela —
e evitou entregar um campo que grava nulo para todo mundo. **Um recurso que nao preenche nada nao se
le como "falta dado"; le-se como defeito**, e o proximo a olhar vai depurar codigo que esta correto.

Derivacao que nao resolve e PIOR que campo escolhido a mao: o campo escolhido funciona hoje e melhora
quando o dado chegar; a derivacao vazia parece pronta e nao funciona nunca.

## O que aconteceu

O chamado precisava dizer de que setor vem. O desenho obvio: o token identifica a pessoa, a pessoa
esta no HCM, o HCM tem `codLoc`, o `codLoc` e o no da arvore — logo, derive. Ninguem deveria ter de
dizer em que setor trabalha.

Tres chaves candidatas, medidas na base local:

| chave | casos |
|---|---|
| e-mail (`read.People.Email` = `read.Colaboradores.Email`) | **0** de 5 |
| matricula (`Matricula` = `IdSistockler`) | **0** de 505 |
| `numCad` (ultimo segmento da matricula) | **0** de 505 |

O e-mail era o candidato serio, e falhou por dois motivos somados: 455 dos 505 colaboradores nao tem
e-mail comercial preenchido no HCM, e nenhuma das 5 pessoas que ja usaram o sistema esta entre os 50
que tem. A matricula tem a forma `1/1/301342` — `empresa/filial/numCad` —, e o `numCad` tem 6 digitos
enquanto o `idSistockler` de quem estava logado tem 3: sao contadores de sistemas diferentes, e
nenhuma normalizacao os aproxima.

A fatia virou "unidade ESCOLHIDA na abertura", com um seletor opcional. Funciona hoje, e no dia em
que o RH preencher o e-mail comercial a derivacao entra como PADRAO do campo — sem desmanchar nada.

## Como aplicar

1. **Liste as chaves candidatas antes de escrever a primeira linha** e conte cada uma. Uma contagem
   por candidata; nao pare na primeira que "deve funcionar".
2. Conte tambem a **cobertura da coluna** (`SUM(CASE WHEN x IS NOT NULL...)`) e nao so o casamento:
   uma chave pode casar 100% das linhas preenchidas e cobrir 10% da tabela. As duas perguntas sao
   diferentes, e a segunda e a que decide se o recurso funciona para as pessoas.
3. Meca com as linhas de VERDADE, incluindo a sua propria. Foi olhar o proprio registro — e ver que
   nem ele casava — que fechou a duvida.
4. Quando a chave nao existe, **entregue a versao explicita e escreva no codigo por que**. O comentario
   precisa dizer o numero medido e a data: sem isso, o proximo a passar reabre a discussao do zero, ou
   pior, "conserta" implementando a derivacao vazia.
5. Nao registre a impossibilidade so no commit. Ela vira **comentario no dominio, no contrato e no
   teste** — nos tres lugares onde alguem tentaria derivar.

## Corolario generico

**Toda derivacao e uma juncao disfarcada.** Enquanto ela e uma frase em portugues — "o sistema pode
saber o setor da pessoa" — parece uma questao de esforco. Escrita como `JOIN`, ela passa a ter um
numero, e o numero as vezes e zero.
