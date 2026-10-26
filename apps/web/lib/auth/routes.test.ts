import type { Profile } from "@/lib/api/hooks/account";

import { onboardingRoute } from "./routes";

const base: Profile = {
  user_id: "u1",
  email: "u@example.com",
  display_name: null,
  language: "en",
  timezone: "Asia/Kolkata",
  nudge_time: "09:00",
  onboarding_step: "done",
  privacy_notice_accepted: true,
  whatsapp_linked: false,
  email_digest: true,
};

describe("onboardingRoute", () => {
  it.each([
    [{ privacy_notice_accepted: false, onboarding_step: "done" }, "/onboarding/consents"],
    [{ onboarding_step: "goal" }, "/onboarding/goal"],
    [{ onboarding_step: "import" }, "/onboarding/import"],
    [{ onboarding_step: "style" }, "/onboarding/style"],
    [{ onboarding_step: "done" }, null],
  ] as const)("%o → %s", (overrides, expected) => {
    expect(onboardingRoute({ ...base, ...overrides })).toBe(expected);
  });
});
