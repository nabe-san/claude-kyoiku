// /books/ 配下の共有パスワード認証で使う署名・検証ロジック。
// Edge Runtimeでも動くよう、Web Crypto API (crypto.subtle) のみに依存する。

export const BOOKS_SESSION_COOKIE = 'rekishi_books_access';
export const BOOKS_SESSION_MAX_AGE = 60 * 60 * 24 * 30; // 30日（秒）
export const BOOKS_SESSION_PATH = '/books';

function toHex(buffer: ArrayBuffer): string {
  return [...new Uint8Array(buffer)].map((b) => b.toString(16).padStart(2, '0')).join('');
}

async function hmacHex(secret: string, message: string): Promise<string> {
  const key = await crypto.subtle.importKey(
    'raw',
    new TextEncoder().encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign'],
  );
  const signature = await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(message));
  return toHex(signature);
}

// 文字数の違いも含めて実行時間の差を抑えるための固定長比較。
// Node専用のcrypto.timingSafeEqualはEdge Runtimeで使えないため使用しない。
function constantTimeEqual(a: string, b: string): boolean {
  const aBytes = new TextEncoder().encode(a);
  const bBytes = new TextEncoder().encode(b);
  const len = Math.max(aBytes.length, bBytes.length, 32);
  let diff = aBytes.length ^ bBytes.length;
  for (let i = 0; i < len; i++) {
    diff |= (aBytes[i] ?? 0) ^ (bBytes[i] ?? 0);
  }
  return diff === 0;
}

/** 有効期限（UNIXミリ秒）を含む署名付きセッショントークンを発行する。 */
export async function createSessionToken(
  secret: string,
  maxAgeSeconds: number = BOOKS_SESSION_MAX_AGE,
): Promise<string> {
  const expiresAt = Date.now() + maxAgeSeconds * 1000;
  const payload = String(expiresAt);
  const signature = await hmacHex(secret, payload);
  return `${payload}.${signature}`;
}

/** セッショントークンの署名と有効期限を検証する。改ざん・期限切れはfalse。 */
export async function verifySessionToken(
  token: string | undefined | null,
  secret: string,
): Promise<boolean> {
  if (!token) return false;
  const separatorIndex = token.indexOf('.');
  if (separatorIndex <= 0) return false;

  const payload = token.slice(0, separatorIndex);
  const signature = token.slice(separatorIndex + 1);

  const expiresAt = Number(payload);
  if (!Number.isFinite(expiresAt) || Date.now() > expiresAt) return false;

  const expectedSignature = await hmacHex(secret, payload);
  return constantTimeEqual(signature, expectedSignature);
}

/** 共有パスワードの比較。固定長ダイジェスト同士を比較し、生の値は直接比較しない。 */
export async function verifySharedPassword(input: string, expected: string): Promise<boolean> {
  if (!input || !expected) return false;
  const context = 'books-password-compare';
  const [inputDigest, expectedDigest] = await Promise.all([
    hmacHex(context, input),
    hmacHex(context, expected),
  ]);
  return constantTimeEqual(inputDigest, expectedDigest);
}

/**
 * ログイン後のリダイレクト先として安全な相対パスだけを許可する。
 * 外部URLやプロトコル相対URL（//evil.example.com）へは飛ばさない。
 */
export function sanitizeBooksRedirect(raw: string | null | undefined): string {
  const fallback = '/books/';
  if (!raw) return fallback;
  if (raw.startsWith('//') || raw.includes('\\')) return fallback;
  if (!raw.startsWith('/books')) return fallback;

  try {
    const parsed = new URL(raw, 'http://localhost');
    if (parsed.pathname === '/books' || parsed.pathname.startsWith('/books/')) {
      return `${parsed.pathname}${parsed.search}`;
    }
    return fallback;
  } catch {
    return fallback;
  }
}
