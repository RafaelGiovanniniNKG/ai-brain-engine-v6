---
id: texto-impresso-tem-de-caber-no-encoding-do-console
projects: all
confidence: 0.8
last_confirmed: 2026-08-19
status: active
origin: bot-email (2026-08-19), primeira execução real do CLI no Windows — console em cp1252 e seta unicode no relatório
complementa: "comando-que-nao-faz-nada-e-sai-com-zero-parece-sucesso"
---
Texto que o processo **imprime** tem de caber no encoding do console de destino. Um caractere
fora da tabela levanta `UnicodeEncodeError` **depois** de o trabalho estar feito: efeito já
aplicado, exit code de falha, e nenhuma pista da causa no lugar onde se procura.

**Esperado:** o comando imprimir o relatório e sair com 0
**Aconteceu:** `UnicodeEncodeError` no `print` do relatório, **após** as escritas terem sido
aplicadas. O próprio script de diagnóstico morreu do mesmo jeito ao imprimir o achado.

## Por que é pior do que parece

O erro não acontece onde o risco estava. Todo o cuidado tinha ido para as escritas — portão,
dry-run, verificação de efeito — e a falha veio da **última linha**, a que só conta o que
aconteceu. O resultado é a pior combinação possível:

* o mundo **mudou** (mensagens movidas, arquivo escrito, requisição enviada);
* o processo **reporta falha**;
* o relatório que explicaria o que foi feito é exatamente o que não saiu.

Numa tarefa agendada isso é indistinguível de "não rodou", e a decisão seguinte — rodar de novo —
é tomada sem saber que a primeira metade já aconteceu.

No Windows agrava: `sys.stdout` herda o codepage do console (cp1252 é comum), e o mesmo comando
que funciona redirecionado para arquivo UTF-8 quebra quando alguém roda no terminal.

## Como aplicar

1. **Trate o encoding de saída como parte do contrato do texto**, não do terminal de quem roda.
   Seta, elipse, travessão, emoji e box-drawing são a fonte quase inteira do problema — use o
   equivalente ASCII (`->`, `...`) em texto de relatório e de erro.
2. **Blinde o stream de qualquer jeito.** `sys.stdout.reconfigure(errors="replace")` na entrada
   do programa. Mensagem de erro de terceiro (SDK, API, driver) não está sob seu controle, e é
   ela que vai trazer o caractere que você não previu.
3. **Teste a codificabilidade, não a aparência.** `relatorio.to_text().encode("cp1252")` num
   teste é barato, roda em qualquer máquina e reprova antes do usuário. Uma asserção de conteúdo
   ("tem a palavra X") passa verde com o caractere que derruba o `print`.
4. **Escreva arquivo com `encoding` explícito** e nunca dependa do default da plataforma — o
   relatório em disco tem de sobreviver mesmo quando o do console não sobreviveu.
5. **Se houver efeito irreversível antes do relatório, o relatório não pode ser o que quebra.**
   Ordene: aplicar → persistir o registro em arquivo → imprimir. Impressão é a etapa mais
   descartável e tem de ser a última.

## Corolário genérico

**A borda de apresentação também é borda.** Serialização, log, e-mail, terminal, nome de arquivo,
cabeçalho HTTP: em toda saída existe um conjunto de caracteres aceitos, e ele é mais estreito do
que o da sua string. Quando essa borda vem depois de um efeito irreversível, ela deixa de ser
cosmética e passa a ser risco operacional — porque o custo dela não é uma linha feia, é uma
operação sem rastro.
