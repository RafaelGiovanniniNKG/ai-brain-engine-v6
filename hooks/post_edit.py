#!/usr/bin/env python
"""Sensores de edição: um processo por edição, não quinze.

Roda depois de cada Write/Edit e devolve ao modelo, no mesmo turno, o que as
ferramentas de verdade acharam no arquivo que ele acabou de tocar:

  .cs .razor .csproj .props .targets  ->  slopwatch  (teste desligado, aviso
      silenciado, catch vazio, sleep em teste, slop de csproj, bypass de CPM)
  .csproj .props                      ->  matriz de dependência entre projetos
  .ts .tsx .js                        ->  ESLint com config externa, quando o
      pacote estiver instalado na pasta do motor (Passo 2b)

Decisões que valem registro:
  * `PostToolUse` NÃO bloqueia — a ferramenta já rodou. O canal é
    `additionalContext`, que o modelo lê. Quem barra é o portão do Passo 3.
  * A linha de base do slopwatch mora FORA do repo alvo
    (`sensores/slopwatch/baseline-<repo>.json`). Sem ela, o modo `--hook` do
    slopwatch sai com 2 só por não achar o arquivo — bloqueio pelo motivo
    errado. Então: com base, filtra o que é pré-existente; sem base, analisa só
    o arquivo tocado e avisa que a base não existe.
  * `dotnet format` ficou FORA daqui de propósito: precisa do projeto carregado
    e custa segundos, enquanto o servidor de linguagem já entrega o erro real.
  * Nunca levanta e nunca demora: 25 s de teto por sensor, e erro de sensor
    virou aviso, não bloqueio.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import estado  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
TETO_SEG = 25

EXT_DOTNET = {".cs", ".razor", ".cshtml", ".csproj", ".props", ".targets"}
EXT_PROJETO = {".csproj", ".props"}
EXT_WEB = {".ts", ".tsx", ".mts", ".cts", ".js", ".mjs"}


def _entrada() -> dict:
    try:
        return json.loads(sys.stdin.read() or "{}")
    except Exception:
        return {}


def _arquivo_editado(d: dict) -> Path | None:
    """Caminho do arquivo editado, SEMPRE resolvido.

    `resolve()` não é decoração: no Windows, `C:\\Users\\RAFAEL~1.GIO\\...` (forma
    curta 8.3) e `C:\\Users\\rafael.giovannini\\...` (forma longa) são a mesma
    pasta, mas o ESLint compara TEXTO e conclui "File ignored because outside of
    base path" — sai com 1, com um aviso, e o sensor parece ter passado quando na
    verdade não olhou o arquivo. Falso verde é pior que vermelho.
    """
    ti = d.get("tool_input") or {}
    for chave in ("file_path", "filePath", "path", "notebook_path"):
        if ti.get(chave):
            bruto = Path(str(ti[chave]))
            try:
                return bruto.resolve()
            except Exception:
                return bruto
    return None


def _repo_de(arquivo: Path) -> Path | None:
    try:
        r = subprocess.run(
            ["git", "-C", str(arquivo.parent), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0 and r.stdout.strip():
            return Path(r.stdout.strip())
    except Exception:
        pass
    return None


def _rodar(cmd: list[str], cwd: Path | None = None) -> tuple[int, str]:
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=TETO_SEG, cwd=str(cwd) if cwd else None,
        )
        return r.returncode, ((r.stdout or "") + (r.stderr or "")).strip()
    except subprocess.TimeoutExpired:
        return 0, ""  # sensor lento não vira bloqueio
    except FileNotFoundError:
        return 0, ""  # ferramenta não instalada: silêncio, não erro
    except Exception:
        return 0, ""


def _slopwatch(arquivo: Path, repo: Path | None) -> str:
    exe = shutil.which("slopwatch") or shutil.which("slopwatch.exe")
    if not exe:
        return ""
    cmd = [exe, "analyze", "-f", str(arquivo), "--min-severity", "warning"]
    aviso = ""
    base = RAIZ / "sensores" / "slopwatch" / f"baseline-{repo.name}.json" if repo else None
    if base and base.is_file():
        cmd += ["--baseline", str(base)]
    else:
        cmd += ["--no-baseline"]
        if repo:
            aviso = (
                f"\n(sem linha de base para `{repo.name}` — achado pré-existente também aparece. "
                f"Para criar: rodar `slopwatch init` no repo, mover o `.slopwatch/baseline.json` para "
                f"`sensores/slopwatch/baseline-{repo.name}.json` e apagar o `.slopwatch` do repo.)"
            )
    codigo, saida = _rodar(cmd, cwd=repo)
    if codigo != 0 and saida:
        return "### slopwatch reprovou o arquivo que você acabou de editar\n" + saida + aviso
    return ""


def _camadas(repo: Path | None) -> str:
    if not repo:
        return ""
    script = RAIZ / "sensores" / "camadas" / "assert_refs.py"
    if not script.is_file():
        return ""
    codigo, saida = _rodar([sys.executable, str(script), "--repo", str(repo)])
    if codigo != 0 and saida:
        return "### a matriz de dependência entre projetos foi violada\n" + saida
    return ""


def _eslint(arquivo: Path, repo: Path | None) -> str:
    config = RAIZ / "sensores" / "eslint" / "guard.config.mjs"
    binario = RAIZ / "sensores" / "eslint" / "node_modules" / "eslint" / "bin" / "eslint.js"
    if not (config.is_file() and binario.is_file()):
        return ""  # Passo 2b ainda não instalado
    # O caminho-base do ESLint 10 vem do DIRETÓRIO DE TRABALHO, não da config.
    # Rodar de fora faz ele responder "File ignored because outside of base path"
    # e passar com aviso — reprovação silenciosa disfarçada de sucesso. E
    # `--format compact` saiu do núcleo no 10: passar a flag derruba o processo
    # com uma mensagem que parece achado e não é.
    base = repo or arquivo.parent
    try:
        alvo = str(arquivo.relative_to(base))  # relativo à base: nada de comparar texto
    except ValueError:
        alvo = str(arquivo)
    codigo, saida = _rodar(
        ["node", str(binario), "--no-config-lookup", "-c", str(config),
         "--max-warnings", "0", alvo],
        cwd=base,
    )
    if "outside of base path" in saida:
        # não deveria mais acontecer (caminho resolvido + relativo). Se acontecer,
        # é falha do sensor, e falha de sensor se declara — não se engole.
        return (
            "### o sensor de TypeScript não conseguiu olhar o arquivo\n"
            f"O ESLint respondeu 'outside of base path' para `{alvo}` com base em `{base}`. "
            "Isso NÃO é aprovação: o arquivo não foi analisado."
        )
    if codigo != 0 and saida:
        return "### ESLint reprovou o arquivo que você acabou de editar\n" + saida
    return ""


def main() -> int:
    d = _entrada()
    arquivo = _arquivo_editado(d)
    if not arquivo:
        return 0
    ext = arquivo.suffix.lower()
    if ext not in (EXT_DOTNET | EXT_WEB):
        return 0
    if not arquivo.exists():
        return 0

    repo = _repo_de(arquivo)
    partes = {p.lower() for p in arquivo.parts}
    if partes & {"bin", "obj", "node_modules", ".git"}:
        return 0

    achados = []
    if ext in EXT_DOTNET:
        achados.append(_slopwatch(arquivo, repo))
    if ext in EXT_PROJETO:
        achados.append(_camadas(repo))
    if ext in EXT_WEB:
        achados.append(_eslint(arquivo, repo))

    texto = "\n\n".join(a for a in achados if a).strip()

    # O registro acontece SEMPRE, com ou sem achado: quem decide o portão é a
    # existência da edição, não a existência de reprovação.
    estado.registrar_edicao(d.get("session_id", ""), str(arquivo), str(repo) if repo else None, texto)

    # `agent_id` só vem preenchido quando este hook disparou DENTRO de um
    # sub-agente. Nesse caso a edição vai também para o registro endereçado pelo
    # diretório, porque não está documentado se o sub-agente carrega o mesmo
    # `session_id` de quem o chamou — e se não carregar, a linha acima grava num
    # lugar que o portão da sessão principal nunca lê.
    if d.get("agent_id"):
        estado.registrar_edicao_de_agente(
            d.get("cwd") or (str(repo) if repo else str(arquivo.parent)),
            str(arquivo),
            d.get("agent_type") or "",
        )

    if not texto:
        return 0

    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": (
                "SENSORES DO MOTOR (v6) — o arquivo que você acabou de editar foi reprovado "
                "por ferramenta, não por opinião. Conserte a causa antes de seguir; não "
                "silencie o aviso, não desabilite o teste e não adicione supressão para "
                "esconder o problema.\n\n" + texto
            ),
        }
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
