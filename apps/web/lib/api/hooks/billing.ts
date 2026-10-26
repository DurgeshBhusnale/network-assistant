import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "@/lib/auth/AuthProvider";

import { api, toApiError, unwrap, type Schemas } from "../client";

export type Plans = Schemas["PlansOut"];
export type Entitlement = Schemas["EntitlementOut"];
export type Order = Schemas["OrderOut"];
export type PaymentStatus = Schemas["PaymentStatusOut"];
export type ProductCode = Schemas["OrderIn"]["product"];

const keys = {
  plans: ["billing", "plans"] as const,
  entitlement: ["billing", "entitlement"] as const,
};

export function usePlans() {
  return useQuery({
    queryKey: keys.plans,
    staleTime: 10 * 60_000,
    queryFn: () => unwrap(api.GET("/v1/billing/plans")),
  });
}

export function useEntitlement() {
  const enabled = useAuth().session !== null;
  return useQuery({
    queryKey: keys.entitlement,
    enabled,
    queryFn: () => unwrap(api.GET("/v1/billing/entitlement")),
  });
}

export function useCreateOrder() {
  return useMutation({
    mutationFn: (product: ProductCode) =>
      unwrap(api.POST("/v1/billing/orders", { body: { product } })),
  });
}

export function useCheckoutResult() {
  return useMutation({
    mutationFn: (body: Schemas["CheckoutResultIn"]) =>
      unwrap(api.POST("/v1/billing/checkout-result", { body })),
  });
}

/** Waits for the verified webhook (the only thing that grants a plan). */
export async function waitForPaid(
  orderId: string,
  timeoutMs = 30_000,
): Promise<PaymentStatus | null> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const { data, error, response } = await api.GET("/v1/billing/orders/{order_id}", {
      params: { path: { order_id: orderId } },
    });
    if (error) throw toApiError(response.status, error);
    if (data?.status === "paid") return data;
    await new Promise((r) => setTimeout(r, 2000));
  }
  return null;
}

export function useDevComplete() {
  return useMutation({
    mutationFn: (orderId: string) =>
      unwrap(
        api.POST("/v1/billing/dev/complete/{order_id}", {
          params: { path: { order_id: orderId } },
        }),
      ),
  });
}

export function useRefreshPlan() {
  const qc = useQueryClient();
  return () =>
    Promise.all([
      qc.invalidateQueries({ queryKey: keys.entitlement }),
      qc.invalidateQueries({ queryKey: ["today"] }),
    ]);
}

export function rupees(paise: number): string {
  return `₹${(paise / 100).toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}
