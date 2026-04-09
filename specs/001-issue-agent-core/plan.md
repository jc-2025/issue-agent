# Implementation Plan: Autonomous GitHub Issue Fixer

**Branch**: `001-issue-agent-core` | **Date**: 2026-04-08 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-issue-agent-core/spec.md`

## Summary

Build a CLI tool that accepts a GitHub issue URL, uses a Claude-powered agentic loop with tool
use to explore the repository, apply a code fix, run the test suite iteratively, and open a
draft PR when tests pass. The agent loop is the core architectural primitive — Claude drives
all reasoning about what to read, change, and verify.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: anthropic (Claude API + tool use), PyGitHub (GitHub REST API), subprocess (test runner), tempfile (sandbox), click (CLI)
**Storage**: N/A — all state is in-memory during a run; temp directory is cleaned up after
**Testing**: pytest for own test suite; subprocess to run target repo's test suite
**Target Platform**: macOS / Linux CLI
**Project Type**: CLI tool
**Performance Goals**: Complete a full run (success or failure) within 5 minutes
**Constraints**: Max 3 retry attempts per run; agent loop capped at 20 iterations to prevent runaway costs
**Scale/Scope**: MVP — single issue, single repo, Python-only target repos

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Claude-First | ✅ PASS | All AI reasoning via Anthropic SDK tool use. No other LLM. |
| II. Agentic Loop | ✅ PASS | Core loop: plan → act (read/write/run) → observe → repeat |
| III. Real-World Effects | ✅ PASS | Real GitHub API, real subprocess test execution, real PRs |
| IV. Test-Driven Validation | ✅ PASS | Agent runs target test suite; own code uses pytest |
| V. Simplicity & Scope | ✅ PASS | Python repos only, bug fixes only, CLI interface, no frontend |

No violations. Proceeding to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/001-issue-agent-core/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (from /speckit-tasks)
```

### Source Code (repository root)

```text
issue_agent/
├── __init__.py
├── cli.py               # Click CLI entrypoint — accepts issue URL
├── github_client.py     # GitHub API: fetch issue, clone repo, open PR
├── agent.py             # Claude agentic loop — tool definitions + loop
├── tools.py             # Tool implementations: read_file, write_file, list_dir, run_tests
└── sandbox.py           # Temp directory lifecycle management

tests/
├── unit/
│   ├── test_agent.py
│   ├── test_tools.py
│   └── test_github_client.py
└── integration/
    └── test_full_run.py  # End-to-end against a real fixture repo

main.py                  # Entrypoint: `python main.py <issue-url>`
requirements.txt
README.md
```

**Structure Decision**: Single-project CLI layout. No frontend needed for MVP. Clean separation
between GitHub I/O, agent loop, tool execution, and sandbox management.
