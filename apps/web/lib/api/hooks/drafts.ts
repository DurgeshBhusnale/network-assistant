import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "@/lib/auth/AuthProvider";

import { api, unwrap, type Schemas } from "../client";

export type Draft = Schemas["DraftOut"];
export type Tone = NonNullable<Schemas["DraftCreate"]["tone"]>;
export type Style = Schemas["StyleOut"];

export const draftKeys = {
  draft: (id: string) => ["drafts", id] as const,
  style: ["style"] as const,
};

export function useDraft(id: string) {
  const enabled = useAuth().session !== null;
  return useQuery({
    queryKey: draftKeys.draft(id),
    enabled,
    queryFn: () => unwrap(api.GET("/v1/drafts/{draft_id}", { params: { path: { draft_id: id } } })),
  });
}

export function useCreateDraft(contactId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Schemas["DraftCreate"]) =>
      unwrap(
        api.POST("/v1/contacts/{contact_id}/draft", {
          params: { path: { contact_id: contactId } },
          body,
        }),
      ),
    onSuccess: (draft) => qc.setQueryData(draftKeys.draft(draft.id), draft),
  });
}

export function useRegenerateDraft(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (tone: Tone | null) =>
      unwrap(
        api.POST("/v1/drafts/{draft_id}/regenerate", {
          params: { path: { draft_id: id } },
          body: { tone },
        }),
      ),
    onSuccess: (draft) => qc.setQueryData(draftKeys.draft(id), draft),
  });
}

export function useEditDraft(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (final_text: string) =>
      unwrap(
        api.PATCH("/v1/drafts/{draft_id}", {
          params: { path: { draft_id: id } },
          body: { final_text },
        }),
      ),
    onSuccess: (draft) => qc.setQueryData(draftKeys.draft(id), draft),
  });
}

export function useStyle() {
  const enabled = useAuth().session !== null;
  return useQuery({
    queryKey: draftKeys.style,
    enabled,
    queryFn: () => unwrap(api.GET("/v1/style")),
  });
}

export function useSaveStyle() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (samples: string[]) => unwrap(api.PUT("/v1/style/samples", { body: { samples } })),
    onSuccess: (style) => qc.setQueryData(draftKeys.style, style),
  });
}
