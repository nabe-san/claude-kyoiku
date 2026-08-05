"""Stop hook: commit only the files record_edit.py logged during this turn.
Never touches other untracked/modified files already sitting in the working tree.
"""
import os
import subprocess

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PENDING_FILE = os.path.join(REPO_ROOT, ".claude", ".autocommit-pending.txt")
REPO_ROOT_NORM = os.path.normcase(REPO_ROOT)


def is_inside_repo(path):
    try:
        abs_norm = os.path.normcase(os.path.abspath(path))
        return os.path.commonpath([REPO_ROOT_NORM, abs_norm]) == REPO_ROOT_NORM
    except ValueError:
        return False


def main():
    if not os.path.exists(PENDING_FILE):
        return

    with open(PENDING_FILE, "r", encoding="utf-8") as fh:
        lines = [line.strip() for line in fh if line.strip()]

    # Always clear pending state so it never leaks into a later, unrelated turn.
    os.remove(PENDING_FILE)

    if not lines:
        return

    candidates = sorted(set(lines))
    files = [f for f in candidates if os.path.exists(f) and is_inside_repo(f)]
    if not files:
        return

    add = subprocess.run(
        ["git", "add", "--"] + files,
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    if add.returncode != 0:
        return

    # Nothing actually changed (e.g. gitignored path, or edit reverted to HEAD content).
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=REPO_ROOT).returncode == 0:
        return

    staged = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=REPO_ROOT, capture_output=True, text=True,
    ).stdout.split()

    summary = "、".join(staged[:5])
    if len(staged) > 5:
        summary += f" 他{len(staged) - 5}件"

    message = (
        f"auto: {summary}\n\n"
        "Claude Code の PostToolUse/Stop フックによる自動コミットです。\n\n"
        "Co-Authored-By: Claude <noreply@anthropic.com>"
    )
    subprocess.run(["git", "commit", "-m", message], cwd=REPO_ROOT)


if __name__ == "__main__":
    main()
