// 概念タグ マスター語彙（科目別）の読み込み・集計ユーティリティ
// src/data/concepts/*.json を科目別のファイルとして扱う。
// ファイル名（拡張子除く）がそのまま科目キーになる（例: history-general.json → "history-general"）。

export interface ConceptVocabEntry {
  slug: string;
  name: string;
  category: string;
}

export const SUBJECT_ORDER = ['history-general', 'japanese-history', 'civics'] as const;
export type SubjectKey = (typeof SUBJECT_ORDER)[number];

export const SUBJECT_LABELS: Record<SubjectKey, string> = {
  'history-general': '歴史総合',
  'japanese-history': '日本史探究',
  civics: '公共',
};

const vocabFiles = import.meta.glob('/src/data/concepts/*.json', { eager: true }) as Record<
  string,
  { default: ConceptVocabEntry[] }
>;

// 科目キー → 語彙エントリ配列（ファイルが存在する科目のみキーを持つ）
export const vocabularyBySubject: Partial<Record<SubjectKey, ConceptVocabEntry[]>> = {};
for (const [path, mod] of Object.entries(vocabFiles)) {
  const key = path.split('/').pop()!.replace(/\.json$/, '') as SubjectKey;
  vocabularyBySubject[key] = mod.default;
}

// 概念名 → 科目 → カテゴリ のマップ
export function buildConceptCategoryMap(): Map<string, Map<SubjectKey, string>> {
  const map = new Map<string, Map<SubjectKey, string>>();
  for (const subject of SUBJECT_ORDER) {
    const entries = vocabularyBySubject[subject];
    if (!entries) continue;
    for (const entry of entries) {
      if (!map.has(entry.name)) map.set(entry.name, new Map());
      map.get(entry.name)!.set(subject, entry.category);
    }
  }
  return map;
}

// 科目 → カテゴリの出現順リスト（語彙ファイル内の並び順を維持する）
export function buildCategoryOrder(): Partial<Record<SubjectKey, string[]>> {
  const order: Partial<Record<SubjectKey, string[]>> = {};
  for (const subject of SUBJECT_ORDER) {
    const entries = vocabularyBySubject[subject];
    if (!entries) continue;
    const seen = new Set<string>();
    const categories: string[] = [];
    for (const entry of entries) {
      if (!seen.has(entry.category)) {
        seen.add(entry.category);
        categories.push(entry.category);
      }
    }
    order[subject] = categories;
  }
  return order;
}
