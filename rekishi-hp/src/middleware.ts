import { defineMiddleware } from 'astro:middleware';
import { BOOKS_ACCESS_PASSWORD, BOOKS_SESSION_SECRET } from 'astro:env/server';
import { BOOKS_SESSION_COOKIE, verifySessionToken, sanitizeBooksRedirect } from './lib/auth';

const PUBLIC_BOOKS_PATHS = new Set(['/books/login', '/books/login/', '/books/logout', '/books/logout/']);

export const onRequest = defineMiddleware(async (context, next) => {
  const { pathname } = context.url;
  const isBooksPath = pathname === '/books' || pathname.startsWith('/books/');

  // /books/ 配下以外は認証と無関係なので即座に通す。
  if (!isBooksPath) {
    return next();
  }

  // ログイン・ログアウトページ自体は認証チェックの対象外。
  if (PUBLIC_BOOKS_PATHS.has(pathname)) {
    return next();
  }

  // 秘密鍵・共有パスワードが未設定の場合はfail closed（誰も通さない）。
  if (!BOOKS_ACCESS_PASSWORD || !BOOKS_SESSION_SECRET) {
    return new Response('読書ノートは現在設定の都合により利用できません。', {
      status: 503,
      headers: { 'content-type': 'text/plain; charset=utf-8' },
    });
  }

  const token = context.cookies.get(BOOKS_SESSION_COOKIE)?.value;
  const authenticated = await verifySessionToken(token, BOOKS_SESSION_SECRET);

  if (authenticated) {
    return next();
  }

  const redirectTarget = sanitizeBooksRedirect(pathname + context.url.search);
  return context.redirect(`/books/login?redirect=${encodeURIComponent(redirectTarget)}`, 302);
});
