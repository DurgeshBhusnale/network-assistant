import { useMutation, useQuery } from "@tanstack/react-query";

import { api, toApiError, unwrap } from "../client";

export function usePushConfig() {
  return useQuery({
    queryKey: ["push", "config"],
    staleTime: 60 * 60_000,
    queryFn: () => unwrap(api.GET("/v1/push/config")),
  });
}

type Sub = { endpoint: string; keys: Record<string, string> };

export function useSavePushSubscription() {
  return useMutation({
    mutationFn: async (body: Sub) => {
      const { error, response } = await api.POST("/v1/push/subscribe", { body });
      if (!response.ok) throw toApiError(response.status, error);
    },
  });
}

export function useDeletePushSubscription() {
  return useMutation({
    mutationFn: async (body: Sub) => {
      const { error, response } = await api.DELETE("/v1/push/subscribe", { body });
      if (!response.ok) throw toApiError(response.status, error);
    },
  });
}
