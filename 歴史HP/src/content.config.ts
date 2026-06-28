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
    relatedBooks: z.array(z.string()).default([]),
    relatedNotes: z.array(z.string()).default([]),
    materials: z.array(z.object({
      label: z.string(),
      file: z.string(),
    })).default([]),
  }),
});

const books = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/books' }),
  schema: z.object({
    title: z.string(),
    author: z.string(),
    year: z.number().optional(),
    publisher: z.string().optional(),
    summary: z.string().optional(),
    concepts: z.array(z.string()).default([]),
    relatedUnits: z.array(z.string()).default([]),
  }),
});

export const collections = { units, books };
