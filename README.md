# ai-brain-engine-v6

Plugin de Claude Code, de uso pessoal. Instala **na máquina**, trabalha **dentro** de qualquer
repositório e **não escreve um único arquivo lá**.

Ele existe para fechar quatro falhas medidas no v5 (diagnóstico de 28/08/2026):

| Falha | O que o v6 faz |
|---|---|
| As regras aprendidas nunca chegavam ao modelo | Injeta no início da sessão, e o que é mecânico vira bloqueio em vez de texto |
| Nenhum sensor mecânico em .NET/Angular | Servidor de linguagem, `slopwatch`, ESLint externo, afirmação de camada — tudo fora do repo |
| Nada impedia dizer "pronto" sem prova | Nega o encerramento quando houve edição de código sem teste verde |
| O vault era mão única e dependia de lembrar | Captura por gatilho automático, com cursor e hash, e leitura de volta na sessão seguinte |

**Plano, decisões e evidências:** `C:\Github\obsidian-vault\Projetos\ai-brain-engine-v6`.
Nenhum documento de plano vive neste repositório — é a mesma regra que vale para os repos de
trabalho.

## Estado

Passo 0 (medir e cortar) e Passo 1 (casca viva) — ver o registro de execução no plano.

## Instalar

```powershell
# uma vez, no Claude Code
/plugin marketplace add C:\Github\ai-brain-engine-v6
/plugin install ai-brain-engine-v6@ai-brain-engine-v6 --scope user

# para desenvolver, sem instalar
claude --plugin-dir C:\Github\ai-brain-engine-v6
```

Dependências de máquina (já instaladas em 02/09/2026): `csharp-ls` (`dotnet tool install --global
csharp-ls`) e `typescript-language-server` (`npm i -g typescript-language-server typescript`).

## Estrutura

```
.claude-plugin/plugin.json   manifesto (só o nome é obrigatório)
.lsp.json                    C# e TypeScript com diagnóstico ligado
hooks/hooks.json             injeção no início da sessão + prova do que chegou
hooks/session_start.py       monta o bloco de contexto (teto de 6.000 caracteres)
hooks/instructions_probe.py  anota qual instrução o modelo recebeu — temporário
regras/                      as regras vivas, uma por arquivo (portadas do v5)
mapa.json                    repo -> pasta do projeto no vault
_prova/                      saída da sonda; não versionado
```

## Regras da casa

- Uma regra só nasce de falha real, com o `origin` apontando a sessão ou o commit que a originou.
- Injeção é limitada de propósito: manchete da regra, não o corpo.
- Hook que pode quebrar a sessão sai em silêncio com código 0.
- Nada de licença paga.
