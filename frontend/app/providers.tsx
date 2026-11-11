"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { QUERY_RETRY_COUNT } from "@/lib/constants";

export default function Providers({ children }: { children: React.ReactNode }) {
  // Created once per browser session (inside useState), never shared at module level.
  const [queryClient] = useState(
    () => new QueryClient({ defaultOptions: { queries: { retry: QUERY_RETRY_COUNT } } }),
  );
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
