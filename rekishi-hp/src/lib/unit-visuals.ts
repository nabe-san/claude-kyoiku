// 授業構成カードのサムネイル画像。src/assets/unit-visuals/[slug].{jpg,jpeg,png,webp} を
// 置くだけで自動表示される。frontmatterの編集は不要（ファイル名 = units の slug と一致させる）。
// 画像がない授業は UnitVisual.astro の手描きSVGにフォールバックする。

import type { ImageMetadata } from 'astro';

const visualFiles = import.meta.glob('/src/assets/unit-visuals/*.{jpg,jpeg,png,webp}', {
  eager: true,
}) as Record<string, { default: ImageMetadata }>;

export const unitVisualsBySlug: Record<string, ImageMetadata> = {};
for (const [path, mod] of Object.entries(visualFiles)) {
  const slug = path.split('/').pop()!.replace(/\.(jpg|jpeg|png|webp)$/, '');
  unitVisualsBySlug[slug] = mod.default;
}

// バナー枠は画像の高さの半分以下しか表示できないため、構図によっては
// 中央クロップ（デフォルト）だと主題が切れてしまう。その場合だけ個別に上下位置を調整する。
export const unitVisualFocus: Record<string, string> = {
  'teikoku-shugi': 'center 20%',
};
