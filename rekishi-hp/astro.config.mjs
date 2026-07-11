import { defineConfig, envField } from 'astro/config';
import vercel from '@astrojs/vercel';

export default defineConfig({
  output: 'static',
  adapter: vercel(),
  env: {
    schema: {
      // /books/ 共有パスワード認証用。値は.envまたはVercelの環境変数で設定する（.envはGit管理外）。
      BOOKS_ACCESS_PASSWORD: envField.string({ context: 'server', access: 'secret', optional: true }),
      BOOKS_SESSION_SECRET: envField.string({ context: 'server', access: 'secret', optional: true }),
    },
  },
});
