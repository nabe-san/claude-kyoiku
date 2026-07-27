"""
Claude Codeのセッション履歴（~/.claude/projects/以下のJSONL）を
Obsidian Vaultの Markdown ノートに変換する。

使い方:
    python import_claude_code_logs.py

再実行しても同じファイル名は上書きされるだけなので、
定期的に実行して差分を取り込む運用でOK。
"""
import json
import re
from datetime import datetime
from pathlib import Path

PROJECTS_DIR = Path.home() / ".claude" / "projects"
VAULT_LOG_DIR = Path.home() / "Desktop" / "MyObsidian" / "07_RawLogs" / "ClaudeCode"

# フォルダ名（伏字化されたパス）→ 分かりやすい表示名
PROJECT_NAME_MAP = {
    "c--projects-claude-kaihatsu": "claude開発",
    "c--projects-rekishi-hp": "歴史HP",
    "c--Users-kengo-Desktop-claude--": "claude開発(旧Desktop)",
    "c--Users-kengo-Desktop-ClaudeCode--v2": "ClaudeCode_v2",
    "c--Users-kengo-Desktop-ClaudeCode--v2--------": "ClaudeCode_v2_別環境",
    "c--Users-kengo-OneDrive--------claude--": "OneDrive_claude",
}


def extract_text(content) -> str:
    """message.content（str または content block配列）からノート化するテキストを取り出す"""
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    parts = []
    for block in content:
        if not isinstance(block, dict):
            continue
        block_type = block.get("type")
        if block_type == "text":
            parts.append(block.get("text", ""))
        elif block_type == "tool_use":
            parts.append(f"*[ツール実行: {block.get('name', 'tool')}]*")
        # thinking / tool_result はノートには含めない（内部処理・生ログのため）
    return "\n".join(p for p in parts if p.strip())


def sanitize_filename(text: str, maxlen: int = 40) -> str:
    text = re.sub(r'[\\/:*?"<>|\n\r\t]', " ", text).strip()
    text = re.sub(r"\s+", " ", text)
    return text[:maxlen] if text else "無題"


def convert_session(jsonl_path: Path, out_dir: Path) -> Path | None:
    session_id = jsonl_path.stem
    messages = []
    first_ts = None

    for line in jsonl_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue

        if obj.get("type") not in ("user", "assistant"):
            continue

        message = obj.get("message") or {}
        role = message.get("role", obj.get("type"))
        text = extract_text(message.get("content"))
        if not text.strip():
            continue

        ts = obj.get("timestamp")
        if first_ts is None:
            first_ts = ts
        messages.append((role, text, ts))

    if not messages:
        return None

    first_user_text = next((t for r, t, _ in messages if r == "user"), "無題")
    title = sanitize_filename(first_user_text.splitlines()[0])

    date_str = "unknown-date"
    if first_ts:
        try:
            date_str = datetime.fromisoformat(first_ts.replace("Z", "+00:00")).strftime("%Y-%m-%d")
        except ValueError:
            pass

    project_label = out_dir.name
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{date_str}_{title}_{session_id[:8]}.md"

    lines = [
        "---",
        f"date: {date_str}",
        f"session_id: {session_id}",
        "source: Claude Code",
        f"project: {project_label}",
        "tags: [claude-code, ログ]",
        "---",
        "",
        f"# {title}",
        "",
    ]
    for role, text, ts in messages:
        speaker = "🧑 User" if role == "user" else "🤖 Claude"
        lines.append(f"## {speaker}")
        if ts:
            lines.append(f"*{ts}*")
        lines.append("")
        lines.append(text)
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def main():
    if not PROJECTS_DIR.exists():
        print(f"プロジェクトディレクトリが見つかりません: {PROJECTS_DIR}")
        return

    total = 0
    for project_dir in sorted(PROJECTS_DIR.iterdir()):
        if not project_dir.is_dir():
            continue
        project_label = PROJECT_NAME_MAP.get(project_dir.name, project_dir.name)
        out_dir = VAULT_LOG_DIR / project_label

        for jsonl_path in sorted(project_dir.glob("*.jsonl")):
            result = convert_session(jsonl_path, out_dir)
            if result:
                total += 1
                print(f"変換: {result}")

    print(f"\n完了: {total}件のセッションをMarkdown化しました。")
    print(f"出力先: {VAULT_LOG_DIR}")


if __name__ == "__main__":
    main()
