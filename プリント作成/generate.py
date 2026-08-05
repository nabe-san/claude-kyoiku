"""
プリント作成ツール（2フェーズ方式）

Phase 1: 教科書画像 → Claude で構造化テキストに分析 → キャッシュ保存
         （教科書/分析キャッシュ/ を テスト問題作成 と共有する）
Phase 2: 分析テキスト → Claude で「授業プリントの構造」をJSONで生成
Phase 3: JSON → build_docx.py で 学生用・模範解答 の2つのWordを固定テンプレで生成
         （デザインだけ調整したい場合は Phase 3 だけを再実行できる： python build_docx.py <フォルダ名>）
"""

import argparse
import base64
import io
import json
import os
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from build_docx import build_both, is_done as _docx_is_done, sprint

load_dotenv()

BASE_DIR = Path(__file__).parent
INPUT_DIR = BASE_DIR.parent / "教科書"
OUTPUT_DIR = BASE_DIR / "output"
CACHE_DIR = BASE_DIR.parent / "教科書" / "分析キャッシュ"

MODEL = "claude-sonnet-4-6"
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
MAX_IMAGE_PX = 1568  # API制限（2000px）より小さい安全値


# ================================================================
# Phase 1: 教科書画像 → 構造化テキスト分析（テスト問題作成と同じキャッシュを共有）
# ================================================================

ANALYSIS_PROMPT = """\
あなたは高校の歴史教科書の内容を分析するアシスタントです。
提示された教科書の画像を詳細に読み取り、以下の項目を構造化してまとめてください。
授業プリントを作成する際の根拠テキストとして使用するため、正確さを最優先にしてください。

## 出力項目

### 1. 主要概念・用語
重要語句とその意味・説明を箇条書きで列挙する。

### 2. 歴史的事実（年号・人物・出来事）
「西暦年：出来事（関係人物）」の形式で時系列に列挙する。

### 3. 因果関係
「原因 → 結果」の形式で整理する。

### 4. 歴史的意義・影響
各出来事が歴史の流れの中で持つ意味・影響を記述する。

### 5. グラフ・表・資料の内容
グラフや表がある場合は以下を記述する：
- 資料名（例：資料1「輸出品の割合」）
- 軸・凡例の説明
- 読み取れる数値・傾向（例：1885年の生糸の割合は約XX%）
- グラフから導ける歴史的結論

### 6. 地図・図版・風刺画
地図や図版がある場合は内容と歴史的文脈を記述する。

### 7. 一次史料・文字資料（枠囲み資料）【最重要】
教科書には四角で囲まれた番号タイトル付きの文字資料が掲載されている。
例：「6 キャラコ禁止法」「9 児童労働法（フランス、1841年）」「20 ガンジーがみた植民地支配下のインド」
これらを全て以下の形式で完全に転記する：

資料番号タイトル：【資料XX「〇〇」】
出典・注記：（括弧内の情報があれば）
本文：（枠内の文章を一字一句そのまま転記する）

※ 枠内の本文は省略せず、読み取れる限り完全に転記すること。
※ 読み取り不可の箇所は「（読み取り不可）」と明記する。

### 8. 教科書の「問い」
教科書本文中に掲載されている問いかけ（「問い」「考えよう」「まとめ」等のラベルがついた問題）を全て抽出する。
各問いの本文を完全に転記し、どのテーマ・節に対応するかを明記する。

## 注意事項
- 画像から読み取れない箇所は「（読み取り不可）」と明記する
- 数値が不鮮明・不確かな場合は推測せず「（数値不明）」と記す
- 教科書に書かれていない事実を補足・追加しない
- 一次史料（7番）は最も重要な出力項目である。枠囲み資料が1つでも見えたら必ず転記すること
"""


def load_images_from_folder(folder: Path) -> list[dict]:
    """フォルダ内の画像をリサイズして base64 エンコードして返す"""
    from PIL import Image

    blocks = []
    for p in sorted(folder.iterdir()):
        if p.suffix.lower() in IMAGE_EXTS:
            img = Image.open(p).convert("RGB")
            w, h = img.size
            if max(w, h) > MAX_IMAGE_PX:
                scale = MAX_IMAGE_PX / max(w, h)
                img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=75)
            data = base64.standard_b64encode(buf.getvalue()).decode()
            blocks.append({"type": "image",
                            "source": {"type": "base64", "media_type": "image/jpeg", "data": data}})
            sprint(f"    画像読み込み: {unicodedata.normalize('NFC', p.name)} ({img.size[0]}x{img.size[1]})")
    return blocks


