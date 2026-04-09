# CLI Contract

## Usage

```bash
python main.py <github-issue-url> [OPTIONS]

# Example
python main.py https://github.com/owner/repo/issues/42
```

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--max-retries` | 3 | Max fix attempts before giving up |
| `--model` | claude-sonnet-4-5 | Claude model to use |
| `--dry-run` | False | Run without opening a PR |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Claude API key |
| `GITHUB_TOKEN` | Yes | GitHub personal access token |

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | PR opened successfully |
| 1 | Agent gave up or max retries hit |
| 2 | Auth error (bad token or no repo access) |
| 3 | Invalid issue URL |

## stdout Format

Each step prints a prefixed line:
```
[READ]  src/utils.py
[WRITE] src/utils.py
[TEST]  PASS (12 passed, 0 failed)
[TEST]  FAIL — retrying (attempt 2/3)
[PR]    https://github.com/owner/repo/pull/43
[DONE]  Fix applied successfully
[FAIL]  Gave up after 3 attempts: tests kept failing on line 42
```
