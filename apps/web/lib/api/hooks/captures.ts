import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "@/lib/auth/AuthProvider";

import { api, toApiError, unwrap, type Schemas } from "../client";
import { loopKeys } from "./loop";

export type Capture = Schemas["CaptureOut"];
export type CaptureCandidate = Schemas["CaptureCandidate"];
export type CaptureDecision = Schemas["CaptureDecision"];
export type UploadMime = Schemas["UploadUrlIn"]["mime"];

const captureKey = (id: string) => ["captures", id] as const;

/** Polls while the worker transcribes and extracts. */
export function useCapture(id: string | null) {
  const enabled = useAuth().session !== null && id !== null;
  return useQuery({
    queryKey: captureKey(id ?? "none"),
    enabled,
    queryFn: () =>
      unwrap(api.GET("/v1/captures/{capture_id}", { params: { path: { capture_id: id ?? "" } } })),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "queued" || status === "processing" ? 1500 : false;
    },
  });
}

export function useUploadAudio() {
  return useMutation({
    mutationFn: async ({ blob, mime }: { blob: Blob; mime: UploadMime }) => {
      const { upload_url, storage_path } = await unwrap(
        api.POST("/v1/captures/upload-url", { body: { mime } }),
      );
      const response = await fetch(upload_url, {
        method: "PUT",
        body: blob,
        headers: { "content-type": mime },
      });
      if (!response.ok) throw toApiError(response.status, null);
      return storage_path;
    },
  });
}

export function useCreateCapture() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Schemas["CaptureCreate"]) => unwrap(api.POST("/v1/captures", { body })),
    onSuccess: (capture) => qc.setQueryData(captureKey(capture.id), capture),
  });
}

export function useConfirmCapture(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (decisions: CaptureDecision[]) =>
      unwrap(
        api.POST("/v1/captures/{capture_id}/confirm", {
          params: { path: { capture_id: id } },
          body: { decisions },
        }),
      ),
    onSuccess: async () => {
      await Promise.all([
        qc.invalidateQueries({ queryKey: captureKey(id) }),
        qc.invalidateQueries({ queryKey: ["contacts"] }),
        qc.invalidateQueries({ queryKey: loopKeys.today }),
      ]);
    },
  });
}

export function useDiscardCapture(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { error, response } = await api.POST("/v1/captures/{capture_id}/discard", {
        params: { path: { capture_id: id } },
      });
      if (!response.ok) throw toApiError(response.status, error);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: captureKey(id) }),
  });
}
