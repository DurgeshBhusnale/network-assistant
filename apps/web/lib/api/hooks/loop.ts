import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "@/lib/auth/AuthProvider";

import { api, toApiError, unwrap, type Schemas } from "../client";
import { draftKeys } from "./drafts";

export type Today = Schemas["TodayOut"];
export type SuggestionItem = Schemas["SuggestionOut"];
export type GoalStrip = Schemas["GoalStripOut"];
export type Replies = Schemas["RepliesOut"];
export type PendingReply = Schemas["PendingReply"];
export type Progress = Schemas["ProgressOut"];
export type SendResult = Schemas["SendOut"];
export type InteractionIn = Schemas["InteractionIn"];

export const loopKeys = {
  today: ["today"] as const,
  replies: ["replies"] as const,
  progress: ["progress"] as const,
};

function useEnabled(): boolean {
  return useAuth().session !== null;
}

export function useToday() {
  return useQuery({
    queryKey: loopKeys.today,
    enabled: useEnabled(),
    queryFn: () => unwrap(api.GET("/v1/today")),
  });
}

export function useRepliesPending() {
  return useQuery({
    queryKey: loopKeys.replies,
    enabled: useEnabled(),
    staleTime: 60_000,
    queryFn: () => unwrap(api.GET("/v1/replies/pending")),
  });
}

export function useProgress() {
  return useQuery({
    queryKey: loopKeys.progress,
    enabled: useEnabled(),
    queryFn: () => unwrap(api.GET("/v1/progress")),
  });
}

function useInvalidateLoop() {
  const qc = useQueryClient();
  return () =>
    Promise.all([
      qc.invalidateQueries({ queryKey: loopKeys.today }),
      qc.invalidateQueries({ queryKey: loopKeys.replies }),
      qc.invalidateQueries({ queryKey: loopKeys.progress }),
    ]);
}

async function noContent(promise: Promise<{ error?: unknown; response: Response }>) {
  const { error, response } = await promise;
  if (!response.ok) throw toApiError(response.status, error);
}

export function useSnooze() {
  const invalidate = useInvalidateLoop();
  return useMutation({
    mutationFn: ({ id, days }: { id: string; days: 1 | 7 }) =>
      noContent(
        api.POST("/v1/suggestions/{suggestion_id}/snooze", {
          params: { path: { suggestion_id: id } },
          body: { days },
        }),
      ),
    onSuccess: invalidate,
  });
}

export function useDismiss() {
  const invalidate = useInvalidateLoop();
  return useMutation({
    mutationFn: (id: string) =>
      noContent(
        api.POST("/v1/suggestions/{suggestion_id}/dismiss", {
          params: { path: { suggestion_id: id } },
        }),
      ),
    onSuccess: invalidate,
  });
}

export function useSuggestionDraft() {
  const qc = useQueryClient();
  const invalidate = useInvalidateLoop();
  return useMutation({
    mutationFn: (id: string) =>
      unwrap(
        api.POST("/v1/suggestions/{suggestion_id}/draft", {
          params: { path: { suggestion_id: id } },
          body: {},
        }),
      ),
    onSuccess: async (draft) => {
      qc.setQueryData(draftKeys.draft(draft.id), draft);
      await invalidate();
    },
  });
}

export function useSend(draftId: string) {
  return useMutation({
    mutationFn: (channel: "whatsapp" | "linkedin") =>
      unwrap(
        api.POST("/v1/drafts/{draft_id}/send", {
          params: { path: { draft_id: draftId } },
          body: { channel },
        }),
      ),
  });
}

export function useLogInteraction() {
  const qc = useQueryClient();
  const invalidate = useInvalidateLoop();
  return useMutation({
    mutationFn: (body: InteractionIn) => unwrap(api.POST("/v1/interactions", { body })),
    onSuccess: async (_, body) => {
      if (body.draft_id) await qc.invalidateQueries({ queryKey: draftKeys.draft(body.draft_id) });
      await qc.invalidateQueries({ queryKey: ["contacts", "person", body.contact_id] });
      await invalidate();
    },
  });
}
