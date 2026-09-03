---
name: v6-pr
description: Valida um Pull Request inteiro — correção, padrão do repo, arquitetura e testes — a partir de um PR do Azure DevOps (ID ou URL), do GitHub, de uma branch local ou de um diff colado. Roda os sensores mecânicos antes dos revisores, dispara revisores em paralelo com focos declarados, verifica cada achado e corta o que tem confiança abaixo de 80. Entrega parecer em português com veredito. Não commita, não dá push, não vota no PR. Use quando o Rafael mandar um PR para validar ou revisar.
---

# Validar um PR

Irmã da `v6-revisar`. A diferença é a entrada e o escopo: a `v6-revisar` olha o diff da branch em que você está; esta resolve **um PR de verdade** (Azure, GitHub, branch ou diff colado), lê a descrição e o alvo do merge, e cobre dois eixos que a outra não cobre — **arquitetura** e **testes** — porque num PR o que passa aqui vira o padrão do repositório amanhã.

É **só leitura**. Nunca commita, nunca dá push, nunca faz merge, nunca vota nem aprova. Se ele pedir para aplicar correção, aplica no diretório de trabalho e sem nenhuma referência a IA em código, comentário ou mensagem.

## Uso

```
/v6-pr 4168                              # ID do Azure, rodando dentro do repo clonado
/v6-pr <URL do PR>                       # Azure DevOps ou GitHub
/v6-pr <branch> [vs <base>]              # diff local; base = master ou main
/v6-pr                                   # a branch atual contra a base
```

Faltou contexto (qual repo, qual base)? **Pergunte antes.** Não chute e não revise o diff errado.

---

## Fase 0 — Resolver o PR em diff, arquivos e intenção

Você precisa de quatro coisas: o **diff**, a **lista de arquivos**, **base e origem** (para abrir o arquivo inteiro quando o diff não der contexto) e a **descrição do PR** — sem ela você revisa o código sem saber o que ele deveria fazer, e aí só sobra gosto pessoal.

### Azure DevOps

A extensão `azure-devops` está instalada. Rode de dentro do repositório clonado; o `az` acha organização e projeto pelo remote.

```bash
az repos pr show --id <id> --organization https://dev.azure.com/stockler-it \
  --query "{titulo:title, autor:createdBy.displayName, origem:sourceRefName, base:targetRefName, descricao:description, status:status}" -o json
```

Duas armadilhas medidas neste ambiente:
- **`status` é quem diz se o PR foi mergeado.** `lastMergeCommit` e `mergeStatus` descrevem o merge de *pré-visualização* que o Azure calcula sozinho — já foi lido errado aqui. Com `status: active`, correção vai na branch do PR.
- Se o `az` falhar por autenticação, **avise na hora** e caia para a branch local. Não fique tentando em laço.

Com base e origem em mão, gere o diff localmente — é mais confiável que puxar o patch pela API:

```bash
git fetch origin
git diff origin/<base>...origin/<origem>
git diff --stat origin/<base>...origin/<origem>
```

O `...` de três pontos é obrigatório: ele mostra só o que a feature mudou desde que divergiu. Com dois pontos, tudo que entrou na base depois aparece como se fosse do PR.

### GitHub

Só se o `gh` existir (`command -v gh`); senão, avise e use a branch local.

```bash
gh pr diff <numero ou url>
gh pr view <numero ou url> --json title,author,baseRefName,headRefName,body
```

### Branch local ou diff colado

```bash
git fetch origin
git diff origin/<base>...<branch>
```

A base padrão do SiStockler é `master`; confira com `git symbolic-ref refs/remotes/origin/HEAD`. Diff colado usa-se direto, e quando faltar contexto peça o caminho do repositório.

**Antes de seguir:** se o diff passar de ~2.000 linhas, diga o tamanho e **proponha fatiar por pasta ou por tema**. Revisor com diff gigante devolve ruído, e ruído faz o parecer inteiro ser ignorado.

---

## Fase 1 — Aterrar o julgamento no repositório, não em regra genérica

Duas fontes, as duas obrigatórias.

**As regras da casa**, que os repositórios da empresa não têm em arquivo e não podem ter:

```bash
python <plugin>/hooks/regras.py --repo <caminho do alvo> --completo
```

Cole a saída inteira no prompt de **cada** revisor. Sem isso eles revisam por gosto geral — e é o gosto geral que produz achado inútil.

**O padrão observado no alvo.** Leia o que existir de `.editorconfig`, `Directory.Build.props`, `Directory.Packages.props`, analisadores, `.eslintrc*`, `pyproject.toml`. Depois abra **dois ou três vizinhos já existentes do mesmo tipo** dos arquivos que mudaram — outro handler, outro controller, outro componente — e anote de 3 a 6 convenções concretas. São elas que viram critério no eixo de padrão. Convenção que você não conseguiu observar em nenhum vizinho **não é convenção do projeto**, é preferência sua: não reporte.

---

## Fase 2 — Sensores primeiro (o que é fato não gasta revisor)

```bash
slopwatch analyze -d <alvo> --baseline <plugin>/sensores/slopwatch/baseline-<repo>.json
python <plugin>/sensores/camadas/assert_refs.py --repo <alvo>
```

O que o sensor achou entra no parecer como **fato**, com o comando que o produziu, e não passa pela verificação de confiança. Sensor sem base de comparação sai com erro e barraria tudo pelo motivo errado — se a base não existir para este repositório, diga que o sensor ficou de fora em vez de inventar um resultado.

