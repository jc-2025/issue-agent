---
name: repo-graph
description: Maps the full upstream/downstream dependency graph for a GitHub repo. Saves results to .claude/repo-graph.json. Supports refresh (re-scan + merge), manual additions, and is read by other skills (issue-fix, etc.) to assess blast radius before making changes.
---

## User Input

```text
$ARGUMENTS
```

**Modes** (determined from arguments):

| Invocation | Mode |
|-----------|------|
| `/repo-graph init https://github.com/owner/repo` | Initial scan — build graph from scratch, create `.claude/repo-graph.json` |
| `/repo-graph refresh` | Re-scan repo and merge with existing graph, preserving manual entries |
| `/repo-graph add upstream github.com/owner/dep "reason"` | Manually add an upstream edge |
| `/repo-graph add downstream github.com/owner/consumer "reason"` | Manually add a downstream edge |
| `/repo-graph show` | Print the current saved graph without re-scanning |
| `/repo-graph show --mermaid` | Print the Mermaid diagram for the current saved graph |

Optional flags for scan modes:
- `--depth 2` — recurse into upstream dependencies (default: 1)
- `--no-downstream` — skip downstream detection (faster)
- `--json` — output raw JSON instead of Mermaid + report

---

## Persistence: `.claude/repo-graph.json`

After every scan or manual edit, save the full graph to `.claude/repo-graph.json` in the project root.

**This file is the source of truth.** Other skills read it. Never overwrite manual entries on refresh — merge instead.

### Schema

```json
{
  "repo": "owner/repo",
  "last_scanned": "2026-04-08T00:00:00Z",
  "upstream": [
    {
      "repo": "owner/dep-a",
      "type": "depends-on",
      "confidence": "HIGH",
      "signals": ["requirements.txt line 4"],
      "version": "^2.1.0",
      "break_risk": "MEDIUM",
      "manual": false,
      "note": ""
    }
  ],
  "downstream": [
    {
      "repo": "owner/consumer-x",
      "type": "depends-on",
      "confidence": "HIGH",
      "signals": ["GitHub dependents page"],
      "manual": false,
      "note": ""
    }
  ],
  "unresolved": [
    {
      "name": "stripe",
      "type": "calls-api",
      "signals": ["src/billing.py import stripe"],
      "note": "Could not resolve to GitHub repo"
    }
  ],
  "metadata": {
    "primary_language": "Python",
    "is_fork": false,
    "parent_repo": null,
    "scan_depth": 1,
    "api_calls_used": 23
  }
}
```

### Merge Rules (on refresh)

