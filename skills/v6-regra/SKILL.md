---
name: v6-regra
description: Registra uma regra viva a partir de uma falha real que acabou de acontecer, para o motor injetar essa lição no início de toda sessão futura e nos revisores. Também confirma regra antiga que voltou a se provar, e lista as que estão perdendo confiança por falta de uso. Use quando algo deu errado por um motivo que vai se repetir, ou quando o Rafael disser para registrar o aprendizado.
---

# Registrar uma regra viva

As regras vivas são o único caminho pelo qual uma lição sobrevive à sessão. O motor as injeta no início de **toda** sessão e as cola no prompt de **todo** revisor — porque os repositórios da empresa não têm arquivo de instrução e não podem ter. São 39 hoje, uma por arquivo em `regras/`.

**Regra só nasce de dor real.** Não de boa prática lida, não de preferência, não de "seria bom se". O campo `origin` é obrigatório e tem de apontar a sessão, o commit ou o incidente que a originou — regra sem origem é dogma, e dogma envelhece sem ninguém notar.

## O gatilho: o que merece regra

Merece quando as três coisas valem juntas:

1. **Aconteceu de verdade**, e você pode dizer o que se esperava e o que aconteceu.
2. **Vai se repetir** — a causa é do ambiente, da ferramenta ou do desenho, não distração de uma vez.
3. **Não estava óbvio antes.** Se qualquer pessoa acertaria de primeira, não é regra: é descuido.

Não merece: o que o código já registra, o que o histórico do git conta, o que só valia para aquela tarefa. E não merece uma regra nova se **já existe uma que cobre** — nesse caso, confirme a que existe (abaixo).

## Como se escreve

Um arquivo em `regras/<slug>.md`:

```markdown
---
id: <o mesmo slug>
projects: all              # ou o nome da pasta do repositório onde vale
confidence: 0.9            # quanto você confia hoje, de 0 a 1
last_confirmed: 2026-09-03 # a data de hoje
origin: <o que se esperava, o que aconteceu, e onde ver — sessão, commit ou incidente>
status: active             # só `active` é carregado
---
A lição em modo imperativo, 1 a 3 linhas, começando pelo que fazer ou não fazer.
```

**A primeira frase é a regra inteira.** A injeção do início de sessão mostra só a manchete — o corpo não vai. Então uma regra cuja primeira frase é contexto ("Durante a migração do módulo X, percebemos que…") chega ao modelo como ruído. Comece pela ordem, e deixe o porquê para a segunda linha.

E escreva o **mecanismo**, não a categoria. "Cuidado com configuração" não muda decisão nenhuma; "componente que monta a própria configuração ignora a variável de ambiente que você setou, e pode apontar para produção" muda.

## Confiança e decaimento

A confiança cai **0,02 por semana** desde a última confirmação, e abaixo do mínimo a regra deixa de ser injetada. Isso é de propósito: aprendizado que nunca é reinjetado é aprendizado morto, e aprendizado que nunca decai é dogma.

Então, quando uma regra antiga **volta a se provar**, o certo não é criar outra: é atualizar `last_confirmed` para hoje e, se for o caso, subir a `confidence`. Diga isso ao Rafael com a data antiga ao lado da nova — é o registro de que a lição continua viva.

## Promoção de escopo

Regra que já se provou em **dois projetos ou mais** e está com confiança 0,8 ou acima é candidata a `projects: all`. Proponha; a promoção é decisão dele, não sua.

## O critério de pronto, que é executável

Escrever o arquivo não é terminar. **Uma regra que não carrega é pior que uma regra que não existe**, porque parece que a lição está guardada — e já houve um defeito em que o carregador lia uma pasta inexistente e nenhuma regra era reinjetada, em silêncio. Então prove:

```bash
python <plugin>/hooks/regras.py --repo <caminho do repositório onde ela deve valer>
```

A manchete da regra nova tem de aparecer na saída, com a confiança ao lado. Se não apareceu, o problema é o frontmatter — `status`, `projects` ou a data — e não a redação.

## Fechar

Mostre o arquivo gerado, a saída do comando acima com a regra dentro, e diga em uma linha qual sessão ou commit ela guarda. Se ele discordar da redação, a dele vale: é a lição dele que está sendo escrita.
