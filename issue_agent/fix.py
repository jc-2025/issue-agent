"""Fix command — autonomous GitHub issue fixer using Claude Agent SDK."""

import sys

from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, ResultMessage

from issue_agent.prompts import build_fix_prompt


async def run_fix(
    issue_url: str,
    model: str = "claude-sonnet-4-20250514",
    max_turns: int = 50,
    verbose: bool = False,
) -> bool:
    """Run the issue-fix agent.

    Returns True if a PR was opened, False otherwise.
    """
    prompt = build_fix_prompt(issue_url)

    click_echo = _make_echo(verbose)
    click_echo(f"\n  issue-agent fix\n  {issue_url}\n", bold=True)

    success = False

    async for message in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            allowed_tools=["Read", "Edit", "Bash", "WebFetch", "Glob", "Grep"],
            model=model,
            max_turns=max_turns,
            permission_mode="bypassPermissions",
        ),
    ):
        if isinstance(message, AssistantMessage):
            text = _extract_text(message)
            if text:
                for line in text.splitlines():
                    stripped = line.strip()
                    if stripped.startswith("["):
                        click_echo(stripped)
                    elif verbose:
                        click_echo(stripped)

            if verbose and hasattr(message, "content"):
                for block in message.content:
                    if hasattr(block, "name"):
                        click_echo(f"  -> tool: {block.name}", dim=True)

        elif isinstance(message, ResultMessage):
            if message.subtype == "success":
                success = True
                click_echo(f"\n  Completed. Cost: ${message.total_cost_usd:.4f}", bold=True)
            else:
                click_echo(f"\n  Agent stopped: {message.subtype}", err=True)

    return success


def _extract_text(message: AssistantMessage) -> str:
    """Extract text content from an assistant message."""
    if not hasattr(message, "content"):
        return ""
    parts = []
    for block in message.content:
        if hasattr(block, "text"):
            parts.append(block.text)
    return "\n".join(parts)


def _make_echo(verbose: bool):
    """Create a click-style echo function."""
    import click

    def echo(msg: str, bold: bool = False, dim: bool = False, err: bool = False):
        style = {}
        if bold:
            style["bold"] = True
        if dim:
            style["dim"] = True
        if err:
            style["fg"] = "red"
        click.echo(click.style(msg, **style) if style else msg)

    return echo
