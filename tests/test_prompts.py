"""Tests for prompt template generation."""

from issue_agent.prompts import build_fix_prompt, build_graph_prompt


def test_fix_prompt_contains_issue_url():
    url = "https://github.com/owner/repo/issues/42"
    prompt = build_fix_prompt(url)
    assert url in prompt
    assert "gh issue view" in prompt
    assert "gh pr create" in prompt


def test_fix_prompt_has_quality_rules():
    prompt = build_fix_prompt("https://github.com/owner/repo/issues/1")
    assert "NEVER open a PR with failing tests" in prompt
    assert "NEVER modify more than 10 files" in prompt


def test_fix_prompt_handles_features_and_bugs():
    prompt = build_fix_prompt("https://github.com/owner/repo/issues/1")
    assert "bug" in prompt.lower()
    assert "feature" in prompt.lower()
    assert "Classify the Issue" in prompt


def test_graph_prompt_contains_repo_url():
    url = "https://github.com/owner/repo"
    prompt = build_graph_prompt(url)
    assert url in prompt
    assert "gh repo view" in prompt
    assert "Mermaid" in prompt


def test_graph_prompt_depth():
    prompt = build_graph_prompt("https://github.com/owner/repo", depth=2)
    assert "Scan depth: 2" in prompt


def test_graph_prompt_no_downstream():
    prompt = build_graph_prompt("https://github.com/owner/repo", no_downstream=True)
    assert "SKIP downstream detection" in prompt


def test_graph_prompt_default_includes_downstream():
    prompt = build_graph_prompt("https://github.com/owner/repo")
    assert "SKIP downstream detection" not in prompt