Se o repositório tiver testes de arquitetura, rode-os: eles são a opinião do próprio time sobre a estrutura, e um PR que os quebra já tem veredito.

---

## Fase 3 — Revisores em paralelo, focos declarados

Dispare **num único disparo** os que se aplicam. Use os agentes que existem nesta máquina — `ai-brain-engine-v6:csharp-reviewer` para `.cs`, e agente de propósito geral com o **foco escrito no prompt** para os outros eixos. Nunca chame revisor por um nome que você não viu na lista de agentes: agente inexistente falha em silêncio e o eixo fica sem revisão nenhuma.

Cada revisor recebe: o bloco de regras da Fase 1, as convenções observadas, a descrição do PR e o escopo (arquivos + base/origem).

1. **Correção** — bug real, borda, nulo, `await` faltando, concorrência, transação no lugar errado, segurança.
2. **Padrão do repositório** — só contra as convenções observadas na Fase 1.
3. **Arquitetura** — o eixo que a revisão comum não faz. No recorte do diff:
   - **direção de dependência** que o PR introduziu, inclusive por transitividade (o pacote que entrou arrasta o quê?);
   - **composição e DI**: registro novo sem consumidor, consumidor sem registro, tempo de vida suspeito, e *composition root* divergente entre processos — o mesmo comando despachado por API e por worker se comporta diferente, e behaviors valem por processo;
   - **segundo caminho para a mesma coisa**: dois despachantes, dois lugares que publicam o mesmo evento, dois relógios. A resposta errada aqui é silenciosa;
   - **consequência operacional**: fila, outbox, estado terminal sem leitor, retry sem teto, health check que mente, alerta cujo próprio canal pode estar fora;
   - **dados**: SQL parametrizado, índice para a consulta que o código novo faz, crescimento sem purga, migração versus modelo, e DDL — que é decisão do Rafael, sempre;
   - **antes de desregistrar ou apagar handler legado**, mapear *todos* os despachantes do comando, não só a rota.
4. **Testes** — cobertura é o começo, não o eixo. Procure:
   - o que mudou e não tem teste, e teste sem asserção que discrimine;
   - **teste que não consegue reprovar**: golden cujo estado inicial já satisfaz a asserção, mock do próprio objeto sob teste, asserção que passa com qualquer valor;
   - **semeadura com chave fixa**, que passa na primeira execução e acusa a migração pelo resíduo da segunda;
   - **espera fixa antes de publicar** em teste de fila: não deixa o teste lento, *reprova* sob carga, porque publicação sem assinante é descartada. Espere a condição e faça da espera uma pré-condição;
   - **teste que nunca roda em máquina alguma** — condicionado a Docker, variável de ambiente ou host fixo;
   - em golden, **valor cumulativo virando delta**, e divergência que move um valor exigindo os dois lados no relatório.

Todo achado sai com **arquivo:linha**, severidade, a consequência concreta (entrada → efeito) e a correção com **critério de pronto executável** — um comando que ou passa ou não. "Melhorar o tratamento de erro" não é critério de pronto.

---

## Fase 4 — Verificar cada achado antes de reportar

Um verificador barato por achado, com rubrica de 0 a 100. **Corte abaixo de 80.** Perguntas: o consumidor apontado existe mesmo? chega por transitividade? é decisão já registrada no repositório ou no cofre? o golden congela isso de propósito? qual o modo de falha da correção proposta? o arquivo citado tem essa linha?

O que não sobreviver, cai — e não vai para o parecer nem como observação. Achado que o verificador derrubou e você reportou "só para constar" é exatamente o ruído que esta fase existe para matar.

---

## Fase 5 — O parecer, em português

```
## PR <id> — <título>
Base: <base> → Origem: <origem>  |  Arquivos: <n>  |  Linguagens: <...>  |  Situação: <status>

**Veredito:** aprovar · aprovar com ressalvas · pedir mudanças
<duas linhas: o que o PR faz e o estado geral>

### Fatos dos sensores
- <o que a ferramenta apontou> — `<comando que produziu>`

### Correção
- [crítico] arquivo.cs:42 — <consequência: entrada → efeito> → <correção> · pronto quando: `<comando>`

### Arquitetura
### Testes
### Padrão do repositório
### Sugestões (opcionais, fora do escopo do PR)

### Olhado e sem achado
<o que foi coberto e está certo, para ninguém reabrir>

### Fora da revisão
<eixo, pasta ou sensor que não foi coberto, e por quê>
```

Severidade: crítico (quebra, perda de dado, segurança), alto, médio, baixo. Ordene cada seção. Seção vazia recebe "nada a apontar" — **não invente achado para preencher**. As duas últimas seções não são enfeite: sem elas, ninguém sabe se o silêncio é aprovação ou omissão.

Feche oferecendo: *"quer que eu aplique alguma dessas correções?"* — e só toque no código depois do sim.

## Regras

- Nunca commitar, dar push, mergear, votar ou aprovar. Se ele pedir para comentar no PR do Azure, só `az devops invoke` autentica (Bearer cai na tela de login), e o corpo precisa dos escapes `\uXXXX` senão o CLI come os acentos.
- Nenhuma referência a IA em código, comentário, mensagem de commit ou no parecer.
- Sem `arquivo:linha`, não reporta.
- Travou — autenticação, repo não clonado, base ambígua? Avise na hora e ofereça o caminho alternativo. Não fique moendo sozinho.
