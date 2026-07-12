from typer.testing import CliRunner

from app.main import app

runner = CliRunner()


def test_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "AI Platform" in result.stdout
