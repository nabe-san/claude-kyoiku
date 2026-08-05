"""PostToolUse hook (Edit|Write|NotebookEdit): record the touched file path
so the Stop hook (auto_commit.py) can stage exactly these files and nothing else.
"""
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PENDING_FILE = os.path.join(REPO_ROOT, ".claude", ".autocommit-pending.txt")


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return

    tool_input = data.get("tool_input") or {}
    tool_response = data.get("tool_response") or {}
    file_path = (
        tool_input.get("file_path")
        or tool_input.get("notebook_path")
        or tool_response.get("filePath")
    )
    if not file_path:
        return

    with open(PENDING_FILE, "a", encoding="utf-8") as fh:
        fh.write(file_path + "\n")


if __name__ == "__main__":
    main()
