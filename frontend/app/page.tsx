"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import NoteForm from "@/components/NoteForm";
import NoteList, { NoteSkeletons, useDeleteNote } from "@/components/NoteList";
import { getMe, getNotes } from "@/lib/api";
import { clearToken, useToken } from "@/lib/auth";

export default function NotesPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const token = useToken();
  const [tag, setTag] = useState<string | null>(null);

  // Auth guard. undefined means "not known yet" (hydration), so wait for it.
  // This also fires when a 401 clears the token, or on logout in another tab.
  useEffect(() => {
    if (token === null) router.replace("/login");
  }, [token, router]);

  const me = useQuery({ queryKey: ["me"], queryFn: getMe, enabled: !!token });
  const notes = useQuery({
    queryKey: ["notes", tag],
    queryFn: () => getNotes(tag),
    enabled: !!token,
  });
  const remove = useDeleteNote();

  if (!token) {
    return (
      <main className="center-screen" aria-busy="true">
        <span className="spinner spinner-lg" aria-label="Loading" />
      </main>
    );
  }

  function logout() {
    clearToken();
    queryClient.clear(); // the next user must not see this user's cached notes
  }

  return (
    <>
      <header className="topbar">
        <div className="container topbar-inner">
          <span className="brand">
            <span className="brand-mark" aria-hidden="true">
              B
            </span>
            BriefBase
          </span>
          <span className="spacer" />
          {me.data && <span className="user-email">{me.data.email}</span>}
          <button className="btn btn-ghost btn-sm" onClick={logout}>
            Log out
          </button>
        </div>
      </header>

      <main className="container page">
        <NoteForm />

        <div className="section-header">
          <h2>Your notes</h2>
          {notes.data && <span className="count">{notes.data.length}</span>}
          <span className="spacer" />
          {tag && (
            <button
              className="chip active"
              onClick={() => setTag(null)}
              aria-label={`Clear filter #${tag}`}
            >
              #{tag} <span aria-hidden="true">✕</span>
            </button>
          )}
        </div>

        <div className="stack">
          {remove.isError && (
            <p className="alert">Could not delete note: {remove.error.message}</p>
          )}

          {notes.isPending ? (
            <NoteSkeletons />
          ) : notes.isError ? (
            <p className="alert">Could not load notes: {notes.error.message}</p>
          ) : notes.data.length === 0 ? (
            <div className="empty">
              <h3>{tag ? `No notes tagged #${tag}` : "No notes yet"}</h3>
              <p className="muted small">
                {tag ? "Clear the filter to see all notes." : "Paste one above to get started."}
              </p>
            </div>
          ) : (
            <NoteList
              notes={notes.data}
              activeTag={tag}
              onSelectTag={setTag}
              onDelete={(id) => remove.mutate(id)}
            />
          )}
        </div>
      </main>
    </>
  );
}
