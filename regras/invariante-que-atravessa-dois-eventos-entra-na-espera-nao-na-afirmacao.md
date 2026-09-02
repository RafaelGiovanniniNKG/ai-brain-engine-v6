---
rule: Invariante que atravessa DOIS eventos nao pode ser afirmado na hora contra a projecao - ele entra na ESPERA, que converge quando e janela e estoura quando e violacao
origin: sessao 2026-08-18, ultimo dia do Service Desk - o E2E "so ha UMA politica padrao" reprovou 1 em 51 no CI e passou na execucao seguinte, com o modelo de escrita correto
projects: all
confidence: 0.85
confidence_origem: alta (mecanismo deduzido do numero de eventos da operacao, e confirmado por o mesmo codigo passar na execucao seguinte)
complementa: "buffer-alugado-guardado-alem-do-callback-le-memoria-de-outro", "teste-de-tela-precisa-afirmar-em-qual-tela-esta", "canario-prova-que-a-sonda-le-nao-que-ela-reporta"
status: active
---

## A regra

Quando uma operacao troca **quem** detem um estado exclusivo — a politica padrao, o registro ativo, o
lider —, ela quase sempre levanta **dois** eventos: desmarca o anterior, marca o novo. A projecao os
aplica em sequencia, e **entre um e outro existe uma janela em que o invariante aparece violado na
LEITURA com o modelo de escrita perfeitamente correto**.

Afirmar o invariante logo depois da escrita reprova dentro dessa janela:

```csharp
// ERRADO: reprova na janela entre os dois eventos.
var visiveis = await EsperarAsync(client, v => v.Contains(a) && v.Contains(b));
Assert.True(visiveis.Count(x => x.Padrao) <= 1);

// CERTO: o invariante entra na CONDICAO da espera.
var visiveis = await EsperarAsync(
    client,
    v => v.Contains(a) && v.Contains(b) && v.Count(x => x.Padrao) <= 1);
```

**E a retentativa nao mascara violacao de verdade** — e este e o ponto que faz a regra valer: se a
escrita realmente tiver dois padrao, o estado **nunca converge**, a espera estoura e o teste reprova.
A espera e o que **distingue** "ainda nao chegou" de "esta errado". A afirmacao imediata nao distingue:
ela chama os dois de defeito.

## O que aconteceu

`Politica_de_SLA_e_administravel_por_HTTP_e_so_ha_UMA_padrao` reprovou no CI com *"Ha 2 politicas
marcadas como padrao ao mesmo tempo"* — 1 falha em 51. A execucao seguinte, do **mesmo commit**, passou.

O teste ja tinha sido reescrito uma vez, semanas antes, por outro motivo: a primeira versao afirmava
"a padrao e a segunda" e reprovava porque outros testes da mesma classe tambem definem a propria
padrao, e "a padrao" e estado **global**. A reescrita trocou aquilo pelo invariante `<= 1` — correta
quanto a concorrencia entre testes, e ainda cega quanto a **janela da projecao**.

Duas reescritas, duas causas diferentes, o mesmo sintoma. O que faltava nas duas era perguntar
**quantos eventos** a operacao levanta.

## Como aplicar

1. **Conte os eventos da operacao antes de escrever a assercao.** Um evento: pode afirmar depois da
   espera. Dois ou mais: o invariante vai para dentro da espera. A pergunta "quantos eventos?" e mais
   rapida que qualquer depuracao de intermitencia.
2. **Ponha na mensagem de estouro o VALOR observado**, e nao so "nao chegou ao estado esperado". Sem o
   numero, o vermelho nao separa "faltou aparecer um registro" de "dois continuam marcados" — e as duas
   causas pedem investigacoes opostas.
3. **Nao troque o invariante por algo mais fraco** para o teste parar de piscar. `<= 1` dentro da espera
   continua provando a regra; afirmar so "existe pelo menos uma padrao" nao prova nada e passa num
   sistema quebrado.
4. **Suspeite de "esta intermitente" como diagnostico.** Duas vezes no mesmo dia, neste projeto, um
   vermelho intermitente tinha causa determinavel — e as causas eram **opostas**: uma era defeito de
   producao (buffer alugado), outra era teste afirmando cedo demais. Reexecutar teria escondido a
   primeira; mexer no produto teria estragado a segunda.

## Corolario generico

**Consistencia eventual nao atrasa apenas a chegada do dado: ela atrasa a chegada do INVARIANTE.** Um
sistema que garante "no maximo um padrao" garante isso no fim da sequencia de eventos, e nao em cada
instante da leitura — e um teste que ignora essa diferenca esta afirmando algo que o desenho nunca
prometeu.
