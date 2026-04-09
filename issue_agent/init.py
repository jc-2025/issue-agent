"""Init command — onboard a project with coding standards and conventions."""

import os
import shutil
from pathlib import Path

import click


def run_init(from_project: str | None = None, target_dir: str = ".") -> None:
    """Run the init flow — either interactive or import."""
    target = Path(target_dir).resolve()

    if from_project:
        _import_config(Path(from_project).resolve(), target)
    else:
        _interactive_init(target)


def _interactive_init(target: Path) -> None:
    """Interview the developer and generate config files."""
    click.echo(click.style("\n  issue-agent init\n", bold=True))
    click.echo("  I'll ask a few questions about your project to set up conventions.\n")

    # Language & framework
    language = click.prompt("  Primary language", default="Python")
    framework = click.prompt("  Framework (or 'none')", default="none")

    # Commands
    test_cmd = click.prompt("  Test command", default=_guess_test_cmd(target, language))
    lint_cmd = click.prompt("  Lint/format command (or 'none')", default=_guess_lint_cmd(language))
    build_cmd = click.prompt("  Build command (or 'none')", default="none")

    # Code style
    click.echo(click.style("\n  Code style preferences:\n", bold=True))
    naming = click.prompt(
        "  Naming convention",
        type=click.Choice(["snake_case", "camelCase", "PascalCase", "mixed"], case_sensitive=False),
        default=_default_naming(language),
    )
    imports_style = click.prompt("  Import style preference (or 'none')", default="none")
    max_file_length = click.prompt("  Max file length (lines, or 'none')", default="none")

    # PR conventions
    click.echo(click.style("\n  PR & git conventions:\n", bold=True))
    branch_format = click.prompt(
        "  Branch naming",
        type=click.Choice(["type/description", "type/issue-number-description", "free-form"], case_sensitive=False),
        default="type/issue-number-description",
    )
    commit_format = click.prompt(
        "  Commit message format",
        type=click.Choice(["conventional", "free-form"], case_sensitive=False),
        default="conventional",
    )

    # Custom rules
    click.echo(click.style("\n  Additional rules:\n", bold=True))
    custom_rules = click.prompt(
        "  Any other conventions? (free text, or 'none')",
        default="none",
    )

    # Generate files
    config = ProjectConfig(
        language=language,
        framework=framework if framework != "none" else None,
        test_cmd=test_cmd,
        lint_cmd=lint_cmd if lint_cmd != "none" else None,
        build_cmd=build_cmd if build_cmd != "none" else None,
        naming=naming,
        imports_style=imports_style if imports_style != "none" else None,
        max_file_length=max_file_length if max_file_length != "none" else None,
        branch_format=branch_format,
        commit_format=commit_format,
        custom_rules=custom_rules if custom_rules != "none" else None,
    )

    _write_config(target, config)

    click.echo(click.style("\n  Done! Generated:", bold=True))
    click.echo(f"    CLAUDE.md")
    click.echo(f"    .claude/rules/coding-style.md")
    click.echo(f"    .claude/rules/testing.md")
    click.echo()


def _import_config(source: Path, target: Path) -> None:
    """Import config from an existing project."""
    click.echo(click.style("\n  issue-agent init --from\n", bold=True))
    click.echo(f"  Importing config from: {source}\n")

    found_files = []

    # Check for CLAUDE.md
    source_claude_md = source / "CLAUDE.md"
    if source_claude_md.exists():
        found_files.append(("CLAUDE.md", source_claude_md))

    # Check for .claude/rules/
    source_rules = source / ".claude" / "rules"
    if source_rules.is_dir():
        for rule_file in sorted(source_rules.glob("*.md")):
            rel = Path(".claude/rules") / rule_file.name
            found_files.append((str(rel), rule_file))

    if not found_files:
        click.echo("  No CLAUDE.md or .claude/rules/ found in source project.")
        click.echo("  Run `issue-agent init` without --from for interactive setup.\n")
        return

    # Show what was found
    click.echo("  Found config files:")
    for rel_path, _ in found_files:
        click.echo(f"    {rel_path}")
    click.echo()

    # Ask which to import
    for rel_path, source_file in found_files:
        content = source_file.read_text()

        # Show a preview (first 5 lines)
        preview = "\n".join(content.splitlines()[:5])
        click.echo(f"  --- {rel_path} ---")
        click.echo(f"  {preview}")
        if len(content.splitlines()) > 5:
            click.echo(f"  ... ({len(content.splitlines())} lines total)")
        click.echo()

        action = click.prompt(
            f"  Import {rel_path}?",
            type=click.Choice(["yes", "skip", "edit"], case_sensitive=False),
            default="yes",
        )

        if action == "skip":
            click.echo(f"  Skipped {rel_path}\n")
            continue

        if action == "edit":
            click.echo("  Enter replacement content (end with an empty line):")
            lines = []
            while True:
                line = input()
                if line == "":
                    break
                lines.append(line)
            content = "\n".join(lines) + "\n"

        # Write the file
        target_file = target / rel_path
        target_file.parent.mkdir(parents=True, exist_ok=True)
        target_file.write_text(content)
        click.echo(f"  Wrote {rel_path}\n")

    click.echo(click.style("  Import complete!\n", bold=True))


