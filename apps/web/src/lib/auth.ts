/** Browser-side auth state: the bearer token + the signed-in email, in
 *  localStorage. The token is the real credential; the backend verifies it. */

const TOKEN_KEY = "omnicaption.token";
const EMAIL_KEY = "omnicaption.email";

export function getToken(): string {
  if (typeof window === "undefined") return "";
  return window.localStorage.getItem(TOKEN_KEY) ?? "";
}

export function getEmail(): string {
  if (typeof window === "undefined") return "";
  return window.localStorage.getItem(EMAIL_KEY) ?? "";
}

export function setSession(email: string, token: string): void {
  window.localStorage.setItem(TOKEN_KEY, token);
  window.localStorage.setItem(EMAIL_KEY, email);
}

export function clearSession(): void {
  window.localStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(EMAIL_KEY);
}

export function isAuthed(): boolean {
  return getToken().length > 0;
}
