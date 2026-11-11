"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { createNote } from "@/lib/api";
import { CONTENT_MAX_LENGTH, NOTES_KEY, TITLE_MAX_LENGTH } from "@/lib/constants";

const CONTENT_ROWS = 8; // visible height of the note textarea

export default function NoteForm() {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");

  const create = useMutation({
    mutationFn: createNote,
    onSuccess: () => {
      // Prefix match: refetches the unfiltered list and every filtered one.
      queryClient.invalidateQueries({ queryKey: NOTES_KEY });
      setTitle("");
      setContent("");
    },
  });

  return (
    <form
      className="card stack"
      onSubmit={(e) => {
        e.preventDefault();
        create.mutate({ title: title.trim() || null, content });
      }}
    >
      <div className="card-header">
        <h2>New note</h2>
        <p className="muted small">Paste any text. AI will summarize it and add tags.</p>
      </div>

      <label className="field">
        <span className="field-label">Title (optional)</span>
        <input
          className="input"
          placeholder="e.g. Weekly sync notes"
          maxLength={TITLE_MAX_LENGTH}
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
      </label>

      <label className="field">
        <span className="field-label">Note</span>
        <textarea
          className="input"
          placeholder="Paste your note here…"
          rows={CONTENT_ROWS}
          required
          maxLength={CONTENT_MAX_LENGTH}
          value={content}
          onChange={(e) => setContent(e.target.value)}
        />
      </label>

      {create.isError && <p className="alert">{create.error.message}</p>}

      <div className="row">
        <span className="muted small">
          {content.length.toLocaleString()} / {CONTENT_MAX_LENGTH.toLocaleString()}
        </span>
        <span className="spacer" />
        <button
          type="submit"
          className="btn btn-primary"
          disabled={create.isPending || !content.trim()}
        >
          {create.isPending && <span className="spinner" aria-hidden="true" />}
          {create.isPending ? "Summarizing…" : "Save note"}
        </button>
      </div>
    </form>
  );
}
