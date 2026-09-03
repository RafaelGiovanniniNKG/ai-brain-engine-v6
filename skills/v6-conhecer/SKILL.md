---
name: v6-conhecer
description: Conhece um repositório do zero e documenta a arquitetura, os padrões que um arquivo novo tem de imitar, e como rodar aquilo de verdade — tudo no cofre, nada dentro do repositório. Use na primeira sessão dentro de um projeto que ainda não tem nota no cofre, ou quando a nota que existe é velha o bastante para enganar. Não altera código.
---

# Conhecer um repositório

Existe para o começo frio: sessão aberta num projeto que **não tem nota no cofre**. Nesse caso a injeção do início de sessão não tem nada para injetar, e todo o motor fica valendo o mesmo que nada. Esta skill produz a primeira nota; a `v6-curar` cuida dela depois, quando já houver diário.

**Nada é escrito dentro do repositório.** Nem guia, nem arquivo de instrução, nem arquivo de passeio de código. É a regra da casa e não tem exceção: a empresa não aceita, e o motor existe justamente para provar que dá para ter memória sem sujar o repositório de trabalho. Todo o produto vai para `Projetos/<repo>/` no cofre.

Não altera código. Não commita. Se o repositório tiver arquivo de instrução próprio, **leia** — mas não crie um.

---

## Fase 1 — Reconhecimento mecânico (você mesmo, é barato)

Antes de gastar leitura, junte os sinais que um comando dá de graça. Para .NET e Angular, que são a casa:

```bash
git -C <alvo> log --oneline -15                 # o que andou, e em que ritmo
git -C <alvo> ls-files | head -100
git -C <alvo> ls-files "*.csproj" "*.slnx" "*.sln" "package.json" "angular.json"
git -C <alvo> ls-files "*.sql" "*migrations*" "*Migrations*"
git -C <alvo> ls-files ".github/*" "azure-pipelines*" "*.yml"
```

Do que apareceu, extraia: os projetos e a versão de plataforma de cada um, quem é executável e quem é biblioteca, quais são os projetos de teste, o gerenciamento central de pacote se houver, e o que a integração contínua roda. Isso já responde metade das perguntas sem ninguém ler nada.

## Fase 2 — Fan-out por dimensão

Aqui **vale usar agentes**, e é o caso claro: muitos arquivos, e o que volta para você é conclusão, não conteúdo. Dispare num único disparo, todos **somente leitura**, cada um com a dimensão declarada e a ordem de devolver **conclusão com `arquivo:linha`** — sem a âncora você não consegue reconferir, e conclusão que não se reconfere não entra na nota.

1. **Arquitetura e direção de dependência** — quais projetos existem, quem depende de quem *de fato*, o que chega por transitividade, e onde a direção é violada.
2. **Pontos de entrada e composição** — o que sobe: API, worker, aplicativo de mesa, tarefa agendada. Onde cada processo monta as dependências, e se dois processos montam diferente para o mesmo trabalho.
3. **O padrão a imitar** — a pergunta prática: *se eu criar um arquivo novo desse tipo aqui, o que ele tem de parecer?* Nomes, pasta, forma do arquivo, como recebe dependência, como devolve erro. **Uma convenção só conta se aparecer em dois lugares ou mais.** Vista uma vez é hábito de um arquivo, e apontar isso como padrão do projeto faz a nota mentir.
4. **Contratos transversais** — o caminho do erro até a resposta, onde a validação roda, de onde vem a hora (e se é local ou universal, por agregado), o que virou registro de erro, e onde a transação começa e termina.
5. **Dados** — banco, migração versus modelo, SQL escrito à mão e se é parametrizado, e o que está pendente de comando de estrutura — que é decisão do Rafael, sempre.
6. **Testes** — quais projetos, o que roda em máquina limpa, o que depende de Docker, variável de ambiente ou máquina específica, e portanto **o que nunca roda em lugar nenhum**.

## Fase 3 — Rodar, que é a parte que ninguém faz

Documentação de repositório costuma descrever o desenho e mentir sobre a operação. Então **rode** o que dá para rodar, e guarde a saída de verdade:

```bash
dotnet build <alvo>            # ou: npm ci && npm run build
dotnet test <alvo/test/...>    # o projeto de teste, não a suíte inteira
```

Guarde a linha do placar (`Failed: 0, Passed: N`) palavra por palavra. **Se não rodou, a nota escreve "não rodei", não "funciona".** E anote toda armadilha que você pagou no caminho — versão de runtime que obriga avanço de versão, variável de idioma que reprova comparação de saída, porta que o front espera, ordem de comando que importa. É essa seção que economiza a próxima hora de alguém, muito mais que o desenho.

## Fase 4 — Escrever, em dois arquivos com propósitos diferentes

```
Projetos/<repo>/_index.md                      # curto, é o que a sessão injeta
Projetos/<repo>/Arquitetura e padrões (<repo>).md   # longo, lido quando precisa
```

O índice tem **teto de 4.000 caracteres** — não é estética, é o orçamento da injeção de início de sessão, e o que passar é cortado. Meça antes de entregar. Ele leva só o que muda a primeira hora de trabalho:

- frontmatter com `projeto`, `tipo: índice`, `curado_em: <hoje>`;
- o que o projeto é, em duas ou três linhas;
- **antes de rodar qualquer coisa**: as armadilhas da Fase 3;
- os pontos de entrada e o comando que sobe cada um;
- o padrão a imitar, em cinco linhas no máximo;
- trabalho em aberto, com o que está sem commit;
- ponteiro para a nota longa.

A nota longa não tem teto e recebe o resto: o mapa de dependência, os contratos transversais, os dados, o inventário de testes com o que nunca roda, e as conclusões com `arquivo:linha`.

Duas regras de escrita: **sem marcas de versão** (nada de "o que mudou", "antes era assim"), e **trabalho não commitado é pendência, nunca conclusão**.

## Fase 5 — Ligar o repositório ao cofre

Sem isso todo o trabalho fica invisível: registre o par no `mapa.json` do motor, senão a próxima sessão dentro daquele repositório abre sem contexto e alguém vai escrever a nota de novo.

## Fase 6 — Fechar

No chat, poucas linhas: o que o projeto é, as duas ou três armadilhas que mais custam, o que você **não** conseguiu conferir, e onde as notas ficaram. O que não foi coberto tem de ser dito com nome — dimensão ou pasta —, porque silêncio se lê como aprovação.
