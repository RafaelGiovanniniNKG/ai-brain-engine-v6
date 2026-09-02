---
id: antes-de-migrar-ou-alterar-um-verbo-execute-o-le
projects: all
confidence: 0.7
last_confirmed: 2026-07-30
status: active
origin: migracao-operacional Onda 1/2 (2026-07-30): L15 IsRequiredPhoto + Passo 1 CleaningStatusType
---
Antes de migrar ou alterar um verbo, EXECUTE o legado por HTTP na API real, observe status + corpo + o que foi gravado, documente o medido no ledger e congele em GOLDEN. So depois escreva o slice. Nunca inferir contrato lendo o handler.

**Esperado:** o contrato do verbo migrado bate com o do legado
**Aconteceu:** caracterizacao por LEITURA perdeu 3 regras do handler (perda de dado silenciosa) e uma premissa de PK errada que so o E2E pegou

## Ordem obrigatoria por verbo

1. **RODAR o legado** (HTTP na API real, nao unit test) nos casos: caminho felizardo, payload invalido, id inexistente, id duplicado, campo omitido.
2. **OBSERVAR** status + corpo + o que ficou gravado na coluna (inclusive o carimbo de tempo).
3. **DOCUMENTAR** o medido no ledger — o medido, nao o inferido.
4. **GOLDEN**: congelar. Teste que afirma o valor errado e pior que teste ausente, porque cimenta a regressao.
5. Só então escrever o slice.

## Corolarios (todos medidos, nao supostos)

- **Ler o diff de um campo NAO substitui ler o handler inteiro daquele verbo.** O diff mostra onde o NOME aparece; nao mostra a funcao que envolve o valor (`Normalize…`, `?? valorGravado`, checagem de contradicao).
- **Guarda de contrato ViewModel→command e CEGA para o handler.** Ela prova que o campo CHEGA ao command; nao prova que ele e usado, nem como. Campo novo exige as duas verificacoes.
- **Premissa herdada de agregado analogo e suspeita.** No MESMO repo variam: relogio (`DateTime.Now` vs `DateTime.UtcNow`) e geracao de PK (identity vs `ValueGeneratedNever` + linha semeada por `HasData`). Conferir por agregado, sempre.
- **Rodar RED contra o legado ANTES de escrever a asserção.** Escrever a asserção primeiro faz o teste nascer verde afirmando o que eu presumi.
