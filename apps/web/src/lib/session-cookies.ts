// Shared between server route handlers and client components. Keep this
// module free of next/headers and other server-only imports.
export const OWNER_COOKIE = "kf_owner_session";
export const CSRF_COOKIE = "kf_csrf";
export const CSRF_HEADER = "x-csrf-token";
export const SESSION_MAX_AGE_SECONDS = 60 * 60 * 24 * 30;
export const LEGACY_KEY_STORAGE = "kinfold_owner_key";
export const POST_LOGIN_REDIRECT_KEY = "kinfold_post_login_redirect";
