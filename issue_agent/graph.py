"""Graph command — dependency graph scanner using Claude Agent SDK."""

from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, ResultMessage

from issue_agent.prompts import build_graph_prompt


async def run_graph(
    repo_url: str,
    model: str = "claude-sonnet-4-20250514",
    max_turns: int = 30,
    depth: int = 1,
    no_downstream: bool = False,
    verbose: bool = False,
) -> bool:
    """Run the repo-graph agent.

    Returns True if the graph was generated successfully.
    """
    prompt = build_graph_prompt(repo_url, depth=depth, no_downstream=no_downstream)

    click_echo = _make_echo(verbose)
    click_echo(f"\n  issue-agent graph\n  {repo_url}\n", bold=True)

    success = False

    async for message in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            allowed_tools=["Bash", "WebFetch", "Read", "Glob", "Grep"],
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
                    elif stripped.startswith("```") or stripped.startswith("graph "):
                        click_echo(stripped)
                    elif "REPO GRAPH REPORT" in stripped or stripped.startswith("UPSTREAM") or stripped.startswith("DOWNSTREAM") or stripped.startswith("RISK"):
                        click_echo(stripped, bold=True)
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
