import json
import subprocess

COMANDOS = [
    ["uv", "run", "mypy", "."],
    ["uv", "run", "ruff", "check", "."],
    ["uv", "run", "ruff", "format", "--check", "."],
]


def executar(comando: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        comando, capture_output=True, text=True, encoding="utf-8", check=False
    )


def main() -> None:
    if ".py" not in executar(["git", "status", "--porcelain"]).stdout:
        return

    falhas = []
    for comando in COMANDOS:
        resultado = executar(comando)
        if resultado.returncode != 0:
            falhas.append(
                f"$ {' '.join(comando)}\n{resultado.stdout}{resultado.stderr}"
            )

    if falhas:
        motivo = (
            "Quality gates com achados. Corrija e execute novamente:\n\n"
            + "\n".join(falhas)
        )
        print(json.dumps({"decision": "block", "reason": motivo}))


if __name__ == "__main__":
    main()
