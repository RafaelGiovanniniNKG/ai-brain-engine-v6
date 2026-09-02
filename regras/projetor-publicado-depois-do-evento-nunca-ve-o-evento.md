---
id: projetor-publicado-depois-do-evento-nunca-ve-o-evento
projects: Projeto-SiStockler.ServiceDesk, POC-cqrs-reference-architecture, Projeto-SiStockler.OperationalManagement
confidence: 0.9
status: active
last_confirmed: 2026-08-17
origin: ServiceDesk (2026-08-17) — primeira carga real do HCM gravou 505 colaboradores em `dbo` e ZERO em `read`. O worker de projecao rodava imagem de tres dias antes, sem o projetor do tipo novo: consumiu as 505 mensagens, deu ack e descartou.
---
Publicar o evento ANTES de o consumidor saber lidar com ele nao adia a projecao — **destroi a
entrega**. O worker consome, nao encontra projetor para o tipo, considera a mensagem tratada, e a
fila esvazia. Reconstruir o worker depois nao traz nada de volta: a mensagem nao existe mais.

**Esperado:** subir a imagem nova do worker faz a projecao alcancar o que ficou para tras
**Aconteceu:** `dbo.Colaboradores` com 505 linhas, `read.Colaboradores` com 0, filas do broker
VAZIAS, e `outbox` com `pendentes = 0` — tudo indicando "publicado com sucesso". O inbox tinha 505
marcas da assinatura `audit` (que consome tudo genericamente) e NENHUMA da `projection`, o que e a
assinatura do problema: quem marcou, tratou; quem nao marcou, descartou.

## Como aplicar

1. Ao acrescentar um tipo de evento, **subir o consumidor ANTES do produtor**. Consumidor novo com
   produtor velho nao recebe nada e nao perde nada; o contrario perde em silencio.
2. Se ja aconteceu, o dado nao esta perdido: as linhas do outbox sobrevivem, e o replay reenfileira.
   Foi o que recuperou as 505 — `POST /admin/replay` com janela do dia.
3. `AssinaturaParaReprocessar` so e necessario quando o inbox JA marcou a mensagem para aquela
   assinatura. Quando o consumidor descartou sem marcar, o replay simples basta.
4. Nao confie em "outbox com zero pendentes" como prova de que a leitura recebeu. Ele prova
   PUBLICACAO, e publicacao para um consumidor que descarta e indistinguivel de sucesso. A unica
   prova e contar as linhas dos dois lados.
5. Em stack de desenvolvimento, `docker compose ps` mostrando `Up 3 days` num worker e o aviso: a
   imagem dele e anterior ao codigo que voce acabou de escrever.

## Corolario generico (vale fora deste repo)

**Consumidor que ignora tipo desconhecido em silencio transforma ordem de deploy em perda de dado.**
Um consumidor que PARQUEASSE o desconhecido — em vez de dar ack — teria transformado o mesmo erro de
ordem num acumulo visivel na fila, recuperavel sem replay e sem ninguem precisar suspeitar. Ack de
mensagem desconhecida e uma decisao, e ela custa exatamente isto.
