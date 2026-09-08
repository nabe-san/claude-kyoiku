"""人物イラスト・ヒーロー画像 自動生成スクリプト（歴史シミュレーションv2）

OpenAI Images API (gpt-image-1) でシナリオの人物イラスト／扉絵（ヒーロー画像）を生成し、
- 人物イラスト: assets/portraits/<id>.webp として保存
    → 対象シナリオの scenario.json の characters.<characterKey>.photo を自動更新
- ヒーロー画像: assets/scenes/<id>.webp として保存
    → 対象シナリオの scenario.json の meta.heroImage を自動更新
    → トップ画面 scenarios.json の該当カード（id一致）の image を自動更新
（いずれも開発用・公開用の両方に反映。公開用にまだファイルが無ければスキップ）

新しいシナリオを作るたびに、このスクリプトを1回実行すれば
人物イラストとヒーロー画像の両方がまとめて作られる。

使い方:
    python generate_portraits.py portraits_todo/05_ロシア革命_レーニン.json
    python generate_portraits.py portraits_todo/05_ロシア革命_レーニン.json --dry-run
    python generate_portraits.py portraits_todo/05_ロシア革命_レーニン.json --force

キュー用JSONの形式（1シナリオにつき1ファイル。portraits_todo/ に置く）:
[
  {
    "id": "lenin",
    "type": "portrait",
    "prompt": "英語での見た目の説明（年代・服装・表情・背景色のヒントなど）",
    "scenario": "scenarios/05_ロシア革命_レーニン/scenario.json",
    "characterKey": "protagonist"
  },
  {
    "id": "lenin-finland-station-hero",
    "type": "hero",
    "prompt": "英語での場面の説明（登場人物・状況・構図・雰囲気など）",
    "scenario": "scenarios/05_ロシア革命_レーニン/scenario.json",
    "scenarioListId": "05_lenin_russian_revolution"
  }
]

"type" を省略すると "portrait" 扱いになる（既存キューファイルとの互換性のため）。

注意:
- 画像生成にはOpenAI APIの課金が発生する（1枚あたり数十円程度、quality設定に依存）。
- 既に画像ファイルが存在する場合はスキップする（--force で上書き）。
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
PORTRAIT_STYLE_PREFIX = (
    "Semi-realistic painterly digital illustration portrait, in the style of an "
    "educational history textbook illustration (NOT a photograph, NOT anime, NOT a "
    "cartoon). Muted, slightly desaturated earthy color palette. Aged parchment / "
    "beige mottled paper-texture background with soft vignette lighting. Waist-up, "
    "three-quarter view portrait, dignified and serious expression, soft directional "
    "studio lighting, fine linework with painterly shading, high detail on the face "
    "and period-accurate clothing. No text, no watermark, no signature, no frame, "
    "no border. Subject: "
)

# 既存のヒーロー画像（扉絵）と統一感を持たせるための共通スタイル指定
HERO_STYLE_PREFIX = (
    "Semi-realistic painterly digital illustration, in the style of an educational "
    "history textbook illustration (NOT a photograph, NOT anime, NOT a cartoon). Wide "
    "cinematic composition depicting a full narrative scene with figures and "
    "environment, muted slightly desaturated earthy color palette, dramatic and "
    "atmospheric lighting suited to the scene, painterly brushwork with fine detail, "
    "historically accurate clothing and setting. No text, no watermark, no signature, "
    "no frame, no border, no modern anachronistic elements. Scene: "
)

IMAGE_SIZE = "1536x1024"  # 既存の人物イラスト・ヒーロー画像の横長比率に合わせる
IMAGE_QUALITY = "medium"

REQUIRED_KEYS = {
    "portrait": ("id", "prompt", "scenario", "characterKey"),
    "hero": ("id", "prompt", "scenario", "scenarioListId"),
}


def load_queue(queue_path: Path) -> list[dict]:
    with open(queue_path, encoding="utf-8") as f:
        items = json.load(f)
    for item in items:
        item_type = item.get("type", "portrait")
        for key in REQUIRED_KEYS[item_type]:
            if key not in item:
                raise ValueError(f"キュー項目（type={item_type}）に '{key}' がありません: {item}")
    return items


def generate_image(client, style_prefix: str, prompt: str) -> bytes:
    full_prompt = style_prefix + prompt
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


def update_scenario_field(scenario_path: Path, updater) -> bool:
    """scenario.json を読み込み、updater(data) を適用して保存する。存在しなければ False。"""
    if not scenario_path.exists():
        return False
    with open(scenario_path, encoding="utf-8") as f:
        data = json.load(f)
    if not updater(data):
        return False
    with open(scenario_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return True


def update_scenario_photo(scenario_path: Path, character_key: str, photo_rel_path: str) -> bool:
    def updater(data):
        chars = data.get("characters", {})
        if character_key not in chars:
            print(f"  警告: {scenario_path} に characters.{character_key} がありません", file=sys.stderr)
            return False
        chars[character_key]["photo"] = photo_rel_path
        return True

    return update_scenario_field(scenario_path, updater)


def update_scenario_hero_image(scenario_path: Path, hero_rel_path: str) -> bool:
    def updater(data):
        data.setdefault("meta", {})["heroImage"] = hero_rel_path
        return True

    return update_scenario_field(scenario_path, updater)


def update_scenarios_list_image(scenarios_json_path: Path, list_id: str, image_rel_path: str) -> bool:
    if not scenarios_json_path.exists():
        return False
    with open(scenarios_json_path, encoding="utf-8") as f:
        data = json.load(f)
    entries = data.get("scenarios", [])
    target = next((e for e in entries if e.get("id") == list_id), None)
    if target is None:
        print(f"  警告: {scenarios_json_path} に id={list_id} のカードがありません", file=sys.stderr)
        return False
    target["image"] = image_rel_path
    with open(scenarios_json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return True


def process_portrait(client, item, force):
    portrait_rel = f"assets/portraits/{item['id']}.webp"
    dev_dest = BASE_DIR / portrait_rel
    public_dest = PUBLIC_DIR / portrait_rel

    if dev_dest.exists() and not force:
        print(f"[{item['id']}] 既に存在するためスキップ（--force で再生成）: {dev_dest}")
    else:
        print(f"[{item['id']}] 人物イラスト生成中...")
        png_bytes = generate_image(client, PORTRAIT_STYLE_PREFIX, item["prompt"])
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
    elif not public_scenario.exists():
        print(f"  情報: 公開用 {public_scenario} は未作成のためスキップ")


def process_hero(client, item, force):
    hero_rel = f"assets/scenes/{item['id']}.webp"
    dev_dest = BASE_DIR / hero_rel
    public_dest = PUBLIC_DIR / hero_rel

    if dev_dest.exists() and not force:
        print(f"[{item['id']}] 既に存在するためスキップ（--force で再生成）: {dev_dest}")
    else:
        print(f"[{item['id']}] ヒーロー画像生成中...")
        png_bytes = generate_image(client, HERO_STYLE_PREFIX, item["prompt"])
        save_as_webp(png_bytes, dev_dest)
        save_as_webp(png_bytes, public_dest)
        print(f"  保存: {dev_dest}")
        print(f"  保存: {public_dest}")

    dev_scenario = BASE_DIR / item["scenario"]
    public_scenario = PUBLIC_DIR / item["scenario"]
    if update_scenario_hero_image(dev_scenario, hero_rel):
        print(f"  更新: {dev_scenario} (meta.heroImage)")
    if update_scenario_hero_image(public_scenario, hero_rel):
        print(f"  更新: {public_scenario} (meta.heroImage)")
    elif not public_scenario.exists():
        print(f"  情報: 公開用 {public_scenario} は未作成のためスキップ")

    dev_list = BASE_DIR / "scenarios.json"
    public_list = PUBLIC_DIR / "scenarios.json"
    if update_scenarios_list_image(dev_list, item["scenarioListId"], hero_rel):
        print(f"  更新: {dev_list} (id={item['scenarioListId']} の image)")
    if update_scenarios_list_image(public_list, item["scenarioListId"], hero_rel):
        print(f"  更新: {public_list} (id={item['scenarioListId']} の image)")


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
            item_type = item.get("type", "portrait")
            style_prefix = HERO_STYLE_PREFIX if item_type == "hero" else PORTRAIT_STYLE_PREFIX
            asset_dir = "scenes" if item_type == "hero" else "portraits"
            print(f"[{item['id']}] ({item_type}) -> assets/{asset_dir}/{item['id']}.webp")
            print(f"  scenario: {item['scenario']}")
            if item_type == "hero":
                print(f"  scenarioListId: {item['scenarioListId']}")
            else:
                print(f"  characterKey: {item['characterKey']}")
            print(f"  prompt: {style_prefix}{item['prompt']}")
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
        item_type = item.get("type", "portrait")
        if item_type == "hero":
            process_hero(client, item, args.force)
        else:
            process_portrait(client, item, args.force)

    print(f"\n完了: {len(items)}件処理しました。")


if __name__ == "__main__":
    main()
