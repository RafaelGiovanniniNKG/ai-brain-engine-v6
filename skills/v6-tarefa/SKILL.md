---
name: v6-tarefa
description: Conduz uma mudança de código no tamanho certo de cerimônia — pequena vai direto, média tem plano no chat com um sim explícito, grande tem especificação e plano no vault atrás de portão de aprovação. Use quando o Rafael pedir uma feature, correção ou refatoração e não estiver claro quanto ritual a tarefa merece; ou quando ele pedir explicitamente para planejar antes de fazer.
---

# Tarefa, no tamanho certo

O fluxo do v5 rodou **5 vezes em 60 sessões**. Não foi indisciplina dele: o ritual era pesado demais para o dia a dia, então ele desviava — e desviar significava trabalho sem registro e sem revisão. Esta skill existe para o ritual **caber na tarefa**.

Regra que vale para os três tamanhos: **nada de plano, spec ou documento dentro do repositório da empresa.** Vai para o vault ou fica no chat.

## Primeiro: escolher o tamanho — e dizer qual escolheu

| Tamanho | Como reconhecer | Cerimônia |
|---|---|---|
| **Pequena** | O diff se descreve numa frase. Um arquivo, ou poucos, sem decisão de desenho. Correção óbvia, renomeação, ajuste de texto. | Nenhuma. Faz, roda o teste, entrega. |
| **Média** | Dois a cinco arquivos, ou existe uma escolha de desenho com mais de um caminho razoável. | Plano curto **no chat**, e um "sim" explícito dele antes de escrever código. |
| **Grande** | Toca contrato de API, schema, mensageria; ou é migração; ou vai levar mais de uma sessão. | Especificação e plano **no vault**, portão de aprovação, implementação em fatias com prova por fatia. |

Anuncie o tamanho em uma linha e o motivo. Se ele discordar, o dele vale. Em dúvida entre dois, **escolha o menor e diga que pode subir** — cerimônia sobra é cerimônia que ele vai desviar.

## Pequena

1. Faz.
2. Roda o teste do projeto afetado — não a suíte inteira.
3. Entrega dizendo o que mudou e **o placar do teste**. Sem placar, diga que não testou.

O portão de encerramento vai te barrar se você editar código e não rodar teste. Ele está certo; não tente contorná-lo.

## Média

1. **Ler antes de propor.** O código que já existe manda mais que a sua ideia: ache o padrão equivalente no repo e siga-o. Se for migração, **execute o legado primeiro e registre o retorno real** — nunca inferir o contrato lendo o handler.
2. **Plano no chat**, curto: o que muda, em quais arquivos, qual o risco, como se prova que funcionou. Perguntas de verdade que existirem vão aqui, juntas, não pingadas.
3. **Espere o sim.** Não comece sem ele.
4. Implementa seguindo a convenção do alvo.
5. Fecha com `v6-revisar` e com o teste do projeto afetado.

## Grande

1. **Especificação no vault** (`Projetos/<repo>/<slug da tarefa>.md`): o problema, o comportamento esperado, o que está fora do escopo, e o critério de pronto **executável** (um comando que ou passa ou não).
2. **Plano no vault**, com as fatias em ordem e, para cada uma, a prova que a encerra. Fatia sem prova não é fatia, é intenção.
3. **PARE e espere a aprovação dele.** Escreva isso na sua última linha, sem ambiguidade.
4. Implementa **uma fatia por vez**, provando cada uma antes de seguir. Se a prova de uma fatia falhar, pare e conte — não acumule fatia vermelha.
5. Ao fim de cada fatia, atualize o registro no vault com o que mudou e o placar.
6. Fecha com `v6-revisar` sobre o diff inteiro.

## Regras da casa que valem nos três

Rode `python <plugin>/hooks/regras.py --repo <alvo>` e leia. As que mais mordem aqui:

- **Antes de migrar ou alterar um verbo, execute o legado** e documente o retorno real.
- **Antes de escrita irreversível, faça uma leitura que revele o destino efetivo** e aborte se não for o esperado. Indeterminado também aborta.
- **Afirmação de prova aponta o teste que a sustenta.** "Testado" sem comando e saída não vale.
- **Nunca SQL em homologação ou produção**; DDL é decisão dele.
- **Nada de dependência de núcleo com licença paga** — verifique e declare a licença ao propor biblioteca.

## O que não fazer

- Não subir de tamanho sozinho: se a tarefa cresceu no meio, **diga que cresceu** e ofereça o portão, em vez de gastar uma hora dele sem avisar.
- Não escrever plano ou spec dentro do repositório da empresa.
- Não implementar tamanho grande sem o sim explícito.
- Não entregar sem placar de teste.
- Não perguntar de novo o que ele já respondeu nesta sessão.
