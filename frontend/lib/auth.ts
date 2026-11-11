"use client";

import { useSyncExternalStore } from "react";

// The JWT lives in localStorage: the frontend (Vercel) and backend (Railway) are
// different sites, and the API returns the token in the response body. Trade-off
// vs. an httpOnly cookie is explained in the README. Mitigations: all user and AI
// text is rendered as plain React text, the token expires after 60 minutes, and
// it is cleared on any 401.
const KEY = "briefbase_token";
const CHANGE_EVENT = "briefbase-token-change";

export function getToken(): string | null {
  return localStorage.getItem(KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(KEY, token);
  window.dispatchEvent(new Event(CHANGE_EVENT));
}

export function clearToken(): void {
  localStorage.removeItem(KEY);
  window.dispatchEvent(new Event(CHANGE_EVENT));
}

function subscribe(onChange: () => void): () => void {
  // "storage" fires when another tab changes the token, so logging out in one
  // tab logs out the others; CHANGE_EVENT covers changes made in this tab.
  window.addEventListener("storage", onChange);
  window.addEventListener(CHANGE_EVENT, onChange);
  return () => {
    window.removeEventListener("storage", onChange);
    window.removeEventListener(CHANGE_EVENT, onChange);
  };
}

/**
 * The current token: a string when logged in, null when not, and undefined
 * while it is still unknown (server render and hydration, where localStorage
 * is unavailable). Callers must not redirect on undefined.
 */
export function useToken(): string | null | undefined {
  return useSyncExternalStore(subscribe, getToken, () => undefined);
}
