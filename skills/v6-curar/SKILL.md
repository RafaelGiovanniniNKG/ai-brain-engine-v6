---
name: v6-curar
description: Promove o diário automático do projeto a conhecimento curado — propõe uma nova nota-índice AO LADO da atual (nunca por cima), para o Rafael comparar e aprovar. Também confere o orçamento da memória automática e propõe poda dos diários velhos. Use quando o diário acumulou sessões, quando o motor avisar que o índice da memória está perto do teto, ou quando o Rafael pedir para curar/organizar a documentação de um projeto.
---

# Curar: do diário automático para o conhecimento curado

O diário se escreve sozinho e é **descartável por construção**. A nota-índice é o oposto: é ela que o motor injeta no início de toda sessão, e é o artefato de maior sinal que existe. Esta skill é a ponte entre os dois, e ela **propõe**, nunca decide.

## Regra de ouro

**A nota-índice atual nunca é modificada por você.** A proposta vai para um arquivo ao lado, e o Rafael compara e aprova. Isso é copiado do produto equivalente da Anthropic, cuja regra é literal: *"a loja de entrada nunca é modificada, então você pode revisar a saída e descartar se não gostar"*.

E: **curadoria se expressa como foco e exclusão, não como comando de edição de linha.** Passe de síntese ignora instrução do tipo "mude a frase X para Y".

## Passos

### 1. Descobrir o alvo
Se o Rafael não disse o projeto, use o repositório da sessão atual (`git rev-parse --show-toplevel`). Ache a pasta dele no vault por `ai-brain-engine-v6/mapa.json`. Se não houver pasta, **pare e pergunte** — criar pasta nova de projeto é decisão dele.

### 2. Ler o que existe (nesta ordem)
1. `_index.md` da pasta (ou a nota `Índice — …` / `Visão Geral …` legada). É a base a superar, não a apagar.
2. `_diario/*.md` com data **posterior** ao `curado_em` do frontmatter do índice. Se não houver `curado_em`, pegue os últimos 14 dias.
3. Os commits do período: `git log --oneline --since=<data do curado_em>`.

Se não houver diário novo desde a última curadoria, **diga isso e pare**. Curar sem material novo só embaralha o que já estava bom.

### 3. Confrontar com a realidade antes de escrever
O diário registra o que foi feito; ele **não** sabe o que ficou verdade depois. Antes de promover qualquer afirmação:
- confira contra o estado atual do repo (`git status`, `git log -1`, o arquivo citado ainda existe?);
- afirmação de prova só sobe se o diário trouxer o placar (`Failed: 0, Passed: N`). Sem número, escreva "não verificado";
- trabalho não commitado é **pendência**, nunca conclusão.

### 4. Escrever a proposta
Grave em `_index.proposto.md`, na mesma pasta. **Teto de 4.000 caracteres** (cerca de 60 linhas) — não é estética: é o orçamento de injeção do início de sessão, e o que passar dele é cortado. Meça antes de entregar. Estrutura:

- **Frontmatter**: `projeto`, `tipo: índice`, `curado_em: <hoje>`, `tags`. Plano, valores citados quando tiverem `:` ou acento.
- **O que é o projeto**, em duas ou três linhas.
- **Antes de rodar qualquer coisa**: as armadilhas que fazem perder tempo (ambiente, ordem de comandos, o que parece defeito e não é).
- **Trabalho em aberto**, com o que está sem commit e o que aguarda decisão dele.
- **Decisões travadas**, com o porquê — sem o porquê a decisão volta a ser discutida.
- **Ligações** `[[...]]` para as notas de tema.

Corte sem piedade: se uma linha não mudaria a ação de quem lê amanhã, ela não entra. O que sair do índice **não se apaga** — vira ou fica numa nota de tema.

### 5. Mostrar a diferença e esperar
Apresente ao Rafael, em texto: o que **entrou**, o que **saiu** e o que **mudou de conclusão** (o mais importante — é onde a documentação estava mentindo). Depois pare e espere.

Só quando ele aprovar: mova a proposta sobre o índice (`_index.proposto.md` → `_index.md`) e diga o que fez.

### 6. Orçamento da memória automática
Leia `autoMemoryDirectory` de `~/.claude/settings.json` e meça o `MEMORY.md` de lá.

**O teto é 200 linhas ou 25.600 bytes, o que vier primeiro — e o que passa disso deixa de ser carregado, em silêncio.** Se estiver acima de 160 linhas ou 20.480 bytes, proponha (e só proponha):
- fundir as linhas que falam do mesmo assunto;
- aposentar as que descrevem trabalho terminado há mais de 60 dias, movendo a nota para o vault;
- reescrever as mais longas em uma linha, mantendo o gancho.

Meça e mostre o antes e o depois em números. Nunca apague nota — mover é reversível, apagar não.

### 7. Poda do diário
Diários com mais de 30 dias já cumpriram o papel. Liste quantos são e o período, e **pergunte** antes de apagar. Se ele aprovar, apague só os que já estão refletidos no índice.

## O que não fazer

- Não escrever sobre `_index.md` sem aprovação explícita.
- Não apagar diário, nota ou linha de memória por conta própria.
- Não promover afirmação sem prova: sem placar, é "não verificado".
- Não inventar decisão que o diário não registra. Ausência de decisão se escreve como "nada registrado".
- Não deixar o índice passar de 4.000 caracteres. Acima disso ele é cortado na injeção, e o que foi cortado não existe para o modelo.
