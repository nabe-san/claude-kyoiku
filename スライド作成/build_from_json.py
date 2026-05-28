"""既存のslide_structure.jsonから新デザインでPPTXを生成"""
import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

from pathlib import Path
from datetime import datetime

# generate.py の関数をそのまま使う
from generate import create_pptx

structure = json.loads(Path("output/slide_structure.json").read_text(encoding="utf-8"))

# スライドタイプを適切に変換
for s in structure["slides"]:
    title = s.get("title", "")
    if s.get("type") == "content":
        if "ロードマップ" in title or "先行オーガナイザー" in title or "この授業で学ぶ" in title:
            s["type"] = "organizer"
        elif "最初の一歩" in title or "活動" in title or "ワーク" in title:
            s["type"] = "activity"

ts = datetime.now().strftime("%Y%m%d_%H%M")
out = Path("output") / f"{ts}_自己実現とキャリア形成_v2.pptx"
create_pptx(structure, out)
