---
name: issue-fix
description: Autonomous GitHub issue fixer. Given a GitHub issue URL, explores the repo, writes a fix, runs tests iteratively, and opens a draft PR. Uses Claude's native tools — no external dependencies required.
---

## User Input

```text
$ARGUMENTS
```

The argument is a GitHub issue URL. Example: `https://github.com/owner/repo/issues/42`

---

## Pre-flight: Load Repo Graph

Before doing anything else, check if `.claude/repo-graph.json` exists in the project root.

```bash
cat .claude/repo-graph.json 2>/dev/null
```

If it exists, load it silently. You will use it in two ways:
1. **Before writing any fix** — check if the file you're about to modify is depended on by any downstream repo. If so, add a warning to the PR body.
2. **In the PR description** — if downstream consumers exist, list them under a "Blast Radius" section.

If the graph doesn't exist, continue normally — just skip the blast radius check.

---

## Pre-flight Checks

Before doing anything else, verify the environment is ready:

```bash
# Check GitHub CLI is authenticated
gh auth status 2>&1
```

```bash
# Check ANTHROPIC_API_KEY is set (needed if spawning sub-agents — not required for skill-only use)
echo ${ANTHROPIC_API_KEY:+"API key present"}
```

If `gh auth status` fails, stop immediately and tell the user to run `gh auth login` first.

---

## Execution Workflow

### Step 1 — Parse and Fetch the Issue

Extract `owner`, `repo`, and `issue_number` from the URL.

```bash
gh issue view <issue_number> --repo <owner>/<repo> --json number,title,body,labels,state
```

- If the issue is closed, warn the user but proceed unless they say to stop.
- If the issue is not found or access is denied, stop and report the error clearly.
- Print: `[ISSUE] #<number>: <title>`

---

### Step 2 — Understand the Repository

You are already in the repo (or the user is running this from the repo root). Do NOT clone — operate on the working directory.

Explore the codebase systematically:

1. Read the top-level directory structure
2. Identify the language and test framework (look for `pytest.ini`, `setup.py`, `pyproject.toml`, `package.json`, `Makefile`, etc.)
3. Read the README if present — extract any setup or test-running instructions
4. Search for files most likely related to the issue:
   - Grep for keywords from the issue title and body
   - Look for filenames that match the described component or feature
   - Read the 2-3 most relevant files fully before forming a hypothesis

**Do not guess at which files are relevant based on the issue title alone.** Read enough code to actually understand the bug before proposing a fix.

Print: `[EXPLORE] Found test runner: <pytest|unittest|npm test|etc>`
Print: `[EXPLORE] Relevant files: <file1>, <file2>, ...`

---

### Step 3 — Reproduce the Failure (if possible)

Before writing any code, run the existing test suite to establish a baseline:

```bash
# Run tests and capture output
<test_command> 2>&1 | head -100
```

- If tests are already failing in a way that matches the issue → good, you have a target.
- If all tests pass → the issue may be a missing test case. Note this and proceed.
- If tests error out due to setup/deps → report the setup error to the user and stop.

Print: `[BASELINE] <X> passed, <Y> failed, <Z> errors`

---

### Step 4 — Form a Fix Hypothesis

Based on your reading of the code and the issue description, articulate:

1. **Root cause**: What is actually wrong and why
2. **Fix approach**: What change will resolve it
3. **Risk assessment**: What else might break

Do this as internal reasoning — do NOT print a long explanation to the user unless you are genuinely uncertain. If uncertain about the correct fix, pick the most conservative option (smallest change with least side effects).

---

### Step 5 — Create a Working Branch

```bash
# Create a branch named after the issue
git checkout -b fix/issue-<issue_number>-<slug>
```

Where `<slug>` is a 2-3 word kebab-case description of the fix (e.g. `fix/issue-42-null-pointer-check`).

Print: `[BRANCH] fix/issue-<number>-<slug>`

---

### Step 6 — Implement the Fix

Write the minimal change needed to fix the issue:

- Change only what is necessary — do not refactor unrelated code
- If the fix requires a new test, write it
- If the issue mentions a specific behavior, ensure the fix matches that behavior exactly
- Preserve existing code style, naming conventions, and formatting

Print: `[WRITE] <filename>` for each file modified.

---

### Step 7 — Verify the Fix (Iterative Loop)

Run the test suite after every change. Iterate until tests pass or you exhaust attempts.

**Attempt loop (max 3 attempts)**:

```bash
<test_command> 2>&1
```

**On each attempt**:
- If tests pass → proceed to Step 8
- If tests fail → read the failure output carefully, revise your hypothesis, update the fix
- If the same failure repeats twice → your fix approach is wrong; reconsider root cause

**If tests are still failing after 3 attempts**:
- Do NOT open a PR
- Restore the original files (`git checkout -- .`)
- Delete the branch (`git checkout main && git branch -D fix/issue-<number>-<slug>`)
- Print a clear summary of: what you tried, what the test output was, why you gave up
- Suggest what a human developer should investigate next

Print after each run: `[TEST] Attempt <N>/3 — <PASS|FAIL> (<X> passed, <Y> failed)`

---

### Step 8 — Open a Draft PR

Tests are passing. Open a draft PR:

```bash
gh pr create \
  --title "<concise fix description>" \
  --body "$(cat <<'EOF'
## Summary

<1-3 sentences describing what was wrong and how it was fixed>

## Changes

<bullet list of files changed and what was changed in each>

## Testing

- All existing tests pass
- <describe any new tests added>

Closes #<issue_number>
EOF
)" \
  --draft \
  --base main
```

**PR title format**: `fix: <what was fixed> (#<issue_number>)`
Example: `fix: handle null input in parse_config (#42)`

Print: `[PR] Draft PR opened: <url>`
Print: `[DONE] ✓ Issue #<number> fixed and PR opened.`

---

## Quality Rules

These are non-negotiable — violating any of them means stopping and telling the user why:

- **Never open a PR with failing tests.** Not even "mostly passing."
- **Never modify more than 5 files.** If the fix requires more, it's out of scope — stop and explain.
- **Never rewrite working code.** Fix the bug, don't refactor the module.
- **Never delete tests.** If a test is in your way, that test is probably right and your fix is wrong.
- **Always reference the issue number** in the branch name, commit, and PR.
- **If you are not confident in the fix**, say so in the PR body. Don't pretend.

---

## Output Format Summary

Every step prints a prefixed status line so the user always knows what's happening:

```
[ISSUE]   #42: Config parser crashes on empty input
[EXPLORE] Found test runner: pytest
[EXPLORE] Relevant files: src/config.py, tests/test_config.py
[BASELINE] 14 passed, 1 failed
[BRANCH]  fix/issue-42-empty-input-crash
[WRITE]   src/config.py
[TEST]    Attempt 1/3 — FAIL (14 passed, 1 failed)
[WRITE]   src/config.py
[TEST]    Attempt 2/3 — PASS (15 passed, 0 failed)
[PR]      Draft PR opened: https://github.com/owner/repo/pull/43
[DONE]    ✓ Issue #42 fixed and PR opened.
```
