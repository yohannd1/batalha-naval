from sys import argv, executable, platform
from os import chdir, environ, name as os_name
from pathlib import Path
from subprocess import run

MYPY_OPTS = ["--strict", "--cache-fine-grained", "--explicit-package-bases"]


def do_setup(python: str) -> None:
    run([python, "-m", "pip", "install", "-e", "."])


def main(args: list[str]) -> None:
    here = Path(args[0]).parent
    chdir(here)

    venv_path = Path("venv").absolute()
    venv_created = False
    if not venv_path.exists():
        run([executable, "-m", "venv", venv_path])
        venv_created = True

    # como já temos o env, basta chamar daqui, mas para isso precisamos adicionar ele ao PATH
    is_windows = platform.startswith("win") or os_name == "nt"
    bin_path = venv_path / ("Scripts" if is_windows else "bin")
    envpath_sep = ";" if is_windows else ":"
    environ["PATH"] = str(bin_path) + envpath_sep + environ["PATH"]

    # chamando o python do venv pelo caminho completo
    python = str(bin_path / ("python.exe" if is_windows else "python"))

    def install_if_needed(package: str, bin_name: str) -> None:
        bin_suffix = ".exe" if is_windows else ""
        if (bin_path / (bin_name + bin_suffix)).exists():
            return
        run([python, "-m", "pip", "install", package])

    assert len(args) >= 2
    cmd = args[1]

    # sempre forçar a fazer um setup inicialmente
    if venv_created and cmd != "setup":
        do_setup(python)

    if cmd == "check":
        assert len(args) <= 3
        install_if_needed(package="mypy", bin_name="mypy")

        folder_to_check = "bnaval" if len(args) == 2 else args[2]
        run([python, "-m", "mypy", *MYPY_OPTS, folder_to_check])
    elif cmd == "format":
        assert len(args) == 2
        install_if_needed(package="black", bin_name="black")
        run([python, "-m", "black", "."])
    elif cmd == "doc":
        assert len(args) == 2
        install_if_needed(package="pdoc", bin_name="pdoc")
        run([python, "-m", "pdoc", "-o", "doc", "bnaval"])
    elif cmd == "client":
        assert len(args) == 2
        run([python, "-m", "bnaval.client"])
    elif cmd == "server":
        assert len(args) == 2
        run([python, "-m", "bnaval.server"])
    elif cmd == "setup":
        assert len(args) == 2
        do_setup(python)
    else:
        print(f"Ação desconhecida: {repr(cmd)}")


if __name__ == "__main__":
    main(argv)
