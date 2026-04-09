# Issue Agent

AI-powered CLI for automated GitHub issue fixing and dependency graph scanning. Built with the [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk).

## What It Does

**`issue-agent fix`** — Give it a GitHub issue URL. It reads the issue, explores the repo, writes a fix, runs the test suite iteratively, and opens a draft PR.

**`issue-agent graph`** — Give it a GitHub repo URL. It maps the full upstream/downstream dependency graph by scanning package manifests, GitHub Actions, code-level imports, environment variables, and more.

## Install

```bash
git clone https://github.com/jc-2025/issue-agent.git
cd issue-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

**Requirements:**
- Python 3.11+
- `ANTHROPIC_API_KEY` environment variable set
- `gh` CLI installed and authenticated (`gh auth login`)

## Usage

### Fix a GitHub Issue

```bash
issue-agent fix https://github.com/owner/repo/issues/42
```

The agent will:
1. Fetch the issue details
2. Explore the codebase to understand the bug
3. Create a fix branch
4. Implement the minimal fix
5. Run tests (up to 3 attempts)
6. Open a draft PR if tests pass

```
[ISSUE]    #42: Config parser crashes on empty input
[EXPLORE]  Found test runner: pytest
[EXPLORE]  Relevant files: src/config.py, tests/test_config.py
[BASELINE] 14 passed, 1 failed
[BRANCH]   fix/issue-42-empty-input-crash
[WRITE]    src/config.py
[TEST]     Attempt 1/3 — PASS (15 passed, 0 failed)
[PR]       Draft PR opened: https://github.com/owner/repo/pull/43
[DONE]     Issue #42 fixed and PR opened.
```

### Map a Dependency Graph

```bash
issue-agent graph https://github.com/owner/repo
```

Options:
- `--depth 2` — recurse into upstream dependencies
- `--no-downstream` — skip downstream detection (faster)

Output includes a Mermaid diagram and structured report:

```
[SETUP]      owner/repo — Python — 142 stars
[UPSTREAM]   Manifests: found 12 packages, resolved 8 to GitHub repos
[UPSTREAM]   Actions: found 3 workflow files, 5 action dependencies
[UPSTREAM]   Code signals: found 2 API/SDK dependencies
[DOWNSTREAM] Found 4 dependent repos

REPO GRAPH REPORT: owner/repo
UPSTREAM (15 dependencies)
DOWNSTREAM (4 dependents)
RISK SUMMARY: 2 HIGH, 8 MEDIUM, 5 LOW
```

### Options

Both commands support:
- `--model <model>` — Claude model to use (default: claude-sonnet-4-20250514)
- `--max-turns <n>` — max agent loop iterations
- `--verbose` — show full agent message stream

## How It Works

Issue Agent uses the Claude Agent SDK to run an autonomous agent loop. Claude decides which files to read, what changes to make, and when to run tests — the SDK handles tool execution and the reasoning loop.

The agent has access to: file reading/writing, bash commands, web fetching, and code search (glob/grep). All reasoning and decision-making is done by Claude.

## Architecture

```
issue_agent/
  cli.py       — Click CLI with fix and graph commands
  fix.py       — Agent SDK wrapper for issue fixing
  graph.py     — Agent SDK wrapper for dependency scanning
  prompts.py   — Prompt templates for both agents
```

## License

MIT
