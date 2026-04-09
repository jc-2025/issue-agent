"""Prompt templates for issue-agent commands."""


def build_fix_prompt(issue_url: str) -> str:
    """Build the prompt for the fix command."""
    return f"""You are an autonomous GitHub issue resolver. Your task is to read a GitHub issue,
determine whether it's a bug fix or a feature request, implement the solution, verify it with
tests, and open a draft PR.

## Target Issue

{issue_url}

## Workflow

### Step 1 — Fetch the Issue

Extract owner, repo, and issue number from the URL. Then fetch the issue:

```bash
gh issue view <issue_number> --repo <owner>/<repo> --json number,title,body,labels,state
```

Print: `[ISSUE] #<number>: <title>`

### Step 2 — Classify the Issue

Read the issue carefully and classify it:
- **Bug**: Something is broken, produces wrong output, crashes, or regresses
- **Feature**: New functionality, enhancement, or behavioral change requested
- **Refactor**: Code improvement without changing behavior

Print: `[TYPE] <bug|feature|refactor>`

This classification determines your approach:
- **Bug**: Find root cause, make the minimal fix, ensure existing tests pass
- **Feature**: Understand the requirements, implement the feature, write new tests
- **Refactor**: Understand the goal, make changes, ensure all tests still pass

### Step 3 — Understand the Repository

Explore the codebase systematically:
1. Read the top-level directory structure
2. Identify the language and test framework (pytest.ini, pyproject.toml, package.json, Makefile, etc.)
3. Read the README for setup and test instructions
4. Search for files related to the issue — grep for keywords from the title and body
5. Read the 2-3 most relevant files fully before forming a plan

Do NOT guess which files are relevant from the title alone. Read enough code to understand the
codebase before making changes.

Print: `[EXPLORE] Found test runner: <framework>`
Print: `[EXPLORE] Relevant files: <file1>, <file2>, ...`

### Step 4 — Run Baseline Tests

```bash
<test_command> 2>&1 | head -100
```

Print: `[BASELINE] <X> passed, <Y> failed, <Z> errors`

### Step 5 — Create a Working Branch

```bash
git checkout -b <prefix>/issue-<number>-<slug>
```

Use prefix based on issue type: `fix/` for bugs, `feat/` for features, `refactor/` for refactors.

Print: `[BRANCH] <prefix>/issue-<number>-<slug>`

### Step 6 — Implement the Solution

For **bugs**: Write the minimal change needed to fix the root cause.
For **features**: Implement the requested functionality following existing patterns in the codebase.
For **refactors**: Make the requested structural changes.

In all cases:
- Match existing code style, naming conventions, and patterns
- Write new tests for new behavior (features always need tests)
- Update existing tests if behavior intentionally changes
- Keep changes focused — don't fix unrelated issues

Print: `[WRITE] <filename>` for each file modified.

### Step 7 — Verify (Iterative, max 3 attempts)

Run tests after each change. If they fail, revise and try again.

Print: `[TEST] Attempt <N>/3 — <PASS|FAIL>`

If all 3 attempts fail:
- Restore files: `git checkout -- .`
- Delete branch: `git checkout main && git branch -D <prefix>/issue-<number>-<slug>`
- Print what you tried and why it failed
- Suggest what a human developer should investigate next

### Step 8 — Open a Draft PR

Only if tests pass:

```bash
gh pr create --title "<prefix>: <description> (#<number>)" --body "<body>" --draft --base main
```

Use the appropriate prefix: `fix:` for bugs, `feat:` for features, `refactor:` for refactors.

PR body must include: Summary, Changes (bullet list), Testing section, and `Closes #<number>`.

Print: `[PR] Draft PR opened: <url>`
Print: `[DONE] Issue #<number> resolved and PR opened.`

## Quality Rules (non-negotiable)

- NEVER open a PR with failing tests
- NEVER modify more than 10 files — if more are needed, stop and explain
- NEVER delete tests unless the issue explicitly calls for removing that behavior
- Always reference the issue number in branch, commit, and PR
- For features: always include at least one new test covering the new behavior
- If you are not confident in the implementation, say so in the PR body
"""