- Any entry with `"manual": true` is **never overwritten or deleted** — preserve it exactly
- Scanned entries from the previous run that are no longer found → move to an `"archived"` array with a `removed_at` timestamp (don't silently delete)
- New entries found in the re-scan → add normally with `"manual": false`
- If a scanned entry already exists, update `signals`, `confidence`, `break_risk`, and `last_scanned` but preserve any user-added `note`

---

## Manual Add Mode

When invoked as `/repo-graph add upstream github.com/owner/dep "we call their internal webhook"`:

1. Read `.claude/repo-graph.json`
2. Add the new entry with `"manual": true`, `"confidence": "HIGH"`, `"signals": ["manually added"]`, and the provided reason as `"note"`
3. Save the file
4. Print confirmation: `[ADDED] upstream: github.com/owner/dep (manual) — "we call their internal webhook"`

Manual entries appear in the graph and report with a 📌 pin icon to distinguish them from scanned entries.

---

## Mental Model

You are building a **directed dependency graph** centered on the target repo.

```
[upstream-repo-A] ──depends-on──▶ [TARGET REPO] ──depends-on──▶ [upstream-repo-B]
[downstream-repo-X] ◀──depends-on── [TARGET REPO]
```

Every edge has:
- **type**: one of `depends-on`, `dev-depends-on`, `uses-action`, `submodule`, `forks`, `calls-api`, `references`
- **confidence**: `HIGH` (explicit in manifest) / `MEDIUM` (inferred from code) / `LOW` (inferred from docs/config)
- **signal**: what evidence was found (e.g. `requirements.txt line 12`, `src/client.py import`)

Your job is to find as many edges as possible across ALL signal types, not just package manifests.

---

## Execution Workflow

### Phase 0 — Setup & Repo Access

Parse `owner` and `repo` from the URL.

```bash
# Fetch top-level metadata
gh repo view <owner>/<repo> --json name,description,primaryLanguage,languages,isFork,parent,templateRepository,forkCount,stargazerCount,defaultBranchRef
```

```bash
# Get the full file tree (up to 3 levels deep)
gh api repos/<owner>/<repo>/git/trees/HEAD --field recursive=1 --jq '[.tree[] | select(.type=="blob") | .path]'
```

Store the file tree. You will use it repeatedly to decide what to fetch next.

Print: `[SETUP] <owner>/<repo> — <primaryLanguage> — <starCount>★ <forkCount> forks`

If the repo is a fork, immediately record the parent as an upstream `forks` edge (HIGH confidence).

---

### Phase 1 — Upstream Detection

Work through every signal type below. For each one: fetch the relevant file(s), parse them, and record edges. Never skip a signal type just because the primary language doesn't suggest it — polyglot repos are common.

#### Signal 1A: Package Manifests (HIGH confidence)

Fetch and parse whichever of these exist in the file tree:

| File | Extracts |
|------|---------|
| `package.json` | `dependencies`, `devDependencies`, `peerDependencies` |
| `package-lock.json` / `yarn.lock` | resolved versions (use for pinned upstream) |
| `requirements.txt` / `requirements/*.txt` | Python packages |
| `pyproject.toml` | `[project.dependencies]`, `[tool.poetry.dependencies]` |
| `Pipfile` | `[packages]`, `[dev-packages]` |
| `go.mod` | `require` directives |
| `Cargo.toml` | `[dependencies]`, `[dev-dependencies]` |
| `Gemfile` | gem dependencies |
| `pom.xml` | `<dependency>` elements |
| `build.gradle` / `build.gradle.kts` | `dependencies {}` block |
| `composer.json` | `require`, `require-dev` |

For each package found, resolve it to a GitHub repo:

```bash
# For npm packages:
curl -s https://registry.npmjs.org/<package-name>/latest | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(d.get('repository', {}).get('url', '') or d.get('homepage', ''))
"

# For PyPI packages:
curl -s https://pypi.org/pypi/<package-name>/json | python3 -c "
import sys, json
d = json.load(sys.stdin)
info = d.get('info', {})
print(info.get('project_urls', {}).get('Source', '') or info.get('home_page', ''))
"
```

Only record packages that resolve to a GitHub URL. Ignore packages with no GitHub source.
Label `devDependencies` as `dev-depends-on`, everything else as `depends-on`.

Print: `[UPSTREAM] Manifests: found <N> packages, resolved <M> to GitHub repos`

---

#### Signal 1B: GitHub Actions (HIGH confidence)

```bash
gh api repos/<owner>/<repo>/contents/.github/workflows --jq '.[].name' 2>/dev/null
```

For each workflow file found:

```bash
gh api repos/<owner>/<repo>/contents/.github/workflows/<filename> --jq '.content' | base64 -d
```

Parse every `uses:` directive. These are direct `owner/repo@version` references.
Record as `uses-action` edges (HIGH confidence).

Also look for `actions/checkout`, `actions/setup-*` etc. — include these.

Print: `[UPSTREAM] Actions: found <N> workflow files, <M> action dependencies`

---

#### Signal 1C: Git Submodules (HIGH confidence)

```bash
gh api repos/<owner>/<repo>/contents/.gitmodules 2>/dev/null --jq '.content' | base64 -d
```

Parse every `url =` line. Record as `submodule` edges (HIGH confidence).

---

#### Signal 1D: Dockerfile / Docker Compose (MEDIUM confidence)

Fetch `Dockerfile`, `Dockerfile.*`, `docker-compose.yml`, `docker-compose.yaml` if present.

Parse:
- `FROM <image>` directives — if image references a GitHub package (`ghcr.io/owner/repo`), record as `depends-on`
- `docker-compose.yml` `build.context` pointing to another repo path is LOW confidence

---

#### Signal 1E: Code-Level API & SDK Calls (MEDIUM confidence)

This is the signal most tools miss. Fetch the 5-10 most substantive source files (prefer files named `client.py`, `api.py`, `service.ts`, `config.*`, `*client*`, `*service*`, `*sdk*`).

Look for:

```python
# Python patterns
import anthropic
import openai
import boto3
import stripe
requests.get("https://api.something.com")
BASE_URL = "https://..."
```

```typescript
// TypeScript/JS patterns
import Anthropic from '@anthropic-ai/sdk'
const client = new SomeClient(...)
fetch('https://api.something.com/...')
axios.get('https://...')
```

For each external API/SDK found:
- If it's a named SDK (`anthropic`, `openai`, `stripe`, `twilio`, etc.) → resolve to GitHub repo
- If it's a hardcoded URL → extract the domain, infer the service, note as `calls-api` (MEDIUM)
- Record confidence as MEDIUM (inferred, not declared)

Print: `[UPSTREAM] Code signals: found <N> API/SDK dependencies`

---

#### Signal 1F: Environment Variables & Config Files (LOW–MEDIUM confidence)

Fetch `.env.example`, `config.yaml`, `config.json`, `config.toml`, `settings.py`, `constants.*` if present.

Look for:
- Variable names like `STRIPE_API_KEY`, `OPENAI_API_KEY`, `AWS_*`, `GITHUB_TOKEN` → infer service dependency
- Base URL constants → infer API dependency
- Service names in connection strings

Record as `calls-api` with LOW confidence (existence of env var doesn't prove active use, but it's a signal).

---

#### Signal 1G: README & Documentation Links (LOW confidence)

```bash
gh api repos/<owner>/<repo>/contents/README.md --jq '.content' | base64 -d
```

Extract all markdown links `[text](url)` and bare URLs. Filter to GitHub repo URLs only.
Record as `references` edges (LOW confidence) — these are often upstream tools, related projects, or inspirations.

Also check `docs/`, `CONTRIBUTING.md`, `ARCHITECTURE.md` if they exist.

---

### Phase 2 — Downstream Detection

Find repos that depend on THIS repo.

#### Signal 2A: GitHub Dependents (HIGH confidence)

```bash
# GitHub exposes a dependents page — scrape it
curl -s "https://github.com/<owner>/<repo>/network/dependents" | python3 -c "
import sys, re
html = sys.stdin.read()
# Extract repo links from dependent list
matches = re.findall(r'href=\"/([^/]+/[^/\"]+)\"[^>]*>[^<]*</a>\s*</span>', html)
for m in set(matches[:20]):
    print(m)
"
```

Record each as a `depends-on` edge pointing INTO the target repo (downstream).

#### Signal 2B: GitHub Actions Dependents

```bash
# Search for repos using this as an action
gh search repos "uses: <owner>/<repo>" --json fullName,url --limit 20 2>/dev/null
```

Record as `uses-action` downstream edges.

#### Signal 2C: Package Registry Dependents

If the repo publishes to npm:
```bash
curl -s "https://registry.npmjs.org/-/v1/search?text=<package-name>&size=5" | python3 -c "
import sys, json
results = json.load(sys.stdin)
for r in results.get('objects', []):
    print(r['package']['name'], r['package'].get('links', {}).get('repository', ''))
"
```

If it publishes to PyPI — note the package name and weekly download count as a downstream impact metric.

Print: `[DOWNSTREAM] Found <N> dependent repos`

---

### Phase 3 — Recursive Depth (if --depth > 1)

For each upstream GitHub repo discovered in Phase 1 with HIGH confidence, repeat Phase 1 on that repo (one level deep). Mark these nodes as depth-2.

Cap at 20 total upstream nodes to avoid runaway API calls.

Print: `[RECURSE] Expanding <N> upstream repos to depth 2...`

---

### Phase 4 — Build & Output the Graph

#### 4A: Deduplicate and Score

Consolidate all edges. If the same relationship was found via multiple signals, upgrade the confidence:
- 2+ signals → upgrade LOW→MEDIUM or MEDIUM→HIGH
- Note all signals in the edge metadata

#### 4B: Risk Assessment

For each upstream dependency, assess break risk:
- **HIGH RISK**: Unpinned version (`*`, `latest`, no lockfile) + frequently updated repo
- **MEDIUM RISK**: Pinned major version only (`^1.x`)
- **LOW RISK**: Exact version pin with lockfile

For each downstream dependent, assess blast radius:
- Number of downstream repos found
- Whether this repo is published to a package registry (public API surface)

#### 4C: Mermaid Diagram

Output a Mermaid graph. Use subgraphs to separate upstream/downstream. Color-code by confidence.

```
graph TD
    subgraph UPSTREAM
        A[owner/dep-a] -->|depends-on HIGH| TARGET
        B[owner/dep-b] -->|uses-action HIGH| TARGET
        C[some-api] -->|calls-api MEDIUM| TARGET
    end

    TARGET[fa:fa-star owner/target-repo]

    subgraph DOWNSTREAM
        TARGET -->|depends-on HIGH| D[owner/consumer-a]
        TARGET -->|uses-action MEDIUM| E[owner/consumer-b]
    end

    style TARGET fill:#f90,color:#000
    style A fill:#e8f4fd
    style D fill:#fde8e8
```

#### 4D: Structured Report

Print the following report after the diagram:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REPO GRAPH REPORT: <owner>/<repo>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

UPSTREAM (<N> dependencies found)
──────────────────────────────────
HIGH confidence:
  → github.com/owner/repo-a     [depends-on]     via: requirements.txt
  → github.com/actions/checkout [uses-action]     via: .github/workflows/ci.yml
  → github.com/owner/repo-b     [submodule]       via: .gitmodules

MEDIUM confidence:
  → stripe API                  [calls-api]       via: src/billing.py import stripe
  → openai API                  [calls-api]       via: OPENAI_API_KEY in .env.example

LOW confidence:
  → github.com/owner/inspo-lib  [references]      via: README.md link

DOWNSTREAM (<M> dependents found)
──────────────────────────────────
  ← github.com/consumer/app-a   [depends-on]      via: GitHub dependents page
  ← github.com/consumer/app-b   [uses-action]     via: GitHub search

RISK SUMMARY
────────────���─────────────────────
⚠ HIGH:   <N> unpinned upstream deps (could break on upstream publish)
◆ MEDIUM: <N> major-pinned deps
✓ LOW:    <N> exact-pinned deps

BLAST RADIUS: <M> known downstream consumers
If this repo publishes a breaking change, these repos may be affected.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Constraints

- Max 50 GitHub API calls per run (use `gh api` with targeted queries, not brute-force)
- Never read more than 20 source files for Signal 1E — be selective
- If rate limited, pause and notify the user, then continue
- Private repos: skip any repo you cannot access, note it as `[private — skipped]`
- If a dependency cannot be resolved to a GitHub URL, record the package name only (no node in graph)
