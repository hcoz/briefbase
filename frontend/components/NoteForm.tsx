"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { createNote } from "@/lib/api";

export default function NoteForm() {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");

  const create = useMutation({
    mutationFn: createNote,
    onSuccess: () => {
      // Prefix match: refetches the unfiltered list and every filtered one.
      queryClient.invalidateQueries({ queryKey: ["notes"] });
      setTitle("");
      setContent("");
    },
  });

  return (
    <form
      className="stack card"
      onSubmit={(e) => {
        e.preventDefault();
        create.mutate({ title: title.trim() || null, content });
      }}
    >
      <input
        placeholder="Title (optional)"
        maxLength={200}
        value={title}
        onChange={(e) => setTitle(e.target.value)}
      />
      <textarea
        placeholder="Paste your note here…"
        rows={6}
        required
        maxLength={50_000}
        value={content}
        onChange={(e) => setContent(e.target.value)}
      />
      <button type="submit" disabled={create.isPending || !content.trim()}>
        {create.isPending ? "Summarizing…" : "Save note"}
      </button>
      {create.isError && <p className="error">{create.error.message}</p>}
    </form>
  );
}
