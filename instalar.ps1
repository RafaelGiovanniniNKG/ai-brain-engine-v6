# Instala o motor numa maquina. Um comando, e pode rodar de novo sem estragar nada.
#
#     powershell -ExecutionPolicy Bypass -File instalar.ps1
#     powershell -ExecutionPolicy Bypass -File instalar.ps1 -Vault "D:\meu-vault"
#     powershell -ExecutionPolicy Bypass -File instalar.ps1 -Conferir     # so diagnostica
#
# Idempotente: cada passo confere antes de agir e diz o que fez. Nada e sobrescrito
# sem backup. Se um passo opcional falhar (sem rede, sem SDK), o motor continua
# funcionando com aquele sensor desligado, e o diagnostico diz qual.

[CmdletBinding()]
param(
  [string]$Vault = "",
  [switch]$Conferir,
  [switch]$SemFerramentas
)

$ErrorActionPreference = "Continue"
$RAIZ = Split-Path -Parent $MyInvocation.MyCommand.Path
$feitos = @(); $pulados = @(); $falhas = @()

function Passo($nome) { Write-Host "`n>> $nome" -ForegroundColor Cyan }
function Ok($msg)     { Write-Host "   [feito] $msg" -ForegroundColor Green; $script:feitos += $msg }
function Pula($msg)   { Write-Host "   [ja ok] $msg" -ForegroundColor DarkGray; $script:pulados += $msg }
function Falha($msg)  { Write-Host "   [falha] $msg" -ForegroundColor Yellow; $script:falhas += $msg }

function Tem($cmd) {
  if (Get-Command $cmd -ErrorAction SilentlyContinue) { return $true }
  $t = Join-Path $env:USERPROFILE ".dotnet\tools"
  foreach ($e in @("", ".exe", ".cmd")) { if (Test-Path (Join-Path $t "$cmd$e")) { return $true } }
  return $false
}

Write-Host "ai-brain-engine-v6 - instalacao" -ForegroundColor White
Write-Host "repo: $RAIZ"

if ($Conferir) {
  & python (Join-Path $RAIZ "hooks\doutor.py")
  exit $LASTEXITCODE
}

# ---------------------------------------------------------------- 1. o vault
Passo "Onde fica o vault"
if (-not $Vault) {
  foreach ($c in @("C:\Github\obsidian-vault", (Join-Path $env:USERPROFILE "obsidian-vault"),
                   (Join-Path $env:USERPROFILE "Documents\obsidian-vault"))) {
    if (Test-Path $c) { $Vault = $c; break }
  }
}
if ($Vault -and (Test-Path $Vault)) {
  $local = Join-Path $RAIZ "local.json"
  @{ vault = ($Vault -replace '\\', '/') } | ConvertTo-Json | Out-File -FilePath $local -Encoding utf8
  Ok "vault em $Vault (gravado em local.json, que nao vai pro git)"
} else {
  Falha "vault nao encontrado. Rode de novo com -Vault ""<caminho>"". Sem ele, nada e documentado."
}

# ------------------------------------------------- 2. instrucao compartilhada
Passo "Instrucao compartilhada, acima dos repositorios"
if ($Vault) {
  $paiRepos = Split-Path -Parent $Vault
  $destino = Join-Path $paiRepos "CLAUDE.md"
  $modelo  = Join-Path $RAIZ "modelos\CLAUDE.ancestral.md"
  if (Test-Path $destino) {
    Pula "$destino ja existe (nao toquei)"
  } elseif (Test-Path $modelo) {
    Copy-Item $modelo $destino
    Ok "criado $destino a partir do modelo"
  } else {
    Falha "modelo nao encontrado em $modelo"
  }
}

