from pathlib import Path


def test_launcher_script_exists_and_is_executable() -> None:
    launcher = Path("scripts/ai")
    assert launcher.is_file()
    assert launcher.stat().st_mode & 0o111


def test_install_script_exists_and_is_executable() -> None:
    install_script = Path("scripts/install.sh")
    assert install_script.is_file()
    assert install_script.stat().st_mode & 0o111


def test_launcher_detects_project_root_via_env(tmp_path, monkeypatch) -> None:
    project_root = tmp_path / "ai-platform"
    project_root.mkdir()
    (project_root / "pyproject.toml").write_text(
        'name = "ai-platform"\n',
        encoding="utf-8",
    )
    venv_bin = project_root / ".venv" / "bin"
    venv_bin.mkdir(parents=True)
    (project_root / ".venv" / "bin" / "activate").write_text(
        "# mock activate\n",
        encoding="utf-8",
    )
    cli_entry = venv_bin / "ai"
    cli_entry.write_text("#!/bin/sh\necho ai-platform-cli \"$@\"\n", encoding="utf-8")
    cli_entry.chmod(0o755)

    launcher = Path("scripts/ai").resolve()
    monkeypatch.setenv("AI_PLATFORM_ROOT", str(project_root))

    import subprocess

    result = subprocess.run(
        [str(launcher), "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "ai-platform-cli" in result.stdout


def test_launcher_reports_missing_project(tmp_path, monkeypatch) -> None:
    missing_root = tmp_path / "missing"
    monkeypatch.setenv("AI_PLATFORM_ROOT", str(missing_root))

    import subprocess

    launcher = Path("scripts/ai").resolve()
    result = subprocess.run(
        [str(launcher), "find", "test"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "ai-platform error" in result.stderr
    assert "Could not find" in result.stderr or "is not an ai-platform project" in result.stderr
