"""人物イラスト自動生成スクリプト（歴史シミュレーションv2）

OpenAI Images API (gpt-image-1) でシナリオ登場人物のイラストを生成し、
- assets/portraits/<id>.webp として保存（開発用・公開用の両方）
- 対象シナリオの scenario.json の characters.<characterKey>.photo を自動更新
    （開発用・公開用の両方。公開用にまだシナリオが無ければスキップ）

使い方:
    python generate_portraits.py portraits_todo/05_ロシア革命_レーニン.json
    python generate_portraits.py portraits_todo/05_ロシア革命_レーニン.json --dry-run
    python generate_portraits.py portraits_todo/05_ロシア革命_レーニン.json --force

キュー用JSONの形式（1シナリオにつき1ファイル。portraits_todo/ に置く）:
[
  {
    "id": "lenin",
    "prompt": "英語での見た目の説明（年代・服装・表情・背景色のヒントなど）",
    "scenario": "scenarios/05_ロシア革命_レーニン/scenario.json",
    "characterKey": "protagonist"
  }
]

注意:
- 画像生成にはOpenAI APIの課金が発生する（1枚あたり数十円程度、quality設定に依存）。
- 既に assets/portraits/<id>.webp が存在する場合はスキップする（--force で上書き）。
"""

import argparse
import base64
import io
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
PUBLIC_DIR = BASE_DIR.parent / "歴史シミュレーションv2_public"

# 既存の人物イラストと統一感を持たせるための共通スタイル指定
STYLE_PREFIX = (
    "Semi-realistic painterly digital illustration portrait, in the style of an "
    "educational history textbook illustration (NOT a photograph, NOT anime, NOT a "
    "cartoon). Muted, slightly desaturated earthy color palette. Aged parchment / "
    "beige mottled paper-texture background with soft vignette lighting. Waist-up, "
    "three-quarter view portrait, dignified and serious expression, soft directional "
    "studio lighting, fine linework with painterly shading, high detail on the face "
    "and period-accurate clothing. No text, no watermark, no signature, no frame, "
    "no border. Subject: "
)

IMAGE_SIZE = "1536x1024"  # 既存ポートレートの横長比率に合わせる
IMAGE_QUALITY = "medium"


def load_queue(queue_path: Path) -> list[dict]:
    with open(queue_path, encoding="utf-8") as f:
        items = json.load(f)
    for item in items:
        for key in ("id", "prompt", "scenario", "characterKey"):
            if key not in item:
                raise ValueError(f"キュー項目に '{key}' がありません: {item}")
    return items


def generate_image(client, prompt: str) -> bytes:
    full_prompt = STYLE_PREFIX + prompt
    resp = client.images.generate(
        model="gpt-image-1",
        prompt=full_prompt,
        size=IMAGE_SIZE,
        quality=IMAGE_QUALITY,
        n=1,
    )
    b64 = resp.data[0].b64_json
    return base64.b64decode(b64)


def save_as_webp(png_bytes: bytes, dest: Path) -> None:
    from PIL import Image

    img = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, "WEBP", quality=85)


def update_scenario_photo(scenario_path: Path, character_key: str, photo_rel_path: str) -> bool:
    if not scenario_path.exists():
        return False
    with open(scenario_path, encoding="utf-8") as f:
        data = json.load(f)
    chars = data.get("characters", {})
    if character_key not in chars:
        print(f"  警告: {scenario_path} に characters.{character_key} がありません", file=sys.stderr)
        return False
    chars[character_key]["photo"] = photo_rel_path
    with open(scenario_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("queue", help="portraits_todo/ 以下のキューJSONファイルへのパス")
    parser.add_argument("--dry-run", action="store_true", help="APIを呼ばず、送信するプロンプトだけ表示する")
    parser.add_argument("--force", action="store_true", help="既存の画像があっても再生成する")
    args = parser.parse_args()

    load_dotenv(BASE_DIR / ".env")

    queue_path = Path(args.queue)
    if not queue_path.is_absolute():
        queue_path = BASE_DIR / queue_path
    items = load_queue(queue_path)

    if args.dry_run:
        for item in items:
            print(f"[{item['id']}] -> assets/portraits/{item['id']}.webp")
            print(f"  scenario: {item['scenario']} / characterKey: {item['characterKey']}")
            print(f"  prompt: {STYLE_PREFIX}{item['prompt']}")
            print()
        print(f"(dry-run: {len(items)}件。実行にはAPI課金が発生します)")
        return

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("エラー: OPENAI_API_KEY が設定されていません（.env を確認してください）", file=sys.stderr)
        sys.exit(1)

    from openai import OpenAI

    client = OpenAI(api_key=api_key)

    for item in items:
        portrait_rel = f"assets/portraits/{item['id']}.webp"
        dev_dest = BASE_DIR / portrait_rel
        public_dest = PUBLIC_DIR / portrait_rel

        if dev_dest.exists() and not args.force:
            print(f"[{item['id']}] 既に存在するためスキップ（--force で再生成）: {dev_dest}")
        else:
            print(f"[{item['id']}] 生成中...")
            png_bytes = generate_image(client, item["prompt"])
            save_as_webp(png_bytes, dev_dest)
            save_as_webp(png_bytes, public_dest)
            print(f"  保存: {dev_dest}")
            print(f"  保存: {public_dest}")

        dev_scenario = BASE_DIR / item["scenario"]
        public_scenario = PUBLIC_DIR / item["scenario"]
        if update_scenario_photo(dev_scenario, item["characterKey"], portrait_rel):
            print(f"  更新: {dev_scenario} (characters.{item['characterKey']}.photo)")
        if update_scenario_photo(public_scenario, item["characterKey"], portrait_rel):
            print(f"  更新: {public_scenario} (characters.{item['characterKey']}.photo)")
        elif public_scenario.exists() is False:
            print(f"  情報: 公開用 {public_scenario} は未作成のためスキップ")

    print(f"\n完了: {len(items)}件処理しました。")


if __name__ == "__main__":
    main()
