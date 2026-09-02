# Como trabalhar nos repositórios do Rafael

Este arquivo fica **acima** de todos os repos em `C:\Github` e é carregado em qualquer sessão
aberta abaixo dele. Vale para tudo. Coisa específica de um projeto mora na nota daquele projeto
no vault, não aqui.

## Idioma e escrita

- Responda sempre em **português do Brasil**.
- Nada de atribuição a IA em mensagem de commit, PR, código ou documento.
- Explique pelo mecanismo, não pelo jargão. Se o desenho é seu e não dele, "camada", "portão" e
  "golden" não comunicam nada — descreva o que acontece.

## Nunca

- **Não rode nada em produção.** Nem leitura "só para conferir", sem pedido explícito.
- **Não altere nem execute SQL em homologação ou produção.** Validação é no ambiente de
  desenvolvimento. DDL é decisão do Rafael, sempre.
- **Não adicione dependência de núcleo com licença paga** (nem "camada grátis" de produto pago).
  Ao recomendar biblioteca ou ferramenta, verifique e declare a licença.
- **Não crie arquivo `.md` de plano, spec ou documentação dentro de repositório de código da
  empresa.** A empresa não aceita. Documento vai para o vault: `C:\Github\obsidian-vault`.
- Não commite nem dê push sem pedido. Se estiver no branch padrão, crie branch antes.

## Antes de afirmar

- **Afirmação de prova aponta o teste que a sustenta.** "Testado", "validado" e "funcionando" só
  com o comando e a saída. Sem isso, diga que não testou.
- **Antes de migrar ou alterar um verbo, execute o legado** e documente o retorno real. Nunca
  inferir o contrato lendo o handler.
- **Antes de escrita irreversível, faça uma leitura que revele o destino efetivo e aborte se não
  for o esperado.** Configuração é intenção; leitura é medição. Indeterminado também aborta.
- Se o build ou o teste falhou, diga que falhou, com a saída. Trabalho parcial se relata como
  parcial.

## Como medir

- Teste do projeto tocado, não a suíte inteira a cada edição.
- `dotnet test` sem exportar `DOTNET_CLI_UI_LANGUAGE` — a variável vaza para o processo de teste
  e reprova golden por mensagem traduzida.
- Emulador e ambiente de desenvolvimento para prova de ponta a ponta; nunca o ambiente real.

## O motor

O `ai-brain-engine-v6` é um plugin instalado nesta máquina: injeta o contexto do projeto no
início da sessão, roda os sensores da stack, barra encerramento sem prova e escreve o registro no
vault. Ele não coloca arquivo nenhum dentro dos repositórios. O plano e as evidências dele estão
em `C:\Github\obsidian-vault\Projetos\ai-brain-engine-v6`.
