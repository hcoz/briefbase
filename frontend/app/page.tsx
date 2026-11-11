"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import NoteForm from "@/components/NoteForm";
import NoteList, { useDeleteNote } from "@/components/NoteList";
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

  if (!token) return <main>Loading…</main>;

  function logout() {
    clearToken();
    queryClient.clear(); // the next user must not see this user's cached notes
  }

  return (
    <main>
      <header className="row">
        <h1>BriefBase</h1>
        <span className="spacer" />
        {me.data && <span className="muted">{me.data.email}</span>}
        <button onClick={logout}>Log out</button>
      </header>

      <NoteForm />

      <h2>Your notes</h2>
      {tag && (
        <p className="filter">
          Filtered by <strong>#{tag}</strong>{" "}
          <button className="link" onClick={() => setTag(null)}>
            ✕ clear
          </button>
        </p>
      )}
      {remove.isError && <p className="error">Could not delete note: {remove.error.message}</p>}

      {notes.isPending ? (
        <p>Loading notes…</p>
      ) : notes.isError ? (
        <p className="error">Could not load notes: {notes.error.message}</p>
      ) : notes.data.length === 0 ? (
        <p className="muted">{tag ? `No notes tagged #${tag}.` : "No notes yet. Paste one above."}</p>
      ) : (
        <NoteList
          notes={notes.data}
          activeTag={tag}
          onSelectTag={setTag}
          onDelete={(id) => remove.mutate(id)}
        />
      )}
    </main>
  );
}