# ------------------------------------------------------------ 3. ferramentas
if (-not $SemFerramentas) {
  Passo "Ferramentas de medicao (cada uma e opcional; sem ela, aquele sensor fica desligado)"

  if (Tem "dotnet") {
    foreach ($t in @(@{n="csharp-ls"; p="csharp-ls"}, @{n="slopwatch"; p="Slopwatch.Cmd"})) {
      if (Tem $t.n) { Pula "$($t.n) ja instalado" }
      else {
        $saida = & dotnet tool install --global $t.p 2>&1 | Out-String
        if (Tem $t.n) { Ok "$($t.n) instalado" } else { Falha "$($t.n): $($saida.Trim() -split "`n" | Select-Object -Last 1)" }
      }
    }
  } else { Falha "dotnet nao encontrado - sensores de .NET ficam de fora" }

  if (Tem "npm") {
    if (Tem "typescript-language-server") { Pula "typescript-language-server ja instalado" }
    else {
      & npm i -g typescript-language-server typescript 2>&1 | Out-Null
      if (Tem "typescript-language-server") { Ok "typescript-language-server instalado" }
      else { Falha "typescript-language-server nao instalou" }
    }
    $eslintBin = Join-Path $RAIZ "sensores\eslint\node_modules\eslint\bin\eslint.js"
    if (Test-Path $eslintBin) { Pula "eslint do motor ja instalado" }
    else {
      Push-Location (Join-Path $RAIZ "sensores\eslint")
      & npm install 2>&1 | Out-Null
      Pop-Location
      if (Test-Path $eslintBin) { Ok "eslint do motor instalado (fora dos repos de trabalho)" }
      else { Falha "npm install do eslint falhou - sensor de TypeScript fica desligado" }
    }
  } else { Falha "npm nao encontrado - sensor de TypeScript fica de fora" }

  & python -c "import yaml" 2>$null
  if ($?) { Pula "pyyaml presente" }
  else {
    & python -m pip install --quiet pyyaml 2>&1 | Out-Null
    & python -c "import yaml" 2>$null
    if ($?) { Ok "pyyaml instalado" } else { Pula "sem pyyaml - o motor usa o serializador simples embutido" }
  }
}

# ---------------------------------------------------------------- 4. o plugin
Passo "Registrar o plugin"
if (Tem "claude") {
  $lista = & claude plugin list 2>&1 | Out-String
  if ($lista -match "ai-brain-engine-v6") {
    Pula "plugin ja registrado"
  } else {
    & claude plugin marketplace add $RAIZ 2>&1 | Out-Null
    & claude plugin install "ai-brain-engine-v6@ai-brain-engine-v6" --scope user 2>&1 | Out-Null
    $lista = & claude plugin list 2>&1 | Out-String
    if ($lista -match "ai-brain-engine-v6") { Ok "plugin instalado no escopo do usuario" }
    else { Falha "nao consegui registrar o plugin" }
  }
} else { Falha "comando claude nao encontrado" }

# ------------------------------------------------------------ 5. as settings
Passo "Ajustar as configuracoes do usuario"
$py = @"
import io, json, shutil, sys
from pathlib import Path
S = Path.home()/'.claude'/'settings.json'
vault = sys.argv[1] if len(sys.argv) > 1 else ''
d = {}
if S.is_file():
    try: d = json.loads(io.open(S, encoding='utf-8').read())
    except Exception: d = {}
    shutil.copy2(S, S.with_suffix('.json.bak-v6'))
mudou = []
if vault:
    alvo = vault.replace('\\', '/').rstrip('/') + '/_memoria'
    if d.get('autoMemoryDirectory') != alvo:
        d['autoMemoryDirectory'] = alvo; mudou.append('autoMemoryDirectory')
if d.get('autoMemoryEnabled') is not True:
    d['autoMemoryEnabled'] = True; mudou.append('autoMemoryEnabled')
if d.get('autoDreamEnabled') is not True:
    d['autoDreamEnabled'] = True; mudou.append('autoDreamEnabled')
ligados = d.get('enabledPlugins') or {}
if ligados.get('ecc@ecc') is True:
    ligados['ecc@ecc'] = False; d['enabledPlugins'] = ligados; mudou.append('ecc desligado')
io.open(S, 'w', encoding='utf-8', newline='\n').write(json.dumps(d, ensure_ascii=False, indent=2) + '\n')
json.loads(io.open(S, encoding='utf-8').read())   # relê para provar que o JSON continua valido
print('|'.join(mudou) if mudou else 'nada a mudar')
"@
$tmp = Join-Path $env:TEMP "v6-settings.py"
$py | Out-File -FilePath $tmp -Encoding utf8
$r = (& python $tmp $Vault 2>&1 | Out-String).Trim()
Remove-Item $tmp -ErrorAction SilentlyContinue
if ($r -eq "nada a mudar") { Pula "configuracoes ja estavam certas" }
elseif ($r -match "Traceback") { Falha "settings.json nao foi alterado: $r" }
else { Ok "ajustado: $r (backup em settings.json.bak-v6)" }

# ------------------------------------------------------------- 6. as provas
Passo "Provar que funciona"
$provas = @("prova_plugin_carrega", "prova_injecao", "prova_portao", "prova_guarda_commit")
foreach ($p in $provas) {
  $arq = Join-Path $RAIZ "testes\$p.py"
  if (-not (Test-Path $arq)) { continue }
  & python $arq *> $null
  if ($LASTEXITCODE -eq 0) { Ok "$p" } else { Falha "$p reprovou - rode 'python testes\$p.py' para ver" }
}

# ---------------------------------------------------------------- resultado
Write-Host "`n$('=' * 64)"
Write-Host "feitos: $($feitos.Count)   ja estavam ok: $($pulados.Count)   com problema: $($falhas.Count)"
if ($falhas.Count -gt 0) {
  Write-Host "`nO que ficou pendente:" -ForegroundColor Yellow
  $falhas | ForEach-Object { Write-Host "  - $_" -ForegroundColor Yellow }
}
Write-Host "`nDiagnostico completo:" -ForegroundColor Cyan
& python (Join-Path $RAIZ "hooks\doutor.py")
$codigo = $LASTEXITCODE
Write-Host "`nAbra uma sessao nova DENTRO de um repositorio para o motor entrar em vigor." -ForegroundColor White
exit $codigo
