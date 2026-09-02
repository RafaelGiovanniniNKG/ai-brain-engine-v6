---
name: v6-revisar
description: Revisa o diff da branch com vários revisores em paralelo e um verificador por achado, cortando o que tem confiança abaixo de 80. Injeta as regras da casa no prompt de cada revisor, porque os repositórios da empresa não têm arquivo de instrução. Use quando o Rafael pedir revisão, antes de abrir PR, ou como fechamento de uma tarefa média ou grande. Não commita e não altera código — é só leitura.
---

# Revisar

Padrão copiado do que a Anthropic usa no `code-review` e no `feature-dev` — vários revisores em paralelo com focos diferentes, e **um verificador barato por achado** com rubrica de confiança de 0 a 100, cortando abaixo de 80. Com uma adaptação obrigatória.

## A adaptação que muda tudo

Os revisores oficiais leem as regras do **arquivo de instrução do projeto**. Nos repositórios da empresa esse arquivo não existe e não pode existir. Então **o motor injeta as regras no prompt de cada revisor**:

```bash
python <plugin>/hooks/regras.py --repo <caminho do alvo> --completo
```

Cole a saída inteira no prompt de cada revisor. Sem isso eles revisam por gosto geral, e é justamente o gosto geral que produz achado inútil.

## Passos

### 1. Delimitar o que está sob revisão
`git diff` da branch contra a base (`git merge-base HEAD origin/main` ou `master`), ou o que o Rafael apontar. Se o diff passar de ~2.000 linhas, **diga o tamanho e proponha fatiar** — revisor com diff gigante devolve ruído.

Liste os arquivos e as linguagens. Isso decide quem revisa.

### 2. Rodar os sensores primeiro
Achado que uma ferramenta pega não deve gastar revisor:

```bash
slopwatch analyze -d <alvo> --baseline <plugin>/sensores/slopwatch/baseline-<repo>.json
python <plugin>/sensores/camadas/assert_refs.py --repo <alvo>
```

O que o sensor achou entra no relatório como **fato**, não como opinião — e não precisa de verificação de confiança.

### 3. Revisores em paralelo (num único disparo)
Três a cinco, com focos **diferentes e declarados**, todos recebendo o bloco de regras:

1. **Correção** — bug real, condição de borda, nulo, concorrência, transação no lugar errado.
2. **Contrato** — o que muda para quem consome: rota, payload, código de status, evento publicado, migração de schema.
3. **Aderência às regras da casa** — cada regra injetada como critério de reprovação.
4. **Teste** — o teste prova o comportamento ou só executa o código? Existe caso que poderia FALHAR? (regra da casa: caso de golden precisa poder falhar.)
5. **Simplicidade** — duplicação, abstração sem uso, código morto. Só se o diff for grande.

Para `.cs`, use o agente `csharp-reviewer` (adaptado às convenções do SiStockler) em vez de um revisor genérico.

Todos são **somente leitura** e devem devolver, por achado: arquivo e linha, o que quebra, a entrada que produz o efeito, e a correção sugerida.

### 4. Verificar cada achado (o passo que a maioria pula)
Para cada achado, um verificador em contexto limpo pontua de 0 a 100 — e a rubrica vai **literal** para ele:

- **0**: falso positivo, ou problema pré-existente que o diff não introduziu.
- **25**: pode ser real, não deu para confirmar. Se é estilo, não está nas regras injetadas.
- **50**: é real, mas é minúcia ou raro na prática.
- **75**: conferido; é real, vai acontecer, e importa — ou está explicitamente numa regra da casa.
- **100**: confirmado, com a evidência no código.

**Reporte só ≥ 80.** Achado que cita uma regra da casa exige que o verificador confirme que a regra **diz aquilo mesmo** — regra invocada de memória é como o revisor inventa autoridade.

### 5. Relatório
Em português, agrupado por severidade, cada achado com arquivo:linha, o efeito concreto e a correção. Depois:

- **o que os sensores acharam** (fato, sem nota de confiança);
- **quantos achados foram descartados** pelo corte de 80 — o número importa: se descartou muito, os revisores estão gerando ruído e o foco deles precisa mudar;
- **o que NÃO foi revisado** (arquivo grande demais, gerado, fora do escopo).

Se não houver achado acima de 80, diga isso em uma linha e pare. Revisão sem achado é resultado, não fracasso.

## O que não fazer

- Não commitar, não corrigir, não formatar. Isto é leitura.
- Não reportar estilo que não esteja nas regras injetadas ou no `.editorconfig` do alvo.
- Não reportar achado com confiança abaixo de 80 "só para constar".
- Não dizer que revisou o que não leu. Arquivo pulado se declara.
- Não invocar regra da casa sem citar o arquivo dela em `regras/`.
