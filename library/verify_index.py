#!/usr/bin/env python3
"""書籍索引の機械検査。API・ネットワーク不使用、入力ファイルは読み取りのみ。

使い方: python verify_index.py 索引.md OCR.md
終了コード: 0=NGなし / 1=NGあり
"""
import re
import sys
from pathlib import Path

ROLES = {"思考の道具", "反転素材", "事例・証言", "論争軸", "背景知識"}
STATES = {"照合済", "要確認"}
KEY_RE = re.compile(r"`([^`]+)`@(\d+)")
SCAN_RE = re.compile(r"<!--\s*scan_page:\s*(\d+)\s*\|[^>]*-->")
COMMENT_RE = re.compile(r"<!--.*?-->", re.S)


def squash(s: str) -> str:
    return re.sub(r"\s+", "", s)


def load_pages(ocr_text: str):
    """scan_page ごとの本文（空白・コメント除去）。マーカー前の本文はページ0。"""
    parts = []
    pos = 0
    cur = 0
    for m in SCAN_RE.finditer(ocr_text):
        parts.append((cur, ocr_text[pos:m.start()]))
        cur = int(m.group(1))
        pos = m.end()
    parts.append((cur, ocr_text[pos:]))
    pages = {}
    for n, t in parts:
        pages[n] = pages.get(n, "") + squash(COMMENT_RE.sub("", t))
    return pages


def split_cards(text: str):
    cards = []
    for m in re.finditer(r"^### (P-\d{3}) (.+)$", text, re.M):
        cards.append((m.group(1), m.group(2), m.start()))
    out = []
    for i, (pid, title, start) in enumerate(cards):
        end = cards[i + 1][2] if i + 1 < len(cards) else len(text)
        body = text[start:end]
        # 次の見出し（### 章名 / ## D）以降は含めない
        first_nl = body.find("\n") + 1
        cut = re.search(r"^(## |### (?!P-))", body[first_nl:], re.M)
        if cut:
            body = body[: first_nl + cut.start()]
        out.append((pid, title, body))
    return out


def field(body: str, name: str):
    m = re.search(rf"^- {name}:\s*(.*)$", body, re.M)
    return m.group(1).strip() if m else None


def main(idx_path: str, ocr_path: str) -> int:
    idx = Path(idx_path).read_text(encoding="utf-8")
    ocr = Path(ocr_path).read_text(encoding="utf-8")
    pages = load_pages(ocr)
    whole = "".join(pages.values())
    cards = split_cards(idx)

    ng = warn = ok = 0
    problems = []

    # ID 連番・重複
    ids = [c[0] for c in cards]
    if len(ids) != len(set(ids)):
        problems.append(("NG", "-", "論点IDが重複している"))
    nums = [int(i[2:]) for i in ids]
    if nums != list(range(1, len(nums) + 1)):
        problems.append(("NG", "-", f"論点IDが連番でない: {ids}"))

    for pid, title, body in cards:
        loc = field(body, "位置")
        role = field(body, "役割")
        state = field(body, "状態")
        keys_line = field(body, "照合キー")
        if not loc:
            problems.append(("NG", pid, "位置が無い"))
        if not role:
            problems.append(("NG", pid, "役割が無い"))
        else:
            main_role = re.split(r"[（(]", role)[0].strip()
            if main_role not in ROLES:
                problems.append(("NG", pid, f"役割の語彙が不正: {role}"))
        if state not in STATES:
            problems.append(("NG", pid, f"状態の語彙が不正: {state}"))
        if "【本の内容】" not in body or "【教材研究の整理】" not in body:
            problems.append(("NG", pid, "【本の内容】/【教材研究の整理】が揃っていない"))
        if not keys_line or not KEY_RE.search(keys_line):
            problems.append(("NG", pid, "照合キーが無い"))

        # 照合キー + OCR数値
        targets = []
        for name in ("照合キー", "OCR数値"):
            line = field(body, name)
            if line:
                targets += [(name, k, int(n)) for k, n in KEY_RE.findall(line)]
        card_bad = False
        for name, key, n in targets:
            k = squash(key)
            if k in pages.get(n, ""):
                ok += 1
            elif any(k in pages.get(n + d, "") for d in (-1, 1)):
                warn += 1
                card_bad = True
                problems.append(("ズレ", pid, f"{name} `{key}` は scan {n} に無く前後ページにある"))
            elif k in whole:
                ng += 1
                card_bad = True
                problems.append(("NG", pid, f"{name} `{key}` は scan {n} に無い（別ページには存在）"))
            else:
                ng += 1
                card_bad = True
                problems.append(("NG", pid, f"{name} `{key}` がOCR全文に存在しない"))
        if state == "照合済" and card_bad:
            problems.append(("NG", pid, "状態が照合済だが照合に問題がある"))

    print(f"論点 {len(cards)} 件 / 照合 OK {ok}・ズレ {warn}・NG {ng}")
    for kind, pid, msg in problems:
        print(f"[{kind}] {pid}: {msg}")
    bad = ng or any(k == "NG" for k, _, _ in problems)
    print("結果:", "NGあり" if bad else "NGなし")
    return 1 if bad else 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2]))
