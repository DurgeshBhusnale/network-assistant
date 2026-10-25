"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useState, type ReactNode } from "react";

import { registerServiceWorker } from "@/lib/device/serviceWorker";

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () => new QueryClient({ defaultOptions: { queries: { staleTime: 30_000, retry: 1 } } }),
  );

  useEffect(() => {
    if (process.env.NODE_ENV === "production") void registerServiceWorker();
  }, []);

  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
