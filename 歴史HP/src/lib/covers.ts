// 読書ノートの書影。src/assets/covers/[slug].{jpg,jpeg,png,webp} を置くだけで自動表示される。
// frontmatterの編集は不要（ファイル名 = books の slug と一致させる）。

import type { ImageMetadata } from 'astro';

const coverFiles = import.meta.glob('/src/assets/covers/*.{jpg,jpeg,png,webp}', {
  eager: true,
}) as Record<string, { default: ImageMetadata }>;

export const coversBySlug: Record<string, ImageMetadata> = {};
for (const [path, mod] of Object.entries(coverFiles)) {
  const slug = path.split('/').pop()!.replace(/\.(jpg|jpeg|png|webp)$/, '');
  coversBySlug[slug] = mod.default;
}
