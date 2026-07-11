// 教科書目次の読み込みユーティリティ。
// 正本は src/data/curriculum/*.json（history-general.json / japanese-history.json / civics.json）。
//
// 教科書によって階層の深さが異なるため、章は次の2パターンのどちらかを取る：
//   - sections だけを持つ（節を挟まない。歴史総合の各章、公共 第1部の各章）
//   - groups を持つ（節を挟む。公共 第2部の各章）
// また、章を持たず部の直下に項目が並ぶ場合（公共 第3部）は、
// standalone: true の擬似章として表現し、章見出しを表示せず部の直下に並べる。

export interface CurriculumSectionGroup {
  title: string;
  sections: string[];
}

export interface CurriculumChapter {
  number: number;
  part: number;
  title: string;
  standalone?: boolean;
  sections?: string[];
  groups?: CurriculumSectionGroup[];
}

export interface CurriculumData {
  parts: { number: number; title: string }[];
  chapters: CurriculumChapter[];
}

const curriculumFiles = import.meta.glob('/src/data/curriculum/*.json', { eager: true }) as Record<
  string,
  { default: CurriculumData }
>;

export const historyGeneralCurriculum: CurriculumData | undefined =
  curriculumFiles['/src/data/curriculum/history-general.json']?.default;

export const japaneseHistoryCurriculum: CurriculumData | undefined =
  curriculumFiles['/src/data/curriculum/japanese-history.json']?.default;

export const civicsCurriculum: CurriculumData | undefined =
  curriculumFiles['/src/data/curriculum/civics.json']?.default;
