#!/usr/bin/env python3
"""
歴史シミュレーション キャラクター画像生成ツール

DALL-E 3 で人物イラストを生成し、scenarios/<シナリオ>/images/ に PNG で保存する。
生成後は index.html の photo パスを自動で書き換えるか、変更箇所を表示する。

使い方:
  python generate_images.py --scenario 01_日露戦争_桂太郎
  python generate_images.py --scenario 01_日露戦争_桂太郎 --period "Meiji era Japan"
  python generate_images.py --scenario 01_日露戦争_桂太郎 --keys katsura,komura
  python generate_images.py --scenario 01_日露戦争_桂太郎 --force   # 上書き再生成
  python generate_images.py --scenario 01_日露戦争_桂太郎 --update-html  # HTML も自動更新

前提:
  - .env に OPENAI_API_KEY=sk-... を設定
  - pip install openai python-dotenv
"""

import os, re, sys, base64, argparse
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

try:
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except ImportError:
    print("エラー: openai が未インストールです。pip install openai を実行してください。")
    sys.exit(1)

BASE_DIR  = Path(__file__).parent
SCENARIOS = BASE_DIR / "scenarios"

# ================================================================
# スタイルプロンプト（全キャラクター共通）
# ================================================================
# 画風を統一するための固定指示。変更したい場合はここを編集する。
STYLE_PROMPT = (
    "Portrait illustration in a refined Japanese ukiyo-e-inspired style. "
    "Soft watercolor washes, warm amber and sepia tones, clean flat linework. "
    "Dignified expression, authentic period-appropriate formal attire. "
    "Plain off-white background. No text, no watermark, no frame."
)

# ================================================================
# キャラクター解析（index.html → CHARS リスト）
# ================================================================

def parse_chars_from_html(html_text: str) -> list[dict]:
    """CHARS オブジェクトを解析して [{key, name, role, photo}] を返す。"""
    match = re.search(r"const CHARS\s*=\s*\{(.+?)\n\};", html_text, re.DOTALL)
    if not match:
        return []
    block = match.group(1)

    chars = []
    for m in re.finditer(
        r"(\w+)\s*:\s*\{[^}]*?name\s*:\s*'([^']+)'[^}]*?role\s*:\s*'([^']+)'(?:[^}]*?photo\s*:\s*'([^']*)')?",
        block,
        re.DOTALL,
    ):
        key, name, role, photo = m.group(1), m.group(2), m.group(3), m.group(4) or ""
        # 'official' など汎用キーを除外（名前が役職名と同じケース）
        if key in ("official", "narrator", "player"):
            continue
        chars.append({"key": key, "name": name, "role": role, "photo": photo})
    return chars


# ================================================================
# DALL-E 3 画像生成
# ================================================================

def build_prompt(name: str, role: str, period: str) -> str:
    return (
        f"Portrait of {name}, {role} during the {period}. "
        f"Historical figure, East Asian appearance. "
        f"{STYLE_PROMPT}"
    )


def generate_image(name: str, role: str, period: str, output_path: Path) -> bool:
    """DALL-E 3 で1枚生成し PNG に保存。成功で True を返す。"""
    prompt = build_prompt(name, role, period)
    print(f"\n  [{name}] 生成中...")
    print(f"  role   : {role}")
    print(f"  period : {period}")

    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1024x1024",
        quality="standard",
        response_format="b64_json",
        n=1,
    )

    img_b64 = response.data[0].b64_json
    output_path.write_bytes(base64.b64decode(img_b64))
    print(f"  → 保存: {output_path.relative_to(BASE_DIR)}")
    return True


# ================================================================
# index.html の photo パスを書き換え
# ================================================================

