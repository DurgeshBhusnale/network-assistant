"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { FullScreenLoader } from "@/components/ui/FullScreenLoader";
import { useMe } from "@/lib/api/hooks/account";
import { useAuth } from "@/lib/auth/AuthProvider";
import { onboardingRoute } from "@/lib/auth/routes";

/** Signed-in users only; others go to /sign-in. */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { session, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !session) router.replace("/sign-in");
  }, [loading, session, router]);

  if (loading || !session) return <FullScreenLoader />;
  return <>{children}</>;
}

/** The main app: signed in and onboarding finished (or skipped); otherwise resume onboarding. */
export function RequireOnboarded({ children }: { children: ReactNode }) {
  return (
    <RequireAuth>
      <OnboardingResume>{children}</OnboardingResume>
    </RequireAuth>
  );
}

function OnboardingResume({ children }: { children: ReactNode }) {
  const me = useMe();
  const router = useRouter();
  const pathname = usePathname();
  const route = me.data ? onboardingRoute(me.data) : null;
  // A cached profile can be stale right after an onboarding step (e.g. consents just saved), so
  // only redirect on fresh data; otherwise the user bounces back to the step they just finished.
  const target = route && !me.isFetching ? route : null;

  useEffect(() => {
    if (target && target !== pathname) router.replace(target);
  }, [target, pathname, router]);

  if (me.isPending || route) return <FullScreenLoader />;
  return <>{children}</>;
}
