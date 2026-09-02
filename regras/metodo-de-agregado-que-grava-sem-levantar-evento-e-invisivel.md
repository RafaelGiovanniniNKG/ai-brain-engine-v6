---
id: metodo-de-agregado-que-grava-sem-levantar-evento-e-invisivel
projects: Projeto-SiStockler.ServiceDesk, POC-cqrs-reference-architecture, Projeto-SiStockler.OperationalManagement
confidence: 0.95
status: active
last_confirmed: 2026-08-14
origin: ServiceDesk (2026-08-14) — sexta ocorrencia da familia num unico dia. `SlaPolicy.DefinirPrazo` gravava os quatro pares de prazo e nao chamava `LevantarMudanca()`; foi ao ar num commit meu e so apareceu porque um reparo de dado nao surtiu efeito.
---
Em CQRS com projecao, **um metodo de agregado que muda estado e nao levanta evento e uma escrita que
nao existe para o resto do sistema**. Os testes de dominio passam (o estado do agregado esta certo),
a API responde 200, o banco de escrita muda — e a tela continua mostrando o valor antigo para sempre.

**Esperado:** ajustar o prazo da prioridade grava e a leitura acompanha
**Aconteceu:** `DefinirPrazo` fazia o `switch`, atribuia os campos e retornava. Nenhum evento. O caso
`Normal` era o pior: escrevia nos MESMOS campos que `AjustarPrazos`, que emite — dois caminhos para o
mesmo dado, um silencioso. Ocorrencias irmas no mesmo dia: `Asset.Criar` sem `LevantarMudanca()`
(ativo criado nunca chegava na leitura) e a politica padrao com dois eventos empatados.

## Como aplicar

1. Todo metodo publico de agregado que ATRIBUI campo termina em `LevantarMudanca()` — ou tem um
   comentario dizendo por que nao. Se o metodo tem `return` antecipado por idempotencia, o evento
   fica depois do guarda, nao antes.
2. O teste que guarda isso conta EVENTOS. Afirmar o estado final passa igual no codigo defeituoso,
   porque a escrita nunca esteve errada — o que faltava era o aviso.
3. `[Theory]` com uma linha por ramo do `switch`. O ramo esquecido e sempre o que ninguem exercitou.
4. Sintoma de campo: um reparo de dado por comando legitimo **nao surte efeito**. Se escrever de
   novo o mesmo valor nao conserta a leitura, ou ha guarda de idempotencia bloqueando o evento, ou
   o metodo nunca emitiu nenhum.

## Corolario generico (vale fora deste repo)

**Guarda de idempotencia + ausencia de evento = divergencia permanente.** Quando a escrita ja esta
com o valor certo, o agregado se recusa a emitir ("nada mudou"), e nenhum comando legitimo consegue
mais consertar a leitura. O dado fica errado de um jeito que so replay ou uma mudanca de ida e volta
desfaz — e e por isso que este defeito nao pode ser tratado como cosmetico.
