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
  const target = me.data ? onboardingRoute(me.data) : null;

  useEffect(() => {
    if (target && target !== pathname) router.replace(target);
  }, [target, pathname, router]);

  if (me.isPending || target) return <FullScreenLoader />;
  return <>{children}</>;
}