def run_analysis(image_blocks: list[dict]) -> str:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    content = list(image_blocks) + [{"type": "text", "text": ANALYSIS_PROMPT}]
    response = client.messages.create(
        model=MODEL,
        max_tokens=8192,
        messages=[{"role": "user", "content": content}],
    )
    return response.content[0].text


def get_or_create_analysis(folder: Path) -> str:
    """
    キャッシュ（教科書/分析キャッシュ/<フォルダ名>.json）があれば読み込む。
    テスト問題作成・授業自動生成と同じ場所・同じ形式を使うため、
    どちらかで既に分析済みの単元は API を呼ばずに再利用できる。
    """
    folder_name = unicodedata.normalize("NFC", folder.name)
    cache_file = CACHE_DIR / f"{folder_name}.json"

    if cache_file.exists():
        sprint(f"  [キャッシュ使用] {folder_name}.json")
        data = json.loads(cache_file.read_text(encoding="utf-8"))
        return data["content"]

    sprint(f"  [Phase 1] {folder_name} を分析中...")
    image_blocks = load_images_from_folder(folder)
    if not image_blocks:
        sprint(f"  [警告] 画像が見つかりません: {folder}")
        return ""

    analysis = run_analysis(image_blocks)

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_data = {
        "folder": folder_name,
        "analyzed_at": datetime.now().isoformat(),
        "image_count": len(image_blocks),
        "content": analysis,
    }
    cache_file.write_text(json.dumps(cache_data, ensure_ascii=False, indent=2), encoding="utf-8")
    sprint(f"  [Phase 1 完了] キャッシュ保存 → {cache_file.name}")
    return analysis


# ================================================================
# Phase 2: プリント構造（JSON）を生成
# ================================================================

JSON_SCHEMA_EXAMPLE = """\
{
  "title": "（第N回　単元タイトル）",
  "big_question": "（単元を貫く大きな問い）",
  "page_range": "（教科書のページ範囲。例: pp.86-89。分からなければnull）",
  "overview_questions": ["（観点1）", "（観点2）", "（観点3）"],
  "sections": [
    {
      "roman": "I",
      "heading": "（セクション見出し）",
      "subtitle": "（例: テーマ① / テーマ①に取り組む / テーマ①②の合流点 / テーマ②の帰結）",
      "items": [
        {"type": "glossary", "label": "▼ キーワード整理", "terms": [
          {"term": "（用語）", "definition": "（説明）"}
        ]},
        {"type": "question", "number": 1, "text": "（教科書の問いをもとにした設問文）", "hint": null, "reference": null, "answer": "（模範解答）", "point": "（一言ポイント。不要ならnull）"},
        {"type": "supplementary", "label": "補助資料　図②「〇〇」の内容", "body": "（資料の内容を要約・転記）"},
        {"type": "question", "number": 2, "text": "（設問文）", "hint": "（難しい問いのみ。易・中程度はnull）", "reference": "図①", "answer": "（模範解答）", "point": null},
        {"type": "comparison_question", "number": 3, "text": "（比較を求める設問文）", "hint": null, "columns": ["（列1見出し）", "（列2見出し）"], "answers": ["（列1模範解答）", "（列2模範解答）"], "point": null}
      ]
    },
    {
      "roman": "IV",
      "heading": "まとめ",
      "subtitle": "（例: テーマ①②③）",
      "items": [
        {"type": "summary", "central_question": "（大きな問いの再掲）", "vocabulary": ["語句1", "語句2", "語句3"], "answer": "（指定語句をすべて使った模範解答）", "point": "（一言ポイント）"}
      ]
    }
  ]
}
"""