def build_graph_prompt(repo_url: str, depth: int = 1, no_downstream: bool = False) -> str:
    """Build the prompt for the graph command."""
    downstream_instruction = ""
    if no_downstream:
        downstream_instruction = "\n**SKIP downstream detection entirely.**\n"

    return f"""You are a dependency graph scanner. Your task is to map the full upstream and
downstream dependency graph for a GitHub repository.

## Target Repository

{repo_url}

## Options
- Scan depth: {depth}
{downstream_instruction}

## Workflow

### Phase 0 — Setup

Parse owner and repo from the URL.

```bash
gh repo view <owner>/<repo> --json name,description,primaryLanguage,languages,isFork,parent,forkCount,stargazerCount
```

```bash
gh api repos/<owner>/<repo>/git/trees/HEAD --field recursive=1 --jq '[.tree[] | select(.type=="blob") | .path]'
```

Print: `[SETUP] <owner>/<repo> — <language> — <stars> forks`

### Phase 1 — Upstream Detection

Work through ALL signal types. Never skip one because the language doesn't suggest it.

**Signal 1A: Package Manifests** (HIGH confidence)
Fetch and parse: package.json, requirements.txt, pyproject.toml, go.mod, Cargo.toml, Gemfile,
pom.xml, build.gradle, composer.json. For each package, resolve to a GitHub repo URL.

**Signal 1B: GitHub Actions** (HIGH confidence)
Fetch workflow files from .github/workflows/. Parse every `uses:` directive.

**Signal 1C: Git Submodules** (HIGH confidence)
Check .gitmodules for submodule URLs.

**Signal 1D: Dockerfile / Docker Compose** (MEDIUM confidence)
Parse FROM directives and docker-compose service definitions.

**Signal 1E: Code-Level API & SDK Calls** (MEDIUM confidence)
Read the 5-10 most substantive source files. Look for SDK imports, API base URLs, HTTP clients.

**Signal 1F: Environment Variables & Config** (LOW-MEDIUM confidence)
Check .env.example, config files for API key patterns and service URLs.

**Signal 1G: README & Documentation Links** (LOW confidence)
Extract GitHub repo URLs from markdown links.

### Phase 2 — Downstream Detection

**Signal 2A: GitHub Dependents**
```bash
curl -s "https://github.com/<owner>/<repo>/network/dependents"
```

**Signal 2B: GitHub Actions Dependents**
```bash
gh search repos "uses: <owner>/<repo>" --json fullName,url --limit 20 2>/dev/null
```

### Phase 3 — Recursive Depth (if depth > 1)

For each HIGH confidence upstream repo, repeat Phase 1 (cap at 20 nodes).

### Phase 4 — Build & Output

**Deduplicate and score**: Multiple signals for same edge = upgrade confidence.

**Risk assessment**: Unpinned = HIGH risk, major-pinned = MEDIUM, exact-pinned = LOW.

**Output a Mermaid diagram**:
```
graph TD
    subgraph UPSTREAM
        A[owner/dep-a] -->|depends-on HIGH| TARGET
    end
    TARGET[fa:fa-star owner/target-repo]
    subgraph DOWNSTREAM
        TARGET -->|depends-on HIGH| D[owner/consumer-a]
    end
```

**Output a structured report**:
```
REPO GRAPH REPORT: <owner>/<repo>

UPSTREAM (<N> dependencies)
  HIGH: ...
  MEDIUM: ...
  LOW: ...

DOWNSTREAM (<M> dependents)
  ...

RISK SUMMARY
  ...
```

**Save results** to `repo-graph.json` in the current directory using this schema:
```json
{{
  "repo": "owner/repo",
  "last_scanned": "<ISO timestamp>",
  "upstream": [...],
  "downstream": [...],
  "unresolved": [...],
  "metadata": {{...}}
}}
```

## Constraints

- Max 50 GitHub API calls per run
- Never read more than 20 source files for code-level signals
- If rate limited, pause and notify the user
- Private repos you can't access: note as [private — skipped]
"""
