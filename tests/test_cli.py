"""Tests for CLI argument parsing."""

from click.testing import CliRunner

from issue_agent.cli import main


def test_version():
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_fix_requires_url():
    runner = CliRunner()
    result = runner.invoke(main, ["fix"])
    assert result.exit_code != 0
    assert "Missing argument" in result.output


def test_graph_requires_url():
    runner = CliRunner()
    result = runner.invoke(main, ["graph"])
    assert result.exit_code != 0
    assert "Missing argument" in result.output


def test_help():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "fix" in result.output
    assert "graph" in result.output