def update_html(html_path: Path, updates: dict[str, str]):
    """updates = {key: 'images/key.png'} で photo 値を置換して上書き保存。"""
    text = html_path.read_text(encoding="utf-8")
    for key, new_photo in updates.items():
        # 対象行パターン: photo: 'xxx' （その CHARS エントリ内）
        # キー名を手がかりに、直後のブロック内の photo を置換する
        pattern = rf"({re.escape(key)}\s*:\s*\{{(?:[^}}]|(?<=')[^']*(?='))*?photo\s*:\s*')[^']*(')"
        replacement = rf"\g<1>{new_photo}\g<2>"
        new_text, n = re.subn(pattern, replacement, text, flags=re.DOTALL)
        if n:
            text = new_text
            print(f"  HTML 更新: {key}.photo → '{new_photo}'")
        else:
            print(f"  [警告] {key} の photo 行が見つからず — 手動で変更してください")
    html_path.write_text(text, encoding="utf-8")


# ================================================================
# メイン
# ================================================================

def main():
    parser = argparse.ArgumentParser(description="歴史シミュレーション キャラクター画像生成")
    parser.add_argument("--scenario", required=True,
                        help="シナリオフォルダ名（例: 01_日露戦争_桂太郎）")
    parser.add_argument("--period", default="Meiji era Japan, circa 1900",
                        help="時代（英語）。例: 'Meiji era Japan' / 'Bismarck-era Prussia'")
    parser.add_argument("--keys",
                        help="対象キャラクターキーをカンマ区切りで指定（省略時は全員）")
    parser.add_argument("--force", action="store_true",
                        help="既存画像も再生成する")
    parser.add_argument("--update-html", action="store_true",
                        help="生成後に index.html の photo パスを自動更新する")
    args = parser.parse_args()

    scenario_dir = SCENARIOS / args.scenario
    html_path = scenario_dir / "index.html"
    images_dir = scenario_dir / "images"

    if not html_path.exists():
        print(f"エラー: {html_path} が見つかりません")
        sys.exit(1)

    if not os.getenv("OPENAI_API_KEY"):
        print("エラー: OPENAI_API_KEY が設定されていません（.env を確認）")
        sys.exit(1)

    images_dir.mkdir(exist_ok=True)

    html_text = html_path.read_text(encoding="utf-8")
    chars = parse_chars_from_html(html_text)

    if not chars:
        print("エラー: index.html から CHARS を解析できませんでした。")
        print("       CHARS オブジェクトの形式を確認してください。")
        sys.exit(1)

    if args.keys:
        target_keys = {k.strip() for k in args.keys.split(",")}
        chars = [c for c in chars if c["key"] in target_keys]
        if not chars:
            print(f"エラー: 指定キー {target_keys} が CHARS に見つかりません")
            sys.exit(1)

    print("=" * 56)
    print(f"  シナリオ : {args.scenario}")
    print(f"  時代     : {args.period}")
    print(f"  対象     : {len(chars)} 人")
    print(f"  出力先   : scenarios/{args.scenario}/images/")
    print("=" * 56)

    # 1枚あたり約 $0.04（standard 品質）
    cost_est = len([c for c in chars if args.force or not (images_dir / f"{c['key']}.png").exists()]) * 0.04
    print(f"  推定コスト: ${cost_est:.2f} USD\n")

    updated = {}
    for char in chars:
        out_path = images_dir / f"{char['key']}.png"
        if out_path.exists() and not args.force:
            print(f"  [スキップ] {char['name']}（既存画像あり。再生成は --force）")
            continue
        try:
            generate_image(char["name"], char["role"], args.period, out_path)
            updated[char["key"]] = f"images/{char['key']}.png"
        except Exception as e:
            print(f"  [エラー] {char['name']}: {e}")

    print(f"\n{'=' * 56}")
    if not updated:
        print("  新規生成なし")
        return

    print(f"  生成完了: {len(updated)} 枚")

    if args.update_html:
        print("\n  index.html を自動更新中...")
        update_html(html_path, updated)
        print("  完了")
    else:
        print("\n  index.html への反映方法（--update-html で自動化可）:")
        print("  以下の photo 値を変更してください:\n")
        for key, path in updated.items():
            print(f"    {key}: {{ ..., photo: '{path}', ... }}")

    print(f"{'=' * 56}")


if __name__ == "__main__":
    main()
