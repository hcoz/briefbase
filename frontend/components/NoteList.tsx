"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { deleteNote, resummarize, type Note } from "@/lib/api";

type Props = {
  notes: Note[];
  activeTag: string | null;
  onSelectTag: (tag: string) => void;
  onDelete: (id: number) => void;
};

// Optimistic delete: the note disappears from every cached list (filtered and
// unfiltered) at once. On error the snapshot is restored; either way ["notes"]
// is refetched afterwards so the cache matches the server.
// Used by the page, not by NoteItem: the item unmounts as soon as it is
// removed from the cache, and its error message would go with it.
export function useDeleteNote() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteNote,
    onMutate: async (id: number) => {
      await queryClient.cancelQueries({ queryKey: ["notes"] }); // don't let a stale fetch overwrite us
      const previous = queryClient.getQueriesData<Note[]>({ queryKey: ["notes"] });
      queryClient.setQueriesData<Note[]>({ queryKey: ["notes"] }, (old) =>
        old?.filter((n) => n.id !== id),
      );
      return { previous };
    },
    onError: (_err, _id, context) => {
      context?.previous.forEach(([key, data]) => queryClient.setQueryData(key, data));
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: ["notes"] }),
  });
}

export default function NoteList({ notes, activeTag, onSelectTag, onDelete }: Props) {
  return (
    <ul className="notes">
      {notes.map((note) => (
        <NoteItem
          key={note.id}
          note={note}
          activeTag={activeTag}
          onSelectTag={onSelectTag}
          onDelete={onDelete}
        />
      ))}
    </ul>
  );
}

// One component per note so each has its own re-summarize pending/error state.
function NoteItem({ note, activeTag, onSelectTag, onDelete }: { note: Note } & Omit<Props, "notes">) {
  const queryClient = useQueryClient();
  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["notes"] });

  const resum = useMutation({ mutationFn: () => resummarize(note.id), onSuccess: invalidate });

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
        <button onClick={() => resum.mutate()} disabled={resum.isPending}>
          {resum.isPending ? "Summarizing…" : "Re-summarize"}
        </button>
        <button onClick={() => onDelete(note.id)} disabled={resum.isPending}>
          Delete
        </button>
      </div>
      {resum.isError && <p className="error">{resum.error.message}</p>}
    </li>
  );
}
