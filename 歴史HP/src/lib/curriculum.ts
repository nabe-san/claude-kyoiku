// 教科書目次（歴史総合）の読み込みユーティリティ。
// 正本は src/data/curriculum/history-general.json。

export interface CurriculumChapter {
  number: number;
  part: number;
  title: string;
  sections: string[];
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
