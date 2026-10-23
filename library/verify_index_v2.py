#!/usr/bin/env python3
"""書籍索引の機械検査 v2。verify_index.py の拡張版（元ファイルは変更していない）。

変更点:
  - ページ記号に旧形式 `<!-- page: N -->` も使う（scan_page がある場合はそちらを優先）
  - 標準出力を UTF-8 に固定（Windows での文字化け対策）

使い方: python -I -X utf8 verify_index_v2.py 索引.md OCR.md
終了コード: 0=NGなし / 1=NGあり
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # python -I でも同フォルダを読む
import verify_index as v1  # 同じフォルダの verify_index.py を再利用

SCAN_RE = v1.SCAN_RE
PAGE_RE = re.compile(r"<!--\s*page:\s*(\d+)\s*-->")


def load_pages(ocr_text: str):
    """scan_page があればそれを、無ければ旧形式の page を使う。"""
    marker = SCAN_RE if SCAN_RE.search(ocr_text) else PAGE_RE
    parts, pos, cur = [], 0, 0
    for m in marker.finditer(ocr_text):
        parts.append((cur, ocr_text[pos:m.start()]))
        cur = int(m.group(1))
        pos = m.end()
    parts.append((cur, ocr_text[pos:]))
    pages = {}
    for n, t in parts:
        pages[n] = pages.get(n, "") + v1.squash(v1.COMMENT_RE.sub("", t))
    return pages


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    v1.load_pages = load_pages  # main() はモジュール内の load_pages を参照する
    sys.exit(v1.main(sys.argv[1], sys.argv[2]))
