---
id: sonda-que-reconhece-forma-nao-mede-trabalho
projects: all
confidence: 0.95
last_confirmed: 2026-09-03
origin: 2026-09-03 — sessão de reorganização do cofre: 79 arquivos mexidos, 5 commits e 8 suítes de teste rodadas, e o diário automático do motor gravou "nenhum arquivo editado, nenhum commit, nenhum teste rodado". Quatro sondas caladas ao mesmo tempo, por quatro listas de forma diferentes; medido no código e num repo de teste (`git commit -q` não imprime nada).
status: active
complementa: "saida-nao-zero-nao-dispara-posttooluse", "canario-prova-que-a-sonda-le-nao-que-ela-reporta"
---
Sonda que reconhece trabalho por **lista de formas** — extensão do arquivo, padrão do comando,
linha impressa na saída, diretório de onde perguntar — mede a forma, não o trabalho: qualquer
variação legítima cai fora da lista, e o silêncio da sonda se lê como "nada aconteceu".
Derive do **estado** (o que o git vê sujo, o que o relógio diz), e confira a sonda contra uma
sessão em que o trabalho comprovadamente aconteceu.

## O que aconteceu

Uma sessão inteira mexeu em 79 arquivos, fez 5 commits e rodou 8 suítes (114 casos). O diário
automático do motor registrou, para essa mesma sessão:

> Nada registrado (nenhum arquivo editado, nenhum commit, nenhum teste rodado).

E o portão de encerramento liberou — corretamente, na conta dele: não havia edição pendente de
prova, porque não havia edição nenhuma.

Quatro sondas independentes ficaram cegas ao mesmo tempo, cada uma por uma lista de forma:

| a sonda procurava | por que não achou |
|---|---|
| a linha `[branch sha] mensagem` na saída do `git commit` | o comando foi `git commit -q`, que **não imprime nada** em caso de sucesso |
| a extensão do arquivo em `EXT_CODIGO` | a lista tem `.cs .razor .cshtml .ts .tsx .mts .cts .js .mjs .dart` — **`.md`, `.py` e `.json` não** |
| um padrão de `PADROES_TESTE` | tem `\bpytest\b`, não tem `python <caminho>/prova_x.py` |
| `git status` no repositório do `cwd` da ferramenta | o `cwd` do shell voltava ao repo A a cada chamada, e o trabalho era no repo B — **perguntou no lugar errado** |

O agravante é que o sensor de edição pelo terminal foi escrito **de propósito** para não adivinhar
pelo texto do comando ("script que escreve arquivo passaria batido", diz o comentário dele). O
desenho estava certo. O que o traiu foram as outras três listas — e o `cwd`, que decide em qual
árvore a pergunta correta é feita.

## Como aplicar

1. **Antes de confiar numa sonda, rode-a contra trabalho que você sabe que existe.** Não contra um
   caso sintético: contra uma sessão real de trabalho pesado. Sonda nova nasce presumida cega.
2. **Silêncio nunca é evidência de ausência.** Se a saída de uma sonda pode ser "não vi nada", ela
   precisa de um canário contínuo — algo que, se a sonda emudecer, acende luz.
3. **Prefira derivar do estado.** "O que o git vê sujo desde o início da sessão" continua valendo
   quando alguém escreve por um script, por um editor, ou por uma ferramenta que ainda não existe.
   Lista de extensões, de padrões e de linhas impressas envelhece a cada ferramenta nova.
4. **Quando o estado tem de ser consultado em algum lugar, o "onde" é parte da medição.** Perguntar
   a coisa certa na árvore errada devolve "limpo" com toda a confiança do mundo.
5. **Bandeira de silêncio é bandeira de cegueira.** `-q`, `--quiet`, `--no-progress`, `2>/dev/null`
   economizam ruído e apagam exatamente a linha de que a sonda depende. Se um sensor lê a saída de
   um comando, o comando não pode ser calado — ou o sensor não pode depender da saída.
