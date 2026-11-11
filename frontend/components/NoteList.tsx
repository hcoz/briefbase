"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { deleteNote, resummarize, type Note } from "@/lib/api";

type Props = {
  notes: Note[];
  activeTag: string | null;
  onSelectTag: (tag: string) => void;
};

export default function NoteList({ notes, activeTag, onSelectTag }: Props) {
  return (
    <ul className="notes">
      {notes.map((note) => (
        <NoteItem key={note.id} note={note} activeTag={activeTag} onSelectTag={onSelectTag} />
      ))}
    </ul>
  );
}

// One component per note so each has its own pending/error state.
function NoteItem({ note, activeTag, onSelectTag }: { note: Note } & Omit<Props, "notes">) {
  const queryClient = useQueryClient();
  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["notes"] });

  const remove = useMutation({ mutationFn: () => deleteNote(note.id), onSuccess: invalidate });
  const resum = useMutation({ mutationFn: () => resummarize(note.id), onSuccess: invalidate });
  const busy = remove.isPending || resum.isPending;

  // All user and AI text is rendered as plain React text (escaped), never as HTML.
  return (
    <li className="card">
      <div className="row">
        <strong>{note.title ?? "Untitled"}</strong>
        <span className="spacer" />
        <small className="muted">{new Date(note.created_at).toLocaleString()}</small>
      </div>

      {note.summary ? <p>{note.summary}</p> : <p className="muted">Summary unavailable.</p>}

      {note.tags.length > 0 && (
        <div className="tags">
          {note.tags.map((t) => (
            <button
              key={t}
              className={t === activeTag ? "tag active" : "tag"}
              onClick={() => onSelectTag(t)}
            >
              #{t}
            </button>
          ))}
        </div>
      )}

      <details>
        <summary>Original note</summary>
        <p className="content">{note.content}</p>
      </details>

      <div className="row">
        <button onClick={() => resum.mutate()} disabled={busy}>
          {resum.isPending ? "Summarizing…" : "Re-summarize"}
        </button>
        <button onClick={() => remove.mutate()} disabled={busy}>
          {remove.isPending ? "Deleting…" : "Delete"}
        </button>
      </div>
      {resum.isError && <p className="error">{resum.error.message}</p>}
      {remove.isError && <p className="error">{remove.error.message}</p>}
    </li>
  );
}
