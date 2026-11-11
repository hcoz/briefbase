// Form limits. They mirror backend/app/constants.py. The API is the source of
// truth and validates every request; these only drive form hints.
export const PASSWORD_MIN_LENGTH = 8;
export const PASSWORD_MAX_LENGTH = 128;
export const TITLE_MAX_LENGTH = 200;
export const CONTENT_MAX_LENGTH = 20_000;

// React Query keys. NOTES_KEY is a prefix: invalidating it refetches the
// unfiltered list and every filtered one built by notesKey().
export const ME_KEY = ["me"] as const;
export const NOTES_KEY = ["notes"] as const;
export const notesKey = (tag: string | null) => [...NOTES_KEY, tag] as const;

// How many times a failed query is retried before the error is shown.
export const QUERY_RETRY_COUNT = 1;
