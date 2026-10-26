import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "@/lib/auth/AuthProvider";

import { api, toApiError, unwrap } from "../client";

const statusKey = ["whatsapp", "status"] as const;

export function useWhatsAppStatus() {
  const enabled = useAuth().session !== null;
  return useQuery({
    queryKey: statusKey,
    enabled,
    queryFn: () => unwrap(api.GET("/v1/whatsapp/status")),
  });
}

export function useLinkCode() {
  return useMutation({ mutationFn: () => unwrap(api.POST("/v1/whatsapp/link-code")) });
}

export function useUnlinkWhatsApp() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { error, response } = await api.DELETE("/v1/whatsapp/link");
      if (!response.ok) throw toApiError(response.status, error);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: statusKey }),
  });
}

export function useRefreshWhatsAppStatus() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: statusKey });
}
