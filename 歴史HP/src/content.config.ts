import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

const units = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/units' }),
  schema: z.object({
    title: z.string(),
    subject: z.enum(['history-general', 'japanese-history', 'civics']),
    visual: z.enum(['imperialism', 'industrial', 'insei', 'default']).default('default'),
    concepts: z.array(z.string()),
    bigQuestion: z.string(),
    subQuestion: z.string().optional(),
    overview: z.string().optional(),
    keywords: z.array(z.string()).optional(),
    answer: z.string().optional(),
    relatedBooks: z.array(z.string()),
    relatedNotes: z.array(z.string()),
    materials: z.array(z.object({
      label: z.string(),
      file: z.string(),
    })),
  }),
});

// 将来追加予定（読書ノート・思考ノート）
// const books = defineCollection({ ... });
// const notes = defineCollection({ ... });

export const collections = { units };
