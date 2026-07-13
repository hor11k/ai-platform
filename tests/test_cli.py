import subprocess
import sys
from pathlib import Path

from typer.testing import CliRunner

from app.main import REGISTERED_COMMAND_NAMES, app

runner = CliRunner()


def test_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "AI Platform" in result.stdout


def test_top_level_help_lists_registered_commands() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    for command in REGISTERED_COMMAND_NAMES:
        assert command in result.stdout


def test_all_commands_are_registered_on_app() -> None:
    command_names = [command.name for command in app.registered_commands]

    assert command_names == list(REGISTERED_COMMAND_NAMES)


def test_main_module_registers_every_command() -> None:
    main_source = Path("app/main.py").read_text(encoding="utf-8")

    for command in REGISTERED_COMMAND_NAMES:
        import_line = (
            f"from app.commands.{command} import register as register_{command}"
        )
        assert import_line in main_source
        assert f"register_{command}(app)" in main_source


def test_ingest_help_via_cli_runner() -> None:
    result = runner.invoke(app, ["ingest", "--help"])

    assert result.exit_code == 0
    assert "Incrementally index" in result.stdout


def _python3_executable() -> str:
    python3 = Path(sys.executable).with_name("python3")
    return str(python3 if python3.is_file() else sys.executable)


def test_ingest_help_via_python3_module_entrypoint() -> None:
    result = subprocess.run(
        [_python3_executable(), "-m", "app.main", "ingest", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "Incrementally index" in result.stdout


def test_ingest_help_via_console_script() -> None:
    ai_script = Path(sys.executable).parent / "ai"
    if not ai_script.is_file():
        ai_script = Path(__file__).resolve().parents[1] / ".venv" / "bin" / "ai"

    result = subprocess.run(
        [str(ai_script), "ingest", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "Incrementally index" in result.stdout
