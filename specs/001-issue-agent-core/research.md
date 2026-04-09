# Research: Autonomous GitHub Issue Fixer

**Phase**: 0 — Research & Decisions
**Date**: 2026-04-08

## Decision 1: Agent Loop Design

**Decision**: Use Claude's tool use API directly (no LangChain/LangGraph).

**Rationale**: Constitution Principle I prohibits AI wrappers. The Anthropic SDK's native tool
use is sufficient — define tools as JSON schemas, pass them in the API call, execute tool calls
returned by Claude, feed results back as tool_result messages, repeat until Claude returns a
stop_reason of "end_turn".

**Alternatives considered**:
- LangChain/LangGraph: Rejected — adds abstraction over tool use, violates Claude-First principle
- Custom orchestration framework: Rejected — overkill for MVP; native SDK loop is simpler

---

## Decision 2: GitHub Interaction

**Decision**: Use PyGitHub for issue/PR operations; use `git clone` via subprocess for repo access.

**Rationale**: PyGitHub provides clean Python abstractions for GitHub REST API (fetch issues,
create PRs, list branches). Cloning via subprocess is simpler than using the GitHub Contents API
for full repo access — especially for running tests which require a real filesystem.

**Alternatives considered**:
- GitHub Contents API only: Rejected — can't run tests without a full local clone
- GitPython: Considered but subprocess `git clone` is simpler for read + single-branch use

---

## Decision 3: Sandbox / Isolation

**Decision**: Clone repo into Python `tempfile.mkdtemp()`, run all operations there, clean up on exit.

**Rationale**: Keeps host filesystem clean. Subprocess test execution is scoped to the temp dir.
Simple try/finally ensures cleanup even on failure.

**Alternatives considered**:
- Docker container: Rejected — adds setup complexity, overkill for MVP
- In-memory filesystem: Rejected — can't run subprocess tests against it

---

## Decision 4: Tool Set for Agent

**Decision**: Provide Claude exactly 5 tools:

| Tool | Purpose |
|------|---------|
| `list_directory` | Explore repo structure — returns file tree for a path |
| `read_file` | Read file contents — returns text |
| `write_file` | Write/overwrite a file — applies code changes |
| `run_tests` | Run pytest/unittest in sandbox — returns stdout/stderr |
| `finish` | Signal completion — agent calls this when done or giving up |

**Rationale**: Minimal surface area, easy to implement and test. Claude can navigate any repo
with just list + read + write + run. The `finish` tool gives Claude a clean way to terminate
the loop with a status message (success or failure reason).

**Alternatives considered**:
- Search/grep tool: Useful but Claude can reason from file list + targeted reads for MVP
- Bash execution tool: Too broad, security risk, out of scope for MVP

---

## Decision 5: Retry / Loop Termination

**Decision**: Max 3 fix attempts (configurable via `--max-retries`). Max 20 total tool calls
per run to cap API cost. Agent loop exits when Claude calls `finish` or limits are hit.

**Rationale**: 3 attempts is enough to handle common test-fix-retest cycles without burning
excessive API credits. 20 tool call cap prevents runaway loops on complex issues.

---

## Decision 6: PR Description Generation

**Decision**: Ask Claude to generate the PR title and body as part of the `finish` tool call
payload — fields: `status`, `pr_title`, `pr_body`, `files_changed`.

**Rationale**: Claude already has full context of what it changed and why. Generating the PR
description in the same call avoids an extra API round-trip.

---

## Resolved Clarifications

None — spec had no open clarifications.
