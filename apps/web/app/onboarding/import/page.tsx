import { OnboardingPlaceholderStep } from "@/components/shell/OnboardingPlaceholderStep";
import { copy } from "@/lib/copy/en";

export default function ImportStepPage() {
  return (
    <OnboardingPlaceholderStep
      step={2}
      title={copy.onboarding.importTitle}
      body={copy.onboarding.importBody}
      next="style"
      nextRoute="/onboarding/style"
    />
  );
}
