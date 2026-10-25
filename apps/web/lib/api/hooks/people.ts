import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "@/lib/auth/AuthProvider";
import { accessToken } from "@/lib/auth/supabase";

import { api, toApiError, unwrap, type Schemas } from "../client";

export type ContactSummary = Schemas["ContactSummary"];
export type Person = Schemas["PersonOut"];
export type ContactCreate = Schemas["ContactCreate"];
export type ContactUpdate = Schemas["ContactUpdate"];
export type ImportJob = Schemas["ImportOut"];
export type HistoryItem = Schemas["HistoryItem"];
export type Memory = Schemas["MemoryOut"];

export const peopleKeys = {
  all: ["contacts"] as const,
  list: (q: string) => ["contacts", "list", q] as const,
  person: (id: string) => ["contacts", "person", id] as const,
};

export function useContacts(q: string) {
  const enabled = useAuth().session !== null;
  return useInfiniteQuery({
    queryKey: peopleKeys.list(q),
    enabled,
    initialPageParam: null as string | null,
    queryFn: ({ pageParam }) =>
      unwrap(
        api.GET("/v1/contacts", {
          params: { query: { q: q || undefined, cursor: pageParam ?? undefined } },
        }),
      ),
    getNextPageParam: (last) => last.next_cursor ?? null,
  });
}

export function usePerson(id: string) {
  const enabled = useAuth().session !== null;
  return useQuery({
    queryKey: peopleKeys.person(id),
    enabled,
    queryFn: () =>
      unwrap(api.GET("/v1/contacts/{contact_id}", { params: { path: { contact_id: id } } })),
  });
}

function useInvalidatePeople() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: peopleKeys.all });
}

export function useCreateContact() {
  const invalidate = useInvalidatePeople();
  return useMutation({
    mutationFn: (body: ContactCreate) => unwrap(api.POST("/v1/contacts", { body })),
    onSuccess: invalidate,
  });
}

export function useUpdateContact(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ContactUpdate) =>
      unwrap(
        api.PATCH("/v1/contacts/{contact_id}", { params: { path: { contact_id: id } }, body }),
      ),
    onSuccess: async (person) => {
      qc.setQueryData(peopleKeys.person(id), person);
      await qc.invalidateQueries({ queryKey: ["contacts", "list"] });
    },
  });
}

export function useDeleteContact() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { error, response } = await api.DELETE("/v1/contacts/{contact_id}", {
        params: { path: { contact_id: id } },
      });
      if (!response.ok) throw toApiError(response.status, error);
    },
    onSuccess: async (_, id) => {
      qc.removeQueries({ queryKey: peopleKeys.person(id) });
      await qc.invalidateQueries({ queryKey: ["contacts", "list"] });
    },
  });
}

export function useAddMemory(contactId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (text: string) =>
      unwrap(
        api.POST("/v1/contacts/{contact_id}/memories", {
          params: { path: { contact_id: contactId } },
          body: { text },
        }),
      ),
    onSuccess: () => qc.invalidateQueries({ queryKey: peopleKeys.person(contactId) }),
  });
}

export function useDeleteMemory(contactId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (memoryId: string) => {
      const { error, response } = await api.DELETE("/v1/memories/{memory_id}", {
        params: { path: { memory_id: memoryId } },
      });
      if (!response.ok) throw toApiError(response.status, error);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: peopleKeys.person(contactId) }),
  });
}

export function useStagePicker() {
  return useMutation({
    mutationFn: (contacts: Schemas["PickerContact"][]) =>
      unwrap(api.POST("/v1/imports/picker", { body: { contacts } })),
  });
}

/** Multipart upload; openapi-fetch's JSON body handling doesn't fit FormData, so call directly. */
export function useStageFile() {
  return useMutation({
    mutationFn: async (file: File): Promise<ImportJob> => {
      const form = new FormData();
      form.append("file", file);
      const token = await accessToken();
      const response = await fetch("/api/v1/imports/file", {
        method: "POST",
        body: form,
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      const body: unknown = await response.json().catch(() => null);
      if (!response.ok) throw toApiError(response.status, body);
      return body as ImportJob;
    },
  });
}

export function useCommitImport() {
  const invalidate = useInvalidatePeople();
  return useMutation({
    mutationFn: (id: string) =>
      unwrap(api.POST("/v1/imports/{import_id}/commit", { params: { path: { import_id: id } } })),
    onSuccess: invalidate,
  });
}
