import { clearToken, getToken } from "./auth";

// Inlined at build time by Next (see Dockerfile build arg / Vercel env).
const BASE_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/+$/, "");

export type User = { id: number; email: string };

export type Note = {
  id: number;
  title: string | null;
  content: string;
  summary: string | null;
  tags: string[];
  created_at: string;
};

export type NoteInput = { title: string | null; content: string };

type Token = { access_token: string; token_type: string };

// FastAPI errors are {"detail": "..."}, or a list of field errors for a 422.
async function errorMessage(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) {
      return body.detail.map((d: { msg: string }) => d.msg).join("; ");
    }
  } catch {
    // body was not JSON
  }
  return `Request failed (${res.status})`;
}

async function apiFetch<T>(path: string, init: RequestInit = {}, auth = true): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body) headers.set("Content-Type", "application/json");
  const token = auth ? getToken() : null;
  if (token) headers.set("Authorization", `Bearer ${token}`);

  let res: Response;
  try {
    res = await fetch(`${BASE_URL}${path}`, { ...init, headers });
  } catch {
    throw new Error("Could not reach the server. Please try again.");
  }

  if (!res.ok) {
    // Expired, invalid or revoked session: drop the token. The notes page
    // watches the token (useToken) and redirects to /login when it is gone.
    if (res.status === 401 && auth) clearToken();
    throw new Error(await errorMessage(res));
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// Login/register don't send a stale token, and a 401 there means "wrong
// credentials", not "session expired".
export const login = (email: string, password: string) =>
  apiFetch<Token>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }, false);

export const register = (email: string, password: string) =>
  apiFetch<Token>("/auth/register", { method: "POST", body: JSON.stringify({ email, password }) }, false);

export const getMe = () => apiFetch<User>("/auth/me");

export const getNotes = (tag: string | null) =>
  apiFetch<Note[]>(tag ? `/notes?tag=${encodeURIComponent(tag)}` : "/notes");

export const createNote = (note: NoteInput) =>
  apiFetch<Note>("/notes", { method: "POST", body: JSON.stringify(note) });

export const deleteNote = (id: number) => apiFetch<void>(`/notes/${id}`, { method: "DELETE" });

export const resummarize = (id: number) =>
  apiFetch<Note>(`/notes/${id}/summarize`, { method: "POST" });