class ProjectConfig:
    """Holds project configuration from the interview."""

    def __init__(
        self,
        language: str,
        framework: str | None,
        test_cmd: str,
        lint_cmd: str | None,
        build_cmd: str | None,
        naming: str,
        imports_style: str | None,
        max_file_length: str | None,
        branch_format: str,
        commit_format: str,
        custom_rules: str | None,
    ):
        self.language = language
        self.framework = framework
        self.test_cmd = test_cmd
        self.lint_cmd = lint_cmd
        self.build_cmd = build_cmd
        self.naming = naming
        self.imports_style = imports_style
        self.max_file_length = max_file_length
        self.branch_format = branch_format
        self.commit_format = commit_format
        self.custom_rules = custom_rules


def _write_config(target: Path, config: ProjectConfig) -> None:
    """Generate CLAUDE.md and .claude/rules/ from config."""

    # CLAUDE.md
    stack = config.language
    if config.framework:
        stack += f" + {config.framework}"

    commands = [f"- Test: `{config.test_cmd}`"]
    if config.lint_cmd:
        commands.append(f"- Lint: `{config.lint_cmd}`")
    if config.build_cmd:
        commands.append(f"- Build: `{config.build_cmd}`")

    commit_section = ""
    if config.commit_format == "conventional":
        commit_section = """
## Commit Messages

Use conventional commits: `type: description`
- `fix:` for bug fixes
- `feat:` for new features
- `refactor:` for code restructuring
- `test:` for adding/updating tests
- `docs:` for documentation changes
"""

    branch_section = ""
    if config.branch_format == "type/issue-number-description":
        branch_section = """
## Branch Naming

Use `type/issue-number-description` format:
- `fix/issue-42-null-check`
- `feat/issue-15-user-auth`
- `refactor/issue-8-cleanup-utils`
"""
    elif config.branch_format == "type/description":
        branch_section = """
## Branch Naming

Use `type/description` format:
- `fix/null-check`
- `feat/user-auth`
"""

    custom_section = ""
    if config.custom_rules:
        custom_section = f"""
## Additional Conventions

{config.custom_rules}
"""

    claude_md = f"""# Project Guidelines

## Stack

{stack}

## Commands

{chr(10).join(commands)}
{commit_section}{branch_section}{custom_section}"""

    (target / "CLAUDE.md").write_text(claude_md)

    # .claude/rules/coding-style.md
    rules_dir = target / ".claude" / "rules"
    rules_dir.mkdir(parents=True, exist_ok=True)

    style_rules = [f"- Use {config.naming} naming convention"]
    if config.imports_style:
        style_rules.append(f"- Imports: {config.imports_style}")
    if config.max_file_length:
        style_rules.append(f"- Keep files under {config.max_file_length} lines")
    style_rules.append("- Match existing code style in the file being modified")
    style_rules.append("- No unrelated changes in the same PR")

    coding_style = f"""---
description: Code style conventions for {config.language} files
---

# Coding Style

{chr(10).join(style_rules)}
"""

    (rules_dir / "coding-style.md").write_text(coding_style)

    # .claude/rules/testing.md
    testing_rules = f"""---
description: Testing conventions
---

# Testing

- Run tests with: `{config.test_cmd}`
- All PRs must have passing tests before merge
- New features must include at least one test
- Bug fixes should include a regression test when possible
- Never delete existing tests unless the behavior is intentionally removed
"""

    (rules_dir / "testing.md").write_text(testing_rules)


def _guess_test_cmd(target: Path, language: str) -> str:
    """Guess the test command based on project files."""
    if (target / "pyproject.toml").exists() or (target / "pytest.ini").exists():
        return "pytest"
    if (target / "package.json").exists():
        return "npm test"
    if (target / "Cargo.toml").exists():
        return "cargo test"
    if (target / "go.mod").exists():
        return "go test ./..."
    if (target / "Makefile").exists():
        return "make test"
    if language.lower() == "python":
        return "pytest"
    if language.lower() in ("javascript", "typescript"):
        return "npm test"
    return "pytest"


def _guess_lint_cmd(language: str) -> str:
    """Guess the lint command based on language."""
    lang = language.lower()
    if lang == "python":
        return "ruff check ."
    if lang in ("javascript", "typescript"):
        return "eslint ."
    if lang == "go":
        return "golangci-lint run"
    if lang == "rust":
        return "cargo clippy"
    return "none"


def _default_naming(language: str) -> str:
    """Default naming convention for a language."""
    lang = language.lower()
    if lang in ("python", "rust", "go"):
        return "snake_case"
    if lang in ("javascript", "typescript", "java", "kotlin"):
        return "camelCase"
    return "snake_case"
