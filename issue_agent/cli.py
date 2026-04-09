"""CLI entrypoint for issue-agent."""

import asyncio
import sys

import click

from issue_agent import __version__


@click.group()
@click.version_option(version=__version__)
def main():
    """AI-powered GitHub issue fixer and dependency graph scanner."""


@main.command()
@click.argument("issue_url")
@click.option("--model", default="claude-sonnet-4-20250514", help="Claude model to use.")
@click.option("--max-turns", default=50, help="Max agent loop iterations.")
@click.option("--verbose", is_flag=True, help="Show full agent message stream.")
def fix(issue_url: str, model: str, max_turns: int, verbose: bool):
    """Fix a GitHub issue and open a draft PR.

    ISSUE_URL is the full GitHub issue URL, e.g.
    https://github.com/owner/repo/issues/42
    """
    from issue_agent.fix import run_fix

    asyncio.run(run_fix(issue_url, model=model, max_turns=max_turns, verbose=verbose))


@main.command()
@click.argument("repo_url")
@click.option("--model", default="claude-sonnet-4-20250514", help="Claude model to use.")
@click.option("--max-turns", default=30, help="Max agent loop iterations.")
@click.option("--depth", default=1, help="Recursion depth for upstream scanning.")
@click.option("--no-downstream", is_flag=True, help="Skip downstream detection.")
@click.option("--verbose", is_flag=True, help="Show full agent message stream.")
def graph(repo_url: str, model: str, max_turns: int, depth: int, no_downstream: bool, verbose: bool):
    """Map the dependency graph for a GitHub repository.

    REPO_URL is the full GitHub repo URL, e.g.
    https://github.com/owner/repo
    """
    from issue_agent.graph import run_graph

    asyncio.run(run_graph(
        repo_url,
        model=model,
        max_turns=max_turns,
        depth=depth,
        no_downstream=no_downstream,
        verbose=verbose,
    ))


if __name__ == "__main__":
    main()
