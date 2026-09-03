---
name: v6-arquitetura
description: Valida a arquitetura de um repositório .NET inteiro e entrega achados numerados com evidência arquivo:linha, consequência concreta e critério de pronto executável — direção de dependências, composição e código morto, contratos transversais, operacional, dados e testes como guarda. Somente leitura no alvo; o relatório vai para o cofre. Use quando a pergunta é "esta arquitetura está saudável?" — para "este PR está bom?" use v6-pr.
---

# Validar a arquitetura de um repositório

A pergunta aqui não é se o código segue um padrão externo: é **onde a arquitetura está doente, com que evidência, e como curar com critério verificável**. A régua é a coerência interna do próprio repositório, as decisões já registradas nele, e a consequência mensurável de cada desvio.

Irmã da `v6-pr`, que olha arquitetura só dentro do diff de um PR. Esta varre o repositório todo.

**Somente leitura no alvo.** Nenhum arquivo é escrito lá — nem o relatório. Ele vai para `Projetos/<projeto>/Validação de arquitetura — <data>.md` no cofre, como nota normal do projeto: o relatório é registro do que foi medido, não plano, e é para ser lido junto das outras notas do projeto. Build ou teste só com autorização explícita dele; ler metadados (`csproj`, `project.assets.json`, `git grep`) é livre.

## Os princípios, cada um nascido de um erro real de auditoria

1. **Evidência ou silêncio.** Todo achado cita `projeto/arquivo:linha`. Sem isso não entra — nem como observação.
2. **Tipo não é pacote.** Antes de propor remover uma referência de projeto "sem uso", confira o grafo de pacotes (`obj/project.assets.json`) e os símbolos que só chegam por transitividade — `SqlException`, extensões relacionais, ligação de configuração. O achado tem de **prever o pacote a declarar** junto com a remoção: "só tirar" quebra o build. E ao mexer em tipo de saída de projeto, confira instruções de nível superior no `Program.cs` antes de dizer que a troca é trivial.
3. **Morto se prova, não se presume.** Para chamar código de morto, três evidências: zero registro em **todos** os pontos de composição (a API e cada worker, separadamente), nenhuma varredura de assembly que o alcance, e nenhuma referência fora de comentário ou texto. **Teste que o usa como objeto sob teste conta como consumidor** — a cobertura se transfere antes de apagar, não depois.
4. **Alcançabilidade real.** "Use o componente X que já existe" só vale se o consumidor proposto consegue referenciá-lo na direção certa. Diga **onde** ele teria de morar.
5. **Critério de pronto executável.** Cada achado termina com um comando ou teste que decide. Se depender de ambiente, credencial ou comando de estrutura de banco, diga **de quem** é a ação — comando de estrutura é decisão do Rafael, sempre.
6. **Decisão registrada não é achado.** Comentário explicativo, valor congelado em comparação de saída, regra viva, divergência deliberada documentada — tudo isso é decisão. Vai para "olhado e sem achado", e não se reabre. Mensagem ou ordem congelada em comparação de saída não se "corrige".
7. **Consequência operacional antes de recomendar.** Valide o desenho no **modo de falha**, não no caminho feliz: verificação de vida que derruba a rota inteira, alerta cuja chave de agrupamento muda a cada ciclo, vigia que só roda dentro do processo que ele vigia.

## Fase 0 — Inventário mecânico (você mesmo, é barato)

```bash
grep -rn "ProjectReference\|TargetFramework\|OutputType" --include=*.csproj . | grep -v "/bin/\|/obj/"
grep -rn "RegisterServicesFromAssembl\|AddValidatorsFromAssembly\|AddOpenBehavior" --include=*.cs . | grep -v "/bin/\|/obj/\|Tests"
grep -rn "TODO\|throw new NotImplementedException" --include=*.cs . | grep -v "/bin/\|Tests" | head -40
grep -rln "NetArchTest\|ArchUnit\|LayerDependency" --include=*.cs .
python <plugin>/sensores/camadas/assert_refs.py --repo <alvo>
```

O que a Fase 0 aponta é **hipótese**, nunca achado. Segue para a Fase 2.

## Fase 1 — Fan-out por dimensão

Agentes somente leitura, em paralelo, um foco declarado cada, todos recebendo as regras da casa (`python <plugin>/hooks/regras.py --repo <alvo> --completo`). Dimensões:

1. **Camadas e dependências** — direção real entre projetos, acoplamento por transitividade, e se as regras que os testes de arquitetura declaram são as mesmas que o código obedece.
2. **Composição e código morto** — registro contra classe existente, tempo de vida suspeito, pontos de composição divergentes entre processos, e a prova tripla do princípio 3.
3. **Contratos transversais** — ordem e contrato dos comportamentos do pipeline; transação (isolamento, nova tentativa, rastreador de mudanças em reprocessamento); validação (onde roda e o que custa quando falha); relógio (fonte única? universal ou local, por agregado?); registro (nível, correlação, o que virou erro).
4. **Operacional** — caixa de saída e filas: estado terminal tem leitor? nova tentativa tem teto e carta morta? travas e múltiplas instâncias; verificação de vida (a semântica de degradado contra inoperante, e quem observa de fora); alerta (o canal é alcançável? tem agrupamento? qual o modo de falha do próprio alerta?); número de configuração que dois processos compartilham e um deles mudou.
5. **Dados** — SQL escrito à mão é parametrizado? há índice para a consulta que o código novo faz? crescimento sem expurgo; migração contra modelo; comando de estrutura pendente e de quem é.
6. **Testes como guarda** — o que pegaria uma regressão estrutural (ordem do pipeline, registro no contêiner, contrato de evento); o que a comparação de saída congela; teste condicionado a Docker, variável ou máquina — e portanto **o que nunca roda em lugar nenhum**; verde no vácuo (objeto sob teste substituído por simulação, asserção que não discrimina).

## Fase 2 — Refutar antes de reportar

Para cada hipótese, pergunte: quem consome isso? chega por transitividade? é decisão registrada? a comparação de saída congela de propósito? o consumidor proposto alcança? qual o modo de falha da **correção** proposta? O que não sobreviver, cai.

E lembre do que o próprio motor mediu: **quem escreveu e quem revisa carregam o mesmo ponto cego.** Refutação feita pelo mesmo raciocínio que gerou a hipótese não refuta nada — procure o fato que contradiz, no arquivo, não o argumento que convence.

## Fase 3 — O relatório, no cofre

- **Achados numerados**, em **grupos independentes** com ordem de execução dentro de cada grupo. Cada um: dimensão, evidência `arquivo:linha`, consequência concreta (entrada → efeito), correção com critério de pronto executável, risco da correção, e dependência de outros itens.
- **Olhado e sem achado** — o que foi coberto e está certo, para ninguém reabrir.
- **Dívidas já registradas, reconfirmadas** — separadas dos achados novos.
- **O que ficou de fora** — dimensão ou pasta não coberta, dita com nome. Corte silencioso faz o silêncio parecer aprovação.

No chat, entregue só o resumo e o caminho do relatório: a lista inteira no chat não se lê e não se reencontra depois.
