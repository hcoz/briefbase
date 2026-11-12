"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { QUERY_RETRY_COUNT } from "@/lib/constants";

export default function Providers({ children }: { children: React.ReactNode }) {
  // Created in useState, not at module level, so the cache is never shared between users.
  const [queryClient] = useState(
    () => new QueryClient({ defaultOptions: { queries: { retry: QUERY_RETRY_COUNT } } }),
  );
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
