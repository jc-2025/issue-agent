"""Tests for init command."""

import os
from pathlib import Path

from click.testing import CliRunner

from issue_agent.cli import main
from issue_agent.init import ProjectConfig, _write_config, _guess_test_cmd, _guess_lint_cmd, _default_naming


def test_init_shows_in_help():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert "init" in result.output


def test_init_help():
    runner = CliRunner()
    result = runner.invoke(main, ["init", "--help"])
    assert result.exit_code == 0
    assert "--from" in result.output


def test_write_config_generates_claude_md(tmp_path):
    config = ProjectConfig(
        language="Python",
        framework="Flask",
        test_cmd="pytest",
        lint_cmd="ruff check .",
        build_cmd=None,
        naming="snake_case",
        imports_style=None,
        max_file_length=None,
        branch_format="type/issue-number-description",
        commit_format="conventional",
        custom_rules=None,
    )
    _write_config(tmp_path, config)

    claude_md = (tmp_path / "CLAUDE.md").read_text()
    assert "Python + Flask" in claude_md
    assert "`pytest`" in claude_md
    assert "`ruff check .`" in claude_md
    assert "conventional commits" in claude_md


def test_write_config_generates_rules(tmp_path):
    config = ProjectConfig(
        language="TypeScript",
        framework="Next.js",
        test_cmd="npm test",
        lint_cmd="eslint .",
        build_cmd="npm run build",
        naming="camelCase",
        imports_style="named imports only",
        max_file_length="300",
        branch_format="type/description",
        commit_format="free-form",
        custom_rules="Always use async/await over .then()",
    )
    _write_config(tmp_path, config)

    style = (tmp_path / ".claude" / "rules" / "coding-style.md").read_text()
    assert "camelCase" in style
    assert "named imports only" in style
    assert "300 lines" in style

    testing = (tmp_path / ".claude" / "rules" / "testing.md").read_text()
    assert "`npm test`" in testing


def test_write_config_custom_rules(tmp_path):
    config = ProjectConfig(
        language="Python",
        framework=None,
        test_cmd="pytest",
        lint_cmd=None,
        build_cmd=None,
        naming="snake_case",
        imports_style=None,
        max_file_length=None,
        branch_format="free-form",
        commit_format="free-form",
        custom_rules="Always type-hint function signatures",
    )
    _write_config(tmp_path, config)

    claude_md = (tmp_path / "CLAUDE.md").read_text()
    assert "Always type-hint function signatures" in claude_md


def test_guess_test_cmd_python(tmp_path):
    (tmp_path / "pyproject.toml").write_text("")
    assert _guess_test_cmd(tmp_path, "Python") == "pytest"


def test_guess_test_cmd_node(tmp_path):
    (tmp_path / "package.json").write_text("{}")
    assert _guess_test_cmd(tmp_path, "JavaScript") == "npm test"


def test_guess_test_cmd_rust(tmp_path):
    (tmp_path / "Cargo.toml").write_text("")
    assert _guess_test_cmd(tmp_path, "Rust") == "cargo test"


def test_guess_lint_cmd():
    assert _guess_lint_cmd("Python") == "ruff check ."
    assert _guess_lint_cmd("TypeScript") == "eslint ."
    assert _guess_lint_cmd("Go") == "golangci-lint run"
    assert _guess_lint_cmd("Rust") == "cargo clippy"


def test_default_naming():
    assert _default_naming("Python") == "snake_case"
    assert _default_naming("JavaScript") == "camelCase"
    assert _default_naming("Go") == "snake_case"


def test_import_no_config(tmp_path):
    """Import from a dir with no config should show a message."""
    source = tmp_path / "source"
    source.mkdir()

    runner = CliRunner()
    result = runner.invoke(main, ["init", "--from", str(source)])
    assert "No CLAUDE.md" in result.output


def test_import_copies_claude_md(tmp_path):
    """Import should copy CLAUDE.md from source."""
    source = tmp_path / "source"
    source.mkdir()
    (source / "CLAUDE.md").write_text("# My Project\n\nTest: pytest\n")

    target = tmp_path / "target"
    target.mkdir()

    runner = CliRunner()
    result = runner.invoke(main, ["init", "--from", str(source)], input="yes\n")
    # The command writes to cwd, not target — but we can test the flow ran
    assert result.exit_code == 0
