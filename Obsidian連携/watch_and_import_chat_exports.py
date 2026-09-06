"""
Downloadsフォルダを監視し、ChatGPT/Claude.aiのエクスポートZIPを自動検出して
import_chat_exports.py の変換ロジックでVaultに取り込む。

_inbox フォルダへの手動移動が不要になる（エクスポート申請→メールでZIPダウンロード、
だけが手動作業として残る）。ファイル名ではなく中身（conversations.jsonの有無）で
判定するので、Downloadsにある無関係なZIPはそのまま無視される。

処理済みZIPは _inbox/_archive に移動し、次回以降スキャン対象から外れる。

Task Schedulerから定期実行する想定（例: 週次）。新しいエクスポートZIPが無ければ
何もしない。
"""
import shutil
from datetime import datetime
from pathlib import Path

from import_chat_exports import (
    VAULT_LOG_DIR,
    convert_chatgpt,
    convert_claude_ai,
    load_conversations_json,
)

DOWNLOADS_DIR = Path.home() / "Downloads"
ARCHIVE_DIR = Path(__file__).parent / "_inbox" / "_archive"


def main():
    if not DOWNLOADS_DIR.exists():
        print(f"{DOWNLOADS_DIR} が見つかりません。")
        return

    zips = sorted(DOWNLOADS_DIR.glob("*.zip"))
    if not zips:
        print("Downloadsにzipファイルがありません。")
        return

    found = 0
    for path in zips:
        try:
            data = load_conversations_json(path)
        except Exception as e:
            print(f"読み込み失敗（スキップ）: {path.name} ({e})")
            continue

        if not data:
            continue

        if isinstance(data, list) and data and "mapping" in data[0]:
            out_dir = VAULT_LOG_DIR / "ChatGPT"
            written, skipped = convert_chatgpt(data, out_dir)
            print(f"{path.name}: ChatGPTの会話 {written}件を変換（{skipped}件は既存のためスキップ） → {out_dir}")
        elif isinstance(data, list) and data and "chat_messages" in data[0]:
            out_dir = VAULT_LOG_DIR / "Claude"
            written, skipped = convert_claude_ai(data, out_dir)
            print(f"{path.name}: Claude.aiの会話 {written}件を変換（{skipped}件は既存のためスキップ） → {out_dir}")
        else:
            continue  # conversations.jsonはあったが未知の形式。手動確認に委ねてDownloadsに残す

        found += 1
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        dest = ARCHIVE_DIR / path.name
        if dest.exists():
            dest = ARCHIVE_DIR / f"{path.stem}_{datetime.now():%Y%m%d%H%M%S}{path.suffix}"
        shutil.move(str(path), str(dest))
        print(f"  → 処理済みZIPを移動: {dest}")

    if found == 0:
        print("該当するエクスポートZIPは見つかりませんでした。")


if __name__ == "__main__":
    main()