def build_print_prompt(analysis: str, subject: str, folder_name: str) -> str:
    return f"""\
あなたは高校{subject}教員のアシスタントです。
以下の【教科書分析テキスト】だけを根拠に、生徒が資料をもとに考えながら取り組む
「授業プリント」の構造をJSONで設計してください。

## タイトルの形式（重要）
- この単元のフォルダ名は「{folder_name}」。title は必ず「第N回　（教科書本文に基づく単元名）」の形式にする
  （「回」を使う。「節」「章」などに変えない。前後を（）「」などの記号で囲まない）
- big_question はプリント冒頭に大きく掲げる、単元全体を貫く問い1文のみ（前後を記号で囲まない）

## 問いの設計原則（最重要）
- 教科書に掲載されている問い（分析テキストの8番）を中心に組み立てる。教科書の問いは無駄なものがないので、
  できる限りそのまま使う。教科書にない問いは原則として加えない
- 問いは「答えることで歴史の解像度が上がる」流れになるよう配列する（「〜は誰か」ではなく
  「なぜ〜か」「〜の結果どうなったか」「〜の意義は何か」を問う）
- 一問一答的な単純暗記の設問は作らない
- reference（資料参照の補足）は、教科書の問いの文中にすでに資料番号が含まれている場合は null にする。
  資料番号が文中にない問いにのみ、参照先を reference に入れる

## プリントの構成原則
- 単元全体を貫く「大きな問い」（big_question）を1つ設定し、プリント冒頭に明示する
- 大きな問いを2〜3個の観点（overview_questions）に分解し、各観点をそれぞれ1つ以上のセクションで扱う
- 各セクションが「導入→展開→合流→帰結→まとめ」の論理的な流れでつながるよう配列する。
  subtitle にはそのセクションがどの観点（テーマ①など）を扱うかを明示する
  （例: "テーマ①"、"テーマ①に取り組む"、"テーマ①②の合流点"、"テーマ②の帰結"）
- セクション数（まとめを含む）は4〜6程度を目安にする。関連する問いはまとめて1セクションにし、
  細かく分割しすぎない
- 各史料・重要語句の近くに glossary（用語解説）を適宜配置する。セクション冒頭にまとめて置く場合は
  label を "▼ キーワード整理" にし、単発の場合は label を null にする
- 一次史料・枠囲み資料（分析テキストの7番）を使う設問には、資料の内容を supplementary として
  その設問の直前に配置し、生徒が資料を読んでから答える構成にする
- 2つの対象を比較させる設問は comparison_question にし、columns に列見出しを入れる
- 最後のセクションは必ず heading を "まとめ" にし、items は summary 1件のみとする。
  summary の vocabulary は本文中の重要語句から3〜5個選び、answer はそれをすべて使った記述解答にする

## ヒントの設計原則
- 難しい問い（背景知識・論理の補助が必要、または問いの意図が分かりにくい）にのみ hint を付ける
- 易しい問い（史料に答えが直接書いてある）・中程度の問い（複数史料を結びつける）は hint を null にする
- hint の文体は「〜に注目しよう」のように一言で、なるべく自力で考えさせる

## 出力ルール
- 分析テキストに書かれていない事実・年号・人名を使わない
- number は文書全体の通し番号（question と comparison_question 共通、セクションをまたいでも連番を続ける）
- answer は1〜3文程度。point は模範解答の要点を一言でまとめた短文（無理につけなくてよい場合はnull）
- セクションの roman は "I", "II", "III"... の通し番号

## 教科書分析テキスト（この内容だけを根拠にすること）
{analysis}

---

## 出力形式（このJSONのみを出力する。前後の説明文は不要）

{JSON_SCHEMA_EXAMPLE}
"""


def _clean_title(title: str) -> str:
    """Claudeが前後に括弧・鉤括弧を付けてしまった場合に取り除く"""
    title = title.strip()
    for left, right in (("（", "）"), ("(", ")"), ("「", "」"), ("『", "』")):
        if title.startswith(left) and title.endswith(right):
            title = title[len(left):-len(right)].strip()
    return title


