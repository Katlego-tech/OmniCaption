/** Browser-only settings store (localStorage) — option (a) from docs/18:
 *  zero backend persistence; the key never leaves the user's browser except
 *  toward the backend they configured. */

const API_URL_KEY = "omnicaption.apiUrl";
const FIREWORKS_KEY = "omnicaption.fireworksKey";

export const DEFAULT_API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function getApiUrl(): string {
  if (typeof window === "undefined") return DEFAULT_API_URL;
  return window.localStorage.getItem(API_URL_KEY) ?? DEFAULT_API_URL;
}

export function setApiUrl(url: string): void {
  if (url && url !== DEFAULT_API_URL) {
    window.localStorage.setItem(API_URL_KEY, url.replace(/\/+$/, ""));
  } else {
    window.localStorage.removeItem(API_URL_KEY);
  }
}

export function getFireworksKey(): string {
  if (typeof window === "undefined") return "";
  return window.localStorage.getItem(FIREWORKS_KEY) ?? "";
}

export function setFireworksKey(key: string): void {
  if (key) {
    window.localStorage.setItem(FIREWORKS_KEY, key);
  } else {
    window.localStorage.removeItem(FIREWORKS_KEY);
  }
}
