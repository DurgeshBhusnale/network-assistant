import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "@/lib/auth/AuthProvider";

import { api, toApiError, unwrap, type Schemas } from "../client";

export type Profile = Schemas["ProfileOut"];
export type ProfileUpdate = Schemas["ProfileUpdate"];
export type PackInfo = Schemas["PackOut"];
export type Goal = Schemas["GoalOut"];
export type Consents = Schemas["ConsentsOut"];
export type ConsentsUpdate = Schemas["ConsentsUpdate"];

export const keys = {
  me: ["me"] as const,
  packs: ["packs"] as const,
  activeGoal: ["goals", "active"] as const,
  consents: ["privacy", "consents"] as const,
};

function useSignedIn(): boolean {
  return useAuth().session !== null;
}

export function useMe() {
  const enabled = useSignedIn();
  return useQuery({ queryKey: keys.me, enabled, queryFn: () => unwrap(api.GET("/v1/me")) });
}

export function useUpdateMe() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ProfileUpdate) => unwrap(api.PATCH("/v1/me", { body })),
    onSuccess: (profile) => qc.setQueryData(keys.me, profile),
  });
}

export function usePacks() {
  const enabled = useSignedIn();
  return useQuery({
    queryKey: keys.packs,
    enabled,
    staleTime: 10 * 60_000,
    queryFn: () => unwrap(api.GET("/v1/packs")),
  });
}

export function useActiveGoal() {
  const enabled = useSignedIn();
  return useQuery({
    queryKey: keys.activeGoal,
    enabled,
    queryFn: () => unwrap(api.GET("/v1/goals/active")),
  });
}

export function useCreateGoal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Schemas["GoalCreate"]) => unwrap(api.POST("/v1/goals", { body })),
    onSuccess: async (goal) => {
      qc.setQueryData(keys.activeGoal, goal);
      await qc.invalidateQueries({ queryKey: keys.me });
    },
  });
}

export function useConsents() {
  const enabled = useSignedIn();
  return useQuery({
    queryKey: keys.consents,
    enabled,
    queryFn: () => unwrap(api.GET("/v1/privacy/consents")),
  });
}

export function useUpdateConsents() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ConsentsUpdate) => unwrap(api.PUT("/v1/privacy/consents", { body })),
    onSuccess: async (consents) => {
      qc.setQueryData(keys.consents, consents);
      await qc.invalidateQueries({ queryKey: keys.me });
    },
  });
}

export const goalKeys = { current: ["goals", "current"] as const };

/** Active goal, else the latest paused one: what Settings manages (FR-GOAL-4). */
export function useCurrentGoal() {
  const enabled = useSignedIn();
  return useQuery({
    queryKey: goalKeys.current,
    enabled,
    queryFn: () => unwrap(api.GET("/v1/goals/current")),
  });
}

export function useUpdateGoal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: Schemas["GoalUpdate"] }) =>
      unwrap(api.PATCH("/v1/goals/{goal_id}", { params: { path: { goal_id: id } }, body })),
    // Ranking, Today and onboarding all depend on the goal.
    onSuccess: () => qc.invalidateQueries(),
  });
}

/** FR-PRIV-2: the zip comes straight back; the caller saves the blob. */
export function useExportData() {
  return useMutation({
    mutationFn: async () => {
      const { data, error, response } = await api.POST("/v1/privacy/export", { parseAs: "blob" });
      if (error !== undefined || !(data instanceof Blob)) throw toApiError(response.status, error);
      const match = /filename="([^"]+)"/.exec(response.headers.get("Content-Disposition") ?? "");
      return { blob: data, filename: match?.[1] ?? "my-data.zip" };
    },
  });
}

/** FR-PRIV-3: 202 with an empty body, so no unwrap. */
export function useDeleteAccount() {
  return useMutation({
    mutationFn: async (confirm: string) => {
      const { error, response } = await api.POST("/v1/privacy/delete-account", {
        body: { confirm },
        parseAs: "text",
      });
      if (!response.ok) throw toApiError(response.status, error);
    },
  });
}

export function useAdminMetrics() {
  const enabled = useSignedIn();
  return useQuery({
    queryKey: ["admin", "metrics"],
    enabled,
    retry: false,
    queryFn: () => unwrap(api.GET("/v1/admin/metrics")),
  });
}
