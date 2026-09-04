---
id: comentario-so-para-o-que-o-codigo-nao-consegue-dizer
projects: all
confidence: 0.9
last_confirmed: 2026-09-04
origin: 2026-09-04 — padrão declarado pelo Rafael, com estas palavras: "nunca comente no codigo, so se for extritamente necessario, codigo bem feito nao precisa de explicaçao comentada". Não é post-mortem de defeito: é o padrão da casa, e vale para todo código que eu escrever nos repositórios dele.
status: active
---
**Não escreva comentário que explica O QUE o código faz.** Se a leitura não basta, o conserto é
renomear, extrair função ou mudar a estrutura — não anotar por cima. Comentário só se justifica
para o que o código **não consegue dizer**: o porquê de uma decisão contraintuitiva, a armadilha
que já custou tempo, o motivo de a ordem importar, o número que veio de uma medição.

## Por que isto e não "comente bem"

Comentário que descreve o código é uma segunda cópia da mesma informação, e as duas copias
divergem: o código muda no `git`, o comentário fica. Aí ele passa a **mentir com aparência de
documentação** — e quem lê acredita nele, porque comentário parece intenção declarada. Um nome
ruim com comentário explicando continua sendo um nome ruim, agora com manutenção dobrada.

## O teste, antes de escrever a linha

Pergunte: **isto está no código?**

- Se está — apague o comentário e melhore o código. `// incrementa o contador` sobre `i++`,
  `// retorna o cliente` sobre `return cliente`, um cabeçalho que repete a assinatura do método.
- Se **não está em lugar nenhum** — escreva, e escreva o mecanismo. "Aborta se o `OnConfiguring`
  for construído sem opções: sem isso ele monta a própria conexão e pode apontar para produção"
  não está no código, e não tem como estar.

## O que fica, sem discussão

1. **A armadilha medida.** O que já custou uma sessão e não se deduz lendo. Com o número, se houver.
2. **O porquê de uma escolha que parece errada.** Código que parece um erro e não é vai ser
   "consertado" por alguém — inclusive por mim, seis semanas depois.
3. **A ordem que importa.** "Roda ANTES do registro de execução: senão o portão barra trabalho que
   acabou de ser provado."
4. **O contrato que o tipo não expressa**, e a referência externa: número de incidente, PR, CVE.

## O que não fica

Cabeçalho de arquivo com autor e data (o `git` sabe), seção comentada em vez de apagada (o `git`
guarda), `// TODO` sem dono nem prazo, tradução do nome do método, e comentário de "o que mudou"
— isso é mensagem de commit, não código.

## Nos repositórios da empresa

O código existente tem comentário demais em vários lugares. **A regra vale para o que eu escrevo,
não para uma limpeza que ninguém pediu**: não adicione comentário novo do tipo proibido, e não saia
apagando comentário alheio dentro de um PR que existe para outra coisa.
