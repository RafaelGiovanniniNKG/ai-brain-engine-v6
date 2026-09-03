---
id: prova-que-depende-de-carimbo-de-hora-controla-o-relogio
projects: all
confidence: 1.0
last_confirmed: 2026-09-03
origin: 2026-09-03 — a prova nova do sensor de edição pelo terminal escrevia o arquivo "que já estava sujo" e marcava o início da sessão logo depois. A granularidade do carimbo de hora do sistema de arquivos fazia os dois instantes empatarem: 9/11 numa execução e 11/11 na seguinte, sem mudar uma linha. Trocado `sleep` por `os.utime` explícito, ficou determinístico em 8 execuções seguidas.
status: active
---
Prova cujo veredito depende de HORA DE MODIFICAÇÃO tem de **controlar o relógio** (`os.utime`,
relógio injetado), não esperar por ele: `sleep` para "o carimbo mudar" é aposta na granularidade
do sistema de arquivos e produz vermelho intermitente. E prova que às vezes reprova é pior que
prova nenhuma — ela ensina a ignorar vermelho.
