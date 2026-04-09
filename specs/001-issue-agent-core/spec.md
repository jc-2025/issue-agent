# Feature Specification: Autonomous GitHub Issue Fixer

**Feature Branch**: `001-issue-agent-core`
**Created**: 2026-04-08
**Status**: Draft
**Input**: User description: "Autonomous GitHub issue fixer agent — given a GitHub issue URL, reads the repo, writes a fix, runs tests, opens a PR"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Fix a Bug From a GitHub Issue URL (Priority: P1)

A developer pastes a GitHub issue URL into the tool. The agent reads the issue description,
explores the repository to understand the relevant code, proposes and applies a fix, runs the
existing test suite to verify the fix works, and opens a draft PR on GitHub with a description
of what was changed and why.

**Why this priority**: This is the entire product. Everything else is secondary to this flow working end-to-end.

**Independent Test**: Can be tested by running the CLI with a real public Python repo issue URL and
verifying that a draft PR is opened with a meaningful code change and passing tests.

**Acceptance Scenarios**:

1. **Given** a valid GitHub issue URL for a Python repo with a reproducible bug, **When** the user runs the agent, **Then** a draft PR is opened within a reasonable time containing a code fix that makes the relevant tests pass.
2. **Given** the same issue URL, **When** the agent completes, **Then** the PR description explains what was changed and references the original issue.
3. **Given** a repo where the fix attempt causes tests to fail, **When** the agent observes the failure, **Then** it retries with a revised approach before giving up.

---

### User Story 2 - Transparent Agent Progress (Priority: P2)

The developer can see what the agent is doing in real time — which files it is reading, what
changes it is making, what the test output says — so they can trust the process and intervene
if needed.

**Why this priority**: Without visibility into agent reasoning, the tool is a black box and
developers won't trust it. Transparency is required for the demo to be compelling.

**Independent Test**: Can be tested by running the agent and verifying that each step
(file read, code edit, test run, PR creation) is printed to the console as it happens.

**Acceptance Scenarios**:

1. **Given** the agent is running, **When** it reads a file, **Then** the filename is printed to stdout.
2. **Given** the agent runs tests, **When** results are returned, **Then** pass/fail status and relevant output are shown to the user.
3. **Given** the agent opens a PR, **When** it succeeds, **Then** the PR URL is printed.

---

### User Story 3 - Graceful Failure With Clear Explanation (Priority: P3)

When the agent cannot fix the issue — because it is too complex, out of scope, or tests keep
failing — it exits cleanly and tells the developer exactly why it gave up and what it tried.

**Why this priority**: Graceful failure prevents silent errors and maintains trust even when the
agent doesn't succeed.

**Independent Test**: Can be tested by pointing the agent at an intentionally complex or
out-of-scope issue and verifying the error message is useful and no partial PR is opened.

**Acceptance Scenarios**:

1. **Given** an issue that requires architectural changes beyond bug fixing, **When** the agent detects this, **Then** it exits without opening a PR and explains the limitation.
2. **Given** the agent has exhausted its retry attempts with failing tests, **When** it gives up, **Then** it summarizes what it tried and why it failed.

---

### Edge Cases

- What happens when the repo has no test suite? Agent surfaces this clearly and does not assume the fix is correct.
- What happens when the GitHub issue is ambiguous or lacks reproduction steps? Agent makes a best-effort attempt or exits with a clear explanation — it never asks the user follow-up questions.
- What happens when the fix requires changes to multiple files? Handled for simple cases (1–3 files); declared out of scope for complex refactors.
- What happens when the repo is private and the user lacks access? Agent surfaces an auth error immediately.
- What happens when tests time out? Agent treats a timeout as a failure and retries or exits cleanly.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept a GitHub issue URL as the primary input via CLI.
- **FR-002**: System MUST fetch the issue title and body from the GitHub API.
- **FR-003**: System MUST clone or shallow-fetch the target repository into a temporary working directory.
- **FR-004**: System MUST use an AI agent loop to identify which files are relevant to the issue.
- **FR-005**: System MUST apply code changes to the relevant files based on AI reasoning.
- **FR-006**: System MUST execute the repository's existing test suite after each change and capture the output.
- **FR-007**: System MUST retry with a revised fix if tests fail, up to a configurable maximum number of attempts (default: 3).
- **FR-008**: System MUST open a draft pull request on GitHub when tests pass, referencing the original issue.
- **FR-009**: System MUST print progress to stdout at each major step (file read, edit, test run, PR open).
- **FR-010**: System MUST exit cleanly with a clear explanation if it cannot produce a passing fix.
- **FR-011**: System MUST operate only on Python repositories for MVP scope.

### Key Entities

- **Issue**: A GitHub issue with a URL, title, body, and associated repository.
- **Repository**: A GitHub repo cloned into a temp directory; has files, a test suite, and a default branch.
- **AgentLoop**: The iterative reasoning cycle — reads files, writes changes, observes test results, decides next action.
- **Fix**: A set of file edits produced by the agent intended to resolve the issue.
- **PullRequest**: A GitHub draft PR opened against the target repo's default branch, containing the fix and a generated description.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The agent successfully opens a valid draft PR for at least 3 out of 5 simple, well-defined Python bug issues used in demo testing.
- **SC-002**: Each run completes (success or graceful failure) within 5 minutes on a standard laptop.
- **SC-003**: The PR description is coherent and references the original issue in 100% of successful runs.
- **SC-004**: The agent never opens a PR when tests are still failing.
- **SC-005**: Progress output is visible to the user within 10 seconds of starting a run.

## Assumptions

- The target repository is a public Python project with a runnable test suite (pytest or unittest).
- The GitHub issue describes a bug, not a feature request or architectural change.
- The user has a valid GitHub personal access token available as an environment variable.
- The fix can be accomplished by modifying existing files only — no new files required for MVP.
- The agent runs on macOS or Linux; Windows is out of scope for v1.
- A single issue maps to a localized code change affecting 1–3 files.
