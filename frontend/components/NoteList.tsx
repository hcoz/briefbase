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

// Placeholder cards shown while the first fetch is in flight.
export function NoteSkeletons() {
  return (
    <ul className="notes" aria-busy="true" aria-label="Loading notes">
      {[0, 1, 2].map((i) => (
        <li key={i} className="card note">
          <div className="skeleton skeleton-line" style={{ width: "40%", height: 16 }} />
          <div className="skeleton skeleton-line" />
          <div className="skeleton skeleton-line" style={{ width: "75%" }} />
          <div className="row">
            <div className="skeleton" style={{ width: 64, height: 22, borderRadius: 999 }} />
            <div className="skeleton" style={{ width: 80, height: 22, borderRadius: 999 }} />
          </div>
        </li>
      ))}
    </ul>
  );
}

// One component per note so each has its own re-summarize pending/error state.
function NoteItem({ note, activeTag, onSelectTag, onDelete }: { note: Note } & Omit<Props, "notes">) {
  const queryClient = useQueryClient();
  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["notes"] });

  const resum = useMutation({ mutationFn: () => resummarize(note.id), onSuccess: invalidate });

  const created = new Date(note.created_at);

  // All user and AI text is rendered as plain React text (escaped), never as HTML.
  return (
    <li className="card note">
      <div className="row">
        <h3 className={note.title ? "note-title" : "note-title untitled"}>
          {note.title ?? "Untitled"}
        </h3>
        <span className="spacer" />
        <time
          className="note-date"
          dateTime={note.created_at}
          title={created.toLocaleString()}
        >
          {created.toLocaleDateString(undefined, { dateStyle: "medium" })}
        </time>
      </div>

      {note.summary ? (
        <p className="note-summary">{note.summary}</p>
      ) : (
        <div className="row">
          <span className="badge-warn">Summary unavailable</span>
          <span className="muted small">Try re-summarizing.</span>
        </div>
      )}

      {note.tags.length > 0 && (
        <div className="chips">
          {note.tags.map((t) => (
            <button
              key={t}
              className={t === activeTag ? "chip active" : "chip"}
              onClick={() => onSelectTag(t)}
              aria-pressed={t === activeTag}
            >
              #{t}
            </button>
          ))}
        </div>
      )}

      {resum.isError && <p className="alert">{resum.error.message}</p>}

      <div className="note-footer">
        <details className="original">
          <summary>Show original</summary>
          <p className="content">{note.content}</p>
        </details>
        <div className="note-actions">
          <button
            className="btn btn-ghost btn-sm"
            onClick={() => resum.mutate()}
            disabled={resum.isPending}
          >
            {resum.isPending && <span className="spinner" aria-hidden="true" />}
            {resum.isPending ? "Summarizing…" : "Re-summarize"}
          </button>
          <button
            className="btn btn-ghost btn-danger btn-sm"
            onClick={() => onDelete(note.id)}
            disabled={resum.isPending}
          >
            Delete
          </button>
        </div>
      </div>
    </li>
  );
}
