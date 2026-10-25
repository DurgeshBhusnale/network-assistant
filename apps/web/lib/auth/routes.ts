import type { Profile } from "@/lib/api/hooks/account";

/** Where an authenticated user must be before seeing the app (FR-ONB-1 resume). */
export function onboardingRoute(profile: Profile): string | null {
  if (!profile.privacy_notice_accepted) return "/onboarding/consents";
  switch (profile.onboarding_step) {
    case "goal":
      return "/onboarding/goal";
    case "import":
      return "/onboarding/import";
    case "style":
      return "/onboarding/style";
    case "done":
      return null;
  }
}
