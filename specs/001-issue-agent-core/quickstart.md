# Quickstart: IssueAgent

## Setup

```bash
git clone <this-repo>
cd issue-agent
pip install -r requirements.txt

export ANTHROPIC_API_KEY=sk-ant-...
export GITHUB_TOKEN=ghp_...
```

## Run

```bash
python main.py https://github.com/owner/repo/issues/42
```

## What happens

1. Fetches the issue from GitHub
2. Clones the repo into a temp directory
3. Claude reads the codebase, writes a fix, runs tests
4. If tests pass → opens a draft PR and prints the URL
5. If tests fail → retries up to 3 times, then exits with explanation

## Demo repo

Use `https://github.com/julian-demo/issue-agent-test` — a small Python repo
with intentional bugs and a pytest suite, purpose-built for demoing the agent.
