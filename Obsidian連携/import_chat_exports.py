"""
ChatGPT / Claude.ai からエクスポートしたチャット履歴を
Obsidian Vaultの Markdown ノートに変換する。

事前準備（あなたが先にやる作業）:
  ChatGPT  : 設定 → データ管理 → 「データをエクスポート」→ メールで届いたZIPをダウンロード
  Claude.ai: 設定 → アカウント → 「データをエクスポート」→ 同様にZIPをダウンロード

使い方:
  1. ダウンロードしたZIP（そのままでOK。中のconversations.jsonでも可）を
     このファイルと同じ階層の _inbox フォルダに置く
  2. python import_chat_exports.py を実行
"""
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path

INBOX_DIR = Path(__file__).parent / "_inbox"
VAULT_LOG_DIR = Path.home() / "Desktop" / "MyObsidian" / "ログ"


def sanitize_filename(text: str, maxlen: int = 40) -> str:
    text = re.sub(r'[\\/:*?"<>|\n\r\t]', " ", text or "").strip()
    text = re.sub(r"\s+", " ", text)
    return text[:maxlen] if text else "無題"


def ts_to_date(ts) -> str:
    if ts is None:
        return "unknown-date"
    try:
        if isinstance(ts, str):
            return datetime.fromisoformat(ts.replace("Z", "+00:00")).strftime("%Y-%m-%d")
        return datetime.fromtimestamp(float(ts), tz=timezone.utc).strftime("%Y-%m-%d")
    except (ValueError, OSError, OverflowError):
        return "unknown-date"


def write_note(out_dir: Path, date_str: str, title: str, uid: str, source: str, turns: list) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_title = sanitize_filename(title)
    out_path = out_dir / f"{date_str}_{safe_title}_{uid[:8]}.md"

    lines = [
        "---",
        f"date: {date_str}",
        f"source: {source}",
        f"tags: [ログ, {source.lower()}]",
        "---",
        "",
        f"# {title or '無題'}",
        "",
    ]
    for speaker, text in turns:
        if not text.strip():
            continue
        lines.append(f"## {speaker}")
        lines.append("")
        lines.append(text)
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


# ---------- ChatGPT (conversations.json: ノードがmappingで木構造) ----------

def convert_chatgpt(conversations: list, out_dir: Path) -> int:
    count = 0
    for convo in conversations:
        mapping = convo.get("mapping", {})
        title = convo.get("title") or "無題"
        create_time = convo.get("create_time")

        # current_nodeから親をたどって会話順に並べ直す
        chain = []
        node_id = convo.get("current_node")
        seen = set()
        while node_id and node_id in mapping and node_id not in seen:
            seen.add(node_id)
            chain.append(node_id)
            node_id = mapping[node_id].get("parent")
        chain.reverse()

        turns = []
        for nid in chain:
            message = (mapping.get(nid) or {}).get("message")
            if not message:
                continue
            role = (message.get("author") or {}).get("role")
            if role not in ("user", "assistant"):
                continue
            parts = (message.get("content") or {}).get("parts") or []
            text = "\n".join(p for p in parts if isinstance(p, str))
            if not text.strip():
                continue
            speaker = "🧑 User" if role == "user" else "🤖 ChatGPT"
            turns.append((speaker, text))

        if not turns:
            continue

        uid = convo.get("id") or convo.get("conversation_id") or title
        write_note(out_dir, ts_to_date(create_time), title, uid, "ChatGPT", turns)
        count += 1
    return count


# ---------- Claude.ai (conversations.json: chat_messagesがフラットな配列) ----------

def convert_claude_ai(conversations: list, out_dir: Path) -> int:
    count = 0
    for convo in conversations:
        title = convo.get("name") or "無題"
        uid = convo.get("uuid", title)

        turns = []
        for msg in convo.get("chat_messages", []):
            sender = msg.get("sender")
            text = msg.get("text")
            if not text:
                blocks = msg.get("content") or []
                text = "\n".join(
                    b.get("text", "") for b in blocks
                    if isinstance(b, dict) and b.get("type") == "text"
                )
            if not text or not text.strip():
                continue
            speaker = "🧑 User" if sender == "human" else "🤖 Claude"
            turns.append((speaker, text))

        if not turns:
            continue

        write_note(out_dir, ts_to_date(convo.get("created_at")), title, uid, "Claude", turns)
        count += 1
    return count


def load_conversations_json(path: Path):
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as zf:
            for name in zf.namelist():
                if name.endswith("conversations.json"):
                    with zf.open(name) as f:
                        return json.load(f)
        return None
    if path.suffix.lower() == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def main():
    import sys

    if len(sys.argv) > 1:
        source_dir = Path(sys.argv[1])
    else:
        source_dir = INBOX_DIR
        if not source_dir.exists():
            source_dir.mkdir(parents=True)
            print(f"{source_dir} を作成しました。ここにエクスポートZIPを置いてから再実行してください。")
            return

    files = list(source_dir.glob("*.zip")) + list(source_dir.glob("*.json"))
    if not files:
        print(f"{source_dir} にZIP/JSONファイルが見つかりません。")
        return

    for path in files:
        data = load_conversations_json(path)
        if not data:
            print(f"スキップ（conversations.jsonが見つからない）: {path.name}")
            continue

        if isinstance(data, list) and data and "mapping" in data[0]:
            out_dir = VAULT_LOG_DIR / "ChatGPT"
            n = convert_chatgpt(data, out_dir)
            print(f"{path.name}: ChatGPTの会話 {n}件を変換 → {out_dir}")
        elif isinstance(data, list) and data and "chat_messages" in data[0]:
            out_dir = VAULT_LOG_DIR / "Claude"
            n = convert_claude_ai(data, out_dir)
            print(f"{path.name}: Claude.aiの会話 {n}件を変換 → {out_dir}")
        else:
            print(f"スキップ（未知の形式）: {path.name}")


if __name__ == "__main__":
    main()