def call_claude_for_structure(analysis: str, subject: str, folder_name: str) -> dict:
    """
    JSON構造はキーワード整理・補助資料・比較設問・まとめなど項目数が多く、
    テスト問題作成の max_tokens=8192 では切り詰められる可能性があるため大きめに確保する。
    （教科書/分析キャッシュの過去のトークン切り詰めバグと同種の問題を避けるため）
    """
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    prompt = build_print_prompt(analysis, subject, folder_name)
    response = client.messages.create(
        model=MODEL,
        max_tokens=16000,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError(f"JSONが見つかりません:\n{raw[:300]}")
    structure = json.loads(match.group())
    structure.setdefault("subject", subject)
    structure["title"] = _clean_title(structure.get("title", folder_name))
    return structure


# ================================================================
# フォルダ処理
# ================================================================

def is_done(out_dir: Path) -> bool:
    return _docx_is_done(out_dir)


def process_folder(folder: Path, subject: str, force: bool = False):
    folder_name = unicodedata.normalize("NFC", folder.name)
    out_dir = OUTPUT_DIR / folder_name

    if not force and is_done(out_dir):
        sprint(f"\n[スキップ] {folder_name}  （出力済み。再生成するには --force を付けて実行）")
        return

    sprint(f"\n{'=' * 60}")
    sprint(f"  [{folder_name}] 処理開始")
    sprint(f"{'=' * 60}")

    sprint("\n[Phase 1] 教科書分析（教科書/分析キャッシュ を共有）")
    analysis = get_or_create_analysis(folder)
    if not analysis:
        sprint("  [スキップ] 分析テキストを取得できませんでした。")
        return

    sprint("\n[Phase 2] プリント構造（JSON）を生成中...")
    try:
        structure = call_claude_for_structure(analysis, subject, folder_name)
    except Exception as e:
        sprint(f"  [エラー] 構造生成失敗: {e}")
        return

    out_dir.mkdir(parents=True, exist_ok=True)
    structure_path = out_dir / "structure.json"
    structure_path.write_text(json.dumps(structure, ensure_ascii=False, indent=2), encoding="utf-8")
    sprint("  → structure.json 保存")

    sprint("\n[Phase 3] Word生成中...")
    build_both(structure, out_dir)

    sprint(f"\n完了！ → output/{folder_name}/")


# ================================================================
# メイン
# ================================================================

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="教科書画像から授業プリント（生徒用＋模範解答）を生成します。")
    parser.add_argument("folder", nargs="?", default=None,
                         help="対象フォルダ名（例: 第6回_変容する東アジア）。省略時は未処理フォルダを一括生成する。")
    parser.add_argument("--subject", default=None,
                         help="科目名（歴史総合 / 公共）。folder指定時にどちらのフォルダか特定するためにも使う。")
    parser.add_argument("--force", action="store_true", help="出力済みフォルダも再生成する。")
    return parser.parse_args()


def find_target_folders(folder_name: str | None, subject: str | None) -> tuple[list[Path], str]:
    """
    (対象フォルダのリスト, 科目名) を返す。
    folder_name 指定時は 歴史総合/公共 の両方から探して1件だけ返す。
    """
    subjects = [subject] if subject else ["歴史総合", "公共"]

    if folder_name:
        for subj in subjects:
            candidate = INPUT_DIR / subj / folder_name
            if candidate.exists():
                return [candidate], subj
        searched = ", ".join(str(INPUT_DIR / s / folder_name) for s in subjects)
        sprint(f"\n[エラー] フォルダが見つかりません: {folder_name}")
        sprint(f"  探索先: {searched}")
        return [], subjects[0]

    folders: list[Path] = []
    for subj in subjects:
        subj_dir = INPUT_DIR / subj
        if subj_dir.exists():
            folders += [d for d in sorted(subj_dir.iterdir()) if d.is_dir()]
    return folders, (subject or "歴史総合")


def main():
    sprint("=" * 60)
    sprint("  プリント作成ツール")
    sprint("  生徒作業用プリント + 模範解答（固定テンプレ・2フェーズ方式）")
    sprint("=" * 60)

    if not os.getenv("ANTHROPIC_API_KEY"):
        sprint("\n[エラー] ANTHROPIC_API_KEY が設定されていません。")
        sprint("  .env ファイルに ANTHROPIC_API_KEY=sk-ant-... を記入してください。")
        sys.exit(1)

    args = parse_args()
    folder_dirs, subject_for_prompt = find_target_folders(args.folder, args.subject)

    if not folder_dirs:
        if not args.folder:
            sprint(f"\n[注意] {INPUT_DIR} 配下に授業回フォルダがありません。")
            sprint("  例: 教科書/歴史総合/第6回_変容する東アジア/ に教科書画像を入れてください。")
        return

    sprint(f"\n{len(folder_dirs)} 件のフォルダを検出:")
    for d in folder_dirs:
        out_dir = OUTPUT_DIR / unicodedata.normalize("NFC", d.name)
        status = "✓ 出力済み" if is_done(out_dir) else "→ 未処理"
        sprint(f"  {status}  {d.name}/")

    if args.force:
        sprint("\n[--force] 出力済みフォルダも再生成します")

    for folder_dir in folder_dirs:
        process_folder(folder_dir, subject=subject_for_prompt, force=args.force)

    sprint("\n全処理完了！")


if __name__ == "__main__":
    main()
