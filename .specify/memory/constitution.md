<!-- Sync Impact Report
Version change: 0.0.0 (template) → 1.0.0 (initial ratification)
Added sections: Core Principles (I–V), Tech Stack, Development Workflow, Governance
Removed sections: none (all placeholders replaced)
Templates requiring updates:
  ✅ constitution.md updated
  ⚠ plan-template.md — review for Constitution Check alignment
  ⚠ spec-template.md — review for scope/requirements alignment
  ⚠ tasks-template.md — verify task categories match principles
Follow-up TODOs: none
-->

# IssueAgent Constitution

## Core Principles

### I. Claude-First (NON-NEGOTIABLE)
All AI reasoning, tool use, and agentic behavior MUST be implemented via the Anthropic Claude API.
No other LLM or AI provider is permitted. The agent loop, tool definitions, and orchestration
are built around Claude's tool use API exclusively. External AI wrappers (LangChain, etc.) are
prohibited — use the SDK directly.

### II. Agentic Loop Architecture
The core of this system is a plan → act → observe → repeat loop. Claude MUST drive all
decisions about which files to read, what changes to make, and when to stop. The loop continues
until tests pass or a max-iteration limit is reached. No hardcoded decision trees — Claude reasons
at runtime.

### III. Real-World Effects Only (No Mocks in Production)
The agent operates on real GitHub repos via the GitHub REST API and executes real code in a
sandboxed subprocess environment. All tool implementations MUST produce real, observable effects.
Mock tools are only permitted in unit tests.

### IV. Test-Driven Validation
The agent MUST run the repo's existing test suite after every code change and use the output
to inform the next step. If no test suite exists, the agent MUST surface this clearly rather
than assuming success. Tests are the ground truth for "did the fix work."

### V. Simplicity and Scope Discipline
The MVP targets Python repos and straightforward bug-fix issues only. Scope creep into
architectural changes, multi-file refactors, or non-Python repos is explicitly out of scope
for v1. YAGNI — build what is needed to demo a working agentic loop, nothing more.

## Tech Stack

- **Language**: Python 3.11+
- **AI**: Anthropic Claude API (claude-sonnet latest) with tool use
- **GitHub**: PyGitHub or direct GitHub REST API
- **Sandbox**: subprocess with temp directory isolation
- **Interface**: CLI (MVP), optional Next.js frontend later
- **Dependencies**: anthropic, pygithub, pytest (for own tests)

## Development Workflow

All code is written with Claude Code. Each feature begins with a failing test before
implementation (red-green-refactor). PRs are small and scoped to a single principle or
component. The agent should be demoed on a real public Python repo with a real issue before
considering v1 complete.

## Governance

This constitution supersedes all other practices on this project. Amendments require updating
this file with a version bump and a rationale comment. All implementation decisions MUST be
traceable to one of the five principles above. If a decision cannot be justified by a principle,
either reject the decision or amend the constitution first.

**Version**: 1.0.0 | **Ratified**: 2026-04-08 | **Last Amended**: 2026-04-08
