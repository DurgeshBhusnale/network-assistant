import { useQuery } from "@tanstack/react-query";

import { api, type Schemas } from "../client";

export type Health = Schemas["HealthResponse"];

/** API health. A 503 still carries a HealthResponse body saying which dependency is down. */
export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: async (): Promise<Health> => {
      const { data, error } = await api.GET("/v1/health");
      if (data) return data;
      if (typeof error === "object" && error !== null && "status" in error) return error;
      throw new Error("API unreachable");
    },
  });
}
