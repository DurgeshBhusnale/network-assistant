import { OnboardingFrame } from "@/components/shell/OnboardingFrame";
import { RequireAuth } from "@/components/shell/Gates";

export default function OnboardingLayout({ children }: LayoutProps<"/onboarding">) {
  return (
    <RequireAuth>
      <OnboardingFrame>{children}</OnboardingFrame>
    </RequireAuth>
  );
}
