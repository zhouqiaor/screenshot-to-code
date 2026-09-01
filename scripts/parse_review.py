#!/usr/bin/env python3
"""Parse OCR review.json and build a markdown PR comment.

OCR JSON schema (actual, verified from docs + CSDN examples):
{
  "status": "success",
  "summary": { "files_reviewed": N, "comments": N, "total_tokens": N, ... },
  "tool_calls": { "total": N, "by_tool": { ... } },
  "comments": [
    { "path": "...", "start_line": N, "end_line": N,
      "severity": "critical|high|medium|low",
      "category": "bug|security|performance|...|other",
      "content": "the actual review message text" }
  ]
}

Old (broken) workflow used: data.get("issues").get("file").get("message")
Correct mapping: data.get("comments").get("path").get("content")
"""

import json
import os
import sys


def main():
    if not os.path.exists("review.json"):
        print("No review.json found", file=sys.stderr)
        sys.exit(1)

    with open("review.json") as f:
        data = json.load(f)

    # GitHub Actions does NOT interpolate ${{ }} expressions in referenced script
    # files (only in inline run: blocks). Read them from environment instead.
    gh_repo = os.environ.get("GITHUB_REPOSITORY", "")
    gh_run_id = os.environ.get("GITHUB_RUN_ID", "")
    log_url = ""
    if gh_repo and gh_run_id:
        log_url = f"https://github.com/{gh_repo}/actions/runs/{gh_run_id}"

    lines = ["## OpenCodeReview Summary\n"]

    # Check for review failure first — if failed, post error and early-return
    # so we don't render an empty/meaningless summary table below.
    # OCR uses "complete" or "success" for successful reviews; anything else is a failure.
    status = data.get("status", "")
    message = data.get("message", "")
    if status and status not in ("success", "complete", ""):
        lines.append(f"**Status:** {status}\n")
        if message:
            lines.append(f"**Error:** {message}\n")
        if log_url:
            lines.append(f"\n> Review did not complete successfully. Check the [workflow logs]({log_url}) for details.\n")
        else:
            lines.append("\n> Review did not complete successfully. Check the workflow logs for details.\n")
        body = "\n".join(lines)
        with open("pr-comment.md", "w") as f:
            f.write(body)
        print(f"Generated failure comment with {len(lines)} lines")
        return

    summary = data.get("summary") or {}
    if isinstance(summary, dict):
        stats_str = ", ".join(f"{k}: {v}" for k, v in summary.items())
        lines.append(f"**Summary:** {{{stats_str}}}\n")
    elif isinstance(summary, str) and summary:
        lines.append(f"**Summary:** {summary}\n")

    # OCR uses "comments" as the key for review findings
    issues = data.get("comments") or data.get("issues") or data.get("findings") or []
    if isinstance(issues, list) and issues:
        lines.append(f"**Issues found:** {len(issues)}\n")
        lines.append("| # | Severity | Category | File | Line | Message |")
        lines.append("|---|----------|----------|------|------|---------|")
        for i, issue in enumerate(issues, 1):
            sev = issue.get("severity", issue.get("level", "info"))
            cat = issue.get("category", "")
            fname = issue.get("path", issue.get("file", "?"))
            sline = issue.get("start_line", "")
            eline = issue.get("end_line", "")
            if not eline or sline == eline:
                line_range = str(sline)
            else:
                line_range = f"{sline}-{eline}"
            # OCR uses "content" for the message text
            msg = (
                issue.get("content", "")
                or issue.get("message", "")
                or issue.get("description", "")
            )[:200]
            # Escape pipes and newlines to not break markdown table
            msg = msg.replace("|", "\\|").replace("\n", " ")
            lines.append(f"| {i} | {sev} | {cat} | {fname} | {line_range} | {msg} |")
    else:
        lines.append("**No issues found.** \u2705\n")

    tool_calls = data.get("tool_calls") or {}
    if isinstance(tool_calls, dict) and tool_calls:
        lines.append("\n### Tool Calls\n")
        lines.append(f"- **Total**: {tool_calls.get('total', 'N/A')}")
        by_tool = tool_calls.get("by_tool", {})
        if by_tool:
            lines.append("- **By tool**:")
            for tool, count in by_tool.items():
                lines.append(f"  - {tool}: {count}")

    # Fallback: dump raw JSON if nothing matched
    if not summary and not issues and not tool_calls and not status:
        raw = json.dumps(data, indent=2)[:2000]
        lines.append("### Raw Review Output\n")
        lines.append(f"```json\n{raw}\n```")

    body = "\n".join(lines)
    with open("pr-comment.md", "w") as f:
        f.write(body)
    print(f"Generated comment with {len(lines)} lines")


if __name__ == "__main__":
    main()
